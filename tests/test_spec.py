from utype.types import *
from utype.parser.rule import Rule


class TestSpec:
    def test_json_schema_parser(self):
        from utype.specs.json_schema.parser import JsonSchemaParser
        from utype.specs.python.generator import PythonCodeGenerator
        assert JsonSchemaParser({})() == Any
        assert JsonSchemaParser({'anyOf': [{}, {'type': 'null'}]})() in (Rule, Any)
        assert JsonSchemaParser({'type': 'object'})() == dict
        assert JsonSchemaParser({'type': 'array'})() == list
        assert JsonSchemaParser({'type': 'string'})() == str
        assert JsonSchemaParser({'type': 'string', 'format': 'date'})() == date
