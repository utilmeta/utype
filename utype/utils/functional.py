
def multi(f):
    return isinstance(f, (list, set, frozenset, tuple, type({}.values()), type({}.keys())))


def pop(data, key, default=None):
    if isinstance(data, dict):
        return data.pop(key) if key in data else default
    elif isinstance(data, list):
        return data.pop(key) if key < len(data) else default
    return default