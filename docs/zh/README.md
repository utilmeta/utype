# uType - 介绍

<a href="https://pypi.org/project/utype/" target="_blank">
	<img src="https://img.shields.io/pypi/v/utype" alt="">
</a>
<a href="https://pypi.org/project/utype/" target="_blank">
	<img src="https://img.shields.io/pypi/pyversions/utype" alt="">
</a>
<a href="https://github.com/utilmeta/utype/blob/main/LICENSE" target="_blank">
	<img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="">
</a>
<a href="https://github.com/utilmeta/utype/actions?query=branch%3Amain+" target="_blank">
	<img src="https://img.shields.io/github/actions/workflow/status/utilmeta/utype/test.yaml?branch=main&label=CI" alt="">
</a>
<a href="https://app.codecov.io/github/utilmeta/utype" target="_blank">
	<img src="https://img.shields.io/codecov/c/github/utilmeta/utype?color=green" alt="">
</a>


utype 是一个基于 Python 类型注解的数据类型声明与解析库，能够在运行时根据你的声明对类与函数的参数进行解析转化

* 版本：`0.3.4`【测试】
* 作者：<a href="https://github.com/voidZXL" target="_blank">@voidZXL</a>
* 协议：Apache 2.0
* 代码：<a href="https://github.com/utilmeta/utype" target="_blank">https://github.com/utilmeta/utype</a>

## 需求动机

目前 Python 没有在运行时解析类型与校验约束的机制，所以当我们编写一个函数时，往往需要先对参数进行类型断言和约束校验等操作，然后才能开始编写真正的逻辑，否则很可能会在运行时发生异常错误，如
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

但如果我们能够把类型和约束都在参数中声明出来，在调用时就进行校验，对非法参数直接抛出错误，如
=== "使用 Annotated"  
	```python
	import utype
	from utype.types import Annotated
	
	@utype.parse
	def login(
		username: Annotated[str, utype.Param(regex='[0-9a-zA-Z]{3,20}')],
		password: Annotated[str, utype.Param(min_length=6)]
	):
		# 你可以直接开始编写逻辑了
		return username, password
	
	print(login('alice', 123456))
	('alice', '123456')
	
	try:
		login('@invalid', 123456)
	except utype.exc.ParseError as e:
		print(e)
		"""
		parse item: ['username'] failed: 
		Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
		"""
	```

=== "使用默认值"
	```python
	import utype
	
	@utype.parse
	def login(
		username: str = utype.Param(regex='[0-9a-zA-Z]{3,20}'),
		password: str = utype.Param(min_length=6)
	):
		# 你可以直接开始编写逻辑了
		return username, password
	
	print(login('alice', 123456))
	('alice', '123456')
	
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

## 安装

```shell
pip install -U utype
```

!!! note
	utype 需要 Python >= 3.7

!!! warning
	如果你看到这条提示，欢迎你成为 utype 的测试版本用户，目前 utype 还处于测试阶段，可能存在一些功能没有被测试到，API 也有可能会在未来发生变动，请谨慎用于生产环境，and enjoy~

## 用法示例

### 类型与约束

utype 支持方便地为类型施加约束，你可以使用常用的约束条件（比如大小，长度，正则等）构造约束类型
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

在调用约束类型时，符合类型和约束声明的数据会成功完成转化，不符合的数据会抛出一个解析错误，用于指示哪里出了问题

### 解析 JSON 数据

utype 支持将字典或 JSON 数据转化为类实例，类似于 `pydantic` 和 `attrs` ，如
```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
	username: str = Field(regex='[0-9a-zA-Z]{3,20}')
	signup_time: datetime

# 1. 正常输入
data = {'username': 'bob', 'signup_time': '2022-10-11 10:11:12'}
print(UserSchema(**data))
#> UserSchema(username='bob', signup_time=datetime.datetime(2022, 10, 11, 10, 11, 12))

# 2. 异常输入
try:
	UserSchema(username='@invalid', signup_time='2022-10-11 10:11:12')
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: 
	Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
	"""
```

在简单的声明后，你就可以获得

* 无需声明 `__init__` 便能够接收对应的参数，并且完成类型转化和约束校验
* 提供清晰可读的 `__repr__` 与 `__str__` 函数使得在输出和调试时方便直接获得内部的数据值
* 在属性赋值或删除时根据字段的类型与配置进行解析与保护，避免出现脏数据

### 解析函数参数与结果

utype 提供了函数解析的机制，你只需要把函数参数的类型与配置声明出来，就可以在函数中拿到类型安全，约束保障的参数值，函数的调用者也能够获得满足返回类型声明的结果
```python
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

utype 不仅支持解析普通函数，还支持解析生成器函数，异步函数和异步生成器函数，它们的用法都是一致的，只需要正确地进行类型注解
```python
import utype  
import asyncio  
from typing import AsyncGenerator  

@utype.parse  
async def waiter(rounds: int = utype.Param(gt=0)) -> AsyncGenerator[int, float]:  
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
from utype import Schema, Field
from typing import Tuple

class User(Schema):  
    name: str = Field(max_length=10)  
    age: int

one_of_user = User ^ Tuple[str, int]

print(one_of_user({'name': 'test', 'age': '1'}))
# > User(name='test', age=1)

print(one_of_user([b'test', '1']))
# > ('test', 1)
```

例子中使用了 `^` 异或符号对 utype 数据类 `User` 和嵌套类型 `Tuple[str, int]` 进行逻辑组合，组合得到的逻辑类型就可以转把数据转化为 `User` 或 `Tuple[str, int]` 实例

### 类型的注册扩展
由于每个项目需要的类型转化方式和校验严格程度可能不同，在 utype 中，所有的类型都是支持自行注册和扩展转化函数，如
```python
from utype import Rule, Schema, register_transformer
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

你不仅可以为自定义类型注册转化器，还可以为基本类型（如 `str`, `int` 等）或标准库中的类型（如 `datetime`, `Enum` 等）注册转化器函数，来自定义其中的转化行为

!!! note
	`utype` 提供的是 **运行时** 提供的类型解析能力，也就是说它不能（也没有必要）让 Python 像静态语言一样在程序启动时就能够分析所有的类型与调用是否正确


## RoadMap 与贡献
utype 还在成长中，目前规划了以下将在新版本中实现的特性

* 支持生成 json-schema 格式的输入输出模板文档
* 完善解析错误的处理机制，包括错误处理钩子函数等
* 支持环境变量和配置文件的解析和管理
* 支持命令行参数的声明与解析
* 支持 Python 泛型，类型变量等更多类型注解语法
* 开发 Pycharm / VS Code 插件，支持对约束，逻辑类型和嵌套类型的 IDE 检测与提示

也欢迎你来贡献 feature 或者提交 issue ~

## 用户交流与答疑

中文交流 QQ 群：183623597

<img style="width: 300px" src="https://utype.io/assets/qq-group.jpg" alt="">
