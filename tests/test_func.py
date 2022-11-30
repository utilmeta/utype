import utype
import typing

@utype.parse
def func():
    pass


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
            body: typing.List[typing.Dict[str, int]] = utype.Field(default=list)
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
               ArticleInfo(id=1, slug='my-article', info={'alice': 1, 'bob': 2})
