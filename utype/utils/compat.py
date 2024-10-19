"""
Python type hint standard may vary from versions
"""
import sys
import typing
from typing import (Any, ClassVar, ForwardRef, Optional, Tuple,  # type: ignore
                    Type, Union)

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

try:
    from types import UnionType
except ImportError:
    UnionType = Union

try:
    from typing import Final
except ImportError:
    from typing_extensions import Final

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

try:
    from typing import Required
except ImportError:
    from typing_extensions import Required


__all__ = [
    "get_origin",
    "get_args",
    'Literal',
    'Final',
    'Self',
    'Required',
    'UnionType',
    "ForwardRef",
    "Annotated",
    "is_final",
    "is_union",
    "is_classvar",
    "is_annotated",
    "evaluate_forward_ref",
    'JSON_TYPES'
]

if sys.version_info < (3, 8):

    def get_origin(t) -> Optional[Type[Any]]:
        return getattr(t, "__origin__", None)

    def get_args(t) -> Tuple[Type[Any], ...]:
        return getattr(t, "__args__", ())

else:
    from typing import get_args as _typing_get_args
    from typing import get_origin as _typing_get_origin

    def get_origin(t) -> Optional[Type[Any]]:
        return _typing_get_origin(t) or getattr(t, "__origin__", None)

    def get_args(t) -> Tuple[Type[Any], ...]:
        args = getattr(t, "__args__", ())
        if args == ():
            # typing.get_args(typing.Callable) will throw an error
            return args
        return _typing_get_args(t) or args


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


_AnnotatedTypeNames = {'AnnotatedMeta', '_AnnotatedAlias'}


def is_annotated(ann_type) -> bool:
    # duck type check for Annotated, name in AnnotatedTypeNames and have __origin__ attribute
    return type(ann_type).__name__ in _AnnotatedTypeNames and getattr(ann_type, '__origin__', None)


def is_final(ann_type) -> bool:
    return _check_final(ann_type) or _check_final(getattr(ann_type, "__origin__", None))


ATOM_TYPES = (str, int, bool, float, type(None))
JSON_TYPES = (*ATOM_TYPES, list, dict)
# types thar can directly dump to json
# COMMON_TYPES = (*JSON_TYPES, set, tuple, bytes, *VENDOR_TYPES)
