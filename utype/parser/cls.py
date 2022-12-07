from .base import BaseParser
from .func import FunctionParser
from ..utils.compat import is_classvar, is_final
from ..utils.functional import pop
from .field import ParserField
from typing import Callable, Dict
import inspect
from ..utils.transform import register_transformer, TypeTransformer
from collections.abc import Mapping
from .options import RuntimeOptions
from functools import partial
import warnings


__all__ = ['ClassParser']


class ClassParser(BaseParser):
    function_parser_cls = FunctionParser
    fields: Dict[str, ParserField]

    def __init__(self, obj, *args, **kwargs):
        if not inspect.isclass(obj):
            raise TypeError(f"{self.__class__}: object need to be a class, got {obj}")
        super().__init__(obj, *args, **kwargs)
        self.name = getattr(self.obj, "__qualname__", self.obj.__name__)
        self.init_parser = None

    def setup(self):
        self.generate_from_bases()
        super().setup()

    def validate_class_field_name(self, name: str):
        if not self.validate_field_name(name):
            return False
        for base in self.obj.__bases__:
            if base is object:
                continue
            annotations = getattr(base, "__annotations__", None)
            if annotations:
                # maybe object
                annotation = annotations.get(name)
                if annotation:
                    if is_final(annotation):
                        raise TypeError(
                            f"field: {repr(name)} was declared as Final in {base}, "
                            f"so {self.obj} cannot annotate it again"
                        )

            attr = getattr(base, name, None)
            if self.is_class_internals(
                attr, attname=name, class_qualname=base.__qualname__
            ):
                raise TypeError(
                    f"field: {repr(name)} was declared in {base}, "
                    f"so {self.obj} cannot annotate it again"
                )
        return True

    @classmethod
    def is_class_internals(cls, attr, attname: str, class_qualname: str):
        qualname: str = getattr(attr, "__qualname__", None)
        name: str = getattr(attr, "__name__", None)
        if name and qualname:
            if attname == name and qualname.startswith(f"{class_qualname}."):
                return True
        return False

    def generate_fields(self):
        exclude_vars = self.exclude_vars
        fields = []

        annotations = self.obj.__dict__.get("__annotations__", {})
        # get annotations from __dict__
        # because if base has annotations and sub does not
        # it will directly use the annotations attr of base's

        for key, annotation in annotations.items():
            if (
                not self.validate_class_field_name(key)
                or is_classvar(annotation)
                # or is_final(annotation)
            ):
                exclude_vars.add(key)
                continue
            default = self.obj.__dict__.get(key, ...)
            fields.append(
                self.schema_field_cls.generate(
                    attname=key,
                    annotation=annotation,
                    default=default,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                    options=self.options,
                )
            )

        for key, attr in self.obj.__dict__.items():
            if key in annotations:
                continue
            if (
                attr is ...
                # if this attr is a field in bases, this means to exclude this field in current class
                # otherwise this attr declared that this field is never take from input
                # or isinstance(attr, property)
                or self.is_class_internals(
                    attr, attname=key, class_qualname=self.obj_name
                )
                or not self.validate_class_field_name(key)
            ):
                exclude_vars.add(key)
                continue
            if key in exclude_vars:
                continue
            fields.append(
                self.schema_field_cls.generate(
                    attname=key,
                    annotation=None,
                    default=attr,
                    global_vars=self.globals,
                    forward_refs=self.forward_refs,
                    options=self.options,
                )
            )

        field_map = {}
        for field in fields:
            if field.name in field_map:
                raise ValueError(
                    f"{self.obj}: field name: {repr(field.name)} conflicted at "
                    f"{field}, {field_map[field.name]}"
                )
            field_map[field.name] = field
        self.fields.update(field_map)

    def generate_from_bases(self):
        fields = {}
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()
        exclude_vars = set()
        option_list = []

        for base in reversed(self.obj.__bases__):  # according to MRO
            if not isinstance(base, type(self.obj)) or base is object:
                continue
            parser = self.apply_for(base)  # should use cache
            if not parser.options.vacuum:
                option_list.append(parser.options)

            fields.update(parser.fields)

            exclude_vars.update(parser.exclude_vars)
            alias_map.update(parser.field_alias_map)
            attr_alias_map.update(parser.attr_alias_map)
            case_insensitive_names.update(parser.case_insensitive_names)

        cls_options = self.options  # add current cls options
        if cls_options:
            option_list.append(cls_options)

        self.options = self.options_cls.generate_from(*option_list)
        self.fields = fields
        self.exclude_vars = exclude_vars
        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

    def make_setter(self, field: ParserField, post_setattr=None):
        def setter(_obj_self: object, value):
            if self.options.immutable or field.immutable:
                raise AttributeError(
                    f"{self.name}: "
                    f"Attempt to set immutable attribute: [{repr(field.attname)}]"
                )

            options = self.options.make_runtime(_obj_self.__class__, force_error=True)
            value = field.parse_value(value, options=options)
            _obj_self.__dict__[field.attname] = value
            if callable(post_setattr):
                post_setattr(_obj_self, field, value, options)

        return setter

    def make_deleter(self, field: ParserField, post_delattr=None):
        def setter(_obj_self: object):
            if self.options.immutable or field.immutable:
                raise AttributeError(
                    f"{self.name}: "
                    f"Attempt to set immutable attribute: [{repr(field.attname)}]"
                )

            options = self.options.make_runtime(_obj_self.__class__, force_error=True)
            if field.is_required(options):
                raise AttributeError(
                    f"{self.name}: Attempt to delete required schema key: {repr(field.attname)}"
                )

            if field.attname not in _obj_self.__dict__:
                raise AttributeError(
                    f"{self.name}: Attempt to delete nonexistent key: {repr(field.attname)}"
                )

            _obj_self.__dict__.pop(field.attname)

            if callable(post_delattr):
                post_delattr(_obj_self, field, options)

        return setter

    def make_getter(self, field: ParserField):
        def getter(_obj_self: object):
            if field.attname not in _obj_self.__dict__:
                raise AttributeError(
                    f"{self.name}: {repr(field.attname)} not provided in schema"
                )
            return _obj_self.__dict__[field.attname]

        return getter

    def assign_properties(self,
                          getter: Callable = None,
                          setter: Callable = None,
                          deleter: Callable = None,
                          post_setattr: Callable = None,
                          post_delattr: Callable = None):

        for key, field in self.fields.items():
            if field.property:
                continue

            prop = property(
                partial(getter, field=field) if getter else self.make_getter(field),
                partial(setter, field=field) if setter else self.make_setter(field, post_setattr=post_setattr),
                partial(deleter, field=field) if deleter else self.make_deleter(field, post_delattr=post_delattr),
            )
            # prop.__field__ = field        # cannot set attribute to @property
            setattr(self.obj, field.attname, prop)

    def get_parser(self, obj_self: object):
        if self.obj == obj_self.__class__:
            return self
        return self.resolve_parser(obj_self.__class__)

    def make_contains(self, output_only: bool = False):
        contains_func = self.obj.__dict__.get("__contains__")
        if contains_func:
            return

        def __contains__(_obj_self, item: str):
            parser = self.get_parser(_obj_self)
            field = parser.get_field(item)
            if not field:
                return False
            if field.attname not in _obj_self.__dict__:
                return False
            if not output_only:
                return True
            if field.no_output(_obj_self.__dict__[field.attname], options=parser.options):
                return False
            return True

        setattr(self.obj, "__contains__", __contains__)
        return __contains__

    def make_repr(self, ignore_str: bool = False):
        repr_func = self.obj.__dict__.get("__repr__")
        if repr_func:
            return

        def __repr__(_obj_self):
            parser = self.get_parser(_obj_self)
            items = []
            for key, val in _obj_self.__dict__.items():
                field = parser.get_field(key)
                if not field:
                    continue
                items.append(f"{field.attname}={repr(val)}")
            values = ", ".join(items)
            return f"{parser.name}({values})"

        def __str__(_obj_self):
            return _obj_self.__repr__()

        setattr(self.obj, "__repr__", __repr__)

        if not ignore_str:
            setattr(self.obj, "__str__", __str__)

        return __repr__

    def set_attributes(self,
                       values,
                       instance: object,
                       options: RuntimeOptions,
                       ):
        parser = self
        for key, field in parser.fields.items():
            if key not in values:
                continue
                # value = field.get_default(parser.options, defer=False)
                # if value is ...:
                #     if field.attname in _obj_self.__dict__:
                #         # delete attr for that unprovided value
                #         # any access to this attribute will raise AttributeError
                #         _obj_self.__dict__.pop(field.attname)
                #     continue
            elif field.no_output(values[key], options=options):
                value = values.pop(key)
                # for schema
                # _obj_self.__dict__[field.attname] = value
            else:
                value = values[key]

            if field.property:
                try:
                    field.property.fset(instance, values[key])      # call the original setter
                    # setattr(instance, field.attname, values[key])
                except Exception as e:
                    error_option = field.get_on_error(options)
                    msg = f"@property: {repr(field.attname)} assign failed with error: {e}"
                    if error_option == options.THROW:
                        raise e.__class__(msg) from e
                    else:
                        warnings.warn(msg)
                    continue
                # raise the error directly if setattr failed
            else:
                # TODO: it seems redundant for Schema, so we just use it as a fallback for now
                # and work on it later if something went wrong
                instance.__dict__[field.attname] = value

    def make_init(
        self,
        # init_super: bool = False,
        # allow_runtime: bool = False,
        # set_attributes: bool = True,
        # coerce_property: bool = False,
        no_parse: bool = False,
        post_init: Callable = None,
    ):

        init_func = getattr(self.obj, "__init__", None)

        init_parser = self.resolve_parser(init_func)
        if init_parser:
            # if init_func is already decorated like a Wrapper
            # we do not touch it either
            # case1: user use @utype.parse over the __init__ function
            # case2: base ClassParser has assigned the wrapped init with __parser__ attribute
            self.init_parser = init_parser
            return

        if not inspect.isfunction(init_func):

            def __init__(_obj_self, **kwargs):
                parser = self.get_parser(_obj_self)
                options = parser.options.make_runtime(
                    parser.obj,
                    options=pop(kwargs, "__options__")  # if allow_runtime else None,
                )

                if no_parse:
                    values = kwargs
                else:
                    values = parser(kwargs, options=options)

                parser.set_attributes(values, _obj_self, options=options)

                if post_init:
                    post_init(_obj_self, values, options)

            __init__.__parser__ = self
        else:
            self.init_parser = self.function_parser_cls.apply_for(init_func)
            __init__ = self.init_parser.wrap(parse_params=True, parse_result=False)

        setattr(self.obj, "__init__", __init__)
        # self.obj.__dict__['__init__'] = __init__
        # the INPUT parser
        # we do not merge fields or options here
        # each part does there job
        # init just parse data as it declared and take it to initialize the class
        # class T(Schema):
        #     mul: int
        #     def __init__(self, a: float, b: int):
        #         super().__init__(mul=a * b)
        # we will make init_parser the "INPUT" parser

        return __init__


@register_transformer(
    attr="__parser__",
    detector=lambda cls: isinstance(getattr(cls, "__parser__", None), ClassParser),
)
def transform(transformer: TypeTransformer, data, cls):
    parser: ClassParser = cls.__parser__
    if not isinstance(data, (dict, Mapping)):
        if transformer.no_explicit_cast:
            raise TypeError(f"invalid input type for {cls}, should be dict or Mapping")
        else:
            data = transformer(data, dict)
    if not transformer.options.vacuum:
        if parser.options.allowed_runtime_options:
            # pass the runtime options
            data.update(__options__=transformer.options)
    return cls(**data)
