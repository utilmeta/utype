from typing import Any, Iterable
import warnings
from .parser.func import FunctionParser
from .parser.cls import ClassParser
from .parser.options import Options


def parse(f=None, *, mode: str = None,
          options=None,
          ignore_params: bool = False,
          ignore_result: bool = False):
    if ignore_params and ignore_result:
        warnings.warn(f'you turn off both params and result parse in @parse decorator,'
                      f' which is basically meaningless...')

    if mode:
        if options:
            options = options & Options(mode=mode)
        else:
            options = Options(mode=mode)

    def decorator(func):
        parser = FunctionParser.apply_for(func)
        return parser.wrap(
            options=options,
            parse_params=not ignore_params,
            parse_result=not ignore_result
        )

    if f:
        return decorator(f)
    return decorator


def dataclass(
    obj=None, *,
    options: Options = None,
    init: bool = True,
    repr: bool = True,   # noqa
    setattr: bool = False,  # noqa
    delattr: bool = False   # noqa
):
    def decorator(cls):
        parser = ClassParser.apply_for(cls)
        return parser.wrap(
            options=options,
            parse_params=not ignore_params,
            parse_result=not ignore_result
        )


def apply(
    rule_cls=None, *,
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
    pass


def handle(*func_and_errors):
    pass
