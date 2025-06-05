import utype
from utype.types import *
from utype.parser.rule import Rule


class TargetSchema(utype.Schema):
    name: str
    ref: Optional['RefSchema'] = None
    ref_values: List['RefSchema'] = utype.Field(default_factory=list)


class RefSchema(utype.Schema):
    value: int = None


class InfiniteSchema(utype.Schema):
    name: str
    self: List['InfiniteSchema'] = utype.Field(default_factory=list)


class TestSpec:
    def test_json_schema_parser(self):
        from utype.specs.json_schema.parser import JsonSchemaParser
        assert JsonSchemaParser({})() == Any
        assert JsonSchemaParser({'anyOf': [{}, {'type': 'null'}]})() in (Rule, Any)
        assert JsonSchemaParser({'type': 'object'})() == dict
        assert JsonSchemaParser({'type': 'array'})() == list
        assert JsonSchemaParser({'type': 'string'})() == str
        assert JsonSchemaParser({'type': 'string', 'format': 'date'})() == date

    def test_schema_generator(self):
        class TestSchema(utype.Schema):
            int_val: int
            str_val: str
            bytes_val: bytes
            float_val: float
            bool_val: bool
            uuid_val: UUID
            # test nest types
            list_val: List[str] = utype.Field(default_factory=list)  # test callable default
            union_val: Union[int, List[int]] = utype.Field(default_factory=list)

        from utype.specs.json_schema.generator import JsonSchemaGenerator
        output = JsonSchemaGenerator(TestSchema)()
        assert output == {'type': 'object',
                          'properties': {'int_val': {'type': 'integer'},
                                         'str_val': {'type': 'string'},
                                         'bytes_val': {'type': 'string', 'format': 'binary'},
                                         'float_val': {'type': 'number', 'format': 'float'},
                                         'bool_val': {'type': 'boolean'},
                                         'uuid_val': {'type': 'string', 'format': 'uuid'},
                                         'list_val': {'type': 'array', 'items': {'type': 'string'}},
                                         'union_val': {'anyOf': [{'type': 'integer'},
                                                                 {'type': 'array', 'items': {'type': 'integer'}}]}},
                          'required': ['int_val',
                                       'str_val',
                                       'bytes_val',
                                       'float_val',
                                       'bool_val',
                                       'uuid_val']}

    def test_forward_ref_generator(self):
        from utype.specs.json_schema.generator import JsonSchemaGenerator
        output = JsonSchemaGenerator(TargetSchema)()
        assert output == {'type': 'object',
                          'properties': {'name': {'type': 'string'},
                                         'ref': {'anyOf': [{'type': 'object',
                                                            'properties': {'value': {'type': 'integer'}}},
                                                           {'type': 'null'}]},
                                         'ref_values': {'type': 'array',
                                                        'items': {'type': 'object',
                                                                  'properties': {'value': {'type': 'integer'}}}}},
                          'required': ['name']}

    def test_recursive_generator(self):
        from utype.specs.json_schema.generator import JsonSchemaGenerator
        refs = {}
        ref_output = JsonSchemaGenerator(InfiniteSchema, defs=refs)()
        assert ref_output == {'$ref': '#/$defs/InfiniteSchema'}
        assert refs == {InfiniteSchema: {'type': 'object',
                                         'properties': {'name': {'type': 'string'},
                                                        'self': {'type': 'array',
                                                                 'items': {'$ref': '#/$defs/InfiniteSchema'}}},
                                         'required': ['name']}}

        output = JsonSchemaGenerator(InfiniteSchema)()
        assert output == {'type': 'object',
                          'properties': {'name': {'type': 'string'},
                                         'self': {'type': 'array', 'items': {'$ref': '#/$defs/InfiniteSchema'}}},
                          'required': ['name']}
