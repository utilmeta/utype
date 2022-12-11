from utype import Schema, Field
from datetime import datetime
from typing import List


class ArticleSchema(Schema):
    slug: str = Field(
        regex=r"[a-z0-9]+(?:-[a-z0-9]+)*",
        immutable=True,
        example='my-article',
        description='the url part of an article'
    )
    content: str = Field(alias_from=['text', 'body'])
    # body: str = Field(required=False, deprecated='content')
    views: int = Field(ge=0, default=0, readonly=True)
    created_at: datetime = Field(
        alias='createdAt',
        readonly=True,
        required=False,
    )
    tags: List[str] = Field(default_factory=list, no_output=lambda v: not v)


article = ArticleSchema(
    slug=b'test-article',
    body='article body',
    tags=[]
)
assert 'createdAt' not in article

print(article)
# > ArticleSchema(slug='test-article', content='article body', views=0)

try:
    article.slug = 'other-slug'
except AttributeError as e:
    print(e)
    """
    AttributeError: ArticleSchema: Attempt to set immutable attribute: ['slug']
    """

from utype import exc
try:
    article.views = -3
except exc.ParseError as e:
    print(e)
    """
    ParseError: parse item: ['views'] failed: Constraint: <ge>: 0 violated
    """

article.created_at = '2022-02-02 10:11:12'
print(dict(article))
# > {'slug': 'test-article', 'content': 'article body',
# > 'views': 0, 'createdAt': datetime.datetime(2022, 2, 2, 10, 11, 12)}
