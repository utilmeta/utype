import typing

from utilmeta.types import *
from utilmeta.utils import *
from utilmeta.util import common
from utilmeta.core.schema import Schema, types, Field
import json
import pytest  # noqa


class TestSchemaClass:
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

            dt_val: datetime = Field(default=common.time_now)
            null_val: Optional[str] = Field(length=6, on_error='exclude')
            d_val: date = Field(required=False)
            # test nest types
            list_val: List[str] = Field(default=list)  # test callable default
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
                self.seg_key, self.multi_alias_key = val.split('/')

            def method1(self, val: str):
                self.null_val = "123456"
                self.int_val = val  # noqa

            @classmethod
            def cls_validator(cls, val: str):
                return cls.__name__ == val

            @staticmethod
            def static_method(param: str):
                pass

            def __validate__(self):
                self.method1("123")

        temp = dict(TestSchema.__parser__.fields)
        assert temp.get("prop1") is None
        assert temp.get("@alias") is not None

    def test_forward_ref(self):
        class T(Schema):
            with_con: types.Str | None = Field(max_length=5)
            int_or_list: types.NegativeInt | 'types.PositiveInt' = Field(max_digits=3)    # test forward ref
            forward_in_args: List['types.PositiveInt'] = Field(max_length=3)    # test forward ref
            forward_in_dict: Dict[types.PositiveInt | 'types.EmailStr', List['types.PositiveInt']] = Field(length=3)
            # union type with constraints

    def test_functional_initialize_and_aliases(self):
        class _AliasSchema(Schema):
            # test alias
            seg_key: str = Field(alias="__key__", default="0")  # case __
            item_list: List[int] = Field(
                alias="items", default=list
            )  # case dict property
            at_param: int = Field(alias="@param")  # case invalid identifier
            multi_alias_key: str = Field(
                alias_from=["alias1", "alias2", "alias3"], alias="@alias"
            )

        class AliasSchema(Schema):
            def __init__(
                self,
                seg_key: str = Field(alias="__key__", default="0"),
                item_list: List[int] = Field(alias="items", default=list),
                at_param: int = Field(alias="@param"),
                multi_alias_key: str = Field(
                    alias_from=["alias1", "alias2", "alias3"], alias="@alias"
                ),
            ):
                super().__init__(locals())

        class AliasSchemaKwargs(Schema):
            def __init__(
                self,
                seg_key: str = Field(alias="__key__", default="0"),
                item_list: List[int] = Field(alias="items", default=list),
                multi_alias_key: str = Field(
                    alias_from=["alias1", "alias2", "alias3"], alias="@alias"
                ),
                at_param: int = Field(alias="@param"),
                **kwargs: str,
            ):
                super().__init__(locals())

        # test template
        assert str(_AliasSchema.__template__) == str(AliasSchema.__template__)

        # test init
        inst0 = _AliasSchema(
            __key__=1, items="[1,3]", **{"@param": "-3.1", "@alias": {}}
        )
        inst1 = AliasSchema(
            __key__=1, items="[1,3]", **{"@param": "-3.1", "@alias": {}}
        )  # noqa
        inst2 = AliasSchema(
            seg_key=1, item_list="[1,3]", at_param=-3, multi_alias_key="{}"
        )  # noqa
        assert inst1 == inst2
        assert dict(inst0) == dict(inst1)
        # test idempotent

        # assert AliasSchema(json.dumps(inst2)) == inst2  # json str    aliased schema requires **
        assert _AliasSchema(json.dumps(inst0).encode()) == inst0  # json bytes

        # test inherit failing
        with pytest.raises(ValueError):
            # no **kwargs in AliasSchema __init__ and no __init__ in children schema
            class AliasChildrenFailed(AliasSchema):  # noqa
                a: int
                b: str

        class AliasChildren1(AliasSchemaKwargs):
            a: int
            b: str

        assert AliasChildren1(a=1, b=2, **inst1) == AliasChildren1(
            dict(**inst1, a=1, b=2)
        )  # noqa

        class AliasChildren2(AliasSchema):
            def __init__(self, a: int, b: str, **kwargs):
                # switch a and b to test init function is actually being called
                Schema.__init__(self, a=b, b=a, **kwargs)  # noqa

        class AliasChildren3(AliasSchemaKwargs):
            def __init__(self, a: int, b: str, **kwargs):
                # switch a and b to test init function is actually being called
                super().__init__(a=a + 2, b=b * 2, **kwargs)  # noqa

        child2 = AliasChildren2(**inst2, a=1, b=2)  # noqa
        assert child2.a == 2
        assert child2.b == "1"
        assert child2.seg_key == "1"

        child3 = AliasChildren3(**inst2, a=1, b=2)  # noqa
        assert child3.a == 3
        assert child3.b == "22"  # b is str, so b in __init__ is '2', b * 2 = '22'
        assert child3.seg_key == "1"

        # update
        inst0.seg_key = 15
        assert inst0["__key__"] == "15"
        inst0.update({"@param": 0.3, "item_list": 3})
        assert inst0["at_param"] == 0  # test attr key access
        assert inst0.item_list == [3]

        # deletion
        inst1.pop("seg_key")
        del inst1.item_list
        assert (
            inst1.item_list == []
        )  # default is provided, so access attribute will still get the default value
        assert set(inst1) == {"@alias", "@param"}

        with pytest.raises(KeyError):
            _ = inst1["__key__"]
            # but directly access to the missing key will throw KeyError
            # and default will not be used in this situation

        with pytest.raises(AttributeError):
            del inst1.at_param  # delete required

        class ConvertSchema(Schema):
            class Sub(Schema, isolate=True):
                val: str = Field(converter=lambda x: "_" + x)

            def __init__(self, sub: Sub, num: int = Field(converter=lambda x: x * x)):
                super().__init__(locals())

        ct = ConvertSchema(sub={"val": "x"}, num=3)  # noqa
        assert ct["sub"]["val"] == "_x"  # apply only once
        assert ct["num"] == 9

        # test omit init
        class OmitSchema(Schema):
            def __init__(
                self,
                alias_n0: int = Field(alias="@n0", required=False),
                /,
                alias_n1: int = Field(alias="@n1", required=False),
                *,  # pos or kw
                named_n2: int = Field(alias="@n2", required=False),
            ):  # kw only
                super().__init__(locals())

        _o = OmitSchema()
        o0 = OmitSchema(0)
        o1 = OmitSchema(0, 1)
        _o1 = OmitSchema(0, alias_n1=1)
        o2 = OmitSchema(0, 1, named_n2=2)

        assert "@n0" not in _o
        assert o0["@n0"] == 0
        assert "@n1" not in o0
        assert o1["@n0"] == 0
        assert o1["@n1"] == 1
        assert _o1["@n1"] == 1
        assert "@n2" not in o1
        assert o2["@n0"] == 0
        assert o2["@n1"] == 1
        assert o2["@n2"] == 2

    def test_forward_ref(self):
        def outer(k):
            return k

        class TestSchema(Schema):
            r1: Any
            r2: ''
            r3: None
            r4 = ''

            def r5(self):
                pass

            @classmethod
            def r6(cls):
                pass

            @staticmethod
            def r7():
                pass

            r8 = outer
            r9: type(None) = Field(alias_from=['_r9', 'r9_'])

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
            def r13(self, value: str = Field(alias_from=['r13_alias'], default='1.5')):
                self._r13 = float(value)

        with pytest.raises(Exception):
            class s(Schema):
                update: str = ''

        class ForwardSchema(Schema):
            int1: 'types.PositiveInt' = Field(lt=10)
            int2: 'types.PositiveInt' = Field(lt=20)
            l_int: List['types.PositiveInt'] = Field(length=5)
            l_int_f: 'List[types.PositiveInt]' = Field(max_length=3)

    def test_schema_rule(self):
        # require / default / omit / null
        class RuleSchema(Schema):
            required1: str
            required2: int = Field(required=True)
            default1: str = "default"
            default2: int = Field(le=5, default=3)
            omit: int = Field(gt=5, required=False)
            null1: str = Field(length=5, null=True)
            null_default1: int = Field(length=5, null=True, default=0)

        data1 = {
            "required1": "0",
            "required2": "1",
            "default2": 5,
            "null1": "12345",
            "null_default1": None,
        }
        rsc = RuleSchema(data1)
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
        assert dict(AliasTypeSchema(dict1={1: 3, 2: 4}, list2=['{"a": 1}', (), ()])) == dict(
            dict1={'1': [3], '2': [4]},
            list2=({"a": 1}, [], set())
        )

    def test_dict_type(self):
        class DictSchema(Schema):
            dict1: Dict[Tuple[str, int], int]
            dict2: Dict[Field(type=str, length=3), Field(type=int)]
            dict_nested: Dict[str, Dict[int, List[int]]]
            rule_dict: dict = Field(dict_type=(int, Field(value="1")), default=dict)

        da = DictSchema(
            {
                "dict1": {(1, 1): 1, (1, 2): 2},
                "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                "dict_nested": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                "rule_dict": [{"1": "1", 2: "1"}],
            }
        )

        assert da.dict1 == {("1", 1): 1, ("1", 2): 2}
        assert da.dict2 == {"qwe": 0, "abc": -10}
        assert da.dict_nested == {"1": {2: [1, 2], 3: [4]}, "2": {}}
        assert da.rule_dict == {1: "1", 2: "1"}

        with pytest.raises(exc.ParseError):
            DictSchema(
                {
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"1234": 0}),  # exceed length
                    "dict3": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                {
                    "dict1": {(1, 1, 2): 1, (1,): 2},  # tuple length
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict3": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                {
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict3": str(
                        [{1: {"abc": ["1", 2], 3: 4}, 2: {}}]
                    ),  # cannot convert int
                }
            )

        with pytest.raises(exc.ParseError):
            DictSchema(
                {
                    "dict1": {(1, 1): 1, (1, 2): 2},
                    "dict2": json.dumps({"qwe": "0.3", "abc": "-10"}),
                    "dict_nested": str([{1: {"2": ["1", 2], 3: 4}, 2: {}}]),
                    "rule_dict": [{"1": "2", 2: "1"}],  # mismatch rule
                }
            )

    def test_array_type(self):
        class ArraySchema(Schema):
            __options__ = Schema.Options(ignore_required=True)

            lst1: List[int]
            lst2: List[Tuple[str, int]]
            lst3: List[Dict[int, Tuple[int, bool]]]
            lst4: List[Field(type=str, length=4)]

            tp1: Tuple[Union[int, List[int]], List[Field(type=str, length=4)]]

            set1: Set[Field(type=str, length=4)]
            set2: Set[Union[Field(type=str, length=4), Field(type=int, lt=10)]]
            set3: Set[Tuple[int, bool, Field(type=str, length=4)]]

        da = ArraySchema(
            lst1=["1", 3, b"5"],
            lst2=["[1,2]", [3, 4]],
            lst3=b"{1:[1,0]}",
            lst4=["1234", 2345],
            tp1=[["1"], [1234]],
            set1="[1234, 2345]",
            set2=[1234, 3, "4", "2345"],
            set3=([1, 0, 1234], ["3", "", "xxxx"]),
        )

        assert da.lst1 == [1, 3, 5]
        assert da.lst2 == [("1", 2), ("3", 4)]
        assert da.lst3 == [{1: (1, False)}]
        assert da.lst4 == ["1234", "2345"]
        assert da.tp1 == ([1], ["1234"])
        assert da.set1 == {"1234", "2345"}
        assert da.set2 == {"1234", 3, 4, "2345"}
        assert da.set3 == {(1, False, "1234"), (3, False, "xxxx")}

        with pytest.raises(exc.ParseError):
            ArraySchema(lst2=['["a","b"]', [1, 2]])

        with pytest.raises(exc.ParseError):
            ArraySchema(lst3='{"3":["a",0]}')

        with pytest.raises(exc.ParseError):
            ArraySchema(set2=[123])

    def test_union_optional(self):
        class UnionSchema(Schema):
            opt: Optional[int] = Field(gt=3)
            union: Union[Dict[str, int], int]

        class UnionSchema2(Schema):
            opt: Optional[int] = Field(const=1)
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

        uu = UnionSchema | UnionSchema2

    def test_property(self):
        class UserSchema(Schema):
            name: str
            level: int = 0

            @property
            def label(self):
                return f"{self.name}<{self.level}>"

        assert UserSchema(name="Bob", level=3).label == "Bob<3>"

    def test_nested_schema(self):
        class UserSchema(Schema):
            name: str
            level: int = 0

            class key_info(Schema):
                access_key: str
                last_activity: datetime = Field(default=datetime.now)

        assert (
            UserSchema(
                {"name": "Joe", "key_info": {"access_key": "KEY"}}
            ).key_info.access_key
            == "KEY"
        )

        class UserSchema2(Schema):
            name: str
            level: int = 0

            class KeyInfo(Schema):
                access_key: str
                last_activity: datetime = Field(default=datetime.now)

            access_keys: List[KeyInfo]

        assert "KeyInfo" not in UserSchema2.__template__  # isolate
        assert (
            UserSchema2(**{"name": "Joe", "access_keys": {"access_key": "KEY"}})
            .access_keys[0]
            .access_key
            == "KEY"
        )

    def test_schema_init(self):
        class Test1(Schema):
            def __init__(self, a: int, **kwargs):
                a += 1
                super().__init__(locals())

        assert Test1.__options__.excess_preserve  # **kwargs
        assert dict(Test1(1, b=2)) == {"a": 2, "b": 2}  # test init logic

    def test_invalid_schema(self):
        with pytest.raises(AttributeError):

            class InvalidSchema(Schema):  # noqa
                items: int

        with pytest.raises(AttributeError):

            class InvalidSchema(Schema):  # noqa
                _seg_key1: str = Field(length=3)

        with pytest.raises(AttributeError):
            # conflict
            class InvalidSchema(Schema):  # noqa
                key1: str
                key2: int = Field(alias="key1")

        with pytest.raises(AttributeError):
            # conflict
            class InvalidSchema(Schema):  # noqa
                key1: str
                key2: int = Field(alias_from=["key1", "key3"])

        with pytest.raises(AttributeError):
            # conflict
            class InvalidSchema(Schema):  # noqa
                key1: str

                def __init__(self, key2: int = Field(alias_from="key1")):
                    super().__init__(locals())

        with pytest.raises(AttributeError):
            # conflict
            class BaseSchema(Schema):
                key1: str

            class InvalidSchema(BaseSchema):  # noqa
                def __init__(self, key2: int = Field(alias_from="key1")):
                    super().__init__(locals())

    def test_schema_options(self):
        class UserSchemaDisallow(Schema):
            __options__ = Schema.Options(allow_excess=False)
            name: str
            level: int = 0

        assert dict(UserSchemaDisallow(name="Test")) == {"name": "Test", "level": 0}

        with pytest.raises(exc.ExcessError):
            UserSchemaDisallow(name="Test", code="XYZ")

        class UserSchemaPreserve(Schema):
            __options__ = Schema.Options(excess_preserve=True)
            name: str
            level: int = 0

        assert dict(UserSchemaPreserve(name="Test", code="XYZ")) == {
            "name": "Test",
            "code": "XYZ",
            "level": 0,
        }

        class UserSchemaIgnore(Schema):
            __options__ = Schema.Options(ignore_required=True)
            name: str
            level: int = 0

        user = UserSchemaIgnore()
        assert dict(user) == {"level": 0}
        with pytest.raises(AttributeError):
            user.name  # noqa

        class UserSchemaDisallowType(Schema):
            __options__ = Schema.Options(allow_type_transform=False)
            name: str
            level: int = 0

        with pytest.raises(exc.ParseError):
            UserSchemaDisallowType(name=107, level="3")

        class IndexSchema(Schema):
            indexes: List[int]

        class IndexSchemaExclude(Schema):
            __options__ = Schema.Options(list_exclude_against=True)
            indexes: List[int]

        with pytest.raises(exc.ParseError):
            IndexSchema(indexes=[1, 2, "ab"])

        assert dict(IndexSchemaExclude(indexes=[1, 2, "ab"])) == {"indexes": [1, 2]}

        class IndexSchemaPreserve(Schema):
            __options__ = Schema.Options(list_preserve_against=True)
            indexes: List[int]

        assert dict(IndexSchemaPreserve(indexes=[1, 2, "ab"])) == {
            "indexes": [1, 2, "ab"]
        }

        class NoDefaultSchema(Schema):
            __options__ = Schema.Options(no_default=True)
            default: str = "0"

        with pytest.raises(AttributeError):
            _ = NoDefaultSchema().default
            # no default
            # 1. when parsing, default value will never be used to fill unprovided key
            # 2. when accessing missing attributes, it will throw AttributeError instead of give a default

        class SubclassSchema(Schema):
            dt: date

        class AllowSubclassSchema(Schema):
            __options__ = Schema.Options(allow_type_subclasses=True)
            dt: date

        assert SubclassSchema(dt=datetime(2022, 1, 1, 12, 12, 12)).dt == date(2022, 1, 1)
        assert AllowSubclassSchema(dt=datetime(2022, 1, 1, 12, 12, 12)).dt == datetime(2022, 1, 1, 12, 12, 12)

        class TypeOnlySchema(Schema):
            __options__ = Schema.Options(type_only=True)
            attr: str = Field(value='xxxx')
            lst: List[int] = Field(length=3)

        assert dict(TypeOnlySchema(attr=3, lst='1,2,3,4')) == {'attr': '3', 'lst': [1, 2, 3, 4]}   # ignore other rules

        # case styles
        class AllowCaseSchema(Schema):
            __options__ = Schema.Options(
                alias_from_generator=[
                    Schema.Options.CAMEL_CASE_GENERATOR,
                    Schema.Options.KEBAB_CASE_GENERATOR,
                    lambda x: "@" + x
                ],
                alias_for_generator=Schema.Options.CAP_KEBAB_CASE_GENERATOR,
            )
            attr_name: str
            CAP_ATTR_NAME: str
            fixed_name: str = Field(alias_from=['fix1', 'fix2'], alias='@fix')

        attr_name_vars = ['attr_name', '@attr_name', 'attr-name', 'attrName', 'ATTR-NAME']
        cap_attr_name_vars = ['CAP_ATTR_NAME', '@CAP_ATTR_NAME', 'cap-attr-name', 'capAttrName', 'CAP-ATTR-NAME']
        fix_name_vars = ['fix1', 'fix2']    # override the Options config

        for a1 in attr_name_vars:
            for a2 in cap_attr_name_vars:
                for f3 in fix_name_vars:
                    assert dict(AllowCaseSchema({a1: 'a1', a2: 'a2', f3: 'a3'})) \
                           == {'ATTR-NAME': 'a1', 'CAP-ATTR-NAME': 'a2', '@fix': 'a3'}

        class ImmutableSchema(Schema):
            __options__ = Schema.Options(immutable=True)
            attr: str = ''

        sc = ImmutableSchema(attr='x')
        with pytest.raises(AttributeError):
            sc.attr = 'y'
        with pytest.raises(AttributeError):
            del sc.attr
        with pytest.raises(AttributeError):
            sc['attr'] = 'y'
        with pytest.raises(AttributeError):
            sc.update(attr='y')
        with pytest.raises(AttributeError):
            sc.pop('attr')
        with pytest.raises(TypeError):
            sc.popitem()
        with pytest.raises(TypeError):
            sc.clear()

        class InsensitiveSchema(Schema):
            __options__ = Schema.Options(case_insensitive=True)
            VALUE: int = 0
            attr: str
            other_name: bool = False

        assert dict(InsensitiveSchema(value='3', Attr='x', OTHER_NAME=True)) == \
               {'VALUE': 3, 'attr': 'x', 'other_name': True}
        # attr ane key access of case_insensitive schema will also support case_insensitive access

        with pytest.raises(AttributeError):
            class InsensitiveSchemaInvalid1(Schema):
                __options__ = Schema.Options(case_insensitive=True)
                VALUE: int = 0
                value: int
                # name is same

        with pytest.raises(AttributeError):
            class InsensitiveSchemaInvalid2(Schema):
                __options__ = Schema.Options(case_insensitive=True)
                val1: int = Field(alias_from=['VALUE'])
                value: str
                # name is same

        # class CommonSchema(Schema):
        #     __options__ = Schema.Options(exact_attribute_access=False)
        #     attr: str = Field(alias='attr_for', alias_from=['attr_from'])
        #
        # class ExactSchema(Schema):
        #     __options__ = Schema.Options(exact_attribute_access=True)
        #     attr: str = Field(alias='attr_for', alias_from=['attr_from'])
        #
        # assert CommonSchema(attr_from='x').attr_for == 'x'
        # assert CommonSchema(attr_from='x').attr == 'x'
        # assert CommonSchema(attr_from='x').attr_from == 'x'
        # assert ExactSchema(attr_from='x').attr == 'x'

        # with pytest.raises(AttributeError):
        #     assert ExactSchema(attr_for='x').attr_for
        # with pytest.raises(AttributeError):
        #     assert ExactSchema(attr_from='x').attr_from

        class IgnoreDiscardSchema(Schema):
            __options__ = Schema.Options(ignore_discard=["v1"])
            v1: str = QueryField(discard=True)
            v2: str = QueryField(discard=True)
            v3: str = "x"

        assert dict(IgnoreDiscardSchema(v1='x', v2='y', v3='z')) == {'v1': 'x', 'v3': 'z'}

        class BestEffortSchema(Schema):
            __options__ = Schema.Options(best_effort_transform=True)
            attr: int = Field(value=10)
            tp: int

        assert dict(BestEffortSchema(attr=3, tp='xx')) == {'attr': 3, 'tp': 'xx'}
        assert dict(BestEffortSchema(attr=3, tp='33')) == {'attr': 3, 'tp': 33}

        # test options in data
        class v(Schema):
            value: int

        data = {"__options__": Schema.Options(case_insensitive=True), "VALUE": '1'}
        assert v(**data).value == 1

        data = {"__options__": Schema.Options(ignore_discard=True), "v1": 1, 'v2': 2}
        assert dict(IgnoreDiscardSchema(**data)) == {'v1': '1', 'v2': '2', 'v3': 'x'}

        class UnprovidedSchema1(Schema):
            __options__ = Schema.Options(unprovided_attribute=KeyError)
            attr: str = Field(required=False)

        with pytest.raises(KeyError):
            _ = UnprovidedSchema1().attr

        class UnprovidedSchema2(Schema):
            __options__ = Schema.Options(unprovided_attribute=list)
            attr: str = Field(required=False)

        assert UnprovidedSchema2().attr == []

        class UnprovidedSchema2(Schema):
            __options__ = Schema.Options(unprovided_attribute=None)
            attr: str = Field(required=False)

        assert UnprovidedSchema2().attr is None

        from utilmeta.util.parser.cls import ClassParser

        class ExClassParser(ClassParser):
            pass

        class ClassOptionsSchema(Schema):
            __parser_cls__ = ExClassParser

            class __options__(Schema.Options):
                unprovided_attribute = None
                ignore_conflict = True
                ignore_required = True
