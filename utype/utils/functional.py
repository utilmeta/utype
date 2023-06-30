from typing import Optional

LOCALS_NAME = "<locals>"


def multi(f):
    return isinstance(
        f, (list, set, frozenset, tuple, type({}.values()), type({}.keys()))
    )


def pop(data, key, default=None):
    if isinstance(data, dict):
        return data.pop(key) if key in data else default
    elif isinstance(data, list):
        return data.pop(key) if key < len(data) else default
    return default


def copy_value(data):
    """
    return a new value identical to default , but different in memory,
    to avoid multiple initialize to modify the same default data
    """
    if multi(data):
        return type(data)([copy_value(d) for d in data])
    elif isinstance(data, dict):
        return {k: copy_value(v) for k, v in data.items()}
    return data


def get_name(func) -> Optional[str]:
    if isinstance(func, str):
        return func
    if isinstance(func, property):
        func = func.fget
    from functools import partial

    if isinstance(func, partial):
        if hasattr(func, "__name__"):
            return func.__name__
        func = func.func
    if hasattr(func, "__name__"):
        return func.__name__
    return None


def get_obj_name(obj) -> str:
    name = getattr(
        obj, "__qualname__", getattr(obj, "__name__", None)
    ) or str(obj)
    if LOCALS_NAME in name:
        name = str(name.split(LOCALS_NAME)[-1]).strip(".")
    return name


def is_local_var(obj):
    name = getattr(
        obj, "__qualname__", getattr(obj, "__name__", None)
    ) or ''
    return not name or LOCALS_NAME in name
