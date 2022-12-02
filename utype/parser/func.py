from typing import Tuple, List
from .options import Options, RuntimeOptions
from ..utils.functional import pop
from ..utils import exceptions as exc
from .rule import resolve_forward_type, Rule
from .field import SchemaField
import inspect
from .base import BaseParser
from functools import wraps, cached_property
from collections.abc import Generator, AsyncGenerator, Iterator, AsyncIterator, Iterable, AsyncIterable
import warnings


LAMBDA_NAME = (lambda: None).__name__
LOCALS_NAME = '<locals>'


class FunctionParser(BaseParser):
    @classmethod
    def validate_function(cls, f):
        return isinstance(f, (staticmethod, classmethod)) or inspect.ismethod(f) or inspect.isfunction(f)

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
            raise TypeError(f'Invalid function: {f}')
        return f, first_reserve

    @classmethod
    def get_return_type(cls, f):
        if isinstance(f, (staticmethod, classmethod)):
            f = f.__func__
        if not f:
            return None
        return getattr(f, '__annotations__', {}).get('return')

    @classmethod
    def infer_instancemethod(cls, func):
        return hasattr(func, '__qualname__') and func.__qualname__.endswith('.' + func.__name__) and \
               not func.__qualname__.endswith(f'{LOCALS_NAME}.' + func.__name__)

    def __init__(self, func, options: Options = None):
        if not self.validate_function(func):
            raise TypeError(f'{self.__class__}: invalid function or method: {func}, must be method or function')

        self.instancemethod = False
        self.classmethod = isinstance(func, classmethod)
        self.staticmethod = isinstance(func, staticmethod)

        self.is_method = inspect.ismethod(func)
        self.is_lambda = inspect.isfunction(func) and func.__name__ == LAMBDA_NAME
        self.is_coroutine = inspect.iscoroutinefunction(func)
        self.is_generator = inspect.isgeneratorfunction(func)
        self.is_async_generator = inspect.isasyncgenfunction(func)
        self.is_asynchronous = self.is_coroutine or self.is_async_generator

        func, self.first_reserve = self.analyze_func(func)
        parameters = inspect.signature(func).parameters.items()

        if not self.first_reserve and not self.is_method and not self.is_lambda:
            # guess instance method
            if self.infer_instancemethod(func) and len(parameters) >= 1:
                self.first_reserve = True
                self.instancemethod = True

        self.reserve_name = None
        if self.first_reserve:
            _r, *parameters = parameters
            self.reserve_name = _r[0]

        # annotates = {k: v.annotation for k, v in self.parameters if v.annotation is not v.empty}
        # defaults = {k: v.default for k, v in self.parameters if v.default is not v.empty}
        # if a param is not defaulted or annotated, it rule is Rule(require=True)

        self.parameters: Iterable[Tuple[str, inspect.Parameter]] = parameters
        self.kw_var = None  # only for function, **kwargs
        self.pos_var_index = None
        self.pos_var = None  # only for function, *args
        self.pos_key_map = {}   # reverse version of arg index
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

        opt_list = [options]
        if self.kw_annotation:
            opt_list.append(self.options_cls(addition=self.kw_annotation))
        elif self.kw_var:
            opt_list.append(self.options_cls(addition=True))

        super().__init__(func, options=self.options_cls.generate_from(*opt_list))

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

    @property
    def do_parse_generator(self):
        return (self.is_generator or self.is_async_generator) and \
               (self.generator_send_type or self.generator_yield_type or self.generator_return_type)

    def generate_return_types(self):
        # see if the return type match the function
        # focus on sync / async
        # generator / coroutine / async generator
        if not self.return_annotation:
            return

        self.return_type = self.parse_annotation(annotation=self.return_annotation)

        # https://docs.python.org/3/library/typing.html#typing.Generator
        if self.return_type and issubclass(self.return_type, Rule):
            if self.is_generator:
                if self.return_type.__origin__ in (Iterable, Iterator):
                    self.generator_yield_type = self.return_type.__args__[0]
                elif self.return_type.__origin__ == Generator:
                    self.generator_yield_type, self.generator_send_type, self.generator_return_type = \
                        self.return_type.__args__
                else:
                    warnings.warn(f'Invalid return type annotation: {self.return_annotation} '
                                  f'for generator function, should be Generator[...] / Iterator[...] / Iterable[...]')
            elif self.is_async_generator:
                if self.return_type.__origin__ in (AsyncIterable, AsyncIterator):
                    self.generator_yield_type = self.return_type.__args__[0]
                elif self.return_type.__origin__ == AsyncGenerator:
                    self.generator_yield_type, self.generator_send_type = self.return_type.__args__
                else:
                    warnings.warn(f'Invalid return type annotation: {self.return_annotation} '
                                  f'for async generator function, should be '
                                  f'AsyncGenerator[...] / AsyncIterator[...] / AsyncIterable[...]')

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
    def positional_only_fields(self) -> List[Tuple[int, SchemaField]]:
        fields = []
        for i, key in enumerate(self.pos_only_keys):
            field = self.get_field(key)
            if not field:
                continue
            fields.append((i, field))
        return fields

    def __str__(self):
        return f'<{self.__class__.__name__}: {self.obj.__qualname__}>'

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.obj.__qualname__}>'

    def generate_fields(self):
        exclude_vars = self.exclude_vars
        fields = []

        for name, param in self.parameters:
            if not self.validate_field_name(name):
                exclude_vars.add(name)
                continue
            if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL):
                continue
            fields.append(self.schema_field_cls.generate(
                attname=name,
                annotation=param.annotation if param.annotation is not param.empty else None,
                default=param.default if param.default is not param.empty else ...,
                global_vars=self.globals,
                forward_refs=self.forward_refs,
                options=self.options
            ))

        field_map = {}
        for field in fields:
            if field.name in field_map:
                raise ValueError(f'{self.obj}: field name: {repr(field.name)} conflicted at '
                                 f'{field}, {field_map[field.name]}')
            if not field.always_provided:
                raise ValueError(f'{self.obj}: field(name={repr(field.name)}) is not required, '
                                 f'you should set a default')
            field_map[field.name] = field
        self.fields.update(field_map)

    def validate_fields(self):
        """
        all the non-keyword-only args need to check the
        non-keyword-only: required > has-default > no default (*pos)
        keyword-only: required/has-default > no default (*kwargs)
        """

        super().validate_fields()

    def resolve_forward_refs(self, local_vars=None, ignore_errors: bool = True):
        resolved = super().resolve_forward_refs(
            local_vars=local_vars,
            ignore_errors=ignore_errors
        )
        if resolved:
            self.position_type, r = resolve_forward_type(self.position_type)
            self.return_type, r = resolve_forward_type(self.return_type)

    def wrap(self, options: Options = None,
             first_reserve: bool = None,
             parse_params: bool = None,
             parse_result: bool = None):

        options = self.options.make_runtime(options=options)
        if self.is_async_generator:
            f = self.get_async_generator(
                options=options,
                first_reserve=first_reserve,
                parse_params=parse_params,
                parse_result=parse_result
            )
        elif self.is_coroutine:
            @wraps(self.obj)
            async def f(*args, **kwargs):
                return await self.async_call(
                    args, kwargs,
                    options=options,
                    first_reserve=first_reserve,
                    parse_params=parse_params,
                    parse_result=parse_result
                )
        else:
            @wraps(self.obj)
            def f(*args, **kwargs):     # noqa
                return self.sync_call(
                    args, kwargs,
                    options=options,
                    first_reserve=first_reserve,
                    parse_params=parse_params,
                    parse_result=parse_result
                )
        f.__parser__ = self
        return f

    def parse_pos_type(self, index: int, value, options: RuntimeOptions):
        pos_type = self.position_type
        # we should just ignore the runtime addition type
        if pos_type:
            try:
                value = options.transformer(value, pos_type)
            except Exception as e:
                error = exc.ParseError(
                    item=index,
                    value=value,
                    type=pos_type,
                    origin_exc=e
                )
                if options.invalid_items == options.PRESERVE:
                    options.collect_waring(error.formatted_message)
                    return value
                elif options.invalid_items == options.EXCLUDE:
                    options.collect_waring(error.formatted_message)
                    return ...
                else:
                    options.handle_error(error)
        return value

    def parse_params(self, args: tuple, kwargs: dict, options: RuntimeOptions) -> Tuple[tuple, dict]:
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
                arg = self.parse_pos_type(index=i, value=arg, options=options)
                if arg is ...:
                    continue
            else:
                field = self.positional_fields.get(i)
                # if field not exists, maybe it's a excluded var
                if field:
                    parsed_keys.append(field.attname)
                    arg = field.parse_value(arg, options=options)
                    if arg is ...:
                        # on_error=excluded, or error collected
                        pass
            parsed_args.append(arg)

        # 2. check if unprovided args has default give, and the unprovided required args
        for index, field in self.positional_only_fields:
            if field.attname in parsed_keys:
                continue
            if field.is_required(options=options):
                options.handle_error(exc.AbsenceError(item=field.attname))
                continue
            default = field.get_default(options)
            if default is not ...:
                # this position is definitely after parsed_args
                # because required args is always (we enforce check) ahead of default args
                parsed_args.append(default)
                parsed_keys.append(field.attname)       # need to append parsed as well

        parsed_kwargs = self.parse_data(
            kwargs,
            options=options,
            excluded_keys=parsed_keys,
            as_attname=True
        )

        return tuple(parsed_args), parsed_kwargs

    def get_params(self, args: tuple, kwargs: dict, options: RuntimeOptions,
                   first_reserve=None, parse_params: bool = None):
        _ = None
        if first_reserve is None:
            first_reserve = self.first_reserve
        if first_reserve:
            if self.instancemethod or self.classmethod:
                _self = pop(kwargs, '__self__')
                if self.classmethod:
                    if _self:
                        _ = getattr(_self, '__class__', None)
                    else:
                        _ = pop(kwargs, '__class__')
                elif _self:
                    _ = _self
            if args and not _:
                _, *args = args
        if parse_params:
            args, kwargs = self.parse_params(args, kwargs, options=options)
        if first_reserve:
            args = (_, *args)

        # if fill_omitted:
        #     # in function, omit param need to be filled (with ...) or TypeError will be raised
        #     # but in request and other scenarios maybe it's not required
        #     for omit_key in self.omitted_keys:
        #         key = self.attr_alias(omit_key)
        #         ind = self.arg_index.get(key)
        #         if key in self.pos_only_keys:
        #             if ind is None:
        #                 continue
        #             while ind >= len(parsed_args):
        #                 parsed_args.append(...)
        #         else:
        #             # index is None also means key maybe kw-only
        #             if ind is None or ind >= len(parsed_args):
        #                 # not filled in args
        #                 parsed_kwargs.setdefault(omit_key, ...)

        return args, kwargs

    def parse_result(self, result, options: RuntimeOptions):
        if self.return_type:
            try:
                result = options.transformer(result, self.return_type)
            except Exception as e:
                error = exc.ParseError(
                    item='<return>',
                    value=result,
                    type=self.return_type,
                    origin_exc=e
                )
                options.handle_error(error)
        return result

    def sync_generator(self, generator: Generator, options: RuntimeOptions):
        i = 0
        while True:
            try:
                item = next(generator)
            except StopIteration as err:
                result = err.value
                if result is None or not self.generator_return_type:
                    # raise the same StopIteration
                    raise
                try:
                    result = options.transformer(result, self.generator_return_type)
                except Exception as e:
                    error = exc.ParseError(
                        item=f'<generator.return>',
                        value=result,
                        type=self.generator_return_type,
                        origin_exc=e
                    )
                    options.handle_error(error, force_raise=True)
                return result
            else:
                if self.generator_yield_type:
                    try:
                        item = options.transformer(item, self.generator_yield_type)
                    except Exception as e:
                        error = exc.ParseError(
                            item=f'<generator.yield[{i}]>',
                            value=item,
                            type=self.generator_yield_type,
                            origin_exc=e
                        )
                        options.handle_error(error, force_raise=True)

                sent = yield item

                if sent is not None:
                    if self.generator_send_type:
                        try:
                            sent = options.transformer(sent, self.generator_send_type)
                        except Exception as e:
                            error = exc.ParseError(
                                item=f'<generator.send[{i}]>',
                                value=sent,
                                type=self.generator_send_type,
                                origin_exc=e
                            )
                            options.handle_error(error, force_raise=True)
                    generator.send(sent)
                i += 1

    def get_async_generator(self, options: RuntimeOptions,
                            first_reserve: bool = None,
                            parse_params: bool = None,
                            parse_result: bool = None,
                            ):
        @wraps(self.obj)
        async def async_generator(*args, **kwargs):
            args, kwargs = self.get_params(
                args, kwargs,
                options=options,
                first_reserve=first_reserve,
                parse_params=parse_params
            )
            func = self.obj
            generator = func(*args, **kwargs)
            i = 0
            async for item in generator:
                if parse_result and self.generator_yield_type:
                    try:
                        item = options.transformer(item, self.generator_yield_type)
                    except Exception as e:
                        error = exc.ParseError(
                            item=f'<asyncgenerator.yield[{i}]>',
                            value=item,
                            type=self.generator_yield_type,
                            origin_exc=e
                        )
                        options.handle_error(error, force_raise=True)

                sent = yield item

                if sent is not None:
                    if parse_result and self.generator_send_type:
                        try:
                            sent = options.transformer(sent, self.generator_send_type)
                        except Exception as e:
                            error = exc.ParseError(
                                item=f'<asyncgenerator.send[{i}]>',
                                value=sent,
                                type=self.generator_send_type,
                                origin_exc=e
                            )
                            options.handle_error(error, force_raise=True)
                    await generator.asend(sent)
                i += 1
        return async_generator

    def sync_call(self, args: tuple, kwargs: dict, options: RuntimeOptions,
                  first_reserve=None, parse_params: bool = None, parse_result: bool = None):
        args, kwargs = self.get_params(
            args, kwargs,
            options=options,
            first_reserve=first_reserve,
            parse_params=parse_params
        )
        func = self.obj
        result = func(*args, **kwargs)
        if parse_result:
            if self.do_parse_generator:
                return self.sync_generator(result, options=options)
            result = self.parse_result(result, options=options)
        return result

    async def async_call(self, args: tuple, kwargs: dict, options: RuntimeOptions,
                         first_reserve=None, parse_params: bool = None, parse_result: bool = None):
        args, kwargs = self.get_params(
            args, kwargs,
            options=options,
            first_reserve=first_reserve,
            parse_params=parse_params
        )
        func = self.obj
        result = await func(*args, **kwargs)
        if parse_result:
            # we may not want to change the result form even if it's another coroutine
            # we leave to user to await it to avoid changing the actual logic of the function
            # while inspect.iscoroutine(result):
            #     result = await result
            result = self.parse_result(result, options=options)
        return result

    # def __call__(self, *args, **kwargs):
    #     return self.sync_call(args, kwargs)
