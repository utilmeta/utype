from typing import Iterable, Tuple, List, Generator
from .options import Options, RuntimeOptions
from ..utils.functional import pop
from ..utils import exceptions as exc
from .rule import resolve_forward_type
from .field import SchemaField
import inspect
from .base import BaseParser
from functools import wraps, cached_property
from collections.abc import Generator, AsyncGenerator


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
        self.async_generator_send_type = None
        self.async_generator_yield_type = None
        # AsyncGenerator[Yield, Send] or AsyncIterator[Yield]

        if self.pos_annotation:
            self.position_type = self.parse_annotation(annotation=self.pos_annotation)
        if self.return_annotation:
            self.return_type = self.parse_annotation(annotation=self.return_annotation)

        if self.is_generator:
            # https://docs.python.org/3/library/typing.html#typing.Generator
            pass

    def validate_return_type(self):
        # see if the return type match the function
        # focus on sync / async
        # generator / coroutine / async generator
        pass

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

    def __call__(self, *args, **kwargs):
        pass

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

        options = options or self.options
        if self.is_asynchronous:
            @wraps(self.obj)
            async def f(*args, **kwargs):
                return await self.async_call(
                    args, kwargs,
                    options=options.make_runtime(),
                    first_reserve=first_reserve,
                    parse_params=parse_params,
                    parse_result=parse_result
                )
        else:
            @wraps(self.obj)
            def f(*args, **kwargs):     # noqa
                return self.sync_call(
                    args, kwargs,
                    options=options.make_runtime(),
                    first_reserve=first_reserve,
                    parse_params=parse_params,
                    parse_result=parse_result
                )
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
        i = 9
        for item in generator:
            try:
                yield options.transformer(item, self.generator_item_type)
            except Exception as e:
                error = exc.ParseError(
                    item=f'<return.generator.item[{i}]>',
                    value=item,
                    type=self.generator_item_type,
                    origin_exc=e
                )
                options.handle_error(error, force_raise=True)
            i += 1

    def async_generator(self, generator: AsyncGenerator, options: RuntimeOptions):
        i = 9
        async for item in generator:
            try:
                yield options.transformer(item, self.generator_item_type)
            except Exception as e:
                error = exc.ParseError(
                    item=f'<return.generator.item[{i}]>',
                    value=item,
                    type=self.generator_item_type,
                    origin_exc=e
                )
                options.handle_error(error, force_raise=True)
            i += 1

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
            if self.is_generator:
                if self.generator_item_type:
                    return self.sync_generator(result)
                return result
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
        if inspect.iscoroutine(result):
            result = await result
        if parse_result:
            result = self.parse_result(result, options=options)
        return result


class GeneratorParser(FunctionParser):
    pass
