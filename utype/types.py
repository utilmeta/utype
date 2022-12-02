from .parser.rule import Rule
from collections import abc
from .utils import exceptions as exc
from decimal import Decimal
from typing import Union, Type
from enum import Enum

# from typing import TypeVar
# T = TypeVar('T')


class Number(Rule):
    primitive = "number"

    @classmethod
    def check_type(cls, t):
        # must be an iterable
        assert issubclass(t, (int, float, Decimal))


class Array(Rule):
    __origin__ = abc.Iterable
    primitive = "array"
    contains: type
    max_contains: int
    min_contains: int
    unique_items: bool

    def __iter__(self):
        raise NotImplementedError

    def __class_getitem__(cls, item) -> Type["Array"]:
        if not isinstance(item, tuple):
            item = (item,)
        return cls.annotate(cls.__origin__, *item)

    @classmethod
    def check_type(cls, t):
        # must be an iterable
        assert hasattr(t, "__iter__")


class Object(Rule):
    primitive = "object"

    def __iter__(self):
        raise NotImplementedError

    def __class_getitem__(cls, params):
        if len(params) != 2:
            raise TypeError(
                f"{cls} should use {cls}[KeyType, ValType] with 2 params, got {params}"
            )
        return cls.annotate(cls.__origin__, *params)

    @classmethod
    def check_type(cls, t):
        # must be an iterable
        assert hasattr(t, "__iter__") and hasattr(t, "items")


class Float(float, Number):
    pass


class Int(int, Number):
    pass


class Str(str, Rule):
    pass


class Bool(str, Rule):
    pass


class Null(Rule):
    __origin__ = type(None)
    primitive = "null"
    # const = None


class PositiveInt(Int):
    gt = 0


class NaturalInt(Int):
    ge = 0


class PositiveFloat(Float):
    gt = 0


class NegativeFloat(Float):
    lt = 0


class NanFloat(Float):
    @classmethod
    def apply(cls, value, __options__=None):
        value = super().apply(value, __options__)
        import math

        if not math.isnan(value):
            # do not use const = float('nan')
            # cause NaN can not use equal operator
            raise exc.ConstraintError(constraint="const", constraint_value=float("nan"))
        return value


class InfinityFloat(Float):
    enum = [float("inf"), float("-inf")]


AbnormalFloat = NanFloat ^ InfinityFloat

NormalFloat = Float & ~AbnormalFloat


class NegativeInt(Int):
    lt = 0


class Timestamp(Float):
    """
    timestamps to represent datetime and date
    """

    ge = 0
    format = "timestamp"

    @classmethod
    def apply(cls, value, __options__=None):
        import datetime

        if isinstance(value, datetime.datetime):
            value = value.timestamp()
        elif isinstance(value, datetime.timedelta):
            value = value.total_seconds()
        super().apply(value, __options__)


def enum_array(
    item_enum: Union[Type[Enum], list, tuple, set],
    item_type=None,
    array_type=list,
    unique: bool = False,
    array_strict: bool = True,
) -> Type[Array]:
    """
    Make an array type, which item is one of the enum value
    """
    if isinstance(item_enum, Enum):
        EnumItem = item_enum
    else:

        class EnumItem(Rule):
            __origin__ = item_type
            enum = item_enum

    class EnumArray(array_type, Array):
        __args__ = (EnumItem,)
        __ellipsis_args__ = issubclass(array_type, tuple)
        unique_items = unique
        strict = array_strict

    return EnumArray


class SlugStr(Str):
    """
    Slug str or URI
    """

    format = "slug"
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"


# class Secret(Str):
#     """
#     Slug str or URI
#     """
#     def __repr__(self):
#         return f'{self.__class__.__name__}("%s")' % ('*' * 6)
#
#     def __str__(self):
#         return f'{self.__class__.__name__}("%s")' % ('*' * 6)


class Year(Int):
    ge = 1
    le = 9999


class Month(Int):
    ge = 1
    le = 12


class Day(Int):
    ge = 1
    le = 31


class Week(Int):
    ge = 1
    le = 53


class WeekDay(Int):
    ge = 1
    le = 7


class Quarter(Int):
    ge = 1
    le = 4


class Hour(Int):
    ge = 0
    le = 23


class Minute(Int):
    ge = 0
    le = 59


class Second(Int):
    ge = 0
    le = 59


class EmailStr(Str):
    format = "email"
    regex = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"


# from pathlib import Path
#
#
# class FilePath(Path, Rule):
#     format = 'file-path'
#     is_dir: bool = False
#     is_abs: bool = None
#     is_link: bool = None
#     is_exists: bool = None
#     max_size: int
#     min_size: int
#
#
# class Directory(Path, Rule):
#     format = 'directory'
#     is_dir: bool = True
#     is_abs: bool = None
#     is_link: bool = None
#     is_exists: bool = None
#     max_files: int
#     min_files: int
