"""
Python type hint standard may vary from versions
"""

import sys
import typing
from typing import (  # type: ignore
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable as TypingCallable,
    ClassVar,
    Final,
    Dict,
    ForwardRef,
    Generator,
    Iterable,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


__all__ = [
    "get_origin",
    "get_args",
    "ForwardRef",
    "is_final",
    "is_union",
    "is_classvar",
    "evaluate_forward_ref",
]

if sys.version_info < (3, 8):

    def get_origin(t) -> Optional[Type[Any]]:
        return getattr(t, "__origin__", None)

    def get_args(t) -> Tuple[Type[Any], ...]:
        return getattr(t, "__args__", ())

else:
    from typing import get_origin as _typing_get_origin
    from typing import get_args as _typing_get_args

    def get_origin(tp) -> Optional[Type[Any]]:
        return _typing_get_origin(tp) or getattr(tp, "__origin__", None)

    def get_args(t) -> Tuple[Type[Any], ...]:
        return _typing_get_args(t) or getattr(t, "__args__", ())


try:
    from typing import ForwardRef  # type: ignore

    def evaluate_forward_ref(ref: ForwardRef, globalns: Any, localns: Any):
        return typing._eval_type(ref, globalns, localns)  # noqa

except ImportError:
    # python 3.6
    from typing import _ForwardRef as ForwardRef  # noqa

    def evaluate_forward_ref(ref: ForwardRef, globalns: Any, localns: Any):
        return ref._eval_type(globalns, localns)  # noqa


if sys.version_info < (3, 10):

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union

else:
    import types
    import typing

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union or tp is types.UnionType  # noqa


def _check_classvar(v) -> bool:
    return type(v) == type(ClassVar) and (
        sys.version_info < (3, 7) or getattr(v, "_name", None) == "ClassVar"
    )


def _check_final(v) -> bool:
    return type(v) == type(Final) and (
        sys.version_info < (3, 7) or getattr(v, "_name", None) == "Final"
    )


def is_classvar(ann_type) -> bool:
    return _check_classvar(ann_type) or _check_classvar(
        getattr(ann_type, "__origin__", None)
    )


def is_final(ann_type) -> bool:
    return _check_final(ann_type) or _check_final(getattr(ann_type, "__origin__", None))


ATOM_TYPES = (str, int, bool, float, type(None))
JSON_TYPES = (*ATOM_TYPES, list, dict)
# types thar can directly dump to json
# COMMON_TYPES = (*JSON_TYPES, set, tuple, bytes, *VENDOR_TYPES)

