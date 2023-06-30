# uType
[![Version](https://img.shields.io/pypi/v/utype)](https://pypi.org/project/utype/)
[![Python Requires](https://img.shields.io/pypi/pyversions/utype)](https://pypi.org/project/utype/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/utilmeta/utype/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/utilmeta/utype/test.yaml?branch=main&label=CI)](https://github.com/utilmeta/utype/actions?query=branch%3Amain+)
[![Test Coverage](https://img.shields.io/codecov/c/github/utilmeta/utype?color=green)](https://app.codecov.io/github/utilmeta/utype)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Downloads](https://pepy.tech/badge/utype/month)](https://pepy.tech/project/utype)

utype is a data types declaration & parsing library based on Python type annotations, 
enforce types and constraints for classes and functions at runtime

* Version: `0.3.3` [test]
* Author: [@voidZXL](https://github.com/voidZXL)
* License: Apache 2.0
* Source Code: [https://github.com/utilmeta/utype](https://github.com/utilmeta/utype)
* Documentation: [https://utype.io](https://utype.io)
* 中文文档: [https://utype.io/zh](https://utype.io/zh)


### Core Features

* Enforce types, data classes, function params and result parsing at runtime based on Python type annotation
* Support a variety of constraints, logical operators and flexible parsing options
* Highly extensible, all type transformer can be register, extend and override

### Installation

```shell
pip install -U utype
```

utype requires Python >= 3.7

### Usage Example

### Types and constraints
The utype support to add constraints on types, such as
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
    Constraint: 0 violated
    """
``` 


Data that conforms to the type and constraints will complete the conversion, otherwise will throw a parse error indicating what went wrong

### Parsing dataclasses

utype supports the "dataclass" usage that convert a dict or JSON to a class instance, similar to `pydantic` and `attrs`
```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')
    signup_time: datetime

# 1. Valid input
data = {'username': 'bob', 'signup_time': '2022-10-11 10:11:12'}
print(UserSchema(**data))
#> UserSchema(username='bob', signup_time=datetime.datetime(2022, 10, 11, 10, 11, 12))

# 2. Invalid input
try:
    UserSchema(username='@invalid', signup_time='2022-10-11 10:11:12')
except exc.ParseError as e:
    print(e)
    """
    parse item: ['username'] failed: 
    Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
    """
```

After a simple declaration, you can get

* Automatic `__init__` to take input data, perform validation and attribute assignment
* Providing  `__repr__` and `__str__` to get the clearly print output of the instance
* parse and protect attribute assignment and deletion to avoid dirty data

### Parsing functions

utype can also parse function params and result
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
    parse item: ['id'] failed: Constraint: : 0 violated
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
    You can easily get type checking and code completion of IDEs (such as Pycharm, VS Code) during development

utype supports not only normal functions, but also generator functions, asynchronous functions, and asynchronous generator functions with the same usage
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
    The `AsyncGenerator` type is used to annotate the return value of the asynchronous generator, which has two parameters: the type of the value output by `yield`, type of the value sent by `asend`

As you can see, the parameters passed to the function and the value received from `yield` were all converted to the expected type as declared


### Logical operation of type
utype supports logical operations on types and data structures using Python-native logical operators
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

The example uses the `^` exclusive or symbol to logically combine  `User` and `Tuple[str, int]`, and the new logical type gains the ability to convert data to one of those

### Register transformer for type
Type transformation and validation strictness required by each project may be different, so in utype, all types support registraton, extension and override, such as
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

You can register transformers not only for custom types, but also for basic types (such as `str`, `int`, etc.) Or types in the standard library (such as `datetime`, `Enum`, etc.) To customize the conversion behavior

## RoadMap and Contribution
The utype is still growing, and the following features are planned for implementation in the new version

* Support the generation of input and output template documents in json-schema format
* Improve the handling mechanism of parsing errors, including error handling hook functions, etc.
* Support parsing and management of environment variables and configuration files
* Support the declaration and resolution of command line parameters
* Support for Python generics, type variables, and more type annotation syntax
* Develop Pycharm/VS Code plugin that supports IDE detection and hints for constraints, logical types, and nested types

You are also welcome to contribute features or submit issues.


## Community

* Twitter: <a href="https://twitter.com/utype_io" target="_blank">utype_io</a>
* Discord: <a href="https://discord.gg/d98ndkNA77"  target="_blank">utype</a>
* Email: dev@utype.io
