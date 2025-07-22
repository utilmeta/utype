from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import pytest

import utype
from utype import Field, Options, Schema, exc
from utype.utils.style import AliasGenerator


@pytest.fixture(params=(False, True))
def dfs(request):
    return request.param


@pytest.fixture(params=('throw', 'exclude', 'preserve'))
def on_error(request):
    return request.param


@pytest.fixture(params=('throw', 'init', 'ignore'))
def unresolved(request):
    return request.param


class TestOptions:
    def test_parsing(self):
        # test class options
        class UserIgnore(Schema):
            class __options__(Options):
                ignore_required = True

            name: str
            level: int = 0

        u1 = UserIgnore()
        assert dict(u1) == {"level": 0}

        class UserSchemaIgnore(Schema):
            __options__ = Options(ignore_required=True)
            name: str
            level: int = 0

        user = UserSchemaIgnore()
        assert dict(user) == {"level": 0}
        with pytest.raises(AttributeError):
            user.name  # noqa

        class TypeOnlySchema(Schema):
            __options__ = Options(ignore_constraints=True)
            attr: str = Field(const='xxxx')
            lst: List[int] = Field(length=3)

        assert dict(TypeOnlySchema(attr=3, lst='1,2,3,4')) == {'attr': '3', 'lst': [1, 2, 3, 4]}   # ignore other rules

    def test_immutable(self):
        class ImmutableSchema(Schema):
            __options__ = Options(immutable=True)
            attr: str = ''

        sc = ImmutableSchema(attr='x')
        with pytest.raises(exc.UpdateError):
            sc.attr = 'y'
        with pytest.raises(exc.DeleteError):
            del sc.attr
        with pytest.raises(exc.UpdateError):
            sc['attr'] = 'y'
        with pytest.raises(exc.UpdateError):
            sc.update(attr='y')
        with pytest.raises(exc.DeleteError):
            sc.pop('attr')
        with pytest.raises(exc.DeleteError):
            sc.popitem()
        with pytest.raises(exc.DeleteError):
            sc.clear()

    def test_delete(self):
        class AttrSchema(Schema):
            # __options__ = Options(i)
            attr: str = ''
        a = AttrSchema()
        assert dict(a) == {'attr': ''}
        del a.attr
        assert dict(a) == {}
        with pytest.raises(exc.DeleteError):
            del a.attr

        class AttrSchema2(Schema):
            __options__ = Options(ignore_delete_nonexistent=True)
            attr: str = ''

        a = AttrSchema2()
        assert dict(a) == {'attr': ''}
        del a.attr
        assert dict(a) == {}
        del a.attr
        assert dict(a) == {}

    # def test_secret_names(self):
    #     pass

    def test_alias(self):
        # case styles
        class AllowCaseSchema(Schema):
            __options__ = Options(
                alias_from_generator=[
                    AliasGenerator.camel,
                    AliasGenerator.kebab,
                    lambda x: "@" + x
                ],
                alias_generator=AliasGenerator.cap_kebab,
            )
            attr_name: str
            CAP_ATTR_NAME: str
            fixed_name: str = Field(alias_from=['fix1', 'fix2'], alias='@fix')

        attr_name_vars = ['attr_name', '@attr_name', 'attr-name', 'attrName', 'ATTR-NAME']
        cap_attr_name_vars = ['CAP_ATTR_NAME', '@CAP_ATTR_NAME', 'cap-attr-name', 'capAttrName', 'CAP-ATTR-NAME']
        fix_name_vars = ['fix1', 'fix2', '@fix']    # override the Options config

        for a1 in attr_name_vars:
            for a2 in cap_attr_name_vars:
                for f3 in fix_name_vars:
                    assert dict(AllowCaseSchema({a1: 'a1', a2: 'a2', f3: 'a3'})) \
                           == {'ATTR-NAME': 'a1', 'CAP-ATTR-NAME': 'a2', '@fix': 'a3'}

        class AllowCaseSchemaIn(Schema):
            __options__ = Options(
                case_insensitive=True,
                alias_from_generator=[
                    AliasGenerator.camel,
                    AliasGenerator.kebab,
                    lambda x: "@" + x
                ],
            )
            attr_name: str
            CAP_ATTR_NAME: str
            fixed_name: str = Field(alias_from=['fix1', 'fix2'], alias='@fix')

        attr_name_vars = ['ATTR_name', '@attr_NAme', 'attr-Name', 'AttrName', 'ATTR-name']
        cap_attr_name_vars = ['CAP_Attr_Name', '@Cap_attr_NAME', 'cap-Attr-Name',
                              'capAttrName', 'CAP-ATTR-NAME', 'cap_attr_name']
        fix_name_vars = ['fix1', 'fix2', 'FIX1', '@FIX']  # override the Options config

        for a1 in attr_name_vars:
            for a2 in cap_attr_name_vars:
                for f3 in fix_name_vars:
                    assert dict(AllowCaseSchemaIn({a1: 'a1', a2: 'a2', f3: 'a3'})) \
                           == {'attr_name': 'a1', 'CAP_ATTR_NAME': 'a2', '@fix': 'a3'}

        class InsensitiveSchema(Schema):
            __options__ = Options(case_insensitive=True)
            VALUE: int = 0
            attr: str
            other_name: bool = False

        assert dict(InsensitiveSchema(value='3', Attr='x', OTHER_NAME=True)) == \
               {'VALUE': 3, 'attr': 'x', 'other_name': True}
        # attr ane key access of case_insensitive schema will also support case_insensitive access

        with pytest.raises(exc.ConfigError):
            class InsensitiveSchemaInvalid1(Schema):
                __options__ = Options(case_insensitive=True)
                VALUE: int = 0
                value: int
                # name is same

        with pytest.raises(exc.ConfigError):
            class InsensitiveSchemaInvalid2(Schema):
                __options__ = Options(case_insensitive=True)
                val1: int = Field(alias_from=['VALUE'])
                value: str
                # name is same

        # ------------
        class AliasSchema(Schema):
            alias: str = Field(alias_from=['alias_from', '@af2'])

        assert dict(AliasSchema({'alias': 1, 'alias_from': 1, '@af2': 1})) == {'alias': '1'}

        with pytest.raises(exc.AliasConflictError):
            dict(AliasSchema({'alias': 1, 'alias_from': 2}))

        class AliasSchema2(Schema):
            __options__ = Options(ignore_alias_conflicts=True)
            alias: str = Field(alias_from=['alias_from', '@af2'])
        assert dict(AliasSchema2({'alias': 1, 'alias_from': 2})) == {'alias': '1'}
        assert dict(AliasSchema2({'alias_from': 1, '@af2': 2})) == {'alias': '1'}

    def test_addition(self):
        class UserSchemaDisallow(Schema):
            __options__ = Options(addition=False)
            name: str
            level: int = 0

        assert dict(UserSchemaDisallow(name="Test")) == {"name": "Test", "level": 0}

        with pytest.raises(exc.ExceedError):
            UserSchemaDisallow(name="Test", code="XYZ")

        class UserSchemaPreserve(Schema):
            __options__ = Options(addition=True)
            name: str
            level: int = 0

        assert dict(UserSchemaPreserve(name="Test", code="XYZ")) == {
            "name": "Test",
            "code": "XYZ",
            "level": 0,
        }

        user = UserSchemaPreserve(name='alice', age=19, invite_code='XYZ')
        assert user['age'] == user.age == 19
        assert 'invite_code' in user
        # test additional property access

        class User(Schema):
            name: str
            level: int = 0

        User.__from__({'name': 'test', 'code': 'XYZ'}, options=Options(addition=True))

        with pytest.raises(exc.ParseError):
            User.__from__({'name': 'test', 'code': 'XYZ'}, options=Options(addition=False))

        with pytest.raises(exc.ConfigError):
            @utype.parse(options=Options(addition=True))
            def f():
                pass

        # with pytest.warns():
        #     @utype.parse(options=Options(addition=False))
        #     def f(**kwargs):
        #         return kwargs

    def test_invalids(self, on_error):
        class BestEffortSchema(Schema):
            __options__ = Options(invalid_values=on_error)
            attr: int = Field(const=10, required=False)
            tp: int = Field(required=False)
            rq: int

        if on_error == 'preserve':
            with pytest.warns():
                assert dict(BestEffortSchema(attr=10, rq='4', tp='xx')) == {'attr': 10, 'rq': 4, 'tp': 'xx'}
            with pytest.warns():
                assert dict(BestEffortSchema(attr=3, rq='4', tp='33')) == {'attr': 3, 'rq': 4, 'tp': 33}
        elif on_error == 'exclude':
            with pytest.warns():
                assert dict(BestEffortSchema(attr=10, rq='4', tp='xx')) == {'attr': 10, 'rq': 4}
            with pytest.warns():
                assert dict(BestEffortSchema(attr=3, rq='4', tp='33')) == {'rq': 4, 'tp': 33}

            with pytest.raises(exc.ParseError):
                BestEffortSchema(attr=3, rq='@@@', tp='33')

        else:
            with pytest.raises(exc.ParseError):
                BestEffortSchema(attr=3, tp='xx')

        class IndexSchema(Schema):
            __options__ = Options(invalid_items=on_error)
            indexes: List[int]

        if on_error == 'preserve':
            with pytest.warns():
                assert dict(IndexSchema(indexes=[1, 2, "ab"])) == {
                    "indexes": [1, 2, "ab"]
                }
        elif on_error == 'exclude':
            with pytest.warns():
                assert dict(IndexSchema(indexes=[1, 2, "ab"])) == {"indexes": [1, 2]}
        else:
            with pytest.raises(exc.ParseError):
                IndexSchema(indexes=[1, 2, "ab"])

        # from utype.types import PositiveInt

        class DicSchema(Schema):
            __options__ = Options(invalid_keys=on_error, invalid_values=on_error)

            dic: Dict[int, int]

        if on_error == 'preserve':
            with pytest.warns():
                assert DicSchema(dic={'3': 'x', 'x': '3'}).dic == {
                    3: 'x',
                    'x': 3
                }

        elif on_error == 'exclude':
            with pytest.warns():
                assert DicSchema(dic={'3': '1', '2': 'x', 'x': '3'}).dic == {
                    3: 1,
                }

        else:
            with pytest.raises(exc.ParseError):
                DicSchema(dic={'3': '1', '2': 'x', 'x': '3'})

        class IndexSchema(Schema):
            __options__ = Options(
                invalid_items='exclude',
                invalid_keys='preserve',
            )

            indexes: List[int]
            info: Dict[Tuple[int, int], int]

        data = {
            'indexes': ['1', '-2', '*', 3],
            'info': {
                '2,3': 6,
                '3,4': 12,
                'a,b': '10'
            }
        }

        with pytest.warns():
            assert dict(IndexSchema(**data)) == {'indexes': [1, -2, 3], 'info': {(2, 3): 6, (3, 4): 12, 'a,b': 10}}

    def test_max_min_params(self, dfs):
        class Info(Schema):
            __options__ = Options(
                data_first_search=dfs,
                min_params=2,
                max_params=5,
                addition=True
            )
            version: str

        data = {
            'version': 'v1',
            'k1': 1,
            'k2': 2,
            'k3': 3
        }
        assert len(Info(**data)) == 4

        with pytest.raises(exc.ParamsLackError):
            Info(version='v1')

        with pytest.raises(exc.ParamsExceedError):
            Info(**data, k4=4, k5=5)

    def test_max_depth(self):
        # test self reference
        class T(Schema):
            __options__ = Options(max_depth=3)
            a: str = ''
            b: int = Field(ge=0)
            t: 'T' = None

        data = {
            'a': b'3',
            'b': '4'
        }
        data['t'] = data       # recursive references (Circular reference)

        with pytest.raises(exc.ParseError) as err_info:
            T(**data)

        assert 'max_depth' in str(err_info.value)

    def test_defaults(self):
        class NoDefaultSchema(Schema):
            __options__ = Options(no_default=True)
            default: str = "0"

        with pytest.raises(AttributeError):
            _ = NoDefaultSchema().default
            # no default
            # 1. when parsing, default value will never be used to fill unprovided key
            # 2. when accessing missing attributes, it will throw AttributeError instead of give a default

        class ForceDefaultRequired(Schema):
            __options__ = Options(force_default=None)
            default: str

        assert ForceDefaultRequired().default is None

        class ForceDefault(Schema):
            __options__ = Options(force_default=None)
            default: str = 0

        f = ForceDefault()
        assert f.default is None
        assert 'default' in f

        class ForceDefaultSchema(Schema):
            __options__ = Options(force_default=None, ignore_required=True)
            default: str

        f = ForceDefaultSchema()
        assert f.default is None
        assert 'default' in f

        class DeferDefaultSchema(Schema):
            __options__ = Options(force_default=None, ignore_required=True, defer_default=True)
            default: str

        d = DeferDefaultSchema()
        assert d.default is None
        assert 'default' not in d

        class SelectedDeferDefaultSchema(Schema):
            __options__ = Options(
                ignore_required=['a1', 'a2'],
                defer_default=['a3']
            )
            a1: str
            a2: str = '2'
            a3: str = '3'

        d = SelectedDeferDefaultSchema()
        assert 'a1' not in d
        assert d.a2 == '2'
        assert d.a3 == '3'
        assert list(dict(d).keys()) == ['a2']

    def test_errors(self):
        class LoginForm(Schema):
            username: str = Field(regex='[0-9a-zA-Z]{3,20}')
            password: str = Field(min_length=6, max_length=20)

        form = {
            'username': '@attacker',
            'password': '12345',
            'token': 'XXX'
        }

        with pytest.raises(exc.CollectedParseError) as collected:
            LoginForm.__from__(form, options=Options(
                addition=False,
                collect_errors=True,
            ))

        assert len(collected.value.errors) == 3

        with pytest.raises(exc.CollectedParseError) as collected:
            LoginForm.__from__(form, options=Options(
                addition=False,
                collect_errors=True,
                max_errors=2
            ))

        assert len(collected.value.errors) == 2

        # class LoginForm(Schema):
        #     class __options__(Options):
        #         addition = False
        #         collect_errors = True
        #         case_insensitive = True
        #
        #     username: str = Field(regex='[0-9a-zA-Z]{3,20}')
        #     password: str = Field(min_length=6, max_length=20)

        @utype.parse(options=Options(
            addition=False,
            collect_errors=True,
            case_insensitive=True
        ))
        def login(
            username: str = Field(regex='[0-9a-zA-Z]{3,20}'),
            password: str = Field(min_length=6, max_length=20)
        ):
            return username, password

        with pytest.raises(exc.CollectedParseError) as collected:
            login(**form)

        assert len(collected.value.errors) == 3

    def test_type_preferences(self):
        from utype import type_transform

        with pytest.raises(TypeError):
            type_transform('[1,2,3]', list, options=Options(no_explicit_cast=True))

        with pytest.raises(TypeError):
            type_transform('{"value": true}', dict, options=Options(no_explicit_cast=True))

        with pytest.raises(TypeError):
            type_transform(3.1415, int, options=Options(no_data_loss=True))

        with pytest.raises(ValueError):
            type_transform('2022-03-04 10:11:12', date, options=Options(no_data_loss=True))

        class UserSchemaDisallowType(Schema):
            __options__ = Options(no_explicit_cast=True)
            name: str
            level: int = 0

        with pytest.raises(exc.ParseError):
            UserSchemaDisallowType(name=107, level="3")

        class NoLossSchema(Schema):
            __options__ = Options(no_data_loss=True)
            dt: date

        with pytest.raises(exc.ParseError):
            NoLossSchema(dt=datetime(2022, 1, 1, 12, 12, 12))

    def test_unresolved_types(self, unresolved):
        class MyClass:
            def __init__(self, value):
                self.value = value

        class MySchema(Schema):
            __options__ = Options(
                unresolved_types=unresolved
            )

            cls: MyClass = None

        if unresolved == 'throw':
            with pytest.raises(exc.ParseError):
                MySchema(cls=3)
        elif unresolved == 'init':
            inst = MySchema(cls=3)
            assert inst.cls.value == 3
        elif unresolved == 'ignore':
            inst = MySchema(cls=3)
            assert inst.cls == 3
