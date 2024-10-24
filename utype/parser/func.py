import inspect
from collections.abc import (AsyncGenerator, AsyncIterable, AsyncIterator,
                             Callable, Generator, Iterable, Iterator, Mapping)
from functools import wraps
from typing import List, Tuple, Optional

from ..utils import exceptions as exc
from ..utils.compat import is_classvar, is_final
from ..utils.datastructures import cached_property, unprovided
from ..utils.functional import pop
from .base import BaseParser
from .field import ParserField
from .options import Options, RuntimeContext
from .rule import Rule, resolve_forward_type
from ..settings import warning_settings

LAMBDA_NAME = (lambda: None).__name__
LOCALS_NAME = "<locals>"


def _f_pass_doc():
    """"""


def _f_pass():
    pass


PASSED_CODES = (
    _f_pass.__code__.co_code,
    _f_pass_doc.__code__.co_code,
)


class FunctionParser(BaseParser):
    @property
    def bound(self):
        # class A:
        #    class B:
        #        def f():
        # f.__qualname__ = 'A.B.f'
        # f.bound -> 'A.B'
        name = self.obj.__qualname__
        if '.' in name:
            return '.'.join(name.split('.')[:-1])
        return None

    @classmethod
    def function_pass(cls, f):
        if not inspect.isfunction(f):
            return False
        return getattr(f, "__code__").co_code in PASSED_CODES

    @classmethod
    def validate_function(cls, f):
        return (
            isinstance(f, (staticmethod, classmethod))
            or inspect.ismethod(f)
            or inspect.isfunction(f)
        )

    @classmethod
    def apply_class(
        cls,
        target: type,
        options: Options = None,
        no_cache: bool = False,
        ignore_params: bool = False,
        ignore_result: bool = False,
        eager: bool = False,
    ):
        """
        Patch all explicit methods in class (name not beginning with "_")
        """
        for key, val in target.__dict__.items():
            if key.startswith("_"):
                continue
            if not cls.validate_function(val):
                continue
            current_parser = cls.resolve_parser(val)
            if current_parser:
                continue
            parser = cls.apply_for(
                val, no_cache=no_cache, options=options, from_class=target
            )
            func = parser.wrap(
                parse_params=not ignore_params,
                parse_result=not ignore_result,
                eager_parse=eager,
            )
            setattr(target, key, func)
        return target

    @classmethod
    def analyze_func(cls, f):
        first_reserve = None
        if isinstance(f, classmethod):
            first_reserve = True
            f = f.__func__
        elif isinstance(f, staticmethod):
            first_reserve = False
            f = f.__func__
        elif inspect.ismethod(f):
            first_reserve = False
        elif not inspect.isfunction(f):
            raise TypeError(f"Invalid function: {f}")
        return f, first_reserve

    @classmethod
    def get_return_type(cls, f):
        if isinstance(f, (staticmethod, classmethod)):
            f = f.__func__
        if not f:
            return None
        return getattr(f, "__annotations__", {}).get("return")

    @classmethod
    def infer_instancemethod(cls, func):
        return (
            hasattr(func, "__qualname__")
            and func.__qualname__.endswith("." + func.__name__)
            and not func.__qualname__.endswith(f"{LOCALS_NAME}." + func.__name__)
        )

    def __init__(self, func, options: Options = None, from_class: type = None):
        if not self.validate_function(func):
            raise TypeError(
                f"{self.__class__}: invalid function or method: {func}, must be method or function"
            )

        self.from_class = from_class
        self.instancemethod = False
        self.classmethod = isinstance(func, classmethod)
        self.staticmethod = isinstance(func, staticmethod)

        func, self.first_reserve = self.analyze_func(func)

        self.is_method = inspect.ismethod(func)
        self.is_lambda = inspect.isfunction(func) and func.__name__ == LAMBDA_NAME
        self.is_coroutine = inspect.iscoroutinefunction(func)
        self.is_generator = inspect.isgeneratorfunction(func)
        self.is_async_generator = inspect.isasyncgenfunction(func)
        self.is_asynchronous = self.is_coroutine or self.is_async_generator
        self.is_passed = self.function_pass(func)

        parameters = inspect.signature(func).parameters.items()

        if self.from_class:
            # within a class context, the instance method is easy to detect
            # exclude the staticmethod/classmethod is enough
            if (
                not self.first_reserve
                and not self.staticmethod
                and not self.classmethod
            ):
                self.first_reserve = True
                self.instancemethod = True
        else:
            if (
                not self.first_reserve
                and not self.is_method
                and not self.is_lambda
                and not self.staticmethod
            ):
                # guess instance method
                if len(parameters) >= 1:
                    (fk, first_param), *_rest = parameters
                    first_param: inspect.Parameter
                    if (
                        first_param.kind
                        in (
                            first_param.POSITIONAL_ONLY,
                            first_param.POSITIONAL_OR_KEYWORD,
                        )
                        and first_param.default is first_param.empty
                        and first_param.annotation is first_param.empty
                    ):

                        if self.infer_instancemethod(func):
                            self.first_reserve = True
                            self.instancemethod = True

        self.reserve_name = None
        if self.first_reserve:
            _r, *parameters = parameters
            self.reserve_name = _r[0]

        # annotates = {k: v.annotation for k, v in self.parameters if v.annotation is not v.empty}
        # defaults = {k: v.default for k, v in self.parameters if v.default is not v.empty}
        # if a param is not defaulted or annotated, it rule is Rule(require=True)

        self.exclude_indexes = set()
        self.parameters: Iterable[Tuple[str, inspect.Parameter]] = parameters
        self.kw_var = None  # only for function, **kwargs
        self.pos_var_index = None
        self.pos_var = None  # only for function, *args
        self.pos_key_map = {}  # reverse version of arg index
        self.arg_index = {}
        self.max_args = 0
        self.min_args = 0
        self.pos_annotation = None
        self.kw_annotation = None
        self.return_annotation = self.get_return_type(func)

        arg_names = []
        kw_names = []
        pos_only_keys = []
        common_arg_names = []

        for i, (k, v) in enumerate(self.parameters):
            v: inspect.Parameter
            arg_names.append(k)
            if v.kind == v.VAR_POSITIONAL:
                self.pos_var_index = i
                self.pos_var = k
                if v.annotation != v.empty:
                    self.pos_annotation = v.annotation
                continue
            elif v.kind == v.VAR_KEYWORD:
                self.kw_var = k
                if v.annotation != v.empty:
                    self.kw_annotation = v.annotation
                continue
            else:
                common_arg_names.append(k)
                if v.kind == v.POSITIONAL_ONLY:
                    pos_only_keys.append(k)
                    self.min_args += 1
                else:
                    kw_names.append(k)

                if v.kind != v.KEYWORD_ONLY:
                    self.max_args += 1
                    self.pos_key_map[i] = k
                    self.arg_index[k] = i

        self.arg_names = arg_names
        self.kw_names = kw_names
        self.pos_only_keys = pos_only_keys
        self.common_arg_names = common_arg_names

        if self.kw_var:
            opt_list = [options]
            if self.kw_annotation:
                opt_list.append(self.options_cls(addition=self.kw_annotation))
            elif self.kw_var:
                opt_list.append(self.options_cls(addition=True))
            options = self.options_cls.generate_from(*opt_list)

        super().__init__(func, options=options)

        self.init_kwargs = {"options": options, "from_class": from_class}
        if not self.kw_var and self.options.addition:
            raise exc.ConfigError(
                f"FunctionParser: {func}, specify addition: {options.addition} "
                f"without declaring the **kwargs variable"
            )
        if self.kw_var and not self.options.addition:
            warning_settings.warn(
                f"FunctionParser: {func}, specified **{self.kw_var}"
                f" but set addition=False, {self.kw_var} will always be empty",
                warning_settings.function_kwargs_With_no_addition,
            )

        if self.options.no_default:
            raise exc.ConfigError(
                f"FunctionParser: {func}.options cannot specify no_default=True"
            )

        if self.options.defer_default:
            raise exc.ConfigError(
                f"FunctionParser: {func}.options cannot specify defer_default=True"
            )

        if self.options.immutable:
            warning_settings(
                f"FunctionParser: {func}, specified immutable=True in Options, which is useless",
                warning_settings.function_invalid_options
            )
        if self.options.secret_names:
            warning_settings.warn(
                f"FunctionParser: {func}, specified secret_names in Options, which is useless",
                warning_settings.function_invalid_options
            )

        self.position_type = None
        self.return_type = None

        self.generator_send_type = None
        self.generator_yield_type = None
        self.generator_return_type = None
        # Generator[Yield, Send, Return] or Iterator[Yield, Return]
        # self.async_generator_send_type = None
        # self.async_generator_yield_type = None
        # AsyncGenerator[Yield, Send] or AsyncIterator[Yield]

        if self.pos_annotation:
            self.position_type = self.parse_annotation(annotation=self.pos_annotation)

        self.generate_return_types()

    # @property
    # def do_parse_generator(self):
    #     return (self.is_generator or self.is_async_generator) and (
    #         self.generator_send_type
    #         or self.generator_yield_type
    #         or self.generator_return_type
    #     )

    def generate_return_types(self):
        # see if the return type match the function
        # focus on sync / async
        # generator / coroutine / async generator
        if not self.return_annotation:
            return

        self.return_type = self.parse_annotation(
            annotation=self.return_annotation
        )

        # https://docs.python.org/3/library/typing.html#typing.Generator
        if self.return_type and isinstance(self.return_type, type) and issubclass(self.return_type, Rule):
            if self.is_generator:
                if self.return_type.__origin__ in (Iterable, Iterator):
                    self.generator_yield_type = self.return_type.__args__[0]
                elif self.return_type.__origin__ == Generator:
                    (
                        self.generator_yield_type,
                        self.generator_send_type,
                        self.generator_return_type,
                    ) = self.return_type.__args__
                else:
                    warning_settings.warn(
                        f"Invalid return type annotation: {self.return_annotation} "
                        f"for generator function, should be Generator[...] / Iterator[...] / Iterable[...]",
                        warning_settings.function_invalid_return_annotation
                    )
            elif self.is_async_generator:
                if self.return_type.__origin__ in (AsyncIterable, AsyncIterator):
                    self.generator_yield_type = self.return_type.__args__[0]
                elif self.return_type.__origin__ == AsyncGenerator:
                    (
                        self.generator_yield_type,
                        self.generator_send_type,
                    ) = self.return_type.__args__
                else:
                    warning_settings.warn(
                        f"Invalid return type annotation: {self.return_annotation} "
                        f"for async generator function, should be "
                        f"AsyncGenerator[...] / AsyncIterator[...] / AsyncIterable[...]",
                        warning_settings.function_invalid_return_annotation
                    )

    @cached_property
    def positional_fields(self):
        fields = {}
        for index, key in self.pos_key_map.items():
            field = self.get_field(key)
            if not field:
                continue
            fields[index] = field
        return fields

    @cached_property
    def positional_only_fields(self) -> List[Tuple[int, ParserField]]:
        fields = []
        for i, key in enumerate(self.pos_only_keys):
            field = self.get_field(key)
            if not field:
                continue
            fields.append((i, field))
        return fields

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.obj.__qualname__}>"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.obj.__qualname__}>"

    def get_pos_field(self, index: int) -> Optional[ParserField]:
        key = self.pos_key_map.get(index)
        if key:
            return self._get_field_from(self.fields, key)
        return None

    def generate_fields(self):
        exclude_vars = set()
        exclude_indexes = set()
        global_vars = self.globals
        fields = []

        for i, (name, param) in enumerate(self.parameters):
            if not self.validate_field_name(name):
                exclude_vars.add(name)
                if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
                    exclude_indexes.add(i)
                continue
            if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
                continue

            annotation = None
            if param.annotation is not param.empty:
                if param.annotation is None:
                    annotation = type(None)
                    # annotation = None means no annotation (param.empty)
                else:
                    annotation = param.annotation
                    if is_final(annotation) or is_classvar(annotation):
                        warning_settings.warn(
                            f"{self.obj}: param: {repr(name)} invalid annotation: {annotation}, "
                            f"this is only for class variables, please use the type directly",
                            warning_settings.function_invalid_params_annotation
                        )
                        # args = get_args(annotation)
                        # annotation = args[0] if args else None
                        continue

            try:
                field = self.parser_field_cls.generate(
                    attname=name,
                    annotation=annotation,
                    default=param.default
                    if param.default is not param.empty
                    else unprovided,
                    global_vars=global_vars,
                    forward_refs=self.forward_refs,
                    options=self.options,
                    positional_only=param.kind == param.POSITIONAL_ONLY,
                    bound=self.bound,
                    **self.kwargs
                )
            except Exception as e:
                raise exc.ConfigError(f'{self.name}: parse field [{repr(name)}] failed with error: {e}')

            fields.append(
                field
            )

        field_map = {}
        for field in fields:
            name = field.name

            if field.is_case_insensitive(self.options):
                name = name.lower()

            if name in field_map:
                raise exc.ConfigError(
                    f"{self.obj}: field name: {repr(name)} conflicted at "
                    f"{field}, {field_map[name]}",
                    obj=self.obj,
                    field=name,
                )
            if not self.is_passed:
                # is function is :pass, we do not check for now
                field.check_function(self.obj)  # check for function
            field_map[name] = field

        self.fields.update(field_map)
        self.exclude_vars = exclude_vars
        self.exclude_indexes = exclude_indexes

    def validate_fields(self):
        """
        all the non-keyword-only args need to check the
        non-keyword-only: required > has-default > no default (*pos)
        keyword-only: required/has-default > no default (**kwargs)
        """

        super().validate_fields()

        # validate DEFAULT order
        optional_name = None
        for i, (k, v) in enumerate(self.parameters):
            if self.first_reserve and not i:
                continue
            v: inspect.Parameter
            if v.kind == v.VAR_POSITIONAL:
                continue
            elif v.kind == v.VAR_KEYWORD:
                continue

            if v.kind == v.KEYWORD_ONLY:
                # keyword args does not need to check for default order
                continue

            field = self.get_field(k)
            if field:
                required = field.no_default
            else:
                required = v.default != v.empty

            if required:
                if i in self.exclude_indexes:
                    continue
                if optional_name:
                    msg = (
                        f"{self.obj}: non-default argument: {repr(k)} "
                        f"follows default argument: {repr(optional_name)}"
                    )
                    if v.kind == v.POSITIONAL_ONLY:
                        raise SyntaxError(msg)
                    else:
                        warning_settings.warn(msg, warning_settings.function_non_default_follows_default_args)
            else:
                optional_name = k

    def resolve_forward_refs(self, local_vars=None, ignore_errors: bool = True):
        resolved = super().resolve_forward_refs(
            local_vars=local_vars, ignore_errors=ignore_errors
        )
        if resolved:
            if self.position_type:
                self.position_type, r = resolve_forward_type(self.position_type)
            if self.return_type:
                self.return_type, r = resolve_forward_type(self.return_type)

    def wrap(
        self,
        options: Options = None,
        first_reserve: bool = None,
        parse_params: bool = None,
        parse_result: bool = None,
        eager_parse: bool = False,
        ignore_methods: bool = False,
    ):

        if self.is_async_generator:
            f = self.get_async_generator(
                options=options,
                first_reserve=first_reserve,
                parse_params=parse_params,
                parse_result=parse_result,
                eager=eager_parse,
            )
        elif self.is_coroutine:
            f = self.get_async_call(
                options=options,
                first_reserve=first_reserve,
                parse_params=parse_params,
                parse_result=parse_result,
                eager=eager_parse,
            )
        elif self.is_generator:
            f = self.get_sync_generator(
                options=options,
                first_reserve=first_reserve,
                parse_params=parse_params,
                parse_result=parse_result,
                eager=eager_parse,
            )
        else:
            # if eager_parse:
            #     warnings.warn(f'{self.obj} is a sync function')

            @wraps(self.obj)
            def f(*args, **kwargs):  # noqa
                # MAKE CONTEXT AT RUNTIME !
                context = options.make_context() if options else self.make_context()
                return self.sync_call(
                    args,
                    kwargs,
                    context=context,
                    first_reserve=first_reserve,
                    parse_params=parse_params,
                    parse_result=parse_result,
                )

        f.__parser__ = self
        if not ignore_methods:
            if self.classmethod:
                return classmethod(f)
            elif self.staticmethod:
                return staticmethod(f)
        return f

    def parse_pos_type(self, index: int, value, context: RuntimeContext):
        options = context.options
        pos_type = self.position_type
        # we should just ignore the runtime addition type
        if not pos_type:
            return value

        pos_key = f"*{self.pos_var}:{index}" if self.pos_var else index
        with context.enter(pos_key) as new_context:
            try:
                value = new_context.transformer(value, pos_type)
            except Exception as e:
                error = exc.ParseError(
                    item=new_context.route, value=value, type=pos_type, origin_exc=e
                )
                if options.invalid_items == options.PRESERVE:
                    context.collect_waring(error.formatted_message)
                elif options.invalid_items == options.EXCLUDE:
                    context.collect_waring(error.formatted_message)
                    return unprovided
                else:
                    context.handle_error(error)
        return value

    def parse_addition(self, key: str, value, context: RuntimeContext):
        var_key = f"**{self.kw_var}:{key}" if self.kw_var else key
        return super().parse_addition(var_key, value=value, context=context)

    def parse_params(
        self, args: tuple, kwargs: dict, context: RuntimeContext
    ) -> Tuple[tuple, dict]:
        # def f(self, *args, arg1, arg2, **kwargs):
        # self.f(1, 2, 3)
        # def f(self, data):
        # self.f({})
        # not keyword-only argument may show up at pos args
        parsed_args = []
        parsed_keys = []

        # 1. parse giving args, including the positional args
        for i, arg in enumerate(args):
            if self.pos_var and i >= self.pos_var_index:
                # eg. f(a, b, *args): pos_var_index = 2
                arg = self.parse_pos_type(index=i, value=arg, context=context)
                if unprovided(arg):
                    continue
            else:
                field = self.positional_fields.get(i)

                if field:
                    if field.is_no_input(arg, options=context.options):
                        arg = field.get_default(options=context.options)
                    else:
                        parsed_keys.append(field.attname)
                        arg = field.parse_value(arg, context=context)
                    if unprovided(arg):
                        # on_error=excluded, or error collected
                        continue
                else:
                    if i in self.exclude_indexes:
                        # excluded var
                        # def f(a, _b, _c):
                        # we do not parse, just append this arg
                        pass
                    else:
                        # excess var ignore
                        continue

            parsed_args.append(arg)

        # 2. check if unprovided args has default give, and the unprovided required args
        for index, field in self.positional_only_fields:
            if field.attname in parsed_keys:
                continue
            if field.is_required(options=context.options):
                context.handle_error(exc.AbsenceError(item=field.attname))
                continue
            default = field.get_default(context.options)
            if not unprovided(default):
                # this position is definitely after parsed_args
                # because required args is always (we enforce check) ahead of default args
                parsed_args.append(default)
            parsed_keys.append(field.attname)  # need to append parsed as well
            # positional only field is excluded no matter the arg is provided or not

        parsed_kwargs = self.parse_data(
            kwargs, context=context, excluded_keys=parsed_keys, as_attname=True
        )
        context.raise_error()  # raise the parse error before calling the function
        return tuple(parsed_args), parsed_kwargs

    def get_params(
        self,
        args: tuple,
        kwargs: dict,
        context: RuntimeContext,
        first_reserve=None,
        parse_params: bool = None,
    ):
        _ = None
        if first_reserve is None:
            first_reserve = self.first_reserve
        if first_reserve:
            if self.instancemethod or self.classmethod:
                _self = pop(kwargs, "__self__")
                if self.classmethod:
                    if _self:
                        _ = getattr(_self, "__class__", None)
                    else:
                        _ = pop(kwargs, "__class__")
                elif _self:
                    _ = _self
            if args and not _:
                _, *args = args
        if parse_params:
            args, kwargs = self.parse_params(args, kwargs, context=context)
        if first_reserve:
            if self.from_class:
                if self.classmethod:
                    if not isinstance(_, type) or not issubclass(_, self.from_class):
                        raise exc.InvalidSubclass(type=self.from_class, value=_)
                else:
                    if not isinstance(_, self.from_class):
                        raise exc.InvalidInstance(type=self.from_class, value=_)
            args = (_, *args)
        return args, kwargs

    def parse_result(self, result, context: RuntimeContext):
        if self.return_type:
            try:
                result = context.transformer(result, self.return_type)
            except Exception as e:
                error = exc.ParseError(
                    item="<return>", value=result, type=self.return_type, origin_exc=e
                )
                context.handle_error(error, force_raise=True)
        return result

    def sync_from_generator(self, generator: Generator, context: RuntimeContext):
        i = 0
        sent = None
        while True:
            try:
                if sent is not None:
                    item = generator.send(sent)
                else:
                    item = next(generator)
            except StopIteration as err:
                result = err.value
                if result is None or not self.generator_return_type:
                    # raise the same StopIteration
                    return result
                try:
                    result = context.transformer(result, self.generator_return_type)
                except Exception as e:
                    error = exc.ParseError(
                        item=f"<generator.return>",
                        value=result,
                        type=self.generator_return_type,
                        origin_exc=e,
                    )
                    context.handle_error(error, force_raise=True)
                return result
            else:
                if inspect.isgenerator(item):
                    generator = item
                    continue
                    # maybe a tail opt generator

                if self.generator_yield_type:
                    try:
                        item = context.transformer(item, self.generator_yield_type)
                    except Exception as e:
                        error = exc.ParseError(
                            item=f"<generator.yield[{i}]>",
                            value=item,
                            type=self.generator_yield_type,
                            origin_exc=e,
                        )
                        context.handle_error(error, force_raise=True)

                sent = yield item

                if sent is not None:
                    if self.generator_send_type:
                        try:
                            sent = context.transformer(sent, self.generator_send_type)
                        except Exception as e:
                            error = exc.ParseError(
                                item=f"<generator.send[{i}]>",
                                value=sent,
                                type=self.generator_send_type,
                                origin_exc=e,
                            )
                            context.handle_error(error, force_raise=True)
                i += 1

    def get_sync_generator(
        self,
        options: Options = None,
        first_reserve: bool = None,
        parse_params: bool = None,
        parse_result: bool = None,
        eager: bool = False,
    ):
        @wraps(self.obj)
        def eager_generator(*args, **kwargs) -> Generator:
            context = (options or self.options).make_context()
            self.resolve_forward_refs()
            args, kwargs = self.get_params(
                args,
                kwargs,
                context=context,
                first_reserve=first_reserve,
                parse_params=parse_params,
            )
            func = self.obj
            generator: Generator = func(*args, **kwargs)
            if parse_result:
                return self.sync_from_generator(generator, context)
            return generator

        if eager:
            return eager_generator

        @wraps(self.obj)
        def sync_generator(*args, **kwargs):
            gen = eager_generator(*args, **kwargs)
            sent = None
            while True:
                try:
                    if sent is not None:
                        item = gen.send(sent)
                    else:
                        item = next(gen)
                except StopIteration as err:
                    return err.value
                else:
                    sent = yield item

        return sync_generator

    async def async_from_generator(
        self, generator: AsyncGenerator, context: RuntimeContext
    ):
        i = 0
        async for item in generator:
            if inspect.isasyncgen(item):
                generator = item
                continue

            if self.generator_yield_type:
                try:
                    item = context.transformer(item, self.generator_yield_type)
                except Exception as e:
                    error = exc.ParseError(
                        item=f"<asyncgenerator.yield[{i}]>",
                        value=item,
                        type=self.generator_yield_type,
                        origin_exc=e,
                    )
                    context.handle_error(error, force_raise=True)

            sent = yield item

            if sent is not None:
                if self.generator_send_type:
                    try:
                        sent = context.transformer(sent, self.generator_send_type)
                    except Exception as e:
                        error = exc.ParseError(
                            item=f"<asyncgenerator.send[{i}]>",
                            value=sent,
                            type=self.generator_send_type,
                            origin_exc=e,
                        )
                        context.handle_error(error, force_raise=True)
                # await generator.asend(sent)
                try:
                    await generator.asend(sent)
                except StopAsyncIteration:
                    return
            i += 1

    def get_async_generator(
        self,
        options: Options = None,
        first_reserve: bool = None,
        parse_params: bool = None,
        parse_result: bool = None,
        eager: bool = False,
    ):
        @wraps(self.obj)
        def eager_generator(*args, **kwargs) -> AsyncGenerator:
            context = (options or self.options).make_context()
            self.resolve_forward_refs()
            args, kwargs = self.get_params(
                args,
                kwargs,
                context=context,
                first_reserve=first_reserve,
                parse_params=parse_params,
            )
            func = self.obj
            generator: AsyncGenerator = func(*args, **kwargs)
            if parse_result:
                return self.async_from_generator(generator, context)
            return generator

        if eager:
            return eager_generator

        @wraps(self.obj)
        async def async_generator(*args, **kwargs):
            async_gen = eager_generator(*args, **kwargs)
            async for item in async_gen:
                sent = yield item
                if sent is not None:
                    try:
                        await async_gen.asend(sent)
                    except StopAsyncIteration:
                        return

        return async_generator

    def get_async_call(
        self,
        options: Options = None,
        first_reserve: bool = None,
        parse_params: bool = None,
        parse_result: bool = None,
        eager: bool = False,
    ):
        @wraps(self.obj)
        def eager_call(*args, **kwargs):
            context = (options or self.options).make_context()
            self.resolve_forward_refs()
            args, kwargs = self.get_params(
                args,
                kwargs,
                context=context,
                first_reserve=first_reserve,
                parse_params=parse_params,
            )
            if parse_result:
                return self.get_async_result(args, kwargs, context=context)
            return self.obj(*args, **kwargs)

        if eager:
            return eager_call

        @wraps(self.obj)
        async def async_call(*args, **kwargs):
            return await eager_call(*args, **kwargs)

        return async_call

    def sync_call(
        self,
        args: tuple,
        kwargs: dict,
        context: RuntimeContext,
        first_reserve=None,
        parse_params: bool = None,
        parse_result: bool = None,
    ):
        self.resolve_forward_refs()
        args, kwargs = self.get_params(
            args,
            kwargs,
            context=context,
            first_reserve=first_reserve,
            parse_params=parse_params,
        )
        func = self.obj
        result = func(*args, **kwargs)
        if parse_result:
            result = self.parse_result(result, context=context)
        return result

    async def get_async_result(
        self, args: tuple, kwargs: dict, context: RuntimeContext
    ):
        # we may not want to change the result form even if it's another coroutine
        # we leave to user to await it to avoid changing the actual logic of the function
        # while inspect.iscoroutine(result):
        #     result = await result
        return self.parse_result(await self.obj(*args, **kwargs), context=context)


def call(
    func: Callable,
    args=None,
    data=None,
    options=None,
    context: RuntimeContext = None,
    parser_cls=FunctionParser,
    ignore_params: bool = False,
    ignore_result: bool = False,
):

    parser = parser_cls.apply_for(func)  # use the __parser__ if already installed
    options = options or parser.options
    new_context: RuntimeContext = (options or parser.options).make_context(
        context=context
    )
    transformer = new_context.transformer

    args = args or ()
    data = data or {}
    if not isinstance(args, Iterable):
        # {} dict instance is an instance of Mapping too
        if transformer.no_explicit_cast:
            raise TypeError(
                f"invalid input type for funtional args, should be dict or Mapping"
            )
        else:
            args = transformer.to_array_types(args)
    if not isinstance(data, Mapping):
        # {} dict instance is an instance of Mapping too
        if transformer.no_explicit_cast:
            raise TypeError(
                f"invalid input type for functional data, should be dict or Mapping"
            )
        else:
            data = transformer.to_dict(data)

    if new_context.options.cast_keyword_str:
        _data = {}
        for key, val in data.items():
            if not isinstance(key, str):
                key = transformer.to_str(key)
            _data[key] = val
        data = _data

    f = parser.wrap(
        options, parse_params=not ignore_params, parse_result=not ignore_result
    )
    return f(*args, **data)
