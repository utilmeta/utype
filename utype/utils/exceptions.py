# ERROR for handling parse
from typing import Union, Any, List, Set


class FieldError(AttributeError, KeyError):
    def __init__(
        self,
        msg: str = None,
        *,
        field=None,
        origin_exc: Exception = None,
    ):
        self.msg = msg
        self.field = field
        self.origin = origin_exc


class UpdateError(FieldError):
    pass


class DeleteError(FieldError):
    pass


class ParseError(TypeError, ValueError):
    def __init__(
        self,
        msg: str = None,
        *,
        value: Any = None,
        type: type = None,
        item: Union[
            int, str
        ] = None,  # like key in the object or index in seq to indentify value
        field=None,  # no field can means it's additional field
        origin_exc: Exception = None,
    ):
        if not msg and origin_exc:
            msg = str(origin_exc)
        self.msg = msg
        self.origin_exc = origin_exc
        self.value = value
        self.type = type
        self.item = item
        self.field = field
        super().__init__(self.formatted_message)

    @property
    def formatted_message(self):
        msg = self.msg
        if self.item:
            msg = f'parse item: [{repr(self.item)}] failed: {msg}'
        return msg


class TypeMismatchError(ParseError):
    @property
    def formatted_message(self):
        msg = f"type: {self.type} is unrecognized and forbid to auto-init"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class DiscriminatorMismatchError(ParseError):
    def __init__(self, discriminator: str, discriminator_value=None, **kwargs):
        self.discriminator = discriminator
        self.discriminator_value = discriminator_value
        super().__init__(**kwargs)


class ConstraintError(ParseError):
    def __init__(
        self,
        msg: str = None,
        *,
        value: Any = None,
        type: type = None,
        item: Union[
            int, str
        ] = None,  # like key in the object or index in seq to indentify value
        constraint: str = None,  # failed constraint
        constraint_value: Any = ...,  # failed constraint value
        origin_exc: Exception = None,
    ):
        self.constraint = constraint
        self.constraint_value = constraint_value
        super().__init__(msg, value=value, type=type, item=item, origin_exc=origin_exc)

    @property
    def formatted_message(self):
        if self.constraint:
            msg = f"Constraint: <{self.constraint}>: {repr(self.constraint_value)} violated"
            if self.msg:
                msg += f": {self.msg}"
            return msg
        return self.msg


class ExceedError(ParseError):
    # a key has excess the dict template and allow_excess=False in options
    # def __init__(
    #     self, msg: str = None, excess_items: Union[list, set] = None, **kwargs
    # ):
    #     self.excess_items = excess_items
    #     super().__init__(msg, **kwargs)

    @property
    def formatted_message(self):
        msg = f"parse item: [{repr(self.item)}] exceeded"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class TupleExceedError(ExceedError):
    pass


class AliasConflictError(ParseError):
    pass


# class ItemsExceedError(ExceedError):
#     pass

class DepthExceedError(ParseError):
    def __init__(
        self,
        msg: str = None,
        max_depth: int = None,
        depth: int = None,
        **kwargs,
    ):
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(msg, **kwargs)


class ParamsExceedError(ParseError):
    def __init__(
        self,
        msg: str = None,
        max_params: int = None,
        params_num: int = None,
        **kwargs,
    ):
        self.params_num = params_num
        self.max_params = max_params
        super().__init__(msg, **kwargs)


class ParamsLackError(ParseError):
    def __init__(
        self,
        msg: str = None,
        min_params: int = None,
        params_num: int = None,
        **kwargs,
    ):
        self.params_num = params_num
        self.min_params = min_params
        super().__init__(msg, **kwargs)


class AbsenceError(ParseError):
    @property
    def formatted_message(self):
        msg = f"Required item: {repr(self.item)} is absence"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class DependenciesAbsenceError(AbsenceError):
    def __init__(
        self, msg: str = None, absence_dependencies: Set[str] = None, **kwargs
    ):
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
        super().__init__(";\n".join([str(error) for error in errors]))


class NegateViolatedError(ParseError):
    pass


class OneOfViolatedError(ParseError):
    pass
