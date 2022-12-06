import re


class Article:
    slug: str
    content: str
    views: int = 0

    def __init__(self, slug: str, content: str, views: int = 0):
        if not isinstance(slug, str) \
                or not re.findall(slug,  r"[a-z0-9]+(?:-[a-z0-9]+)*") \
                or len(slug) > 30:
            raise ValueError(f'Bad slug: {slug}')
        if not isinstance(content, str):
            raise ValueError(f'Bad content: {content}')
        if not isinstance(views, int) or views < 0:
            raise ValueError(f'Bad views: {views}')
        self.slug = slug
        self.content = content
        self.views = views


from utype import Schema, Rule, Field


class Slug(str, Rule):
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"


class ArticleSchema(Schema):
    slug: Slug = Field(max_length=30)
    content: str = Field(alias_from=['body', 'text'])
    views: int = Field(ge=0, default=0)


print(ArticleSchema(slug='my-article', text=b'my article body'))
