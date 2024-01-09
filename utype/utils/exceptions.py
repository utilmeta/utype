# ERROR for handling parse
from typing import Any, List, Set, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from ..parser.field import ParserField


class ConfigError(SyntaxError):
    def __init__(self, msg="", obj=None, params: dict = None, field: str = None):
        super().__init__(msg)
        self.obj = obj
        self.params = params
        self.field = field


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

        super().__init__(msg)


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
        field: 'ParserField' = None,  # no field can means it's additional field
        routes: list = None,
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
        self.routes = routes
        super().__init__(self.formatted_message)

    @property
    def formatted_message(self):
        msg = self.msg
        if self.item:
            msg = f"parse item: [{repr(self.item)}] failed: {msg}"
        return msg

    def get_detail(self) -> dict:
        from ..specs.json_schema import JsonSchemaGenerator
        origin = None
        if self.origin_exc:
            if isinstance(self.origin_exc, ParseError) and self.origin_exc.field:
                origin = self.origin_exc.get_detail()

        if origin:
            return {
                'name': self.field.name if self.field else None,
                'field': self.field.field.__class__.__name__ if self.field else None,
                'origin': origin
            }
        return {
            'name': self.field.name if self.field else None,
            'value': self.value,
            'field': self.field.field.__class__.__name__ if self.field else None,
            'schema': JsonSchemaGenerator(self.type)() if self.type else None,
            'msg': self.msg,
        }


class TypeMismatchError(ParseError):
    @property
    def formatted_message(self):
        msg = f"type: {self.type} is unrecognized and forbid to auto-init"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class InvalidInstance(TypeMismatchError):
    @property
    def formatted_message(self):
        msg = f"invalid class instance: {self.value} for {self.type}"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class InvalidSubclass(TypeMismatchError):
    @property
    def formatted_message(self):
        msg = f"invalid subclass: {self.value} for {self.type}"
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
        constraint_value: Any = None,  # failed constraint value
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

    @property
    def formatted_message(self):
        msg = f"max_depth: {self.max_depth} exceed: {self.depth}"
        if self.msg:
            msg += f": {self.msg}"
        return msg


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

    @property
    def formatted_message(self):
        msg = f"max params num: {self.max_params} exceed: {self.params_num}"
        if self.msg:
            msg += f": {self.msg}"
        return msg


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

    @property
    def formatted_message(self):
        msg = f"min params num: {self.min_params} lacked: {self.params_num}"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class AbsenceError(ParseError):
    @property
    def formatted_message(self):
        msg = f"required item: {repr(self.item)} is absence"
        if self.msg:
            msg += f": {self.msg}"
        return msg


class DependenciesAbsenceError(AbsenceError):
    def __init__(
        self, msg: str = None, absence_dependencies: Set[str] = None, **kwargs
    ):
        self.absence_dependencies = absence_dependencies
        super().__init__(msg, **kwargs)

    @property
    def formatted_message(self):
        msg = f"required dependencies: {self.absence_dependencies} is absence"
        if self.msg:
            msg += f": {self.msg}"
        return msg


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

    def get_detail(self) -> list:
        errors = []
        for error in self.errors:
            if isinstance(error, ParseError):
                errors.append(error.get_detail())
            else:
                errors.append({
                    'msg': str(error),
                    'error': error.__class__.__name__
                })
        return errors


class NegateViolatedError(ParseError):
    pass


class OneOfViolatedError(ParseError):
    pass
