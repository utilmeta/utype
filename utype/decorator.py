import inspect
import warnings
from typing import Any, Callable, Iterable, Type, TypeVar, Union

from .parser.cls import ClassParser
from .parser.func import FunctionParser
from .parser.options import Options
from .parser.rule import Lax, Rule
from .utils import exceptions as exc
from .utils.datastructures import Unprovided, unprovided

T = TypeVar("T")
FUNC = TypeVar("FUNC")
CLS = TypeVar("CLS")


def raw(f: FUNC):
    parser = getattr(f, "__parser__", None)
    if isinstance(parser, FunctionParser):
        return parser.obj
    return f


def parse(
    f: T = None,
    # /,  compat 3.7
    *,
    parser_cls: Type[FunctionParser] = FunctionParser,
    options: Union[Options, Type[Options]] = None,
    no_cache: bool = False,
    # static: bool = False,
    ignore_params: bool = False,
    ignore_result: bool = False,
    eager: bool = False,
) -> Union[T, Callable[[T], T]]:
    if ignore_params and ignore_result:
        warnings.warn(
            f"@utype.parse: you turn off both params and result parse in @parse decorator,"
            f" which is basically meaningless..."
        )

    def decorator(func: T) -> T:
        if inspect.isclass(func):
            # class
            parser_cls.apply_class(
                func,
                options=options,
                no_cache=no_cache,
                ignore_result=ignore_result,
                ignore_params=ignore_params,
                eager=eager,
            )
            return func
        else:
            parser = parser_cls.apply_for(func, options=options, no_cache=no_cache)
            return parser.wrap(
                parse_params=not ignore_params,
                parse_result=not ignore_result,
                eager_parse=eager
                # first_reserve=not static
            )

    if f:
        return decorator(f)
    return decorator


def dataclass(
    obj: CLS = None,
    # /,  compat 3.7
    *,
    parser_cls: Type[ClassParser] = ClassParser,
    options: Union[Options, Type[Options]] = None,
    no_cache: bool = False,
    no_parse: bool = False,
    set_class_properties: bool = False,
    post_init: Callable = None,
    post_setattr: Callable = None,
    post_delattr: Callable = None,
    contains: bool = False,
    repr: bool = True,  # noqa
    eq: bool = False,
) -> Union[CLS, Callable[[CLS], CLS]]:
    def decorator(cls: CLS) -> CLS:
        parser = parser_cls.apply_for(cls, options=options, no_cache=no_cache)

        parser.make_init(
            # init_super=init_super,
            # allow_runtime=allow_runtime,
            # set_attributes=init_attributes,
            # coerce_property=init_properties,
            no_parse=no_parse,
            post_init=post_init,
        )
        if repr:
            parser.make_repr()
        if eq:
            parser.make_eq()
        if contains:
            parser.make_contains()
        if set_class_properties:
            parser.assign_properties(
                post_setattr=post_setattr, post_delattr=post_delattr
            )
        elif post_setattr or post_delattr:
            warnings.warn(
                f"@utype.dataclass received post_delattr / post_setattr "
                f'without "set_properties=True", these params won\'t take effect'
            )

        cls.__parser__ = parser
        # set the flag so that class parser can be quickly resolve
        # and transformer can be register

        return parser.obj

    if obj:
        return decorator(obj)
    return decorator


def apply(
    rule_cls: Type[Rule] = Rule,
    *,
    # init: bool = False,     # whether to override init
    # -- constraints:
    const: Any = unprovided,
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
    decimal_places: int = None,
    round: int = None,
    multiple_of: int = None,
    # array
    contains: type = None,
    max_contains: int = None,
    min_contains: int = None,
    unique_items: bool = None,
):
    # if rule_cls:
    #     pass

    if round:
        if decimal_places and decimal_places not in (round, Lax(round)):
            raise exc.ConfigError(
                f"@apply round: {round} is a shortcut for decimal_places=Lax({round}), "
                f"but you specified a different decimal_places: {repr(decimal_places)}"
            )

        decimal_places = Lax(round)

    constraints = {
        k: v
        for k, v in dict(
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
            decimal_places=decimal_places,
            multiple_of=multiple_of,
            contains=contains,
            max_contains=max_contains,
            min_contains=min_contains,
            unique_items=unique_items,
        ).items()
        if v is not None
    }

    if not isinstance(const, Unprovided):
        constraints.update(const=const)

    def decorator(_type):
        cls = rule_cls.annotate(_type, constraints=constraints)
        cls.__name__ = getattr(_type, "__name__", cls.__name__)
        cls.__repr__ = getattr(_type, "__repr__", cls.__repr__)
        cls.__str__ = getattr(_type, "__str__", cls.__str__)
        cls.__applied__ = True
        # applied Rule only checks constraints if value is not the instance of the __origin__ type
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
