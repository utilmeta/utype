import inspect
import decimal
import uuid
from collections.abc import Mapping
from datetime import datetime, date, timedelta, time
from typing import Union
from enum import Enum
# from utilmeta.conf import get_config, Time

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_TIME_FORMAT = '%H:%M:%S'

__encoders__ = {}


def register_encoder(*classes, attr=None, detector=None, allow_subclasses: bool = True):
    signature = (*classes, attr, detector)

    if not detector:
        if not classes and not attr:
            raise ValueError(f'register_transformer must provide any of classes, attr, detector')

        for c in classes:
            assert inspect.isclass(c), f'register_transformer classes must be class, got {c}'

        if attr:
            assert isinstance(attr, str), f'register_transformer classes must be str, got {attr}'

        def detector(_cls):
            if classes:
                if allow_subclasses:
                    if not issubclass(_cls, classes):
                        return False
                else:
                    if _cls not in classes:
                        return False
            if attr and not hasattr(_cls, attr):
                return False
            return True

    def decorator(f):
        __encoders__[signature] = (detector, f)
        return f

    # before runtime, type will be compiled and applied
    # if transformer is defined after the validator compiled
    # it will not take effect
    return decorator


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
def from_mapping(encoder, data):
    return dict(data)


@register_encoder(bytes)
def from_bytes(encoder, data: bytes):
    return data.decode('utf-8', errors='replace')


@register_encoder(date)
def from_datetime(encoder, data: Union[datetime, date]):
    # time_config = get_config(Time)
    # if isinstance(data, datetime):
    #     if time_config.datetime_format:
    #         return data.strftime(DA)
    # else:
    #     if time_config.date_format:
    #         return data.strftime(time_config.date_format)
    return data.isoformat()


@register_encoder(timedelta)
def from_duration(encoder, data: timedelta):
    return duration_iso_string(data)


@register_encoder(time)
def from_time(encoder, data: time):
    r = data.isoformat()
    if data.microsecond:
        r = r[:12]
    return r


@register_encoder(uuid.UUID)
def from_uuid(encoder, data: uuid.UUID):
    return str(data)


@register_encoder(decimal.Decimal)
def from_decimal(encoder, data: decimal.Decimal):
    return float(data) if data.is_normal() else str(data)


@register_encoder(Enum)
def from_enum(encoder, en: Enum):
    return en.value


@register_encoder(attr='__iter__')
def from_iterable(encoder, data):
    return list(data)
