import utype
import typing
from utype import Param, Field, exc, Options, parse
import pytest
from datetime import datetime
from typing import Iterable, Dict, Iterator, Optional, AsyncIterator, AsyncIterable, Awaitable, Generator
import warnings


@pytest.fixture(params=(False, True))
def eager(request):
    return request.param


@pytest.fixture(params=('throw', 'exclude', 'preserve'))
def on_error(request):
    return request.param


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

        # @utype.parse(options=Options(mode='r'))
        # def feed_user(
        #     username: str,
        #     password: str = Param(mode='wa', default=None),
        #     followers_num: int = Param(mode='r', default=None),  # or mode='r'
        #     signup_time: datetime = Param(
        #         mode='ra',
        #         default_factory=datetime.now
        #     ),
        #     __options__: Options = Options(mode='w')
        # ):
        #     return username

    def test_invalids(self):
        from typing import Final, ClassVar

        with pytest.raises(exc.ConfigError):
            @utype.parse(options=Options(no_default=True))
            def f():
                pass

        with pytest.raises(exc.ConfigError):
            @utype.parse(options=Options(defer_default=True))
            def f():
                pass

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

        with pytest.warns():
            @parse
            def func(
                f1: str = Field(alias='test'),
                /
            ):
                return f1

        with pytest.warns():
            @parse
            def func(
                f1: str = Field(alias_from='test'),
                /
            ):
                return f1

        with pytest.warns():
            @parse
            def func(
                f1: str = Field(case_insensitive=True),
                /
            ):
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
                f1: str = Param(''),
                f2: str = Param(),
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
                f2: str = Param(),
            ):
                return f1, f2

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

        with pytest.raises(TypeError):
            example(0, 1, 2, pos_or_kw=1, kw_only_2='0')

        with pytest.raises(exc.AbsenceError):
            # >  required item: 'pos_only' is absence
            example(pos_only='1', pos_or_kw=1, kw_only_2='0')

        r = example('0', '1', '2', kw_only_2='0', k='3')
        assert r == (0, 1, (2,), 0, 0, {'k': 3})

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

    def test_generator(self, eager):
        csv_file = """
        1,3,5
        2,4,6
        3,5,7
        """

        from typing import Tuple

        @utype.parse(eager=eager)
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

        @utype.parse(eager=eager)
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

        @utype.parse(eager=eager)
        def split_iterator(*args: str) -> Iterator[Tuple[int, int]]:
            for arg in args:
                yield arg.split(',')

        params = ['1,2', '-1,3', 'a,b']

        iterator = split_iterator(*params)
        err = None
        while True:
            try:
                ln, rn = next(iterator)
                assert isinstance(ln, int)
                assert isinstance(rn, int)
            except StopIteration:
                break
            except utype.exc.ParseError as e:
                err = e
        assert err and '[2]' in str(err)

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

        @utype.parse(eager=eager)
        def fib(n: int = Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:
            if not n:
                yield _current
            else:
                yield fib(n - 1, _next, _current + _next)

        assert next(fib('100')) == 354224848179261915075

        if eager:
            with pytest.raises(exc.ParseError):
                fib('abc')
            with pytest.raises(exc.ParseError):
                fib(-1)
        else:
            with pytest.raises(exc.ParseError):
                next(fib('abc'))
            with pytest.raises(exc.ParseError):
                next(fib(-1))

        # but with larger num like 1000, it will raise RecursiveError

        @utype.parse(eager=eager)
        def o_fib(n: int = Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:
            if not n:
                yield _current
            else:
                yield utype.raw(o_fib)(n - 1, _next, _current + _next)

        # f10 = next(o_fib(10))
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

    def test_parse_config(self):
        class PositiveInt(int, utype.Rule):
            gt = 0

        class ArticleSchema(utype.Schema):
            id: Optional[PositiveInt]
            title: str = Field(max_length=100)
            slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")

        @utype.parse(
            options=Options(
                addition=False,
                case_insensitive=True
            ),
            ignore_result=True,
        )
        def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
            return {
                'id': id,
                'title': title,
                'slug': '-'.join([''.join(
                    filter(str.isalnum, v)) for v in title.split()]).lower()
            }

        query = {'ID': '3', 'Title': 'Big shot'}
        assert get_article(**query) == {
            'id': 3,
            'title': 'Big shot',
            'slug': 'big-shot'
        }

    @pytest.mark.asyncio
    async def test_async(self, eager):
        import asyncio
        from utype import types

        @utype.parse(eager=eager)
        async def sleep(seconds: float = utype.Param(ge=0)) -> Optional[types.NormalFloat]:
            if not seconds:
                return None
            if isinstance(seconds, types.AbnormalFloat):
                # force return parse error
                return seconds
            await asyncio.sleep(seconds)
            return str(seconds)

        assert await sleep(0) is None
        assert await sleep('0') is None
        assert await sleep(b'0.001') == 0.001

        awaitable = sleep('inf')  # test not await
        with pytest.raises(exc.ParseError):
            await awaitable

        if eager:
            with pytest.raises(exc.ParseError):
                _ = sleep(-0.3)

            with pytest.raises(exc.ParseError):
                _ = sleep('-inf')  # not ge than 0
        else:
            with pytest.raises(exc.ParseError):
                await sleep(-0.3)

            with pytest.raises(exc.ParseError):
                await sleep('-inf')   # not ge than 0

    @pytest.mark.asyncio
    async def test_async_generator(self, eager):
        import utype
        from typing import AsyncGenerator
        import asyncio

        @utype.parse(eager=eager)
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
                await wait_gen.asend(b"0.001")
                # wait for 0.001 seconds
            except StopAsyncIteration:
                pass

        if eager:
            with pytest.raises(exc.ParseError):
                waiter(-3)
            with pytest.raises(exc.ParseError):
                waiter('abc')
        else:
            with pytest.raises(exc.ParseError):
                async for _ in waiter(-3):
                    pass
            with pytest.raises(exc.ParseError):
                async for _ in waiter('abc'):
                    pass

        wait_gen = waiter(2)
        with pytest.raises(exc.ParseError):
            async for index in wait_gen:
                try:
                    await wait_gen.asend(b"abc")
                except StopAsyncIteration:
                    pass

        from utype.types import PositiveFloat

        @utype.parse(eager=eager)
        async def waiter2(*seconds: PositiveFloat | 0) -> AsyncIterable[int]:
            for i, sec in enumerate(seconds):
                yield str(i)
                if sec:
                    assert isinstance(sec, float)
                    await asyncio.sleep(sec)

        w2 = waiter2(0, '0.0001')

        async for ind in w2:
            assert isinstance(ind, int)

        if eager:
            with pytest.raises(exc.ParseError):
                waiter2(-3)
            with pytest.raises(exc.ParseError):
                waiter2('abc')
        else:
            with pytest.raises(exc.ParseError):
                async for _ in waiter2(-3):
                    pass
            with pytest.raises(exc.ParseError):
                async for _ in waiter2('abc'):
                    pass

    def test_class_methods(self):
        class Class:
            arg = '3'

            @classmethod
            @utype.parse
            def operation(cls, p: str):
                return cls.generate2(param=p)

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

            @property
            @utype.parse
            def test(self) -> int:
                return self.arg

            @test.setter
            @utype.parse
            def test(self, v: int = Param(le=10)):
                self.arg = v

        assert Class.operation(b'3') == 3

        assert Class.generate1('3') == 3
        assert Class.generate2(param='3') == 3
        assert Class.generate3(param='3') == 3

        c = Class()
        assert c.test == 3
        c.test = '4'
        assert c.arg == 4
        assert c.test == 4

        with pytest.raises(exc.ParseError):
            c.test = 12

        with pytest.raises(exc.ParseError):
            c.test = 'abc'

        with pytest.raises(exc.ParseError):
            c.arg = 'abc'
            _ = c.test

        with pytest.raises(exc.ParseError):
            Class.generate1(-1)

        with pytest.raises(exc.ParseError):
            Class.generate2(param=-1)

        with pytest.raises(exc.ParseError):
            Class.generate3(param=-1)

        @utype.parse()
        class Auto:
            @classmethod
            def operation(cls, p: str):
                return cls.generate(param=p)

            @staticmethod
            def generate(param: int = Param(ge=0)):
                return param

            def method(self, key: int = Param(le=10)):
                return self.generate(key)

            @utype.parse
            def __call__(self, *args, **kwargs):
                return self, args, kwargs

        assert Auto.operation(b'3') == 3
        assert Auto.generate(b'3') == 3

        with pytest.raises(exc.ParseError):
            Auto.operation(b'-3')

        with pytest.raises(exc.InvalidInstance):
            Auto.method(1, 2)

        assert Auto.method(Auto(), 2) == 2
        assert Auto().method('3') == 3

        @utype.parse
        @utype.dataclass
        class Data:
            arg: int = Field(le=10)

            @classmethod
            def operation(cls, k: str):
                return cls.generate(param=k)

            @staticmethod
            def generate(param: int = Param(ge=0)) -> int:
                return str(param)

            @utype.parse
            def __call__(self, *args: int, **kwargs: int):
                return self.arg, args, kwargs

        d = Data(arg=b'10')
        assert d.arg == 10

        assert d.operation('4') == 4

        with pytest.raises(exc.ParseError):
            d.operation(-3)

        assert d('1', '2', k='3') == (10, (1, 2), {'k': 3})

        from typing import Union

        class Power:
            MOD = 10007

            num: float
            exp: float

            @staticmethod
            @utype.parse
            def int_power(
                num: int = utype.Param(ge=0),
                exp: int = utype.Param(ge=0),
                mod: int = None
            ) -> int:
                return pow(num, exp, mod)

            @staticmethod
            @utype.parse
            def float_power(num: float, exp: float) -> Union[float, complex]:
                return pow(num, exp)

            @classmethod
            @utype.parse
            def cls_power(cls, num: int, exp: int) -> int:
                return cls.int_power(num, exp, mod=cls.MOD)

            @utype.parse
            def power(self) -> int:
                return self.cls_power(self.num, self.exp)

            @utype.parse
            def __init__(self, num: float, exp: float):
                if num < 0:
                    if 1 > exp > -1 and exp != 0:
                        raise exc.ParseError(f'operation not supported, '
                                             f'complex result will be generated')
                self.num = num
                self.exp = exp

        power = Power('3', 3)
        assert power.power() == 27
        assert Power.cls_power('123', 321) == 4402

        with pytest.raises(exc.ParseError):
            Power.cls_power('-1', 321)

        class IntPower:
            @utype.parse
            def __init__(
                self,
                base: int = utype.Param(ge=0),
                exp: int = utype.Param(ge=0),
            ):
                self.base = base
                self.exp = exp

            @utype.parse
            def power(self, mod: int = utype.Param(None, ge=0)) -> int:
                return pow(self.base, self.exp, mod=mod)

        p = IntPower('3', 3)
        assert p.power() == 27
        assert p.power('5') == 2

        class Request:
            def __init__(self, body: bytes):
                self.body = body

            @property
            @utype.parse
            def json_body(self) -> dict:
                return self.body

            @json_body.setter
            @utype.parse
            def json_body(self, data: dict):
                import json
                self.body = json.dumps(data)

        req = Request(b'{"id": 11, "enabled": false}')
        assert req.json_body['enabled'] is False

        req.json_body = '{"id": 11, "enabled": true}'
        assert req.json_body['enabled'] is True

        with pytest.raises(exc.ParseError):
            req.json_body = '@invalid-payload'

        @utype.parse
        class PowerIterator:
            def _power(
                self,
                num: Union[int, float],
                exp: Union[int, float],
            ) -> Union[int, float, complex]:
                return pow(num, exp, self.mod)

            def iter_int(self, *args: int, exp: int) -> Iterator[int]:
                for base in args:
                    yield self._power(base, exp)

            @utype.parse
            def __init__(self, mod: int = None):
                self.mod = mod

        pi = PowerIterator('3')
        pg = pi.iter_int('3', '4', '5', exp=5)
        assert next(pg) == 0
        assert next(pg) == 1
        assert next(pg) == 2

        with pytest.raises(TypeError) as info:
            assert pi._power('-1', 1)       # not applied

        assert info.type == TypeError

