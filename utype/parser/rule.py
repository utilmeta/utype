import inspect
import re
import typing
import warnings
from collections import deque
from decimal import Decimal
from enum import Enum, EnumMeta
from functools import partial
from typing import (Any, AsyncGenerator, Callable, Dict, Generator, List,
                    Mapping, Optional, Tuple, Type, TypeVar, Union, Iterator)

from ..utils import exceptions as exc
from ..utils.compat import (ForwardRef, Literal, evaluate_forward_ref,
                            get_args, get_origin)
from ..utils.datastructures import unprovided
from ..utils.functional import multi, pop
from ..utils.transform import TypeTransformer
from .options import RuntimeContext

T = typing.TypeVar("T")
OTHER = TypeVar("OTHER")
ORIGIN = TypeVar("ORIGIN")

NUM_TYPES = (int, float, Decimal)
SEQ_TYPES = (list, tuple, set, frozenset, deque, Iterator)
MAP_TYPES = (dict, Mapping)
TYPE_EXACT_TOLERANCE = ({int, float},)
OPERATOR_NAMES = {
    "&": "AllOf",
    "|": "AnyOf",
    "^": "OneOf",
    "~": "Not",
}
NONE_ARG_ALLOWED_TYPES = (Callable, Union, Generator, AsyncGenerator)


def resolve_forward_type(t):
    if isinstance(t, ForwardRef):
        if t.__forward_evaluated__:
            return t.__forward_value__, True
        return t, False
    elif isinstance(t, LogicalType):
        res = t.resolve_forward_refs()
        return t, res
    return t, False


def register_forward_ref(
    annotation,
    constraints: dict = None,
    global_vars: Dict[str, Any] = None,
    forward_refs: Dict[str, Tuple[ForwardRef, dict]] = None,
    forward_key: str = None,
):

    if not isinstance(annotation, ForwardRef):
        return
    evaluated = None
    if annotation.__forward_evaluated__:
        evaluated = True
        annotation = annotation.__forward_value__
    elif global_vars:
        try:
            annotation = evaluate_forward_ref(annotation, global_vars, None)
        except NameError:
            # ignore for now
            pass
        else:
            evaluated = True

    if not evaluated:
        if isinstance(forward_refs, dict):
            # class A:
            #   attr1: 'forward' = Field(gt=1)
            #   attr2: 'forward' = Field(gt=2)
            # we use forward_key (attname) over forward_arg
            forward_refs.setdefault(
                f"${forward_key}" if forward_key else annotation.__forward_arg__,
                # use a $ to differ from forward arg
                (annotation, constraints),
            )
            # still not evaluated
            return annotation
        # raise TypeError(f'{repr(forward_key)}: Unsupported ForwardRef: {annotation}')
    return annotation


class LogicalType(type):  # noqa
    def __instancecheck__(cls, obj):
        if isinstance(obj, LogicalType):
            return super().__instancecheck__(obj)
        if cls.combinator:
            for arg in cls.args:
                if isinstance(arg, type) and isinstance(obj, arg):
                    return True
            return False
        origin = getattr(cls, "__origin__", None)
        if isinstance(origin, type):
            if not isinstance(obj, origin):
                return False
            try:
                cls(obj)
                return True
            except exc.ParseError:
                return False
        return False

    @property
    def args(cls):
        return cls.__dict__.get("__args__", [])

    @property
    def combinator(cls):
        return cls.__dict__.get("__combinator__", None)

    def resolve_origins(cls) -> List[type]:
        if cls.combinator:
            origins = []
            for arg in cls.args:
                if isinstance(arg, LogicalType):
                    for ori in arg.resolve_origins():
                        if ori not in origins:
                            origins.append(ori)
                elif isinstance(arg, type):  # exclude forward ref
                    if arg not in origins:
                        origins.append(arg)
            return origins

        origin = getattr(cls, "__origin__", None)
        if isinstance(origin, LogicalType):
            return origin.resolve_origins()
        elif isinstance(origin, type):
            return [origin]
        return []

    def resolve_combined_origin(cls) -> Optional["LogicalType"]:
        if cls.combinator:
            return cls
        origin = getattr(cls, "__origin__", None)
        if isinstance(origin, LogicalType):
            return origin.resolve_combined_origin()
        return None

    @classmethod
    def _parse_arg(mcs, arg):
        if arg is None:
            return type(None)

        if isinstance(arg, ForwardRef):
            return arg

        if isinstance(arg, mcs):
            return arg

        __origin = get_origin(arg)
        if __origin:
            # like List[str] Literal["value"]
            _new_args = get_args(arg) or ()
        else:
            # only if not origin is detected, we let go the class arg
            # for py>3.8, something like list[int] / dict[str, int] in also a class
            if isinstance(arg, type):
                return arg
            __origin = Literal
            _new_args = (arg,)
        return Rule.annotate(__origin, *_new_args)

    def resolve_forward_refs(cls):
        if not cls.combinator:
            return
        args = []
        resolved = False
        for i, arg in enumerate(cls.args):
            arg, resolved = resolve_forward_type(arg)
            if resolved:
                arg = cls._parse_arg(arg)
            args.append(arg)
        if resolved:
            # only adjust args if resolved
            setattr(cls, "__args__", tuple(args))
        return resolved

    def register_forward_refs(
        cls,
        global_vars: Dict[str, Any] = None,
        forward_refs=None,
        forward_key: str = None,
    ):
        if not cls.combinator:
            return
        args = []
        registered = False
        for i, arg in enumerate(cls.args):
            key = f"{forward_key}:{i}" if forward_key else str(i)
            if isinstance(arg, ForwardRef):
                arg = register_forward_ref(
                    annotation=arg,
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=key,
                )
                arg = cls._parse_arg(arg)
                registered = True
            elif isinstance(arg, LogicalType) and arg.combinator:
                if arg.register_forward_refs(
                    global_vars=global_vars, forward_refs=forward_refs, forward_key=key
                ):
                    registered = True
            args.append(arg)
        if registered:
            # only adjust args if registered
            setattr(cls, "__args__", tuple(args))
        return registered

    @classmethod
    def combine(mcs, operator: str, *args):
        __args = []
        for arg in args:
            if isinstance(arg, str):
                arg = ForwardRef(arg)

            arg = mcs._parse_arg(arg)

            if arg in __args:
                # avoid duplicate
                continue
            __args.append(arg)

        return mcs(
            OPERATOR_NAMES.get(operator, operator),
            (),
            {"__args__": __args, "__combinator__": operator},  # noqa
        )  # noqa

    def combine_by(cls, comb: str, other, reverse: bool = False):
        if cls.combinator == comb:
            left_parts = cls.args
        else:
            left_parts = (cls,)
        if isinstance(other, LogicalType) and comb == other.combinator:
            right_parts = other.args
        else:
            right_parts = other if isinstance(other, tuple) else (other,)
        args = (*right_parts, *left_parts) if reverse else (*left_parts, *right_parts)
        return cls.combine(comb, *args)

    @classmethod
    def all_of(mcs, *args):
        return mcs.combine("&", *args)

    @classmethod
    def any_of(mcs, *args):
        return mcs.combine("|", *args)

    @classmethod
    def one_of(mcs, *args):
        return mcs.combine("^", *args)

    @classmethod
    def not_of(mcs, value):
        return mcs.combine("~", value)

    def __and__(cls: T, other: OTHER) -> Union[T, OTHER]:
        return cls.combine_by("&", other)

    def __rand__(cls: T, other: OTHER) -> Union[OTHER, T]:
        return cls.combine_by("&", other, reverse=True)

    def __or__(cls: T, other: OTHER) -> Union[T, OTHER]:
        if getattr(other, "__origin__", None) == Union:
            return cls.combine_by("|", other.__args__)
        return cls.combine_by("|", other)

    def __ror__(cls: T, other: OTHER) -> Union[OTHER, T]:
        if getattr(other, "__origin__", None) == Union:
            return cls.combine_by("|", other.__args__, reverse=True)
        return cls.combine_by("|", other, reverse=True)

    def __xor__(cls: T, other: OTHER) -> Union[T, OTHER]:
        return cls.combine_by("^", other)

    def __rxor__(cls: T, other: OTHER) -> Union[OTHER, T]:
        return cls.combine_by("^", other, reverse=True)

    def __invert__(cls):
        if cls.combinator == "~":
            return cls.args[0]
        return cls.combine("~", cls)

    # def __getitem__(cls, item: T) -> typing.Iterable[T]:
    #     return item

    def __repr__(cls):
        def _repr(_arg):
            if isinstance(_arg, LogicalType):
                return repr(_arg)
            return getattr(_arg, "__name__", None) or repr(_arg)

        if not cls.args:
            origin = getattr(cls, "__origin__", None)
            validators = getattr(cls, "__validators__", [])
            constraints = ", ".join(f"{key}={val}" for key, val, c in validators)
            origin_repr = ""
            if origin:
                origin_repr = _repr(origin)
                if constraints:
                    origin_repr += ", "
            return f"{cls.__name__}({origin_repr}{constraints})"

        args_repr = ", ".join([_repr(arg) for arg in cls.args])
        l_par = "(" if cls.combinator else "["
        r_par = ")" if cls.combinator else "]"
        return f"{cls.__name__}{l_par}{args_repr}{r_par}"

    def __str__(cls):
        return repr(cls)

    def parse(cls, value, *args, **kwargs):
        pass

    # compat Python 3.7, not adding the positional only sign
    def logical_parse(cls, value, context: RuntimeContext = None, **kwargs):
        context = context or RuntimeContext()
        # IMPORTANT:
        # we must do clone here (as the parser do make_runtime)
        # to prompt a new RuntimeOptions, to collect the error in this layer

        if cls.combinator == "&":
            for con in cls.args:
                try:
                    # each value transform will pass on to the next condition
                    # like NormalFloat = AllOf(Float, Not(AbnormalFloat))('3.3')
                    value = context.transformer(value, con)
                except Exception as e:
                    context.handle_error(e)
                    break
            return value

        elif cls.combinator == "|":
            # 1. check EXACT identical type
            for con in cls.args:
                if type(value) == con:
                    return value
            # 2. try to transform in strict mode
            # strict_transformer = options.get_transformer(no_explicit_cast=True, no_data_loss=True)

            for con in cls.args:
                with context.enter(cls.combinator) as new_context:
                    try:
                        # error isolation
                        value = new_context.transformer(value, con)
                    except Exception as e:
                        context.collect_tmp_error(e)
                    else:
                        context.clear_tmp_error()
                        break

        elif cls.combinator == "^":
            # 1. check EXACT identical type
            # because args are de-duplicate, so value can only end up one type
            for con in cls.args:
                if type(value) == con:
                    return value

            xor = None

            for con in cls.args:
                with context.enter(cls.combinator) as new_context:
                    try:
                        value = new_context.transformer(value, con)
                        if xor is None:
                            xor = con
                        else:
                            context.handle_error(
                                exc.OneOfViolatedError(
                                    f"More than 1 conditions ({xor}, {con}) is True in XOR conditions"
                                )
                            )
                            xor = None
                            break
                    except Exception as e:
                        context.collect_tmp_error(e)

            if xor is not None:
                # only one condition is satisfied in XOR
                context.clear_tmp_error()

        elif cls.combinator == "~":
            for con in cls.args:
                with context.enter(cls.combinator) as new_context:
                    try:
                        new_context.transformer(value, con)
                        context.handle_error(
                            exc.NegateViolatedError(
                                f"Negate condition: {con} is violated"
                            )
                        )
                    except Exception:  # noqa
                        break
                        # value = cls._get_error_result(e, value, **kwargs)

        context.raise_error()  # raise error if collected
        return value

    def __call__(cls, value, *args, **kwargs):
        if cls.combinator:
            return cls.logical_parse(value, *args, **kwargs)
        return cls.parse(value, *args, **kwargs)


class ConstraintMode:
    mode = None
    support_constraints = None

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        return False


class Lax(ConstraintMode):
    mode = "lax"


class Constraints:
    TYPE_SPEC_CONSTRAINTS = {
        "max_digits": NUM_TYPES,
        "decimal_places": (float, Decimal),
        "multiple_of": NUM_TYPES,
        "unique_items": SEQ_TYPES,
        # "contains": SEQ_TYPES,
        # "max_contains": SEQ_TYPES,
        # "min_contains": SEQ_TYPES,
        # "dependencies": MAP_TYPES,
    }
    CONSTRAINT_TYPES = {
        "length": (int,),
        "max_length": (int,),
        "min_length": (int,),
        # "contains": (type,),
        # "min_contains": (int,),
        # "max_contains": (int,),
        "decimal_places": (int,),
        "max_digits": (int,),
        "multiple_of": (int, float),
        "unique_items": (bool,),
    }
    # default type is resolved to "string"

    def __init__(self, rule_cls: Type["Rule"]):
        self.rule_cls = rule_cls

    @property
    def origin_type(self):
        return self.rule_cls.__origin__

    @origin_type.setter
    def origin_type(self, t: type):
        if isinstance(t, type):
            self.rule_cls.__origin__ = t
            self.rule_cls.__origin_transformer__ = (
                self.rule_cls.transformer_cls.resolver_transformer(t)
            )

    def valid_length(self, bounds: dict):
        length = bounds.get("length")
        max_length = bounds.get("max_length")
        min_length = bounds.get("min_length")
        if length is not None:
            if not (isinstance(length, int) and length >= 0):
                raise exc.ConfigError(f"Rule length: {length} must be a int >= 0")
            if min_length is not None:
                if min_length > length:
                    raise exc.ConfigError(
                        f"Rule length: {length} and min_length: {min_length} both specified"
                    )
                else:
                    pop(bounds, "min_length")
                    min_length = None
            if max_length is not None:
                if max_length < length:
                    raise exc.ConfigError(
                        f"Rule length: {length} and max_length: {max_length} both specified"
                    )
                else:
                    pop(bounds, "max_length")
                    max_length = None
        else:
            if min_length is not None:
                if not (isinstance(min_length, int) and min_length >= 0):
                    raise exc.ConfigError(
                        f"Rule min_length: {min_length} must be a int >= 0"
                    )

                if not min_length:
                    pop(bounds, "min_length")
                    min_length = None

            if max_length is not None:
                if not (isinstance(max_length, int) and max_length > 0):
                    raise exc.ConfigError(
                        f"Rule max_length: {max_length} must be a int > 0"
                    )
                if min_length is not None:
                    if max_length < min_length:
                        raise exc.ConfigError(
                            f"Rule max_length: {max_length} must >= min_length: {min_length}"
                        )

        if {length, min_length, max_length} != {None}:
            # has length constraints, validate type
            if self.origin_type:
                if not hasattr(self.origin_type, "__len__"):
                    # just warning here, we will coerce to str in runtime
                    if issubclass(self.origin_type, (int, float, Decimal)):
                        warnings.warn(
                            f"Rule specify length constraints for type: {self.origin_type} "
                            f"that does not support length, we recommend to use "
                            f'"max_digits" and "round" for number types'
                        )
                    else:
                        warnings.warn(
                            f"Rule specify length constraints for type: {self.origin_type} "
                            f"that does not support length, value will be convert to str to validate length"
                        )

    def valid_bounds(self, bounds: dict):
        _max = _min = None
        _max_t = _min_t = None

        gt = bounds.get("gt")
        ge = bounds.get("ge")
        lt = bounds.get("lt")
        le = bounds.get("le")

        t = self.origin_type
        if t == bool:
            raise TypeError(f"bool type does not support bounds")

        if gt is not None:
            if not callable(gt):
                _min_t = type(gt)
                _min = gt
            if t and not hasattr(t, "__le__"):
                raise exc.ConfigError(
                    f"Rule: type {t} does not support <gt> constraint for not providing __le__ method"
                )

        if ge is not None:
            if _min is not None:
                raise exc.ConfigError("Rule gt/ge cannot assign together")

            if not callable(ge):
                _min_t = type(ge)
                _min = ge

            if t and not hasattr(t, "__lt__"):
                raise exc.ConfigError(
                    f"Rule: type {t} does not support <ge> constraint for not providing __lt__ method"
                )

        if lt is not None:
            if not callable(lt):
                _max_t = type(lt)
                _max = lt

            if t and not hasattr(t, "__ge__"):
                raise exc.ConfigError(
                    f"Rule: type {t} does not support <lt> constraint for not providing __ge__ method"
                )

        if le is not None:
            if _max is not None:
                raise exc.ConfigError("Rule lt/le cannot assign together")

            if not callable(le):
                _max_t = type(le)
                _max = le

            if t and not hasattr(t, "__gt__"):
                raise exc.ConfigError(
                    f"Rule: type {t} does not support <le> constraint for not providing __gt__ method"
                )

        if _min_t and _max_t:
            if _min_t != _max_t:
                raise exc.ConfigError(
                    f"Rule gt/ge type {_min_t} must equal to lt/le type {_max_t}"
                )

        _t = _max_t or _min_t
        if _t:
            if self.origin_type:
                if (
                    isinstance(self.origin_type, LogicalType)
                    and self.origin_type.combinator
                ):
                    resolved = False
                    for arg in self.origin_type.__args__:
                        if {arg, _t} in TYPE_EXACT_TOLERANCE:
                            resolved = True
                            break
                        if issubclass(arg, _t):
                            resolved = True
                            break
                    if not resolved:
                        raise exc.ConfigError(
                            f"Rule range type {_t} not resolved in type: {self.origin_type}"
                        )

                else:
                    if not issubclass(self.origin_type, _t):
                        if {self.origin_type, _t} in TYPE_EXACT_TOLERANCE:
                            pass
                        else:
                            raise exc.ConfigError(
                                f"Rule range type {_t} must equal to value type {self.origin_type}"
                            )
            else:
                self.origin_type = _t

            if _min is not None and _max is not None:
                if _min >= _max:
                    raise exc.ConfigError(
                        f"Rule lt/le ({repr(_max)}) must > gt/ge ({repr(_min)})"
                    )
                if isinstance(_max, int) and isinstance(_min, int):
                    if gt and lt:
                        if _max - _min < 2:
                            raise exc.ConfigError(
                                f"Rule int lt: {_max} - gt: {_min} must greater or equal than 2"
                            )

    def valid_types(self, bounds: dict):
        for key, val in bounds.items():
            value_types = self.CONSTRAINT_TYPES.get(key)
            origin_types = self.TYPE_SPEC_CONSTRAINTS.get(key)
            if value_types and not isinstance(val, value_types):
                raise exc.ConfigError(
                    f"Constraint: {repr(key)} should be {value_types} object, got {val}"
                )
            if origin_types:
                if self.origin_type:
                    if (
                        isinstance(self.origin_type, LogicalType)
                        and self.origin_type.combinator
                    ):
                        if not any(
                            issubclass(tp, origin_types)
                            for tp in self.origin_type.__args__
                        ):
                            raise exc.ConfigError(
                                f"Constraint: {repr(key)} is only for type: "
                                f"{origin_types}, got {self.origin_type.__args__}"
                            )
                    else:
                        if origin_types == NUM_TYPES and self.origin_type == bool:
                            # bool is subclass of int
                            raise exc.ConfigError(
                                f"Constraint: {repr(key)} is only for type: {origin_types}, got bool"
                            )
                        if not issubclass(self.origin_type, origin_types):
                            raise exc.ConfigError(
                                f"Constraint: {repr(key)} is only for type: "
                                f"{origin_types}, got {self.origin_type}"
                            )
                else:
                    # set the type if missing
                    self.origin_type = origin_types[0]

    def validate_constraints(self, constraints: dict):
        if "const" in constraints:
            const = constraints["const"]
            if self.origin_type:
                if isinstance(self.origin_type, LogicalType):
                    raise exc.ConfigError(
                        f"Rule const: {repr(const)} cannot apply to LogicalType"
                    )
                if not isinstance(const, self.origin_type):
                    if {type(const), self.origin_type} in TYPE_EXACT_TOLERANCE:
                        pass
                    else:
                        raise exc.ConfigError(
                            f"Rule const: {repr(const)} not instance of type: {self.origin_type}"
                        )
            # else:
            #     # transform type before check const
            #     self.origin_type = type(const)
            # we do not force a type to const, it is up to developer to decide
            # whether to transform before const check
            return {"const": const}  # ignore other constraints
        elif "enum" in constraints:
            enum = constraints["enum"]
            if isinstance(enum, EnumMeta):
                member_type = getattr(enum, "_member_type_", None)
                if member_type is object:
                    member_type = None
                if member_type:
                    if self.origin_type:
                        if not issubclass(member_type, self.origin_type):
                            raise exc.ConfigError(
                                f"Rule enum member type: {member_type} is "
                                f"conflict with origin type: {self.origin_type}"
                            )
                    else:
                        self.origin_type = member_type
            elif multi(enum):
                enum = list(enum)
            else:
                raise exc.ConfigError(
                    f"Invalid enum: {enum}, must be a Enum subclass of list/tuple/set"
                )
            return {"enum": enum}  # ignore other constraints

        constraints = {k: v for k, v in constraints.items() if v is not None}

        if "unique_items" in constraints and not constraints["unique_items"]:
            # only True is valid
            pop(constraints, "unique_items")

        if "decimal_places" in constraints:
            decimals = constraints["decimal_places"]
            digits = constraints.get("max_digits")
            if decimals and digits:
                # 0.123
                if digits < decimals:
                    raise exc.ConfigError(
                        f"Rule: constraint max_digits: {digits} must >= {decimals}"
                    )

        # other constraints other that const is considered not-null
        self.valid_types(constraints)
        self.valid_bounds(constraints)
        self.valid_length(constraints)
        return constraints

    def validate_base_constraints(self):
        # TODO
        """
        a: PositiveInt = Field(lt=-5)
        like above is considered invalid, but it will be checked in bounds
        some may hard to check
        a: PositiveInt = Field(gt=-5)
        this will override the base constraints, and violate the base class definition
        we should give a warning or error in that case
        """

    def generate_validators(self) -> List[Tuple[str, Any, Callable]]:
        constraint_mode = {}
        constraints = dict()    # for python >= 3.7, ordered dict is dict
        for key in self.rule_cls.__constraints__:
            if hasattr(self.rule_cls, key) and hasattr(self.__class__, key):
                value = getattr(self.rule_cls, key)
                if unprovided(value):
                    # this is a sign that the subclass cancel a constraint from the base class
                    # and to differ with None (for const constraint, None is still consider a valid param)
                    continue
                if isinstance(value, ConstraintMode):
                    constraint_mode[key] = value.mode
                    value = value.value
                constraints[key] = value

        if not constraints:
            return []

        constraints = self.validate_constraints(constraints)
        validators = []
        for key, val in constraints.items():
            mode = constraint_mode.get(key)
            if mode:
                name = f"{mode}_{key}"
            else:
                name = key
            func = getattr(self.__class__, name, None)
            if not func:
                raise exc.ConfigError(
                    f"{self.__class__}: constraint {repr(name)} not discovered,"
                    f" you can override this class and custom it"
                )
            validators.append((key, val, func))
        return validators

    @classmethod
    def decimal_places(cls, value, d):
        digits, decimals = cls._parse_decimal(value)

        if decimals > d:
            raise ValueError

        if isinstance(value, Decimal):
            # if current decimal is Decimal('1.3') and decimal places is 2
            # we will make it Decimal('1.30') by using round
            return round(value, d)
        return value

    @classmethod
    def lax_decimal_places(cls, value, r):
        return round(value, r)

    @classmethod
    def multiple_of(cls, value, of: int):
        mod = value % of
        if mod:
            raise ValueError
        return value

    @classmethod
    def lax_multiple_of(cls, value, of: int):
        mod = value % of
        if mod:
            return (value // of) * of
        return value

    @classmethod
    def _parse_decimal(cls, value):
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        digit_tuple, exponent = value.as_tuple()[1:]
        if exponent in {"F", "n", "N"}:
            raise ValueError

        if exponent >= 0:
            digits = len(digit_tuple) + exponent
            decimals = 0
        else:
            if abs(exponent) > len(digit_tuple):
                digits = abs(exponent)
            else:
                digits = len(digit_tuple)
            decimals = abs(exponent)
        return digits, decimals

    @classmethod
    def max_digits(cls, value, max_digits: int):
        digits, decimals = cls._parse_decimal(value)
        if digits > max_digits:
            raise ValueError
        return value

    @classmethod
    def lax_max_digits(cls, value, max_digits: int):
        digits, decimals = cls._parse_decimal(value)
        if digits <= max_digits:
            return value

        delta = digits - max_digits

        # 123.456
        # decimals: 3
        # max_digits: 4
        # delta: 3

        if decimals >= delta:
            return round(value, decimals - delta)
        raise ValueError

    @classmethod
    def const(cls, value, v):
        if value != v:
            raise ValueError
        # 0 False
        # 1 True
        if type(value) != type(v):
            if {type(value), type(v)} in TYPE_EXACT_TOLERANCE:
                pass
            else:
                raise ValueError
        return v

    @classmethod
    def lax_const(cls, value, v):
        return v

    @classmethod
    def enum(cls, value, lst):
        if isinstance(lst, EnumMeta):
            # return the value instead of the enum type
            return lst(value).value

        if isinstance(value, Enum):
            value = value.value

        if value not in lst:
            raise ValueError
        return value

    @classmethod
    def lax_enum(cls, value, lst):
        if isinstance(lst, EnumMeta):
            # return the value instead of the enum type
            return lst(value).value

        if isinstance(value, Enum):
            value = value.value

        if value not in lst:
            return list(lst)[0]
        return value

    @classmethod
    def regex(cls, value, r):
        if not re.fullmatch(r, str(value)):
            raise ValueError
        return value

    @classmethod
    def gt(cls, value, gt):
        if value <= gt:
            raise ValueError
        return value

    @classmethod
    def ge(cls, value, ge):
        if value < ge:
            raise ValueError
        return value

    @classmethod
    def lax_ge(cls, value, ge):
        if value < ge:
            return ge
        return value

    @classmethod
    def lt(cls, value, lt):
        if value >= lt:
            raise ValueError
        return value

    @classmethod
    def le(cls, value, le):
        if value > le:
            raise ValueError
        return value

    @classmethod
    def lax_le(cls, value, le):
        if value > le:
            return le
        return value

    @classmethod
    def length(cls, value, lg):
        v = value
        if not hasattr(value, "__len__"):
            v = str(value)
        if len(v) != lg:
            raise ValueError
        return value

    @classmethod
    def lax_length(cls, value, lg):
        v = value
        converted = False
        if not hasattr(value, "__len__"):
            converted = True
            v = str(value)
        if len(v) != lg:
            if converted or len(v) < lg:
                raise ValueError
            return value[:lg]
        return value

    @classmethod
    def max_length(cls, value, m):
        v = value
        if not hasattr(value, "__len__"):
            v = str(value)
        if len(v) > m:
            raise ValueError
        return value

    @classmethod
    def lax_max_length(cls, value, m):
        v = value
        converted = False
        if not hasattr(value, "__len__"):
            converted = True
            v = str(value)
        if len(v) > m:
            if converted:
                raise ValueError
            return value[:m]
        return value

    @classmethod
    def min_length(cls, value, m):
        v = value
        if not hasattr(value, "__len__"):
            v = str(value)
        if len(v) < m:
            raise ValueError
        return value

    @classmethod
    def unique_items(cls, value: list, u):
        if not u:
            return value
        lst = []
        for val in value:
            if val in lst:
                raise ValueError(f"value is not unique")
            lst.append(val)
        return value

    @classmethod
    def lax_unique_items(cls, value: list, u):
        if not u:
            return value
        lst = []
        for val in value:
            if val in lst:
                continue
            lst.append(val)
        # if not strict, just return a unique version of the input
        return type(value)(lst)  # noqa


class Rule(metaclass=LogicalType):
    transformer_cls = TypeTransformer
    constraints_cls = Constraints
    context_cls = RuntimeContext

    __origin__: type = None
    __applied__: bool = False
    __abstract__: bool = False
    __args__: Tuple[type, ...] = None
    __ellipsis_args__: bool = False
    __arg_transformers__: Tuple[Callable, ...] = None
    __origin_transformer__: Callable = None
    __args_parser__: Callable = None

    __validators__: List[Tuple[str, Any, Callable]] = []
    __constraints__: List[str] = [
        # define the constraints and it's order
        "gt",
        "ge",
        "lt",
        "le",
        "const",
        "enum",
        "regex",
        "decimal_places",
        "multiple_of",
        "max_digits",
        "length",
        "max_length",
        "min_length",
        # "contains",
        # "max_contains",
        # "min_contains",
        "unique_items",
    ]
    __transformer__: Callable

    # flag for document
    primitive: Literal[
        "null", "boolean", "object", "array", "integer", "number", "string"
    ]
    format: Optional[str]
    extra: dict  # additional data to the generated schema document

    # constraints
    gt: Any  # exclusiveMinimum
    ge: Any  # minimum
    lt: Any  # exclusiveMaximum
    le: Any  # maximum
    const: Any
    enum: Union[Enum, list, tuple, set]
    regex: str
    length: int
    max_length: int
    min_length: int

    # number constraints
    decimal_places: int
    multiple_of: int
    max_digits: int

    # array constraints
    unique_items: bool
    # rule-validate constraints
    contains: type = None
    max_contains: int = None
    min_contains: int = None

    # dependencies: Dict[str, Union[List[str], Dict[str, List[str]]]]     # for dict type only
    # this property can be defined in schema.__options__
    # https://json-schema.org/understanding-json-schema/reference/object.html
    # https://json-schema.org/understanding-json-schema/reference/array.html

    # **kwargs: str -> "additionalProperties": {"type": "string"}

    # json dict can only support str key, we can only extend it to finite primitive types
    # Dict[str, int] patternProperties: {".*": {"type": integer}}
    # Dict[int, int] patternProperties: {"[0-9]": {"type": integer}}, propertyNames: {"type": "integer"}
    # Dict[bool, int] patternProperties: {"true|false": {"type": integer}}, propertyNames: {"type": "boolean"}

    def __class_getitem__(cls, item):
        args = ()
        origin = cls.__origin__
        if isinstance(item, tuple):
            args = item
        elif cls.__origin__:
            args = (item,)
        else:
            origin = item
        if args and cls.__args__:
            raise exc.ConfigError(f"{cls}: args: {cls.__args__} already specified")
        return cls.annotate(origin, *args)

    def __init_subclass__(cls, **kwargs):
        # if not cls.__origin__:
        origin = None
        class_getitem = cls.__dict__.get("__class_getitem__")
        for base in cls.__bases__:
            if issubclass(base, Rule):
                if not class_getitem:
                    class_getitem = getattr(base, "__class_getitem__", None)
                continue
            if origin:
                raise TypeError(f"{cls}: Multiple origin types: {origin}, {base}")
            origin = base

        if origin:
            if not cls.__origin__:
                cls.__origin__ = origin
            elif issubclass(origin, cls.__origin__):
                cls.__origin__ = origin
            else:
                raise TypeError(
                    f"{cls}: Invalid origin: {origin} of sub type:"
                    f" not subclass of base type: {cls.__origin__}"
                )

        if cls.__origin__:
            if isinstance(cls.__origin__, ForwardRef):
                if not cls.__origin__.__forward_evaluated__:
                    raise TypeError(
                        f"{cls}: cannot setup with unevaluated ForwardRef as origin"
                    )
                cls.__origin__ = cls.__origin__.__forward_value__

            if not isinstance(cls.__origin__, type):
                raise TypeError(f"Invalid origin: {cls.__origin__}, must be a class")
            cls.__abstract__ = bool(
                getattr(cls.__origin__, "__abstractmethods__", None)
            )

            cls.__origin_transformer__ = cls.transformer_cls.resolver_transformer(
                cls.__origin__
            )
            if not cls.__origin_transformer__:
                warnings.warn(
                    f"{cls}: origin type: {cls.__origin__} got no transformer resolved, "
                    f"will just pass {cls.__origin__}(data) at runtime"
                )

        if cls.__args__:
            if hasattr(cls, "__class_getitem__"):

                def _cannot_getitem(*_args):
                    raise TypeError(
                        f"{cls.__name__}: argument is already set, "
                        f"cannot perform getitem ({_args})"
                    )

                cls.__class_getitem__ = _cannot_getitem

            if not multi(cls.__args__):
                cls.__args__ = (cls.__args__,)  # noqa
            arg_transformers = []
            for arg in cls.__args__:
                if isinstance(arg, ForwardRef):
                    if arg.__forward_evaluated__:
                        arg = arg.__forward_value__
                    else:
                        # we will resolve it later
                        arg_transformers.append(None)
                        continue
                if arg is None:
                    arg_transformers.append(None)
                    if cls.__origin__ and issubclass(
                        cls.__origin__, NONE_ARG_ALLOWED_TYPES
                    ):
                        continue
                    warnings.warn(
                        f"None arg: {arg} detected where origin type: {cls.__origin__} is not in "
                        f"{NONE_ARG_ALLOWED_TYPES}"
                    )
                    continue

                if not isinstance(arg, type):
                    raise TypeError(f"Invalid arg: {arg}, must be a class")
                transformer = cls.transformer_cls.resolver_transformer(arg)
                if not transformer:
                    warnings.warn(
                        f"{cls}: arg type: {arg} got no transformer resolved, "
                        f"will just pass {arg}(data) at runtime"
                    )

                arg_transformers.append(transformer)
            cls.__arg_transformers__ = tuple(arg_transformers)
            cls.__args_parser__ = cls.resolve_args_parser()
            if not cls.__args_parser__:
                warnings.warn(
                    f"{cls}: type: {cls.__origin__} with __args__ cannot resolve an args parser, "
                    f"you should inherit resolve_args_parser and specify yourself"
                )
        else:
            if class_getitem and not cls.__dict__.get("__class_getitem__"):
                # we should do a little hack here
                # because according to MRO
                # class UniqueTuple(tuple, Array):
                # UniqueTuple[str] will end up calling __class_getitem__ of tuple
                # and get a GenericAlias instead of Rule
                func = partial(class_getitem.__func__, cls)
                func.__func__ = class_getitem.__func__
                cls.__class_getitem__ = func
                # if __args__ is present, we do not set class getitem then

        cls.__validators__ = cls.constraints_cls(cls).generate_validators()
        cls._validate_contains()

    @classmethod
    def annotate(
        cls,
        type_=None,
        *args_,
        constraints: Dict[str, Any] = None,
        global_vars: Dict[str, Any] = None,
        forward_refs=None,
    ):
        args = []
        ellipsis_args = False

        if type_ == Any:
            if args_:
                warnings.warn(f"Any type cannot specify args: {args_}")
            if constraints:
                warnings.warn(f"Any type cannot specify constraints: {constraints}")
            return Rule

        elif type_ == Literal:
            # special for literal type
            constraints = constraints or {}
            if len(args_) == 1:
                constraints["const"] = args_[0]
            elif len(args_) > 1:
                constraints["enum"] = args_
            else:
                raise exc.ConfigError(f"empty literal")
            type_ = cls.__origin__ or type(args_[0])
        else:
            for arg in args_:
                if isinstance(arg, TypeVar):
                    type_cons: tuple = getattr(arg, "__constraints__", None)
                    if type_cons:
                        arg = LogicalType.any_of(*type_cons)
                    else:
                        # stand for any
                        # TODO: support type var validation
                        arg = Rule
                    args.append(arg)
                    continue

                if arg is ...:
                    if isinstance(type_, type) and not issubclass(type_, tuple):
                        raise exc.ConfigError(
                            f"{cls} args: {args_} with ... only apply to tuple, got {type_}"
                        )
                    ellipsis_args = True
                    continue
                if arg is None:
                    # some origin like Generator / AsyncGenerator / Union / Callable need None arg
                    args.append(arg)
                    continue
                annotation = cls.parse_annotation(
                    arg, global_vars=global_vars, forward_refs=forward_refs
                )
                # this annotation can be a ForwardRef
                # not with constraints, cause that is applied to upper layer
                if annotation is None:
                    continue
                args.append(annotation)

        # if not args and not constraints:
        #     return type_

        name = cls.__name__
        if type_ == Union:
            type_ = LogicalType.any_of(*args)
            # clear the args for union
            args = []

        if isinstance(type_, LogicalType):
            # if type_.combinator:
            #     # we cannot directly inherit combined rules
            #     # just add a AllOf condition
            #     return type_ & cls.annotate(
            #         cls.__origin__, *args,
            #         constraints=constraints,
            #         forward_refs=forward_refs,
            #         global_vars=global_vars
            #     )
            if issubclass(type_, cls):
                # use the subclass name
                name = type_.__name__

        # if type_ == Union:
        #     any_of = LogicalType.any_of(*args)
        #     if not constraints:
        #         return any_of
        #     return any_of & cls.annotate(constraints=constraints)   # no need to pass globals

        attrs = {}
        if type_:
            attrs.update(__origin__=type_)
        if args:
            attrs.update(__args__=args)
        if ellipsis_args:
            attrs.update(__ellipsis_args__=True)
        if constraints:
            attrs.update(constraints)
        return LogicalType(name, (cls,), attrs)

    @classmethod
    def parse_annotation(
        cls,
        annotation,
        constraints=None,
        global_vars=None,
        forward_refs=None,
        forward_key=None,
    ):
        if isinstance(annotation, str):
            if not annotation:
                raise TypeError(
                    f"{repr(forward_key)}: Empty forward ref string: {annotation}"
                )
            # ForwardRef
            annotation = ForwardRef(annotation)

        if isinstance(annotation, ForwardRef):
            annotation = register_forward_ref(
                annotation=annotation,
                constraints=constraints,
                global_vars=global_vars,
                forward_refs=forward_refs,
                forward_key=forward_key,
            )
            if isinstance(annotation, ForwardRef):
                # if annotation still cannot be resolved by global vars
                # directly return
                return annotation

        if annotation is Any:
            return Rule  # use empty rule as any

        # no constraints, we can directly use it
        if isinstance(annotation, LogicalType):
            if annotation.combinator:
                annotation.register_forward_refs(
                    # we don't need to pass constraints here
                    # as those will be combined in below logics
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=forward_key,
                )
            # do not detect origin for Logical types (including Rule)
            origin = None
        else:
            origin = get_origin(annotation)

        if origin:
            # first resolve origin
            # generic types like list[int] with origin is still a type
            args = get_args(annotation) or ()
            constraints = constraints or {}
            return cls.annotate(
                origin,
                *args,
                constraints=constraints,
                forward_refs=forward_refs,
                global_vars=global_vars,
            )
        elif annotation:
            if isinstance(annotation, type):
                if constraints:
                    return cls.annotate(
                        annotation,
                        constraints=constraints,
                        forward_refs=forward_refs,
                        global_vars=global_vars,
                    )
                else:
                    # no constraints, we can directly use it
                    return annotation
            raise TypeError(
                f"{repr(forward_key)}: invalid annotation: {annotation}"
            )
        elif constraints:
            return cls.annotate(
                constraints=constraints,
                forward_refs=forward_refs,
                global_vars=global_vars,
            )
        return None

    @classmethod
    def check_type(cls, t):
        return True

    @classmethod
    def merge_type(cls, t):
        if not t or not isinstance(t, type):
            return cls
        if not cls.__origin__:
            return t
        if cls.combinator:
            return t & cls
        if cls.__origin__ and issubclass(cls.__origin__, t):
            return cls
        constraints = {}
        for name, val, func in cls.__validators__:
            constraints[name] = getattr(cls, name, val)
            # do not lose the mode info
            # so we get value from cls first

        # try to find a strong constraint
        if 'const' in constraints or 'enum' in constraints:
            return cls

        if isinstance(t, LogicalType):
            if t.combinator:
                return t & cls
            elif issubclass(t, Rule):
                for name, val, func in t.__validators__:
                    constraints[name] = getattr(t, name, val)
                if 'const' in constraints or 'enum' in constraints:
                    return t
                return Rule.annotate(
                    t.__origin__ or cls.__origin__,
                    *(t.__args__ or cls.__args__ or []),
                    constraints=constraints
                )
        elif issubclass(t, Enum):
            # do not need to apply constraint to a strong type
            return t
        return Rule.annotate(
            t,
            *(cls.__args__ or []),
            constraints=constraints
        )

    @classmethod
    def parse(cls, value, context: RuntimeContext = None):
        # use __options__ instead of options is to identify much clearer with other subclass init kwargs
        context = context or cls.context_cls()
        options = context.options
        # IMPORTANT:
        # we must do clone here (as the parser do make_runtime)
        # to prompt a new RuntimeOptions, to collect the error in this layer
        value = cls.pre_validate(value, context)

        if cls.__origin__:
            # no matter cls.__transformer__ is None or not
            if cls.__applied__ and isinstance(value, cls.__origin__):
                # this is final for @utype.apply
                # since the actual type is hidden, so the value of the "hidden" type
                # is consider passed the type validation
                # [this property is not recommended to inherited by developer]
                return cls.post_validate(value, context)

            try:
                value = context.transformer.apply(
                    value, cls.__origin__, func=cls.__origin_transformer__
                )
            except Exception as e:
                error = exc.ParseError(origin_exc=e)
                # if type cannot convert, the following args and constraints cannot validate
                # can just abort and stop collect errors if it is specified
                context.handle_error(error, force_raise=True)

            if value is None:
                # do not continue if value is None after parse
                # optional / AnyOf(..., None) may happen to this
                # we just parse args and check constraints for not-None value
                return value

        if cls.__args_parser__:
            value = cls.__args_parser__(value, context)

            if not cls.__abstract__ and type(value) != cls.__origin__:
                # for abstract types (like Sequence / Iterable)
                # we just give an instance that satisfy those abstract methods (like a list instance)
                value = cls.__origin__(value)

        if not options.ignore_constraints:
            # if options ignore constraints, we will just do type transform
            # constraints_inst = cls.constraints_cls(cls, options=options)
            for key, constraint, validator in cls.__validators__:
                # constraint = getattr(cls, key)
                try:
                    value = validator(value, constraint)
                except Exception as e:
                    error = (
                        e
                        if isinstance(e, exc.ConstraintError)
                        else exc.ConstraintError(
                            origin_exc=e, constraint=key, constraint_value=constraint
                        )
                    )
                    # if validator already throw a constraint error
                    # may an inner constraint (like max_contains in contains) is violated
                    context.handle_error(error)

            if cls.contains:
                value = cls._parse_contains(value, context=context)

        context.raise_error()
        # raise error if collected
        # and leave the error the upper layer to collect
        return cls.post_validate(value, context)

    @classmethod
    def pre_validate(cls, value, context: RuntimeContext = None):
        # meant to be inherited to define user-specific logic before type transform
        return value

    @classmethod
    def post_validate(cls, value, context: RuntimeContext = None):
        # meant to be inherited to define user-specific logic after the transform and constraints validation
        return value

    def __init__(self, value):
        # just to let the IDE know that this class can be init with single param
        # this function will not get called
        self._value = self.parse(value)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self._value)})"

    def __str__(self):
        return f"{self.__class__.__name__}({repr(self._value)})"

    @classmethod
    def _validate_contains(cls):
        # validate max_contains and min_contains as well
        contains = cls.contains
        min_contains = cls.min_contains
        max_contains = cls.max_contains

        if max_contains or min_contains:
            if not contains:
                raise exc.ConfigError(
                    f"Rule with max_contains/min_contains must set <contains> constraint"
                )

            if max_contains is not None and min_contains is not None:
                if max_contains < min_contains:
                    raise exc.ConfigError(
                        f"Rule with max_contains: {max_contains} is little than min_contains"
                    )

        elif not contains:
            return

        from collections.abc import Iterable

        if isinstance(cls.__origin__, type) and not issubclass(
            cls.__origin__, Iterable
        ):
            raise exc.ConfigError(
                f"Rule: constraint: contains is only for Iterable, got {cls.__origin__}"
            )

    @classmethod
    def _parse_contains(cls, value, context: RuntimeContext):
        # validate max_contains and min_contains as well
        if not cls.contains:
            return value

        contains = 0
        for i, item in enumerate(value):
            with context.enter(route=i) as item_context:
                try:
                    item_context.transformer(item, cls.contains)
                except (TypeError, ValueError):
                    pass
                else:
                    contains += 1

        if not contains:
            context.handle_error(
                exc.ConstraintError(
                    f"{cls.contains} not contained in value",
                    constraint="contains",
                    constraint_value=cls.contains,
                )
            )
        elif cls.min_contains and contains < cls.min_contains:
            context.handle_error(
                exc.ConstraintError(
                    f"value contains {contains} of {cls.contains}, which is lower than min_contains",
                    constraint="min_contains",
                    constraint_value=cls.min_contains,
                )
            )
        elif cls.max_contains and contains > cls.max_contains:
            context.handle_error(
                exc.ConstraintError(
                    f"value contains {contains} of {cls.contains}, which is bigger than max_contains",
                    constraint="max_contains",
                    constraint_value=cls.max_contains,
                )
            )
        return value

    @classmethod
    def resolve_forward_refs(cls):
        # an override version of LogicalType.resolve_forward_refs
        if not cls.__args__:
            return False
        args = []
        arg_transformers = []
        resolved = False
        for arg, trans in zip(cls.__args__, cls.__arg_transformers__):
            if isinstance(arg, LogicalType):
                # including the Rule class and LogicalType with combinator
                if arg.resolve_forward_refs():
                    resolved = True
            elif isinstance(arg, ForwardRef):
                if arg.__forward_evaluated__:
                    arg = arg.__forward_value__
                    resolved = True
                    transformer = cls.transformer_cls.resolver_transformer(arg)
                    if not transformer:
                        warnings.warn(
                            f"{cls}: arg type: {arg} got no transformer resolved, "
                            f"will just pass {arg}(data) at runtime"
                        )
                    trans = transformer or trans
            args.append(arg)
            arg_transformers.append(trans)
        if resolved:
            cls.__args__ = tuple(args)
            cls.__arg_transformers__ = tuple(arg_transformers)
        return resolved

    @classmethod
    def resolve_args_parser(cls):
        if not cls.__origin__ or not cls.__args__:
            return None
        if issubclass(cls.__origin__, MAP_TYPES):
            return cls._parse_map_args
        elif issubclass(cls.__origin__, SEQ_TYPES):
            if issubclass(cls.__origin__, tuple) and not cls.__ellipsis_args__:
                return cls._parse_tuple_args
            return cls._parse_seq_args
        elif cls.__origin__ == type:
            return cls._parse_type_arg
        return None

    @classmethod
    def _parse_tuple_args(cls, value: tuple, context: RuntimeContext):
        result = []
        options = context.options

        if options.no_data_loss and len(value) > len(cls.__args__):
            for item in range(len(cls.__args__), len(value)):
                context.handle_error(exc.TupleExceedError(item=item, value=value[item]))

        for i, (arg, func) in enumerate(zip(cls.__args__, cls.__arg_transformers__)):
            if i >= len(value):
                context.handle_error(
                    exc.AbsenceError(
                        f"prefixItems required prefix: [{i}] not provided", item=i
                    )
                )

            with context.enter(route=i) as arg_context:
                try:
                    result.append(
                        arg_context.transformer.apply(value[i], arg, func=func)
                    )
                except Exception as e:
                    error = exc.ParseError(
                        item=i, value=value[i], type=arg, origin_exc=e
                    )
                    if options.invalid_items == options.PRESERVE:
                        context.collect_waring(error.formatted_message)
                        result.append(value[i])
                        continue
                    context.handle_error(error)

        return cls.__origin__(result)

    @classmethod
    def _parse_seq_args(cls, value: Union[list, set], context: RuntimeContext):
        result = []
        arg_type = cls.__args__[0]
        arg_transformer = cls.__arg_transformers__[0]
        options = context.options

        for i, item in enumerate(value):
            with context.enter(route=i) as arg_context:
                try:
                    result.append(
                        arg_context.transformer.apply(
                            item, arg_type, func=arg_transformer
                        )
                    )
                except Exception as e:
                    error = exc.ParseError(
                        item=i, value=value[i], type=arg_type, origin_exc=e
                    )
                    if options.invalid_items == options.EXCLUDE:
                        context.collect_waring(error.formatted_message)
                        continue
                    if options.invalid_items == options.PRESERVE:
                        context.collect_waring(error.formatted_message)
                        result.append(item)
                        continue
                    context.handle_error(error)
        return result

    @classmethod
    def _parse_map_args(cls, value: dict, context: RuntimeContext):
        result = {}
        if not cls.__args__:
            return value

        key_type = cls.__args__[0]
        key_transformer = cls.__arg_transformers__[0]
        value_type = None
        value_transformer = None
        if len(cls.__args__) > 1:
            value_type = cls.__args__[1]
            value_transformer = cls.__arg_transformers__[1]

        options = context.options

        for _key, _val in value.items():
            with context.enter(route=f"{_key}<key>") as key_context:
                try:
                    key = key_context.transformer.apply(
                        _key, key_type, func=key_transformer
                    )
                except Exception as e:
                    error = exc.ParseError(
                        item=f"{_key}<key>", value=_key, type=key_type, origin_exc=e
                    )
                    if options.invalid_keys == options.EXCLUDE:
                        context.collect_waring(error.formatted_message)
                        continue
                    elif options.invalid_keys == options.PRESERVE:
                        key = _key
                        context.collect_waring(error.formatted_message)
                    else:
                        context.handle_error(error)
                        continue

            if value_type:
                with context.enter(route=key) as value_context:
                    try:
                        val = value_context.transformer.apply(
                            _val, value_type, func=value_transformer
                        )
                    except Exception as e:
                        error = exc.ParseError(
                            item=key, value=_val, type=value_type, origin_exc=e
                        )
                        if options.invalid_values == options.EXCLUDE:
                            context.collect_waring(error.formatted_message)
                            continue
                        elif options.invalid_values == options.PRESERVE:
                            context.collect_waring(error.formatted_message)
                            val = _val
                        else:
                            context.handle_error(error)
                            continue
            else:
                val = _val
            result[key] = val
        return result

    @classmethod
    def _parse_type_arg(cls, value, context: RuntimeContext):
        type_cls = cls.__args__[0]
        if issubclass(value, type_cls):
            return value
        context.handle_error(exc.InvalidSubclass(
            type=type_cls, value=value
        ))
        return value


if isinstance(Callable, type):
    @TypeTransformer.registry.register(Callable, allow_subclasses=False)
    def transform_callable(transformer: TypeTransformer, value, t):
        if not callable(value):
            raise TypeError
        return value

if isinstance(Any, type):
    @TypeTransformer.registry.register(Any, allow_subclasses=False)
    def transform_callable(transformer: TypeTransformer, value, t):
        # accept any value
        return value


@TypeTransformer.registry.register(metaclass=LogicalType)
def transform_rule(transformer: TypeTransformer, value, t: LogicalType):
    return t(value, context=transformer.context)
