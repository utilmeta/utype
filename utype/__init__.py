from .utils.transform import TypeTransformer, register_transformer, type_transform
from .utils.encode import register_encoder
from .parser.rule import Rule, Lax
from .parser.field import Field
from .parser.options import Options
from .schema import Schema, DataClass, LogicalMeta
from .utils import exceptions as exc
from .decorator import parse, handle, apply, dataclass


VERSION = (0, 2, 0, None)


def _get_version():
    pre_release = VERSION[3] if len(VERSION) > 3 else ""
    version = ".".join([str(v) for v in VERSION[:3]])
    if pre_release:
        version += f"-{pre_release}"
    return version


__version__ = _get_version()
