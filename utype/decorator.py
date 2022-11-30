

def parse(f, *, params: bool = True, result: bool = True, options=None):
    pass


def apply(
    rule_cls=None, *,
    const: Any = ...,
    enum: Iterable = None,
    gt=None,
    ge=None,
    lt=None,
    le=None,
    regex: str = None,
    length: int = None,
    max_length: int = None,
    min_length: int = None,
    # number
    max_digits: int = None,
    round: int = None,
    multiple_of: int = None,
    # array
    contains: type = None,
    max_contains: int = None,
    min_contains: int = None,
    unique_items: bool = None,
):
    pass

def handle(*func_and_errors):
    pass
