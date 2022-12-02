import inspect
import warnings
from typing import Literal, Union, List, Optional, Any, Callable, Type
from ..utils.transform import TypeTransformer
from ..utils.functional import multi
from ..utils import exceptions as exc


class RuntimeOptionsMixin:
    # CAMEL_CASE_GENERATOR = AliasGenerator.camel
    # SNAKE_CASE_GENERATOR = AliasGenerator.snake
    # KEBAB_CASE_GENERATOR = AliasGenerator.kebab
    # CAP_SNAKE_CASE_GENERATOR = AliasGenerator.cap_snake
    # CAP_KEBAB_CASE_GENERATOR = AliasGenerator.cap_kebab
    # PASCAL_CASE_GENERATOR = AliasGenerator.pascal

    EXCLUDE = "exclude"
    PRESERVE = "preserve"
    THROW = "throw"

    transformer_cls = TypeTransformer  # support custom with scope
    collect_errors: bool = False
    max_errors: int = 0
    # if errors reach to this limit, just throw and do not collect further
    # default strategy is fail-fast,
    # but if collect_errors = True. we will collect every error message of the data
    # so we need to continue to parse even if there are error occurs
    # and pack it as the error output,
    # this options is for debug-only

    max_depth: int = None
    max_properties: int = None
    min_properties: int = None
    # max/min properties is validate BEFORE parse, to avoid a too big input data

    addition: Union[bool, None, type] = None
    # <True: preserve
    # <type: preserve as this type
    # None: ignore
    # False: raise ExcessError
    # Exception: raise this error
    # note: another way for this params is to define a **kwargs: type in __init__
    invalid_items: Literal["exclude", "preserve", "throw"] = "throw"
    invalid_keys: Literal["exclude", "preserve", "throw"] = "throw"
    invalid_values: Literal["exclude", "preserve", "throw"] = "throw"

    unresolved_types: Literal["ignore", "init", "throw"] = "throw"
    # 'ignore': just ignore type transform and retain the input value
    # 'init':   use t(data) to init unresolved type, and throw the error if raised
    # 'throw':  throw the error if data is not as type

    ignore_error_property: bool = False
    ignore_no_input: bool = False
    ignore_no_output: bool = False
    # alter type transform
    no_explicit_cast: Optional[bool] = False
    no_data_loss: Optional[bool] = False
    # alter constraints
    ignore_constraints: Union[List[str], bool] = False
    # for Rule, ignore constraints, only transform type
    ignore_alias_conflicts: bool = False
    ignore_dependencies: bool = False

    force_required: bool = False
    ignore_required: bool = False
    force_default: Any = ...
    # force a default value for Field(required=False) with no default
    no_default: bool = False
    # do not take default value (leave it unprovided)
    data_first_search: Optional[bool] = False
    mode: str = None


class RuntimeOptions(RuntimeOptionsMixin):
    override: bool = False
    depth: int

    def __init__(
        self,
        context: "RuntimeOptions" = None,
        cls=None,
        force_error: bool = False,
        error_hooks: dict = None,
        options: dict = None,
    ):

        self.context = context
        self.depth = (context.depth + 1) if context else 0
        self.routes = []
        self.errors = []
        self.tmp_errors = []
        self.warnings = []
        self.cls = cls
        self.cls_routes = []
        self.error_hooks = error_hooks
        self.options = options
        self.force_error = force_error

        if options:
            for key, val in options.items():
                if hasattr(RuntimeOptionsMixin, key):
                    self.__dict__[key] = val

    def __repr__(self):
        return f"{self.__class__.__name__}(cls={self.cls}, options={self.options})"

    def __str__(self):
        return self.__repr__()

    def clone(self):
        return self.__class__(
            context=self,
            cls=self.cls,
            force_error=self.force_error,
            options=self.options,
            error_hooks=self.error_hooks,
        )

    @property
    def transformer(self) -> TypeTransformer:
        return self.transformer_cls(self)

    def get_transformer(
        self,
        no_explicit_cast: bool = None,
        no_data_loss: bool = None,
    ):
        return self.transformer_cls(
            self, no_explicit_cast=no_explicit_cast, no_data_loss=no_data_loss
        )

    @property
    def vacuum(self):
        return not self.options

    def raise_error(self):
        # raise error if there is any
        # if there are tmp errors, raise as well (like when all AnyOf condition is violated)
        if not self.errors and not self.tmp_errors:
            return
        errors = list(self.errors)
        if self.tmp_errors:
            errors.extend(self.tmp_errors)
        raise exc.CollectedParseError(errors=errors)

    def collect_tmp_error(self, e: Exception):
        # the error does not need to raise right now (like a Union condition)
        # we will collect and wait for upper layer to decide when to raise
        # err = Error(e)
        self.tmp_errors.append(e)

    def clear_tmp_error(self):
        self.tmp_errors = []

    def handle_error(
        self,
        e: Exception,
        force_raise: bool = False,
    ):
        # err = Error(e)
        self.errors.append(e)
        if force_raise or not self.collect_errors or len(self.errors) > self.max_errors:
            raise e

    def collect_waring(self, warning, category=None):
        warnings.warn(warning, category=category)
        self.warnings.append(warning)


class Options(RuntimeOptionsMixin):
    # -- PARAMS
    case_insensitive: bool = None
    alias_from_generator: Union[Callable, List[Callable]] = None
    alias_generator: Callable = None
    unprovided_attribute: Any = ...
    immutable: bool = False
    override: bool = False
    allowed_runtime_options: Union[str, None, List[str]] = "*"

    def __init__(
        self,
        *,
        mode: str = None,
        transformer_cls: Type[TypeTransformer] = TypeTransformer,
        override: bool = False,
        immutable: bool = False,
        collect_errors: bool = False,
        max_errors: int = 0,
        max_properties: int = None,
        min_properties: int = None,
        no_explicit_cast: Optional[bool] = False,
        no_data_loss: Optional[bool] = False,
        addition: Union[bool, type, None] = None,
        invalid_items: Literal["exclude", "preserve", "throw"] = "throw",
        invalid_keys: Literal["exclude", "preserve", "throw"] = "throw",
        invalid_values: Literal["exclude", "preserve", "throw"] = "throw",
        unresolved_types: Literal["ignore", "init", "throw"] = "throw",
        # you can define your own unresolved behaviour by inherit
        # TypeTransformer and tweak handle_unresolved()
        ignore_error_property: bool = False,
        force_default: Any = ...,
        no_default: bool = False,
        ignore_required: bool = False,
        force_required: bool = False,
        ignore_no_input: bool = False,
        ignore_no_output: bool = False,
        ignore_constraints: bool = False,  # for Rule, ignore constraints, only transform type
        alias_from_generator: Union[Callable, List[Callable]] = None,
        alias_generator: Callable = None,
        ignore_alias_conflict: bool = None,
        allowed_runtime_options: Union[str, None, List[str]] = "*",
        case_insensitive: bool = None,
        max_depth: int = None,
        unprovided_attribute: Any = ...,
        data_first_search: Optional[bool] = False
        # if this value is a subclass of Exception, then raise that error if attr is unprovided
        # if this value is another callable (like dict, list), return value()
        # otherwise return this value directly when attr is unprovided
    ):

        if no_data_loss:
            if addition is None:
                # ignore the input addition is not a "NO-LOSS" approach
                # warnings.warn(f'')
                addition = False

        if multi(alias_from_generator):
            for g in alias_from_generator:
                if not callable(g):
                    raise TypeError(
                        f"Options.alias_from_generator must be a callable or a list of callable"
                    )

        elif alias_from_generator:
            if not callable(alias_from_generator):
                raise TypeError(
                    f"Options.alias_from_generator must be a callable or a list of callable"
                )

        if force_default is not ...:
            if no_default:
                raise ValueError(
                    "Options force_default and no_default can not both specify"
                )

        options = {}
        for key, val in locals().items():
            if hasattr(self, key):
                if getattr(self, key) == val:
                    continue
                self.__dict__[key] = val
                options[key] = val
        self._options = options

    _option_names = [
        k for k, v in inspect.signature(__init__).parameters.items() if k != "self"
    ]

    def __repr__(self):
        options = [f"{key}={repr(val)}" for key, val in self._options.items()]
        return f"{self.__class__.__name__}(%s)" % ", ".join(options)

    def __str__(self):
        return self.__repr__()

    @classmethod
    def initialize(cls):
        options = {}
        for name in cls._option_names:
            if hasattr(cls, name):
                options[name] = getattr(cls, name)
        return cls(**options)

    @property
    def vacuum(self):
        return not self._options

    def make_runtime(
        self,
        cls=None,
        force_error: bool = False,
        options: Union["RuntimeOptions", "Options"] = None,
    ) -> RuntimeOptions:
        kwargs = dict(self._options)

        # if options is Options, it's the first
        # if options is RuntimeOptions, it's passing down through the context
        context = None
        if isinstance(options, Options):
            spec = options._options
            if self.allowed_runtime_options == "*":
                pass
            elif self.allowed_runtime_options:
                spec = {
                    k: v for k, v in spec.items() if k in self.allowed_runtime_options
                }
            else:
                spec = {}

            if options.override:
                kwargs = spec
            elif not self.override and spec:
                kwargs.update(spec)

        elif isinstance(options, RuntimeOptions):
            context = options
            if context.override:
                kwargs = context.options

        return RuntimeOptions(
            context=context, cls=cls, options=kwargs, force_error=force_error
        )

    def clone(self):
        # give the same interface
        return self.make_runtime()

    @classmethod
    def generate_from(cls, *options) -> "Options":
        if not options:
            return cls()
        res = None
        for opt in options:
            if not opt:
                continue
            if inspect.isclass(opt):  # accept from class
                if issubclass(opt, Options):
                    opt = opt.initialize()
                else:
                    opt = {
                        k: v for k, v in opt.__dict__.items() if k in cls._option_names
                    }
            if isinstance(opt, dict):  # accept from dict
                opt = cls(**opt)
            if not isinstance(opt, Options):
                continue
            if opt.vacuum:
                continue
            if not res or opt.override:
                res = opt
            else:
                res &= opt
        return res or cls()

    def __and__(self, other: "Options") -> "Options":
        if not isinstance(other, Options) or other.vacuum:
            return self
        if self.vacuum:
            return other
        if other.override:
            return other
        if self.override:
            return self
        specs = dict(self._options)
        specs.update(other._options)
        return self.__class__(**specs)

    def __call__(self, fn=None, *args, **kwargs):
        # fn can be a schema or function
        if fn:
            fn.__options__ = self
            return fn
