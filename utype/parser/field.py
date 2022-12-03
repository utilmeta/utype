import inspect
import warnings
from datetime import datetime, date, timedelta, time, timezone
from uuid import UUID
from decimal import Decimal
from typing import (
    Literal,
    Union,
    List,
    Optional,
    Any,
    Callable,
    Final,
    Iterable,
    Set,
    Dict,
)
from .rule import Rule, LogicalType, resolve_forward_type
from .options import Options, RuntimeOptions
from ..utils.compat import get_origin, get_args
from ..utils import exceptions as exc
from collections.abc import Mapping
from ..utils.functional import multi, copy_value
from ipaddress import IPv4Address, IPv6Address


class Field:
    DEFAULT_REQUIRED = True

    def __init__(
        self,
        *,
        alias: Union[str, Callable] = None,
        alias_from: Union[str, List[str], Callable] = None,
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
        default=...,
        default_factory: Callable = None,
        deprecated: Union[bool, str] = False,
        discriminator=None,  # discriminate the schema union by it's field
        no_input: Union[bool, str, Callable] = False,
        # can be a callable that takes the value of the field
        # give the bool of no_input / no_output
        # like no_output=lambda v: v is None  will ignore all None value when output
        no_output: Union[bool, str, Callable] = False,
        on_error: Literal["exclude", "preserve", "throw"] = None,  # follow the options
        unprovided: Any = ...,
        immutable: bool = False,
        secret: bool = False,
        dependencies: Union[list, type] = None,
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
        example=...,
        # message: str = None,  # report this message if error occur
        # --- CONSTRAINTS ---
        strict: Optional[bool] = None,
        const: Any = ...,
        enum: Iterable = None,
        gt=None,
        ge=None,
        lt=None,
        le=None,
        regex: str = None,
        length: int = None,
        max_length: int = None,
        min_length: int = None,
        # number
        max_digits: int = None,
        round: int = None,
        multiple_of: int = None,
        # array
        contains: type = None,
        max_contains: int = None,
        min_contains: int = None,
        unique_items: bool = None,
        # custom validator
        # validator: Union[Callable, List[Callable]] = None
    ):

        if mode:
            if readonly or writeonly:
                raise ValueError(
                    f"Field: mode: ({repr(mode)}) cannot set with readonly or writeonly"
                )

        if readonly and writeonly:
            raise ValueError(f"Field: readonly and writeonly cannot be both specified")
        if readonly:
            mode = "r"
        if writeonly:
            mode = "w"

        if deprecated:
            required = False

        if default is not ...:
            required = False
            if default_factory:
                raise ValueError(
                    f"Field: default: {repr(default)} and default factory cannot set both"
                )

        if default_factory:
            required = False
            if not callable(default_factory):
                raise ValueError(
                    f"Field: default_factory: {repr(default_factory)} must be a callable"
                )

        if required is None:
            required = self.DEFAULT_REQUIRED

        if isinstance(no_input, str):
            if mode:
                if no_input not in mode:
                    raise ValueError(
                        f"Field no_input: {repr(no_input)} is not in mode: {repr(mode)}"
                    )

        if isinstance(no_output, str):
            if mode:
                if no_output not in mode:
                    raise ValueError(
                        f"Field no_output: {repr(no_output)} is not in mode: {repr(mode)}"
                    )

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
        self.unprovided = unprovided
        self.dependencies = dependencies
        self.discriminator = discriminator
        self.on_error = on_error
        self.mode = mode

        self.title = title
        self.description = description
        self.example = example
        # self.message = message
        self.secret = secret  # will display "******" instead of real value in repr

        constraints = {
            k: v
            for k, v in dict(
                strict=strict,
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
                round=round,
                multiple_of=multiple_of,
                contains=contains,
                max_contains=max_contains,
                min_contains=min_contains,
                unique_items=unique_items,
            ).items()
            if v is not None
        }
        if const is not ...:
            constraints.update(const=const)

        self.strict = strict
        self.constraints = constraints
        # self.validator = validator

    @property
    def no_default(self):
        return self.default is ... and not self.default_factory

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
        if self.alias_from:
            if not multi(self.alias_from):
                alias_from = [self.alias_from]
            else:
                alias_from = self.alias_from
            if generator:
                alias_from.append(generator)
            for alias in alias_from:
                if callable(alias):
                    alias = alias(attname)
                if multi(alias):
                    aliases.update([a for a in alias if isinstance(a, str) and a])
                elif isinstance(alias, str) and alias:
                    aliases.add(alias)
        # if self.case_insensitive:
        #     aliases = set(a.lower() for a in aliases)
        return aliases

    def to_spec(self):
        # convert to schema specification
        # like https://json-schema.org/
        pass

    def __call__(self, fn_or_cls, *args, **kwargs):
        setattr(fn_or_cls, "__field__", self)
        return fn_or_cls


class SchemaField:
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
        final: bool = False,
    ):

        self.attname = attname
        self.type = input_type
        self.output_type = output_type
        self.field = field
        self.property = field_property
        self.final = final

        if self.field.case_insensitive:
            name = name.lower()
            if aliases:
                aliases = [a.lower() for a in aliases]

        self.name = name
        self.aliases = set(aliases or []).difference({self.name})
        self.all_aliases = self.aliases.union({self.name})

        # self.input_transformer = self.transformer_cls.resolver_transformer(input_type)
        self.dependencies = set()
        self.attr_dependencies = set()
        self.deprecated_to = None
        self.discriminator_map = {}
        self.validate_annotation()

    def _get_const(self):
        if inspect.isclass(self.type) and issubclass(self.type, Rule):
            return getattr(self.type, "const", ...)
        return ...

    def validate_annotation(self):
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
                    cls_parser = ClassParser.resolve_parser(arg)
                    if not cls_parser:
                        raise ValueError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but got a type: {arg} "
                            f"that not support, must be a data class "
                            f"(like subclass of DataClass / Schema or "
                            f"use @dataclass to decorate a class)"
                        )

                    field = cls_parser.get_field(self.field.discriminator)
                    if not isinstance(field, SchemaField):
                        raise ValueError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but is was not find in type: "
                            f"{arg}, you should define {self.field.discriminator}: "
                            f'Literal["some-value"] in that schema'
                        )

                    const = field._get_const()
                    if not isinstance(const, (int, str, bool)):
                        raise ValueError(
                            f"Field: {repr(self.attname)} specify a discriminator: "
                            f"{repr(self.field.discriminator)}, but in type {arg}, there is no"
                            f" common type const ({repr(const)}) set for this field, you should "
                            f"define {self.field.discriminator}: "
                            f'Literal["some-value"] in that schema'
                        )

                    if const in discriminator_map:
                        raise ValueError(
                            f"Field: {repr(self.attname)} with discriminator: "
                            f"{repr(self.field.discriminator)}, got a duplicate value:"
                            f" {repr(const)} for {arg} and {discriminator_map[const]}"
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

    def apply_fields(
        self,
        fields: Dict[str, "SchemaField"],
        excluded_vars: Set[str],
        alias_map: dict,
        attr_alias_map: dict,
    ):
        """
        take the field
        """
        if self.aliases:
            inter = self.aliases.intersection(fields)
            if inter:
                raise ValueError(
                    f"Field(name={repr(self.name)}) aliases: {inter} conflict with fields"
                )
        if self.field.dependencies:
            dependencies = []
            attr_dependencies = []
            for dep in self.field.dependencies:
                if dep in alias_map:
                    dep = alias_map[dep]
                if dep not in fields:
                    if dep in excluded_vars:
                        continue
                    raise ValueError(
                        f"Field(name={repr(self.name)}) dependency: {repr(dep)} not exists"
                    )
                if dep not in dependencies:
                    dependencies.append(dep)
                attr = attr_alias_map.get(dep, dep)
                if attr not in attr_dependencies:
                    attr_dependencies.append(attr)
            self.dependencies = set(dependencies)
            self.attr_dependencies = set(attr_dependencies)
        if self.field.deprecated_to:
            to = self.field.deprecated_to
            if to in alias_map:
                to = alias_map[to]
            if to not in fields:
                raise ValueError(
                    f"Field(name={repr(self.name)}) is deprecated,"
                    f" but prefer field : {repr(to)} not exists"
                )
            self.deprecated_to = to

    def resolve_forward_refs(self):
        self.type, r = resolve_forward_type(self.type)
        self.output_type, r = resolve_forward_type(self.output_type)

    @property
    def always_provided(self):
        return self.field.required or not self.field.no_default

    @property
    def immutable(self):
        if self.final:
            return True
        return self.field.immutable

    def is_case_insensitive(self, options: Options) -> bool:
        if self.field.case_insensitive is not None:
            return bool(self.field.case_insensitive)
        return bool(options.case_insensitive)

    def get_unprovided(self, options: Options):
        # options = options or self.options
        if options and options.unprovided_attribute is not ...:
            value = options.unprovided_attribute
        elif self.field.unprovided is not ...:
            value = self.field.unprovided
        else:
            return ...
        if callable(value):
            return value()
        return copy_value(value)

    def get_default(self, options: RuntimeOptions):
        # options = options or self.options
        if options.no_default:
            return ...
        if options.force_default is not ...:
            default = options.force_default
        elif self.field.default is not ...:
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
            return ...
        return copy_value(default)

    def get_on_error(self, options: RuntimeOptions):
        if self.field.on_error:
            return self.field.on_error
        return options.invalid_values

    def get_example(self):
        if self.field.example is not ...:
            return self.field.example

    def is_required(self, options: RuntimeOptions):
        if options.ignore_required:
            return False
        if isinstance(self.field.required, bool):
            return self.field.required
        if not options.mode:
            return False
        return self.field.required in options.mode

    def no_input(self, value, options: RuntimeOptions):
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

    def no_output(self, value, options: RuntimeOptions):
        no_output = (
            self.field.no_output(value)
            if callable(self.field.no_output)
            else self.field.no_output
        )

        if not options.mode:
            # no mode
            return no_output if isinstance(no_output, bool) else False

        if isinstance(no_output, (str, list, set, tuple)):
            return options.mode in no_output

        if self.field.mode:
            return options.mode not in self.field.mode

        return bool(no_output)

    def check_function(self):
        if not self.field.required and self.field.no_default:
            pass
        if self.field.no_output:
            warnings.warn(
                f"Field.no_output has no meanings in function params, please consider move it"
            )
            pass

    def parse_value(self, value, options: RuntimeOptions):
        if self.field.deprecated:
            to = (
                f", use {repr(self.deprecated_to)} instead"
                if self.deprecated_to
                else ""
            )
            options.collect_waring(
                f"{repr(self.name)} is deprecated{to}", category=DeprecationWarning
            )

        type = self.type
        if self.discriminator_map:
            if isinstance(value, dict):
                discriminator = value.get(self.field.discriminator)
                if discriminator in self.discriminator_map:
                    type = self.discriminator_map[discriminator]
                    # directly assign type instead parse it in a Logical context

        trans = options.transformer
        try:
            return trans(value, type)
        except Exception as e:
            error = exc.ParseError(
                item=self.name, type=self.type, value=value, field=self, origin_exc=e
            )
            error_option = self.get_on_error(options)
            if error_option == options.EXCLUDE:
                if self.is_required(options):
                    # required field cannot be excluded
                    options.handle_error(error)
                else:
                    options.collect_waring(error.formatted_message)
            elif error_option == options.PRESERVE:
                options.collect_waring(error.formatted_message)
                return value
            else:
                options.handle_error(error)
            return ...

    @classmethod
    def generate(
        cls,
        attname: str,
        annotation: Any = None,
        default=...,
        global_vars=None,
        forward_refs=None,
        options: Options = None,
    ):
        prop = None
        output_type = None
        no_input = False
        no_output = False
        dependencies = None
        field = default

        if isinstance(default, property):
            prop = default
            default = None
            if prop.fset:
                _, (k, param) = inspect.signature(prop.fset).parameters.items()
                param: inspect.Parameter
                if param.annotation != param.empty:
                    annotation = param.annotation
                if param.default != param.empty:
                    # @prop.setter
                    # def prop(self, value: str = Field(...)):
                    #     pass
                    # we will forbid such behaviour
                    # as it could involve no-consistent behaviour between setter and getter
                    # the only proper usage of Field over property is
                    # @Field(...)
                    # @property
                    # def prop(self):
                    #     pass

                    default = param.default
                    if isinstance(default, Field):
                        raise ValueError(
                            f"property: {repr(attname)} defines Field i"
                            f"n setter param default value, which is not appropriate, "
                            f"you should use @{default} over the @property"
                        )

                dependencies = inspect.getclosurevars(prop.fget).unbound
                # use the unbound properties as default dependencies of property
                # you can use @Field(dependencies=[...]) to specify yourself
            else:
                no_input = True

            if prop.fget:
                return_annotation = getattr(prop.fget, "__annotations__", {}).get(
                    "return"
                )
                output_type = cls.rule_cls.parse_annotation(
                    annotation=return_annotation,
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=attname,
                )
            else:
                no_output = True

            field = getattr(prop, "__field__", None)

        if not isinstance(field, Field):
            field = cls.field_cls(
                default=default,
                no_input=no_input,
                no_output=no_output,
                dependencies=dependencies,
            )

        final = False
        _origin = get_origin(annotation)
        if _origin == Final:
            # this type should take care in this level
            # because it does not affect validation / transformation
            # and rather a field behaviour
            final = True
            args = get_args(annotation)
            if args:
                annotation = args[0]

        input_type = cls.rule_cls.parse_annotation(
            annotation=annotation,
            constraints=field.constraints,
            global_vars=global_vars,
            forward_refs=forward_refs,
            forward_key=attname,
        )
        return cls(
            attname=attname,
            name=field.get_alias(
                attname, generator=options.alias_generator if options else None
            ),
            aliases=field.get_alias_from(
                attname, generator=options.alias_from_generator if options else None
            ),
            input_type=input_type,
            output_type=output_type or input_type,
            field=field,
            field_property=prop,
            # options=options,
            final=final,
        )
