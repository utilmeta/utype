import inspect
import keyword
import re

from utype.parser.rule import Rule, LogicalType
from utype.parser.field import Field
from utype.parser.cls import ClassParser
from utype.parser.func import FunctionParser
from utype import unprovided, Options
from typing import Type, Dict, Any, ForwardRef
from utype.utils.functional import represent, valid_attr
from collections import deque

ORIGIN_MAP: dict = {
    list: 'List',
    dict: 'Dict',
    tuple: 'Tuple',
    set: 'Set',
    deque: 'Deque',
    frozenset: 'FrozenSet',
}


class PythonCodeGenerator:
    # pass in a defs dict to generate re-use '$defs'
    object_base_cls = 'utype.Schema'
    object_field_cls = 'utype.Field'

    def __init__(self, t,
                 defs: Dict[type, str] = None,
                 force_forward_ref: bool = False
                 # refs: Dict[str, dict] = None,
                 # with_schemas: bool = False,
                 # names: Dict[str, type] = None,
                 # ref_prefix: str = None,
                 # mode: str = None,
                 # output: bool = False
                 ):
        self.t = t
        self.defs = defs or {}
        self.force_forward_ref = force_forward_ref
        # self.refs = refs
        # self.schemas = {}
        # self.with_schemas = with_schemas

    def __call__(self) -> str:
        if inspect.isfunction(self.t):
            return self.generate_for_function(self.t)
        return self.generate_for_type(self.t, with_constraints=True, annotation=False)

    def generate_for_function(self, f, force_forward_ref: bool = None) -> str:
        if force_forward_ref is None:
            force_forward_ref = self.force_forward_ref

        parser: FunctionParser = getattr(f, '__parser__', None) or FunctionParser.apply_for(f)

        params = []
        if parser.first_reserve:
            if parser.instancemethod:
                params.append('self')
            elif parser.classmethod:
                params.append('cls')

        kinds = []
        for i, (k, v) in enumerate(parser.parameters):
            if kinds and all(kind == v.POSITIONAL_ONLY for kind in kinds) and v.kind == v.POSITIONAL_OR_KEYWORD:
                params.append('/')
            if not any(kind in (v.KEYWORD_ONLY, v.VAR_KEYWORD) for kind in kinds) and v.kind == v.KEYWORD_ONLY:
                params.append('*')

            kinds.append(v.kind)
            field = parser.get_field(k)
            if field:
                param_type = field.type
                param_default = field.field
            else:
                param_type = parser.parse_annotation(v.annotation) if v.annotation != v.empty else unprovided
                param_default = v.default if v.default != v.empty else unprovided

            arg_name = k
            if v.kind == v.VAR_POSITIONAL:
                arg_name = f'*{k}'
            elif v.kind == v.VAR_KEYWORD:
                arg_name = f'**{k}'

            args = [arg_name]
            if not unprovided(param_type) and param_type:
                annotation = self.generate_for_type(param_type, with_constraints=False, annotation=True)
                if not isinstance(field.type, ForwardRef):
                    if force_forward_ref:
                        annotation = repr(annotation)
                args.append(f': {annotation}')

            if not unprovided(param_default):
                if isinstance(param_default, Field):
                    default = self.generate_for_field(param_default)
                else:
                    default = represent(param_default)
                if default:
                    if len(args) == 1:
                        args.append(f'={default}')
                    else:
                        args.append(f' = {default}')
            params.append(''.join(args))

        return_annotation = None
        if parser.return_type:
            return_annotation = self.generate_for_type(parser.return_type, with_constraints=False, annotation=True)

        func_content = f'def {f.__name__}(%s)' % ', '.join(params)
        if return_annotation:
            func_content += f' -> {return_annotation}: pass'
        else:
            func_content += ': pass'
        return func_content

    def generate_for_type(self, t, with_constraints: bool = True, annotation: bool = True) -> str:
        if t is None:
            return 'Any'
        if isinstance(t, str):
            return t
        if isinstance(t, ForwardRef):
            return repr(t.__forward_arg__)
        if not isinstance(t, type) or t in (Any, Rule):
            return 'Any'
        if isinstance(t, LogicalType):
            if t.combinator:
                arg_list = [self.generate_for_type(arg, with_constraints=with_constraints, annotation=True)
                            for arg in t.args]
                if not arg_list:
                    return 'Any'
                if t.combinator == '|':
                    if len(t.args) == 2 and type(None) in t.args:
                        index = 0 if t.args[1] is type(None) else 1
                        return f'Optional[{arg_list[index]}]'
                    return f'Union[%s]' % ', '.join(arg_list)
                elif t.combinator == '~':
                    return '~' + arg_list[0]
                return str(f' {t.combinator} ').join(arg_list)
            elif issubclass(t, Rule):
                return self.generate_for_rule(t, with_constraints=with_constraints, annotation=annotation)
        elif isinstance(getattr(t, "__parser__", None), ClassParser) and not annotation:
            return self.generate_for_dataclass(t)
            # if not annotation or (self.with_schemas and t != self.t):
            #     content = self.generate_for_dataclass(t)
            #     if not annotation:
            #         return content
        return represent(t) if t else 'Any'

    def generate_for_rule(self, t: Type[Rule], with_constraints: bool = True, annotation: bool = True) -> str:
        constraints = {}
        if with_constraints:
            for name, val, func in t.__validators__:
                constraints[name] = getattr(t, name, val)
        origin = t.__origin__
        args = []
        if t.__args__:
            origin_str = ORIGIN_MAP.get(origin) or self.generate_for_type(origin, with_constraints=False)
            args = [self.generate_for_type(arg, with_constraints=True) for arg in t.__args__]
            type_str = f'{origin_str}[%s]' % (', '.join(args))
        else:
            type_str = self.generate_for_type(origin, with_constraints=False)

        if annotation:
            if constraints:
                constraints_str = ('utype.Field(%s)' %
                                   (', '.join([f'{k}={represent(v)}' for k, v in constraints.items()])))
                return f'Annotated[{type_str}, {constraints_str}]'
            return type_str
        else:
            lines = [f'class {t.__name__}({type_str}, Rule):']
            if t.__doc__:
                lines.append(f'\t"""{t.__doc__}"""')
            if args:
                lines.append('\t__args__ = [%s]' % ', '.join(args))
            if constraints:
                for name, val in constraints.items():
                    lines.append(f'\t{name} = {represent(val)}')
            if len(lines) == 1:
                lines.append('\tpass')
            return '\n'.join(lines)

    @classmethod
    def generate_for_field(cls, field: Field, addition: dict = None) -> str:
        if not field.__spec_kwargs__ and not addition and field.__class__ == Field:
            return ''
        name = None
        if field.__class__ == Field:
            name = cls.object_field_cls
        return field._repr(name=name, addition=addition)

    @classmethod
    def get_constraints(cls, t) -> dict:
        if isinstance(t, LogicalType) and issubclass(t, Rule):
            constraints = cls.get_constraints(t.__origin__)
            for name, val, func in t.__validators__:
                constraints[name] = getattr(t, name, val)
            return constraints
        return {}

    @classmethod
    def get_attname(cls, name: str, excludes: list = None) -> str:
        if name.isidentifier():
            name = re.sub('[^A-Za-z0-9]+', '_', name)
            if not name.isidentifier():
                name = 'key_' + name
        elif keyword.iskeyword(name):
            name = name + '_'
        if excludes:
            while name in excludes:
                name = name + '_1'
        return name

    def generate_for_dataclass(self, t, force_forward_ref: bool = None) -> str:
        if force_forward_ref is None:
            force_forward_ref = self.force_forward_ref

        parser: ClassParser = getattr(t, '__parser__')
        cls_name = parser.name.split('.')[-1]
        name_line = f'class {cls_name}({self.object_base_cls}):'
        options_line = None
        if not parser.options.vacuum:
            if parser.options.__class__ == Options:
                options_line = f'\t__options__ = utype.{repr(parser.options)}'
            else:
                options_line = f'\t__options__ = {repr(parser.options)}'

        lines = [name_line]
        if t.__doc__:
            lines.append(f'\t"""{t.__doc__}"""')
        if options_line:
            lines.append(options_line)
        attrs = []
        attr_names = []
        for name, field in parser.fields.items():
            attname = field.attname or name
            type_str = self.generate_for_type(field.type, with_constraints=False, annotation=True)
            if not isinstance(field.type, ForwardRef):
                if force_forward_ref:
                    type_str = repr(type_str)
            addition = dict(self.get_constraints(field.type))
            if not valid_attr(attname):
                attname = self.get_attname(attname, excludes=attr_names)
                addition.update(alias=name)
            field_str = self.generate_for_field(field.field, addition=addition) or None
            attr_names.append(attname)
            parts = [attname]
            if type_str:
                parts.extend([f': {type_str}'])
            if field_str:
                parts.extend([f' = {field_str}'])
            attrs.append('\t' + ''.join(parts))
        lines.extend(attrs)
        if len(lines) == 1:
            lines.append('\tpass')
        content = '\n'.join(lines)
        return content
