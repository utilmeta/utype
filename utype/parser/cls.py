from .base import BaseParser
from .func import FunctionParser
from ..utils.compat import is_classvar, is_final
import inspect


class ClassParser(BaseParser):
    function_parser_cls = FunctionParser

    def setup(self):
        self.generate_from_bases()
        super().setup()
        self.generate_init_parser()

    def validate_class_field_name(self, name: str):
        if not self.validate_field_name(name):
            return False
        for base in self.obj.__bases__:
            annotation = base.__annotations__.get(name)
            if annotation:
                if is_final(annotation):
                    raise TypeError(f'field: {repr(name)} was declared as Final in {base}, '
                                    f'so {self.obj} cannot annotate it again')
            attr = getattr(base, name, None)
            if self.is_class_internals(attr, attname=name, class_qualname=base.__qualname__):
                raise TypeError(f'field: {repr(name)} was declared in {base}, '
                                f'so {self.obj} cannot annotate it again')
        return True

    @classmethod
    def is_class_internals(cls, attr, attname: str, class_qualname: str):
        qualname: str = getattr(attr, '__qualname__', None)
        name: str = getattr(attr, '__name__', None)
        if name and qualname:
            if attname == name and qualname.startswith(f'{class_qualname}.'):
                return True
        return False

    def generate_fields(self):
        exclude_vars = self.exclude_vars
        fields = []

        annotations = getattr(self.obj, '__annotations__', {})
        for key, annotation in annotations.items():
            if (
                not self.validate_class_field_name(key)
                or is_classvar(annotation)
                # or is_final(annotation)
            ):
                exclude_vars.add(key)
                continue
            default = self.obj.__dict__.get(key, ...)
            fields.append(self.schema_field_cls.generate(
                attname=key,
                annotation=annotation,
                default=default,
                global_vars=self.globals,
                forward_refs=self.forward_refs,
                options=self.options
            ))

        for key, attr in self.obj.__dict__.items():
            if key in annotations:
                continue
            if (
                attr is ...
                # if this attr is a field in bases, this means to exclude this field in current class
                # otherwise this attr declared that this field is never take from input
                # or isinstance(attr, property)
                or self.is_class_internals(attr, attname=key, class_qualname=self.obj_name)
                or not self.validate_class_field_name(key)
            ):
                exclude_vars.add(key)
                continue
            if key in exclude_vars:
                continue
            fields.append(self.schema_field_cls.generate(
                attname=key,
                annotation=None,
                default=attr,
                global_vars=self.globals,
                forward_refs=self.forward_refs,
                options=self.options
            ))

        field_map = {}
        for field in fields:
            if field.name in field_map:
                raise ValueError(f'{self.obj}: field name: {repr(field.name)} conflicted at '
                                 f'{field}, {field_map[field.name]}')
            field_map[field.name] = field
        self.fields.update(field_map)

    def generate_from_bases(self):
        if not inspect.isclass(self.obj):
            return

        fields = {}
        alias_map = {}
        attr_alias_map = {}
        case_insensitive_names = set()
        exclude_vars = set()
        option_list = []

        for base in reversed(self.obj.__bases__):   # according to MRO
            if not isinstance(base, type(self.obj)) or base is object:
                continue
            parser = self.apply_for(base)       # should use cache
            if not parser.options.vacuum:
                option_list.append(parser.options)

            fields.update(parser.fields)

            exclude_vars.update(parser.exclude_vars)
            alias_map.update(parser.field_alias_map)
            attr_alias_map.update(parser.attr_alias_map)
            case_insensitive_names.update(parser.case_insensitive_names)

        cls_options = getattr(self.obj, '__options__', None)
        if cls_options:
            option_list.append(cls_options)

        self.options = self.options_cls.generate_from(*option_list)
        self.fields = fields
        self.exclude_vars = exclude_vars
        self.field_alias_map = alias_map
        self.attr_alias_map = attr_alias_map
        self.case_insensitive_names = case_insensitive_names

    def generate_init_parser(self):
        if not inspect.isclass(self.obj):
            return

        init_func = self.obj.__dict__.get('__init__')
        if not inspect.isfunction(init_func):
            # if init_func is already decorated like a Wrapper
            # we do not touch it either
            return

        # setattr(init_func, '__options__', self.options)     # set this options

        init_parser = self.function_parser_cls.apply_for(init_func)
        self.obj.__dict__['__init__'] = init_parser

        # the INPUT parser
        # we do not merge fields or options here
        # each part does there job
        # init just parse data as it declared and take it to initialize the class
        # class T(Schema):
        #     mul: int
        #     def __init__(self, a: float, b: int):
        #         super().__init__(mul=a * b)
        # we will make init_parser the "INPUT" parser

        # addition = self.init_parser.additional_options
        # if not addition.vacuum:
        #     self.options &= addition
        #
        # self.fields.update(self.init_parser.fields)
        # self.exclude_vars.update(self.init_parser.exclude_vars)
        # self.field_alias_map.update(self.init_parser.field_alias_map)
        # self.attr_alias_map.update(self.init_parser.attr_alias_map)
        # self.case_insensitive_names.update(self.init_parser.case_insensitive_names)
