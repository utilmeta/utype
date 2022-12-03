# uType
[![Version](https://img.shields.io/pypi/v/utype)](https://pypi.org/project/utype/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/utilmeta/utype/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

utype is a data type & schema declaration & parsing library based on Python type annotations, enforce type and constraints at runtime

* Version: `0.2.0` [test]
* Author: @voidZXL
* License: Apache 2.0
* Documentation: [https://utype.io](https://utype.io)
* 中文文档: [https://utype.io/zh](https://utype.io/zh)


### Core Features

* Enforce types, data classes, function params and result parsing at runtime based on Python type annotation
* Support a variety of constraints, logical operator and flexible parsing options
* Highly extensible, all type transformer can be register, extend and override
* Support JSON-Schema documentation with OpenAPI compatibility

### Installation

```shell
pip install -U utype
```

utype requires Python >= 3.7

### Usage Example

### Basic Types & Constraints
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


### Data Class

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


### RoadMap & Contribution


### Licence

Apache 2.0