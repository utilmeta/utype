# Options - tuning parse
In utype, Options can be used to tune the parsing behavior of dataclasses and functions. In this document, we will explain its usage in detail.

## Type transform options

Type conversion (transformation) is the most critical part of data parsing, and Options provides some options to control the behavior of type conversion.

### Transforming preferences

* `no_explicit_cast`: no explicit type conversion, default is False

The meaning of no explicit type conversion is to try not to have unexpected type conversion, and the implementation will group the types according to primitive types.

1. `null`: None
2. `boolean`: 0, 1, True, False
3. `number`: int/float/decimal etc.
4. `string`: str/bytes/by tearray and binary bytes
5. `array`: list/tuple/set
6. `object`: dict/mapping

When `no_explicit_cast=True`, types in the same group can be converted to each other, and types in different groups cannot be converted to each other. However, there are some special cases. For example, `Decimal` (fixed-point number) allows conversion from `str`, because conversion from `float` number will be distorted; Types such as datetime also support conversion from date strings and timestamps because there is no more native type expression

As an example, utype allows string to list/dictionary conversions by default, provided certain patterns are met, such as
```python
from utype import type_transform

print(type_transform('[1,2,3]', list))
# > [1, 2, 3]
print(type_transform('{"value": true}', dict))
# > {'value': True}
```

However, such conversion is not allowed when `no_explicit_cast=True`
```python
from utype import type_transform, Options

try:
	type_transform('[1,2,3]', list, options=Options(no_explicit_cast=True))
except TypeError:
	pass

try:
	type_transform('{"value": true}', dict, options=Options(no_explicit_cast=True))
except TypeError:
	pass
	
print(type_transform((1, 2), list, options=Options(no_explicit_cast=True)))
# > [1, 2]
```

 * `no_data_loss`: disallow information loss during transformation, False by default

By default, we allow for the loss of information in type conversions, such as

```python
from utype import type_transform

print(type_transform("Some Value", bool))
# > True

print(type_transform(3.1415, int))
# > 3

from datetime import date
print(type_transform('2022-03-04 10:11:12', date))
# 2022-03-04
```

In these examples, the information of the input data is irreversibly compressed or lost during type conversion. If `no_data_loss=True`, these conversions with information loss will cause an error

```python
from utype import type_transform, Options

try:
	type_transform(3.1415, int, options=Options(no_data_loss=True))
except TypeError:
	pass
```

Only accept conversions without information loss, such as

 1. `bool`: Accepts `True` only, `False`, `0`, `1` and some strings that explicitly represent Boolean values, such as `'true'`, `'f'` `'no'`, etc.
 2. `int`: does not accept `float` or `Decimal` with significant decimal places
 3. `date`: does not accept conversions from `datetime` or strings containing hour, minute, and second parts

!!! note
	These above preferences is only the "flag" for transformer functions, Python itself does not have such mechanism to guarantee these conditions, instead they are implemented in the corresponding transformer functions, if you define or override a type transformer function, you should implement these preferences by youself

### Unknown types

If a type cannot find a matching converter in utype (including converters registered by the developer itself), it is called an unknown type. For the conversion of an unknown type (which does not match the input data), utype provides a configuration parameter in Options.

* `unresolved_types`: specifies the behavior for handling unknown types. It takes several values
	1. `'ignore'`: ignore, no longer convert, but directly use the input value as the result
	2. `'init'`: attempt to initialize an unknown type with `t(data)`
	3. `'throw'`: throw an error directly and do not convert any more. This option is the default.

```python
from utype import Schema, Options

class MyClass:  
    def __init__(self, value):  
        self.value = value  
          
class MySchema(Schema):  
    __options__ = Options(  
        unresolved_types='init',  
    )  
      
    inst: MyClass = None  
  
data = MySchema(inst=3)

print(data.inst.value)
# > 3
```


## Data processing options

Options provides some parameters for functions and dataclasses to tune the entire input data, including 

* `addition`: controls parameters beyond the declared scope, several options can be specified

	1. `None`: default option, directly ignored, without receiving and processing
	2. `True`: accept additional parameters as part of data
	3. `False`: disallow additional parameters. If input contains extra parameters, an error is thrown.
	4. `<type>`: specify a type to which the value of the extra parameter needs to be converted

Here is an example usage of `addition`.
```python
from utype import Schema, Options, exc

class User(Schema):  
    name: str  
    level: int = 0

data = {'name': 'Test', 'code': 'XYZ'}
print(dict(User.__from__(data)))   # default: addition=None
# > {'name': 'Test', 'level': 0}

user = User.__from__(data, options=Options(addition=True))
print(dict(user))
# > {'name': 'Test', 'level': 0, 'code': 'XYZ'}

try:
	User.__from__(data, options=Options(addition=False))
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['code'] exceeded
	"""
```

!!! note
	For function, you can accept additional params by declaring `**kwargs`, so unless you need to ban additional params with `addition=False`, there is no need to declare `addition` in function Options

* `max_depth`: limits the maximum depth of data nesting. This parameter is primarily used to limit self-referencing or circularly referenced data structures to avoid recursive stack overflows

```python
from utype import Schema, Options, exc

class Comment(Schema):  
    __options__ = Options(max_depth=3)  
    content: str  
    comment: 'Comment' = None  
  
comment = {'content': 'stuck'}  
comment['comment'] = comment 

try:  
    Comment(**comment)  
except exc.ParseError as e:  
    print(e)  
    """  
    parse item: ['comment'] failed:    
    parse item: ['comment'] failed:   
    parse item: ['comment'] failed: max_depth: 3 exceed: 4  
    """
```

In the example, we construct a self-referencing dictionary. If we keep parsing according to the data class declaration, we will continue parsing until Python throws a recursive error. We can control the maximum depth of parsing by limiting `max_depth`.

In addition, Options provides a limit adjustment that controls the number of input parameters.

* `max_params`: set the maximum number of parameters passed in
* `min_params`: set the minimum number of parameters passed in

These two options are often used when enabled `addition=True` to control the number of input parameters before parsing, so as to avoid consuming parsing resources due to too large input data.

```python
from utype import Schema, Options, exc

class Info(Schema):  
    __options__ = Options(  
        min_params=2,  
        max_params=5,  
        addition=True  
    )  
    version: str  
  
data = {  
    'version': 'v1',  
    'k1': 1,  
    'k2': 2,  
    'k3': 3  
}  
print(len(Info(**data)))
# > 4  

try:  
    Info(version='v1')
except exc.ParamsLackError as e:  
    print(e)  
    """
    min params num: 2 lacked: 1
    """

try:  
    Info(**data, k4=4, k5=5)
except exc.ParamsExceedError as e:  
    print(e)  
    """
    max params num: 5 exceed: 6
    """
```

As you can see, when the number of input parameters is less than `min_params`, the `exc.ParamsLackError` is thrown, and when the number of input parameters is greater than `max_params`, the `exc.ParamsExceedError` is thrown

**Distinction from length constraints**

Although you can also constrain the length of the dictionary using `min_length` and `max_length` from Rule, they are functionally different from `max_params`/ `min_params`:

`max_params` / `min_params` is the validation of the input data before all field parsing begins, in order to avoid consuming parsing resources because the input data is too large. And `max_length`/ `min_length` in the dataclass, is used to limit the length of the **output** data after all fields are parsed

And `max_params` / `min_params` can be used to restrict the input of function arguments, while `max_length` / `min_length` can only restrict normal types and dataclasses

## Error handling

Options provides a series of error handling options to control the behavior of parsing errors, including

* `collect_errors`: whether to collect all errors. The default is False.

When utype parses the parameters of dataclasses and functions, if it finds a invalid data (unable to complete type conversion or satisfy constraints) when `collect_errors=False`, it will directly throw the error as `exc.ParseError`, which is a “fail-fast” strategy.

But when `collect_errors=True`, utype will continue to parse and collect all the errors encountered. When the input data is done parsing, these errors will be combined to a `exc.CollectedParseError` and thrown out. All the input data error information can be obtained from this combined error.

```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    __options__ = Options(  
        addition=False,
        collect_errors=True
    )  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)  
  
form = {  
    'username': '@attacker',  
    'password': '12345',  
    'token': 'XXX'  
}

try:
	LoginForm(**form)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['token'] exceeded
	"""
	print(len(e.errors))
	# > 3
```

!!! note
	Of course, it will be a slightly cost for invalid inputs when `collect_errors=True`, so it is more recommended to turn on in debug only, for locating the errors more efficiently

* `max_errors`: In `collect_errors=True` mode, set a threshold for the number of errors. If the number of errors reaches this threshold, the collection will not continue, collected errors will be merged and thrown immediately.

```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    __options__ = Options(  
        addition=False,
        collect_errors=True,
        max_errors=2
    )  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)  
  
form = {  
    'username': '@attacker',  
    'password': '12345',  
    'token': 'XXX'  
}

try:
	LoginForm(**form)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	"""
	print(len(e.errors))
	# > 2
```

### Illegal data processing

Options also provides error handling for specific categories of elements.

* `invalid_items`: how to deal with illegal items in lists/sets/tuples.
* `invalid_keys`: how to deal with illegal keys in dictionary/mapping.
* `invalid_values`:  how to deal with illegal values in dictionary/mapping.

These configurations all have the same options.

1. `'throw'`: default value, throw error directly
2. `'exclude'`: strips illegal elements out of the data with a warning, but no error is thrown
3. `'preserve'`: left illegal elements in the data with a warning, but no error is thrown

Let’s look at an example in detail.
```python
from utype import Schema, Options, exc
from typing import List, Dict, Tuple

class IndexSchema(Schema):  
    __options__ = Options(  
        invalid_items='exclude',  
        invalid_keys='preserve',  
    )  
  
    indexes: List[int]  
    info: Dict[Tuple[int, int], int]  
  
data = {  
    'indexes': ['1', '-2', '*', 3],  
    'info': {  
        '2,3': 6,  
        '3,4': 12,  
        'a,b': '10'  
    }  
}

index = IndexSchema(**data)
# UserWarning: parse item: [2] failed: could not convert string to float: '*'
# UserWarning: parse item: ['a,b<key>'] failed: could not convert string to float: 'a'

print(index)
# > IndexSchema(indexes=[1, -2, 3], info={(2, 3): 6, (3, 4): 12, 'a,b': 10})
```

We specified `invalid_items='exclude'` in the Options of `IndexSchema`, so illegal elements in the list elements will be eliminated, such as the input `['1', '-2', '*', 3]` being converted to  `[1, -2, 3]`

We have also specified `invalid_keys='preserve'`,indicating that the dictionary key cannot be converted will be retained, so in `'info'` field of the input, the key that can complete the conversion is converted, and the key that cannot complete the conversion is also retained

!!! warning
	Unless you known what you are doing, do not use `'preserve'` in error configuration, for that will break the type-safe guarantee in the runtime

## Field behavior options

Options provides options to configure the behavior of the fields, including

* `ignore_required`: ignore required parameters, which make all parameters optional
* `no_default`: ignore default values. unprovided parameters will not appear in the data
* `force_default`: force to specified a default value
* `defer_default`: forcibly defer the calculation of the default value, corresponding to the `defer_default` in `Field` params
* `ignore_constraints`: ignore constraints validation, with type conversion only
* `immutable`: make all attributes of the dataclass immutable, that is, they cannot be assigned or deleted.

!!! warning
	`no_default`, `defer_default` and `immutable` only applies to dataclasses, which cannot use in function Options

* `ignore_delete_nonexistent`：In dataclass, you can use `del data.attr` to delete the `attr` attribute of data instance, if this attribute not exists, a `DeleteError` will be raised, or you can turn `ignore_delete_nonexistent=True` to ignore such error

> New in version 0.6.2

These options are not enabled by default. Enabling these options is equivalent to forcing the configuration value of the `Field`, so you can refer to [Field API References](/references/field)

## Field alias options

Options also provides some options for controlling field names and aliases

* `case_insensitive`: whether to accept parameters in a case-insensitive manner. The default is False.
* `alias_generator` specifies a function used to generate output aliases for fields that are not specified `alias`
* `alias_from_generator`: specifies a function used to generate input aliases for fields that are not specified `alias_from`
* `ignore_alias_conflicts`: whether to ignore alias conflicts in the input data. The default is False.


### Case style transformation

Different programming languages or developers may have different naming styles, so the API functions you provide may need to be converted from different naming styles.

For example, in Python, you typically use lowercase and underscore to name fields, and if your client needs to receive camelCase data, you typically need to declare it this way.

```python
from utype import Schema, Field

class ArticleSchema(Schema):
	slug: str
	liked_num: int = Field(alias='likedNum') 
	created_at: str = Field(alias='createdAt')
```


But because Options provides `alias_generator` options, you can specify an output alias conversion function utype for the entire dataclass, such as

```python
from utype import Schema
from utype.utils.style import AliasGenerator
from datetime import datetime

class ArticleSchema(Schema):
    __options__ = Schema.Options(
        alias_from_generator=[
            AliasGenerator.kebab,
            AliasGenerator.pascal,
        ],
        alias_generator=AliasGenerator.camel
    )

	slug: str
	liked_num: int
	created_at: datetime

data = {
	'Slug': 'my-article',                # pascal case
	'LikedNum': '3',                     # pascal case
	'created-at': '2022-03-04 10:11:12'  # kebab case
}
article = ArticleSchema(**data)
print(article)

print(dict(article))
# {
#	'slug': 'my-article',
#	'likedNum': 3,
#	'createdAt': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```

In order to make the naming style conversion more convenient, some commonly used alias generation functions that can generate various naming style fields have been provided in `utype.utils.style.AliasGenerator`.

* `camel`:  `camelCase` naming style
* `pascal`:  `PascalCase` naming style
* `snake`:  `snake_case` naming style, the recommended variable naming style for languages such as Python
* `kebab`:  `kebab-case` naming style
* `cap_snake`:  `CAP_SNAKE_CASE` naming style, often used for constant naming
* `cap_kebab`:  `CAP-KEBAB-CASE` naming style

You only need to use these functions to specify `alias_generator` or `alias_from_generator` to get the corresponding naming style conversion capabilities, such as the parsing option in the example specifies `alias_from_generator` `[AliasGenerator.kebab, AliasGenerator.pascal]`, which means it can convert from the input data in the kebab-case naming style and PascalCase naming style, and which `alias_generator=AliasGenerator.camel` means it will convert the output data to the camelCase style

So we can see that the naming style used for the input data in the example can be correctly recognized and accepted, the corresponding type conversion is completed and output to the target alias.
