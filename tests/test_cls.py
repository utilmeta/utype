import typing
import utype
from utype import Rule, Options, exc, Field, Schema, register_transformer
from utype import types
from typing import List, Dict, Tuple, Union, Set, Optional, Type, Any
from datetime import datetime, date, timedelta, time, timezone
from uuid import UUID
from decimal import Decimal
from enum import Enum
from collections.abc import Mapping
import json
import pytest  # noqa


# must be module-level, otherwise cannot resolve by globals
class Self(Schema):
    name: str
    to_self: "Self" = Field(required=False)
    self_lst: List["Self"] = Field(default_factory=list)


class TestClass:
    def test_init(self):
        class Slug(str, Rule):
            regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"

        @register_transformer(Slug)
        def to_slug(transformer, value: str, t: Type[Slug]):
            str_value = transformer(value, str)
            return t(
                "-".join(
                    ["".join(filter(str.isalnum, v)) for v in str_value.split()]
                ).lower()
            )

        class ArticleSchema(Schema):
            slug: Slug

        assert dict(ArticleSchema(slug=b"My Awesome Article!")) == {
            "slug": "my-awesome-article"
        }

    def test_apply(self):
        pass
        # TODO
        # @utype.apply(gt=0, le=12)
        # class Month(int):
        #     @utype.parse
        #     def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int:
        #         from calendar import monthrange
        #         return monthrange(year, self)[1]
        #
        # @utype.register_transformer(Month)
        # def to_month(trans, data, t):
        #     if isinstance(data, date):
        #         return data.month
        #     return trans(data, t)
        #
        # mon = Month(date(2022, 2, 2))
        # assert int(mon) == 2
        # mon = Month(b'3')
        # assert mon.get_days(year=b'2000')

    def test_dataclass(self):
        @utype.dataclass
        class DataClass:
            name: str = Field(max_length=10)
            age: int

        dt = DataClass(name=b"test", age="2")
        assert dt.name == "test"
        assert dt.age == 2

        @utype.dataclass(
            set_properties=True,
            allow_runtime=True,
            init_super=True,
        )
        class DataClass(dict):
            name: str = Field(max_length=10)
            age: int

    def test_setup(self):
        class CustomType:
            def __init__(self, val):
                self.val = val
                self.str_val = str(val)

        class TestSchemaBase(Schema):
            # test common types
            int_val: int
            str_val: str
            bytes_val: bytes
            float_val: float
            bool_val: bool
            uuid_val: UUID
            custom_val: CustomType

            dt_val: datetime = Field(default_factory=datetime.now)
            null_val: Optional[str] = Field(length=6, on_error="exclude")
            d_val: date = Field(required=False)
            # test nest types
            list_val: List[str] = Field(default_factory=list)  # test callable default
            dict_val: Dict[str, int]
            dict_val2: Dict[int, List[float]]
            dict_val3: Dict[Tuple[int, str], bool]
            union_val: Union[str, List[int]]
            tuple_val: Tuple[str, int, bool]
            set_val: Set[str]

        class AliasSchema(Schema):
            # test alias
            seg_key: str = Field(alias="__key__")  # case __
            item_list: List[int] = Field(alias="items")  # case dict property
            at_param: int = Field(alias="@param")  # case invalid identifier
            multi_alias_key: str = Field(
                alias_from=["alias1", "alias2", "alias3"], alias="@alias"
            )

        class TestSchema(TestSchemaBase, AliasSchema):  # test multi inherit
            class IsolateSchema(Schema):
                key1: int
                key2: str

            isolate_val: IsolateSchema
            isolate_val2: List[IsolateSchema]
            isolate_val3: Optional[IsolateSchema]

            class inner(Schema):
                key1: int
                key2: str

            inner2: inner
            inner3: Dict[str, inner]

            @property
            def prop1(self) -> str:  # test property
                return self.seg_key + self.multi_alias_key  # test alias refer

            @prop1.setter
            def prop1(self, val: str):
                self.seg_key, self.multi_alias_key = val.split("/")

            def method1(self, val: str):
                self.null_val = "123456"
                self.int_val = val  # noqa

            @classmethod
            def cls_validator(cls, val: str):
                return cls.__name__ == val

            @staticmethod
            def static_method(param: str):
                pass

    def test_forward_ref(self):
        class T(Schema):
            __options__ = Options(ignore_required=True)

            forward_con: "types.Second" = Field(ge=30)
            with_con: types.Str | None = Field(max_length=5)
            int_or_list: types.NegativeInt | "List[types.PositiveInt]"
            one_of_int_list: types.NegativeInt ^ List["types.PositiveInt"]
            forward_in_args: List["types.PositiveInt"] = Field(
                max_length=3
            )  # test forward ref
            forward_in_dict: Dict[
                types.PositiveInt | "types.EmailStr", List["types.PositiveInt"]
            ] = Field(length=1)
            # union type with constraints

        assert dict(
            T(
                forward_con=31,
                with_con=None,
                int_or_list="2,3",
                forward_in_args=["1", b"2.4"],
                forward_in_dict=b'{"a@b23.com": [1, 2, "3"]}',
            )
        ) == dict(
            forward_con=31,
            with_con=None,
            int_or_list=[2, 3],
            forward_in_args=[1, 2],
            forward_in_dict={"a@b23.com": [1, 2, 3]},
        )

        with pytest.raises(exc.ParseError):
            T(
                forward_con=61,
            )

        with pytest.raises(exc.ParseError):
            T(
                with_con="*" * 10,
            )

        with pytest.raises(exc.ParseError):
            T(
                int_or_list="abc",
            )

        with pytest.raises(exc.ParseError):
            T(forward_in_args=[1, 2, 3, 4])
        with pytest.raises(exc.ParseError):
            T(forward_in_dict={1: [2], 2: [1]})

        sf = Self(name=1, to_self=b'{"name":"test"}')
        assert sf.to_self.name == "test"
        assert sf.self_lst == []

        sf2 = Self(name="t2", self_lst=[dict(sf)])
        assert sf2.self_lst[0].name == "1"
        assert "to_self" not in sf2

        # class ForwardSchema(Schema):
        #     int1: 'types.PositiveInt' = Field(lt=10)
        #     int2: 'types.PositiveInt' = Field(lt=20)
        #     l_int: List['types.PositiveInt'] = Field(length=5)
        #     l_int_f: 'List[types.PositiveInt]' = Field(max_length=3)

    def test_class_vars(self):
        def outer(k):
            return k

        class TestSchema(Schema):
            r1: typing.Any
            r2: "str"
            r3: None
            r4 = ""

            def r5(self):
                pass

            @classmethod
            def r6(cls):
                pass

            @staticmethod
            def r7():
                pass

            r8 = outer
            r9: type(None) = Field(alias_from=["_r9", "r9_"])

            class r10:
                pass

            class r11(Schema):
                a: str

            r12: r11

            _r13: float

            @property
            def r13(self) -> int:
                return int(self._r13)

            @r13.setter
            @Field(alias_from=["r13_alias"], default="1.5")
            def r13(self, value: str):
                self._r13 = float(value)

        with pytest.raises(Exception):

            class s(Schema):
                update: str = ""

    def test_functional_initialize_and_aliases(self):
        # test omit init
        class OmitSchema(Schema):
            n0: int
            n1: int
            n2: Any = Field(alias_from=["named_n2"])

            def __init__(
                self,
                alias_n0: int = 0,
                /,
                alias_n1: int = Field(
                    alias_from=["n1", "_n1"], default_factory=lambda: 1
                ),
                *,  # pos or kw
                named_n2: int = Field(alias="@n2"),
            ):  # kw only
                super().__init__(n0=alias_n0, n1=alias_n1, named_n2=named_n2)

        o0 = OmitSchema(named_n2=1)
        o1 = OmitSchema(1, _n1="2", **{"@n2": 2.5})
        o2 = OmitSchema(0, 3, **{"@n2": "2"})

        assert o0.n0 == 0
        assert o0.n1 == 1
        assert o0.n2 == 1
        assert o1.n0 == 1
        assert o1.n1 == 2
        assert o1.n2 == 2
        assert o2.n0 == 0
        assert o2.n1 == 3
        assert o2.n2 == 2  # int does the type cast

    def test_schema_rule(self):
        # require / default / omit / null
        class RuleSchema(Schema):
            required1: str
            required2: int = Field(required=True)
            default1: str = "default"
            default2: int = Field(le=5, default=3)
            omit: int = Field(gt=5, required=False)
            null1: Optional[int] = Field(max_digits=5)
            null_default1: Optional[int] = Field(max_digits=5, default=0)

        data1 = {
            "required1": "0",
            "required2": "1",
            "default2": 5,
            "null1": "12345",
            "null_default1": None,
        }
        rsc = RuleSchema(**data1)
        assert rsc.required2 == 1
        assert rsc.null_default1 is None
        assert rsc.default1 == "default"
        with pytest.raises(KeyError):
            _ = rsc["omit"]

        i_data1 = {
            # 'required1': '0',
            "required2": "1",
            "null1": "12345",
        }
        with pytest.raises(exc.ParseError):
            RuleSchema(**i_data1)

        i_data2 = {
            "required1": "0",
            # 'required2': '1',
            "null1": "12345",
        }
        with pytest.raises(exc.ParseError):
            RuleSchema(**i_data2)

        i_data3 = {
            "required1": "0",
            "required2": "1",
            # 'null1': '12345',
        }
        with pytest.raises(exc.ParseError):
            RuleSchema(**i_data3)

    def test_aliased_type(self):
        class AliasTypeSchema(Schema):
            dict1: Dict[typing.AnyStr, typing.List]
            list2: Tuple[Dict, List, Set]

        # not encouraged but still support
        assert dict(
            AliasTypeSchema(dict1={1: 3, 2: 4}, list2=['{"a": 1}', (), ()])
        ) == dict(
            # this behaviour might change in the future
            dict1={b"1": [3], b"2": [4]},
            list2=({"a": 1}, [], set()),
        )

    def test_dict_type(self):
        class MyStr(str, Rule):
            length = 3

        class Const1(str, Rule):
            const = "1"

        class DictSchema(Schema):
            dict1: Dict[Tuple[str, int], int]
            dict2: Dict[MyStr, int]
            dict_nested: Dict[str, Dict[int, List[int]]]
            rule_dict: Dict[int, Const1] = Field(default_factory=dict)

        da = DictSchema(
            **{
                "dict1": {(1, 1): 1, (1, 2): 2},
                "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                "dict_nested": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                "rule_dict": [{"1": "1", 2: "1", 3: 1}],
            }
        )

        assert da.dict1 == {("1", 1): 1, ("1", 2): 2}
        assert da.dict2 == {"qwe": 0, "abc": -10}
        assert da.dict_nested == {"1": {2: [1, 2], 3: [4]}, "2": {}}
        assert da.rule_dict == {1: "1", 2: "1", 3: "1"}

        with pytest.raises(exc.ParseError):
            DictSchema(
                **{
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"1234": 0}),  # exceed length
                    "dict3": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                **{
                    "dict1": {(1, 1, 2): 1, (1,): 2},  # tuple length
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict3": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                **{
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict3": str(
                        [{1: {"abc": ["1", 2], 3: 4}, 2: {}}]
                    ),  # cannot convert int
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                **{
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict_nested": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                    "rule_dict": [{"1": "2", 2: "1"}],  # mismatch rule
                }
            )

    def test_union_optional(self):
        class UnionSchema(Schema):
            opt: Optional[int] = Field(gt=3)
            union: Union[Dict[str, int], int]

        class UnionSchema2(Schema):
            opt: Optional[int]
            union: Union[Dict[str, int], int]

        u1 = UnionSchema(opt=None, union=3)
        assert u1.opt is None
        assert u1.union == 3

        u2 = UnionSchema(opt=5, union={1: "2"})
        assert u2.opt == 5
        assert u2.union == {"1": 2}

        u3 = UnionSchema(opt=5, union=[1])
        assert u3.union == 1

        with pytest.raises(exc.ParseError):
            UnionSchema(opt=5, union={"a": "b"})  # cannot convert to Dict[str, int]

    def test_property(self):
        class UserSchema(Schema):
            name: str
            level: int = 0

            @property
            def label(self):
                return f"{self.name}<{self.level}>"

        assert UserSchema(name="Bob", level=3).label == "Bob<3>"

    # def test_nested_schema(self):
    #     class UserSchema(Schema):
    #         name: str
    #         level: int = 0
    #
    #         class key_info(Schema):
    #             access_key: str
    #             last_activity: datetime = Field(default_factory=datetime.now)
    #
    #     assert (
    #         UserSchema(
    #             {"name": "Joe", "key_info": {"access_key": "KEY"}}
    #         ).key_info.access_key
    #         == "KEY"
    #     )
    #
    #     class UserSchema2(Schema):
    #         name: str
    #         level: int = 0
    #
    #         class KeyInfo(Schema):
    #             access_key: str
    #             last_activity: datetime = Field(default_factory=datetime.now)
    #
    #         access_keys: List[KeyInfo]
    #
    #     assert "KeyInfo" not in UserSchema2.__template__  # isolate
    #     assert (
    #         UserSchema2(**{"name": "Joe", "access_keys": {"access_key": "KEY"}})
    #         .access_keys[0]
    #         .access_key
    #         == "KEY"
    #     )

    # def test_invalid_schema(self):
    #     with pytest.raises(AttributeError):
    #         class InvalidSchema(Schema):  # noqa
    #             items: int
    #
    # def test_schema_options(self):
    #     class UserSchemaDisallow(Schema):
    #         __options__ = Schema.Options(allow_excess=False)
    #         name: str
    #         level: int = 0
    #
    #     assert dict(UserSchemaDisallow(name="Test")) == {"name": "Test", "level": 0}
    #
    #     with pytest.raises(exc.ExcessError):
    #         UserSchemaDisallow(name="Test", code="XYZ")
    #
    #     class UserSchemaPreserve(Schema):
    #         __options__ = Schema.Options(excess_preserve=True)
    #         name: str
    #         level: int = 0
    #
    #     assert dict(UserSchemaPreserve(name="Test", code="XYZ")) == {
    #         "name": "Test",
    #         "code": "XYZ",
    #         "level": 0,
    #     }
    #
    #     class UserSchemaIgnore(Schema):
    #         __options__ = Schema.Options(ignore_required=True)
    #         name: str
    #         level: int = 0
    #
    #     user = UserSchemaIgnore()
    #     assert dict(user) == {"level": 0}
    #     with pytest.raises(AttributeError):
    #         user.name  # noqa
    #
    #     class UserSchemaDisallowType(Schema):
    #         __options__ = Schema.Options(allow_type_transform=False)
    #         name: str
    #         level: int = 0
    #
    #     with pytest.raises(exc.ParseError):
    #         UserSchemaDisallowType(name=107, level="3")
    #
    #     class IndexSchema(Schema):
    #         indexes: List[int]
    #
    #     class IndexSchemaExclude(Schema):
    #         __options__ = Schema.Options(list_exclude_against=True)
    #         indexes: List[int]
    #
    #     with pytest.raises(exc.ParseError):
    #         IndexSchema(indexes=[1, 2, "ab"])
    #
    #     assert dict(IndexSchemaExclude(indexes=[1, 2, "ab"])) == {"indexes": [1, 2]}
    #
    #     class IndexSchemaPreserve(Schema):
    #         __options__ = Schema.Options(list_preserve_against=True)
    #         indexes: List[int]
    #
    #     assert dict(IndexSchemaPreserve(indexes=[1, 2, "ab"])) == {
    #         "indexes": [1, 2, "ab"]
    #     }
    #
    #     class NoDefaultSchema(Schema):
    #         __options__ = Schema.Options(no_default=True)
    #         default: str = "0"
    #
    #     with pytest.raises(AttributeError):
    #         _ = NoDefaultSchema().default
    #         # no default
    #         # 1. when parsing, default value will never be used to fill unprovided key
    #         # 2. when accessing missing attributes, it will throw AttributeError instead of give a default
    #
    #     class SubclassSchema(Schema):
    #         dt: date
    #
    #     class AllowSubclassSchema(Schema):
    #         __options__ = Schema.Options(allow_type_subclasses=True)
    #         dt: date
    #
    #     assert SubclassSchema(dt=datetime(2022, 1, 1, 12, 12, 12)).dt == date(2022, 1, 1)
    #     assert AllowSubclassSchema(dt=datetime(2022, 1, 1, 12, 12, 12)).dt == datetime(2022, 1, 1, 12, 12, 12)
    #
    #     class TypeOnlySchema(Schema):
    #         __options__ = Schema.Options(type_only=True)
    #         attr: str = Field(value='xxxx')
    #         lst: List[int] = Field(length=3)
    #
    #     assert dict(TypeOnlySchema(attr=3, lst='1,2,3,4')) == {'attr': '3', 'lst': [1, 2, 3, 4]}   # ignore other rules
    #
    #     # case styles
    #     class AllowCaseSchema(Schema):
    #         __options__ = Schema.Options(
    #             alias_from_generator=[
    #                 Schema.Options.CAMEL_CASE_GENERATOR,
    #                 Schema.Options.KEBAB_CASE_GENERATOR,
    #                 lambda x: "@" + x
    #             ],
    #             alias_for_generator=Schema.Options.CAP_KEBAB_CASE_GENERATOR,
    #         )
    #         attr_name: str
    #         CAP_ATTR_NAME: str
    #         fixed_name: str = Field(alias_from=['fix1', 'fix2'], alias='@fix')
    #
    #     attr_name_vars = ['attr_name', '@attr_name', 'attr-name', 'attrName', 'ATTR-NAME']
    #     cap_attr_name_vars = ['CAP_ATTR_NAME', '@CAP_ATTR_NAME', 'cap-attr-name', 'capAttrName', 'CAP-ATTR-NAME']
    #     fix_name_vars = ['fix1', 'fix2']    # override the Options config
    #
    #     for a1 in attr_name_vars:
    #         for a2 in cap_attr_name_vars:
    #             for f3 in fix_name_vars:
    #                 assert dict(AllowCaseSchema({a1: 'a1', a2: 'a2', f3: 'a3'})) \
    #                        == {'ATTR-NAME': 'a1', 'CAP-ATTR-NAME': 'a2', '@fix': 'a3'}
    #
    #     class ImmutableSchema(Schema):
    #         __options__ = Schema.Options(immutable=True)
    #         attr: str = ''
    #
    #     sc = ImmutableSchema(attr='x')
    #     with pytest.raises(AttributeError):
    #         sc.attr = 'y'
    #     with pytest.raises(AttributeError):
    #         del sc.attr
    #     with pytest.raises(AttributeError):
    #         sc['attr'] = 'y'
    #     with pytest.raises(AttributeError):
    #         sc.update(attr='y')
    #     with pytest.raises(AttributeError):
    #         sc.pop('attr')
    #     with pytest.raises(TypeError):
    #         sc.popitem()
    #     with pytest.raises(TypeError):
    #         sc.clear()
    #
    #     class InsensitiveSchema(Schema):
    #         __options__ = Schema.Options(case_insensitive=True)
    #         VALUE: int = 0
    #         attr: str
    #         other_name: bool = False
    #
    #     assert dict(InsensitiveSchema(value='3', Attr='x', OTHER_NAME=True)) == \
    #            {'VALUE': 3, 'attr': 'x', 'other_name': True}
    #     # attr ane key access of case_insensitive schema will also support case_insensitive access
    #
    #     with pytest.raises(AttributeError):
    #         class InsensitiveSchemaInvalid1(Schema):
    #             __options__ = Schema.Options(case_insensitive=True)
    #             VALUE: int = 0
    #             value: int
    #             # name is same
    #
    #     with pytest.raises(AttributeError):
    #         class InsensitiveSchemaInvalid2(Schema):
    #             __options__ = Schema.Options(case_insensitive=True)
    #             val1: int = Field(alias_from=['VALUE'])
    #             value: str
    #             # name is same
    #
    #     # class CommonSchema(Schema):
    #     #     __options__ = Schema.Options(exact_attribute_access=False)
    #     #     attr: str = Field(alias='attr_for', alias_from=['attr_from'])
    #     #
    #     # class ExactSchema(Schema):
    #     #     __options__ = Schema.Options(exact_attribute_access=True)
    #     #     attr: str = Field(alias='attr_for', alias_from=['attr_from'])
    #     #
    #     # assert CommonSchema(attr_from='x').attr_for == 'x'
    #     # assert CommonSchema(attr_from='x').attr == 'x'
    #     # assert CommonSchema(attr_from='x').attr_from == 'x'
    #     # assert ExactSchema(attr_from='x').attr == 'x'
    #
    #     # with pytest.raises(AttributeError):
    #     #     assert ExactSchema(attr_for='x').attr_for
    #     # with pytest.raises(AttributeError):
    #     #     assert ExactSchema(attr_from='x').attr_from
    #
    #     class IgnoreDiscardSchema(Schema):
    #         __options__ = Schema.Options(ignore_discard=["v1"])
    #         v1: str = Field(discard=True)
    #         v2: str = Field(discard=True)
    #         v3: str = "x"
    #
    #     assert dict(IgnoreDiscardSchema(v1='x', v2='y', v3='z')) == {'v1': 'x', 'v3': 'z'}
    #
    #     class BestEffortSchema(Schema):
    #         __options__ = Schema.Options(best_effort_transform=True)
    #         attr: int = Field(value=10)
    #         tp: int
    #
    #     assert dict(BestEffortSchema(attr=3, tp='xx')) == {'attr': 3, 'tp': 'xx'}
    #     assert dict(BestEffortSchema(attr=3, tp='33')) == {'attr': 3, 'tp': 33}
    #
    #     # test options in data
    #     class v(Schema):
    #         value: int
    #
    #     data = {"__options__": Schema.Options(case_insensitive=True), "VALUE": '1'}
    #     assert v(**data).value == 1
    #
    #     data = {"__options__": Schema.Options(ignore_discard=True), "v1": 1, 'v2': 2}
    #     assert dict(IgnoreDiscardSchema(**data)) == {'v1': '1', 'v2': '2', 'v3': 'x'}
    #
    #     class UnprovidedSchema1(Schema):
    #         __options__ = Schema.Options(unprovided_attribute=KeyError)
    #         attr: str = Field(required=False)
    #
    #     with pytest.raises(KeyError):
    #         _ = UnprovidedSchema1().attr
    #
    #     class UnprovidedSchema2(Schema):
    #         __options__ = Schema.Options(unprovided_attribute=list)
    #         attr: str = Field(required=False)
    #
    #     assert UnprovidedSchema2().attr == []
    #
    #     class UnprovidedSchema2(Schema):
    #         __options__ = Schema.Options(unprovided_attribute=None)
    #         attr: str = Field(required=False)
    #
    #     assert UnprovidedSchema2().attr is None
    #
    #
    #     class ClassOptionsSchema(Schema):
    #         class __options__(Schema.Options):
    #             unprovided_attribute = None
    #             ignore_conflict = True
    #             ignore_required = True
