import inspect
import warnings
from collections.abc import Mapping
from functools import partial
from typing import Callable, Dict, Type, TypeVar

from ..utils import exceptions as exc
from ..utils.compat import is_classvar, is_final
from ..utils.datastructures import unprovided
from ..utils.functional import pop
from ..utils.transform import TypeTransformer
from .base import BaseParser
from .field import ParserField
from .func import FunctionParser
from .options import Options, RuntimeContext

T = TypeVar("T")

__all__ = ["ClassParser", "init_dataclass"]


class ClassParser(BaseParser):
    # IGNORE_ATTR_TYPES = (staticmethod, classmethod, FunctionType, type)
    # if these type not having annotation, we will not recognize them as field
    function_parser_cls = FunctionParser
    fields: Dict[str, ParserField]

    def __init__(self, obj, *args, **kwargs):
        if not inspect.isclass(obj):
            raise TypeError(f"{self.__class__}: object need to be a class, got {obj}")
        super().__init__(obj, *args, **kwargs)
        self.init_parser = None

    @property
    def in_out_identical(self):
        for val in self.fields.values():
            if val.no_input is True and val.no_output is True:
                # ignored
                continue
            if val.no_input or val.no_output:
                return False
        return True

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
                    f"so {self.obj} cannot annotate it as a field"
                )
        return True

    @classmethod
    def is_class_internals(cls, attr, attname: str, class_qualname: str = None):
        if isinstance(attr, (staticmethod, classmethod)):
            return True
        if inspect.ismethoddescriptor(attr):
            # like method_descriptor
            return True
        qualname: str = getattr(attr, "__qualname__", None)
        name: str = getattr(attr, "__name__", None)
        if name and qualname:
            if not class_qualname:
                # loosely check
                return attname == name and "." in qualname

            if attname == name and qualname.startswith(f"{class_qualname}."):
                return True
        return False

    @property
    def globals(self) -> dict:
        dic = dict(super().globals)
        # for the self-reference model in the function (not in global vars)
        # dic.setdefault(self.obj.__name__, self.obj)
        name = self.obj.__name__
        current_obj = dic.get(name)
        if current_obj:
            if getattr(current_obj, '__qualname__', None) != getattr(self.obj, '__qualname__', None):
                from ..settings import warning_settings
                warning_settings.warn(
                    f'Parser object: {self.obj} got conflict object: {current_obj} '
                    f'with same name: {repr(name)}, it may affect the ForwardRef resolve',
                    warning_settings.globals_name_conflict
                )

        dic[name] = self.obj
        # !IMPORTANT: we need to override __name__ for current obj
        # cause in the locals, same name may be the different object, we should be careful about that
        return dic

    def generate_fields(self):
        exclude_vars = self.exclude_vars
        fields = []

        annotations = self.obj.__dict__.get("__annotations__", {})
        # get annotations from __dict__
        # because if base has annotations and sub does not
        # it will directly use the annotations attr of base's
        global_vars = self.globals

        for key, annotation in annotations.items():
            if (
                not self.validate_class_field_name(key)
                or is_classvar(annotation)
                # or is_final(annotation)
            ):
                exclude_vars.add(key)
                continue
            default = self.obj.__dict__.get(key, unprovided)
            if annotation is None:
                # a: None
                # a: Optional[None]
                # a: Union[None]
                annotation = type(None)
                # to make a difference to annotation=None

            try:
                field = self.parser_field_cls.generate(
                    attname=key,
                    annotation=annotation,
                    default=default,
                    global_vars=global_vars,
                    forward_refs=self.forward_refs,
                    options=self.options,
                    force_clear_refs=self.is_local,
                    bound=self.bound,
                    **self.kwargs
                )
            except Exception as e:
                raise exc.ConfigError(f'{self.name}: generate field [{repr(key)}] failed with error: {e}')

            fields.append(field)

        for key, attr in self.obj.__dict__.items():
            if key in annotations:
                continue
            if (
                # if this attr is a field in bases, this means to exclude this field in current class
                # otherwise this attr declared that this field is never take from input
                # or isinstance(attr, property)
                self.is_class_internals(attr, attname=key, class_qualname=self.obj_name)
                # or isinstance(attr, self.IGNORE_ATTR_TYPES)
                # check class field name at last
                # because this will check bases internals trying to find illegal override
                or not self.validate_class_field_name(key)
            ):
                # key is not consider a valid field
                # and not
                exclude_vars.add(key)
                continue
            if key in exclude_vars:
                continue
            if attr is Ellipsis and key in self.fields:
                # class base(Schema):
                #     f: int
                # class sub(base):
                #     f = ...
                # means that sub schema has dropped field [f] (not declaring the annotation)
                self.fields.pop(key)
                continue

            try:
                field = self.parser_field_cls.generate(
                    attname=key,
                    annotation=None,
                    default=attr,
                    global_vars=global_vars,
                    forward_refs=self.forward_refs,
                    options=self.options,
                    force_clear_refs=self.is_local,
                    bound=self.bound,
                    **self.kwargs
                )
            except Exception as e:
                raise exc.ConfigError(f'{self.name}: generate field [{repr(key)}] failed with error: {e}')

            fields.append(field)

        field_map = {}
        for field in fields:
            name = field.name

            if field.is_case_insensitive(self.options):
                name = name.lower()

            if name in field_map:
                raise exc.ConfigError(
                    f"{self.obj}: field name: {repr(name)} conflicted at "
                    f"{field}, {field_map[name]}",
                    obj=self.obj,
                    field=name,
                )
            field_map[name] = field

        self.fields.update(field_map)

    def generate_from_bases(self):
        fields = {}
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()
        exclude_vars = set()
        # option_list = []

        for base in reversed(self.obj.__bases__):  # according to MRO
            if not isinstance(base, type(self.obj)) or base is object:
                continue
            parser = self.apply_for(base)  # should use cache
            # if not parser.options.vacuum:
            #     option_list.append(parser.options)

            fields.update(parser.fields)

            exclude_vars.update(parser.exclude_vars)
            alias_map.update(parser.field_alias_map)
            attr_alias_map.update(parser.attr_alias_map)
            case_insensitive_names.update(parser.case_insensitive_names)

        # cls_options = self.options  # add current cls options
        # if cls_options:
        #     option_list.append(cls_options)
        #
        # self.options = self.options_cls.generate_from(*option_list)

        self.fields = fields
        self.exclude_vars = exclude_vars
        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

    def make_setter(self, field: ParserField, post_setattr=None):
        def setter(_obj_self: object, value):
            if self.options.immutable or field.immutable:
                raise exc.UpdateError(
                    f"{self.name}: "
                    f"Attempt to set immutable attribute: [{repr(field.attname)}]"
                )

            context = self.options.make_context(_obj_self.__class__, force_error=True)
            value = field.parse_value(value, context=context)
            _obj_self.__dict__[field.attname] = value
            if callable(post_setattr):
                post_setattr(_obj_self, field, value, context)

        return setter

    def make_deleter(self, field: ParserField, post_delattr=None):
        def deleter(_obj_self: object):
            if self.options.immutable or field.immutable:
                raise exc.DeleteError(
                    f"{self.name}: "
                    f"Attempt to set immutable attribute: [{repr(field.attname)}]"
                )

            context = self.options.make_context(_obj_self.__class__, force_error=True)
            if field.is_required(context.options):
                raise exc.DeleteError(
                    f"{self.name}: Attempt to delete required schema key: {repr(field.attname)}"
                )

            if field.attname not in _obj_self.__dict__:
                raise exc.DeleteError(
                    f"{self.name}: Attempt to delete nonexistent key: {repr(field.attname)}"
                )

            _obj_self.__dict__.pop(field.attname)

            if callable(post_delattr):
                post_delattr(_obj_self, field, context)

        return deleter

    def make_getter(self, field: ParserField):
        def getter(_obj_self: object):
            if field.attname not in _obj_self.__dict__:
                raise AttributeError(
                    f"{self.name}: {repr(field.attname)} not provided in schema"
                )
            return _obj_self.__dict__[field.attname]

        return getter

    def assign_properties(
        self,
        getter: Callable = None,
        setter: Callable = None,
        deleter: Callable = None,
        post_setattr: Callable = None,
        post_delattr: Callable = None,
    ):

        for key, field in self.fields.items():
            if field.property:
                continue

            if getter:
                field_getter = partial(getter, field=field)
            else:
                field_getter = self.make_getter(field)
            if setter:
                field_setter = partial(setter, field=field)
            else:
                field_setter = self.make_setter(field, post_setattr=post_setattr)
            if deleter:
                field_deleter = partial(deleter, field=field)
            else:
                field_deleter = self.make_deleter(field, post_delattr=post_delattr)

            for f in (field_getter, field_setter, field_deleter):
                f.__name__ = field.attname

            prop = property(fget=field_getter, fset=field_setter, fdel=field_deleter)
            # prop.__field__ = field        # cannot set attribute to @property
            setattr(self.obj, field.attname, prop)

    def get_parser(self, obj_self: object):
        if self.obj == obj_self.__class__:
            return self
        return self.resolve_parser(obj_self.__class__)

    def _make_method(self, func: Callable, name: str = None):
        if name:
            func.__name__ = name
        else:
            name = func.__name__

        if name in self.obj.__dict__:
            # already declared
            return False
        attr_func = getattr(self.obj, name, None)
        if hasattr(attr_func, "__parser__"):
            # already inherited
            return False
        func.__parser__ = self
        setattr(self.obj, name, func)
        return True

    def make_contains(self, output_only: bool = False):
        def __contains__(_obj_self, item: str):
            parser = self.get_parser(_obj_self)
            field = parser.get_field(item)
            if not field:
                return False
            if field.attname not in _obj_self.__dict__:
                return False
            if not output_only:
                return True
            if field.is_no_output(
                _obj_self.__dict__[field.attname], options=parser.options
            ):
                return False
            return True

        self._make_method(__contains__)

    def make_eq(self):
        def __eq__(_obj_self, other):
            if not isinstance(other, _obj_self.__class__):
                return False
            if _obj_self.__dict__ == other.__dict__:
                return True
            self_dict = dict(_obj_self.__dict__)
            pop(self_dict, "__context__")
            other_dict = dict(other.__dict__)
            pop(other_dict, "__context__")
            return self_dict == other_dict

        self._make_method(__eq__)

    def make_repr(self, ignore_str: bool = False):
        def __repr__(_obj_self):
            parser = self.get_parser(_obj_self)
            items = []
            for key, val in _obj_self.__dict__.items():
                field = parser.get_field(key)
                if not field:
                    continue
                items.append(f"{field.attname}={field.repr_value(val)}")
            values = ", ".join(items)
            return f"{parser.name}({values})"

        self._make_method(__repr__)

        if not ignore_str:

            def __str__(_obj_self):
                return _obj_self.__repr__()

            self._make_method(__str__)

    def set_attributes(
        self,
        values: dict,
        instance: object,
        options: Options,
    ):

        for key, value in list(values.items()):
            field = self.get_field(key)
            attname = key
            if field:
                if field.is_no_output(values[key], options=options):
                    values.pop(key)
                if field.property:
                    try:
                        field.property.fset(
                            instance, values[key]
                        )  # call the original setter
                        # setattr(instance, field.attname, values[key])
                    except Exception as e:
                        error_option = field.get_on_error(options)
                        msg = f"@property: {repr(field.attname)} assign failed with error: {e}"
                        if error_option == options.THROW:
                            raise e.__class__(msg) from e
                        else:
                            warnings.warn(msg)
                    continue
                attname = field.attname

            # TODO: it seems redundant for Schema, so we just use it as a fallback for now
            # and work on it later if something went wrong
            instance.__dict__[attname] = value
            # set to __dict__ no matter field (maybe addition=True)

    def make_context(self, context=None, force_error: bool = False):
        return self.options.make_context(self.obj, context=context, force_error=force_error)

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

        if not inspect.isfunction(init_func) or self.function_parser_cls.function_pass(
            init_func
        ):
            # if __init__ is declared but passed, we still make a new one

            def __init__(_obj_self, _d: dict = None, **kwargs):
                parser = self.get_parser(_obj_self)

                context = getattr(_obj_self, "__context__", None)
                if not isinstance(context, RuntimeContext):
                    context: RuntimeContext = parser.make_context()

                if isinstance(_d, dict):
                    kwargs.update(_d)

                if no_parse:
                    values = kwargs
                else:
                    values = parser(kwargs, context=context)

                parser.set_attributes(values, _obj_self, options=context.options)

                if post_init:
                    post_init(_obj_self, values, context)

            __init__.__parser__ = self
        else:
            if not no_parse:
                self.init_parser = self.function_parser_cls.apply_for(init_func)
                if self.init_parser.pos_only_keys:
                    raise exc.ConfigError(
                        f"{self.obj}: positional only keys: {self.init_parser.pos_only_keys} "
                        f"is not allowed for dataclasses __init__",
                        obj=self.obj,
                    )
                if self.init_parser.pos_var:
                    raise exc.ConfigError(
                        f"{self.obj}: positional var: {self.init_parser.pos_var} "
                        f"is not allowed for dataclasses __init__",
                        obj=self.obj,
                    )

                __init__ = self.init_parser.wrap(parse_params=True, parse_result=False)
                __init__.__parser__ = self
                # wrapped function is not as same as parse.obj
            else:
                __init__ = init_func

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

    @property
    def schema_annotations(self):
        # this is meant to be extended and override
        # if the result is not None, it will become the x-annotation of the JSON schema output
        data = dict()
        if self.options.mode:
            data.update(mode=self.options.mode)
        if self.options.case_insensitive:
            data.update(case_insensitive=self.options.case_insensitive)
        return data


def init_dataclass(
    cls: Type[T], data, options: Options = None, context: RuntimeContext = None
) -> T:
    parser: ClassParser = getattr(cls, "__parser__", None)
    if not isinstance(parser, ClassParser):
        raise exc.TypeMismatchError(f"Invalid dataclass: {cls}")

    if options:
        new_context: RuntimeContext = options.make_context(cls, context=context)
    else:
        new_context: RuntimeContext = parser.make_context(context=context)

    transformer = new_context.transformer

    try:
        if not isinstance(data, Mapping):
            # {} dict instance is an instance of Mapping too
            if transformer.no_explicit_cast:
                raise TypeError(
                    f"invalid input type for {cls}, should be dict or Mapping"
                )
            else:
                data = transformer.to_dict(data)

        if new_context.options.cast_keyword_str:
            _data = {}
            for key, val in data.items():
                if not isinstance(key, str):
                    key = transformer.to_str(key)
                _data[key] = val
            data = _data
    except Exception as e:
        raise exc.ParseError(type=cls, value=data, origin_exc=e) from e

    inst = cls.__new__(cls)
    inst.__context__ = new_context

    # if parser.init_parser:
    cls.__init__(inst, **data)

    return inst


@TypeTransformer.registry.register(
    attr="__parser__",
    detector=lambda cls: isinstance(getattr(cls, "__parser__", None), ClassParser),
)
def transform_dataclass(transformer: TypeTransformer, data, cls):
    if isinstance(data, (list, tuple)) and not transformer.options.no_explicit_cast:
        if data:
            if transformer.options.no_data_loss and len(data) > 1:
                raise TypeError
            data = data[0]
            # otherwise the data will become dict then fill the dataclass
            if type(data) == cls:
                return data

    if transformer.options.allow_subclasses:
        if isinstance(data, cls):
            # subclass
            return data

    return init_dataclass(cls, data, context=transformer.context)
