from __future__ import annotations

import pytest  # noqa
from utype import Schema, Field


class TestSchema(Schema):
    a: int
    base: TestSchema | None


class MyField(Field):
    my_prop = 'my_value'


class MySchema(Schema):
    __field__ = MyField


class TestGeneratedSchema(Schema):
    key: MySchema


class TestFuture:
    def test_recursive(self):
        t = TestSchema(a=1, base={'a': 2, 'base': None})
        assert t.base.a == 2
        assert t.base.base is None

    def test_generate(self):
        assert isinstance(TestGeneratedSchema.__parser__.fields['key'].field, MyField)
        # class MySchema2(Schema):
        #     __field__ = MyField
        #
        # class TestGeneratedSchema2(Schema):
        #     key: MySchema2
