from utype import Schema, Field


class ArticleSchema(Schema):
    _slug: str
    _title: str

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, val: str = Field(max_length=50)):
        self._title = val
        self._slug = '-'.join([''.join(filter(str.isalnum, v))
                               for v in val.split()]).lower()


article = ArticleSchema(title=b'My Awesome article!')
print(article.slug)
# > 'my-awesome-article'

try:
    article.slug = 'other value'
except AttributeError:
    pass

article.title = b'Our Awesome article!'
print(dict(article))
# > {'slug': 'our-awesome-article', 'title': 'Our Awesome article!'}
