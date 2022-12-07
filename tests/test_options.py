from utype import Schema, Options, exc, Field
from utype.utils.style import AliasGenerator
import pytest
from typing import List
from datetime import date, timedelta, datetime


class TestOptions:    
    def test_schema_options(self):
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

        class UserSchemaIgnore(Schema):
            __options__ = Options(ignore_required=True)
            name: str
            level: int = 0

        user = UserSchemaIgnore()
        assert dict(user) == {"level": 0}
        with pytest.raises(AttributeError):
            user.name  # noqa

        class UserSchemaDisallowType(Schema):
            __options__ = Options(no_explicit_cast=True)
            name: str
            level: int = 0

        with pytest.raises(exc.ParseError):
            UserSchemaDisallowType(name=107, level="3")

        class IndexSchema(Schema):
            indexes: List[int]

        class IndexSchemaExclude(Schema):
            __options__ = Options(invalid_items='exclude')
            indexes: List[int]

        with pytest.raises(exc.ParseError):
            IndexSchema(indexes=[1, 2, "ab"])

        assert dict(IndexSchemaExclude(indexes=[1, 2, "ab"])) == {"indexes": [1, 2]}

        class IndexSchemaPreserve(Schema):
            __options__ = Options(invalid_items='preserve')
            indexes: List[int]

        assert dict(IndexSchemaPreserve(indexes=[1, 2, "ab"])) == {
            "indexes": [1, 2, "ab"]
        }

        class NoDefaultSchema(Schema):
            __options__ = Options(no_default=True)
            default: str = "0"

        with pytest.raises(AttributeError):
            _ = NoDefaultSchema().default
            # no default
            # 1. when parsing, default value will never be used to fill unprovided key
            # 2. when accessing missing attributes, it will throw AttributeError instead of give a default

        class NoLossSchema(Schema):
            __options__ = Options(no_data_loss=True)
            dt: date

        with pytest.raises(exc.ParseError):
            NoLossSchema(dt=datetime(2022, 1, 1, 12, 12, 12))

        class TypeOnlySchema(Schema):
            __options__ = Options(ignore_constraints=True)
            attr: str = Field(const='xxxx')
            lst: List[int] = Field(length=3)

        assert dict(TypeOnlySchema(attr=3, lst='1,2,3,4')) == {'attr': '3', 'lst': [1, 2, 3, 4]}   # ignore other rules

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
        fix_name_vars = ['fix1', 'fix2']    # override the Options config

        for a1 in attr_name_vars:
            for a2 in cap_attr_name_vars:
                for f3 in fix_name_vars:
                    assert dict(AllowCaseSchema({a1: 'a1', a2: 'a2', f3: 'a3'})) \
                           == {'ATTR-NAME': 'a1', 'CAP-ATTR-NAME': 'a2', '@fix': 'a3'}

        class ImmutableSchema(Schema):
            __options__ = Options(immutable=True)
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
            __options__ = Options(case_insensitive=True)
            VALUE: int = 0
            attr: str
            other_name: bool = False

        assert dict(InsensitiveSchema(value='3', Attr='x', OTHER_NAME=True)) == \
               {'VALUE': 3, 'attr': 'x', 'other_name': True}
        # attr ane key access of case_insensitive schema will also support case_insensitive access

        with pytest.raises(AttributeError):
            class InsensitiveSchemaInvalid1(Schema):
                __options__ = Options(case_insensitive=True)
                VALUE: int = 0
                value: int
                # name is same

        with pytest.raises(AttributeError):
            class InsensitiveSchemaInvalid2(Schema):
                __options__ = Options(case_insensitive=True)
                val1: int = Field(alias_from=['VALUE'])
                value: str
                # name is same

        # class CommonSchema(Schema):
        #     __options__ = Options(exact_attribute_access=False)
        #     attr: str = Field(alias='attr_for', alias_from=['attr_from'])
        #
        # class ExactSchema(Schema):
        #     __options__ = Options(exact_attribute_access=True)
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
            v1: str = Field(no_output=True)
            v2: str = Field(no_output=True)
            v3: str = "x"

        assert dict(IgnoreDiscardSchema(v1='x', v2='y', v3='z')) == {'v3': 'z'}

        class BestEffortSchema(Schema):
            __options__ = Options(invalid_values='preserve')
            attr: int = Field(const=10)
            tp: int

        assert dict(BestEffortSchema(attr=3, tp='xx')) == {'attr': 3, 'tp': 'xx'}
        assert dict(BestEffortSchema(attr=3, tp='33')) == {'attr': 3, 'tp': 33}

        # test options in data
        class v(Schema):
            value: int

        data = {"__options__": Options(case_insensitive=True), "VALUE": '1'}
        assert v(**data).value == 1

        data = {"__options__": Options(ignore_no_output=True), "v1": 1, 'v2': 2}
        assert dict(IgnoreDiscardSchema(**data)) == {'v1': '1', 'v2': '2', 'v3': 'x'}

        class UnprovidedSchema1(Schema):
            __options__ = Options(unprovided_attribute=None)
            attr: str = Field(required=False)

        assert UnprovidedSchema1().attr is None

        class UnprovidedSchema2(Schema):
            __options__ = Options(unprovided_attribute=list)
            attr: str = Field(required=False)

        assert UnprovidedSchema2().attr == []

        class UnprovidedSchema2(Schema):
            __options__ = Options(unprovided_attribute=None)
            attr: str = Field(required=False)

        assert UnprovidedSchema2().attr is None

        class ClassOptionsSchema(Schema):
            class __options__(Options):
                unprovided_attribute = None
                ignore_alias_conflicts = True
                ignore_required = True

    def test_type_transform(self):
        pass

    def test_aliases(self):
        pass

    def test_defaults(self):
        pass

    def test_errors(self):
        pass
