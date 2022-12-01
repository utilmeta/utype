from utype import Rule, Options, exc
from utype.utils.transform import TypeTransformer, register_transformer
from utype import types
import uuid
import pytest
from typing import List, Iterator, Iterable
from datetime import datetime, date, timedelta, time, timezone
from uuid import UUID
from decimal import Decimal
from enum import Enum
from collections.abc import Mapping


class TestRule:
    def test_types(self):
        dt = datetime(2022, 1, 2, 21, 22, 23)
        uid = uuid.uuid4()

        # INPUT, OUTPUT, NO_EXPLICIT_CAST, NO_DATA_LOSS
        class NumEnum(int, Enum):
            z = 0
            a = 1
            b = 2
            c = 3
        en_z = NumEnum(0)
        en_a = NumEnum(1)

        class SubInt(int):
            pass

        class SubFloat(float):
            pass

        class SubStr(str):
            pass

        class SubBytes(bytes):
            pass

        class MyIterable(Iterable):
            def __init__(self, lst):
                self.lst = lst

            def __eq__(self, other):
                if not isinstance(other, MyIterable):
                    return False
                return self.lst == other.lst

            def __iter__(self):
                return iter(self.lst)

        class MyMapping(Mapping):
            def __getitem__(self, k):
                return self.dic.__getitem__(k)

            def __eq__(self, other):
                if not isinstance(other, MyMapping):
                    return False
                return self.dic == other.dic

            def __len__(self) -> int:
                return len(self.dic)

            def __init__(self, dic):
                self.dic = dic

            def __iter__(self):
                return iter(self.dic)

        class MyNumber(int):
            pass

        @register_transformer(MyNumber, allow_subclasses=False)
        def trans_my(trans, d, t):
            a, b = str(d).split(',')
            return t(int(a) * int(b))

        assert_map = {
            type(None): [
                (None, None, True, True),
                ('None', None, False, True),
                ('null', None, False, True),
                ('nil', None, False, True),
            ],
            str: [
                (123, "123", False, True),
                (["a"], "a", False, True),
                (["a", "b"], "a", False, False),
                ({"a": 1}, repr({"a": 1}), False, True),
                (b"std", "std", True, True),
                (True, "True", False, True),
                ([], "[]", False, True),
                (['a'], 'a', False, True),
                (['a', 'b'], 'a', False, False),
                (en_z, '0', False, True),
                ('测试1'.encode('gbk'), '1', True, False)     # data loss, use "ignore" on byte errors
            ],
            SubStr: [
                ('123', SubStr("123"), True, True),
                (123, SubStr("123"), False, True),
                (["a"], SubStr("a"), False, True),
                (True, SubStr("True"), False, True),
                (en_z, SubStr('0'), False, True),
                ('测试1'.encode('gbk'), SubStr('1'), True, False)  # data loss, use "ignore" on byte errors
            ],
            bytes: [
                (123, b"123", False, True),
                (["a"], b"a", False, True),
                ([b"a", b"b"], b"a", False, False),
                ({"a": 1}, repr({"a": 1}).encode(), False, True),
                (True, b"True", False, True),
                (bytearray(b'123'), b"123", True, True),
                (memoryview(b'123'), b"123", True, True),
                ('123', b"123", True, True),
                (en_z, b'0', False, True),
            ],
            SubBytes: [
                (b'123', SubBytes(b"123"), True, True),
                (123, SubBytes(b"123"), False, True),
                (True, SubBytes(b"True"), False, True),
                (bytearray(b'123'), SubBytes(b"123"), True, True),
                (memoryview(b'123'), SubBytes(b"123"), True, True),
                ('123', SubBytes(b"123"), True, True),
                (en_z, SubBytes(b'0'), False, True),
            ],
            int: [
                (False, 0, True, True),
                (True, 1, True, True),
                (10.1, 10, True, False),
                ("123", 123, False, True),
                ("10.1", 10, False, False),
                (b"-0.3", 0, False, False),
                ([b"-0.3"], 0, False, False),
                ("-1.24", -1, False, False),
                (Decimal("0.14"), 0, True, False),
                (timedelta(hours=1), 3600, False, True),
                ([10], 10, False, True),
                ([10, 11], 10, False, False),
                (en_z, 0, True, True)       # this enum instance is an instance of int
            ],
            SubInt: [
                (1, SubInt(1), True, True),
                (False, SubInt(0), True, True),
                (True, SubInt(1), True, True),
                (10.1, SubInt(10), True, False),
                ("123", SubInt(123), False, True),
                ("10.1", SubInt(10), False, False),
                (b"-0.3", SubInt(0), False, False),
                (Decimal("0.14"), SubInt(0), True, False),
            ],
            MyNumber: [
                ('2,3', MyNumber(6), True, True),
            ],
            float: [
                (False, 0.0, True, True),
                (True, 1.0, True, True),
                ("123", 123.0, False, True),
                (123, 123.0, True, True),
                ("10.1", 10.1, False, True),
                ("10.100", 10.1, False, True),
                (b"-0.3", -0.3, False, True),
                ("-1.24", -1.24, False, True),
                ("inf", float("inf"), False, True),
                ("Infinity", float("inf"), False, True),
                ("INF", float("inf"), False, True),
                ("-inf", float("-inf"), False, True),
                ("-Infinity", float("-inf"), False, True),
                # ('nan', float('nan')),    cannot asset equal
                # ('NaN', float('nan')),
                # ('-NAN', float('nan')),
                (Decimal("0.14"), 0.14, True, True),
                (timedelta(hours=1, milliseconds=200), 3600.2, False, True),
                (en_a, 1.0, True, True)
            ],
            SubFloat: [
                (10.1, SubFloat(10.1), True, True),
                ("10.100", SubFloat(10.1), False, True),
                (b"-0.3", SubFloat(-0.3), False, True),
                ("-1.24", SubFloat(-1.24), False, True),
                ("inf", SubFloat("inf"), False, True),
                ("Infinity", SubFloat("inf"), False, True),
            ],
            Decimal: [
                (10.1, Decimal("10.1"), True, True),
                (10, Decimal("10"), True, True),
                ("123", Decimal("123"), True, True),    # str is not consider explicit type cast for decimal
                ("10.1", Decimal("10.1"), True, True),
                ("10.100", Decimal("10.100"), True, True),
                (b"-0.3", Decimal("-0.3"), True, True),
                ("-1.24", Decimal("-1.24"), True, True),
                ("inf", Decimal("inf"), True, True),
                (timedelta(hours=1, milliseconds=200), Decimal("3600.2"), False, True),
                (en_z, Decimal("0"), False, True)
            ],
            bool: [
                ("", False, False, False),
                (0, False, True, True),
                (1, True, True, True),
                (1.0, True, True, True),
                (None, False, False, False),
                (-0.0, False, True, True),
                ("false", False, False, True),
                # ("null", False, False, False),    # NULL is not a False value
                # ("none", False),
                # ("None", False),
                ("off", False, False, True),
                ("f", False, False, True),
                ("no", False, False, True),
                # ("nil", False),
                (float("nan"), True, False, False),
                ("[]", True, False, False),
                ("{}", True, False, False),
                ([], False, False, False),
                (object, True, False, False),
                (object(), True, False, False),
                (en_z, False, True, True),      # <NumEnum.z: 0> == 0 : True
                (en_a, True, True, True)
            ],
            datetime: [
                (
                    dt.strftime(fmt),
                    dt.replace(tzinfo=timezone.utc)
                    if (fmt.endswith("GMT") or (fmt.endswith("Z") and "T" in fmt))
                    else dt,
                    True,
                    True
                )
                for key, fmt in TypeTransformer.DATETIME_FORMATS
            ]
            + [
                ('2022-01-02', datetime(2022, 1, 2), True, True),
                # ('10:20:30', datetime(1900, 1, 1, 10, 20, 30), True, True),       # no standard behaviour
                (dt.date(), datetime(2022, 1, 2), True, True),
                (dt.timestamp(), dt.replace(tzinfo=timezone.utc), True, True),
                (int(dt.timestamp()), dt.replace(tzinfo=timezone.utc), True, True),
                (str(dt.timestamp() * 1000), dt.replace(tzinfo=timezone.utc), True, True),
                (str(dt.timestamp() * 1000).encode(), dt.replace(tzinfo=timezone.utc), True, True),
            ],
            timedelta: [
                (0, timedelta(seconds=0), True, True),
                (10, timedelta(seconds=10), True, True),
                ("0", timedelta(seconds=0), False, True),
                ("-10.1", timedelta(seconds=-10.1), False, True),
                (b"-10.1", timedelta(seconds=-10.1), False, True),
                ('P1DT00H00M00S', timedelta(days=1), True, True),
                (b'P1DT00H00M00S', timedelta(days=1), True, True)
            ],
            date: [
                ("2020-02-20", date(2020, 2, 20), True, True),
                (b"2020-02-20", date(2020, 2, 20), True, True),
                (dt.timestamp(), dt.date(), True, False),
                (int(dt.timestamp() * 1000), dt.date(), True, False),
                (dt, dt.date(), True, False),
                (str(dt), dt.date(), True, False),
            ],
            time: [
                ("11:12:13", time(11, 12, 13), True, True),
                (b"11:12:13", time(11, 12, 13), True, True),
                (dt, dt.time(), True, False),
                (dt.date(), time(), True, False),
            ],
            UUID: [
                (str(uid), uid, True, True),
                (str(uid).encode(), uid, True, True),
                (str(uid).upper(), uid, True, True),
                (0x12345678123456781234567812345678, UUID('12345678-1234-5678-1234-567812345678'), False, True),
                (12.3456, UUID('00000000-0000-0000-0000-00000000000c'), False, False)
            ],
            dict: [
                # (None, {}),
                # ("", {}),
                ("{}", {}, False, True),
                ('{"a": true, "b": null}', {"a": True, "b": None}, False, True),
                ("{1: 2}", {1: 2}, False, True),     # python syntax
                (b"{1: 2}", {1: 2}, False, True),
                (b'{"a": 1}', {"a": 1}, False, True),
                ("k1=v1&k2=v2", {"k1": "v1", "k2": "v2"}, False, True),  # querystring syntax
                ('k1=v1;k2=v2', {"k1": "v1", "k2": "v2"}, False, True),  # cookie syntax
                ('k1=v1; k2=v2; k3=v3', {"k1": "v1", "k2": "v2", "k3": "v3"}, False, True),  # cookie syntax
                ('k1=v1, k2=v2, k3=v3', {"k1": "v1", "k2": "v2", "k3": "v3"}, False, True),
                ([("a", 1), ("b", 2)], {"a": 1, "b": 2}, True, True),   # list of tuple can directly pass dict(...)
                ([["a", 1], ["b", 2]], {"a": 1, "b": 2}, True, True),
                ({("a", 1), ("b", 2)}, {"a": 1, "b": 2}, True, True),
                ([{'a': 1}], {'a': 1}, False, True),
                ([{'a': 1}, {'b': 2}], {'a': 1}, False, False),
            ],
            MyMapping: [
                ({1: 2}, MyMapping({1: 2}), True, True),  # python syntax
                ("{1: 2}", MyMapping({1: 2}), False, True),  # python syntax
                ('{"a": true, "b": null}', MyMapping({"a": True, "b": None}), False, True),
                ("k1=v1&k2=v2", MyMapping({"k1": "v1", "k2": "v2"}), False, True),  # querystring syntax
                ([("a", 1), ("b", 2)], MyMapping({"a": 1, "b": 2}), True, True),
                # list of tuple can directly pass dict(...)
            ],
            list: [
                ((1, 2), [1, 2], True, True),
                ({"a": 1, "b": 2}, [{"a": 1, "b": 2}], False, True),
                ("[1,2]", [1, 2], False, True),
                ("(1,2)", [1, 2], False, True),
                ("1,2", ['1', '2'], False, True),
                (b"(1,2)", [1, 2], False, True),
                ("[]", [], False, True),
                ("{}", [], False, True),  # if dict is empty, directly convert to empty list
                ("{1:2}", [{1: 2}], False, True),  # otherwise, do not reduce information
                ("a, b, c", ["a", "b", "c"], False, True),
                ("a;b;c", ["a", "b", "c"], False, True),
                ("a; b; c", ["a", "b", "c"], False, True),
                ("value", ["value"], False, True),
                (True, [True], False, True),
            ],
            MyIterable: [
                ((1, 2), MyIterable([1, 2]), True, True),
                ({"a": 1, "b": 2}, MyIterable([{"a": 1, "b": 2}]), False, True),
                ("[1,2]", MyIterable([1, 2]), False, True),
                ("1,2", MyIterable(['1', '2']), False, True),
            ],
            set: [
                ([1, 2], {1, 2}, True, True),
                ((1, 2), {1, 2}, True, True),
                ({"a": 1, "b": 2}, {"a", "b"}, False, False),
                ("[1,2]", {1, 2}, False, True),
                ("{1,2}", {1, 2}, False, True),
                ("(1,2)", {1, 2}, False, True),
                ("[]", set(), False, True),
                ("a, b", {"a", "b"}, False, True),
                (b"a, b", {"a", "b"}, False, True),
                ("value", {"value"}, False, True),
                (True, {True}, False, True),
            ],
            tuple: [
                ([1, 2], (1, 2), True, True),
                ({"a": 1, "b": 2}, ({"a": 1, "b": 2},), False, True),
                ("[1,2]", (1, 2), False, True),
                ("(1,2)", (1, 2), False, True),
                ("[]", (), False, True),
                ("{}", (), False, True),
                ("()", (), False, True),
                ("a, b", ("a", "b"), False, True),
                (b"a, b", ("a", "b"), False, True),
                ("value", ("value",), False, True),
                (True, (True,), False, True),
            ],
            NumEnum: [
                ('0', en_z, False, True),
                (1, en_a, True, True),
                ('a', en_a, False, False),
                (en_z, en_z, True, True),
            ],
            # color_enum: [    # subclass of Enum
            #     (1, color_enum.red),
            #     ('2', color_enum.blue),
            #     (color_enum.green.name, color_enum.green),
            # ]
        }

        for target_type, values in assert_map.items():
            for input_value, output_value, no_explicit_cast, no_data_loss in values:
                options = Options(
                    no_explicit_cast=no_explicit_cast,
                    no_data_loss=no_data_loss
                ).make_runtime(force_error=True)
                transformer = TypeTransformer(options)
                try:
                    result = transformer(input_value, target_type)
                except Exception as e:
                    assert False, f'{target_type}: transform failed for input: {repr(input_value)}: {e}'

                assert result == output_value, f'{target_type}: wrong output for {repr(input_value)}: ' \
                                               f'{repr(result)} ({repr(output_value)} expected)'

                # True == 1
                # False == 0
                assert type(result) == type(output_value), f'{target_type}: wrong type for {repr(input_value)}: ' \
                                                           f'{repr(result)} ({repr(output_value)}' \
                                                           f' ({type(output_value)}) expected)'

                if not no_explicit_cast:
                    transformer.no_explicit_cast = True
                    try:
                        transformer(input_value, target_type)
                    except Exception:        # noqa: ignore
                        pass
                    else:
                        assert False, f'should raise error if NO_EXPLICIT_CAST: {repr(input_value)} to {target_type}'
                    transformer.no_explicit_cast = False
                if not no_data_loss:
                    transformer.no_data_loss = True
                    try:
                        transformer(input_value, target_type)
                    except Exception:       # noqa: ignore
                        pass
                    else:
                        assert False, f'should raise error if NO_DATA_LOSS: {repr(input_value)} to {target_type}'
                    transformer.no_data_loss = False

    # def test_basic(self):
    #     # from utilmeta.core.schema.rule import Rule
    #     from utilmeta.core.schema.types import NaturalInt
    #     assert NaturalInt(4) == 4
    #     with pytest.raises(exc.ParseError):
    #         NaturalInt(-3)

    def test_logical(self):
        import math
        assert math.isnan(types.NanFloat('NAN'))
        assert math.isnan(types.AbnormalFloat('NAN'))
        assert math.isinf(types.AbnormalFloat('inf'))
        assert math.isinf(types.InfinityFloat('-inf'))
        assert types.NormalFloat('3.3') == 3.3

        with pytest.raises(exc.ParseError):
            types.NanFloat('inf')

        with pytest.raises(exc.ParseError):
            types.InfinityFloat('nan')

        with pytest.raises(exc.ParseError):
            types.NanFloat(3)

        with pytest.raises(exc.ParseError):
            types.NormalFloat('inf')

        with pytest.raises(exc.ParseError):
            types.NormalFloat('nan')

        int_or_dt = types.PositiveInt | date
        assert int_or_dt(3) == 3
        assert int_or_dt(date(2000, 1, 1)) == date(2000, 1, 1)
        with pytest.raises(exc.ParseError):
            int_or_dt('a')

        int_or_none = types.PositiveInt | None
        assert int_or_none(1) == 1
        assert int_or_none(None) is None

        with pytest.raises(exc.ParseError):
            int_or_none('a')

        null_or_const = types.Null | 3 | True
        assert null_or_const(None) is None
        assert null_or_const(3) == 3
        assert null_or_const(True) is True
        assert null_or_const(1) is True

        with pytest.raises(exc.ParseError):
            null_or_const(False)

        with pytest.raises(exc.ParseError):
            null_or_const(2, __options__=Options(no_explicit_cast=True))

        int_or_list = types.NegativeInt | List[str]
        assert int_or_list(3) == ['3']
        assert int_or_list(-3) == -3
        assert int_or_list(['a']) == ['a']
        assert int_or_list([1]) == ['1']

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
            gt = 'a'
            lt = 't'

        class EStrB(Rule):
            ge = 'a'
            le = 't'
        
        class MStrB(Rule):
            ge = 'a'
            lt = 't'
            
        class ListB(Rule):
            gt = [1]
            lt = [10]

        class EListB(Rule):
            ge = [1]
            le = [10]
        
        class MListB(Rule):
            gt = [1]
            le = [10]

        with pytest.raises(ValueError):
            class IntV(Rule):
                gt = 3
                lt = 2

        with pytest.raises(ValueError):
            class IntV(Rule):       # noqa
                gt = 3
                ge = 3

        with pytest.raises(ValueError):
            class IntV(Rule):       # noqa
                gt = 3
                ge = 2

        with pytest.raises(ValueError):
            class IntV(Rule):       # noqa
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

    def test_max_digits(self):
        class MaxFloat(types.Float):
            max_digits = 3

        assert MaxFloat(b'33.123') == 33.123
        assert MaxFloat('-133.123') == -133.123

        with pytest.raises(exc.ConstraintError):
            MaxFloat('3311.123')

        with pytest.raises(exc.ConstraintError):
            MaxFloat(-3311.123)

    def test_multiple_of(self):
        class MulInt(types.Int):
            multiple_of = 3

        assert MulInt(9) == 9
        assert MulInt(b'30.3') == 30
        assert MulInt('-33') == -33

        with pytest.raises(exc.ConstraintError):
            MulInt(b'2.2')

        with pytest.raises(exc.ConstraintError):
            MulInt(32)

        class LooseMulInt(types.Int):
            strict = False
            multiple_of = 3

        assert LooseMulInt('31.1') == 30

    def test_round(self):
        def make_round(r):
            class F(types.Float):
                round = r
            return F

        assert make_round(2)(1.2) == round(1.2, 2)  # noqa
        assert make_round(1)(1.24) == round(1.24, 1)  # noqa
        assert make_round(0)("1.245") == round(1.245, 0)  # noqa
        assert make_round(-1)("31.245") == round(31.245, -1)  # noqa

    def test_contains(self):
        class IntArray(list, types.Array):
            contains = types.PositiveInt
            max_contains = 3
            min_contains = 1

        assert IntArray([1, 2, 3]) == [1, 2, 3]
        assert IntArray([1, 2, -1, 'a', 'b']) == [1, 2, -1, 'a', 'b']
        assert IntArray(['1', True, b'2.3'])

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray([-1])

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray([1, 2, 3, 4, 'a'])

        with pytest.raises(exc.ConstraintError):
            # NO EXPLICITLY POSITIVE INT
            IntArray(['1', -3, b'2.3'], __options__=Options(no_explicit_cast=True))

        int_array = IntArray[int]
        assert int_array(['1', -3, b'2.3']) == [1, -3, 2]

    def test_unique_items(self):
        class UniqueArray(list, types.Array):
            unique_items = True

        assert UniqueArray([1, 2, 3]) == [1, 2, 3]
        assert UniqueArray((1, '1', b'1')) == [1, '1', b'1']

        with pytest.raises(exc.ConstraintError):
            assert UniqueArray((1, 1, 2))

        int_unique_array = UniqueArray[int]
        assert int_unique_array([1, '2', b'3']) == [1, 2, 3]
        with pytest.raises(exc.ConstraintError):
            int_unique_array((1, '1', b'1'))

    # def test_excludes(self):
    #     rule = Rule(excludes=0)
    #     assert rule(1) == 1
    #     with pytest.raises(ValueError):
    #         rule(0)
    #     rule = Rule(template=[int], excludes=[1, 4])
    #     assert rule(["2", "5"]) == [2, 5]
    #     assert rule(3) == [3]
    #     with pytest.raises(ValueError):
    #         rule([1])
    #     rule_ = Rule(template=[int], excludes=[1, 2], strict=False)
    #     assert rule_([1, 4]) == [4]

    def test_enum_const(self):
        class Const(Rule):
            const = 1

        class IntConst(int, Rule):
            const = 1

        class LooseConst(Rule):
            const = 1
            strict = False

        assert Const(1) == 1
        assert IntConst(True) == 1
        assert LooseConst(True) == 1
        assert IntConst('1') == 1

        with pytest.raises(exc.ParseError):
            Const(2)

        with pytest.raises(exc.ParseError):
            Const(True)

        with pytest.raises(exc.ParseError):
            Const('1')

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

        assert array_enum("INFO") == ('INFO',)
        assert array_enum(["INFO", 'ERROR']) == ('INFO', 'ERROR')
        assert unique_array_enum(["INFO", 'ERROR']) == ['INFO', 'ERROR']

        with pytest.raises(exc.ParseError):
            array_enum(["A", "E"])

        with pytest.raises(exc.ParseError):
            array_enum('WRONG')

        with pytest.raises(exc.ParseError):
            # unique
            unique_array_enum(["INFO", 'INFO', 'ERROR'])

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
            EnumRule2('BLUE')

        assert set_enum([Color.RED, Color.BLUE.value]) == {Color.RED.value, Color.BLUE.value}

    def test_regex(self):
        class Reg(Rule):
            regex = "([A-Za-z0-9]+)"
        assert Reg("abcABC123") == "abcABC123"
        with pytest.raises(exc.ConstraintError):
            Reg("abc@123")

    def test_args(self):
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

        class UniqueTuple(tuple, types.Array):
            unique_items = True

        assert UniqueIntArray([-1, '2', True]) == [-1, 2, 1]

        with pytest.raises(exc.ConstraintError):
            UniqueIntArray([-1, 2])

        with pytest.raises(exc.ConstraintError):
            UniqueIntArray([-1, 2, '3', True, 5])

        with pytest.raises(exc.ConstraintError):
            # not unique
            UniqueIntArray([1, '2', True])

        dict_type = SingleItemDict[types.SlugStr, types.NaturalInt | None]
        tup_str = UniqueTuple[types.SlugStr, types.NegativeInt, types.AbnormalFloat]
        tup_eli = UniqueTuple[types.PositiveInt | None, ...]

        assert tup_str([1, '-5', '-infinity']) == ('1', -5, float('-inf'))

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, '-5'])

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, '-5', '-infinity', 1], __options__=Options(no_data_loss=True))

        with pytest.raises(exc.ParseError):
            # absence
            tup_str([1, '-5', 3])

        with pytest.raises(exc.ParseError):
            # absence
            tup_str(['@', -5, 'nan'])

        assert tup_eli([1, 2, None]) == (1, 2, None)
        assert tup_eli([1, b'3', 'nil']) == (1, 3, None)

        with pytest.raises(exc.ParseError):
            tup_eli([-1, None])

        with pytest.raises(exc.ParseError):
            # not unique
            tup_eli([1, 1, None])

        assert dict_type({123: 3}) == {'123': 3}
        assert dict_type({'ab': 'null'}) == {'ab': None}

        with pytest.raises(exc.ParseError):
            # length > 1
            dict_type({123: 3, 'ab': None})

        with pytest.raises(exc.ParseError):
            # length < 1
            dict_type({})

        with pytest.raises(exc.ParseError):
            dict_type({'@': 3})

        with pytest.raises(exc.ParseError):
            dict_type({'A': -1})

        with pytest.raises(exc.ParseError):
            dict_type({'A': 'a'})

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
