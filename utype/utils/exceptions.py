# ERROR for handling parse
from typing import Union, Any, List, Set


class ParseError(TypeError, ValueError):
    def __init__(self, msg: str = None, *,
                 value: Any = None,
                 type: type = None,
                 item: Union[int, str] = None,  # like key in the object or index in seq to indentify value
                 origin_exc: Exception = None):
        if not msg and origin_exc:
            msg = str(origin_exc)
        self.msg = msg
        self.origin_exc = origin_exc
        self.value = value
        self.type = type
        self.item = item
        super().__init__(self.formatted_message)

    @property
    def formatted_message(self):
        return self.msg


class ConstraintError(ParseError):
    def __init__(self, msg: str = None, *,
                 value: Any = None,
                 type: type = None,
                 item: Union[int, str] = None,  # like key in the object or index in seq to indentify value
                 constraint: str = None,        # failed constraint
                 constraint_value: Any = ...,   # failed constraint value
                 origin_exc: Exception = None):
        self.constraint = constraint
        self.constraint_value = constraint_value
        super().__init__(
            msg,
            value=value,
            type=type,
            item=item,
            origin_exc=origin_exc
        )

    @property
    def formatted_message(self):
        if self.constraint:
            msg = f'Constraint: <{self.constraint}>: {repr(self.constraint_value)} violated'
            if self.msg:
                msg += f': {self.msg}'
            return msg
        return self.msg


class ExceedError(ParseError):
    # a key has excess the dict template and allow_excess=False in options
    def __init__(self, msg: str = None, excess_items: Union[list, set] = None, **kwargs):
        super().__init__(msg, **kwargs)
        self.excess_items = excess_items


class AliasConflictError(ParseError):
    pass


class ItemsExceedError(ExceedError):
    pass


class PropertiesExceedError(ExceedError):
    def __init__(self, msg: str = None, max_properties: int = None, properties_num: int = None, **kwargs):
        self.properties_num = properties_num
        self.max_properties = max_properties


class PropertiesLackError(ParseError):
    def __init__(self, msg: str = None, min_properties: int = None, properties_num: int = None, **kwargs):
        self.properties_num = properties_num
        self.min_properties = min_properties


class AbsenceError(ParseError):
    def __init__(self, msg: str = None, absence_item: Union[int, str] = None, **kwargs):
        super().__init__(msg, **kwargs)
        self.absence_item = absence_item


class DependenciesAbsenceError(AbsenceError):
    def __init__(self, msg: str = None, absence_dependencies: Set[str] = None, **kwargs):
        super().__init__(msg, **kwargs)
        self.absence_dependencies = absence_dependencies


class RecursionExceeded(ParseError, RecursionError):
    def __init__(self, msg: str = None, depth: int = None, **kwargs):
        super().__init__(msg, **kwargs)
        self.depth = depth


class TransformError(ParseError, TypeError):
    def __init__(self, msg: str = None, data_type: type = None, **kwargs):
        super().__init__(msg, **kwargs)
        self.data_type = data_type


class CollectedParseError(ParseError):
    def __init__(self, errors: List[ParseError]):
        self.errors = errors
        super().__init__(';\n'.join([str(error) for error in errors]))


class NegateViolatedError(ParseError):
    pass


class OneOfViolatedError(ParseError):
    pass

