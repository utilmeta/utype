from typing import Dict, Union, Tuple, Any, List, Type
from utype.utils.compat import ForwardRef
from utype.parser.rule import LogicalType, Rule
from utype.parser.field import Field
from utype.schema import LogicalMeta, Schema, DataClass
from utype.parser.options import Options
from utype.utils.datastructures import unprovided
from . import constant

_type = type


class JsonSchemaParser:
    object_base_cls = Schema
    object_meta_cls = LogicalMeta
    object_options_cls = Options
    field_cls = Field
    default_type = str

    def __init__(self, json_schema: dict,
                 refs: Dict[str, type] = None,
                 name: str = None,
                 description: str = None,
                 # '#/components/...': SchemaClass
                 # names: Dict[str, type] = None,
                 ref_prefix: str = None,    # '#/components/schemas'
                 def_prefix: str = None,    # 'schemas'
                 type_map: dict = None,
                 ):

        if not isinstance(json_schema, dict):
            raise TypeError(f'Invalid json schema: {json_schema}')
        self.json_schema = json_schema
        self.refs = refs
        self.name = name
        self.description = description
        self.ref_prefix = (ref_prefix.rstrip('/') + '/') if ref_prefix else ''
        self.def_prefix = (def_prefix.rstrip('.') + '.') if def_prefix else ''
        _type_map = dict(constant.TYPE_MAP)
        if type_map:
            _type_map.update(type_map)
        self.type_map = _type_map

    def get_def_name(self, ref: str) -> str:
        ref_name = ref.lstrip(self.ref_prefix)
        return self.def_prefix + ref_name

    # def parse_type(self, schema: dict) -> type:
    #     return self.__class__(
    #         json_schema=schema,
    #         refs=self.refs,
    #         ref_prefix=self.ref_prefix,
    #         def_prefix=self.def_prefix,
    #     ).parse(type_only=True)

    @classmethod
    def get_constraints(cls, schema: dict):
        constraints = {}
        for key, val in schema.items():
            if key in constant.CONSTRAINTS_MAP:
                constraints[constant.CONSTRAINTS_MAP[key]] = val
        return constraints

    def parse_field(self, schema: dict,
                    field_cls: Type[Field] = None,
                    required: bool = None,
                    description: str = None,
                    dependencies: List[str] = None,
                    **kwargs,
                    ) -> Tuple[type, Field]:
        type = self.parse_type(schema, with_constraints=False)
        # annotations
        default = schema.get('default', unprovided)
        deprecated = schema.get('deprecated', False)
        title = schema.get('title')
        description = schema.get('description') or description
        readonly = schema.get('readOnly')
        writeonly = schema.get('writeOnly')
        kwargs.update(self.get_constraints(schema))
        kwargs.update(
            default=default,
            deprecated=deprecated,
            title=title,
            description=description,
            readonly=readonly,
            writeonly=writeonly,
            required=required,
            dependencies=dependencies
        )
        field_cls = field_cls or self.field_cls
        return type, field_cls(**kwargs)

    def __call__(self, *args, **kwargs):
        return self.parse_type(
            self.json_schema,
            name=self.name,
            description=self.description,
            with_constraints=True
        )

    def parse_type(self, schema: dict,
                   name: str = None,
                   description: str = None,
                   with_constraints: bool = True):
        ref = schema.get('$ref')
        type = schema.get('type')
        any_of = schema.get('anyOf')
        one_of = schema.get('oneOf')
        all_of = schema.get('allOf')
        not_of = schema.get('not')
        const = schema.get('const', unprovided)
        enum = schema.get('enum')
        conditions = any_of or one_of or all_of or ([not_of] if not_of else [])
        value = const if not unprovided(const) else enum[0] if enum else unprovided

        if ref:
            return ForwardRef(self.get_def_name(ref))

        constraints = {}
        if with_constraints:
            constraints = self.get_constraints(schema)

        t = self.default_type
        if type:
            if type == 'array':
                return self.parse_array(
                    schema,
                    name=name,
                    description=description,
                    constraints=constraints
                )
            elif type == 'object':
                return self.parse_object(
                    schema,
                    name=name,
                    description=description,
                    constraints=constraints
                )
            else:
                format = schema.get('format')
                t = None
                if format:
                    t = self.type_map.get(format)
                t = t or self.type_map.get(type) or self.default_type

        elif not unprovided(value):
            t = type(value)
        elif conditions:
            condition_types = [self.parse_type(cond) for cond in conditions]
            if any_of:
                t = LogicalType.any_of(*condition_types)
            elif all_of:
                t = LogicalType.all_of(*condition_types)
            elif one_of:
                t = LogicalType.one_of(*condition_types)
            elif not_of:
                t = LogicalType.not_of(*condition_types)

        if constraints:
            return Rule.annotate(
                t,
                name=name,
                description=description,
                constraints=constraints
            )
        return t

    def parse_object(self,
                     schema: dict,
                     name: str = None,
                     description: str = None,
                     constraints: dict = None
                     ):
        name = name or 'ObjectSchema'
        properties = schema.get('properties') or {}
        required = schema.get('required') or []
        additional_properties = schema.get("additionalProperties", unprovided)
        min_properties = schema.get("minProperties", unprovided)
        max_properties = schema.get("maxProperties", unprovided)
        property_names = schema.get("propertyNames")
        dependent_required = schema.get('dependentRequired')
        pattern_properties = schema.get("patternProperties")  # not supported now

        if not properties:
            if property_names:
                key_obj = {'type': 'string'}
                key_obj.update(property_names)
                key_type = self.parse_type(key_obj)
            else:
                key_type = str
            constraints = dict(constraints or {})
            if min_properties:
                constraints.update(min_length=min_properties)
            if max_properties:
                constraints.update(max_length=max_properties)
            return Rule.annotate(dict, key_type, Any, constraints=constraints)

        attrs = {}
        annotations = {}
        options = self.object_options_cls(
            max_params=max_properties,
            min_params=min_properties,
            addition=self.parse_type(additional_properties) if isinstance(additional_properties, dict)
            else additional_properties,
        )

        for key, prop in properties.items():
            field_required = key in required if required else False
            field_dependencies = dependent_required.get(key) if dependent_required else None
            field_type, field = self.parse_field(
                prop,
                required=field_required,
                dependencies=field_dependencies
            )
            annotations[key] = field_type
            attrs[key] = field

        attrs.update(
            __annotations__=annotations,
            __options__=options
        )
        if description:
            attrs.update(__doc__=description)
        new_cls = self.object_meta_cls(name, (self.object_base_cls,), attrs)
        return new_cls

    def parse_array(self,
                    schema: dict,
                    name: str = None,
                    description: str = None,
                    constraints: dict = None
                    ):
        items = schema.get('items')
        prefix_items = schema.get('prefixItems')
        args = []
        origin = list
        addition = None

        if prefix_items:
            origin = tuple
            args = [self.parse_type(item) for item in prefix_items]

            if items is False:
                addition = False
            elif items:
                addition = self.parse_type(items, with_constraints=True)

        elif items:
            items_type = self.parse_type(items, with_constraints=True)
            args = [items_type]

        options = Options(addition=addition) if addition is not None else None
        return Rule.annotate(
            origin, *args,
            name=name,
            description=description,
            constraints=constraints,
            options=options
        )


class JsonSchemaGroupParser:
    schema_parser_cls = JsonSchemaParser

    # '#/components/schemas/...'
    def __init__(self, schemas: Dict[str, dict],
                 # '#/components/...': SchemaClass
                 # names: Dict[str, type] = None,
                 ref_prefix: str = None,  # '#/components/schemas'
                 def_prefix: str = None,  # 'schemas'
                 ):
        self.schemas = schemas
        self.ref_prefix = (ref_prefix.rstrip('/') + '/') if ref_prefix else ''
        self.def_prefix = (def_prefix.rstrip('.') + '.') if def_prefix else ''
        self.refs = {}

    def __call__(self, *args, **kwargs):
        pass

    def parse(self):
        for name, schema in self.schemas.items():
            cls = self.schema_parser_cls(
                json_schema=schema,
                name=name,
                refs=self.refs,
                ref_prefix=self.ref_prefix,
                def_prefix=self.def_prefix
            )()
            ref_name = self.ref_prefix + name
            self.refs[ref_name] = cls
        return self.refs

# class schemas:
#     class Int:
#         pass
#
#     class A:
#         a: 'schemas.Int'