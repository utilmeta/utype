import decimal
import io
import json
import re
import collections
from collections import deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional, Type, TypeVar
from uuid import UUID

from .compat import ForwardRef
from .exceptions import TypeMismatchError
from .functional import multi
from .base import TypeRegistry

if TYPE_CHECKING:
    from ..parser.options import RuntimeContext

T = TypeVar("T")


class DateFormat:
    DATETIME = "%Y-%m-%d %H:%M:%S"
    DATETIME_DF = "%Y-%m-%d %H:%M:%S.%f"
    DATETIME_F = "%Y-%m-%d %H:%M:%S %f"
    DATETIME_P = "%Y-%m-%d %I:%M:%S %p"
    DATETIME_T = "%Y-%m-%dT%H:%M:%S"
    # DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"
    # DATETIME_TFZ = "%Y-%m-%dT%H:%M:%S.%fZ"
    DATETIME_TF = "%Y-%m-%dT%H:%M:%S.%f"
    # DATETIME_ISO = "%Y-%m-%dT%H:%M:%S.%fTZD"
    DATETIME_HTTP = "%a, %d %b %Y %H:%M:%S"
    # DATETIME_GMT = "%a, %d %b %Y %H:%M:%S GMT"
    DATETIME_PS = "%a %b %d %H:%M:%S %Y"
    DATETIME_GMT = "%b %d %H:%M:%S %Y"
    DATE = "%Y-%m-%d"
    DATE_HM = "%Y-%m-%d %H:%M"
    # TIME = '%H:%M:%S'


class TypeTransformer:
    registry = TypeRegistry('transformer', shortcut='__transformer__', cache=True)
    
    # ----- preferences
    # can be override
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%A, %d %B %Y",
        "%a, %d %b %Y",
        "%Y%m%d",
    ]
    DATETIME_FORMATS = [
        DateFormat.DATETIME,
        DateFormat.DATETIME_DF,
        DateFormat.DATETIME_F,
        DateFormat.DATETIME_P,
        DateFormat.DATETIME_T,
        DateFormat.DATETIME_TF,
        DateFormat.DATETIME_HTTP,
        DateFormat.DATETIME_PS,
        DateFormat.DATETIME_GMT,

        # Date formats
        "%Y-%m-%d %H:%M"
    ]

    EPOCH = datetime(1970, 1, 1)
    MS_WATERSHED = int(2e10)
    ARRAY_SEPARATORS = (",", ";")
    NULL_VALUES = ("null", "none", "nil")
    FALSE_VALUES = ("0", "false", "no", "off", "f")
    TRUE_VALUES = ("1", "true", "yes", "on", "t", "y")
    STRUCTURE_BRACKET = [
        "{}",
        "[]",
        "()",
    ]
    DURATION_REGS = [
        re.compile(
            r"^"
            r"(?:(?P<days>-?\d+) (days?, )?)?"
            r"((?:(?P<hours>-?\d+):)(?=\d+:\d+))?"
            r"(?:(?P<minutes>-?\d+):)?"
            r"(?P<seconds>-?\d+)"
            r"(?:\.(?P<microseconds>\d{1,6})\d{0,6})?"
            r"$"
        ),  # Support the sections of ISO 8601 date representation that are accepted by timedelta
        re.compile(
            r"^(?P<sign>[-+]?)"
            r"P"
            r"(?:(?P<days>\d+(.\d+)?)D)?"
            r"(?:T"
            r"(?:(?P<hours>\d+(.\d+)?)H)?"
            r"(?:(?P<minutes>\d+(.\d+)?)M)?"
            r"(?:(?P<seconds>\d+(.\d+)?)S)?"
            r")?"
            r"$"
        ),
    ]

    def __init__(
        self,
        context: "RuntimeContext",
        no_explicit_cast: bool = None,
        no_data_loss: bool = None,
        unresolved_types: str = None,
    ):
        self.context = context
        self.no_explicit_cast = (
            no_explicit_cast
            if no_explicit_cast is not None
            else context.options.no_explicit_cast
        )
        self.no_data_loss = (
            no_data_loss if no_data_loss is not None else context.options.no_data_loss
        )
        self.unresolved_types = (
            unresolved_types
            if unresolved_types is not None
            else context.options.unresolved_types
        )

    @property
    def options(self):
        return self.context.options

    def __repr__(self):
        return f"{self.__class__.__name__}(no_explicit_cast={self.no_explicit_cast}, no_data_loss={self.no_data_loss})"

    @classmethod
    def resolver_transformer(cls, t: type) -> Optional[Callable]:
        return cls.registry.resolve(t)

    def _attempt_from(self, value):
        if self.no_explicit_cast:
            # does not allow
            return value
        if multi(value) and value:
            if self.no_data_loss and len(value) > 1:
                # like convert ["a"] to "a"
                # whether a "data loss" happen in here is leave to future discussion
                # we apply this for now because some data structure will make value a
                # list with a single item
                # * querystring -> query dict
                # * multipart/form-data -> files
                raise TypeError
            return list(value)[0]
        if isinstance(value, Enum):
            return value.value
        return value

    def _from_byte_like(self, data):
        if isinstance(data, (bytes, bytearray, memoryview)):
            if isinstance(data, memoryview):
                data = bytes(data)
            return data.decode(errors="strict" if self.no_data_loss else "ignore")
        return data

    def _attempt_from_number(self, data):
        data = self._from_byte_like(self._attempt_from(data))
        if isinstance(data, datetime):
            return data.timestamp()
        elif isinstance(data, timedelta):
            return data.total_seconds()
        elif isinstance(data, complex) and not self.no_data_loss:
            if not data.imag:
                return data.real
        elif not data:
            # convert ''. None and others to 0
            # might be a questionable feature?
            return 0
        return data

    # ---------------------
    # 2 approach to do first check
    # 1. all the subclasses instance can directly pass through
    # if isinstance(data, t):
    #     # we will follow the type
    #     return data
    #
    # 2. all the subclasses of the hooked types can pass through (by re-initialize)
    # this should guarantee that the type __init__ take only 1 argument
    # if isinstance(data, *_type_classes):
    #     return t(data)

    @registry.register(type(None), allow_subclasses=False)
    def to_null(self, data, t=type(None)) -> None:
        if data is None:
            return None
        if self.no_explicit_cast:
            raise TypeError
        if isinstance(data, str):
            if data.lower() in self.NULL_VALUES:
                return None
        raise TypeError

    # register this metaclass earlier, because str/list/... is all subclass of Iterable
    # this is just a FALLBACK for the iterable/sequence that does not get resolved
    @registry.register(Sequence, Iterable, Iterator)
    def to_iter_types(self, data, t):
        if isinstance(data, t):
            # we will follow the type
            return data
        value = self.to_array_types(data, list)
        if not getattr(t, "__abstractmethods__", None):
            return t(value)
        # if type is still abstracted, just returning the list result
        return value

    @registry.register(Mapping)
    def to_mapping(self, data, t):
        if isinstance(data, t):
            # we will follow the type
            return data
        value = self.to_dict(data, dict)
        if not getattr(t, "__abstractmethods__", None):
            return t(value)
        return value

    @registry.register(str)
    def to_str(self, data, t: Type[str] = str) -> str:
        if isinstance(data, str):
            return t(data)
        data = self._from_byte_like(self._attempt_from(data))
        if self.no_explicit_cast and not isinstance(data, str):
            raise TypeError
        return t(data)

    @registry.register(bytes, bytearray, memoryview)
    def to_bytes(self, data, t: Type[bytes] = bytes):
        data = self._attempt_from(data)

        if isinstance(data, (bytes, bytearray, memoryview)):
            return t(data)

        if isinstance(data, str):
            return t(data.encode())

        if self.no_explicit_cast:
            # bytes can convert all the types (from str)
            # if the value is not bytes (need to transform) in strict mode, throw an error directly
            raise TypeError

        return t(str(data).encode())

    @registry.register(list, tuple, set, frozenset, deque)
    def to_array_types(self, data, t=list):
        if isinstance(data, t):
            return data

        if multi(data):  # same group
            return t(data)

        if self.no_explicit_cast:
            raise TypeError

        data = self._from_byte_like(data)

        if isinstance(data, str):
            data = data.strip()
            # guess string form array like
            # [1, 2, 3]
            # [{"a": b}]
            # {1, 2, 3}
            # a,b,c
            if any(
                data.startswith(v[0]) and data.endswith(v[1])
                for v in self.STRUCTURE_BRACKET
            ):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    import ast

                    data = ast.literal_eval(data)
                    if multi(data):
                        return t(data)
                else:
                    if isinstance(data, list):
                        return t(data)
            else:
                for sep in self.ARRAY_SEPARATORS:
                    if sep in data:
                        return t(v.strip() for v in data.split(sep))

        # if data is None:
        #     return t()

        if isinstance(data, dict):
            if issubclass(t, set):
                if self.no_data_loss:
                    raise TypeError
                # set cannot pack un-hashable dict item
                return t(data)
            if not data:
                # {} -> [], as for no data loss
                return t()
        # instead of tear the item apart
        return t([data])
        # return t(data)

    @registry.register(dict)
    def to_dict(self, data, t=dict) -> dict:
        if isinstance(data, t):
            return data
        if isinstance(data, Mapping):
            return t(data)

        if self.no_explicit_cast:
            raise TypeError

        if self.no_data_loss:
            if isinstance(data, (list, set, tuple)):
                result = {}
                try:
                    for item in data:
                        # dict([{'a': 1, 'b': 2}]) == {'a': 'b'}
                        # is consider a data loss
                        if isinstance(item, (dict, Mapping)):
                            raise TypeError
                        key, val = item
                        result[key] = val
                    return t(result)
                except (TypeError, ValueError):
                    pass
        else:
            try:
                # try for iterable of key, value pairs
                # but data loss may happen in this case
                # like dict([{"a": 1, "b": 2}]) == {"a": "b"}
                return t(data)
                # directly return
            except (TypeError, ValueError):
                pass

        data = self._from_byte_like(self._attempt_from(data))

        if isinstance(data, str):
            try:
                return t(json.loads(data, strict=self.no_data_loss))  # noqa
            except json.decoder.JSONDecodeError:
                data = data.strip()
                if any(
                    data.startswith(v[0]) and data.endswith(v[1])
                    for v in self.STRUCTURE_BRACKET
                ):
                    import ast

                    res = self._attempt_from(ast.literal_eval(data))
                    if isinstance(res, dict):
                        # maybe set
                        return t(res)
                    raise
                if "=" in data:
                    if "&" in data:
                        # a=b&c=d   querystring index
                        from urllib.parse import parse_qs

                        qs = parse_qs(data)
                        return t({k: v[0] if len(v) == 1 else v for k, v in qs.items()})
                    spliter = ";" if ";" in data else ","
                    # cookie syntax or comma separate syntax
                    return t(
                        {
                            value.split("=")[0].strip(): ("=".join(value.split("=")[1:]).strip())
                            for value in data.split(spliter)
                        }
                    )
                raise

        from xml.etree.ElementTree import Element

        if isinstance(data, Element):
            return t(data.attrib)  # noqa

        return t(data)

    # bool is a subclass of int
    @registry.register(float)
    def to_float(self, data, t: Type[float] = float) -> float:
        if isinstance(data, float):
            return t(data)

        if self.no_explicit_cast:
            if not isinstance(data, (int, float, Decimal)):
                raise TypeError
        else:
            data = self._attempt_from_number(data)

        return t(data)

    @registry.register(int)
    def to_integer(self, data, t: Type[int] = int) -> int:
        if isinstance(data, int):
            # including bool:
            # True -> 1
            # False -> 0
            return t(data)

        if self.no_explicit_cast:
            if not isinstance(data, (int, float, Decimal)):
                raise TypeError
        else:
            data = self._attempt_from_number(data)
            if isinstance(data, str):
                if data.lower() in self.FALSE_VALUES:
                    return 0
                if data.lower() in self.TRUE_VALUES:
                    return 1
            elif isinstance(data, t):
                return data

        try:
            data = Decimal(data)
        except decimal.InvalidOperation:
            raise TypeError(f'invalid number: {repr(data)}')
        # !!
        # FOR number > 1e+16, int(float()) will not get accurate result, use decimal instead

        if self.no_data_loss:
            if not data.is_finite():
                raise TypeError
            if data.as_tuple().exponent:
                raise TypeError

        return t(data)

    @registry.register(Decimal)
    def to_decimal(self, data, t: Type[Decimal] = Decimal) -> Decimal:
        if isinstance(data, Decimal):
            return t(data)  # noqa

        if self.no_explicit_cast:
            data = self._from_byte_like(data)
            if not isinstance(data, (int, float, str, Decimal)):
                raise TypeError
        else:
            data = self._attempt_from_number(data)

        return t(str(data).strip())  # noqa

    @registry.register(complex)
    def to_complex(self, data, t=complex) -> complex:
        if isinstance(data, t):
            return data

        if self.no_explicit_cast:
            data = self._from_byte_like(data)
            if not isinstance(data, (int, float, Decimal, str)):
                raise TypeError
        else:
            if isinstance(data, tuple) and len(data) == 2:
                return t(*data)

            data = self._attempt_from_number(data)

        return t(data)

    @registry.register(bool)  # after int
    def to_bool(self, data, t=bool) -> bool:
        if isinstance(data, bool):
            return t(data)
        if data == 1:
            return True
        elif data == 0:
            return False
        if self.no_explicit_cast:
            raise TypeError
        if isinstance(data, bytes):
            data = data.decode()
        rep = str(data).lower()
        if rep in self.FALSE_VALUES:
            return False
        elif rep in self.TRUE_VALUES:
            return True
        if self.no_data_loss:
            # bool can convert all the types
            # if the value is not bool (need to transform) in strict mode, throw an error directly
            raise TypeError
        return bool(data)

    @registry.register(
        date, allow_subclasses=False
    )  # datetime is a subclass of date
    def to_date(self, data, t: Type[date] = date) -> date:
        if isinstance(data, datetime):
            if self.no_data_loss:
                raise ValueError(f"Invalid date: {data}, must be date")
            return data.date()
        elif isinstance(data, t):
            return data

        dt = self.to_datetime(data, datetime, date_first=True)
        if self.no_data_loss:
            if dt.time() != time(0, 0):
                raise ValueError(f"Invalid date: {data}, got time part: {dt.time()}")
        return dt.date()

    @registry.register(datetime)
    def to_datetime(self, data, t: Type[datetime] = datetime, date_first: bool = False) -> datetime:
        if isinstance(data, t):
            return data
        elif isinstance(data, date):
            return t(year=data.year, month=data.month, day=data.day)  # noqa

        data = self._attempt_from(data)
        if isinstance(data, (int, float, Decimal)):
            while abs(data) > self.MS_WATERSHED:
                data /= 1000
            return t.utcfromtimestamp(data).replace(tzinfo=timezone.utc)

        data = self._from_byte_like(data)
        is_utc = "GMT" in data or 'UTC' in data or data.endswith("Z") and "T" in data
        data = data.replace('GMT', '').replace('UTC', '').replace('TZD', '').rstrip('Z').strip()

        if date_first:
            formats = self.DATE_FORMATS + self.DATETIME_FORMATS
        else:
            formats = self.DATETIME_FORMATS + self.DATE_FORMATS

        for f in formats:
            try:
                val = t.strptime(data, f)
                if is_utc:
                    val = val.replace(tzinfo=timezone.utc)
                return val
            except (TypeError, ValueError, re.error):
                continue

        if '+' in str(data):
            for f in formats:
                try:
                    # val = t.strptime(data, f + ' %z')
                    val = t.strptime(data, f + (' %z' if ' +' in str(data) else '%z'))
                    if is_utc:
                        val = val.replace(tzinfo=timezone.utc)
                    return val
                except (TypeError, ValueError, re.error):
                    continue

        try:
            num = self.to_float(data, float)
        except (TypeError, ValueError):
            pass
        else:
            while abs(num) > self.MS_WATERSHED:
                num /= 1000
            return t.utcfromtimestamp(num).replace(tzinfo=timezone.utc)

        raise TypeError('invalid datetime')

    @registry.register(timedelta)
    def to_timedelta(self, data, t: Type[timedelta] = timedelta) -> timedelta:
        if isinstance(data, t):
            return data
        data = self._from_byte_like(self._attempt_from(data))
        try:
            num = self.to_float(data, float)
        except (TypeError, ValueError):
            pass
        else:
            if self.no_explicit_cast and isinstance(data, str):
                raise TypeError
            return t(seconds=num)
        if isinstance(data, str):
            for regex in self.DURATION_REGS:
                match = regex.match(data)
                if not match:
                    continue
                kw = match.groupdict()
                sign = -1 if kw.pop("sign", "+") == "-" else 1
                if kw.get("microseconds"):
                    kw["microseconds"] = kw["microseconds"].ljust(6, "0")

                if (
                    kw.get("seconds")
                    and kw.get("microseconds")
                    and kw["seconds"].startswith("-")
                ):
                    kw["microseconds"] = "-" + kw["microseconds"]
                kw_ = {k: float(v) for k, v in kw.items() if v is not None}
                return sign * t(**kw_)
            if self.no_explicit_cast:
                raise ValueError(f"Invalid timedelta: {data}")
            tm = time.fromisoformat(data)
            return t(
                hours=tm.hour,
                minutes=tm.minute,
                seconds=tm.second,
                microseconds=tm.microsecond,
            )
        raise TypeError

    @registry.register(time)
    def to_time(self, data, t: Type[time] = time) -> time:
        if isinstance(data, t):
            return data
        data = self._attempt_from(data)
        if not self.no_data_loss:
            if isinstance(data, datetime):
                return data.time()
            if isinstance(data, date):
                return t()
        data = self._from_byte_like(data)
        if isinstance(data, str):
            if ':' in data:
                try:
                    return t.fromisoformat(data)
                except ValueError:
                    return self.to_datetime(f'1970-01-01 {data}').time()
        raise TypeError

    @registry.register(UUID)
    def to_uuid(self, data, t: Type[UUID] = UUID) -> UUID:
        if isinstance(data, t):
            return data

        if isinstance(data, str):
            return t(data)

        elif isinstance(data, (bytes, bytearray)):
            try:
                return t(data.decode())
            except ValueError:
                # 16 bytes in big-endian order as the bytes argument fail
                # the above check
                return t(bytes=data)

        if not self.no_explicit_cast:
            if not self.no_data_loss and isinstance(data, (float, Decimal)):
                data = int(data)

            if isinstance(data, int):
                return t(int=data)

        raise TypeError

    # enum should be the last of current types
    # because Enum subclass may inherit other base
    @registry.register(Enum)
    def to_enum(self, data, t: Type[Enum]) -> Enum:
        if isinstance(data, t):
            return data
        if self.no_explicit_cast:
            return t(data)  # noqa
        if not self.no_data_loss:
            if data in t.__members__:  # noqa
                return t.__members__[data]  # noqa
        member_type = getattr(t, "_member_type_", None)
        if member_type and member_type != object:
            if type(data) != member_type:
                data = self(data, member_type)
        return t(data)  # noqa

    @registry.register(io.BytesIO)
    def to_filelike(self, data, t):
        if isinstance(data, t):
            return data
        if isinstance(data, (bytes, bytearray, memoryview)):
            return t(data)
        if self.no_explicit_cast:
            raise TypeError
        return t(str(data).encode())

    @registry.register(type, allow_subclasses=False)
    def to_type(self, data, t=type) -> type:
        if not isinstance(data, type):
            raise TypeError('data is not a type')
        return data

    @registry.register(collections.abc.Callable, allow_subclasses=False)
    def to_callable(self, data, t) -> Callable:
        if not callable(data):
            raise TypeError('data is not callable')
        return data

    def handle_unresolved(self, data, t):
        if isinstance(t, type) and isinstance(data, t):
            # we just loosely match the isinstance for unresolved types
            return data
        if self.unresolved_types == "throw":
            raise TypeMismatchError(value=data, type=t)
        elif self.unresolved_types == "init":
            return t(data)
        return data

    def apply(self, data, t: Type[T], func=None) -> T:
        if not func:
            return self(data, t)
        if type(data) == t:
            # strict equal. not isinstance, like datetime is instance of date
            return data
        if isinstance(t, ForwardRef):
            if not t.__forward_evaluated__:
                raise TypeError(f"ForwardRef: {t} not evaluated")
            t = t.__forward_value__
        return func(self, data, t)

    def __call__(self, data, t: Type[T]) -> T:
        if isinstance(t, ForwardRef):
            if not t.__forward_evaluated__:
                raise TypeError(f"ForwardRef: {t} not evaluated")
            t = t.__forward_value__
        if type(data) == t:
            # strict equal. not isinstance, like datetime is instance of date
            return data
        transformer = self.resolver_transformer(t)
        if not transformer:
            return self.handle_unresolved(data, t)
        return transformer(self, data, t)


def type_transform(data, type: Type[T], options=None) -> T:
    from ..parser.options import Options

    context = (options or Options()).make_context()
    return context.transformer(data, type)
