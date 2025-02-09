import json
import sys
import typing
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import UUID
from decimal import Decimal
import pytest  # noqa

import utype
from utype import (DataClass, Field, Options, Rule, Schema, exc,
                   register_transformer, types)
from utype.utils.compat import Final, Self


@pytest.fixture(params=(False, True))
def dfs(request):
    return request.param


# @pytest.mark.parametrize(argnames='dfs', argvalues=(False, True))
class TestClass:
    def test_init(self, dfs):
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
            __options__ = Options(data_first_search=dfs)

            slug: Slug

        assert dict(ArticleSchema(slug=b"My Awesome Article!")) == {
            "slug": "my-awesome-article"
        }

        # test 1, pos
        assert ArticleSchema(
            dict(slug=b"My Awesome Article!")
        ) == ArticleSchema(
            **dict(slug=b"My Awesome Article!")
        )

        class PowerSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            result: float
            num: float
            exp: float

            def __init__(self, num: float, exp: float):
                assert isinstance(num, float)
                assert isinstance(exp, float)

                if num < 0:
                    if 1 > exp > -1 and exp != 0:
                        raise ValueError(f'operation not supported, '
                                         f'complex result will be generated')
                super().__init__(
                    num=num,
                    exp=exp,
                    result=num ** exp
                )

        power = PowerSchema('3', 3, ignore='other')
        assert power.result == 27
        assert 'ignore' not in power

        with pytest.raises(ValueError):
            PowerSchema(-0.5, -0.5)

        class v(Schema):
            pow: PowerSchema

    def test_dataclass(self, dfs):
        class DT(utype.DataClass):
            __options__ = Options(data_first_search=dfs)

            name: str = Field(max_length=10)
            age: int

        dt = DT.__from__(b'{"name": 1, "age": "2"}')
        assert dt.name == '1'
        assert dt.age == 2

        with pytest.raises(exc.ParseError):
            DT.__from__(b'{"name": 1, "age": "2"}', options=Options(no_explicit_cast=True))

        with pytest.raises(exc.ParseError):
            dt.name = '*' * 20

        with pytest.raises(exc.ParseError):
            dt.age = 'abc'

        @utype.dataclass(set_class_properties=False, options=Options(data_first_search=dfs))
        class DataClass:
            name: str = Field(max_length=10)
            age: int

        assert isinstance(DataClass.name, Field)
        with pytest.raises(AttributeError):
            _ = DataClass.age

        dt = DataClass(name=b"test", age="2")
        assert dt.name == "test"
        assert dt.age == 2

        dt.name = '*' * 20  # will not raise error
        assert dt.name == '*' * 20

        @utype.dataclass(
            set_class_properties=True,
            contains=True,
            repr=True,
            eq=True,
        )
        class DataProp(dict):
            name: str = Field(max_length=10)
            age: int

        assert isinstance(DataProp.name, property)
        assert isinstance(DataProp.age, property)

        v = DataProp(name=1, age='2', other='3')
        assert v.name == '1'
        assert 'age' in v
        assert 'other' not in v

        assert v == DataProp(name=1, age='2')
        assert repr(v) == "DataProp(name='1', age=2)"

        with pytest.raises(exc.ParseError):
            v.name = '*' * 20

        with pytest.raises(exc.ParseError):
            v.age = 'abc'

        # test no parse
        @utype.dataclass(
            no_parse=True,
        )
        class DataNoParse(dict):
            name: str = Field(max_length=10)
            age: int

        a = DataNoParse(name=1, age='2', other='ignore')
        assert a.name == 1
        assert a.age == '2'
        assert a.other == 'ignore'

        @utype.dataclass(
            no_parse=True,
        )
        class DataNoParse(dict):
            name: str = Field(max_length=10)
            age: int

            def __init__(self, name: str):
                super().__init__(name=name, age=0)

        with pytest.raises(TypeError):
            DataNoParse(name=1, age='2')

    def test_inherit(self):
        class base(Schema):
            a: int
            b: int

        class sub(base):
            a = ...
            c: int = 0
            b = Field(required=False)
            # use the inherited annotation (int)

        assert dict(sub(b=1)) == {'b': 1, 'c': 0}
        assert dict(sub(a=2, b='1')) == {'b': 1, 'c': 0}
        assert dict(sub(c='2')) == {'c': 2}

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
            null_val: Optional[str] = Field(length=6, required=False, on_error="exclude")
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

    def test_exclude_var(self, dfs):
        class Exclude(Schema):
            __options__ = Options(addition=True, data_first_search=dfs)

            _exclude: int = 1
            include: int = 0

        e = Exclude(include='3', _exclude='2')
        assert e._exclude == 1
        assert e.include == 3
        assert '_exclude' not in e

    def test_forward_ref(self, dfs):
        class T(Schema):
            __options__ = Options(ignore_required=True, data_first_search=dfs)

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

        # test not-module-level self ref
        class SelfRef(Schema):
            name: str
            to_self: "SelfRef" = Field(required=False)
            self_lst: List["SelfRef"] = Field(default_factory=list)

        sf = SelfRef(name=1, to_self=b'{"name":"test"}')
        assert sf.to_self.name == "test"
        assert sf.self_lst == []

        sf2 = SelfRef(name="t2", self_lst=[dict(sf)])
        assert sf2.self_lst[0].name == "1"
        assert "to_self" not in sf2

        class SelfRef2(Schema):
            name: str
            to_self: Self = Field(required=False)
            self_lst: List[Self] = Field(default_factory=list)

        sfi = SelfRef2(name=1, to_self=b'{"name":"test"}')
        assert sfi.to_self.name == "test"
        assert sfi.self_lst == []

        # class ForwardSchema(Schema):
        #     int1: 'types.PositiveInt' = Field(lt=10)
        #     int2: 'types.PositiveInt' = Field(lt=20)
        #     l_int: List['types.PositiveInt'] = Field(length=5)
        #     l_int_f: 'List[types.PositiveInt]' = Field(max_length=3)

    def test_local_forward_ref(self):
        def f(u=0):
            class LocSelf(Schema):
                num: int = u
                to_self: Optional["LocSelf"] = None
                list_self: List["LocSelf"] = utype.Field(default_factory=list)
            data = LocSelf(to_self={'to_self': {}}, list_self=[{'list_self': []}])
            return data.to_self.to_self.num, data.list_self[0].num

        assert f(1) == (1, 1)
        assert f(2) == (2, 2)

    def test_class_vars(self, dfs):
        def outer(k=None):
            return k

        class TestSchema(Schema):
            __options__ = Options(ignore_required=True, data_first_search=dfs)

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

            r8: Union[typing.Callable, typing.AnyStr] = outer
            r9: type(None) = Field(alias_from=["_r9", "r9_"], default_factory=outer)

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
            def r13(self, value: str = Field(alias_from=["r13_alias"], default="1.5")):
                self._r13 = float(value)

            r14 = outer     # no annotation function
            r15 = r10       # no annotation type (class)
            r16 = r7        # no annotation staticmethod

            r17: typing.ClassVar[str] = '3'
            r18: typing.ClassVar = '3'
            r19: typing.ForwardRef('str') = '3'
            r20: Final = 1
            r21: Final[str] = 'a'        # no input and immutable
            r22: Final[int]              # immutable

        assert set(TestSchema.__parser__.fields) == {
            'r1', 'r2', 'r3', 'r4', 'r8', 'r9', 'r12', 'r13',
            'r14', 'r15', # 'r16',  # new
            'r19', 'r20', 'r21', 'r22'
        }

        t1 = TestSchema(r21='b', r22='3')
        # no input field does not take input from __init__
        # but can still apply default
        assert t1.r21 == 'a'        # final
        assert t1.r22 == 3

        with pytest.raises(exc.UpdateError):
            t1.r21 = 2

        with pytest.raises(exc.UpdateError):
            t1.r22 = 2

        with pytest.raises(Exception):
            class s(Schema):    # noqa
                a: ''       # empty forward ref

        with pytest.raises(Exception):
            class s(Schema):    # noqa
                # invalid annotation:
                r14: outer

        with pytest.raises(Exception):
            class s(Schema):    # noqa
                # invalid annotation:
                r14: typing.Literal

        with pytest.warns():
            class s(Schema):    # noqa
                # invalid annotation:
                r14: typing.TypeVar

        with pytest.raises(Exception):
            class s(Schema):    # noqa
                # invalid annotation:
                r14: typing.TypeVar('T')

        with pytest.raises(Exception):
            class b(Schema):    # noqa
                # invalid annotation:
                f: typing.Final[str] = '3'

            class c(b):    # noqa
                # invalid annotation:
                f: typing.Final[str] = '4'

        with pytest.raises(Exception):
            class s(Schema):     # noqa
                items: list = Field(max_length=10)  # wrong

        with pytest.raises(Exception):
            class s(Schema):    # noqa
                update: str = ""

    def test_types(self):
        class s(Schema):
            a: Type[int]

        with pytest.raises(exc.ParseError):
            s(a=1)

        with pytest.raises(exc.ParseError):
            s(a=str)

        assert s(a=bool).a == bool
        assert s(a=int).a == int

        class s(Schema):
            d: Decimal = utype.Field(ge=0, round=2)

        assert s(d=0.1234).d == Decimal('0.12')

    def test_generic_types(self):
        import sys
        if sys.version_info >= (3, 9):
            class Gen(Schema):
                a: list[int]
                b: dict[int]
                c: dict[int, int]
                d: tuple[int, bool]
                e: set[str]

            assert dict(Gen(
                a=('1', b'f', True),
                b={'1': 2, '2': '3'},
                c={'1': 2, '2': '3'},
                d=[b'2', 0],
                e=['1', 'a', 'a']
            )) == {'a': [1, 0, 1], 'b': {1: 2, 2: '3'}, 'c': {1: 2, 2: 3}, 'd': (2, False), 'e': {'a', '1'}}

    def test_functional_initialize_and_aliases(self, dfs):
        # test omit init
        class OmitSchema(Schema):
            __options__ = Options(data_first_search=dfs)
            n0: int
            n1: int
            n2: Any = Field(alias_from=["named_n2"])

            def __init__(
                self,
                alias_n0: int = 0,
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
        o2_ = OmitSchema(0, 3, **{"@n2": "2"}, invalid='none')

        assert o2 == o2_        # test that init can ignore additions

        assert o0.n0 == 0
        assert o0.n1 == 1
        assert o0.n2 == 1
        assert o1.n0 == 1
        assert o1.n1 == 2
        assert o1.n2 == 2
        assert o2.n0 == 0
        assert o2.n1 == 3
        assert o2.n2 == 2  # int does the type cast

    def test_schema_rule(self, dfs):
        # require / default / omit / null
        class RuleSchema(Schema):
            __options__ = Options(data_first_search=dfs)

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
            str_or_list: Union[str, List[str]]

        u1 = UnionSchema(opt=None, union=3, str_or_list=["1", "2"])
        assert u1.opt is None
        assert u1.union == 3
        assert u1.str_or_list == ["1", "2"]

        u2 = UnionSchema(opt=5, union={1: "2"}, str_or_list="str")
        assert u2.opt == 5
        assert u2.union == {"1": 2}
        assert u2.str_or_list == "str"

        u3 = UnionSchema(opt=5, union=[1], str_or_list=[1, 2])
        assert u3.union == 1
        assert u3.str_or_list == ["1", "2"]

        with pytest.raises(exc.ParseError):
            UnionSchema(opt=5, union={"a": "b"})  # cannot convert to Dict[str, int]

        if sys.version_info >= (3, 10):
            class a(utype.Schema):
                b: int | None = utype.Field(ge=1)

            assert a(b=None).b is None
            assert a(b='3').b == 3

    @pytest.mark.parametrize(argnames=['no_output', 'immutable', 'no_input'],
                             argvalues=[
                                # (False, False, False),
                                # (True, False, False),
                                (True, True, False),
                                (False, False, True)
                             ])
    def test_property(self, dfs, no_output: bool, immutable: bool, no_input: bool):
        class UserSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            name: str
            level: int = 0

            @property
            @Field(alias='@label', no_output=no_output, dependencies=['level'])
            def label(self) -> bytes:       # test conversion
                return f"{self.name}<{self.level}>"

        user = UserSchema(name="Bob", level=3)

        assert user.label == b"Bob<3>"

        if not no_output:
            assert user['@label'] == b"Bob<3>"
        else:
            assert '@label' not in user
            assert 'label' not in user

        # test relate update
        user.level += 1
        assert user.label == b"Bob<4>"

        if not no_output:
            assert user['@label'] == b"Bob<4>"

        # test dependencies

        class ArticleSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            _slug: str
            _title: str

            @property
            @Field(description='article title')
            def title(self) -> str:
                return self._title

            @title.setter
            def title(self, val: str = Field(max_length=50, no_input=no_input, immutable=immutable)):
                self._title = val
                self._slug = '-'.join([''.join(filter(str.isalnum, v))
                                       for v in val.split()]).lower()

            @title.deleter
            def title(self):
                del self._title
                del self._slug

            @property
            @Field(dependencies=title)
            def slug(self) -> str:
                return self._slug

        article = ArticleSchema(title=b'My Awesome article!')

        if not no_input:
            assert article.slug == 'my-awesome-article'
        else:
            assert 'title' not in article
            assert 'slug' not in article

            with pytest.raises(AttributeError):
                _ = article.slug

        with pytest.raises(AttributeError):
            article.slug = 'other value'

        if immutable:
            with pytest.raises(exc.UpdateError):
                article.title = b'Our Awesome article!'
        else:
            article.title = b'Our Awesome article!'
            assert dict(article) == {'slug': 'our-awesome-article', 'title': 'Our Awesome article!'}

            with pytest.raises(exc.ParseError):
                article.title = '*' * 100

            # test deleter
            del article.title
            assert 'title' not in article

            # slug is not affected
            assert 'slug' in article

            with pytest.raises(AttributeError):
                _ = article.title

    def test_input_output(self, dfs):
        class KeyInfo(Schema):
            __options__ = Options(data_first_search=dfs)

            access_key: str = Field(no_output=True)
            last_activity: datetime = Field(default_factory=datetime.now, no_input=True)

            @property
            def key_sketch(self) -> str:
                return self.access_key[:5] + '*' * (len(self.access_key) - 5)

        info = KeyInfo(access_key='QWERTYUIOP')
        assert 'key_sketch' in info
        assert info['key_sketch'] == 'QWERT*****'

        # test generation
        from utype import JsonSchemaGenerator
        assert JsonSchemaGenerator(KeyInfo, output=False)() == {'type': 'object', 'properties':
            {'access_key': {'type': 'string'}}, 'required': ['access_key']}
        assert JsonSchemaGenerator(KeyInfo, output=True)() == {'type': 'object', 'properties':
            {'last_activity': {'type': 'string', 'format': 'date-time'},
             'key_sketch': {'type': 'string'}}, 'required': ['last_activity']}

        class ArticleSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            slug: str = Field(no_input=True)
            title: str
            updated_at: datetime = Field(default_factory=datetime.now, no_input=True)

            def __validate__(self):
                assert 'slug' not in self
                self.slug = '-'.join([''.join(filter(str.isalnum, v))
                                      for v in self.title.split()]).lower()

        article = ArticleSchema(title='My Awesome Article', slug='ignore')

        assert article.slug == 'my-awesome-article'
        assert JsonSchemaGenerator(ArticleSchema, output=False)() == \
               {'type': 'object', 'properties': {'title': {'type': 'string'}}, 'required': ['title']}
        assert JsonSchemaGenerator(ArticleSchema, output=True)() == {'type': 'object',
            'properties': {'slug': {'type': 'string'}, 'title': {'type': 'string'},
                           'updated_at': {'type': 'string', 'format': 'date-time'}},
            'required': ['title', 'updated_at']}

        class t(Schema):
            __options__ = Options(mode='a')
            a: int = Field(mode='rw', no_input='w')

        assert 'a' not in t()

    def test_schema_dict(self, dfs):
        class T(Schema):
            __options__ = Options(data_first_search=dfs, addition=True)

            a: str = Field(max_length=10, default='default')
            b: int = 0
            c: int = Field(ge=10, required=False, alias_from=['c$', 'c#'])
            im: str = Field(required=False, default=None, defer_default=True, immutable=True)
            req: int

        t1 = T(a='123', req=True, addon=1)
        t1.update({
            'b': '123',
            'c$': b'123',
            # test ignore required
        })
        assert t1.c == t1.b == 123      # test attribute update
        assert t1.a == '123'        # no default for update
        t1['c#'] = b'456'
        assert 'c$' in t1
        assert t1.c == 456
        assert 'im' not in t1
        assert t1['addon'] == 1
        assert t1.pop('a') == '123'
        assert 'a' not in t1
        assert t1.pop('addon') == 1     # pop other field
        assert 'addon' not in t1

        with pytest.raises(exc.ParseError):
            t1['c#'] = b'abc'

        with pytest.raises(exc.ParseError):
            t1['c$'] = '1'

        cp = t1.copy()
        assert type(cp) == T
        assert cp == t1

        with pytest.raises(exc.UpdateError):
            t1.im = 3

        with pytest.raises(exc.UpdateError):
            t1['im'] = 3

        with pytest.raises(exc.DeleteError):
            del t1.im

        with pytest.raises(exc.DeleteError):
            # delete required
            del t1.req

        with pytest.raises(exc.DeleteError):
            del t1.im

    def test_combine(self, dfs):
        class MemberSchema(Schema):
            name: str
            level: int = 0

        class GroupSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            name: str
            creator: MemberSchema
            members: List[MemberSchema] = Field(default_factory=list)

        alice = {'name': 'Alice', 'level': '3'}
        bob = b'{"name": "Bob"}'

        group = GroupSchema(name='test', creator=alice, members=(alice, bob))

        assert group.creator.level == 3
        assert group.members[1].name == 'Bob'

        assert MemberSchema.__from__(bob) == group.members[1]

        class UserSchema(Schema):
            __options__ = Options(data_first_search=dfs)

            name: str
            level: int = 0

            class KeyInfo(Schema):
                __options__ = Options(data_first_search=dfs)

                access_key: str
                last_activity: datetime = None

            access_keys: List[KeyInfo] = Field(default_factory=list)

        assert issubclass(UserSchema.KeyInfo, Schema)
        user = UserSchema(**{'name': 'Joe', 'access_keys': {'access_key': 'KEY'}})
        assert user.access_keys[0].access_key == 'KEY'
        assert user.access_keys[0].last_activity is None

        class UsernameMixin(Schema):
            username: str = Field(regex='[0-9a-zA-Z]{3,20}')

        class PasswordMixin(Schema):
            password: str = Field(min_length=6, max_length=20)

        class LoginSchema(UsernameMixin, PasswordMixin):
            __options__ = Options(data_first_search=dfs)

        log = LoginSchema(username=123456, password=123456)
        assert log.username == log.password == '123456'

        from typing import Optional

        class UserInfo(Schema):
            username: str = Field(regex='[0-9a-zA-Z]{3,20}')

        class LoginForm(UserInfo):
            __options__ = Options(data_first_search=dfs)
            password: str = Field(min_length=6, max_length=20)

        password_dict = {"alice": "123456"}

        @utype.parse(options=Options(data_first_search=dfs))
        def login(form: LoginForm) -> Optional[UserInfo]:
            if password_dict.get(form.username) == form.password:
                return {"username": form.username}
            return None

        user = login(b'{"username": "alice", "password": 123456}')
        assert user.username == 'alice'

        with pytest.raises(exc.ParseError):
            login(b'{"username": "alice", "password": 123}')

        assert login(b'{"username": "alice", "password": "wrong-pwd"}') is None

    def test_logical(self, dfs):
        @utype.dataclass(eq=True, contains=True)       # make eq so that instance can be compared
        class LogicalDataClass(metaclass=utype.LogicalMeta):
            __options__ = Options(data_first_search=dfs)
            name: str = Field(max_length=10)
            age: int

        one_of_type = LogicalDataClass ^ Tuple[str, int]

        ld = one_of_type({'name': 'test', 'age': '1'})
        assert ld == LogicalDataClass(name='test', age=1)
        assert 'age' in ld

        assert one_of_type([b'test', '1']) == ('test', 1)

        class LogicalUser(DataClass):
            name: str = Field(max_length=10)
            age: int

        one_of_user = LogicalUser ^ Tuple[str, int]

        assert one_of_user({'name': 'test', 'age': '1'}) == LogicalUser(name='test', age=1)
        assert one_of_user([b'test', '1']) == ('test', 1)

        from utype import JsonSchemaGenerator
        res = JsonSchemaGenerator(one_of_type)()
        assert res == {'oneOf': [{'type': 'object', 'properties':
            {'name': {'type': 'string', 'maxLength': 10}, 'age': {'type': 'integer'}}, 'required': ['name', 'age']},
                                 {'type': 'array', 'prefixItems': [{'type': 'string'}, {'type': 'integer'}]}]}

    def test_pass(self):
        class A(Schema):
            a: str = utype.Field(no_output=True)

        class B(Schema):
            a_or: A

        b = B(a_or=[A(a=3)])
        assert b.a_or.a == '3'
