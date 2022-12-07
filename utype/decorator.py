from typing import Any, Iterable, Callable, Type
import warnings
from .parser.func import FunctionParser
from .parser.cls import ClassParser
from .parser.options import Options
from .parser.rule import Rule
from .utils.transform import register_transformer


def parse(
    f=None,
    *,
    parser_cls: Type[FunctionParser] = FunctionParser,
    options: Options = None,
    no_cache: bool = False,
    ignore_params: bool = False,
    ignore_result: bool = False,
):
    if ignore_params and ignore_result:
        warnings.warn(
            f"you turn off both params and result parse in @parse decorator,"
            f" which is basically meaningless..."
        )

    def decorator(func):
        parser = parser_cls.apply_for(func, options=options, no_cache=no_cache)
        return parser.wrap(
            parse_params=not ignore_params, parse_result=not ignore_result
        )

    if f:
        return decorator(f)
    return decorator


def dataclass(
    obj=None,
    *,
    parser_cls: Type[ClassParser] = ClassParser,
    options: Options = None,
    no_cache: bool = False,
    # allow_runtime: bool = False,
    set_class_properties: bool = False,
    # init_super: bool = False,
    # init_attributes: bool = True,
    # init_properties: bool = False,
    post_init: Callable = None,
    post_setattr: Callable = None,
    post_delattr: Callable = None,
    contains: bool = False,
    repr: bool = True,  # noqa
):
    def decorator(cls):
        parser = parser_cls.apply_for(cls, options=options, no_cache=no_cache)

        parser.make_init(
            # init_super=init_super,
            # allow_runtime=allow_runtime,
            # set_attributes=init_attributes,
            # coerce_property=init_properties,
            post_init=post_init,
        )
        if repr:
            parser.make_repr()
        if contains:
            parser.make_contains()
        if set_class_properties:
            parser.assign_properties(
                post_setattr=post_setattr, post_delattr=post_delattr
            )
        elif post_setattr or post_delattr:
            warnings.warn(f'@utype.dataclass received post_delattr / post_setattr '
                          f'without "set_properties=True", these params won\'t take effect')

        return parser.obj

    if obj:
        return decorator(obj)
    return decorator


def apply(
    rule_cls: Type[Rule] = Rule,
    *,
    # init: bool = False,     # whether to override init
    # -- constraints:
    strict: bool = True,
    const: Any = ...,
    enum: Iterable = None,
    gt=None,
    ge=None,
    lt=None,
    le=None,
    regex: str = None,
    length: int = None,
    max_length: int = None,
    min_length: int = None,
    # number
    max_digits: int = None,
    round: int = None,
    multiple_of: int = None,
    # array
    contains: type = None,
    max_contains: int = None,
    min_contains: int = None,
    unique_items: bool = None,
):
    if rule_cls:
        pass

    constraints = {
        k: v
        for k, v in dict(
            strict=strict,
            enum=enum,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            length=length,
            regex=regex,
            max_digits=max_digits,
            round=round,
            multiple_of=multiple_of,
            contains=contains,
            max_contains=max_contains,
            min_contains=min_contains,
            unique_items=unique_items,
        ).items()
        if v is not None
    }

    if const is not ...:
        constraints.update(const=const)

    def decorator(_type):
        cls = rule_cls.annotate(_type, constraints=constraints)
        cls.__name__ = getattr(_type, '__name__', cls.__name__)
        cls.__repr__ = getattr(_type, '__repr__', cls.__repr__)
        cls.__str__ = getattr(_type, '__str__', cls.__str__)
        return cls
        #
        # if init:
        #     pass
        # else:
        #     @register_transformer(_type)
        #     def _transform_type(trans, value, t):
        #         return type_cls(value)
        #
        #     _transform_type.__name__ = f'_to_{getattr(_type, "__name__", str(_type))}'
        # return _type

    return decorator


def handle(*func_and_errors):
    # implement in next version
    pass
