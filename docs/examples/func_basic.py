import utype
from typing import Optional


class PositiveInt(int, utype.Rule):
    gt = 0


class ArticleSchema(utype.Schema):
    id: Optional[PositiveInt]
    title: str = utype.Field(max_length=100)
    slug: str = utype.Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")


@utype.parse
def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
    return {
        'id': id,
        'title': title,
        'slug': '-'.join([''.join(
            filter(str.isalnum, v)) for v in title.split()]).lower()
    }


print(get_article('3', title=b'My Awesome Article!'))
# > ArticleSchema(id=3, title='My Awesome Article!', slug='my-awesome-article')

try:
    get_article('-1')
except utype.exc.ParseError as e:
    print(e)

try:
    get_article(title='*' * 101)
except utype.exc.ParseError as e:
    print(e)
