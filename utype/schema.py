from .parser.rule import LogicalType
from .parser.options import Options, RuntimeOptions
from .utils.transform import register_transformer, TypeTransformer
from .utils.functional import pop
from collections.abc import Mapping
from .parser.cls import ClassParser
from typing import TypeVar, Type, Union

T = TypeVar('T')


class SchemaMeta(type):
    __logical_type__ = LogicalType

    @property
    def __ref__(cls):
        try:
            name = cls.__qualname__
        except AttributeError:
            name = cls.__name__
        if '.' in name:
            name = ''.join([part.capitalize() if part.islower() else part for part in name.split('.')])
        return f'{cls.__module__}.{name}'

    def __get_field__(cls, key: str):
        return cls.__parser__.get_field(key)

    def __init__(cls, name, bases: tuple, attrs: dict, **kwargs):
        super().__init__(name, bases, attrs)
        if not any(isinstance(base, SchemaMeta) for base in bases):
            # first base classes
            return
        cls.__kwargs__ = kwargs
        cls.__parser_cls__: Type[ClassParser] = getattr(cls, '__parser_cls__', ClassParser)
        cls.__parser__ = cls.__parser_cls__.apply_for(cls)
        cls.__options__ = cls.__parser__.options
        # if cls.__parser__.init_parser:
        #     # override the __init__ to provide type parsing for init function
        #     cls.__init__ = cls.__parser__.init_parser.function

        for key, field in cls.__parser__.fields.items():
            if not field.property:
                setattr(cls, field.attname, field)

    def __and__(cls, other):
        if isinstance(other, LogicalType):
            return other.__rand__(cls)      # noqa
        return cls.__logical_type__.combine('&', cls, other)

    def __rand__(cls, other):
        return cls.__logical_type__.combine('&', other, cls)

    def __or__(cls, other):
        if getattr(other, '__origin__', None) == Union:
            return cls.__logical_type__.combine('|', cls, *other.__args__)
        if isinstance(other, LogicalType):
            return other.__ror__(cls)      # noqa
        return cls.__logical_type__.combine('|', cls, other)

    def __ror__(cls, other):
        if getattr(other, '__origin__', None) == Union:
            return cls.__logical_type__.combine('|', *other.__args__, cls)
        return cls.__logical_type__.combine('|', other, cls)

    def __xor__(cls, other):
        if isinstance(other, LogicalType):
            return other.__rxor__(cls)      # noqa
        return cls.__logical_type__.combine('^', cls, other)

    def __rxor__(cls, other):
        return cls.__logical_type__.combine('^', other, cls)

    def __invert__(cls):
        return cls.__logical_type__.combine('~', cls)


class DataClass(metaclass=SchemaMeta):
    __parser_cls__ = ClassParser
    __parser__: ClassParser
    __options__: Options
    __mode__: str = None

    def __class_getitem__(cls, item):
        pass

    def __validate__(self, options=None):
        pass

    def __post_init__(self, options: RuntimeOptions):
        self.__runtime_options__ = options
        self.__validate__(options)


class Schema(dict, metaclass=SchemaMeta):
    __parser_cls__ = ClassParser
    __parser__: ClassParser
    __options__: Options
    __mode__: str = None

    def __class_getitem__(cls, item):
        pass

    def __validate__(self, options=None):
        pass

    def __str__(self):
        items = []
        for key, val in self.items():
            field = self.__parser__.get_field(key)
            name = field.name if field else key
            items.append(f'{name}={repr(val)}')
        values = ', '.join(items)
        return f'{self.__name__}({values})'

    @property
    def __name__(self):
        return getattr(self.__class__, '__qualname__', self.__class__.__name__)

    def __repr__(self):
        return self.__str__()

    def __post_init__(self, values, options: RuntimeOptions):
        self.__runtime_options__ = options
        self.__validate__(options)

    def __setitem__(self, alias: str, value):
        if self.__options__.immutable:
            raise AttributeError(f'{self.__class__}: '
                                 f'Attempt to set item: [{repr(alias)}] in immutable schema')

        field = self.__parser__.get_field(alias)
        options = self.__options__.make_runtime(__class__, force_error=True)
        if not field:
            if alias in self.__parser__.exclude_vars:
                raise AttributeError(f'{self.__class__}: Attempt to set excluded attribute: {repr(alias)}')
            addition = self.__parser__.parse_addition(alias, value, options=options)
            if addition is ...:
                # ignore addition
                return
            return super().__setitem__(alias, value)

        if field.immutable:
            raise AttributeError(f'{self.__class__}: '
                                 f'Attempt to set immutable item: [{repr(alias)}]')
        value = field.parse_value(value, options=self.__options__.make_runtime(__class__))
        self.__dict__[field.attname] = value

        if not field.no_output(value, options=options):
            super().__setitem__(field.name, value)

    def __setattr__(self, alias: str, value):
        field = self.__parser__.get_field(alias)
        options = self.__options__.make_runtime(__class__, force_error=True)
        if not field:
            if alias in self.__parser__.exclude_vars:
                raise AttributeError(f'{self.__class__}: Attempt to set excluded attribute: {repr(alias)}')
            # addition = self.__parser__.parse_addition(alias, value, options=options)
            # if addition is ...:
            #     # ignore addition
            #     return
            return super().__setattr__(alias, value)

        if self.__options__.immutable or field.immutable:
            raise AttributeError(f'{self.__name__}: '
                                 f'Attempt to set immutable attribute: [{repr(alias)}]')

        value = field.parse_value(value, options=options)
        super().__setattr__(field.attname, value)

        if not field.no_output(value, options=options):
            if field.property:
                value = getattr(self, field.attname)
                # self.__dict__[field.attname] = value
            super().__setitem__(field.name, value)
        else:
            # no output
            if field.name in self:
                super().__delitem__(field.name)

    def __delitem__(self, key: str):
        if self.__options__.immutable:
            raise AttributeError(f'{self.__class__}: '
                                 f'Attempt to delete item: [{repr(key)}] in immutable schema')
        field = self.__parser__.get_field(key)
        if not field:
            return super().__delitem__(key)
        if field.immutable:
            raise AttributeError(f'{self.__name__}: '
                                 f'Attempt to delete immutable item: [{repr(key)}]')
        options = self.__options__.make_runtime(__class__, force_error=True)
        if field.is_required(options):
            raise AttributeError(f'{self.__name__}: Attempt to delete required schema key: {key}')
        super().__delitem__(field.name)
        if hasattr(self, field.attname):
            super().__delattr__(field.attname)

    def __delattr__(self, key: str):
        field = self.__parser__.get_field(key)
        if not field:
            return super().__delattr__(key)
        if self.__options__.immutable or field.immutable:
            raise AttributeError(f'{self.__name__}: '
                                 f'Attempt to delete immutable attribute: [{repr(key)}]')
        options = self.__options__.make_runtime(__class__, force_error=True)
        if field.is_required(options):
            raise AttributeError(f'{self.__name__}: Attempt to delete required schema key: {repr(key)}')
        if field.name in self:
            super().__delitem__(field.name)
        super().__delattr__(field.attname)

    def popitem(self):
        if self.__options__.immutable:
            raise TypeError(f'{self.__name__}: Attempt to popitem in immutable schema')
        return super().popitem()

    def pop(self, key: str):
        if self.__options__.immutable:
            raise AttributeError(f'{self.__class__}: '
                                 f'Attempt to pop item: [{repr(key)}] in immutable schema')
        field = self.__parser__.get_field(key)
        if not field:
            return super().pop(field.name)
        if field.immutable:
            raise AttributeError(f'{self.__name__}: '
                                 f'Attempt to pop immutable item: [{repr(key)}]')
        options = self.__options__.make_runtime(__class__, force_error=True)
        if field.is_required(options):
            raise TypeError(f'{self.__name__}: Attempt to delete required schema key: {repr(key)}')
        return super().pop(field.name)

    def update(self, __m=None, **kwargs):
        if self.__options__.immutable:
            raise AttributeError(f'{self.__name__}: Attempt to update in Options(immutable=True) schema')
        return super().update(self.__parser__(__m or kwargs, options=Options(ignore_required=True).make_runtime()))

    def clear(self):
        if self.__options__.immutable:
            raise TypeError(f'{self.__name__}: Attempt to clear in Options(immutable=True) schema')
        return super().clear()


@register_transformer(metaclass=SchemaMeta)
def transform(transformer: TypeTransformer, data, cls: SchemaMeta):
    if not isinstance(data, (dict, Mapping)):
        if transformer.no_explicit_cast:
            raise TypeError(f'invalid input type for {cls}, should be dict or Mapping')
        else:
            data = transformer(data, dict)
    if not transformer.options.vacuum:
        if not cls.__options__.allowed_runtime_options:
            # pass the runtime options
            data.update(__options__=transformer.options)
    return cls(**data)
