import utype
import typing
from utype import Field, exc
import pytest


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
            body: typing.List[typing.Dict[str, int]] = utype.Field(default_factory=list)
        ) -> ArticleInfo:
            likes = {}
            for item in body:
                likes.update(item)
            return {
                'id': query.id,
                'slug': query.slug,
                'likes': likes
            }

        assert get_article_info(query='id=1&slug=my-article', body=b'[{"alice": 1}, {"bob": 2}]') == \
               ArticleInfo(id=1, slug='my-article', likes={'alice': 1, 'bob': 2})

    def test_args_assign(self):
        @utype.parse
        def complex_func(
            po1: str = Field(required=True),
            po2: int = Field(default_factory=str), /,
            pos_and_kw: int = Field(default=1, alias_from=['pw1', 'pw2']), *,
            kw_only1: str = Field(case_insensitive=True)
        ):
            pass

        # with pytest.warns(match='alias'):
        #     # positional only args's alias is meaningless
        #     @utype.parse
        #     def complex_func1(
        #         po1: str = Field(required=True, alias_from=['a1', 'a2']),
        #         po2: int = Field(default_factory=str), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

        # with pytest.raises(Exception):
        #     # positional only args: default ahead of required
        #     @utype.parse
        #     def complex_func2(
        #         po1: str = Field(default=''),
        #         po2: int = Field(required=True), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

        # with pytest.raises(Exception):
        #     # positional only args: required=False args but no default specified
        #     @utype.parse
        #     def complex_func3(
        #         po1: str = Field(required=False), /,
        #         pos_and_kw: int = 1
        #     ):
        #         pass

    @pytest.mark.asyncio
    async def test_async_generator(self):
        import utype
        from typing import AsyncGenerator
        import asyncio

        @utype.parse
        async def waiter(rounds: int = utype.Field(gt=0)) -> AsyncGenerator[int, float]:
            assert isinstance(rounds, int)
            i = rounds
            while i:
                wait = yield str(i)
                if wait:
                    assert isinstance(wait, float)
                    await asyncio.sleep(wait)
                i -= 1

        wait_gen = waiter('2')
        async for index in wait_gen:
            assert isinstance(index, int)
            try:
                await wait_gen.asend(b'0.05')
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
                    await wait_gen.asend(b'abc')
                except StopAsyncIteration:
                    pass
