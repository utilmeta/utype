from .utils.transform import TypeTransformer, register_transformer, type_transform
from .utils.encode import register_encoder
from .parser.rule import Rule, Lax
from .parser.field import Field, Param
from .parser.options import Options
from .schema import Schema, DataClass, LogicalMeta
from .utils import exceptions as exc
from .decorator import parse, handle, apply, dataclass, raw


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
