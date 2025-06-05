import warnings
from functools import partial
from typing import Callable, List, TypeVar, Union

from .parser.cls import ClassParser, init_dataclass
from .parser.field import ParserField
from .parser.options import Options, RuntimeContext
from .parser.rule import LogicalType
from .utils import exceptions as exc
from .utils.datastructures import unprovided

T = TypeVar("T")
OTHER = TypeVar("OTHER")


class LogicalMeta(type):
    __logical_type__ = LogicalType

    @property
    def __ref__(cls):
        try:
            name = cls.__qualname__
        except AttributeError:
            name = cls.__name__
        if "." in name:
            name = "".join(
                [
                    part.capitalize() if part.islower() else part
                    for part in name.split(".")
                ]
            )
        return f"{cls.__module__}.{name}"

    def __and__(cls: T, other: T) -> Union[T, OTHER]:
        if isinstance(other, LogicalType):
            return other.__rand__(cls)  # noqa
        return cls.__logical_type__.combine("&", cls, other)

    def __rand__(cls: T, other: OTHER) -> Union[OTHER, T]:
        return cls.__logical_type__.combine("&", other, cls)

    def __or__(cls: T, other: OTHER) -> Union[T, OTHER]:
        if getattr(other, "__origin__", None) == Union:
            return cls.__logical_type__.combine("|", cls, *other.__args__)
        if isinstance(other, LogicalType):
            return other.__ror__(cls)  # noqa
        return cls.__logical_type__.combine("|", cls, other)

    def __ror__(cls: T, other: OTHER) -> Union[OTHER, T]:
        if getattr(other, "__origin__", None) == Union:
            return cls.__logical_type__.combine("|", *other.__args__, cls)
        return cls.__logical_type__.combine("|", other, cls)

    def __xor__(cls: T, other: OTHER) -> Union[T, OTHER]:
        if isinstance(other, LogicalType):
            return other.__rxor__(cls)  # noqa
        return cls.__logical_type__.combine("^", cls, other)

    def __rxor__(cls: T, other: OTHER) -> Union[OTHER, T]:
        return cls.__logical_type__.combine("^", other, cls)

    def __invert__(cls):
        return cls.__logical_type__.combine("~", cls)


class DataClass(metaclass=LogicalMeta):
    __parser_cls__ = ClassParser
    __parser__: ClassParser
    __options__: Options

    def __init__(self, *args, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        # options = getattr(cls, "__options__", None)
        cls.__parser__ = parser = cls.__parser_cls__.apply_for(cls)
        cls.__options__ = cls.__parser__.options

        parser.make_init(
            # init_super=False,
            # allow_runtime=True,
            # set_attributes=True,
            # coerce_property=False,
            post_init=cls.__post_init__,
        )
        parser.make_eq()
        parser.make_repr(ignore_str=False)
        parser.make_contains(output_only=True)
        parser.assign_properties(
            post_setattr=cls.__post_setattr__, post_delattr=cls.__post_delattr__
        )

    @property
    def __name__(self):
        return self.__parser__.name

    def __class_getitem__(cls, item):
        raise NotImplementedError

    def __validate__(self):
        pass

    def __post_init__(self, values, context: RuntimeContext):  # noqa
        self.__validate__()

    def __post_setattr__(self, field: ParserField, value, context: RuntimeContext):
        pass

    def __post_delattr__(self, field: ParserField, context: RuntimeContext):
        pass

    # def __copy__(self):
    #     obj = self.__class__.__new__(self.__class__)
    #     obj.__dict__ = self.__dict__
    #     obj.__runtime_options__ = self.__runtime_options__
    #     return obj

    @classmethod
    def __from__(cls, data, options: Options = None):
        return init_dataclass(cls, data, options=options)

    def __export__(
        self,
        includes: Union[str, List[str]] = None,
        excludes: Union[str, List[str]] = None,
        as_attname: bool = False,
        no_output: Callable = None,  # control by value
        mode: str = None,
    ) -> dict:
        pass


class Schema(dict, metaclass=LogicalMeta):
    __parser_cls__ = ClassParser
    __parser__: ClassParser
    __options__: Options
    # __mode__: str = None

    def __init_subclass__(cls, **kwargs):
        # options = getattr(cls, "__options__", None)
        cls.__parser__ = parser = cls.__parser_cls__.apply_for(cls)
        cls.__options__ = cls.__parser__.options

        parser.make_init(
            # init_super=True,
            # allow_runtime=True,
            # set_attributes=False,   # n
            # coerce_property=True,
            post_init=cls.__post_init__,
        )
        parser.assign_properties(
            getter=cls.__field_getter__,
            setter=cls.__field_setter__,
            deleter=cls.__field_deleter__,
        )

        for key, field in parser.property_fields.items():
            # if field.property.fset:
            #   if field.always_no_output(cls.__options__.make_runtime(cls)) and not field.dependants:
            #       continue
            getter = partial(
                cls.__field_getter__, field=field, getter=field.property.fget
            )
            setter = (
                partial(cls.__field_setter__, field=field, setter=field.property.fset)
                if field.property.fset
                else None
            )
            deleter = (
                partial(cls.__field_deleter__, field=field, deleter=field.property.fdel)
                if field.property.fdel
                else None
            )

            for f in (getter, setter, deleter):
                if f:
                    f.__name__ = field.attname

            hooked_property = property(fget=getter, fset=setter, fdel=deleter)
            setattr(cls, field.attname, hooked_property)

    def __class_getitem__(cls, item):
        # if isinstance(item, Options):
        #     class _cls(cls):
        #         __options__ = item
        #     return _cls
        raise NotImplementedError

    def __validate__(self):
        pass

    def __str__(self):
        items = []
        for key, val in self.items():
            field = self.__parser__.get_field(key)
            name = field.attname if field else key
            if field:
                repr_val = field.repr_value(val)
                if unprovided(repr_val):
                    # do not print
                    continue
            else:
                repr_val = repr(val)
            items.append(f"{name}={repr_val}")
        values = ", ".join(items)
        return f"{self.__name__}({values})"

    @property
    def __name__(self):
        return self.__parser__.name

    def __repr__(self):
        return self.__str__()

    @classmethod
    def __from__(cls, data, options=None):
        return init_dataclass(cls, data, options=options)

    # coerce_properties need to separate from set_attributes and execute by order
    # because the dependencies that the property need may not be set during one-time loop
    # (which is guarantee by the field orders, and consider not reliable)
    def __coerce_property__(self, field: ParserField, context: RuntimeContext):
        if field.always_no_output(context.options):
            return

        if field.dependencies and not field.dependencies.issubset(self):
            # maybe some of the dependencies is no_output=True, but still accessible through attribute
            # check if any of those dependencies is not in __dict__, and directly return if found one
            for dep in field.dependencies:
                dep_field = self.__parser__.get_field(dep)
                if not dep_field or dep_field.attname not in self.__dict__:
                    return

        try:
            attr = field.property.fget(self)  # get from the original getter
        except Exception as e:
            error_option = field.output_field.on_error if field.output_field else None
            msg = f"{self.__name__}: @property: {repr(field.attname)} calculate failed with error: {e}"
            if error_option == context.options.THROW:
                raise e.__class__(msg) from e
            else:
                warnings.warn(msg)
            return

        value = field.parse_output_value(  # parse @property result also
            attr, context=context
        )

        if unprovided(value):
            return

        if not field.is_no_output(value, options=context.options):
            super().__setitem__(field.name, value)
            # values[key] = value
            # do not apply cache here
            # when updating it will get nasty
            # _obj_self.__dict__[field.attname] = value
        else:
            if field.name in self:
                super().__delitem__(field.name)
            if field.attname in self.__dict__:
                self.__dict__.pop(field.attname)

        return value

    def __post_init__(self, values, context: RuntimeContext):
        super().__init__(values)
        self.__options__ = context.options  # set options
        for key, field in self.__parser__.property_fields.items():
            self.__coerce_property__(field, context=context)
        self.__validate__()
        context.raise_error()  # raise error if there is any

    def __contains__(self, item: str):
        field = self.__parser__.get_field(item)
        if not field:
            return super().__contains__(item)
        return super().__contains__(field.name)

    def __field_getter__(self, field: ParserField, getter: Callable = None):
        if field.name in self:
            # include output properties which is contained in the data
            return self[field.name]
        if field.attname in self.__dict__:
            # maybe a no_output field
            return self.__dict__[field.attname]

        if callable(getter):
            context = self.__parser__.make_context(force_error=True)
            value = field.parse_output_value(getter(self), context=context)
            if unprovided(value):
                raise AttributeError(
                    f"{self.__name__}: @property: {repr(field.attname)} failed to calculate"
                )
            return value

        deferred_default = field.get_default(
            options=self.__options__, defer=True
        )  # get deferred default
        if not unprovided(deferred_default):
            return deferred_default
        raise AttributeError(
            f"{self.__name__}: {repr(field.attname)} not provided in schema instance"
        )

    def __getitem__(self, item):
        # stay the same behaviour as the __contains__
        field = self.__parser__.get_field(item)
        if field:
            return super().__getitem__(field.name)
        return super().__getitem__(item)

    def __field_setter__(self, value, field: ParserField, setter: Callable = None):
        if self.__options__.immutable or field.immutable:
            raise exc.UpdateError(
                f"{self.__name__}: "
                f"Attempt to set immutable attribute: [{repr(field.attname)}]"
            )

        context = self.__parser__.make_context(force_error=True)
        value = field.parse_value(value, context=context)

        if field.property:
            if callable(setter):
                # @property.fset
                setter(self, value)

            # force calculate property
            self.__coerce_property__(field, context=context)
        else:
            if field.is_no_output(value, options=self.__options__):
                self.__dict__[field.attname] = value
                # no output
                if field.name in self:
                    super().__delitem__(field.name)
            else:
                super().__setitem__(field.name, value)

        if field.dependants:
            # need to update the dependant properties
            for dep in field.dependants:
                dep_field = self.__parser__.get_field(dep)
                if dep_field and dep_field.property:
                    self.__coerce_property__(dep_field, context=context)

    def __setitem__(self, alias: str, value):
        if self.__options__.immutable:
            raise exc.UpdateError(
                f"{self.__class__}: "
                f"Attempt to set item: [{repr(alias)}] in immutable schema"
            )

        field = self.__parser__.get_field(alias)
        if not field:
            if alias in self.__parser__.exclude_vars:
                raise exc.UpdateError(
                    f"{self.__class__}: Attempt to set excluded attribute: {repr(alias)}"
                )
            context = self.__parser__.make_context(force_error=True)
            addition = self.__parser__.parse_addition(alias, value, context=context)
            if unprovided(addition):
                # ignore addition
                return
            return super().__setitem__(alias, value)

        return self.__field_setter__(value, field=field)

    def __field_deleter__(self, field: ParserField, deleter: Callable = None):
        if self.__options__.immutable or field.immutable:
            raise exc.DeleteError(
                f"{self.__name__}: "
                f"Attempt to delete immutable attribute: [{repr(field.attname)}]"
            )

        if callable(deleter):
            deleter(self)

            if field.name in self:
                super().__delitem__(field.name)
        else:
            if field.is_required(self.__options__):
                raise exc.DeleteError(
                    f"{self.__name__}: Attempt to delete required schema key: {repr(field.attname)}"
                )
            if field.name not in self:
                if self.__options__.ignore_delete_nonexistent:
                    return
                raise exc.DeleteError(
                    f"{self.__name__}: Attempt to delete nonexistent attribute: {repr(field.attname)}"
                )
            super().__delitem__(field.name)

        if field.name in self.__dict__:
            self.__dict__.pop(field.attname)

    def __delitem__(self, key: str):
        if self.__options__.immutable:
            raise exc.DeleteError(
                f"{self.__class__}: "
                f"Attempt to delete item: [{repr(key)}] in immutable schema"
            )
        field = self.__parser__.get_field(key)
        if not field:
            return super().__delitem__(key)
        return self.__field_deleter__(field)

    def popitem(self):
        if self.__options__.immutable:
            raise exc.DeleteError(
                f"{self.__name__}: Attempt to popitem in immutable schema"
            )
        return super().popitem()

    def pop(self, key: str, default=unprovided):
        if self.__options__.immutable:
            raise exc.DeleteError(
                f"{self.__class__}: "
                f"Attempt to pop item: [{repr(key)}] in immutable schema"
            )
        field = self.__parser__.get_field(key)
        if not field:
            return super().pop(key)
        if field.immutable:
            raise exc.DeleteError(
                f"{self.__name__}: Attempt to pop immutable item: [{repr(key)}]"
            )
        if field.is_required(self.__options__):
            raise exc.DeleteError(
                f"{self.__name__}: Attempt to delete required schema key: {repr(key)}"
            )
        args = () if unprovided(default) else (default,)
        return super().pop(field.name, *args)

    def update(self, __m=None, **kwargs):
        if self.__options__.immutable:
            raise exc.UpdateError(
                f"{self.__name__}: Attempt to update in immutable schema"
            )
        data = dict(__m) if __m else kwargs
        for key, val in data.items():
            self.__setitem__(key, val)
        # TODO: reduce the dependant property calculation times if there are duplicate dependants

        # options = self.__options__.patch(
        #     ignored_options=['min_params'],
        #     ignore_required=True,
        #     no_default=True,
        # ).make_runtime()
        #
        # values = self.__parser__(
        #     # keep the original options settings including the addition
        #     dict(__m) if __m else kwargs, options=options
        # )
        #
        # self.__parser__.set_attributes(values, self, options=options)
        # self.__parser__.coerce_properties(values, self, options=options)
        #
        # return super().update(values)

    # def __copy__(self):
    #     return self.copy()

    def copy(self):
        obj = self.__class__.__new__(self.__class__)
        dict.update(obj, self)
        # since self.<data> is validated
        # we directly call dict.update to avoid calling the parsing methods again
        obj.__dict__ = self.__dict__
        return obj

    def clear(self):
        if self.__options__.immutable:
            raise exc.DeleteError(
                f"{self.__name__}: Attempt to clear in Options(immutable=True) schema"
            )
        for key, field in self.__parser__.fields.items():
            if field.immutable:
                raise exc.DeleteError(
                    f"{self.__name__}: Attempt to clear schema with immutable field: {repr(field.name)}"
                )
            if field.is_required(self.__options__):  # unless options is ignore_required
                raise exc.DeleteError(
                    f"{self.__name__}: Attempt to delete required schema key: {repr(key)}"
                )
        return super().clear()


DataClass.__init_subclass__()
Schema.__init_subclass__()
