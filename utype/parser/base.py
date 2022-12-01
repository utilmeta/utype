from typing import Optional, Callable, Type, Dict, Set, List, Union
from .field import SchemaField

from .options import Options, RuntimeOptions
from ..utils.compat import *
from ..utils import exceptions as exc
from .rule import resolve_forward_type
from functools import cached_property
import inspect
import sys

__parsers__ = {}


class BaseParser:
    options_cls = Options
    schema_field_cls = SchemaField

    DEFAULT_EXCLUDE_VARS = {
        '__options__',
        '__class__'
    }

    @classmethod
    def apply_for(cls, obj, no_cache: bool = False) -> 'BaseParser':
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

    def __init__(self, obj, options: Options = None):
        self.obj = obj
        self.options: Options = options or self.options_cls()
        self.forward_refs: Dict[str, ForwardRef] = {}  # store unresolved ref
        self.fields: Dict[str, SchemaField] = {}
        self.exclude_vars: Set[str] = set(self.DEFAULT_EXCLUDE_VARS)
        # these data structures are designed to speed up the parsing
        self.case_insensitive_names: Set[str] = set()
        self.field_alias_map: Dict[str, str] = {}
        self.attr_alias_map: Dict[str, str] = {}
        self.error_hooks: Dict[Type[Exception], Callable] = {}
        self.data_first_search = None
        self.addition_type = None

        self.setup()

    def setup(self):
        self.generate_fields()
        self.generate_aliases()
        self.validate_fields()
        self.parse_addition_type()
        self.assign_search_strategy()

    def parse_addition_type(self):
        if self.options.addition and not isinstance(self.options.addition, bool):
            # we treat it as a type
            # including typing.GenericAlias / ForwardRef
            self.addition_type = self.parse_annotation(annotation=self.options.addition)

    def parse_annotation(self, annotation):
        return self.rule_cls.parse_annotation(
            annotation=annotation,
            forward_refs=self.forward_refs,
            global_vars=self.globals
        )

    @cached_property
    def property_fields(self):
        fields = {}
        for key, field in self.fields.items():
            if field.property:
                fields[key] = field
        return fields

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

    def get_attrs(self, data: Union[list, tuple, set, dict, str]):
        if isinstance(data, dict):
            return {self.get_attrs(key): val for key, val in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return type(data)([self.get_attrs(v) for v in data])
        return self.attr_alias_map.get(data, data)

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

    @property
    def rule_cls(self):
        return self.schema_field_cls.rule_cls

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
            return False
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
            self.addition_type, r = resolve_forward_type(self.addition_type)
        return resolved

    @classmethod
    def validate_field_name(cls, name: str):
        if name.startswith('_'):
            return False
        return True

    def generate_fields(self):
        raise NotImplementedError

    def generate_aliases(self):
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()

        for key, field in self.fields.items():
            if field.aliases:   # not contains the name
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

        # for key, field in self.fields.items():
        #     if key in alias_map:
        #         raise ValueError(f'{self.obj}: alias: [{repr(key)}] conflict with field: [{repr(field)}]')

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
            field.apply_fields(
                self.fields,
                alias_map=alias_map,
                attr_alias_map=attr_alias_map
            )

    @property
    def __ref__(self):
        return f'{self.obj.__module__}.{self.obj.__qualname__}'

    @property
    def cls(self):
        return self.obj if inspect.isclass(self.obj) else None

    def __call__(self, data: dict, options: RuntimeOptions = None) -> dict:
        if not isinstance(data, dict):
            data = dict(data)
        self.resolve_forward_refs(ignore_errors=False)
        options = options or self.options.make_runtime(self.cls, options=options)
        result = self.parse_data(data, options=options)
        options.raise_error()
        # raise error if collected
        return result

    def parse_data(self, data: dict, options: RuntimeOptions,
                   as_attname: bool = None,
                   excluded_keys: List[str] = None):
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
            result = self.data_first_parse(
                data, options,
                excluded_keys=excluded_keys,
                as_attname=as_attname
            )
        else:
            result = self.field_first_parse(
                data, options,
                excluded_keys=excluded_keys,
                as_attname=as_attname
            )
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
        # addition_type = options.addition if isinstance(options.addition, type) else self.addition_type
        addition_type = self.addition_type
        # we should just ignore the runtime addition type
        if addition_type:
            try:
                value = options.transformer(value, addition_type)
            except Exception as e:
                options.handle_error(exc.ParseError(
                    item=key,
                    value=value,
                    type=addition_type,
                    origin_exc=e
                ))
        return value

    def data_first_parse(self, data: dict, options: RuntimeOptions,
                         as_attname: bool = False,
                         excluded_keys: List[str] = None):
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

            name = field.attname if as_attname else field.name

            if (name in result) or \
                    (excluded_keys and name in excluded_keys):
                if options.ignore_alias_conflicts:
                    continue
                options.handle_error(exc.AliasConflictError(item=name, value=value))
                continue

            parsed = field.parse_value(value, options=options)
            if parsed is ...:
                continue

            result[name] = parsed

            if field.dependencies:
                dependencies.update(field.attr_dependencies if as_attname else field.dependencies)

        if not options.ignore_required:
            # if required field is ignored. we do not need to check for required fields
            for key, field in self.fields.items():
                name = field.attname if as_attname else field.name
                if name in result:
                    continue
                if excluded_keys and name in excluded_keys:
                    continue
                if field.is_required(options=options):
                    options.handle_error(exc.AbsenceError(item=name))
                    continue
                default = field.get_default(options)
                if default is not ...:
                    result[name] = default

        if dependencies:
            dependant = set(result)
            if excluded_keys:
                dependant.update(excluded_keys)

            diff = dependencies.difference(dependant)
            if diff:
                # some dependencies not provided
                options.handle_error(exc.DependenciesAbsenceError(absence_dependencies=diff))

        # check dependencies before addition

        if addition:
            result.update(addition)

        return result

    def field_first_parse(self, data: dict, options: RuntimeOptions,
                          as_attname: bool = False,
                          excluded_keys: List[str] = None):
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
        for key, field in self.fields.items():
            if excluded_keys and key in excluded_keys:
                continue
            value = unprovided
            name = field.attname if as_attname else field.name

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
                            options.handle_error(exc.AliasConflictError(item=name))
                            break

            if value is unprovided:
                if field.is_required(options=options):
                    options.handle_error(exc.AbsenceError(item=name))
                    continue
                default = field.get_default(options)
                # we don't catch this error for now
                # because default function is "server" function
                # if the default goes wrong, it should directly raise to the user
                if default is not ...:
                    result[name] = default
                continue

            used_alias.update(field.all_aliases)
            # even if field is no-input, it can still set default (by developer, no by input)
            if field.no_input(value, options=options):
                continue
            parsed = field.parse_value(value, options=options)
            if parsed is ...:
                continue

            result[name] = parsed
            if field.dependencies:
                dependencies.update(field.attr_dependencies if as_attname else field.dependencies)

        if dependencies:
            dependant = set(result)
            if excluded_keys:
                dependant.update(excluded_keys)

            diff = dependencies.difference(dependant)
            if diff:
                # some dependencies not provided
                options.handle_error(exc.DependenciesAbsenceError(absence_dependencies=diff))

        # check dependencies before addition

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

        return result
