import inspect
import math
import warnings
import random
from decimal import Decimal
from enum import Enum, EnumMeta
from ..utils.datastructures import unprovided
from ..parser.field import ParserField
from ..parser.base import BaseParser
from ..parser.rule import LogicalType, Rule, SEQ_TYPES, MAP_TYPES
from uuid import UUID
from datetime import date, datetime, timedelta, time
from typing import Type

VALUE_TYPES = (str, int, float, Decimal, datetime, date, time, timedelta)


def get_example_from_json_schema(schema):
    pass


def get_example_from(t: type):
    if t == type(None):
        return None

    if t == bool:
        return random.choice([True, False])

    if t == UUID:
        import uuid
        return uuid.uuid4()

    if isinstance(t, EnumMeta):
        val = random.choice(t.__members__.values())     # noqa
        return t(val.value)

    parser = getattr(t, '__parser__', None)
    if isinstance(parser, BaseParser):
        return t(**get_example_from_parser(parser))

    if inspect.isclass(t) and issubclass(t, Rule):
        return get_example_from_rule(t)

    if isinstance(t, LogicalType):
        return t.get_example()

    return t()


def get_example_from_field(field: ParserField):
    if not unprovided(field.field.example):
        return field.field.example
    return get_example_from(field.type)


def get_example_from_parser(self):
    data = {}
    for name, field in self.fields.items():
        try:
            example = get_example_from_field(field)
        except Exception as e:
            warnings.warn(f'{self.obj}: generate example for field: [{repr(name)}] failed with error: {e}')
            continue
        data[name] = example
    return data


def get_example_from_rule(cls: Type[Rule]):
    """
    If example is forced and there is unsolvable rules (validator / converter) and no example provided
    will prompt error to ask provide example
    """
    if hasattr(cls, 'const'):
        return cls.const

    if hasattr(cls, 'enum'):
        return random.choice(cls.enum)

    if hasattr(cls, 'regex'):
        try:
            import exrex    # noqa
            return exrex.getone(cls.regex)
        except (ModuleNotFoundError, AttributeError):
            pass

    t = cls.__origin__

    if t in SEQ_TYPES:
        if cls.__args__:
            values = []
            if cls.__ellipsis_args__:
                # tuple
                for arg in cls.__args__:
                    values.append(
                        get_example_from(arg)
                    )
            else:
                values.append(
                    get_example_from(cls.__args__[0])
                )
            return t(values)

    if t in MAP_TYPES:
        if cls.__args__:
            values = {}
            key_type = cls.__args__[0]
            val_type = None
            if len(cls.__args__) > 1:
                val_type = cls.__args__[1]
            key = get_example_from(key_type)
            val = get_example_from(val_type) if val_type else None
            values[key] = val
            return t(values)

    if t not in VALUE_TYPES:
        return get_example_from(t)

    multi_of = getattr(cls, 'multiple_of', None)

    length = getattr(cls, 'length', None)
    min_length = getattr(cls, 'min_length', None)
    max_length = getattr(cls, 'max_length', None)

    round_v = getattr(cls, 'decimal_places', None)

    ge = getattr(cls, 'ge', None)
    gt = getattr(cls, 'gt', None)
    le = getattr(cls, 'le', None)
    lt = getattr(cls, 'lt', None)
    min_value = getattr(cls, 'ge', getattr(cls, 'gt', None))
    max_value = getattr(cls, 'le', getattr(cls, 'lt', None))

    if min_value is None:
        if max_value is None:
            if t == datetime:
                return datetime.now()
            elif t == date:
                return datetime.now().date()
            elif t == time:
                return datetime.now().time()
            elif t == timedelta:
                v = datetime.now().time()
                return timedelta(hours=v.hour, minutes=v.minute, seconds=v.second, microseconds=v.microsecond)
            else:
                if isinstance(multi_of, (int, float)):
                    return multi_of * random.randint(1, 10)

                val_length = length
                if val_length is None:
                    min_len = min_length or 0
                    max_len = max_length or min_len + 10
                    val_length = int(min_len + (max_len - min_len) * random.random())

                if not val_length:
                    return t()

                if t == str:
                    import string
                    return ''.join(random.sample(string.digits + string.ascii_letters, val_length))

                elif t in (float, Decimal):
                    if round_v and round_v > 0:
                        val_length = max(val_length - round_v - 1, 1)
                    val = random.randint(10 ** (val_length - 1), 10 ** val_length - 1) + random.random()
                    if round_v is not None:
                        val = round(val, round_v)
                    while len(str(val)) < val_length:
                        val = float(str(val) + '1')
                    return t(val)

                elif t == int:
                    return random.randint(10 ** (val_length - 1), 10 ** val_length - 1)
        else:
            if t in (int, float, Decimal):
                if isinstance(multi_of, (int, float)) and multi_of:
                    times = int(max_value / multi_of)
                    return multi_of * random.randint(max(1, times - 3), times)

                min_value = (max_value / 2) if max_value > 0 else max_value * 2
            elif t in (datetime, date):
                min_value = max_value - timedelta(days=1)   # noqa
            elif t == timedelta:
                min_value = min(timedelta(), max_value - timedelta(days=1))     # noqa
            elif t == time:
                min_value = time()

    elif max_value is None:
        if t in (int, float, Decimal):
            if isinstance(multi_of, (int, float)) and multi_of:
                times = math.ceil(min_value / multi_of)
                return multi_of * random.randint(times, times + 5)

            max_value = (min_value * 2) if min_value > 0 else min_value / 2
        elif t in (datetime, date, timedelta):
            max_value = min_value + timedelta(days=1)  # noqa
        elif t == time:
            max_value = time(23, 59, 59)

    if max_value is not None and min_value is not None:
        try:
            delta = max_value - min_value
            if isinstance(delta, int):
                if isinstance(multi_of, (int, float)) and multi_of:
                    max_times = int(max_value / multi_of)
                    min_times = math.ceil(min_value / multi_of)
                    return multi_of * random.randint(min_times, max_times)

                v = min_value + random.randint(0, delta)
                if v == gt:
                    v = v + 1
                elif v == lt:
                    v = v - 1
            else:
                v = min_value + delta * random.random()

            v = t(v)
            if round_v is not None:
                v = round(v, round_v)
            return v
        except TypeError:
            # like str
            seq = []
            if le:
                seq.append(le)
            if ge:
                seq.append(ge)
            if seq:
                return random.choice(seq)
            if isinstance(min_value, str):
                return min_value + '_' + str(random.randint(0, 9))
    return t()
