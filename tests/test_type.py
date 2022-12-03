import utype
import pytest
from utype import Rule, Options, exc
from utype.utils.transform import TypeTransformer, register_transformer, DateFormat
from utype import types
import uuid
import pytest
from typing import List, Iterator, Iterable
from datetime import datetime, date, timedelta, time, timezone
from uuid import UUID
from decimal import Decimal
from enum import Enum
from collections.abc import Mapping


class TestType:
    def test_transform(self):
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
            a, b = str(d).split(",")
            return t(int(a) * int(b))

        assert_map = {
            type(None): [
                (None, None, True, True),
                ("None", None, False, True),
                ("null", None, False, True),
                ("nil", None, False, True),
            ],
            str: [
                (123, "123", False, True),
                (["a"], "a", False, True),
                (["a", "b"], "a", False, False),
                ({"a": 1}, repr({"a": 1}), False, True),
                (b"std", "std", True, True),
                (True, "True", False, True),
                ([], "[]", False, True),
                (["a"], "a", False, True),
                (["a", "b"], "a", False, False),
                (en_z, "0", False, True),
                (
                    "测试1".encode("gbk"),
                    "1",
                    True,
                    False,
                ),  # data loss, use "ignore" on byte errors
            ],
            SubStr: [
                ("123", SubStr("123"), True, True),
                (123, SubStr("123"), False, True),
                (["a"], SubStr("a"), False, True),
                (True, SubStr("True"), False, True),
                (en_z, SubStr("0"), False, True),
                (
                    "测试1".encode("gbk"),
                    SubStr("1"),
                    True,
                    False,
                ),  # data loss, use "ignore" on byte errors
            ],
            bytes: [
                (123, b"123", False, True),
                (["a"], b"a", False, True),
                ([b"a", b"b"], b"a", False, False),
                ({"a": 1}, repr({"a": 1}).encode(), False, True),
                (True, b"True", False, True),
                (bytearray(b"123"), b"123", True, True),
                (memoryview(b"123"), b"123", True, True),
                ("123", b"123", True, True),
                (en_z, b"0", False, True),
            ],
            SubBytes: [
                (b"123", SubBytes(b"123"), True, True),
                (123, SubBytes(b"123"), False, True),
                (True, SubBytes(b"True"), False, True),
                (bytearray(b"123"), SubBytes(b"123"), True, True),
                (memoryview(b"123"), SubBytes(b"123"), True, True),
                ("123", SubBytes(b"123"), True, True),
                (en_z, SubBytes(b"0"), False, True),
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
                (en_z, 0, True, True),  # this enum instance is an instance of int
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
                ("2,3", MyNumber(6), True, True),
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
                (en_a, 1.0, True, True),
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
                (
                    "123",
                    Decimal("123"),
                    True,
                    True,
                ),  # str is not consider explicit type cast for decimal
                ("10.1", Decimal("10.1"), True, True),
                ("10.100", Decimal("10.100"), True, True),
                (b"-0.3", Decimal("-0.3"), True, True),
                ("-1.24", Decimal("-1.24"), True, True),
                ("inf", Decimal("inf"), True, True),
                (timedelta(hours=1, milliseconds=200), Decimal("3600.2"), False, True),
                (en_z, Decimal("0"), False, True),
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
                (en_z, False, True, True),  # <NumEnum.z: 0> == 0 : True
                (en_a, True, True, True),
            ],
            datetime: [
                          (
                              dt.strftime(fmt),
                              dt.replace(tzinfo=timezone.utc)
                              if (fmt.endswith("GMT") or (fmt.endswith("Z") and "T" in fmt))
                              else dt,
                              True,
                              True,
                          )
                          for k, fmt in DateFormat.__dict__.items()
                          if k.startswith("DATETIME")
                      ]
                      + [
                          ("2022-01-02", datetime(2022, 1, 2), True, True),
                          # ('10:20:30', datetime(1900, 1, 1, 10, 20, 30), True, True),       # no standard behaviour
                          (dt.date(), datetime(2022, 1, 2), True, True),
                          (dt.timestamp(), dt.replace(tzinfo=timezone.utc), True, True),
                          (int(dt.timestamp()), dt.replace(tzinfo=timezone.utc), True, True),
                          # str / bytes timestamp to datetime in consider explicit cast
                          # this behaviour leave to further discussion
                          (
                              str(dt.timestamp() * 1000),
                              dt.replace(tzinfo=timezone.utc),
                              False,
                              True,
                          ),
                          (
                              str(dt.timestamp() * 1000).encode(),
                              dt.replace(tzinfo=timezone.utc),
                              False,
                              True,
                          ),
                      ],
            timedelta: [
                (0, timedelta(seconds=0), True, True),
                (10, timedelta(seconds=10), True, True),
                # "0" still match the Duration regex, does not consider an explicit cast
                # this behaviour leave to further discussion
                ("0", timedelta(seconds=0), True, True),
                ("-10.1", timedelta(seconds=-10.1), True, True),
                (b"-10.1", timedelta(seconds=-10.1), True, True),
                ("P1DT00H00M00S", timedelta(days=1), True, True),
                (b"P1DT00H00M00S", timedelta(days=1), True, True),
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
                (
                    0x12345678123456781234567812345678,
                    UUID("12345678-1234-5678-1234-567812345678"),
                    False,
                    True,
                ),
                (12.3456, UUID("00000000-0000-0000-0000-00000000000c"), False, False),
            ],
            dict: [
                # (None, {}),
                # ("", {}),
                ("{}", {}, False, True),
                ('{"a": true, "b": null}', {"a": True, "b": None}, False, True),
                ("{1: 2}", {1: 2}, False, True),  # python syntax
                (b"{1: 2}", {1: 2}, False, True),
                (b'{"a": 1}', {"a": 1}, False, True),
                (
                    "k1=v1&k2=v2",
                    {"k1": ["v1"], "k2": ["v2"]},
                    False,
                    True,
                ),  # querystring syntax
                ("k1=v1;k2=v2", {"k1": "v1", "k2": "v2"}, False, True),  # cookie syntax
                (
                    "k1=v1; k2=v2; k3=v3",
                    {"k1": "v1", "k2": "v2", "k3": "v3"},
                    False,
                    True,
                ),  # cookie syntax
                (
                    "k1=v1, k2=v2, k3=v3",
                    {"k1": "v1", "k2": "v2", "k3": "v3"},
                    False,
                    True,
                ),
                (
                    [("a", 1), ("b", 2)],
                    {"a": 1, "b": 2},
                    False,
                    True,
                ),  # list of tuple can directly pass dict(...)
                ([["a", 1], ["b", 2]], {"a": 1, "b": 2}, False, True),
                ({("a", 1), ("b", 2)}, {"a": 1, "b": 2}, False, True),
                ([{"a": 1}], {"a": 1}, False, True),
                ([{"a": 1}, {"b": 2}], {"a": 1}, False, False),
                (MyMapping({1: 2}), {1: 2}, True, True),
            ],
            MyMapping: [
                ({1: 2}, MyMapping({1: 2}), True, True),  # python syntax
                ("{1: 2}", MyMapping({1: 2}), False, True),  # python syntax
                (
                    '{"a": true, "b": null}',
                    MyMapping({"a": True, "b": None}),
                    False,
                    True,
                ),
                (
                    "k1=v1&k2=v2",
                    MyMapping({"k1": ["v1"], "k2": ["v2"]}),
                    False,
                    True,
                ),  # querystring syntax
                ([("a", 1), ("b", 2)], MyMapping({"a": 1, "b": 2}), False, True),
                # list of tuple can directly pass dict(...)
            ],
            list: [
                ((1, 2), [1, 2], True, True),
                ({"a": 1, "b": 2}, [{"a": 1, "b": 2}], False, True),
                ("[1,2]", [1, 2], False, True),
                ("(1,2)", [1, 2], False, True),
                ("1,2", ["1", "2"], False, True),
                (b"(1,2)", [1, 2], False, True),
                ("[]", [], False, True),
                (
                    "{}",
                    [],
                    False,
                    True,
                ),  # if dict is empty, directly convert to empty list
                (
                    "{1:2}",
                    [{1: 2}],
                    False,
                    True,
                ),  # otherwise, do not reduce information
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
                ("1,2", MyIterable(["1", "2"]), False, True),
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
                ("0", en_z, False, True),
                (1, en_a, True, True),
                ("a", en_a, False, False),
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
                    no_explicit_cast=no_explicit_cast, no_data_loss=no_data_loss
                ).make_runtime(force_error=True)
                transformer = TypeTransformer(options)
                try:
                    result = transformer(input_value, target_type)
                except Exception as e:
                    assert (
                        False
                    ), f"{target_type}: transform failed for input: {repr(input_value)}: {e}"

                assert result == output_value, (
                    f"{target_type}: wrong output for {repr(input_value)}: "
                    f"{repr(result)} ({repr(output_value)} expected)"
                )

                # True == 1
                # False == 0
                assert type(result) == type(output_value), (
                    f"{target_type}: wrong type for {repr(input_value)}: "
                    f"{repr(result)} ({repr(output_value)}"
                    f" ({type(output_value)}) expected)"
                )

                if not no_explicit_cast:
                    transformer.no_explicit_cast = True
                    try:
                        transformer(input_value, target_type)
                    except Exception:  # noqa: ignore
                        pass
                    else:
                        assert (
                            False
                        ), f"should raise error if NO_EXPLICIT_CAST: {repr(input_value)} to {target_type}"
                    transformer.no_explicit_cast = False
                if not no_data_loss:
                    transformer.no_data_loss = True
                    try:
                        transformer(input_value, target_type)
                    except Exception:  # noqa: ignore
                        pass
                    else:
                        assert (
                            False
                        ), f"should raise error if NO_DATA_LOSS: {repr(input_value)} to {target_type}"
                    transformer.no_data_loss = False

    def test_register(self):
        pass

    def test_encode(self):
        pass

    def test_apply(self):
        @utype.apply(gt=0, le=12)
        class Month(int):
            @utype.parse
            def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int:
                from calendar import monthrange
                return monthrange(year, self)[1]

        @utype.register_transformer(Month)
        def to_month(trans, data, t):
            if isinstance(data, date):
                return data.month
            return trans(data, t)

        mon = Month(date(2022, 2, 2))
        assert int(mon) == 2
        mon = Month(b'3')
        assert mon.get_days(year=b'2000')
