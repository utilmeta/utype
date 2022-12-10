# 函数的解析

!!! note
	虽然按照类型的声明，我们不应该在代码中这样调用函数，但是如果调用函数的是来自网络的 HTTP 请求，就可能会出现例子中的情况


## 声明函数参数


* position only
* position var
* position or keyword
* keyword only
* keyword var

**可选参数的声明限制**
Python 已经限制了


**无效的 Field 参数**

* no_output
* immutable
* defer_default


## 解析参数

你可以在 `@utype.parse` 装饰器的参数中转入以下的函数解析选项
* `ignore_params`：是否忽略对函数参数的解析，默认为 False
* `ignore_result`：是否忽略对函数结果的解析，默认为 False
* `options`：你的解析配置，具体用法可以参考 [Options 解析配置](../references/options)
* `parser_cls`：传入你自定义的解析类，默认是 `utype.parser.FunctionParser`，你可以通过继承和扩展它来实现你自定义的函数解析功能

## 使用场景

### 初始化数据类

```python
import utype
  
class PowerSchema(utype.Schema):  
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
```

这种方式比为数据类自定义 `__init__` 函数还要灵活，因为可以声明多种不同的初始化参数与逻辑


```python
import utype  
from typing import List, Dict

class Slug(str, utype.Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"  
  
class ArticleQuery(utype.Schema):  
    id: int  
    slug: Slug = utype.Field(max_length=30)  
  
class ArticleInfo(ArticleQuery):  
    likes: Dict[str, int]  
  
@utype.parse  
def get_article_info(  
    query: ArticleQuery,  
    body: List[Dict[str, int]] = utype.Field(default=list)  
) -> ArticleInfo:  
    likes = {}  
    for item in body:  
        likes.update(item)  
    return {  
        'id': query.id,  
        'slug': query.slug,  
        'likes': likes  
    }

article = get_article_info(
	query='id=1&slug=my-article', 
	body=b'[{"alice": 1}, {"bob": 2}]'
)

print(article)
# > ArticleInfo(id=1, slug='my-article', info={'alice': 1, 'bob': 2})
```

## 异步函数与生成器

### 异步函数


### 生成器函数

* Generator
* Iterator
* Iterable

### 异步生成器函数


## 其他类型函数

### `@classmethod`
TODO

### `@staticmethod`
TODO

### `@property`
TODO
