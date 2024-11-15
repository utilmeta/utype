from decimal import Decimal
from datetime import datetime, date, time, timedelta
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address
from utype.parser.rule import SEQ_TYPES, MAP_TYPES

PRIMITIVES = ("null", "boolean", "object", "array", "integer", "number", "string")
PRIMITIVE_MAP = {
    type(None): "null",
    bool: "boolean",
    MAP_TYPES: "object",
    SEQ_TYPES: "array",
    int: "integer",
    (float, Decimal): "number",
}
TYPE_MAP = {
    'null': type(None),
    'string': str,
    'boolean': bool,
    'bool': bool,
    'object': dict,
    'array': list,
    'integer': int,
    'int': int,
    'bigint': int,
    'number': float,
    'float': float,
    'decimal': Decimal,
    'binary': bytes,
    'ipv4': IPv4Address,
    'ipv6': IPv6Address,
    'date-time': datetime,
    'date': date,
    'time': time,
    'duration': timedelta,
    'uuid': UUID,
}
OPERATOR_NAMES = {
    "&": "allOf",
    "|": "anyOf",
    "^": "oneOf",
    "~": "not",
}
FORMAT_MAP = {
    (bytes, bytearray, memoryview): 'binary',
    float: 'float',
    IPv4Address: 'ipv4',
    IPv6Address: 'ipv6',
    datetime: 'date-time',
    date: 'date',
    time: 'time',
    timedelta: 'duration',
    UUID: 'uuid'
}
DEFAULT_CONSTRAINTS_MAP = {
    'enum': 'enum',
    'const': 'const',
}
CONSTRAINTS_MAP = {
    'multipleOf': 'multiple_of',
    'maximum': 'le',
    'minimum': 'ge',
    'exclusiveMaximum': 'lt',
    'exclusiveMinimum': 'gt',
    'decimalPlaces': 'decimal_places',
    'maxDigits': 'max_digits',
    'enum': 'enum',
    'const': 'const',
    'maxItems': 'max_length',
    'minItems': 'min_length',
    'uniqueItems': 'unique_items',
    'maxContains': 'max_contains',
    'minContains': 'min_contains',
    'contains': 'contains',
    'maxProperties': 'max_length',
    'minProperties': 'min_length',
    'minLength': 'min_length',
    'maxLength': 'max_length',
    'pattern': 'regex',
}

TYPE_CONSTRAINTS_MAP = {
    ("integer", "number"): {
        'multiple_of': 'multipleOf',
        'le': 'maximum',
        'lt': 'exclusiveMaximum',
        'ge': 'minimum',
        'gt': 'exclusiveMinimum',
        'decimal_places': 'decimalPlaces',
        'max_digits': 'maxDigits',
        **DEFAULT_CONSTRAINTS_MAP,
    },
    ("array",): {
        'max_length': 'maxItems',
        'min_length': 'minItems',
        'unique_items': 'uniqueItems',
        'max_contains': 'maxContains',
        'min_contains': 'minContains',
        'contains': 'contains',
        **DEFAULT_CONSTRAINTS_MAP,
    },
    ("object",): {
        'max_length': 'maxProperties',
        'min_length': 'minProperties',
        **DEFAULT_CONSTRAINTS_MAP,
    },
    ("string",): {
        'regex': 'pattern',
        'max_length': 'maxLength',
        'min_length': 'minLength',
        **DEFAULT_CONSTRAINTS_MAP,
    },
    ("boolean", "null"): DEFAULT_CONSTRAINTS_MAP
}

FORMAT_PATTERNS = {
    'integer': r'[-]?\d+',
    'number': r'[-]?\d+(\.\d+)?',
    'date': r'\d{4}-\d{2}-\d{2}',
}
