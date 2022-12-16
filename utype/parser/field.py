import inspect
import warnings
from datetime import datetime, date, timedelta, time, timezone
from uuid import UUID
from decimal import Decimal
from typing import Literal, Union, List, Any, Callable, Iterable, Set, Dict, Optional
from .rule import Rule, ConstraintMode, Lax, LogicalType, resolve_forward_type
from .options import Options, RuntimeContext
from ..utils.compat import get_args, is_final
from ..utils.datastructures import unprovided
from ..utils import exceptions as exc
from collections.abc import Mapping
from ..utils.functional import multi, copy_value, get_name
from ipaddress import IPv4Address, IPv6Address

represent = repr


class Field:
    def __init__(
        self,
        *,
        alias: Union[str, Callable] = None,
        alias_from: Union[str, List[str], Callable, List[Callable]] = None,
        # can also be a generator
        case_insensitive: bool = None,
        # alias_for: str = None,     we may cancel alias for and replace it with alias
        required: Union[bool, str] = None,
        # required='rw'
        readonly: bool = None,
        # api def: cannot be part of the request body
        # this is the mark for upper-layer to apply
        # the schema-level readonly control is the "immutable" param
        writeonly: bool = None,
        mode: str = None,
        # api def: cannot be part of the response body
        # null: bool = False,
        # use null in type like Optional[int] / int | None
        default: Any = unprovided,
        default_factory: Callable = None,
        defer_default: bool = False,
        deprecated: Union[bool, str] = False,
        discriminator=None,  # discriminate the schema union by it's field
        no_input: Union[bool, str, Callable] = False,
        # can be a callable that takes the value of the field
        # give the bool of no_input / no_output
        # like no_output=lambda v: v is None  will ignore all None value when output
        no_output: Union[bool, str, Callable] = False,
        on_error: Literal["exclude", "preserve", "throw"] = None,  # follow the options
        # unprovided: Any = ...,
        immutable: bool = False,
        # secret: bool = None,    # None means depend on the Options.secret_names
        repr: Union[bool, str, Callable] = None,  # noqa
        dependencies: Union[list, str, property] = None,
        # (backup: internal, disallow, unacceptable)
        # unacceptable: we do not accept this field as an input,
        # but this field will be in the result if present (like default, or attribute set)
        # this is useful to auto_user_field or last_modified_field which we do not
        # want to expose the field to the user in the api docs
        # options: Options = None,  # for the annotated schema
        # property: _property = None,  # noqa
        # schema=None,
        # info: dict = None,
        # --- ANNOTATES ---
        title: str = None,
        description: str = None,
        example: Any = unprovided,
        # message: str = None,  # report this message if error occur
        # --- CONSTRAINTS ---
        const: Any = unprovided,
        enum: Iterable = None,
        gt=None,
        ge=None,
        lt=None,
        le=None,
        regex: str = None,
        length: Union[int, ConstraintMode] = None,
        max_length: Union[int, ConstraintMode] = None,
        min_length: int = None,
        # number
        max_digits: Union[int, ConstraintMode] = None,
        decimal_places: Union[int, ConstraintMode] = None,
        round: int = None,
        multiple_of: Union[int, ConstraintMode] = None,
        # array
        contains: type = None,
        max_contains: int = None,
        min_contains: int = None,
        unique_items: Union[bool, ConstraintMode] = None,
    ):
        if mode:
            if readonly or writeonly:
                raise exc.ConfigError(
                    f"Field: mode: ({represent(mode)}) cannot set with readonly or writeonly",
                    params={"mode": mode},
                )

        if readonly and writeonly:
            raise exc.ConfigError(
                f"Field: readonly and writeonly cannot be both specified",
                params={"readonly": readonly, "writeonly": writeonly},
            )

        if readonly:
            mode = "r"
        if writeonly:
            mode = "w"

        if deprecated:
            required = False

        if not unprovided(default):
            required = False
            if default_factory:
                raise exc.ConfigError(
                    f"Field: default: {represent(default)} and default factory cannot set both",
                    params={"default": default},
                )

        if default_factory:
            required = False
            if not callable(default_factory):
                raise exc.ConfigError(
                    f"Field: default_factory: {represent(default_factory)} must be a callable",
                    params={"default_factory": default_factory},
                )

        if defer_default:
            if unprovided(default) and not default_factory:
                raise exc.ConfigError(
                    f"Field: specify defer_default=True without any default",
                    params={
                        "defer_default": defer_default,
                        "default": default,
                        "default_factory": default_factory,
                    },
                )

        if required is None:
            required = True

        if required:
            if on_error == "exclude":
                raise exc.ConfigError(
                    f'Field: required field does not support on_error="exclude"',
                    params={"required": required, "on_error": on_error},
                )

        if isinstance(no_input, str):
            if mode:
                if no_input not in mode:
                    raise exc.ConfigError(
                        f"Field no_input: {represent(no_input)} is not in mode: {represent(mode)}",
                        params={"no_input": no_input, "mode": mode},
                    )

        if isinstance(no_output, str):
            if mode:
                if no_output not in mode:
                    raise exc.ConfigError(
                        f"Field no_output: {represent(no_output)} is not in mode: {represent(mode)}",
                        params={"no_output": no_output, "mode": mode},
                    )

        if round:
            if decimal_places and decimal_places not in (round, Lax(round)):
                raise exc.ConfigError(
                    f"Field round: {round} is a shortcut for decimal_places=Lax({round}), "
                    f"but you specified a different decimal_places: {represent(decimal_places)}",
                    params={"round": round, "decimal_places": decimal_places},
                )

            decimal_places = Lax(round)

        self.alias = alias if isinstance(alias, str) else None
        self.alias_generator = alias if callable(alias) else None
        self.alias_from = alias_from
        # self.alias_from =
        self.case_insensitive = case_insensitive
        self.deprecated = bool(deprecated)
        self.deprecated_to = deprecated if isinstance(deprecated, str) else None

        self.no_input = no_input
        self.no_output = no_output
        self.immutable = immutable
        self.required = required

        self.default = default
        self.default_factory = default_factory
        self.defer_default = defer_default

        # self.unprovided = unprovided

        deps = []
        if dependencies:
            if not multi(dependencies):
                dependencies = [dependencies]

            for dep in dependencies:
                dep = get_name(dep)
                if not isinstance(dep, str):
                    raise exc.ConfigError(
                        f"Invalid dependency: {represent(dep)}, must be str or property"
                    )
                deps.append(dep)

        if discriminator:
            discriminator = get_name(discriminator)
            if not isinstance(discriminator, str):
                raise exc.ConfigError(
                    f"Field.discriminator must be a str, got {represent(discriminator)}",
                    params={"discriminator": discriminator},
                )

        self.dependencies = deps
        self.discriminator = discriminator
        self.on_error = on_error
        self.mode = mode

        self.title = title
        self.description = description
        self.example = example
        # self.message = message
        # self.secret = secret  # will display "******" instead of real value in repr

        if isinstance(repr, bool):
            if repr:
                repr = represent  # noqa
            else:
                repr = lambda v: unprovided  # noqa
        elif isinstance(repr, str):

            def repr(v, _=repr):  # noqa
                return _

        self.repr: Optional[Callable] = repr

        constraints = {
            k: v
            for k, v in dict(
                enum=enum,
                gt=gt,
                ge=ge,
                lt=lt,
                le=le,
                min_length=min_length,
                max_length=max_length,
                length=length,
                regex=regex,
                max_digits=max_digits,
                decimal_places=decimal_places,
                multiple_of=multiple_of,
                contains=contains,
                max_contains=max_contains,
                min_contains=min_contains,
                unique_items=unique_items,
            ).items()
            if v is not None
        }
        if not unprovided(const):
            constraints.update(const=const)

        self.constraints = constraints

    @property
    def no_default(self):
        return unprovided(self.default) and not self.default_factory

    def get_alias(self, attname: str, generator=None):
        alias = attname
        if self.alias:
            alias = self.alias
        else:
            generator = self.alias_generator or generator
            if generator:
                _alias = generator(attname)
                if isinstance(_alias, str) and _alias:
                    alias = _alias
        return alias

    def get_alias_from(self, attname: str, generator=None) -> Set[str]:
        aliases = {attname}
        alias_from = []
        if self.alias_from:
            if not multi(self.alias_from):
                alias_from = [self.alias_from]
            else:
                alias_from = self.alias_from
            # field alias_from will override generator
        elif generator:
            if multi(generator):
                alias_from.extend(generator)
            else:
                alias_from.append(generator)

        for alias in alias_from:
            if callable(alias):
                alias = alias(attname)
            if multi(alias):
                aliases.update([a for a in alias if isinstance(a, str) and a])
            elif isinstance(alias, str) and alias:
                aliases.add(alias)

        return aliases

    # def to_spec(self):
    #     # convert to schema specification
    #     # like https://json-schema.org/
    #     pass

    def __call__(self, fn_or_cls, *args, **kwargs):
        setattr(fn_or_cls, "__field__", self)
        return fn_or_cls


class Param(Field):
    def __init__(
        self,
        default=unprovided,
        *,
        default_factory: Callable = None,
        alias: Union[str, Callable] = None,
        alias_from: Union[str, List[str], Callable, List[Callable]] = None,
        case_insensitive: bool = None,
        mode: str = None,
        deprecated: Union[bool, str] = False,
        discriminator=None,  # discriminate the schema union by it's field
        no_input: Union[bool, str, Callable] = False,
        on_error: Literal["exclude", "preserve", "throw"] = None,  # follow the options
        dependencies: Union[list, str, property] = None,
        # --- ANNOTATES ---
        title: str = None,
        description: str = None,
        example=unprovided,
        # --- CONSTRAINTS ---
        const=unprovided,
        enum: Iterable = None,
        gt=None,
        ge=None,
        lt=None,
        le=None,
        regex: str = None,
        length: Union[int, ConstraintMode] = None,
        max_length: Union[int, ConstraintMode] = None,
        min_length: int = None,
        # number
        max_digits: Union[int, ConstraintMode] = None,
        decimal_places: Union[int, ConstraintMode] = None,
        round: int = None,
        multiple_of: Union[int, ConstraintMode] = None,
        # array
        contains: type = None,
        max_contains: int = None,
        min_contains: int = None,
        unique_items: Union[bool, ConstraintMode] = None,
    ):
        kwargs = dict(locals())
        kwargs.pop("self")
        kwargs.pop("__class__")
        super().__init__(**kwargs)


class ParserField:
    TYPE_PRIMITIVE = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        list: "array",
        tuple: "array",
        set: "array",
        frozenset: "array",
        dict: "object",
        bytes: "string",
        Decimal: "number",
        date: "string",
        time: "string",
        datetime: "string",
        UUID: "string",
        Mapping: "object",
    }

    TYPE_FORMAT = {
        int: "integer",
        float: "float",
        tuple: "tuple",
        set: "set",
        frozenset: "set",
        bytes: "binary",
        Decimal: "decimal",
        date: "date",
        time: "time",
        datetime: "date-time",
        UUID: "uuid",
        timedelta: "duration",
        timezone: "timezone",
        IPv4Address: "ipv4",
        IPv6Address: "ipv6",
    }

    SECRET_EXEMPT_TYPES = (bool,)
    SECRET_REPR = "*" * 6

    field_cls = Field
    rule_cls = Rule
    # transformer_cls = TypeTransformer

    def __init__(
        self,
        name: str,
        # the actual schema field name
        # alias / attname
        input_type: type,
        # all the transformers and validators are infer from type
        field: Field,
        attname: str = None,
        aliases: Set[str] = None,
        field_property: property = None,
        output_type: type = None,
        output_field: Field = None,
        dependencies: Set[str] = None,
        final: bool = False,
        positional_only: bool = False,
    ):

        self.attname = attname
        self.type = input_type
        self.output_type = output_type
        self.field = field
        self.output_field = output_field
        self.property = field_property
        self.final = final
        self.name = name
        self.aliases = set(aliases or []).difference({self.name})
        self.all_aliases = self.aliases.union({self.name})

        # self.input_transformer = self.transformer_cls.resolver_transformer(input_type)
        self.dependencies = dependencies
        self.attr_dependencies = set()
        self.dependants = set()

        # self.secret = field.secret
        # self.secret_repr = field.secret if isinstance(field.secret, str) else self.SECRET_REPR
        self.repr_func = self.field.repr
        self.input_transformer = None
        self.output_transformer = None
        self.deprecated_to = None
        self.const = unprovided
        self.discriminator_map = {}
        self.positional_only = positional_only

    @property
    def input_origins(self) -> List[type]:
        if isinstance(self.type, LogicalType):
            return self.type.resolve_origins()
        elif isinstance(self.type, type):
            return [self.type]
        return []  # not set or ForwardRef

    @property
    def output_origins(self) -> List[type]:
        if isinstance(self.output_type, LogicalType):
            return self.output_type.resolve_origins()
        elif isinstance(self.output_type, type):
            return [self.output_type]
        return []  # not set or ForwardRef

    def repr_value(self, value):
        if self.repr_func:
            rp = self.repr_func(value)
            if unprovided(rp):
                return rp
            return str(rp)
        return represent(value)

    def setup(self, options: Options):
        if self.is_case_insensitive(options):
            # do not lower name
            # self.name = self.name.lower()
            self.aliases = {a.lower() for a in self.aliases}
            self.all_aliases = {a.lower() for a in self.all_aliases}

        if self.repr_func is None:
            if options.secret_names:
                is_secret = False
                for name in options.secret_names:
                    if name in self.all_aliases:
                        is_secret = True
                        break
                if is_secret:
                    # some types like bool is not some type to hide even if name in the secret names
                    origins = self.input_origins
                    if any([ori in self.SECRET_EXEMPT_TYPES for ori in origins]):
                        is_secret = False

                if is_secret:
                    self.repr_func = lambda v: self.SECRET_REPR

        if isinstance(self.type, type):
            if issubclass(self.type, Rule):
                self.const = getattr(self.type, "const", unprovided)
            else:
                trans = Rule.transformer_cls.resolver_transformer(self.type)
                if not trans:
                    if options.unresolved_types == options.THROW:
                        warnings.warn(
                            f"Field(name={repr(self.name)}) got unresolved type: {self.type}, "
                            f'and Options.unresolved_types == "throw", which will raise error'
                            f" in the runtime if the input value type does not match"
                        )
                else:
                    self.input_transformer = trans

        if isinstance(self.output_type, type):
            if issubclass(self.output_type, Rule):
                pass
            else:
                trans = Rule.transformer_cls.resolver_transformer(self.output_type)
                if not trans:
                    if options.unresolved_types == options.THROW:
                        warnings.warn(
                            f"Field(name={repr(self.name)}) got unresolved output type: {self.output_type}, "
                            f'and Options.unresolved_types == "throw", which will raise error'
                            f" in the runtime if the input value type does not match"
                        )
                else:
                    self.output_transformer = trans

        if self.field.discriminator:
            discriminator_map = {}
            comb = None
            if isinstance(self.type, LogicalType):
                comb = self.type.resolve_combined_origin()

            if not comb:
                raise TypeError(
                    f"Field: {repr(self.attname)} specify a discriminator: "
                    f"{repr(self.field.discriminator)}, but got a common type: {self.type} "
                    f"which does not support discriminator"
                )

            if comb.combinator == "|" or comb.combinator == "^":
                from .cls import ClassParser

                for arg in comb.args:
                    if arg is type(None):
                        # we accept None
                        continue

                    cls_parser = ClassParser.resolve_parser(arg)
                    if not cls_parser:
                        raise exc.ConfigError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but got a type: {arg} "
                            f"that not support, must be a data class "
                            f"(like subclass of DataClass / Schema or "
                            f"use @dataclass to decorate a class)",
                            field=self.name,
                        )

                    field = cls_parser.get_field(self.field.discriminator)
                    if not isinstance(field, ParserField):
                        raise exc.ConfigError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but is was not find in type: "
                            f"{arg}, you should define {self.field.discriminator}: "
                            f'Literal["some-value"] in that schema',
                            field=self.name,
                        )

                    const = field.const
                    if not isinstance(const, (int, str, bool)):
                        raise exc.ConfigError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but in type {arg}, there is no"
                            f" common type const ({repr(const)}) set for this field, you should "
                            f"define {self.field.discriminator}: "
                            f'Literal["some-value"] in that schema',
                            field=self.name,
                        )

                    if const in discriminator_map:
                        raise exc.ConfigError(
                            f"Field: {repr(self.attname)} with discriminator: "
                            f"{repr(self.field.discriminator)}, got a duplicate value:"
                            f" {repr(const)} for {arg} and {discriminator_map[const]}",
                            field=self.name,
                        )

                    discriminator_map[const] = arg
                self.discriminator_map = discriminator_map
            else:
                raise TypeError(
                    f"Field: {repr(self.attname)} specify a discriminator: "
                    f"{repr(self.field.discriminator)}, but got a logical type: {self.type} "
                    f"with combinator: {repr(comb.combinator)} which does not support discriminator, "
                    f'only "^"(OneOf) or "|"(AnyOf) support'
                )

    def add_dependant(self, name: str):
        if name in self.dependants:
            return
        self.dependants.add(name)

    def apply_fields(
        self,
        fields: Dict[str, "ParserField"],
        # excluded_vars: Set[str],
        alias_map: dict,
        # attr_alias_map: dict,
    ):
        """
        take the field
        """
        if self.aliases:
            inter = self.aliases.intersection(fields)
            if inter:
                raise exc.ConfigError(
                    f"Field(name={repr(self.name)}) aliases: {inter} conflict with fields"
                )

        if self.dependencies:

            dependencies = []
            attr_dependencies = []
            for dep in self.dependencies:
                if dep in alias_map:
                    dep = alias_map[dep]
                if dep not in fields:
                    # continue
                    # if dependencies is generated from unbound, it is considered inaccurate
                    if not self.property:
                        raise exc.ConfigError(
                            f"Field(name={repr(self.name)}) dependency: {repr(dep)} not exists"
                        )
                    continue

                field = fields[dep]
                if self.property:
                    # if no getter function
                    # dependant will not affect
                    field.add_dependant(self.name)
                if dep not in dependencies:
                    dependencies.append(dep)
                if field.attname not in attr_dependencies:
                    attr_dependencies.append(field.attname)
            self.dependencies = set(dependencies)
            self.attr_dependencies = set(attr_dependencies)

        if self.field.deprecated_to:
            to = self.field.deprecated_to
            if to in alias_map:
                to = alias_map[to]
            if to not in fields:
                raise exc.ConfigError(
                    f"Field(name={repr(self.name)}) is deprecated,"
                    f" but prefer field : {repr(to)} not exists"
                )
            self.deprecated_to = to

    def resolve_forward_refs(self):
        if self.type:
            self.type, r = resolve_forward_type(self.type)
        if self.output_type:
            self.output_type, r = resolve_forward_type(self.output_type)

    @property
    def always_provided(self):
        # required is mode str or callable does not means
        return self.field.required is True or not self.field.no_default

    @property
    def immutable(self):
        if self.final:
            return True
        return self.field.immutable

    def is_case_insensitive(self, options: Options) -> bool:
        if self.field.case_insensitive is not None:
            return bool(self.field.case_insensitive)
        return bool(options.case_insensitive)

    # def get_unprovided(self, options: Options):
    #     # options = options or self.options
    #     if options and options.unprovided_attribute is not ...:
    #         value = options.unprovided_attribute
    #     elif self.field.unprovided is not ...:
    #         value = self.field.unprovided
    #     else:
    #         return ...
    #     if callable(value):
    #         return value()
    #     return copy_value(value)

    def get_default(self, options: Options, defer: bool = False):
        # options = options or self.options
        if options.no_default:
            return unprovided

        if not defer:
            if self.field.defer_default or options.defer_default:
                return unprovided
        else:
            if not self.field.defer_default and not options.defer_default:
                return unprovided

        if not unprovided(options.force_default):
            default = options.force_default
        elif not unprovided(self.field.default):
            default = self.field.default
        elif self.field.default_factory:
            try:
                default = self.field.default_factory()
            except Exception as e:
                # we should directly raise the error since it is a "ServerError" instead of a parse error
                # we just want to add some info here to help debug
                raise e.__class__(
                    f"Field(name={repr(self.name)}) generate default failed with error: {e}"
                ) from e
        else:
            return unprovided
        return copy_value(default)

    def get_on_error(self, options: Options):
        if self.field.on_error:
            return self.field.on_error
        return options.invalid_values

    def get_example(self):
        if not unprovided(self.field.example):
            return self.field.example

    def is_required(self, options: Options):
        if options.ignore_required or not self.field.required:
            return False
        if self.always_no_input(options):
            return False
        if self.field.required is True:
            return True
        if not options.mode:
            return False
        return options.mode in self.field.required

    def no_input(self, value, options: Options):
        if self.final:
            if not self.field.no_default:
                return True

        no_input = (
            self.field.no_input(value)
            if callable(self.field.no_input)
            else self.field.no_input
        )

        if not options.mode:
            # no mode
            return no_input if isinstance(no_input, bool) else False

        if isinstance(no_input, (str, list, set, tuple)):
            return options.mode in no_input

        if self.field.mode:
            return options.mode not in self.field.mode

        return bool(no_input)

    def always_no_input(self, options: Options):
        # calculate before get the value
        if self.final:
            if not self.field.no_default:
                return True
        field = self.field
        if field.no_input is True:
            return True
        if not options.mode:
            return False
        if callable(field.no_input):
            return False
        if isinstance(field.no_input, (str, list, set, tuple)):
            return options.mode in field.no_input
        if field.mode:
            return options.mode not in field.mode
        return False

    def always_no_output(self, options: Options):
        # calculate before get the value
        field = self.output_field or self.field
        if field.no_output is True:
            return True
        if not options.mode:
            return False
        if callable(field.no_output):
            return False
        if isinstance(field.no_output, (str, list, set, tuple)):
            return options.mode in field.no_output
        if field.mode:
            return options.mode not in field.mode
        return False

    def no_output(self, value, options: Options):
        field = self.output_field or self.field
        # prefer the config in output field rather than input field
        no_output = (
            field.no_output(value)
            if callable(self.field.no_output)
            else field.no_output
        )

        if not options.mode:
            # no mode
            return no_output if isinstance(no_output, bool) else False

        if isinstance(no_output, (str, list, set, tuple)):
            return options.mode in no_output

        if field.mode:
            return options.mode not in field.mode

        return bool(no_output)

    def check_function(self, func):
        if not self.always_provided:
            raise exc.ConfigError(
                f"{func}: Field(name={repr(self.name)}) in function with required=False "
                f"must specify a default or default_factory",
                obj=func,
                field=self.name,
                params={"required": self.field.required, "default": self.field.default},
            )

        if self.field.defer_default:
            # use defer_default=True will cause no default provided
            raise exc.ConfigError(
                f"{func}: Field(name={repr(self.name)}).defer_default has no meanings in function params,"
                f" please consider move it",
                obj=func,
                field=self.name,
                params={"defer_default": self.field.defer_default},
            )

        if self.field.no_default:
            if self.field.no_input:
                raise exc.ConfigError(
                    f"{func}: Field(name={repr(self.name)}) with no_input ({self.field.no_input}) "
                    f"must specify a default/default_factory value",
                    obj=func,
                    field=self.name,
                    params={
                        "no_input": self.field.no_input,
                        "default": self.field.default,
                    },
                )

            if self.field.mode:
                raise exc.ConfigError(
                    f"{func}: Field(name={repr(self.name)}) with mode ({self.field.mode}) "
                    f"must specify a default/default_factory value",
                    obj=func,
                    field=self.name,
                    params={"mode": self.field.mode, "default": self.field.default},
                )

        if self.positional_only:
            if self.field.alias:
                warnings.warn(
                    f"{func}: Field(name={repr(self.name)}).alias ({repr(self.field.alias)}) "
                    f"has no meanings in positional only params,"
                    f" please consider move it"
                )
            if self.field.alias_from:
                warnings.warn(
                    f"{func}: Field(name={repr(self.name)}).alias_from ({repr(self.field.alias_from)}) "
                    f"has no meanings in positional only params,"
                    f" please consider move it"
                )
            if self.field.case_insensitive:
                warnings.warn(
                    f"{func}: Field(name={repr(self.name)}).case_insensitive "
                    f"has no meanings in positional only params,"
                    f" please consider move it"
                )

        if self.field.no_output:
            warnings.warn(
                f"{func}: Field(name={repr(self.name)}).no_output has no meanings in function params,"
                f" please consider move it"
            )

        if self.field.immutable:
            warnings.warn(
                f"{func}: Field(name={repr(self.name)}).immutable has no meanings in function params, "
                f"please consider move it"
            )

        if self.field.repr:
            warnings.warn(
                f"{func}: Field(name={repr(self.name)}).repr has no meanings in function params,"
                f" please consider move it"
            )

    # 1. deal with parse: use context
    def parse_output_value(self, value, context: RuntimeContext):
        type = self.output_type
        if not type:
            return value
        trans = context.transformer
        try:
            return trans(value, type)  # noqa
        except Exception as e:
            error = exc.ParseError(
                item=self.name,
                type=self.output_type,
                value=value,
                field=self,
                origin_exc=e,
            )
            # todo: apply and distinct input field / output field
            error_option = (
                self.output_field.on_error if self.output_field else None
            ) or context.options.invalid_values
            if error_option == context.options.EXCLUDE:
                context.collect_waring(error.formatted_message)
            elif error_option == context.options.PRESERVE:
                context.collect_waring(error.formatted_message)
                return value
            else:
                context.handle_error(error)
            return unprovided

    def parse_value(self, value, context: RuntimeContext):
        if self.field.deprecated:
            to = (
                f", use {repr(self.deprecated_to)} instead"
                if self.deprecated_to
                else ""
            )
            context.collect_waring(
                f"{repr(self.name)} is deprecated{to}", category=DeprecationWarning
            )

        type = self.type
        # trans = context.transformer

        if self.discriminator_map and value is not None:
            if not isinstance(value, Mapping):
                try:
                    value = context.transformer.to_dict(value)
                except Exception as e:
                    context.handle_error(
                        exc.ParseError(
                            item=self.name,
                            type=dict,
                            value=value,
                            field=self,
                            origin_exc=e,
                        )
                    )
                    return unprovided

            discriminator = value.get(self.field.discriminator)
            if discriminator in self.discriminator_map:
                type = self.discriminator_map[discriminator]
                # directly assign type instead parse it in a Logical context
            else:
                context.handle_error(
                    exc.DiscriminatorMismatchError(
                        discriminator=self.field.discriminator,
                        discriminator_value=discriminator,
                        field=self,
                        value=value,
                        item=self.name,
                        type=self.type,
                    )
                )
                return unprovided

        if not type:
            # type is None, not type(None), means the exact same as Any / Rule
            return value

        with context.enter(self.name) as new_context:
            try:
                return new_context.transformer(value, type)  # noqa
            except Exception as e:
                error = exc.ParseError(
                    item=self.name,
                    type=self.type,
                    value=value,
                    field=self,
                    origin_exc=e,
                )
                error_option = self.get_on_error(context.options)
                if error_option == context.options.EXCLUDE:
                    if self.is_required(context.options):
                        # required field cannot be excluded
                        context.handle_error(error)
                    else:
                        context.collect_waring(error.formatted_message)
                    # return default if provided
                    # return unprovided if no default is set
                    return self.get_default(options=context.options, defer=False)
                elif error_option == context.options.PRESERVE:
                    context.collect_waring(error.formatted_message)
                    return value
                else:
                    context.handle_error(error)
                return unprovided

    @classmethod
    def generate(
        cls,
        attname: str,
        annotation: Any,
        default: Any,
        options: Options,
        positional_only: bool = False,
        global_vars=None,
        forward_refs=None,
    ):
        prop = None
        output_type = None
        no_input = False
        no_output = False
        required = True
        dependencies = None
        field = default
        output_field = None

        if isinstance(default, property):
            prop = default
            default = unprovided
            if prop.fset:
                _, (k, param) = inspect.signature(prop.fset).parameters.items()
                param: inspect.Parameter
                if param.annotation != param.empty:
                    annotation = param.annotation

                field = getattr(prop.fset, "__field__", None)

                if param.default != param.empty:
                    # @property
                    # @Field(...)
                    # def prop(self):
                    #     pass
                    #
                    # @prop.setter
                    # def prop(self, value: str = Field(...)):
                    #     pass

                    # default = param.default
                    if isinstance(param.default, Field):
                        field = param.default

                        # some invalid configures
                        if field.alias:
                            raise exc.ConfigError(
                                field=attname, params={"alias": field.alias}
                            )
                        if field.no_output:
                            raise exc.ConfigError(
                                field=attname, params={"no_output": field.no_output}
                            )
                        if field.dependencies:
                            raise exc.ConfigError(
                                field=attname,
                                params={"dependencies": field.dependencies},
                            )

                    else:
                        default = param.default
                        # raise ValueError(
                        #     f"property: {repr(attname)} defines Field i"
                        #     f"n setter param default value, which is not appropriate, "
                        #     f"you should use @{default} over the @property"
                        # )
            else:
                no_input = True
                required = False

            if prop.fget:
                return_annotation = getattr(prop.fget, "__annotations__", {}).get(
                    "return"
                )

                dependencies = inspect.getclosurevars(prop.fget).unbound
                # use the unbound properties as default dependencies of property
                # you can use @Field(dependencies=[...]) to specify yourself

                output_field = getattr(prop.fget, "__field__", None)
                if isinstance(output_field, Field):

                    if output_field.dependencies:
                        dependencies = output_field.dependencies

                    # some invalid configures
                    if output_field.no_input:
                        raise exc.ConfigError(
                            field=attname, params={"no_input": field.no_input}
                        )
                    if output_field.alias_from:
                        raise exc.ConfigError(
                            field=attname, params={"alias_from": field.alias_from}
                        )
                    if not output_field.no_default:
                        raise exc.ConfigError(
                            field=attname, params={"default": field.default}
                        )

                else:
                    output_field = None

                output_type = cls.rule_cls.parse_annotation(
                    annotation=return_annotation,
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=attname,
                    constraints=output_field.constraints if output_field else None,
                )

            else:
                no_output = True

        final = is_final(annotation)
        if final:
            # turn to Any by default, not bare Final, which will not be recognized as a valid annotation
            # _origin = get_origin(annotation)
            # if _origin == Final:
            # this type should take care in this level
            # because it does not affect validation / transformation
            # and rather a field behaviour
            args = get_args(annotation)
            if args:
                annotation = args[0]
            else:
                annotation = Any

        if not isinstance(field, Field):
            field = cls.field_cls(
                default=default,
                no_input=no_input,
                no_output=no_output,
                required=required,
                immutable=final,
            )

        if not dependencies and field.dependencies:
            dependencies = field.dependencies

        input_type = cls.rule_cls.parse_annotation(
            annotation=annotation,
            constraints=field.constraints,
            global_vars=global_vars,
            forward_refs=forward_refs,
            forward_key=attname,
        )

        parser_field = cls(
            attname=attname,
            name=(output_field or field).get_alias(
                attname, generator=options.alias_generator
            ),
            aliases=field.get_alias_from(
                attname, generator=options.alias_from_generator
            ),
            input_type=input_type,
            output_type=output_type,
            field=field,
            output_field=output_field,
            field_property=prop,
            dependencies=dependencies,
            # options=options,
            final=final,
            positional_only=positional_only,
        )
        parser_field.setup(options=options)
        return parser_field
