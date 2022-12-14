from .decorator import apply, dataclass, handle, parse, raw
from .parser.field import Field, Param
from .parser.options import Options
from .parser.rule import Lax, Rule
from .schema import DataClass, LogicalMeta, Schema
from .utils import exceptions as exc
from .utils.encode import register_encoder
from .utils.transform import (TypeTransformer, register_transformer,
                              type_transform)

VERSION = (0, 2, 1, None)


def _get_version():
    pre_release = VERSION[3] if len(VERSION) > 3 else ""
    version = ".".join([str(v) for v in VERSION[:3]])
    if pre_release:
        version += f"-{pre_release}"
    return version


__version__ = _get_version()


def version_info() -> str:
    import platform
    import sys
    from pathlib import Path

    info = {
        'utype version': __version__,
        'installed path': Path(__file__).resolve().parent,
        'python version': sys.version,
        'platform': platform.platform(),
    }
    return '\n'.join('{:>30} {}'.format(k + ':', str(v).replace('\n', ' ')) for k, v in info.items())
