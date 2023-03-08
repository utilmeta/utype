import inspect
import sys
from typing import Callable, Dict, List, Optional, Set, Tuple, Type, Union

from ..utils import exceptions as exc
from ..utils.compat import *
from ..utils.datastructures import cached_property, unprovided
from .field import ParserField
from .options import Options, RuntimeContext
from .rule import resolve_forward_type

LOCALS_NAME = "<locals>"
__parsers__ = {}


class BaseParser:
    options_cls = Options
    parser_field_cls = ParserField

    # DEFAULT_EXCLUDE_VARS = {"__options__", "__class__"}

    @classmethod
    def resolve_parser(cls, obj):
        global __parsers__
        if obj in __parsers__:
            return __parsers__[obj]
        parser = getattr(obj, "__parser__", None)
        if isinstance(parser, cls):
            return parser
        return None

    @classmethod
    def apply_for(cls, obj, no_cache: bool = False, options=None, **kwargs) -> "BaseParser":
        if isinstance(obj, cls):
            return obj
        parser = getattr(obj, "__dict__", {}).get("__parser__")
        # do not use getattr(obj, '__parser__')
        # since it may get to the base class
        if isinstance(parser, cls):
            return parser
        global __parsers__
        # key = (cls, obj)
        key = obj
        if not options:
            options = getattr(obj, '__options__', None)
        if not no_cache and key in __parsers__:
            cached: "BaseParser" = __parsers__[key]
            # if options is not identical, make a new one
            if not options or options == cached.options:
                return cached
        inst = cls(obj, options=options, **kwargs)      # noqa
        if not no_cache:
            __parsers__[key] = inst
        return inst

    def __init__(self, obj, options: Options = None):
        self.obj = obj
        self.init_kwargs = {"options": options}
        self.options: Options = self.options_cls.generate_from(options)

        self.forward_refs: Dict[
            str, Tuple[ForwardRef, dict]
        ] = {}  # store unresolved ref
        self.fields: Dict[str, ParserField] = {}
        self.exclude_vars: Set[str] = set()
        # these data structures are designed to speed up the parsing
        self.case_insensitive_names: Set[str] = set()
        self.field_alias_map: Dict[str, str] = {}
        self.attr_alias_map: Dict[str, str] = {}
        self.error_hooks: Dict[Type[Exception], Callable] = {}
        self.data_first_search = None
        self.addition_type = None
        self.name = self.get_name()
        self.setup()

    def make_context(self, context=None, force_error: bool = False):
        return self.options.make_context(context=context, force_error=force_error)

    @property
    def kwargs(self):
        return {}

    def get_name(self) -> str:
        name = getattr(
            self.obj, "__qualname__", getattr(self.obj, "__name__", None)
        ) or str(self.obj)
        while LOCALS_NAME in name:
            lhs, rhs = name.split(LOCALS_NAME)
            name = str(rhs).strip(".")
        return name

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
            global_vars=self.globals,
        )

    @cached_property
    def property_fields(self):
        fields = {}
        for key, field in self.fields.items():
            if field.property:
                fields[key] = field
        return fields

    def validate_fields(self):
        pass
        # if self.options.allowed_runtime_options:
        #     if "__options__" in self.fields:
        #         raise ValueError(
        #             f"{self.obj} did not specify no_runtime_options=True, "
        #             f'so name "__options__" is used to passing runtime options, which is conflicted'
        #             f' with field {self.fields["__options__"]}'
        #         )

    def _get_field_from(self, fields: dict, key: str) -> Optional[ParserField]:
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

    def get_field(self, key: str) -> Optional[ParserField]:
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
        if (
            self.case_insensitive_names
            or self.field_alias_map
            or self.options.ignore_required
            or self.options.addition
        ):
            # in those cases data first is faster than field first
            self.data_first_search = True
        else:
            self.data_first_search = False

    @property
    def rule_cls(self):
        return self.parser_field_cls.rule_cls

    @property
    def module_name(self):
        return self.obj.__module__

    @property
    def obj_name(self):
        return getattr(self.obj, "__qualname__", None) or getattr(self.obj, "__name__")

    @property
    def globals(self):
        if hasattr(self.obj, "__globals__"):
            # like a function
            return self.obj.__globals__
        return sys.modules[self.module_name].__dict__

    def __getitem__(self, item):
        return self.fields[item]

    def __contains__(self, item):
        return item in self.fields

    def resolve_forward_refs(self, local_vars=None, ignore_errors: bool = True):
        if not self.forward_refs:
            return False
        resolved = False
        for name in list(self.forward_refs):
            ref, constraints = self.forward_refs[name]
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
                            constraints=constraints,
                            global_vars=self.globals,
                            forward_refs=self.forward_refs,
                            forward_key=name,
                        )
                    else:
                        # maybe just ref to some const
                        # a: PositiveInt | '"some value"'
                        # we will not go through the ForwardRef
                        # as the typing star
                        ref.__forward_value__ = self.rule_cls.annotate(
                            type_=type(value),
                            constraints={"const": ref.__forward_value__},
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
        return not name.startswith("_")

    def generate_fields(self):
        raise NotImplementedError

    def generate_aliases(self):
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()

        for key, field in self.fields.items():
            if field.aliases:  # not contains the name
                for alias in field.aliases:
                    if key != alias:
                        if alias in alias_map:
                            raise exc.ConfigError(
                                f"{self.obj}: alias: [{repr(alias)}] "
                                f"conflict with field: [{repr(alias_map[alias])}]",
                                obj=self.obj,
                                field=field.name,
                            )
                        alias_map[alias] = key
                    # if field.attname != alias:
                    attr_alias_map[alias] = field.attname
                    # include equal

            if field.is_case_insensitive(self.options):
                case_insensitive_names.update(field.all_aliases)

        # for key, field in self.fields.items():
        #     if key in alias_map:
        #         raise ValueError(f'{self.obj}: alias: [{repr(key)}] conflict with field: [{repr(field)}]')

        if case_insensitive_names:
            for key, field in self.fields.items():
                if not field.is_case_insensitive(self.options):
                    lower_keys = set(a.lower() for a in field.aliases).union(
                        {key.lower()}
                    )
                    inter = case_insensitive_names.intersection(lower_keys)
                    if inter:
                        raise exc.ConfigError(
                            f"{self.obj}: case sensitive field: [{repr(key)}] "
                            f"conflict with case insensitive field in {inter}",
                            obj=self.obj,
                            field=field.name,
                        )

        # a: str = Field(alias_from=['a1', 'a2'], case_insensitive=True)
        # b: str = Field(alias='A2', alias_from=['A1'])

        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

        for key, field in self.fields.items():
            field.apply_fields(
                self.fields,
                # excluded_vars=self.exclude_vars,
                alias_map=alias_map,
            )

    @property
    def __ref__(self):
        return f"{self.obj.__module__}.{self.obj.__qualname__}"

    @property
    def cls(self):
        return self.obj if inspect.isclass(self.obj) else None

    def __call__(self, data: dict, context: RuntimeContext = None) -> dict:
        if not isinstance(data, dict):
            data = dict(data)
        self.resolve_forward_refs(ignore_errors=False)
        if not context:
            context = self.options.make_context(self.cls)
        result = self.parse_data(data, context=context)
        context.raise_error()
        # raise error if collected
        return result

    def parse_data(
        self,
        data: dict,
        context: RuntimeContext,
        as_attname: bool = None,
        excluded_keys: List[str] = None,
    ):
        options = context.options
        if options.max_params:
            if len(data) > options.max_params:
                context.handle_error(
                    exc.ParamsExceedError(
                        max_params=options.max_params, params_num=len(data)
                    )
                )
        if options.min_params:
            if len(data) < options.min_params:
                context.handle_error(
                    exc.ParamsLackError(
                        min_params=options.min_params, params_num=len(data)
                    )
                )
        dfs = (
            options.data_first_search
            if options.data_first_search is not None
            else self.data_first_search
        )
        if dfs:
            result = self.data_first_parse(
                data, context, excluded_keys=excluded_keys, as_attname=as_attname
            )
        else:
            result = self.field_first_parse(
                data, context, excluded_keys=excluded_keys, as_attname=as_attname
            )
        return result

    def parse_addition(self, key: str, value, context: RuntimeContext):
        if key in self.exclude_vars:
            # excluded vars cannot be carry in addition even if allowed
            return unprovided
        if context.options.addition is False:
            context.handle_error(exc.ExceedError(item=key, value=value))
            return unprovided
        if not context.options.addition:
            # None
            return unprovided
        # addition_type = options.addition if isinstance(options.addition, type) else self.addition_type
        addition_type = self.addition_type
        # we should just ignore the runtime addition type
        if not addition_type:
            return value

        options = context.options
        with context.enter(key) as new_context:
            try:
                value = new_context.transformer(value, addition_type)
            except Exception as e:
                error = exc.ParseError(
                    item=key, value=value, type=addition_type, origin_exc=e
                )
                if options.invalid_values == options.EXCLUDE:
                    context.collect_waring(error.formatted_message)
                    return unprovided
                elif options.invalid_values == options.PRESERVE:
                    context.collect_waring(error.formatted_message)
                else:
                    context.handle_error(error)
        return value

    def data_first_parse(
        self,
        data: dict,
        context: RuntimeContext,
        as_attname: bool = False,
        excluded_keys: List[str] = None,
    ):
        addition = {}
        result = {}
        dependencies = set()
        unprovided_fields = set()
        options = context.options

        for key, value in data.items():
            key = str(key)
            field = self.get_field(key)
            if not field:
                add_value = self.parse_addition(key, value, context=context)
                if not unprovided(add_value):
                    addition[key] = add_value
                continue

            name = field.attname if as_attname else field.name

            if field.is_no_input(value, options=options):
                # no input field does not take input from __init__
                # but can still apply default
                default = field.get_default(options, defer=False)
                if not unprovided(default):
                    result[name] = default
                continue

            if (name in result) or (excluded_keys and name in excluded_keys):
                if options.ignore_alias_conflicts:
                    continue
                context.handle_error(exc.AliasConflictError(item=name, value=value))
                continue

            parsed = field.parse_value(value, context=context)
            if unprovided(parsed):
                continue

            result[name] = parsed

            if field.dependencies:
                dependencies.update(
                    field.attr_dependencies if as_attname else field.dependencies
                )

        if not options.ignore_required:
            # if required field is ignored. we do not need to check for required fields
            for key, field in self.fields.items():
                name = field.attname if as_attname else field.name
                if name in result:
                    continue
                if excluded_keys and name in excluded_keys:
                    continue
                unprovided_fields.add(name)
                if field.is_required(options=options):
                    context.handle_error(exc.AbsenceError(item=name))
                    continue
                default = field.get_default(options, defer=False)
                if not unprovided(default):
                    result[name] = default

        if dependencies:
            dependant = set(result)
            if excluded_keys:
                dependant.update(excluded_keys)

            diff = dependencies.difference(dependant)
            lack = dependencies.intersection(unprovided_fields)
            lack.update(diff)
            if lack:
                # some dependencies not provided
                context.handle_error(
                    exc.DependenciesAbsenceError(absence_dependencies=lack)
                )

        # check dependencies before addition

        if addition:
            result.update(addition)

        return result

    def field_first_parse(
        self,
        data: dict,
        context: RuntimeContext,
        as_attname: bool = False,
        excluded_keys: List[str] = None,
    ):
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
        used_alias = set()
        dependencies = set()
        unprovided_fields = set()
        options = context.options

        for key, field in self.fields.items():
            value = unprovided
            name = field.attname if as_attname else field.name

            if excluded_keys and name in excluded_keys:
                continue

            if options.ignore_alias_conflicts:
                for alias in field.all_aliases:
                    if alias in data:
                        value = data[alias]
                        break
            else:
                for alias in field.all_aliases:
                    if alias in data:
                        if unprovided(value):
                            value = data[alias]
                        else:
                            context.handle_error(exc.AliasConflictError(item=name))
                            break

            if unprovided(value):
                unprovided_fields.add(name)
                if field.is_required(options=options):
                    context.handle_error(exc.AbsenceError(item=name))
                    continue
                default = field.get_default(options, defer=False)
                # we don't catch this error for now
                # because default function is "server" function
                # if the default goes wrong, it should directly raise to the user
                if not unprovided(default):
                    result[name] = default
                continue

            used_alias.update(field.all_aliases)
            # even if field is no-input, it can still set default (by developer, no by input)
            if field.is_no_input(value, options=options):
                # no input field does not take input from __init__
                # but can still apply default
                default = field.get_default(options, defer=False)
                if not unprovided(default):
                    result[name] = default
                continue

            parsed = field.parse_value(value, context=context)
            if unprovided(parsed):
                continue

            result[name] = parsed
            if field.dependencies:
                dependencies.update(
                    field.attr_dependencies if as_attname else field.dependencies
                )

        if dependencies:
            dependant = set(result)
            if excluded_keys:
                dependant.update(excluded_keys)

            diff = dependencies.difference(dependant)
            lack = dependencies.intersection(unprovided_fields)
            lack.update(diff)
            if lack:
                # some dependencies not provided
                context.handle_error(
                    exc.DependenciesAbsenceError(absence_dependencies=lack)
                )

        # check dependencies before addition

        if options.addition is not None:
            # that we cannot ignore addition here
            addition = {}
            for k, v in data.items():
                if k in used_alias:
                    continue
                add_value = self.parse_addition(k, v, context=context)
                if not unprovided(add_value):
                    addition[k] = add_value
            result.update(addition)

        return result
