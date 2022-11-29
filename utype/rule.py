import typing
from typing import Union, Type, Optional, List, Literal, Dict, Any, TypeVar, Tuple, Callable
import inspect
from .utils.compat import get_origin, get_args, ForwardRef, evaluate_forward_ref
from .utils.transform import TypeTransformer, register_transformer
from .utils.functional import pop, multi
from .utils import exceptions as exc
from .options import RuntimeOptions
from enum import EnumMeta, Enum
from functools import partial

import re
import warnings
from collections.abc import Sequence
from collections import deque, Mapping, OrderedDict
from decimal import Decimal

T = typing.TypeVar('T')

NUM_TYPES = (int, float, Decimal)
SEQ_TYPES = (list, tuple, set, frozenset, deque, Sequence)
MAP_TYPES = (dict, Mapping)
OPERATOR_NAMES = {
    '&': 'AllOf',
    '|': 'AnyOf',
    '^': 'OneOf',
    '~': 'Not',
}


def resolve_forward_type(t):
    if isinstance(t, ForwardRef):
        if t.__forward_evaluated__:
            return t.__forward_value__, True
        return t, False
    elif isinstance(t, LogicalType):
        res = t.resolve_forward_refs()
        return t, res
    return t, False


def register_forward_ref(annotation,
                         constraints=None,
                         global_vars=None,
                         forward_refs=None,
                         forward_key=None):

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
            if hasattr(annotation, '__constraints__'):
                annotation = ForwardRef(annotation.__forward_arg__)
            annotation.__constraints__ = constraints
            # class A:
            #   attr1: 'forward' = Field(gt=1)
            #   attr2: 'forward' = Field(gt=2)
            # we use forward_key (attname) over forward_arg
            forward_refs.setdefault(
                f'${forward_key}' if forward_key else annotation.__forward_arg__,
                # use a $ to differ from forward arg
                annotation
            )
            # still not evaluated
            return annotation
        raise TypeError(f'{repr(forward_key)}: Unsupported ForwardRef: {annotation}')
    return annotation


class LogicalType(type):    # noqa
    @property
    def args(cls):
        return cls.__dict__.get('__args__', [])

    @property
    def combinator(cls):
        return cls.__dict__.get('__combinator__', None)

    def resolve_combined_origin(cls) -> Optional['LogicalType']:
        if cls.combinator:
            return cls
        origin = getattr(cls, '__origin__', None)
        if isinstance(origin, LogicalType):
            return origin.resolve_combined_origin()
        return None

    def resolve_forward_refs(cls):
        if not cls.combinator:
            return
        args = []
        resolved = False
        for i, arg in enumerate(cls.args):
            arg, resolved = resolve_forward_type(arg)
            args.append(arg)
        if resolved:
            # only adjust args if resolved
            setattr(cls, '__args__', tuple(args))
        return resolved

    def register_forward_refs(cls, global_vars: Dict[str, Any] = None,
                              forward_refs: Dict[str, ForwardRef] = None,
                              forward_key: str = None):
        if not cls.combinator:
            return
        args = []
        registered = False
        for i, arg in enumerate(cls.args):
            key = f'{forward_key}:{i}' if forward_key else str(i)
            if isinstance(arg, ForwardRef):
                arg = register_forward_ref(
                    annotation=arg,
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=key
                )
                registered = True
            elif isinstance(arg, LogicalType) and arg.combinator:
                if arg.register_forward_refs(
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=key
                ):
                    registered = True
            args.append(arg)
        if registered:
            # only adjust args if registered
            setattr(cls, '__args__', tuple(args))
        return registered

    @classmethod
    def combine(mcs, operator: str, *args):
        __args = []
        for arg in args:
            if arg is None:
                arg = type(None)

            elif isinstance(arg, str):
                arg = ForwardRef(arg)

            elif isinstance(arg, ForwardRef):
                pass

            elif not isinstance(arg, type):
                __origin = get_origin(arg)
                if __origin:
                    # like List[str] Literal["value"]
                    _new_args = get_args(arg)
                else:
                    __origin = Literal
                    _new_args = (arg,)
                arg = Rule.annotate(__origin, *_new_args)

            if arg in __args:
                # avoid duplicate
                continue
            __args.append(arg)

        return mcs(OPERATOR_NAMES.get(operator, operator), (), {   # noqa
            '__args__': __args, '__combinator__': operator})             # noqa

    def combine_by(cls, comb: str, other, reverse: bool = False):
        if cls.combinator == comb:
            left_parts = cls.args
        else:
            left_parts = (cls,)
        if isinstance(other, LogicalType) and comb == other.combinator:
            right_parts = other.args
        else:
            right_parts = other if isinstance(other, tuple) else (other,)
        # print('LR:', left_parts, right_parts)
        args = (*right_parts, *left_parts) if reverse else (*left_parts, *right_parts)
        return cls.combine(comb, *args)

    @classmethod
    def all_of(mcs, *args):
        return mcs.combine('&', *args)

    @classmethod
    def any_of(mcs, *args):
        return mcs.combine('|', *args)

    @classmethod
    def one_of(mcs, *args):
        return mcs.combine('^', *args)

    @classmethod
    def not_of(mcs, value):
        return mcs.combine('~', value)

    def __and__(cls, other):
        return cls.combine_by('&', other)

    def __rand__(cls, other):
        return cls.combine_by('&', other, reverse=True)

    def __or__(cls, other):
        if getattr(other, '__origin__', None) == Union:
            return cls.combine_by('|', other.__args__)
        return cls.combine_by('|', other)

    def __ror__(cls, other):
        if getattr(other, '__origin__', None) == Union:
            return cls.combine_by('|', other.__args__, reverse=True)
        return cls.combine_by('|', other, reverse=True)

    def __xor__(cls, other):
        return cls.combine_by('^', other)

    def __rxor__(cls, other):
        return cls.combine_by('^', other, reverse=True)

    def __invert__(cls):
        if cls.combinator == '~':
            return cls.args[0]
        return cls.combine('~', cls)

    # def __getitem__(cls, item: T) -> typing.Iterable[T]:
    #     return item

    def __repr__(cls):
        def _repr(_arg):
            if isinstance(_arg, LogicalType):
                return repr(_arg)
            return getattr(_arg, '__name__', None) or repr(_arg)

        if not cls.args:
            origin = getattr(cls, '__origin__', None)
            validators = getattr(cls, '__validators__', [])
            constraints = ', '.join(f'{key}={val}' for key, val, c in validators)
            origin_repr = ''
            if origin:
                origin_repr = _repr(origin)
                if constraints:
                    origin_repr += ', '
            return f'{cls.__name__}({origin_repr}{constraints})'

        args_repr = ', '.join([_repr(arg) for arg in cls.args])
        l_par = '(' if cls.combinator else '['
        r_par = ')' if cls.combinator else ']'
        return f'{cls.__name__}{l_par}{args_repr}{r_par}'

    def __str__(cls):
        return repr(cls)

    def apply(cls, *args, **kwargs):
        pass

    def apply_logic(cls, value, __options__: RuntimeOptions = None, **kwargs):
        options = __options__.clone() if __options__ else RuntimeOptions()
        # IMPORTANT:
        # we must do clone here (as the parser do make_runtime)
        # to prompt a new RuntimeOptions, to collect the error in this layer

        if cls.combinator == '&':
            for con in cls.args:
                try:
                    # each value transform will pass on to the next condition
                    # like NormalFloat = AllOf(Float, Not(AbnormalFloat))('3.3')
                    value = options.transformer(value, con)
                except Exception as e:
                    options.handle_error(e)
                    break
            return value

        elif cls.combinator == '|':
            # 1. check EXACT identical type
            for con in cls.args:
                if type(value) == con:
                    return value
            # 2. try to transform in strict mode
            # strict_transformer = options.get_transformer(no_explicit_cast=True, no_data_loss=True)
            for con in cls.args:
                try:
                    value = options.transformer(value, con)
                    options.clear_tmp_error()
                    break
                except Exception as e:
                    options.collect_tmp_error(e)

        elif cls.combinator == '^':
            # 1. check EXACT identical type
            # because args are de-duplicate, so value can only end up one type
            for con in cls.args:
                if type(value) == con:
                    return value

            xor = None
            for con in cls.args:
                try:
                    value = options.transformer(value, con)
                    if xor is None:
                        xor = con
                    else:
                        options.handle_error(exc.OneOfViolatedError(
                            f'More than 1 conditions ({xor}, {con}) is True in XOR conditions'))
                        xor = None
                        break
                except Exception as e:
                    options.collect_tmp_error(e)

            if xor is not None:
                # only one condition is satisfied in XOR
                options.clear_tmp_error()

        elif cls.combinator == '~':
            for con in cls.args:
                try:
                    options.transformer(value, con)
                    options.handle_error(exc.NegateViolatedError(f'Negate condition: {con} is violated'))
                except Exception:   # noqa
                    pass
                    # value = cls._get_error_result(e, value, **kwargs)

        options.raise_error()       # raise error if collected
        return value

    def __call__(cls, *args, **kwargs):
        # print('CALL:', *args, **kwargs)
        if cls.combinator:
            return cls.apply_logic(*args, **kwargs)
        return cls.apply(*args, **kwargs)


class Constraints:
    TYPE_SPEC_CONSTRAINTS = {
        'max_digits': NUM_TYPES,
        'round': NUM_TYPES,
        'multiple_of': NUM_TYPES,
        'unique_items': SEQ_TYPES,
        'contains': SEQ_TYPES,
        'max_contains': SEQ_TYPES,
        'min_contains': SEQ_TYPES,
        'dependencies': MAP_TYPES
    }
    CONSTRAINT_TYPES = {
        'length': (int,),
        'max_length': (int,),
        'min_length': (int,),
        'contains': (type,),
        'min_contains': (int,),
        'max_contains': (int,),
        'round': (int,),
        'max_digits': (int,),
        'multiple_of': (int, float),
        'unique_items': (bool,)
    }
    # default type is resolved to "string"

    def __init__(self, rule_cls: Type['Rule'], options: RuntimeOptions = None):
        self.rule_cls = rule_cls
        self.options = options

    @property
    def origin_type(self):
        return self.rule_cls.__origin__

    @origin_type.setter
    def origin_type(self, t: type):
        if isinstance(t, type):
            self.rule_cls.__origin__ = t

    def valid_length(self, bounds: dict):
        length = bounds.get('length')
        max_length = bounds.get('max_length')
        min_length = bounds.get('min_length')
        if length is not None:
            if not (isinstance(length, int) and length >= 0):
                raise ValueError(f'Rule length: {length} must be a int >= 0')
            if min_length is not None:
                if min_length > length:
                    raise ValueError(f'Rule length: {length} and min_length: {min_length} both specified')
                else:
                    pop(bounds, 'min_length')
                    min_length = None
            if max_length is not None:
                if max_length < length:
                    raise ValueError(f'Rule length: {length} and max_length: {max_length} both specified')
                else:
                    pop(bounds, 'max_length')
                    max_length = None
        else:
            if min_length is not None:
                if not (isinstance(min_length, int) and min_length >= 0):
                    raise ValueError(f'Rule min_length: {min_length} must be a int >= 0')

                if not min_length:
                    pop(bounds, 'min_length')
                    min_length = None

            if max_length is not None:
                if not (isinstance(max_length, int) and max_length > 0):
                    raise ValueError(f'Rule max_length: {max_length} must be a int > 0')
                if min_length is not None:
                    if max_length < min_length:
                        raise ValueError(f'Rule max_length: {max_length} must >= min_length: {min_length}')

        if {length, min_length, max_length} != {None}:
            # has length constraints, validate type
            if self.origin_type:
                if not hasattr(self.origin_type, '__len__'):
                    # just warning here, we will coerce to str in runtime
                    if issubclass(self.origin_type, (int, float, Decimal)):
                        warnings.warn(f'Rule specify length constraints for type: {self.origin_type} '
                                      f'that does not support length, we recommend to use '
                                      f'"max_digits" and "round" for number types')
                    else:
                        warnings.warn(f'Rule specify length constraints for type: {self.origin_type} '
                                      f'that does not support length, value will be convert to str to validate length')

    def valid_bounds(self, bounds: dict):
        _max = _min = None
        _max_t = _min_t = None

        gt = bounds.get('gt')
        ge = bounds.get('ge')
        lt = bounds.get('lt')
        le = bounds.get('le')

        if gt is not None:
            if not callable(gt):
                _min_t = type(gt)
                _min = gt

        if ge is not None:
            if _min is not None:
                raise ValueError("Rule gt/ge cannot assign together")

            if not callable(ge):
                _min_t = type(ge)
                _min = ge

        if lt is not None:
            if not callable(lt):
                _max_t = type(lt)
                _max = lt

        if le is not None:
            if _max is not None:
                raise ValueError("Rule lt/le cannot assign together")

            if not callable(le):
                _max_t = type(le)
                _max = le

        if _min_t and _max_t:
            if _min_t != _max_t:
                raise ValueError(f"Rule gt/ge type {_min_t} must equal to lt/le type {_max_t}")

        _t = _max_t or _min_t
        if _t:
            if self.origin_type:
                if not issubclass(self.origin_type, _t) and \
                        not issubclass(_t, self.origin_type):
                    if {self.origin_type, _t} == {int, float}:
                        pass
                    else:
                        raise TypeError(f"Rule range type {_t} must equal to value type {self.origin_type}")
            else:
                self.origin_type = _t

            if _min is not None and _max is not None:
                if _min >= _max:
                    raise ValueError(f"Rule lt/le ({repr(_max)}) must > gt/ge ({repr(_min)})")
                if isinstance(_max, int) and isinstance(_min, int):
                    if gt and lt:
                        if _max - _min < 2:
                            raise ValueError(f"Rule int lt: {_max} - gt: {_min} must greater or equal than 2")

    def valid_types(self, bounds: dict):
        for key, val in bounds.items():
            value_types = self.CONSTRAINT_TYPES.get(key)
            origin_types = self.TYPE_SPEC_CONSTRAINTS.get(key)
            if value_types and not isinstance(val, value_types):
                raise TypeError(f'Constraint: {repr(key)} should be {value_types} object, got {val}')
            if origin_types:
                if self.origin_type:
                    if not issubclass(self.origin_type, origin_types):
                        raise TypeError(f'Constraint: {repr(key)} is only for type: '
                                        f'{origin_types}, got {self.origin_type}')
                else:
                    # set the type if missing
                    self.origin_type = origin_types[0]

    def validate_constraints(self, constraints: dict):
        if 'const' in constraints:
            const = constraints['const']
            if self.origin_type:
                if not isinstance(const, self.origin_type):
                    raise TypeError(f'Rule const: {repr(const)} not instance of type: {self.origin_type}')
            # else:
            #     # transform type before check const
            #     self.origin_type = type(const)
            # we do not force a type to const, it is up to developer to decide
            # whether to transform before const check
            return {'const': const}      # ignore other constraints
        elif 'enum' in constraints:
            enum = constraints['enum']
            if isinstance(enum, EnumMeta):
                member_type = getattr(enum, '_member_type_', None)
                if member_type is object:
                    member_type = None
                if member_type:
                    if self.origin_type:
                        if not issubclass(member_type, self.origin_type):
                            raise TypeError(f'Rule enum member type: {member_type} is '
                                            f'conflict with origin type: {self.origin_type}')
                    else:
                        self.origin_type = member_type
            elif multi(enum):
                enum = list(enum)
            else:
                raise TypeError(f'Invalid enum: {enum}, must be a Enum subclass of list/tuple/set')
            return {'enum': enum}   # ignore other constraints

        constraints = {k: v for k, v in constraints.items() if v is not None}
        if 'unique_items' in constraints and not constraints['unique_items']:
            # only True is valid
            pop(constraints, 'unique_items')
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
        constraints = OrderedDict()
        for key in self.rule_cls.__constraints__:
            if hasattr(self.rule_cls, key) and hasattr(self.__class__, key):
                value = getattr(self.rule_cls, key)
                if value is ...:
                    # this is a sign that the subclass cancel a constraint from the base class
                    # and to differ with None (for const constraint, None is still consider a valid param)
                    continue
                constraints[key] = value

        if not constraints:
            return []

        constraints = self.validate_constraints(constraints)
        validators = []
        for key, val in constraints.items():
            validators.append((key, getattr(self.rule_cls, key), getattr(self.__class__, key)))
        return validators

    @property
    def strict(self):
        """
        strict means we check the constraints AS-IS, without making any change to the original value
        but if strict=False, means we can "tweak" the value to satisfy the constraints
        (which is not recommend approach to validate request input data)
        """
        return self.rule_cls.strict

    def round(self, value, r):
        if not isinstance(value, float):
            if not self.strict:
                value = float(value)
        return round(value, r)

    def multiple_of(self, value, of: int):
        mod = value % of
        if mod:
            if self.strict:
                raise ValueError
            # convert to the closest number
            return (value // of) * of
        return value

    def max_digits(self, value, max_digits: int):
        digits = abs(round(value))         # use abs to ignore the "-" operator
        if len(str(digits)) > max_digits:
            if self.strict:
                raise ValueError
            # convert to the closest number
            sign = 1 if value > 0 else -1
            return (int(str(digits)[-max_digits:]) + (value - digits)) * sign
        return value

    def const(self, value, v):
        if callable(value):
            value = value()
        if value != v:
            raise ValueError
        if self.strict:
            # 0 False
            # 1 True
            if type(value) != type(v):
                raise ValueError
        return v

    def excludes(self, value, lst):
        if multi(value):
            ex = set(value).intersection(lst)
            if ex:
                if self.strict:
                    raise ValueError
                else:
                    value = _type(value)([v for v in value if v not in ex])     # noqa
        else:
            if value in lst:
                raise ValueError
        return value

    def enum(self, value, lst):
        if isinstance(lst, EnumMeta):
            # return the value instead of the enum type
            return lst(value).value

        if isinstance(value, Enum):
            value = value.value

        if value not in lst:
            if self.strict:
                raise ValueError
            return lst[0]
        return value

    def regex(self, value, r):
        if not re.fullmatch(r, str(value)):
            raise ValueError
        return value

    def gt(self, value, gt):
        if callable(gt):
            gt = gt()
        if value <= gt:
            raise ValueError
        return value

    def ge(self, value, ge):
        if callable(ge):
            ge = ge()
        if value < ge:
            if self.strict:
                raise ValueError
            return ge
        return value

    def lt(self, value, lt):
        if callable(lt):
            lt = lt()
        if value >= lt:
            raise ValueError
        return value

    def le(self, value, le):
        if callable(le):
            le = le()
        if value > le:
            if self.strict:
                raise ValueError
            return le
        return value

    def length(self, value, lg):
        v = value
        converted = False
        if not hasattr(value, '__len__'):
            converted = True
            v = str(value)
        if len(v) != lg:
            if self.strict or converted or len(v) < lg:
                raise ValueError
            return value[:lg]
        return value

    def max_length(self, value, m):
        v = value
        converted = False
        if not hasattr(value, '__len__'):
            converted = True
            v = str(value)
        if len(v) > m:
            if self.strict or converted:
                raise ValueError
            return value[:m]
        return value

    def min_length(self, value, m):
        v = value
        if not hasattr(value, '__len__'):
            v = str(value)
        if len(v) < m:
            raise ValueError
        return value

    def contains(self, value, t):
        # validate max_contains and min_contains as well
        contains = 0
        options = self.options or RuntimeOptions()
        transformer = options.get_transformer(
            no_explicit_cast=True,
            no_data_loss=True
        )   # use strict transformer to detect contains
        for item in value:
            try:
                transformer(item, t)
            except (TypeError, ValueError):
                pass
            else:
                contains += 1
        if not contains:
            raise ValueError(f'{t} not contained in value')
        if self.rule_min_contains and contains < self.rule_min_contains:
            raise exc.ConstraintError(
                f'value contains {contains} of {t}, which is lower than min_contains',
                constraint='min_contains',
                constraint_value=self.rule_min_contains
            )
        if self.rule_max_contains and contains > self.rule_max_contains:
            raise exc.ConstraintError(
                f'value contains {contains} of {t}, which is bigger than max_contains',
                constraint='max_contains',
                constraint_value=self.rule_max_contains
            )
        return value

    def unique_items(self, value: list, u):
        if not u:
            return value
        lst = []
        for val in value:
            if val in lst:
                if self.strict:
                    raise ValueError(f'value is not unique')
                continue
            lst.append(val)
        if not self.strict:
            # if not strict, just return a unique version of the input
            return type(value)(lst)     # noqa
        return value

    @property
    def rule_max_contains(self):
        return getattr(self.rule_cls, 'max_contains', 0)

    @property
    def rule_min_contains(self):
        return getattr(self.rule_cls, 'min_contains', 0)


class Rule(metaclass=LogicalType):
    transformer_cls = TypeTransformer
    constraints_cls = Constraints
    options_cls = RuntimeOptions

    __origin__: type = None
    __abstract__: bool = False
    __args__: Tuple[type, ...] = None
    __ellipsis_args__: bool = False
    __arg_transformers__: Tuple[Callable, ...] = None
    __origin_transformer__: Callable = None
    __args_parser__: Callable = None

    __validators__: List[Tuple[str, Any, Callable]]
    __constraints__: List[str] = [
        # define the constraints and it's order
        'gt',
        'ge',
        'lt',
        'le',
        'const',
        'enum',
        'regex',
        'length',
        'max_length',
        'min_length',
        'round',
        'multiple_of',
        'max_digits',
        'contains',
        'max_contains',
        'min_contains',
        'unique_items'
    ]
    __transformer__: Callable

    # flag for document
    primitive: Literal["null", "boolean", "object", "array", "integer", "number", "string"]
    format: Optional[str]
    extra: dict     # additional data to the generated schema document

    # constraints
    gt: Any     # exclusiveMinimum
    ge: Any     # minimum
    lt: Any     # exclusiveMaximum
    le: Any     # maximum
    const: Any
    enum: Union[Enum, list, tuple, set]
    regex: str
    length: int
    max_length: int
    min_length: int

    # number constraints
    round: int
    multiple_of: int
    max_digits: int

    # array constraints
    contains: type
    max_contains: int
    min_contains: int
    unique_items: bool

    # dependencies: Dict[str, Union[List[str], Dict[str, List[str]]]]     # for dict type only
    # this property can be defined in schema.__options__
    # https://json-schema.org/understanding-json-schema/reference/object.html
    # https://json-schema.org/understanding-json-schema/reference/array.html

    # allow_excess: bool = False -> "additionalProperties": false
    # excess_preserve: bool = True -> "additionalProperties": {}
    # **kwargs: str -> "additionalProperties": {"type": "string"}

    # json dict can only support str key, we can only extend it to finite primitive types
    # Dict[str, int] patternProperties: {".*": {"type": integer}}
    # Dict[int, int] patternProperties: {"[0-9]": {"type": integer}}, propertyNames: {"type": "integer"}
    # Dict[bool, int] patternProperties: {"true|false": {"type": integer}}, propertyNames: {"type": "boolean"}

    strict: bool = True

    def __init_subclass__(cls, **kwargs):
        # if not cls.__origin__:
        origin = None
        class_getitem = None
        for base in cls.__bases__:
            if issubclass(base, Rule):
                if not class_getitem:
                    class_getitem = getattr(base, '__class_getitem__', None)
                continue
            if origin:
                raise TypeError(f'{cls}: Multiple origin types: {origin}, {base}')
            origin = base

        if origin:
            if not cls.__origin__:
                cls.__origin__ = origin
            elif issubclass(origin, cls.__origin__):
                cls.__origin__ = origin
            else:
                raise TypeError(f'{cls}: Invalid origin: {origin} of sub type:'
                                f' not subclass of base type: {cls.__origin__}')

        if cls.__origin__:
            if isinstance(cls.__origin__, ForwardRef):
                if not cls.__origin__.__forward_evaluated__:
                    raise TypeError(f'{cls}: cannot setup with unevaluated ForwardRef as origin')
                cls.__origin__ = cls.__origin__.__forward_value__

            if not isinstance(cls.__origin__, type):
                raise TypeError(f'Invalid origin: {cls.__origin__}, must be a class')
            cls.__abstract__ = bool(getattr(cls.__origin__, '__abstractmethods__', None))
            cls.__origin_transformer__ = cls.transformer_cls.resolver_transformer(cls.__origin__)
            if not cls.__origin_transformer__:
                warnings.warn(f'{cls}: origin type: {cls.__origin__} got no transformer resolved, '
                              f'will just pass {cls.__origin__}(data) at runtime')

        if cls.__args__:
            if hasattr(cls, '__class_getitem__'):
                def _cannot_getitem(*_args):
                    raise TypeError(f'{cls.__name__}: argument is already set, '
                                    f'cannot perform getitem ({_args})')
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
                if not isinstance(arg, type):
                    raise TypeError(f'Invalid arg: {arg}, must be a class')
                transformer = cls.transformer_cls.resolver_transformer(arg)
                if not transformer:
                    warnings.warn(f'{cls}: arg type: {arg} got no transformer resolved, '
                                  f'will just pass {arg}(data) at runtime')

                arg_transformers.append(transformer)
            cls.__arg_transformers__ = tuple(arg_transformers)
            cls.__args_parser__ = cls.resolve_args_parser()
            if not cls.__args_parser__:
                warnings.warn(f'{cls}: type: {cls.__origin__} with __args__ cannot resolve an args parser, '
                              f'you should inherit resolve_args_parser and specify yourself')
        else:
            if class_getitem and not hasattr(cls, '.__class_getitem__'):
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

    @classmethod
    def annotate(cls, type_=None, *args_,
                 constraints: Dict[str, Any] = None,
                 global_vars: Dict[str, Any] = None,
                 forward_refs: Dict[str, ForwardRef] = None
                 ):
        args = []
        ellipsis_args = False

        if type_ == Literal:
            # special for literal type
            constraints = constraints or {}
            if len(args_) == 1:
                constraints['const'] = args_[0]
            elif len(args_) > 1:
                constraints['enum'] = args_
            else:
                raise ValueError(f'empty literal')
            type_ = cls.__origin__ or type(args_[0])
        else:
            for arg in args_:
                if isinstance(arg, TypeVar):
                    continue
                if arg is ...:
                    if not issubclass(type_, tuple):
                        raise ValueError(f'{cls} args: {args_} with ... only apply to tuple, got {type_}')
                    ellipsis_args = True
                    continue
                annotation = cls.parse_annotation(arg, global_vars=global_vars, forward_refs=forward_refs)
                # this annotation can be a ForwardRef
                # not with constraints, cause that is applied to upper layer
                if annotation is None:
                    continue
                args.append(annotation)

        if not args and not constraints:
            return type_

        name = cls.__name__
        if type_ == Union:
            type_ = LogicalType.any_of(*args)

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
    def parse_annotation(cls,
                         annotation,
                         constraints=None,
                         global_vars=None,
                         forward_refs=None,
                         forward_key=None,
                         ):
        if isinstance(annotation, str):
            if not annotation:
                raise TypeError(f'{repr(forward_key)}: Empty forward ref string: {annotation}')
            # ForwardRef
            annotation = ForwardRef(annotation)

        if isinstance(annotation, ForwardRef):
            annotation = register_forward_ref(
                annotation=annotation,
                constraints=constraints,
                global_vars=global_vars,
                forward_refs=forward_refs,
                forward_key=forward_key
            )

        if inspect.isclass(annotation):
            # no constraints, we can directly use it
            if isinstance(annotation, LogicalType) and annotation.combinator:
                annotation.register_forward_refs(
                    # we don't need to pass constraints here
                    # as those will be combined in below logics
                    global_vars=global_vars,
                    forward_refs=forward_refs,
                    forward_key=forward_key
                )

            if constraints:
                return cls.annotate(
                    annotation,
                    constraints=constraints,
                    forward_refs=forward_refs,
                    global_vars=global_vars
                )
            else:
                # no constraints, we can directly use it
                return annotation
        elif annotation:
            origin = get_origin(annotation)
            if origin:
                args = get_args(annotation) or ()
                constraints = constraints or {}
                return cls.annotate(
                    origin, *args,
                    constraints=constraints,
                    forward_refs=forward_refs,
                    global_vars=global_vars
                )
            else:
                raise TypeError(f'{repr(forward_key)}: invalid annotation: {annotation}')
        elif constraints:
            return cls.annotate(
                constraints=constraints,
                forward_refs=forward_refs,
                global_vars=global_vars
            )
        return None

    @classmethod
    def check_type(cls, t):
        return True

    @classmethod
    def apply(cls, value, __options__: RuntimeOptions = None):
        # print('APPLY:', value, __options__)
        # use __options__ instead of options is to identify much clearer with other subclass init kwargs
        options = __options__.clone() if __options__ else cls.options_cls()
        # IMPORTANT:
        # we must do clone here (as the parser do make_runtime)
        # to prompt a new RuntimeOptions, to collect the error in this layer
        trans = cls.transformer_cls(options)

        if cls.__origin__:
            # no matter cls.__transformer__ is None or not
            try:
                value = trans.apply(value, cls.__origin__, func=cls.__origin_transformer__)
                # print('VALUE:', repr(value), cls.__origin__)
            except Exception as e:
                error = exc.ParseError(origin_exc=e)
                # if type cannot convert, the following args and constraints cannot validate
                # can just abort and stop collect errors if it is specified
                options.handle_error(error, force_raise=True)

        if cls.__args_parser__:
            value = cls.__args_parser__(value, trans)

            if not cls.__abstract__ and type(value) != cls.__origin__:
                # for abstract types (like Sequence / Iterable)
                # we just give an instance that satisfy those abstract methods (like a list instance)
                value = cls.__origin__(value)

        if not options.ignore_constraints:
            # if options ignore constraints, we will just do type transform
            constraints_inst = cls.constraints_cls(cls, options=options)
            for key, constraint, validator in cls.__validators__:
                # constraint = getattr(cls, key)
                try:
                    value = validator(constraints_inst, value, constraint)
                except Exception as e:
                    error = e if isinstance(e, exc.ConstraintError) else exc.ConstraintError(
                        origin_exc=e,
                        constraint=key,
                        constraint_value=constraint
                    )
                    # if validator already throw a constraint error
                    # may an inner constraint (like max_contains in contains) is violated
                    options.handle_error(error)

        options.raise_error()
        # raise error if collected
        # and leave the error the upper layer to collect
        return value

    def __init__(self, value):
        # print('INIT:', value)
        self._value = self.apply(value)

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self._value)})'

    def __str__(self):
        return f'{self.__class__.__name__}({repr(self._value)})'

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
                        warnings.warn(f'{cls}: arg type: {arg} got no transformer resolved, '
                                      f'will just pass {arg}(data) at runtime')
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
            return cls._apply_map_args
        elif issubclass(cls.__origin__, SEQ_TYPES):
            if issubclass(cls.__origin__, tuple) and not cls.__ellipsis_args__:
                return cls._apply_tuple_args
            return cls._apply_seq_args
        return None

    @classmethod
    def _apply_tuple_args(cls, value: tuple, trans: TypeTransformer):
        result = []
        options = trans.options

        if options.no_data_loss and len(value) > len(cls.__args__):
            raise exc.ItemsExceedError(excess_items=list(range(len(cls.__args__), len(value))))

        for i, (arg, func) in enumerate(zip(cls.__args__, cls.__arg_transformers__)):
            if i >= len(value):
                raise exc.AbsenceError(f"prefixItems required prefix: [{i}] not provided", absence_item=i)
            try:
                result.append(trans.apply(value[i], arg, func=func))
            except Exception as e:
                error = exc.ParseError(
                    item=i,
                    value=value[i],
                    type=arg,
                    origin_exc=e
                )
                if options.invalid_items == options.PRESERVE:
                    options.collect_waring(error.formatted_message)
                    result.append(value[i])
                    continue
                options.handle_error(error)
        return cls.__origin__(result)

    @classmethod
    def _apply_seq_args(cls, value: Union[list, set], trans: TypeTransformer):
        result = []
        arg_type = cls.__args__[0]
        arg_transformer = cls.__arg_transformers__[0]
        options = trans.options

        for i, item in enumerate(value):
            try:
                # print('TRANS:', item, arg_type)
                result.append(trans.apply(item, arg_type, func=arg_transformer))
            except Exception as e:
                error = exc.ParseError(
                    item=i,
                    value=value[i],
                    type=arg_type,
                    origin_exc=e
                )
                if options.invalid_items == options.EXCLUDE:
                    options.collect_waring(error.formatted_message)
                    continue
                if options.invalid_items == options.PRESERVE:
                    options.collect_waring(error.formatted_message)
                    result.append(item)
                    continue
                options.handle_error(error)
        return result

    @classmethod
    def _apply_map_args(cls, value: dict, trans: TypeTransformer):
        result = {}
        key_type, value_type = cls.__args__
        key_transformer, value_transformer = cls.__arg_transformers__
        options = trans.options
        for _key, _val in value.items():
            try:
                key = trans.apply(_key, key_type, func=key_transformer)
            except Exception as e:
                error = exc.ParseError(
                    item=f'{_key}<key>',
                    value=_key,
                    type=key_type,
                    origin_exc=e
                )

                if options.invalid_keys == options.EXCLUDE:
                    options.collect_waring(error.formatted_message)
                    continue
                elif options.invalid_keys == options.PRESERVE:
                    key = _key
                    options.collect_waring(error.formatted_message)
                else:
                    options.handle_error(error)
                    continue

            try:
                value = trans.apply(_val, value_type, func=value_transformer)
            except Exception as e:
                error = exc.ParseError(
                    item=_key,
                    value=_val,
                    type=value_type,
                    origin_exc=e
                )
                if options.invalid_values == options.EXCLUDE:
                    options.collect_waring(error.formatted_message)
                    continue
                elif options.invalid_values == options.PRESERVE:
                    options.collect_waring(error.formatted_message)
                    value = _val
                else:
                    options.handle_error(error)
                    continue
            result[key] = value
        return result


@register_transformer(metaclass=LogicalType)
def transform_rule(transformer: TypeTransformer, value, t: LogicalType):
    return t(value, __options__=transformer.options)
