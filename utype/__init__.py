from .utils.transform import TypeTransformer, register_transformer
from .rule import Rule
from .field import Field
from .options import Options
from .schema import Schema
from .utils import exceptions as exc
from .decorator import parse, handle, apply


VERSION = (1, 0, 0, 'alpha')


def _get_version():
    pre_release = VERSION[3] if len(VERSION) > 3 else ''
    version = '.'.join([str(v) for v in VERSION[:3]])
    if pre_release:
        version += f'-{pre_release}'
    return version


__version__ = _get_version()
