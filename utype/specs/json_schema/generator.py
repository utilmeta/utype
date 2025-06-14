import inspect
from utype.parser.rule import Rule, LogicalType, SEQ_TYPES, MAP_TYPES
from utype.parser.field import ParserField
from utype.parser.cls import ClassParser
from utype.parser.func import FunctionParser
from utype.parser.base import Options

from typing import Optional, Type, Union, Dict
from utype.utils.datastructures import unprovided
from utype.utils.compat import JSON_TYPES, ForwardRef, evaluate_forward_ref
from enum import EnumMeta
from . import constant


class JsonSchemaGenerator:
    # pass in a defs dict to generate re-use '$defs'

    DEFAULT_PRIMITIVE = "string"
    DEFAULT_REF_PREFIX = "#/$defs/"

    def __init__(self, t,
                 defs: Dict[type, dict] = None,
                 names: Dict[str, type] = None,
                 ref_prefix: str = None,
                 mode: str = None,
                 output: bool = False
                 ):
        self.t = t
        self.defs = defs
        # self.recursive_types = []
        # handle infinite recursive forward ref if defs is empty

        self.names = names
        if isinstance(defs, dict) and self.names is None:
            self.names = {}

        self.ref_prefix = ref_prefix or self.DEFAULT_REF_PREFIX
        self.mode = mode
        self.output = output
        self.options = Options(mode=mode)
        # can generate based on mode and input/output

    def generate_for_type(self, t: type, recursive_types: set = None):
        if t is None:
            return {}
        if not isinstance(t, type):
            return {}
        if issubclass(t, Rule):
            return self.generate_for_rule(t, recursive_types=recursive_types)
        elif isinstance(getattr(t, "__parser__", None), ClassParser):
            return self.generate_for_dataclass(t, recursive_types=recursive_types)
        elif isinstance(t, LogicalType) and t.combinator:
            return self.generate_for_logical(t, recursive_types=recursive_types)
        elif isinstance(t, ForwardRef):
            # for more robust
            if t.__forward_evaluated__:
                return self.generate_for_type(t.__forward_value__, recursive_types=recursive_types)
            else:
                try:
                    annotation = evaluate_forward_ref(t, globals(), None)
                except NameError:
                    # ignore for now
                    return {}
                return self.generate_for_type(annotation, recursive_types=recursive_types)
        elif isinstance(t, EnumMeta):
            base = t.__base__
            enum_type = None
            enum_values = []
            enum_map = {}
            for key, val in t.__members__.items():
                enum_values.append(val.value)
                enum_map[key] = val.value
                enum_type = type(val.value)
            if not isinstance(base, EnumMeta):
                enum_type = base
            prim = self._get_primitive(enum_type)
            fmt = self._get_format(enum_type)
            data = {
                "type": prim,
                "enum": enum_values,
                "x-annotation": {
                    "enums": enum_map
                }
            }
            if fmt:
                data.update(format=fmt)
            return data

        # default common type
        prim = self._get_primitive(t)
        fmt = self._get_format(t)
        data = {"type": prim}
        if fmt:
            data.update(format=fmt)
        return data

    def generate_for_logical(self, t: LogicalType, recursive_types: set = None):
        operator_name = constant.OPERATOR_NAMES.get(t.combinator)
        if not operator_name:
            return {}
        conditions = [self.generate_for_type(cond, recursive_types=recursive_types) for cond in t.args]
        if operator_name == 'not':
            return {operator_name: conditions[0]}
        return {operator_name: conditions}

    def _get_format(self, origin: type) -> Optional[str]:
        if not origin:
            return None
        format = getattr(origin, 'format', None)
        if format and isinstance(format, str):
            return format
        for types, f in constant.FORMAT_MAP.items():
            if issubclass(origin, types):
                return f
        return None

    def _get_primitive(self, origin: type) -> str:
        if not origin:
            return self.DEFAULT_PRIMITIVE
        for types, pri in constant.PRIMITIVE_MAP.items():
            if issubclass(origin, types):
                return pri
        return self.DEFAULT_PRIMITIVE

    def _get_args(self, r: Type[Rule], recursive_types: set = None) -> dict:
        origin = r.__origin__
        args = r.__args__
        if not args:
            return {}
        if not origin:
            return {}
        args_res = [self.generate_for_type(arg, recursive_types=recursive_types) for arg in args]
        if issubclass(origin, tuple):
            if r.__ellipsis_args__:
                name = 'items'
                return {name: args_res[0]}
            else:
                name = 'prefixItems'
                return {name: args_res}
        elif issubclass(origin, SEQ_TYPES):
            name = 'items'
            return {name: args_res[0]}
        elif issubclass(origin, MAP_TYPES):
            name = 'patternProperties'
            key_arg: dict = args_res[0]
            val_arg: dict = args_res[1]
            pattern = dict(key_arg).get('pattern', None)
            if not pattern:
                fmt = key_arg.get('format') or key_arg.get('type')
                if fmt:
                    pattern = constant.FORMAT_PATTERNS.get(fmt)
            pattern = pattern or '.*'
            return {name: {pattern: val_arg}}
        else:
            return {}

    def __call__(self) -> dict:
        if inspect.isfunction(self.t):
            return self.generate_for_function(self.t)
        return self.generate_for_type(self.t)

    def get_defs(self) -> Dict[str, dict]:
        defs = {}
        for t, values in self.defs.items():
            name = self.get_def_name(t)
            defs[name] = values
        return defs

    def generate_for_rule(self, t: Type[Rule], recursive_types: set = None):
        name = t.__qualname__
        if isinstance(self.defs, dict):
            def_name = self.get_def_name(t)
            if def_name:
                return {"$ref": f"{self.ref_prefix}{def_name}"}

        # type
        origin = t.__origin__
        data = dict(self.generate_for_type(origin, recursive_types=recursive_types))
        primitive = getattr(t, 'primitive', None)
        if primitive in constant.PRIMITIVES:
            data.update(type=primitive)
        else:
            primitive = data.get('type', self.DEFAULT_PRIMITIVE)

        # format
        fmt = getattr(t, 'format', None)
        if fmt and isinstance(fmt, str):
            data.update(format=fmt)
        else:
            fmt = self._get_format(origin)
            if fmt and isinstance(fmt, str):
                data.update(format=fmt)

        # constraints
        constrains_map = constant.DEFAULT_CONSTRAINTS_MAP
        for types, mp in constant.TYPE_CONSTRAINTS_MAP.items():
            if primitive in types:
                constrains_map = mp
                break
        for constraint, value, validator in t.__validators__:
            constraint_name = constrains_map.get(constraint, constraint)
            data[constraint_name] = value

        extra = getattr(t, 'extra', None)
        if extra and isinstance(extra, dict):
            data.update(extra)
        if t.__args__:
            data.update(self._get_args(t, recursive_types=recursive_types))
        if isinstance(self.defs, dict) and name != 'Rule':
            if '<locals>' not in name:
                # not a auto created rule
                return {"$ref": f"{self.ref_prefix}{self.set_def(name, t, data)}"}
        return data

    def get_def_name(self, t: type):
        if t in self.defs:
            for k, v in self.names.items():
                if v == t:
                    return k
        return None

    def set_def(self, name: str, t: type, data: dict = None):
        if t in self.defs:
            if data is not None:
                # name already set
                self.defs[t] = data
            return name
        n = 0
        while True:
            _name = name + (f'_{n}' if n else '')
            if _name in self.names:
                n += 1
                continue
            name = _name
            break
            # de-duplicate name
        self.defs[t] = data
        self.names[name] = t
        return name

    def generate_for_field(self, f: ParserField,
                           options: Options = None,
                           recursive_types: set = None
                           ) -> Optional[dict]:
        if self.output:
            if f.always_no_output(options or self.options):
                return None
        else:
            if f.always_no_input(options or self.options):
                return None

        t = f.output_type if self.output else f.type
        if not isinstance(t, type):
            if self.output:
                t = t or f.type
            else:
                t = t or f.output_type

        data = dict(self.generate_for_type(
            t, recursive_types=recursive_types
        ))

        if f.field.title:
            data.update(title=f.field.title)
        if f.field.description:
            data.update(description=f.field.description)
        if f.field.deprecated:
            data.update(deprecated=f.field.deprecated)
        if f.field.mode:
            if f.field.mode == 'r':
                data.update(readOnly=True)
            elif f.field.mode == 'w':
                data.update(writeOnly=True)
        if not unprovided(f.field.example) and f.field.example is not None:
            example = f.field.example
            if type(f.field.example) not in JSON_TYPES:
                example = str(f.field.example)
            data.update(examples=[example])
        if f.aliases:
            aliases = list(f.aliases)
            if aliases:
                # sort to stay identical
                aliases.sort()
            data.update({
                'x-var-name': f.attname,
                'x-aliases': aliases,
                'aliases': aliases,     # compat old version, will be deprecated
            })

        annotations = f.schema_annotations
        if annotations:
            data.update({
                'x-annotation': annotations
            })
        return data

    def generate_for_dataclass(self, t, recursive_types: set = None):
        # name = t.__qualname__
        parser: ClassParser = getattr(t, '__parser__')
        if not isinstance(parser, ClassParser):
            raise TypeError(f'Invalid dataclass: {t}')
        parser.resolve_forward_refs()       # resolve before generate
        cls_name = parser.name
        mode = parser.options.mode
        if mode:
            cls_name += '_' + mode
        if self.output and not parser.in_out_identical:
            cls_name += '_O'

        if isinstance(self.defs, dict):
            def_name = self.get_def_name(t)
            if def_name:
                return {"$ref": f"{self.ref_prefix}{def_name}"}
            cls_name = self.set_def(cls_name, t, data=None)
            # set data to None:
            # avoid cascade references
        elif isinstance(recursive_types, set):
            # handle cascade forward ref
            if t in recursive_types:
                return {"$ref": f"{self.ref_prefix}{cls_name}"}
            recursive_types.add(t)

        data = {"type": "object"}
        required = []
        properties = {}
        dependent_required = {}
        options = parser.options

        if self.output:
            # handle output
            if parser.output_options:
                options = parser.output_options

        for name, field in parser.fields.items():
            value = self.generate_for_field(field, options=options, recursive_types=recursive_types or {t})
            if value is None:
                continue
            properties[name] = value
            if field.dependencies:
                dependent_required[name] = field.dependencies
            if field.is_required(options or self.options):
                # will count options.ignore_required in
                required.append(name)
            elif self.output:
                if not field.no_default:
                    # if field has default, the value is required in the output data
                    required.append(name)

        data.update(properties=properties)
        if required:
            data.update(required=required)
        if dependent_required:
            data.update(dependentRequired=dependent_required)
        addition = options.addition
        if addition is not None:
            if isinstance(addition, type):
                data.update(additionalProperties=self.generate_for_type(addition))
            else:
                data.update(additionalProperties=addition)

        annotations = parser.schema_annotations
        if annotations:
            data.update({
                'x-annotation': annotations
            })

        if isinstance(self.defs, dict):
            return {"$ref": f"{self.ref_prefix}{self.set_def(cls_name, t, data)}"}
        return data

    def generate_for_function(self, f):
        if not inspect.isfunction(f):
            raise TypeError(f'Invalid function: {f}')
        parser = getattr(f, '__parser__', None)
        if not isinstance(parser, FunctionParser):
            parser = FunctionParser.apply_for(f)
        data = {"type": "function"}
        pos_params = []
        required = []
        params = {}
        for name, field in parser.fields.items():
            value = self.generate_for_field(field, options=parser.options)
            if value is None:
                continue
            params[name] = value
            if field.positional_only:
                pos_params.append(name)
            if field.is_required(parser.options or self.options):
                required.append(name)
        data.update(parameters=params)
        if required:
            data.update(required=required)
        if pos_params:
            data.update(positionalOnly=pos_params)
        addition = parser.options.addition
        if addition is not None:
            if isinstance(addition, type):
                data.update(additionalParameters=self.generate_for_type(addition))
            else:
                data.update(additionalParameters=addition)
        return data
