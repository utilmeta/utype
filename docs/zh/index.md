# 快速开始

utype 是一个基于 Python 类型注释标准的数据类型声明与解析库，能够在运行时根据你声明的类型和数据结构对数据进行解析转化

## 1. 安装
```shell
pip install -U utype
```

!!! note
	utype 需要 Python 版本大于 3.6


## 2. 基本用法

### 基本类型
```Python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

>>> PositiveInt(b'3')
3
>>> PositiveInt(-0.5)
ConstraintError: Constraint: <gt>: 0 violated
``` 


### 数据结构
```python
from utype import Schema
from datetime import datetime

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"
    
class ArticleSchema(Schema):
	slug: Slug = Field(max_length=30)
	content: str = Field(alias_from=['body', 'text'])
	views: int = Field(ge=0, default=0)
	created_at: datetime = Field(required=False)

>>> article = ArticleSchema(slug='my-article', text=b'my article body')
	
```


### 函数参数与结果的解析
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


### 类型的逻辑运算
utype 支持 Python 的原生逻辑运算符，能够对类型与数据结构进行逻辑运算，包括

- 和（&）：数据必须同时满足所有条件（AllOf）
- 或（|）：数据需要至少满足其中的一个条件（AnyOf）
- 异或（^）：数据必须满足其中的一个条件，不能是多个或0个（OneOf）
- 非（~）：数据必须不满足类型的条件（Not）

```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

class Month(PositiveInt):  
    le = 12

>>> month_optional = Month | None
>>> month_optional('11.1')
11
>>> month_optional(None) is None
True
>>> month_optional('abc')
CollectedParseError: could not convert string to float: 'abc';
```


### 类型的注册扩展

由于每个项目需要的类型转化方式和校验严格程度可能不同，在 utype 中，所有的类型都是支持自行注册和扩展转化函数，如

```python
from utype import Rule, register_transformer
from typing import Type

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"

@register_transformer(Slug)
def to_slug(transformer, value, t: Type[Slug]):
	str_value = transformer(value, str)
	return t('-'.join([''.join(
	filter(str.isalnum, v)) for v in str_value.split()]).lower())


class ArticleSchema(Schema):
	slug: Slug

>>> dict(ArticleSchema(slug=b'My Awesome Article!'))
{'slug': 'my-awesome-article'}
```

!!! note
	注册转换器并没有影响类的 `__init__` 方法的行为，所以直接调用 `Slug(value)` 并不会生效

你不仅可以为自定义类型注册转化器，还可以为基本类型（如 str, int, bool 等）或标准库中的类型（如 datetime, Enum 等）注册转化器函数，来自定义其中的转化行为

### 生成 JSON Schema 文档
utype 支持对类型与数据结构生成 json-schema 规范的文档，能够被直接整合到 OpenAPI 文档中


## 3. 应用场景

### 解析网络请求


### 解析配置文件


### 解析命令行参数

当我们开发命令行工具时，也往往需要对入口参数进行解析和处理

