import utype
import typing
from utype import Param, Field, exc, Options, parse
import pytest
from datetime import datetime
from typing import Iterable, Dict, Iterator, Optional, AsyncIterator, AsyncIterable, Awaitable, Generator
import warnings


class TestFunc:
    def test_basic(self):
        import utype

        class Slug(str, utype.Rule):
            regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"

        class ArticleQuery(utype.Schema):
            id: int
            slug: Slug = utype.Field(max_length=30)

        class ArticleInfo(ArticleQuery):
            likes: typing.Dict[str, int]

        @utype.parse
        def get_article_info(
            query: ArticleQuery,
            body: typing.List[typing.Dict[str, int]] = utype.Param(
                default_factory=list
            ),
        ) -> ArticleInfo:
            likes = {}
            for item in body:
                likes.update(item)
            return {"id": query.id, "slug": query.slug, "likes": likes}

        assert get_article_info(
            query="id=1&slug=my-article", body=b'[{"alice": 1}, {"bob": 2}]'
        ) == ArticleInfo(id=1, slug="my-article", likes={"alice": 1, "bob": 2})

        @utype.parse
        def create_user(
            username: str = utype.Param(regex='[0-9a-zA-Z_-]{3,20}', example='alice-01'),
            password: str = utype.Param(min_length=6, max_length=50),
            avatar: Optional[str] = utype.Param(
                None,
                description='the avatar url of user',
                alias_from=['picture', 'headImg'],
            ),
            signup_time: datetime = utype.Param(
                no_input=True,
                default_factory=datetime.now
            )
        ) -> dict:
            return {
                'username': username,
                'password': password,
                'avatar': avatar,
                'signup_time': signup_time,
            }

        alice = create_user('alice-001', 'abc1234', headImg='https://fake.avatar', signup_time='ignored')
        assert alice['avatar'] == 'https://fake.avatar'
        assert isinstance(alice['signup_time'], datetime)

    def test_input(self):
        @utype.parse
        def func(
            f1: str = Param(no_input=True, default='default'),
            f2: str = Param(no_input=True, default_factory=list),
        ):
            return f1, f2

        with pytest.raises(exc.ConfigError):
            @utype.parse
            def func(
                f1: str = Param(no_input=True),
                f2: str = Param(no_input=True, default_factory=list),
            ):
                return f1, f2

        with pytest.raises(exc.ConfigError):
            @utype.parse
            def func(
                f1: str = Field(default=None, defer_default=True),
                f2: str = Param(no_input=True, default_factory=list),
            ):
                return f1, f2

    def test_mode(self):
        @utype.parse(options=Options(mode='w'))
        def func(
            fr: str = Param(None, mode='r'),
            fw: list = Param(mode='w', default_factory=list),
        ):
            return fr, fw

        assert func(fr='1', fw=[1]) == (None, [1])

        with pytest.raises(exc.ConfigError):
            @utype.parse
            def func(
                f1: str = Param(mode='r'),     # specify mode with no default
            ):
                return f1

        @utype.parse(options=Options(mode='r'))
        def feed_user(
            username: str,
            password: str = Param(mode='wa', default=None),
            followers_num: int = Param(mode='r', default=None),  # or mode='r'
            signup_time: datetime = Param(
                mode='ra',
                default_factory=datetime.now
            ),
            __options__: Options = Options(mode='w')
        ):
            return username

    def test_invalids(self):
        from typing import Final, ClassVar
        with pytest.warns():
            @utype.parse
            def func2(
                f1: Final[str] = Param(no_input=True, default='default'),
            ):
                return f1

        with pytest.warns():
            @utype.parse
            def func2(
                f1: ClassVar[str] = Param(no_input=True, default='default'),
            ):
                return f1

        with pytest.warns():
            # immutable means nothing to field
            @utype.parse
            def func(f1: str = Field(immutable=True)):
                return f1

        with pytest.warns():
            # immutable means nothing to field
            @utype.parse
            def func(f1: str = Field(repr=False)):
                return f1

    def test_field_default_required_function(self):
        # @parse
        # def func(
        #     f1: str,
        #     f2: str = Param(required=True),
        #     f3: str = Param(required=False),
        #     f4: str = Param(default_factory=str),
        #     f5: int = Param(default=0),
        #     f6: str = ''
        # ):
        #     return locals()

        with pytest.raises(Exception):
            # not accept a not required field with no default
            @parse
            def func(f1: str = Field(required=False)):
                return f1

        @parse
        def func(f1: str = Field(required=False)): pass
        # a passed function can declare not-always-provided param

        with pytest.warns():
            @parse
            def func(
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
            ):
                return f1, f2

            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with pytest.raises(SyntaxError):
            @parse
            def func3(
                f0: str,
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
                _p1: int = 0,
                # positional only
                /,
                # positional or keyword
                f3: str = Field(required=True),
            ):
                return locals()
            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with pytest.warns():
            @parse
            def func3(
                f0: str,
                f1: str = Field(required=False, default=''),
                f2: str = Field(required=True),
            ):
                return locals()
            # required param is after the optional param
            # in not-keyword-only (can be positional passed) function

        with warnings.catch_warnings():
            warnings.simplefilter("error")

            @parse
            def func(
                *,  # if we add a key-word-only sign, it
                f1: str = Param(''),
                f2: str = Field(required=True),
            ):
                return f1, f2

        with pytest.warns():
            # defer default means nothing to
            @parse
            def func(f1: str = Field(default=0, defer_default=True)):
                return f1

    def test_args_kwargs(self, on_error):
        from utype import Rule

        class Index(int, Rule):
            ge = 0

        @utype.parse(options=Options(invalid_items=on_error, invalid_values=on_error))
        def call(*series: int, **mapping: Index | None) -> Dict[str, int]:
            result = {}
            for key, val in mapping.items():
                if val is not None and val < len(series):
                    result[key] = series[val]
            return result

        mp = {
            'k1': 1,   # will convert to string
            'k2': None,
            'k3': '0'
        }
        res = call(-1.1, '3', 4, **mp)
        assert res == {'k1': 3, 'k3': -1}

        if on_error == 'preserve':

            with pytest.warns():
                assert call('a', 1, key='0') == {'key': 'a'}
        elif on_error == 'exclude':

            with pytest.warns():
                assert call('a', 1, k1='i', k2='0') == {'k2': 1}

        elif on_error == 'throw':

            with pytest.raises(exc.ParseError):
                call('a', 'b')

            with pytest.raises(exc.ParseError):
                call(1, 2, key=-3)

    def test_args_assign(self):
        @utype.parse
        def complex_func(
            po1: str = Param(required=True),
            po2: int = Param(default_factory=str),
            /,
            pos_and_kw: int = Param(default=1, alias_from=["pw1", "pw2"]),
            *,
            kw_only1: None = Param(case_insensitive=True),
        ):
            pass

        def func3(
            f0: str,
            f1: str = Param(''),
            f2: str = Param(),
            _p1: int = 0,
            # positional only
            /,
            # positional or keyword
            f3: str = Param(),
            f4: str = Param(),
            _p2: int = 0,
            *args: int,  # positional var
            # keyword only
            f5: str = Param(),
            f6: str,
            _p3: int = 0,
            **kwargs: int  # keyword var
        ):
            return locals()

        def example(
            # positional only
            pos_only: int,
            /,
            # positional or keyword
            pos_or_kw: int = Param(0),
            # positional var
            *args: int,
            # keyword only
            kw_only_1: int = Param(0),
            kw_only_2: int = Param(),
            # keyword var
            **kwargs: int
        ):
            return pos_only, pos_or_kw, args, kw_only_1, kw_only_2, kwargs

        r = example(0, 1, 2, pos_or_kw=1)
        r = example('0', '1', '2', pos_or_kw='1')

        # with pytest.warns(match='alias'):
        #     # positional only args's alias is meaningless
        #     @utype.parse
        #     def complex_func1(
        #         po1: str = Param(required=True, alias_from=['a1', 'a2']),
        #         po2: int = Param(default_factory=str), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

        # with pytest.raises(Exception):
        #     # positional only args: default ahead of required
        #     @utype.parse
        #     def complex_func2(
        #         po1: str = Param(default=''),
        #         po2: int = Param(required=True), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

        # with pytest.raises(Exception):
        #     # positional only args: required=False args but no default specified
        #     @utype.parse
        #     def complex_func3(
        #         po1: str = Param(required=False), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

    def test_excluded_vars(self):
        @utype.parse
        def excluded(a: int, _excluded0: int, *, _excluded1: int = 0):
            return a, _excluded0, _excluded1

        @utype.parse
        def fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1):
            if not n:
                return _current
            else:
                return fib(n - 1, _next, _current + _next)

        assert fib('10') == 55
        assert fib('10', _current=10, _next=6) == 55
        assert fib('10', 10, 5) == 615      # can pass through positional args

    def test_generator(self):

        csv_file = """
        1,3,5
        2,4,6
        3,5,7
        """

        from typing import Tuple

        @utype.parse
        def read_csv(file: str) -> Generator[Tuple[int, ...], None, int]:
            lines = 0
            for line in file.splitlines():
                if line.strip():
                    yield line.strip().split(',')
                    lines += 1
            return lines

        csv = read_csv(csv_file)
        assert next(csv) == (1, 3, 5)
        assert next(csv) == (2, 4, 6)
        assert next(csv) == (3, 5, 7)

        try:
            next(csv)
        except StopIteration as e:
            assert e.value == 3

        @utype.parse
        def echo_round() -> Generator[int, float, int]:
            cnt = 0
            sent = 0
            while True:
                sent = yield round(sent)
                if not sent:
                    break
                cnt += 1
            return cnt

        echo = echo_round()
        next(echo)
        assert echo.send('12.1') == 12
        assert echo.send(b'0.05') == 0
        assert echo.send(3.9) == 4
        try:
            next(echo)
        except StopIteration as e:
            assert e.value == 3

        # lst = ['12.1', b'0.05', 13.9, 0]
        # result = []
        # next(echo)
        # for item in lst:
        #     try:
        #         result.append(echo.send(item))
        #     except StopIteration:
        #         break

        # i = 0
        # for res in echo:
        #     print('res:', res)
        #     echo.send(lst[i])
        #     if res:
        #         result.append(res)
        #     i += 1

        @utype.parse
        def fib(n: int = Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:
            if not n:
                yield _current
            else:
                yield fib(n - 1, _next, _current + _next)

        assert next(fib('100')) == 354224848179261915075

        # but with larger num like 1000, it will raise RecursiveError

        @utype.parse
        def o_fib(n: int = Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:
            if not n:
                yield _current
            else:
                yield utype.raw(o_fib)(n - 1, _next, _current + _next)

        f10 = next(o_fib(10))
        assert next(o_fib(2000)) % 100007 == 57937

        # @utype.parse
        # def fib_loop(n: int = Param(ge=0)) -> int:
        #     a, b = 0, 1
        #     _n = 1
        #     while _n < n:  # First iteration:
        #         # yield a  # yield 0 to start with and then
        #         a, b = b, a + b  # a will now be 1, and b will also be 1, (0 + 1)
        #         _n += 1
        #     return b

    @pytest.mark.asyncio
    async def test_async(self):
        import aiohttp
        import asyncio
        from typing import List, Awaitable

        async def fetch(url: str) -> str:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()

        async def fetch_urls(*urls: str) -> Dict[str, dict]:
            result = {}
            tasks = []

            async def task(loc):
                result[loc] = await fetch(loc)

            for url in urls:
                tasks.append(asyncio.create_task(task(url)))

            await asyncio.gather(*tasks)
            return result

        # def awaitable_fetch_urls(urls: List[str]) -> Awaitable[Dict[str, dict]]:
        #     return fetch_urls(urls)

        req_urls = [
            b'https://httpbin.org/get?k1=v1',
            b'https://httpbin.org/get?k1=v1&k2=v2',
            b'https://httpbin.org/get',
        ]
        res = await fetch_urls(*req_urls)

    @pytest.mark.asyncio
    async def test_async_generator(self):
        import utype
        from typing import AsyncGenerator
        import asyncio

        @utype.parse
        async def waiter(rounds: int = utype.Param(gt=0)) -> AsyncGenerator[int, float]:
            assert isinstance(rounds, int)
            i = rounds
            while i:
                wait = yield str(i)
                if wait:
                    assert isinstance(wait, float)
                    await asyncio.sleep(wait)
                i -= 1

        wait_gen = waiter("2")
        async for index in wait_gen:
            assert isinstance(index, int)
            try:
                await wait_gen.asend(b"0.05")
                # wait for 0.05 seconds
            except StopAsyncIteration:
                pass

        with pytest.raises(exc.ParseError):
            async for _ in waiter(-3):
                pass

        wait_gen = waiter(2)
        with pytest.raises(exc.ParseError):
            async for index in wait_gen:
                try:
                    await wait_gen.asend(b"abc")
                except StopAsyncIteration:
                    pass

    def test_for_cls(self):
        from utype import Schema, exc

        class PowerSchema(Schema):
            result: float
            num: float
            exp: float

        @utype.parse
        def get_power(num: float, exp: float) -> PowerSchema:
            if num < 0:
                if 1 > exp > -1 and exp != 0:
                    raise exc.ParseError(f'operation not supported, '
                                         f'complex result will be generated')
            return PowerSchema(
                num=num,
                exp=exp,
                result=num ** exp
            )

        power = get_power('3', 3)
        assert power.result == 27

        with pytest.raises(exc.ParseError):
            get_power(-0.5, -0.5)

        @utype.parse
        def get_power_locals(num: float, exp: float) -> PowerSchema:
            if num < 0:
                if 1 > exp > -1 and exp != 0:
                    raise exc.ParseError(f'operation not supported, '
                                         f'complex result will be generated')
            result = num ** exp
            return locals()

        v = get_power_locals(num=3)

    def test_class_methods(self):

        class Class:
            @classmethod
            @utype.parse
            def operation(cls):
                return cls.generate2(param='3')

            @staticmethod
            @utype.parse
            def bad(param, value: int = 0):
                return param

            @staticmethod
            @utype.parse
            def generate(param: int = Param(ge=0)):
                return param

            @utype.parse
            @staticmethod
            def generate1(param: int = Param(ge=0)):
                return param

            @staticmethod
            @utype.parse
            def generate2(*, param: int = Param(ge=0)):
                return param

            @staticmethod
            @utype.parse
            def generate3(param: int = Param(ge=0)):
                return param

            @utype.parse
            def __call__(self, *args, **kwargs):
                return self, args, kwargs

        @utype.parse()
        class Auto:
            @classmethod
            def operation(cls):
                return cls.generate(param='3')

            @staticmethod
            def generate(param: int = Param(ge=0)):
                return param

            def method(self, key: int = Param(le=10)):
                return self.generate(key)

            @utype.parse
            def __call__(self, *args, **kwargs):
                return self, args, kwargs

        with pytest.raises(exc.InvalidInstance):
            Auto.method(1, 2)

        @utype.parse
        @utype.dataclass
        class Data:
            @classmethod
            def operation(cls):
                return cls.generate(param='3')

            @staticmethod
            def generate(param: int = Param(ge=0)):
                return param

            @utype.parse
            def __call__(self, *args: int, **kwargs: str):
                return self, args, kwargs

    def test_staticmethod(self):
        pass

    def test_property(self):
        pass

