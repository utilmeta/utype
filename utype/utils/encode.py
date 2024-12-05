import decimal
import io
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Union
from .base import TypeRegistry
import json
from .datastructures import unprovided
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from pathlib import PurePath


encoder_registry = TypeRegistry('encoder', cache=True, shortcut='__encoder__')
register_encoder = encoder_registry.register


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        encoder = encoder_registry.resolve(type(o))
        if encoder:
            return encoder(o)
        return super().default(o)


class JSONSerializer:
    """
    Simple wrapper around json to be used in signing.dumps and
    signing.loads.
    """
    encoder_cls = JSONEncoder
    charset = 'utf-8'
    separators = (',', ':')
    ensure_ascii = False
    skipkeys = True

    def dumps(self, obj):
        return json.dumps(
            obj,
            separators=self.separators,
            cls=self.encoder_cls,
            ensure_ascii=self.ensure_ascii,
            skipkeys=self.skipkeys
        ).encode(self.charset)

    def loads(self, data: bytes):
        return json.loads(data.decode(self.charset))


def duration_iso_string(duration: timedelta):
    if duration < timedelta(0):
        sign = "-"
        duration *= -1
    else:
        sign = ""

    days = duration.days
    seconds = duration.seconds
    microseconds = duration.microseconds

    minutes = seconds // 60
    seconds = seconds % 60

    hours = minutes // 60
    minutes = minutes % 60

    ms = ".{:06d}".format(microseconds) if microseconds else ""
    return "{}P{}DT{:02d}H{:02d}M{:02d}{}S".format(
        sign, days, hours, minutes, seconds, ms
    )


@register_encoder(Mapping)
def from_mapping(data):
    return dict(data)


@register_encoder(set)
def from_set(data):
    return list(data)


@register_encoder(tuple)
def from_tuple(data):
    return list(data)


@register_encoder(unprovided.__class__)
def from_unprovided(data):
    return None


@register_encoder(bytes)
def from_bytes(data: bytes):
    return data.decode("utf-8", errors="replace")


@register_encoder(PurePath, allow_subclasses=True)
def from_path(data: PurePath):
    return str(data)


@register_encoder(io.BytesIO)
def from_bytes_io(data: io.BytesIO):
    return data.read().decode("utf-8", errors="replace")


@register_encoder(date)
def from_datetime(data: Union[datetime, date]):
    return data.isoformat()


@register_encoder(IPv4Network, IPv4Address, IPv6Network, IPv6Address)
def from_ip(data):
    return str(data)


@register_encoder(timedelta)
def from_duration(data: timedelta):
    return duration_iso_string(data)


@register_encoder(time)
def from_time(data: time):
    r = data.isoformat()
    if data.microsecond:
        r = r[:12]
    return r


@register_encoder(uuid.UUID)
def from_uuid(data: uuid.UUID):
    return str(data)


@register_encoder(decimal.Decimal)
def from_decimal(data: decimal.Decimal):
    if data.is_finite():
        if js_unsafe(data):
            return str(data)
        if not data.as_tuple().exponent:
            # integer
            return int(data)
        return float(data)
    # infinity / NaN
    return str(data)


# TODO?
# @register_encoder(float)
# def from_float(data: float):
#     if js_unsafe(data):
#         return str(data)
#     return data
#
#
# @register_encoder(int)
# def from_int(data: int):
#     if js_unsafe(data):
#         return str(data)
#     return data


@register_encoder(Enum)
def from_enum(en: Enum):
    return en.value


MAX_SAFE_NUMBER = 9007199254740991
MIN_SAFE_NUMBER = -9007199254740991


def js_unsafe(num: Union[int, float, decimal.Decimal]):
    return num > MAX_SAFE_NUMBER or num < MIN_SAFE_NUMBER


# @register_encoder(attr="__iter__")
# def from_iterable(encoder, data):
#     return list(data)
