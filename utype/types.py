from decimal import Decimal
from enum import Enum
from datetime import datetime, timedelta, date
from uuid import UUID
from typing import Union, Optional, Tuple, List, Set, Mapping, \
    Dict, Type, Callable, Any, TYPE_CHECKING, Iterator, ClassVar
from .utils.compat import Literal, Annotated, Final, ForwardRef
from .parser.rule import Lax, Rule

# from typing import TypeVar
# T = TypeVar('T')


class Number(Rule):
    primitive = "number"

    @classmethod
    def check_type(cls, t):
        # must be an iterable
        assert issubclass(t, (int, float, Decimal))


class Array(Rule):
    __origin__ = list  # use list instead of abc.Iterable
    primitive = "array"

    # def __class_getitem__(cls, item) -> Type["Array"]:
    #     if not isinstance(item, tuple):
    #         item = (item,)
    #     return cls.annotate(cls.__origin__, *item)

    @classmethod
    def check_type(cls, t):
        # must be an iterable
        assert hasattr(t, "__iter__")


class Object(Rule):
    __origin__ = dict
    primitive = "object"

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


class Bool(Rule):
    __origin__ = bool


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
    def post_validate(cls, value, options=None):
        import math

        if not math.isnan(value):
            # do not use const = float('nan')
            # cause NaN can not use equal operator
            from .utils import exceptions as exc
            raise exc.ConstraintError(constraint="const", constraint_value=float("nan"))
        return value


class InfinityFloat(Float):
    enum = [float("inf"), float("-inf")]


AbnormalFloat = NanFloat ^ InfinityFloat

NormalFloat = Float & ~AbnormalFloat


class Zero(Rule):
    const = 0


Divisor = Float & ~Zero


class NegativeInt(Int):
    lt = 0


class Timestamp(Float):
    """
    timestamps to represent datetime and date
    """

    ge = 0
    format = "timestamp"

    @classmethod
    def pre_validate(cls, value, options=None):
        import datetime

        if isinstance(value, datetime.datetime):
            value = value.timestamp()
        elif isinstance(value, datetime.timedelta):
            value = value.total_seconds()
        return value


def round_number(precision: int = 0, num_type: type = float):
    class RoundNumber(num_type, Rule):
        decimal_places = Lax(precision)

    return RoundNumber


def enum_array(
    item_enum: Union[Type[Enum], list, tuple, set],
    item_type=None,
    array_type=list,
    unique: bool = False,
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

    class EnumArray(Array):
        __origin__ = array_type
        __args__ = (EnumItem,)
        __ellipsis_args__ = issubclass(array_type, tuple)
        unique_items = unique

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


class Datetime(datetime, Rule):
    primitive = "string"
    format = "datetime"


class Date(date, Rule):
    primitive = "string"
    format = "date"


class Timedelta(timedelta, Rule):
    primitive = "string"
    format = "duration"


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
