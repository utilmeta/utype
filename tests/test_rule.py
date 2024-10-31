import decimal
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Iterator, List

import pytest

from utype import Lax, Options, Rule, exc, types, JsonSchemaGenerator
from utype.parser.rule import LogicalType
from utype.utils.compat import Literal


class TestRule:
    def test_logical(self):
        import math

        assert math.isnan(types.NanFloat("NAN"))
        assert math.isnan(types.AbnormalFloat("NAN"))
        assert math.isinf(types.AbnormalFloat("inf"))
        assert math.isinf(types.InfinityFloat("-inf"))
        assert types.NormalFloat("3.3") == 3.3

        with pytest.raises(exc.ParseError):
            types.NanFloat("inf")

        with pytest.raises(exc.ParseError):
            types.InfinityFloat("nan")

        with pytest.raises(exc.ParseError):
            types.NanFloat(3)

        with pytest.raises(exc.ParseError):
            types.NormalFloat("inf")

        with pytest.raises(exc.ParseError):
            types.NormalFloat("nan")

        int_or_dt = types.PositiveInt | date
        assert int_or_dt(b'3') == 3
        assert int_or_dt('2000-1-1') == date(2000, 1, 1)
        with pytest.raises(exc.ParseError):
            int_or_dt("a")

        assert JsonSchemaGenerator(int_or_dt)() == {'anyOf': [{'type': 'number', 'exclusiveMinimum': 0},
                                                              {'type': 'string', 'format': 'date'}]}

        int_or_none = types.PositiveInt | None
        assert int_or_none(1) == 1
        assert int_or_none(None) is None

        with pytest.raises(exc.ParseError):
            int_or_none("a")

        null_or_const = types.Null | 3 | True
        assert null_or_const(None) is None
        assert null_or_const(3) == 3
        assert null_or_const(True) is True
        assert null_or_const(1) is True

        assert JsonSchemaGenerator(null_or_const)() == {'anyOf': [{'type': 'null'}, {'type': 'integer', 'const': 3},
                                                                  {'type': 'boolean', 'const': True}]}

        with pytest.raises(exc.ParseError):
            null_or_const(False)

        with pytest.raises(exc.ParseError):
            null_or_const(2, context=Options(no_explicit_cast=True).make_context())

        int_or_list = types.NegativeInt | List[str]
        assert int_or_list(3) == ["3"]
        assert int_or_list(-3) == -3
        assert int_or_list(["a"]) == ["a"]
        assert int_or_list([1]) == ["1"]

        assert JsonSchemaGenerator(int_or_list)() == {'anyOf': [{'type': 'number', 'exclusiveMaximum': 0},
                                                                {'type': 'array', 'items': {'type': 'string'}}]}

        class IntWeekDay(int, Rule):
            gt = 0
            le = 7

        week_day = IntWeekDay ^ Literal['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

        assert week_day('6') == 6
        assert week_day(b'tue') == 'tue'

        with pytest.raises(exc.ParseError):
            week_day('8')

        # weekday_or_date = week_day | date
        weekday_or_date = LogicalType.any_of(week_day, date)

        assert weekday_or_date(b'5') == 5
        assert weekday_or_date('fri') == 'fri'
        assert weekday_or_date('2000-1-1') == date(2000, 1, 1)

        multi_any = Rule.any_of(dict, list, str, None)
        assert multi_any('str') == 'str'

    def test_length(self):
        class Length3(Rule):
            length = 3

        assert Length3(123) == 123
        assert Length3("123") == "123"
        assert Length3([1, 2, 3]) == [1, 2, 3]
        assert Length3(range(0, 3)) == range(0, 3)

        with pytest.raises(Exception):

            class LengthN(Rule):
                length = -1

        with pytest.raises(exc.ConstraintError):
            Length3(1234)
        with pytest.raises(exc.ConstraintError):
            Length3("1234")
        with pytest.raises(exc.ConstraintError):
            Length3([1, 2])
        with pytest.raises(exc.ConstraintError):
            Length3(range(0, 4))

    def test_min_length(self):
        class Length3(Rule):
            min_length = 3

        assert Length3(123) == 123
        assert Length3("1234") == "1234"
        assert Length3([1, 2, 3, 4]) == [1, 2, 3, 4]
        assert Length3(range(0, 4)) == range(0, 4)

        with pytest.raises(Exception):

            class LengthN(Rule):
                min_length = -1

        with pytest.raises(exc.ConstraintError):
            Length3(12)

        with pytest.raises(exc.ConstraintError):
            Length3([1, 2])

        with pytest.raises(exc.ConstraintError):
            Length3(range(0, 2))

    def test_max_length(self):
        class Length3(Rule):
            max_length = 3

        assert Length3(123) == 123
        assert Length3("12") == "12"
        assert Length3([1, 2]) == [1, 2]
        assert Length3(range(0, 2)) == range(0, 2)

        with pytest.raises(Exception):

            class Length3(Rule):
                max_length = -1

        with pytest.raises(exc.ConstraintError):
            Length3(1234)

        with pytest.raises(exc.ConstraintError):
            Length3(1234)

        with pytest.raises(exc.ConstraintError):
            Length3([1, 2, 3, 4])

        with pytest.raises(exc.ConstraintError):
            Length3(range(0, 4))

    def test_generic(self):
        class LengthRule(Rule):
            min_length = 1
            max_length = 3

        str_len = LengthRule[str]
        assert str_len(b'123') == '123'
        with pytest.raises(exc.ConstraintError):
            str_len(b'1234')

        arr_len = LengthRule[list]
        assert arr_len((1, 2, 3)) == [1, 2, 3]
        arr_int_len = LengthRule[list][int]
        assert arr_int_len((1, '2', b'3')) == [1, 2, 3]
        with pytest.raises(exc.ConstraintError):
            arr_int_len([1, 2, 3, 4])

    def test_value_bound(self):
        class IntB(Rule):
            gt = 1
            lt = 10

        class EIntB(Rule):
            ge = 1
            le = 10

        class MIntB(Rule):
            ge = 1
            lt = 10

        class FloatB(Rule):
            gt = -0.3
            lt = 0.3

        class EFloatB(Rule):
            ge = -0.3
            le = 0.3

        class MFloatB(Rule):
            gt = -0.3
            le = 0.3

        class StrB(Rule):
            gt = "a"
            lt = "t"

        class EStrB(Rule):
            ge = "a"
            le = "t"

        class MStrB(Rule):
            ge = "a"
            lt = "t"

        class ListB(Rule):
            gt = [1]
            lt = [10]

        class EListB(Rule):
            ge = [1]
            le = [10]

        class MListB(Rule):
            gt = [1]
            le = [10]

        class DtB(Rule, datetime):
            gt = datetime(2020, 1, 1)
            le = datetime(2022, 1, 1)

        assert DtB('2021-01-01') == datetime(2021, 1, 1)

        with pytest.raises(exc.ConstraintError):
            DtB('2023-02-03')

        with pytest.raises(exc.ConfigError):
            class IntV(Rule):
                gt = 3
                lt = 2

        with pytest.raises(exc.ConfigError):

            class IntV(Rule):  # noqa
                gt = 3
                ge = 3

        with pytest.raises(exc.ConfigError):

            class IntV(Rule):  # noqa
                gt = 3
                ge = 2

        with pytest.raises(exc.ConfigError):

            class IntV(Rule):  # noqa
                gt = 3
                le = 3

        assert IntB("3") == 3
        assert FloatB("0") == 0
        assert StrB("bc") == "bc"
        assert EStrB("a") == "a"
        assert EListB([1]) == [1]
        assert ListB([1, 2]) == [1, 2]
        assert MIntB("1") == 1
        assert EFloatB("0.3") == 0.3

        with pytest.raises(exc.ConstraintError):
            IntB(0)
        with pytest.raises(exc.ConstraintError):
            FloatB("-0.3")
        with pytest.raises(exc.ConstraintError):
            StrB("a")
        with pytest.raises(exc.ConstraintError):
            ListB([1])

        with pytest.raises(exc.ConstraintError):
            EIntB(0)
        with pytest.raises(exc.ConstraintError):
            MIntB(0.31)
        with pytest.raises(exc.ConstraintError):
            MFloatB(b"-0.3")
        with pytest.raises(exc.ConstraintError):
            MStrB("ts")
        with pytest.raises(exc.ConstraintError):
            MListB([10, 1])

        class LaxEIntB(int, Rule):
            ge = Lax(1)
            le = Lax(10)

        assert LaxEIntB('0') == 1
        assert LaxEIntB(3.3) == 3
        assert LaxEIntB(11) == 10

    def test_max_digits(self):
        class MaxFloat(types.Float):
            max_digits = 6

        assert MaxFloat(b"33.123") == 33.123
        assert MaxFloat("-33.123") == -33.123
        assert MaxFloat("-0.123456") == -0.123456   # the left 0 does not count
        assert MaxFloat("-0.003456") == -0.003456   # the left 0 does not count

        with pytest.raises(exc.ConstraintError):
            MaxFloat("-0.0034567")

        with pytest.raises(exc.ConstraintError):
            MaxFloat("3311.123")

        with pytest.raises(exc.ConstraintError):
            MaxFloat(-3311.123)

        class Hundreds(int, Rule):
            max_digits = 3
            multiple_of = 100

        assert Hundreds('200') == 200

        with pytest.raises(exc.ConstraintError):
            Hundreds(1000)

        with pytest.raises(exc.ConstraintError):
            Hundreds(120)

        class MaxFloat(types.Float):
            max_digits = Lax(6)

        assert MaxFloat('123.4567') == 123.457      # round(123.4567, 3) == 123.457

        with pytest.raises(exc.ConstraintError):
            MaxFloat(1234567.123)

    def test_multiple_of(self):
        class MulInt(types.Int):
            multiple_of = 3

        assert MulInt(9) == 9
        assert MulInt(b"30.3") == 30
        assert MulInt("-33") == -33

        with pytest.raises(exc.ConstraintError):
            MulInt(b"2.2")

        with pytest.raises(exc.ConstraintError):
            MulInt(32)

        class LooseMulInt(types.Int):
            multiple_of = Lax(3)

        assert LooseMulInt("31.1") == 30

    def test_decimals(self):
        class D(decimal.Decimal, Rule):
            decimal_places = 2
            max_digits = 4

        assert D(1.5) == decimal.Decimal('1.50')    # decimal places will shape Decimal

        with pytest.raises(exc.ConstraintError):
            D(111.3)     # -> '11.30'

        with pytest.raises(exc.ConstraintError):
            D(1.323)     # decimal places exceed

        with pytest.raises(exc.ConstraintError):
            D('1.500')     # decimal places exceed

        class FD(float, Rule):
            decimal_places = 3
            max_digits = 4

        assert FD(1.3) == 1.3
        assert FD(111.3) == 111.3

        with pytest.raises(exc.ConstraintError):
            D(0.3234)     # decimal places exceed

        def make_round(r):
            class F(types.Float):
                decimal_places = Lax(r)
            return F

        assert make_round(2)(1.2) == round(1.2, 2)  # noqa
        assert make_round(1)(1.24) == round(1.24, 1)  # noqa
        assert make_round(0)("1.245") == round(1.245, 0)  # noqa
        assert make_round(-1)("31.245") == round(31.245, -1)  # noqa

        with pytest.raises(exc.ConfigError):
            class D1(decimal.Decimal, Rule):
                decimal_places = 3
                max_digits = 2

    def test_contains(self):
        class IntArray(list, types.Array):
            contains = types.PositiveInt
            max_contains = 3
            min_contains = 1

        assert IntArray([1, 2, 3]) == [1, 2, 3]
        assert IntArray([1, 2, -1, "a", "b"]) == [1, 2, -1, "a", "b"]
        assert IntArray(["1", True, b"2.3"]) == ["1", True, b"2.3"]     # no transform

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray([-1])

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray([1, 2, 3, 4, "a"])

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray(["1", -3, b"2.3"], context=Options(no_explicit_cast=True).make_context())

        int_array = IntArray[int]
        assert int_array(["1", -3, b"2.3"]) == [1, -3, 2]

        class Const1(int, Rule):
            const = 1

        class ConTuple(tuple, Rule):
            contains = Const1
            max_contains = 3

        assert ConTuple([1, True]) == (1, True)

        with pytest.raises(exc.ConstraintError):
            ConTuple([0, 2])

        with pytest.raises(exc.ConstraintError):
            ConTuple([1, True, b'1', '1.0'])

    def test_unique_items(self):
        class UniqueArray(list, types.Array):
            unique_items = True

        assert UniqueArray([1, 2, 3]) == [1, 2, 3]
        assert UniqueArray((1, "1", b"1")) == [1, "1", b"1"]

        with pytest.raises(exc.ConstraintError):
            assert UniqueArray((1, 1, 2))

        int_unique_array = UniqueArray[int]
        assert int_unique_array([1, "2", b"3"]) == [1, 2, 3]
        with pytest.raises(exc.ConstraintError):
            int_unique_array((1, "1", b"1"))

        class LaxUniqueArray(list, types.Array):
            unique_items = Lax(True)

        assert LaxUniqueArray([1, 1, 2, 3, 3]) == [1, 2, 3]

    def test_enum_const(self):
        class Const(Rule):
            const = 1

        class IntConst(int, Rule):
            const = 1

        class LooseConst(Rule):
            const = Lax(1)

        assert Const(1) == 1
        assert IntConst(True) == 1
        assert LooseConst(True) == 1
        assert IntConst("1") == 1

        with pytest.raises(exc.ParseError):
            Const(2)

        with pytest.raises(exc.ParseError):
            Const(True)

        with pytest.raises(exc.ParseError):
            Const("1")

        with pytest.raises(exc.ParseError):
            IntConst(2)

        choices = ["INFO", "WARN", "ERROR"]

        array_enum = types.enum_array(choices, array_type=tuple)
        unique_array_enum = types.enum_array(choices, unique=True)

        class EnumRule(Rule):
            enum = choices

        assert EnumRule("WARN") == "WARN"
        with pytest.raises(exc.ConstraintError):
            EnumRule("DEBUG")

        assert array_enum("INFO") == ("INFO",)
        assert array_enum(["INFO", "ERROR"]) == ("INFO", "ERROR")
        assert unique_array_enum(["INFO", "ERROR"]) == ["INFO", "ERROR"]

        class LaxEnumRule(Rule):
            enum = Lax(choices)

        assert LaxEnumRule('OTHER') in choices

        with pytest.raises(exc.ParseError):
            array_enum(["A", "E"])

        with pytest.raises(exc.ParseError):
            array_enum("WRONG")

        with pytest.raises(exc.ParseError):
            # unique
            unique_array_enum(["INFO", "INFO", "ERROR"])

        class Color(Enum):
            RED = 1
            GREEN = 2
            BLUE = 3

        class EnumRule2(Rule):
            enum = Color

        set_enum = types.enum_array(Color, array_type=set)

        assert EnumRule2(Color.RED.value) == Color.RED.value
        assert EnumRule2(Color.GREEN) == Color.GREEN.value

        with pytest.raises(exc.ParseError):
            EnumRule2("BLUE")

        assert set_enum([Color.RED, Color.BLUE.value]) == {
            Color.RED.value,
            Color.BLUE.value,
        }

    def test_regex(self):
        class Reg(Rule):
            regex = "([A-Za-z0-9]+)"

        assert Reg("abcABC123") == "abcABC123"
        with pytest.raises(exc.ConstraintError):
            Reg("abc@123")

    def test_args(self):
        import enum

        from utype.types import Array

        class EnumLevel(str, enum.Enum):
            info = 'INFO'
            warn = 'WARN'
            error = 'ERROR'

        level_array = Array[EnumLevel]

        assert level_array('INFO') == [EnumLevel.info]    # not .value, but the enum instance

        class UniqueIntArray(list, types.Array):
            __args__ = int

            def __iter__(self) -> Iterator[int]:
                return super().__iter__()

            def __getitem__(self, key) -> int:
                return super().__getitem__(key)

            unique_items = True
            contains = types.PositiveInt
            max_contains = 3
            min_contains = 2

        class SingleItemDict(dict, types.Object):
            length = 1

        class UniqueTuple(types.Array):
            __origin__ = tuple
            unique_items = True

        assert UniqueIntArray([-1, "2", True]) == [-1, 2, 1]

        with pytest.raises(exc.ConstraintError):
            UniqueIntArray([-1, 2])

        with pytest.raises(exc.ConstraintError):
            UniqueIntArray([-1, 2, "3", True, 5])

        with pytest.raises(exc.ConstraintError):
            # not unique
            UniqueIntArray([1, "2", True])

        dict_type = SingleItemDict[types.SlugStr, types.NaturalInt | None]
        tup_str = UniqueTuple[types.SlugStr, types.NegativeInt, types.AbnormalFloat]
        tup_eli = UniqueTuple[types.PositiveInt | None, ...]

        assert tup_str([1, "-5", "-infinity"]) == ("1", -5, float("-inf"))

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, "-5"])

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, "-5", "-infinity", 1], context=Options(no_data_loss=True).make_context())

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, "-5", 3])

        with pytest.raises(exc.ParseError):
            # absence
            tup_str(["@", -5, "nan"])

        assert tup_eli([1, 2, None]) == (1, 2, None)
        assert tup_eli([1, b"3", "nil"]) == (1, 3, None)

        with pytest.raises(exc.ParseError):
            tup_eli([-1, None])

        with pytest.raises(exc.ParseError):
            # not unique
            tup_eli([1, 1, None])

        assert dict_type({123: 3}) == {"123": 3}
        assert dict_type({"ab": "null"}) == {"ab": None}

        with pytest.raises(exc.ParseError):
            # length > 1
            dict_type({123: 3, "ab": None})

        with pytest.raises(exc.ParseError):
            # length < 1
            dict_type({})

        with pytest.raises(exc.ParseError):
            dict_type({"@": 3})

        with pytest.raises(exc.ParseError):
            dict_type({"A": -1})

        with pytest.raises(exc.ParseError):
            dict_type({"A": "a"})

    # def test_example(self):
    #     rules = [
    #         Rule(length=3, type=int),
    #         Rule(length=3, type=str),
    #         Rule(type=str, gt="abc"),
    #         Rule(template=[Rule(type=int, max_length=2)], min_length=5),
    #         Rule(template={"key": Rule(type=int, ge=3, le=10)}),
    #         Rule(type_union=[datetime, int]),
    #         Rule(type=timedelta, gt=timedelta(), le=timedelta(days=1)),
    #         Rule(type=str, max_length=10, min_length=7),
    #         Rule(type=float, max_length=10, min_length=7, round=3),
    #         Rule(type=float, length=6, round=3),
    #         Rule(type=Decimal, round=2, gt=3),
    #     ]
    #     for rule in rules:
    #         rule(rule.get_example())
