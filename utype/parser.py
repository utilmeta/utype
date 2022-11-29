from typing import Optional, Callable, Type, List, Dict, Iterable, Tuple, Set
from .field import SchemaField
from .rule import resolve_forward_type
from .options import Options, RuntimeOptions
from .utils.compat import *
from .utils import exceptions as exc
from functools import cached_property
import inspect
import sys

__parsers__ = {}
LAMBDA_NAME = (lambda: None).__name__
LOCALS_NAME = '<locals>'
default_options = Options()


class FunctionAnalyzer:
    @classmethod
    def validate_function(cls, f):
        return isinstance(f, (staticmethod, classmethod)) or inspect.ismethod(f) or inspect.isfunction(f)

    @classmethod
    def analyze_func(cls, f):
        first_reserve = None
        if isinstance(f, classmethod):
            first_reserve = True
            f = f.__func__
        elif isinstance(f, staticmethod):
            first_reserve = False
            f = f.__func__
        elif inspect.ismethod(f):
            first_reserve = False
        elif not inspect.isfunction(f):
            raise TypeError(f'Invalid function: {f}')
        return f, first_reserve

    @classmethod
    def get_return_type(cls, f):
        if isinstance(f, (staticmethod, classmethod)):
            f = f.__func__
        if not f:
            return None
        return getattr(f, '__annotations__', {}).get('return')

    @classmethod
    def inferred_instancemethod(cls, func):
        return hasattr(func, '__qualname__') and func.__qualname__.endswith('.' + func.__name__) and \
               not func.__qualname__.endswith(f'{LOCALS_NAME}.' + func.__name__)

    def __init__(self, func):
        if not self.validate_function(func):
            raise TypeError(f'{self.__class__}: invalid function or method: {func}, must be method or function')

        self.instancemethod = False
        self.classmethod = isinstance(func, classmethod)
        self.staticmethod = isinstance(func, staticmethod)

        self.is_method = inspect.ismethod(func)
        self.is_lambda = inspect.isfunction(func) and func.__name__ == LAMBDA_NAME
        self.is_coroutine = inspect.iscoroutinefunction(func)
        self.is_asynchronous = self.is_coroutine or inspect.isasyncgenfunction(func)
        self.is_generator = inspect.isgeneratorfunction(func)

        func, self.first_reserve = self.analyze_func(func)
        parameters = inspect.signature(func).parameters.items()
        self.func = func

        if not self.first_reserve and not self.is_method and not self.is_lambda:
            # guess instance method
            if self.inferred_instancemethod(func) and len(parameters) >= 1:
                self.first_reserve = True
                self.instancemethod = True

        self.reserve_name = None
        if self.first_reserve:
            _r, *parameters = parameters
            self.reserve_name = _r[0]

        # annotates = {k: v.annotation for k, v in self.parameters if v.annotation is not v.empty}
        # defaults = {k: v.default for k, v in self.parameters if v.default is not v.empty}
        # if a param is not defaulted or annotated, it rule is Rule(require=True)

        self.parameters: Iterable[Tuple[str, inspect.Parameter]] = parameters
        self.key_var = None  # only for function, **kwargs
        self.pos_var_index = None
        self.pos_var = None  # only for function, *args
        self.pos_key_map = {}   # reverse version of arg index
        self.arg_index = {}
        self.max_args = 0
        self.min_args = 0
        self.arg_names = [k for k, v in self.parameters]
        self.kw_names = [k for k, v in self.parameters if v.kind in (v.KEYWORD_ONLY, v.POSITIONAL_OR_KEYWORD)]
        self.common_arg_names = [k for k, v in self.parameters if v.kind not in (v.VAR_POSITIONAL, v.VAR_KEYWORD)]
        self.pos_only_keys = []
        self.omitted_keys = []

        self.pos_annotation = None
        self.kw_annotation = None
        self.return_annotation = self.get_return_type(self.func)

        for i, (k, v) in enumerate(self.parameters):
            v: inspect.Parameter
            if v.kind == v.VAR_POSITIONAL:
                self.pos_var_index = i
                self.pos_var = k
                if v.annotation != v.empty:
                    self.pos_annotation = v.annotation
                continue
            elif v.kind == v.VAR_KEYWORD:
                self.key_var = k
                if v.annotation != v.empty:
                    self.kw_annotation = v.annotation
                continue
            elif v.kind != v.KEYWORD_ONLY:
                self.max_args += 1
                self.pos_key_map[i] = k
                self.arg_index[k] = i
            if v.kind == v.POSITIONAL_ONLY:
                self.pos_only_keys.append(k)
                self.min_args += 1

    def __str__(self):
        return f'<{self.__class__.__name__}: {self.func.__qualname__}>'

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.func.__qualname__}>'


class Parser:
    options_cls = Options
    schema_field_cls = SchemaField
    function_analyzer_cls = FunctionAnalyzer

    DEFAULT_EXCLUDE_VARS = {
        '__options__',
        '__class__'
    }

    @classmethod
    def apply_for(cls, obj, no_cache: bool = False):
        if isinstance(obj, cls):
            return obj
        global __parsers__
        key = (cls, obj)
        if not no_cache and key in __parsers__:
            return __parsers__[key]
        inst = cls(obj)
        if not no_cache:
            __parsers__[key] = inst
        return inst

    def __init__(self, obj):
        self.obj = obj
        self.options: Options = default_options
        # if not isinstance(self.options, Options):
        #     self.options = default_options
        self.function_analyzer = self.function_analyzer_cls(obj) if \
            self.function_analyzer_cls.validate_function(obj) else None

        self.forward_refs: Dict[str, ForwardRef] = {}  # store unresolved ref
        self.fields: Dict[str, SchemaField] = {}
        self.exclude_vars: Set[str] = set(self.DEFAULT_EXCLUDE_VARS)
        # these data structures are designed to speed up the parsing
        self.case_insensitive_names: Set[str] = set()
        self.field_alias_map: Dict[str, str] = {}
        self.attr_alias_map: Dict[str, str] = {}
        self.error_hooks: Dict[Type[Exception], Callable] = {}
        self.data_first_search = None

        self.init_parser: Optional[Parser] = None

        self.generate_from_bases()
        self.generate_fields()
        self.generate_from_init()
        self.generate_aliases()
        self.validate_fields()
        self.assign_search_strategy()

        self.position_type = None
        self.addition_type = None
        self.return_type = None

        if self.function_analyzer:
            if self.function_analyzer.pos_annotation:
                self.position_type = self.rule_cls.parse_annotation(
                    annotation=self.function_analyzer.pos_annotation,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                )
            if self.function_analyzer.kw_annotation:
                self.addition_type = self.rule_cls.parse_annotation(
                    annotation=self.function_analyzer.kw_annotation,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs
                )
            if self.function_analyzer.return_annotation:
                self.return_type = self.rule_cls.parse_annotation(
                    annotation=self.function_analyzer.return_annotation,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs
                )

    # @cached_property
    # def input_fields(self):
    #     fields = {}
    #     for key, field in self.fields.items():
    #         if not field.no_input:
    #             fields[key] = field
    #     return fields

    @cached_property
    def property_fields(self):
        fields = {}
        for key, field in self.fields.items():
            if field.property:
                fields[key] = field
        return fields

    # @cached_property
    # def no_output_fields(self):
    #     fields = {}
    #     for key, field in self.fields.items():
    #         if field.no_output:
    #             fields[key] = field
    #     return fields

    # @cached_property
    # def required_fields(self):
    #     fields = []
    #     for key, field in self.fields.items():
    #         if field.required:
    #             fields.append(key)
    #     return fields

    def validate_fields(self):
        if self.options.allowed_runtime_options:
            if '__options__' in self.fields:
                raise ValueError(f'{self.obj} did not specify no_runtime_options=True, '
                                 f'so name "__options__" is used to passing runtime options, which is conflicted'
                                 f' with field {self.fields["__options__"]}')

    def _get_field_from(self, fields: dict, key: str) -> Optional[SchemaField]:
        if key in fields:
            return fields[key]
        if key in self.field_alias_map:
            return fields[self.field_alias_map[key]]
        if not key.islower() and key.lower() in self.case_insensitive_names:
            # avoid recursive
            return self._get_field_from(fields, key.lower())
        return None

    # def get_input_field(self, key: str) -> Optional[SchemaField]:
    #     return self._get_field_from(self.input_fields, key)

    def get_field(self, key: str) -> Optional[SchemaField]:
        return self._get_field_from(self.fields, key)

    def get_attname(self, key: str) -> Optional[str]:
        if key in self.attr_alias_map:
            return self.attr_alias_map[key]
        if not key.islower() and key.lower() in self.case_insensitive_names:
            # avoid recursive
            if key.lower() in self.attr_alias_map:
                return self.attr_alias_map[key.lower()]
        return None

    def assign_search_strategy(self):
        if self.options.data_first_search is not None:
            # explicitly specified
            self.data_first_search = self.options.data_first_search
            return
        if self.case_insensitive_names or self.field_alias_map or \
                self.options.ignore_required or self.options.addition:
            # in those cases data first is faster than field first
            self.data_first_search = True
        else:
            self.data_first_search = False

    # @property
    # def additional_options(self):
    #     if not self.function_analyzer:
    #         return default_options
    #     options = {}
    #     if self.addition_type:
    #         options.update(addition=self.addition_type)
    #     elif self.function_analyzer.key_var:
    #         options.update(addition=True)
    #     elif '__options__' not in self.function_analyzer.kw_names:
    #         # if __init__ does not take keyword params, and did not specify __options__ param
    #         options.update(no_runtime_options=True)
    #     return self.options_cls(**options) if options else default_options

    @property
    def rule_cls(self):
        return self.schema_field_cls.field_cls.rule_cls

    @property
    def module_name(self):
        return self.obj.__module__

    @property
    def obj_name(self):
        return getattr(self.obj, '__qualname__', None) or getattr(self.obj, '__name__')

    @property
    def globals(self):
        if hasattr(self.obj, '__globals__'):
            # like a function
            return self.obj.__globals__
        return sys.modules[self.module_name].__dict__

    def __iter__(self):
        return iter(self.fields)

    def __getitem__(self, item):
        return self.fields[item]

    def __contains__(self, item):
        return item in self.fields

    def __len__(self):
        return len(self.fields)

    def resolve_forward_refs(self, local_vars=None, ignore_errors: bool = True):
        if not self.forward_refs:
            return
        resolved = False
        for name in list(self.forward_refs):
            ref = self.forward_refs[name]
            try:
                evaluate_forward_ref(ref, self.globals, local_vars)
                if ref.__forward_evaluated__:
                    # evaluated successfully, pop
                    value = ref.__forward_value__
                    if not isinstance(value, type):
                        # maybe some very foolish ForwardRef like
                        # a: "List[str, SomeClass]"
                        # we will just treat this nicely
                        __origin = get_origin(value)
                    else:
                        __origin = value
                    if __origin:
                        ref.__forward_value__ = self.rule_cls.parse_annotation(
                            annotation=value,
                            constraints=getattr(ref, '__constraints__', None),
                            global_vars=self.globals,
                            forward_refs=self.forward_refs,
                            forward_key=name
                        )
                    else:
                        # maybe just ref to some const
                        # a: PositiveInt | '"some value"'
                        # we will not go through the ForwardRef
                        # as the typing star
                        ref.__forward_value__ = self.rule_cls.annotate(
                            type_=type(value),
                            constraints={'const': ref.__forward_value__}
                        )
                    resolved = True
                    self.forward_refs.pop(name)
            except Exception:
                if ignore_errors:
                    continue
                raise
        if resolved:
            for field in self.fields.values():
                field.resolve_forward_refs()
            # resolve for types
            self.position_type, r = resolve_forward_type(self.position_type)
            self.addition_type, r = resolve_forward_type(self.addition_type)
            self.return_type, r = resolve_forward_type(self.return_type)

    @classmethod
    def validate_field_name(cls, name: str):
        if name.startswith('_'):
            return False
        return True

    def validate_class_field_name(self, name: str):
        if not self.validate_field_name(name):
            return False
        for base in self.obj.__bases__:
            annotation = base.__annotations__.get(name)
            if annotation:
                if is_final(annotation):
                    raise TypeError(f'field: {repr(name)} was declared as Final in {base}, '
                                    f'so {self.obj} cannot annotate it again')
            attr = getattr(base, name, None)
            if self.is_class_internals(attr, attname=name, class_qualname=base.__qualname__):
                raise TypeError(f'field: {repr(name)} was declared in {base}, '
                                f'so {self.obj} cannot annotate it again')
        return True

    @classmethod
    def is_class_internals(cls, attr, attname: str, class_qualname: str):
        qualname: str = getattr(attr, '__qualname__', None)
        name: str = getattr(attr, '__name__', None)
        if name and qualname:
            if attname == name and qualname.startswith(f'{class_qualname}.'):
                return True
        return False

    def generate_from_bases(self):
        if not inspect.isclass(self.obj):
            return

        fields = {}
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()
        exclude_vars = set()
        option_list = []

        for base in reversed(self.obj.__bases__):   # according to MRO
            if not isinstance(base, type(self.obj)) or base is object:
                continue
            parser = self.apply_for(base)       # should use cache
            if not parser.options.vacuum:
                option_list.append(parser.options)

            fields.update(parser.fields)

            exclude_vars.update(parser.exclude_vars)
            alias_map.update(parser.field_alias_map)
            attr_alias_map.update(parser.attr_alias_map)
            case_insensitive_names.update(parser.case_insensitive_names)

        cls_options = getattr(self.obj, '__options__', None)
        if cls_options:
            option_list.append(cls_options)

        self.options = self.options_cls.generate_from(*option_list)
        self.fields = fields
        self.exclude_vars = exclude_vars
        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

    def generate_fields(self):
        exclude_vars = self.exclude_vars
        fields = []

        if self.function_analyzer:
            for name, param in self.function_analyzer.parameters:
                if not self.validate_field_name(name):
                    exclude_vars.add(name)
                    continue
                if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
                    continue
                fields.append(self.schema_field_cls.generate(
                    attname=name,
                    annotation=param.annotation if param.annotation is not param.empty else None,
                    default=param.default if param.default is not param.empty else ...,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                    options=self.options
                ))

        elif inspect.isclass(self.obj):
            annotations = getattr(self.obj, '__annotations__', {})
            for key, annotation in annotations.items():
                if (
                    not self.validate_class_field_name(key)
                    or is_classvar(annotation)
                    # or is_final(annotation)
                ):
                    exclude_vars.add(key)
                    continue
                default = self.obj.__dict__.get(key, ...)
                fields.append(self.schema_field_cls.generate(
                    attname=key,
                    annotation=annotation,
                    default=default,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                    options=self.options
                ))

            for key, attr in self.obj.__dict__.items():
                if key in annotations:
                    continue
                if (
                    attr is ...
                    # if this attr is a field in bases, this means to exclude this field in current class
                    # otherwise this attr declared that this field is never take from input
                    # or isinstance(attr, property)
                    or self.is_class_internals(attr, attname=key, class_qualname=self.obj_name)
                    or not self.validate_class_field_name(key)
                ):
                    exclude_vars.add(key)
                    continue
                if key in exclude_vars:
                    continue
                fields.append(self.schema_field_cls.generate(
                    attname=key,
                    annotation=None,
                    default=attr,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                    options=self.options
                ))
        else:
            raise NotImplementedError(f'Unrecognized parser target: {self.obj}, '
                                      f'you should override this method to implement it')

        field_map = {}
        for field in fields:
            if field.name in field_map:
                raise ValueError(f'{self.obj}: field name: {repr(field.name)} conflicted at '
                                 f'{field}, {field_map[field.name]}')
            field_map[field.name] = field
        self.fields.update(field_map)

    def generate_from_init(self):
        if not inspect.isclass(self.obj):
            return

        init_func = self.obj.__dict__.get('__init__')
        if not inspect.isfunction(init_func):
            # class custom it's init
            return

        # setattr(init_func, '__options__', self.options)     # set this options

        self.init_parser = self.apply_for(init_func)
        # the INPUT parser
        # we do not merge fields or options here
        # each part does there job
        # init just parse data as it declared and take it to initialize the class
        # class T(Schema):
        #     mul: int
        #     def __init__(self, a: float, b: int):
        #         super().__init__(mul=a * b)
        # we will make init_parser the "INPUT" parser

        # addition = self.init_parser.additional_options
        # if not addition.vacuum:
        #     self.options &= addition
        #
        # self.fields.update(self.init_parser.fields)
        # self.exclude_vars.update(self.init_parser.exclude_vars)
        # self.field_alias_map.update(self.init_parser.field_alias_map)
        # self.attr_alias_map.update(self.init_parser.attr_alias_map)
        # self.case_insensitive_names.update(self.init_parser.case_insensitive_names)

    def generate_aliases(self):
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()

        for key, field in self.fields.items():
            if field.aliases:
                for alias in field.aliases:
                    if key != alias:
                        if alias in alias_map:
                            raise ValueError(f'{self.obj}: alias: [{repr(alias)}] '
                                             f'conflict with field: [{repr(alias_map[alias])}]')
                        alias_map[alias] = key
                    # if field.attname != alias:
                    attr_alias_map[alias] = field.attname
                    # include equal

            if field.case_insensitive:
                case_insensitive_names.update(*field.aliases, key)

        if case_insensitive_names:
            for key, field in self.fields.items():
                if not field.case_insensitive:
                    lower_keys = set(a.lower() for a in field.aliases).union({key.lower()})
                    inter = case_insensitive_names.intersection(lower_keys)
                    if inter:
                        raise ValueError(f'{self.obj}: case sensitive field: [{repr(key)}] '
                                         f'conflict with case insensitive field in {inter}')

        # a: str = Field(alias_from=['a1', 'a2'], case_insensitive=True)
        # b: str = Field(alias='A2', alias_from=['A1'])

        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

        for key, field in self.fields.items():
            field.generate_dependencies(alias_map)

    @property
    def __ref__(self):
        return f'{self.obj.__module__}.{self.obj.__qualname__}'

    @property
    def cls(self):
        return self.obj if inspect.isclass(self.obj) else None

    def __call__(self, data: dict, options: RuntimeOptions = None) -> dict:
        if not isinstance(data, dict):
            data = dict(data)
        self.resolve_forward_refs()
        options = options or self.options.make_runtime(self.cls, options=options)
        if options.max_properties:
            if len(data) > options.max_properties:
                options.handle_error(exc.PropertiesExceedError(
                    max_properties=options.max_properties, properties_num=len(data)))
        if options.min_properties:
            if len(data) < options.min_properties:
                options.handle_error(exc.PropertiesLackError(
                    min_properties=options.min_properties, properties_num=len(data)))
        dfs = options.data_first_search if options.data_first_search is not None else self.data_first_search
        if dfs:
            result = self.data_first_parse(data, options)
        else:
            result = self.field_first_parse(data, options)
        options.raise_error()
        # raise error if collected
        return result

    def parse_addition(self, key: str, value, options: RuntimeOptions):
        if key in self.exclude_vars:
            # excluded vars cannot be carry in addition even if allowed
            return ...
        if options.addition is False:
            options.handle_error(exc.ExceedError(item=key))
            return ...
        if not options.addition:
            # None
            return ...
        addition_type = options.addition if isinstance(options.addition, type) else self.addition_type
        if addition_type:
            value = options.transformer(value, addition_type)
        return value

    def data_first_parse(self, data: dict, options: RuntimeOptions):
        addition = {}
        result = {}
        dependencies = set()

        for key, value in data.items():
            key = str(key)
            field = self.get_field(key)

            if not field:
                add_value = self.parse_addition(key, value, options=options)
                if add_value is not ...:
                    addition[key] = add_value
                continue

            if field.no_input(value, options=options):
                continue

            if field.name in result:
                if options.ignore_alias_conflicts:
                    continue
                options.handle_error(exc.AliasConflictError(item=field.name))

            parsed = field.parse_value(value, options=options)
            if parsed is ...:
                continue

            result[field.name] = parsed

            if field.dependencies:
                dependencies.update(field.dependencies)

        if not options.ignore_required:
            # if required field is ignored. we do not need to check for required fields
            for key, field in self.fields.items():
                if key in result:
                    continue
                if field.is_required(options=options):
                    options.handle_error(exc.AbsenceError(item=field.name))
                    continue
                default = field.get_default(options)
                if default is not ...:
                    result[field.name] = default

        if not dependencies.issubset(result):
            # some dependencies not provided
            options.handle_error(exc.DependenciesAbsenceError(absence_dependencies=dependencies.difference(result)))

        if addition:
            result.update(addition)

        return result

    def field_first_parse(self, data: dict, options: RuntimeOptions):
        if self.case_insensitive_names:
            _data = {}
            for k, v in data.items():
                k = str(k)
                if k.lower() in self.case_insensitive_names:
                    _data[k.lower()] = v
                else:
                    _data[k] = v
            data = _data

        result = {}
        unprovided = object()
        used_alias = set()
        dependencies = set()
        for name, field in self.fields.items():
            value = unprovided
            if options.ignore_alias_conflicts:
                for alias in field.all_aliases:
                    if alias in data:
                        value = data[alias]
                        break
            else:
                for alias in field.all_aliases:
                    if alias in data:
                        if value is unprovided:
                            value = data[alias]
                        else:
                            options.handle_error(exc.AliasConflictError(item=field.name))
                            break

            if value is unprovided:
                if field.is_required(options=options):
                    options.handle_error(exc.AbsenceError(item=field.name))
                    continue
                default = field.get_default(options)
                # we don't catch this error for now
                # because default function is "server" function
                # if the default goes wrong, it should directly raise to the user
                if default is not ...:
                    result[field.name] = default
                continue

            used_alias.update(field.all_aliases)
            # even if field is no-input, it can still set default (by developer, no by input)
            if field.no_input(value, options=options):
                continue
            parsed = field.parse_value(value, options=options)
            if parsed is ...:
                continue
            result[field.name] = parsed
            if field.dependencies:
                dependencies.update(field.dependencies)

        if options.addition is not None:
            # that we cannot ignore addition here
            addition = {}
            for k, v in data.items():
                if k in used_alias:
                    continue
                add_value = self.parse_addition(k, v, options=options)
                if add_value is not ...:
                    addition[k] = add_value
            result.update(addition)

        if not dependencies.issubset(result):
            # some dependencies not provided
            options.handle_error(exc.DependenciesAbsenceError(absence_dependencies=dependencies.difference(result)))

        return result

    def wrap(self, func=None, options: Options = None,
             first_reserve: bool = None,
             parse_params: bool = None,
             parse_result: bool = None):

        from functools import wraps
        # from utilmeta.util.common import awaitable
        #
        # @wraps(self.obj)
        # def f(*args, **kwargs):
        #     return self.call(
        #         args, kwargs,
        #         func=func, options=options,
        #         first_reserve=first_reserve,
        #         parse_params=parse_params,
        #         parse_result=parse_result
        #     )
        #
        # @awaitable(f)
        # async def f(*args, **kwargs):
        #     return await self.call(
        #         args, kwargs,
        #         func=func, options=options,
        #         first_reserve=first_reserve,
        #         parse_params=parse_params,
        #         parse_result=parse_result
        #     )

        return func

    @property
    def function(self):
        pass
