# 解析函数参数

```python
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

>>> get_article_info(query='id=1&slug=my-article', body=b'[{"alice": 1}, {"bob": 2}]')
ArticleInfo(id=1, slug='my-article', info={'alice': 1, 'bob': 2})
```

!!! note
	虽然按照类型的声明，我们不应该在代码中这样调用函数，但是如果调用函数的是来自网络的 HTTP 请求，就可能会出现例子中的情况



### 异步函数


### 生成器函数


### 异步生成器函数