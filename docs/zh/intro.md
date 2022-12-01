# uType - 介绍

utype 是一个基于 Python 类型注解的数据类型声明与解析库，能够在运行时根据你声明的类型和数据结构对数据进行解析转化

### 核心特性
* 基于 Python 类型注解在运行时对类型，数据结构，函数参数与结果等进行解析转化
* 支持类型约束，类型的逻辑运算等，以声明更复杂的解析条件
* 高度可扩展，所有类型的转化函数都可以注册，覆盖与扩展，并提供高度灵活的解析选项
* 支持输出 json-schema 格式的文档，兼容 OpenAPI 

## 1. 安装
```shell
pip install -U utype
```

!!! note
	utype 需要 Python 版本大于 3.6


## 2. 用法示例

### 基本类型与约束
```Python
from utype import Rule, exc

class PositiveInt(int, Rule):  
    gt = 0

assert PositiveInt(b'3') == 3

try:
	PositiveInt(-0.5)
except exc.ParseError as e:
	print(e)
	"""
	Constraint: <gt>: 0 violated
	"""
``` 


### 转化数据结构

```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
	username: str = Field(regex='[0-9a-zA-Z]{3,20}')
	signup_time: datetime

print(UserSchema(username='bob', signup_time='2022-10-11 10:11:12'))
#> UserSchema(username='bob', signup_time=datetime.datetime(2022, 10, 11, 10, 11, 12))

try:
	UserSchema(username='@invalid', signup_time='2022-10-11 10:11:12')
except exc.ParseError as e:
	print(e)
	"""
	Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
	"""
```

### 解析函数参数与结果

```python
import utype
from typing import Optional

class PositiveInt(int, utype.Rule):  
    gt = 0

class ArticleSchema(utype.Schema):
	id: Optional[PositiveInt]
	title: str = Field(max_length=100)
	slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")

@utype.parse
def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
	return {
		'id': id,
		'title': title,
		'slug': '-'.join([''.join(
			filter(str.isalnum, v)) for v in title.split()]).lower()
	}

print(get_article('3', title=b'My Awesome Article!'))

try:
	get_article('-1')
except utype.exc.ParseError as e:
	print(e)

try:
	get_article(title='*' * 101)
except utype.exc.ParseError as e:
	print(e)
```


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


## 3. 文档指引

接下来我该阅读什么呢？

* Rule 类型约束：如果你需要继续探索能够为类型施加哪些约束（值，长度，正则，枚举等），可以阅读这一节
* Field 字段配置：如果你需要了解如何为字段指定不同的配置（可选，别名，模式，文档），可以阅读这一节
* Options 解析配置：如果你需要了解


* 如果你对 Python 的类型注解语法还不够了解，

* [Python typing 官方文档](https://docs.python.org/zh-cn/3/library/typing.html)