# uType - Introduction

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

utype is a data type declaration and parsing library based on Python type annotations, which can parse and convert data according to your declared type and data structure at runtime

* Version: `0.2.1` [Test]
* Author: <a href="https://github.com/voidZXL" target="_blank">@voidZXL</a>
* License: Apache 2.0
* Code Repository: <a href="https://github.com/utilmeta/utype" target="_blank">https://github.com/utilmeta/utype</a>

## Motivation

Currently, Python does not have a mechanism to resolve types and check constraints at runtime, so when we write a function, we often need to perform type assertion, constraint checking and other operations on the parameters before we can start writing the real logic. Otherwise, an exception may occur at runtime, such as
```python
def login(username, password):  
    import re  
    if not isinstance(username, str) \  
            or not re.match('[0-9a-zA-Z]{3,20}', username):  
        raise ValueError('Bad username')  
    if not isinstance(password, str) \  
            or len(password) < 6:  
        raise ValueError('Bad password')  
    # below is your actual logic
```

However, if we can declare all types and constraints in the parameters in advance, we can check them at the time of calling, and throw a high-readability error directly for parameters that cannot complete type conversion or do not pass constraint checking, such as
```python
import utype

@utype.parse
def login(
	username: str = utype.Param(regex='[0-9a-zA-Z]{3,20}'),
	password: str = utype.Param(min_length=6)
):
	# you can directly start coding
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

In this way we can obtain

* Type checking, code completion, etc. From IDEs improve development efficiency and reduce the chance of bugs.
* Eliminate all the type conversion and verification work, and get the standard high-readability error message to locate the problem.
* The types and constraints of parameters are clearly visible to callers, which improves the efficiency of collaborative development.

## Core features

* Parse and convert types, data classes, function parameters and results at runtime based on Python type annotations
* Support for type constraints, logical operations on types, etc. To declare more complex parsing conditions
* Highly extensible, all types of conversion functions can be registered, overridden, and extended, and provide highly flexible parsing options

## Installation

```shell
pip install -U utype
```

!!! note
    utype requires Python >= 3.7

!!! warning
    If you see this prompt, you are welcome to become a user of the beta version of utype. At present, utype is still in the beta stage. There may be some functions that have not been tested, and the API may change in the future. Please be cautious when using it in a production environment, and enjoy~

## Usage examples

### Types and constraints

The utype support makes it easy to impose constraints on types, and you can use common constraints to construct arbitrary constraint types.
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
    Constraint: : 0 violated
    """
``` 


Data that conforms to the type and constraint declaration will complete the conversion successfully, data that does not will throw a parse error indicating what went wrong

### Parse classes

utype supports the resolution of fields declared in classes in a manner similar to `pydantic` and `attrs`
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

After a simple declaration, you can obtain

* The corresponding parameters can be received without declaration `__init__`, and the type conversion and constraint verification are completed.
* Providing clearly readable `__repr__` and `__str__` functions makes it easy to get the internal data values directly during output and debugging.
* When assigning or deleting an attribute, perform analysis and protection according to the type and configuration of the field to avoid dirty data

### Parse functions

utype provides a function parsing mechanism. You only need to declare the type and configuration of the function parameter, and then you can get the type-safe and constraint-guaranteed parameter value in the function, and the caller can also get the result that meets the declared return type
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
    Using this usage, you can easily get type checking and code completion of IDEs (such as Pycharm, VS Code) during development

The utype supports not only the parsing of normal functions, but also generator functions, asynchronous functions, and asynchronous generator functions. Their usage is the same, and only the corresponding type annotations need to be declared correctly.
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
    The `AsyncGenerator` type is used to annotate the return value of the asynchronous generator, which has two parameters, the first represents the type of the value output by `yield`, and the second represents the type of the value sent by `asend`

As you can see, even though we used types such as character in passing parameters and `yield`, they were all converted to the expected numeric type as declared (of course, an error was thrown if the conversion could not be completed).


### Logical operation of type
Utype supports logical operations on types and data structures using Python-native logical operators
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

The example uses the `^` exclusive or symbol to logically combine the utype data class and the typing nested type, and the new logical type gains the ability to convert data to one of these declarations

### Register transformer for type
Type transformation and validation strictness required by each project may be different, so in utype, all types support self-registration and extended conversion functions, such as
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

* twitter: <a href="https://twitter.com/utype_io" target="_blank">utype_io</a>
* email: dev@utype.io