# uType - 介绍

<a href="https://pypi.org/project/utype/" target="_blank">
	<img src="https://img.shields.io/pypi/v/utype" alt="">
</a>
<a href="https://github.com/utilmeta/utype/blob/main/LICENSE" target="_blank">
	<img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="">
</a>

utype 是一个基于 Python 类型注解的数据类型声明与解析库，能够在运行时根据你声明的类型和数据结构对数据进行解析转化

* 版本：`0.2.0`【测试】
* 作者：周煦林（<a href="https://github.com/voidZXL" target="_blank">https://github.com/voidZXL</a>）
* 协议：Apache 2.0
* 开源仓库：<a href="https://github.com/utilmeta/utype" target="_blank">https://github.com/utilmeta/utype</a>

## 需求动机

目前 Python 没有在运行时解析类型与校验约束的机制，所以当我们编写一个函数时，往往需要先对参数进行类型断言，约束校验等操作，然后才能开始编写真正的逻辑，否则很可能会在运行时发生异常错误，如
```python
def login(username, password):  
    import re  
    if not isinstance(username, str) \  
            or not re.match('[0-9a-zA-Z]{3,20}', username):  
        raise ValueError('Bad username')  
    if not isinstance(password, str) \  
            or len(password) < 6:  
        raise ValueError('Bad password')  
    # 下面才是你真正的处理逻辑
```

但如果我们能够提前把所有的类型和约束都在参数中声明出来，在调用时就进行校验，对无法完成类型转化或不通过约束校验的参数直接抛出一个高可读性的错误，如
```python
import utype

@utype.parse
def login(
	username: str = utype.Field(regex='[0-9a-zA-Z]{3,20}'),
	password: str = utype.Field(min_length=6)
):
	# 你可以直接开始编写逻辑了
	return username, password

print(login(b'abc', 123456))
('abc', '123456')

try:
	login('@invalid', 123456)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: 
	Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
	"""
```

这样我们就可以获得

* 来自 IDE 的类型检查，代码补全等，提高了开发效率，还减少了产生 bug 的机会
* 省去所有的的类型转化与校验工作，并且获得标准的高可读性的报错信息来定位问题
* 对调用者清晰可见参数的类型和约束，提高了协作开发的效率

## 核心特性

* 基于 Python 类型注解在运行时对类型，数据结构，函数参数与结果等进行解析转化
* 支持类型约束，类型的逻辑运算等，以声明更复杂的解析条件
* 高度可扩展，所有类型的转化函数都可以注册，覆盖与扩展，并提供高度灵活的解析选项
* 支持输出 json-schema 格式的文档，兼容 OpenAPI 

## 安装

```shell
pip install -U utype
```

!!! note
	utype 需要 Python >= 3.7，无其他第三方依赖

!!! warning
	如果你看到这条提示，欢迎你成为 utype 的测试版本用户，目前 utype 还处于测试阶段，可能存在一些功能没有被测试到，API 也有可能会在未来发生变动，请谨慎用于生产环境，and enjoy~

## 用法示例

### 类型与约束
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

符合类型和约束声明的数据会成功完成转化，不符合的数据会抛出一个指示哪里出现问题的解析错误

### 转化数据结构
```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
	username: str = Field(regex='[0-9a-zA-Z]{3,20}')
	signup_time: datetime

data = {'username': 'bob', 'signup_time': '2022-10-11 10:11:12'}
print(UserSchema(**data))
#> UserSchema(username='bob', signup_time=datetime.datetime(2022, 10, 11, 10, 11, 12))

try:
	UserSchema(username='@invalid', signup_time='2022-10-11 10:11:12')
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: 
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
#> ArticleSchema(id=3, title='My Awesome Article!', slug='my-awesome-article')

try:
	get_article('-1')
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['id'] failed: Constraint: <gt>: 0 violated
	"""

try:
	get_article(title='*' * 101)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['<return>'] failed: 
	parse item: ['title'] failed: 
	Constraint: <max_length>: 100 violated
	"""
```

!!! success
	使用这样的用法你可以在开发中轻松获得 IDE （如  Pycharm, VS Code）的类型检查与代码补全

utype 不仅支持解析普通函数，还支持生成器函数，异步函数和异步生成器函数，它们的用法都是一致的，只需要正确地声明对应的类型注解
```python
import utype  
import asyncio  
from typing import AsyncGenerator  

@utype.parse  
async def waiter(rounds: int = utype.Field(gt=0)) -> AsyncGenerator[int, float]:  
    assert isinstance(rounds, int)  
    i = rounds  
    while i:  
        wait = yield str(i)  
        if wait:  
            assert isinstance(wait, float)  
            print(f'sleep for: {wait} seconds')
            await asyncio.sleep(wait)  
        i -= 1  
  
async def wait():  
    wait_gen = waiter('2')  
    async for index in wait_gen:  
        assert isinstance(index, int)  
        try:  
            await wait_gen.asend(b'0.5')  
            # sleep for: 0.5 seconds  
        except StopAsyncIteration:  
            return  
  
if __name__ == '__main__':  
    asyncio.run(wait())
```

!!! note
	`AsyncGenerator` 类型用于注解异步生成器的返回值，其中有两个参数，第一个表示 `yield` 出的值的类型，第二个表示 `asend` 发送的值的类型

可以看到，虽然我们在传参和 `yield` 中使用了字符等类型，它们全部都按照声明转化为了期望的数字类型（当然在无法完成转化时会抛出错误）


### 类型的逻辑运算
utype 支持使用 Python 原生的逻辑运算符对类型与数据结构进行逻辑运算
```python
from utype import Rule, exc

class PositiveInt(int, Rule):  
    gt = 0

class Month(PositiveInt):  
    le = 12

month_or_none = Month | None
print(month_or_none('11.1'))
# > 11
assert month_or_none(None) is None

try:
	month_or_none('abc')
except exc.ParseError as e:
	print(e)
	"""
	CollectedParseError: could not convert string to float: 'abc';
	"""
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

print(dict(ArticleSchema(slug=b'My Awesome Article!')))
# > {'slug': 'my-awesome-article'}
```

!!! note
	注册转换器并没有影响类的 `__init__` 方法的行为，所以直接调用 `Slug(value)` 并不会生效

你不仅可以为自定义类型注册转化器，还可以为基本类型（如 str, int, bool 等）或标准库中的类型（如 datetime, Enum 等）注册转化器函数，来自定义其中的转化行为

!!! note
	`utype` 提供的是 **运行时** 提供的类型解析能力，也就是说它不能（也没有必要）让 Python 像静态语言一样在程序启动时就能够分析所有的类型与调用是否正确


## RoadMap 与贡献
utype 还在成长中，目前规划了以下将在新版本中实现的特性

* 完善解析错误的处理机制，包括错误处理钩子函数等
* 支持命令行参数的声明与解析
* 支持 Python 泛型，类型变量等更多类型注解语法
* 开发 Pycharm / VS Code 插件，支持对约束，逻辑类型和嵌套类型的 IDE 检测与提示
* 从 json-schema 生成 utype 数据类代码

也欢迎你来贡献 feature 或者提交 issue ~

## 用户交流与答疑

中文答疑 QQ 群：183623597

<img style="width: 300px" src="https://utype.io/assets/qq-group.jpg" alt="">