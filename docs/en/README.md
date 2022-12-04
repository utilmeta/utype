# uType - Introduction

<a href="https://pypi.org/project/utype/" target="_blank">
<img src="https://img.shields.io/pypi/v/utype" alt="">
</a>
<a href="https://github.com/utilmeta/utype/blob/main/LICENSE" target="_blank">
<img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="">
</a>

utype is a data type declaration and analysis library based on Python type annotations, which can analyze and transform data at runtime according to the type and data structure you declare

* Version: `0.2.0` [testing]
* Author: @voidZXL (<a href="https://github.com/voidZXL" target="_blank">https://github.com/voidZXL</a>)
* License: Apache 2.0
* Code Repository: <a href="https://github.com/utilmeta/utype" target="_blank">https://github.com/utilmeta/utype</a>

## Motivation

At present, Python does not have a mechanism to check type and validate constraints at runtime, so when we write a function, we often need to perform type assertion and constraint checking before we can actually start writing real logic, otherwise it is likely to be An exception error occurs at runtime, such as
```python
def login(username, password):
     import re
     if not isinstance(username, str) \
             or not re.match('[0-9a-zA-Z]{3,20}', username):
         raise ValueError('Bad username')
     if not isinstance(password, str)\
             or len(password) < 6:
         raise ValueError('Bad password')
     # The following is your real processing logic
```

But if we can declare all the types and constraints in the parameters in advance, verify them when calling, and directly throw a highly readable error for the parameters that cannot complete the type conversion or fail the constraint verification, like
```python
import utype

@utype.parse
def login(
    username: str = utype.Field(regex='[0-9a-zA-Z]{3,20}'),
    password: str = utype. Field(min_length=6)
):
    # You can start writing logic directly
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

and you can get

* Type checking, code completion, etc. from the IDE improve development efficiency and reduce the chance of bugs
* Eliminate all type conversion and validation work, and get standard highly readable error messages to locate problems
* The types and constraints of parameters are clearly visible to the caller, which improves the efficiency of collaborative development

## Core Features

* Analyze and transform types, data structures, function parameters and results at runtime based on Python type annotations
* Support type constraints, type logical operations, etc., to declare more complex parsing conditions
* Highly extensible, all types of conversion functions can be registered, covered and extended, and provide highly flexible analysis options
* Support outputting documents in json-schema format, compatible with OpenAPI

## Installation

```shell
pip install -U utype
```

!!! note
    utype requires Python >= 3.7, no other third-party dependencies required

!!! warning
    If you see this prompt, you are welcome to become a user of the beta version of utype. At present, utype is still in the beta stage. There may be some functions that have not been tested, and the API may change in the future. Please be cautious when using it in a production environment, and enjoy~

## Example Usage

### Types and constraints
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

Data that conforms to the type and constraint declaration will complete the conversion successfully, data that does not will throw a parse error indicating what went wrong

### Transform data structure
```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')
    signup_time: datetime

data = {'username': 'bob', 'signup_time': '2022-10-11 10:11:12'}
print(UserSchema(**data))
#> UserSchema(username='bob', signup_time=datetime. datetime(2022, 10, 11, 10, 11, 12))

try:
    UserSchema(username='@invalid', signup_time='2022-10-11 10:11:12')
except exc.ParseError as e:
    print(e)
    """
    parse item: ['username'] failed:
    Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
    """
```


### Parse function parameters and results
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
    Using this usage, you can easily get type checking and code completion of IDEs (such as Pycharm, VS Code) during development

utype not only supports parsing ordinary functions, but also supports generator functions, asynchronous functions and asynchronous generator functions. Their usage is consistent, and only the corresponding type annotations need to be correctly declared
```python
import utype
import asyncio
from typing import AsyncGenerator

@utype.parse
async def waiter(rounds: int = utype. Field(gt=0)) -> AsyncGenerator[int, float]:
     assert isinstance(rounds, int)
     i = rounds
     while i:
         wait = yield str(i)
         if wait:
             assert isinstance(wait, float)
             print(f'sleep for: {wait} seconds')
             await asyncio. sleep(wait)
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
     asyncio. run(wait())
```

!!! note
    The `AsyncGenerator` type is used to annotate the return value of the asynchronous generator, which has two parameters, the first represents the type of the value output by `yield`, and the second represents the type of the value sent by `asend`

It can be seen that although we have used characters and other types in passing parameters and `yield`, they are all converted to the desired number type according to the declaration (of course, an error will be thrown when the conversion cannot be completed)

## Roadmap & contribution


## Community

* discord: 
* email: dev@utype.io