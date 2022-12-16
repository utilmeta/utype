# Options - tuning parse
In utype, Options can be used to manipulate the parsing behavior of data classes and functions. In this document, we will explain its usage in detail.

## Type transform options

Type conversion is the most critical part of data parsing, and Options provides some options to control the behavior of type conversion.

### Transforming preferences

*  `no_explicit_cast`: No explicit type conversion, default is False

The meaning of no explicit type conversion is to try not to have unexpected type conversion, and the implementation will group the types according to the basic types.

1.  `null`：None
2.  `boolean`：0，1, True, False
3.  `number`: int/float/decimal etc.
4. Strings such as `string`: str/bytes/by tearray and binary bytes
5.  `array`：list/tuple/set
6.  `object`：dict/mapping

When this option is enabled, types in the same group can be converted to each other, and types in different groups cannot be converted to each other. However, there are some special cases. For example, Decimal (fixed-point number) allows conversion from str, because conversion from floating-point number will be distorted; Types such as datetime also support conversion from date strings and timestamps because there is no more native type expression

As an example, utype allows string to list/dictionary conversions by default, provided certain patterns are met, such as
```python
from utype import type_transform

print(type_transform('[1,2,3]', list))
# > [1, 2, 3]
print(type_transform('{"value": true}', dict))
# > {'value': True}
```

However, such conversion is not allowed after the parameter is turned on `no_explicit_cast`
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
# [1, 2]
```

 *  `no_data_loss`: No information loss, False by default

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

In these examples, the information of the input data is irreversibly compressed or lost during type conversion. If enabled `no_data_loss`, these conversions with information loss will report an error

```python
from utype import type_transform, Options

try:
	type_transform(3.1415, int, options=Options(no_data_loss=True))
except TypeError:
	pass
```

Only accept conversions without information loss, such as

 1.  `bool`: Accepts `True` only, `False`, `0`, `1` and some strings that explicitly represent Boolean values, such as `'true'`, `'f'` `'no'`, etc.
 2.  `int`: does not accept sums with significant decimal places
 3.  `date`: does not accept conversions from `datetime` or strings containing hour, minute, and second parts

!!! note

### unknown types

If a type cannot find a matching converter in utype (including converters registered by the developer itself), it is called an unknown type. For the conversion of an unknown type (which does not match the input data), utype provides a configuration parameter bit in the resolution option Options.

*  `unresolved_types` Specifies the behavior for handling unknown types. It takes several values
	  1. `'ignore'`: Ignore, no longer convert, but directly use the input value as the result
	  2. `'init'`: Attempt to initialize an unknown type with `t(data)`
	  3. `'throw'`: Throw an error directly and do not convert any more. This option is the default.

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
  
data = MySchema(cls=3)

print(data.inst.value)
# > 3
```

### Customize transformer

In utype, there is a transformer class TypeTransformer, which is responsible for type conversion, and you can extend and customize it by inheriting from it.

```python
from utype import TypeTransformer

class MyTransformer(TypeTransformer):
	def __call__(self, data, t: type):
		# your custom logic
		pass
```

Options provides an argument to specify a converter class.

*  `transformer_cls`: Specify a converter class. The function or data class to which the parse option applies will use the entire class to convert the type.

## Data processing options

Options provides options for conditioning or instrumenting the parameters of functions and the input data of data classes, including

*  `addition` Controls parameters that go beyond the declared scope. Several options can be specified

	1. `None`: Default option, directly ignored, without receiving and processing
	2. `True`: Accept additional parameters
	3. `False`: Suppresses extra parameters. If extra parameters are included in the input, an error is thrown.
	4. `<type>`: Specify a type to which the value of the extra parameter needs to be converted

Here is an example `addition` of the usage of.
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


*  `max_depth`: Limits the maximum depth of data nesting. This parameter is primarily used to limit self-referencing or circularly referenced data structures to avoid recursive stack overflows

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

In the example, we construct a self-referencing dictionary. If we keep parsing according to the data class declaration, we will continue parsing until Python throws a recursive error. We can control the maximum depth of parsing by limiting it `max_depth`.


In addition, Options provides a limit adjustment that controls the number of incoming parameters.

*  `max_params`: Set the maximum number of parameters passed in
*  `min_params`: Set the minimum number of parameters passed in

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

As you can see, when the number of input parameters is less than `min_params`, the `exc.ParamsLackError` is thrown, and when the number of input parameters is greater than `max_params`, the is thrown

**Distinction from length constraint**

Although you can also constrain the length of the dictionary using the sum `min_length` of the Rule constraint parameters `max_length`, they are functionally different from `max_params`/ `min_params`.

`max_params`/ `min_params` is the verification of the input data before all field parsing begins, `max_params` in order to avoid consuming parsing resources because the input data is too large. And `max_length`/ `min_length`, in the data class, is used to limit ** Output ** the length of the data after all fields are parsed

And `max_params`/ `min_params` can be used to restrict the input of function arguments, `max_length`/ `min_length` can only restrict normal types and data classes


## Error handling

Options provides a series of error handling options to control the behavior of parsing errors, including

*  `collect_errors`: Whether to collect all errors. The default bit is False.

When utype parses the parameters of data classes and functions, if it finds the wrong data (unable to complete type conversion or satisfy constraints) `collect_errors=False`, it will directly throw the error as `exc.ParseError` a “quick failure” strategy.

But at `collect_errors=True` that time, utype will continue to parse and collect the errors encountered. When the input data is parsed, these errors will be combined `exc.CollectedParseError` and thrown out. All the input data error information can be obtained from this combined error.

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


*  `max_errors`: In the collection error `collect_errors=True` mode, set a threshold for the number of errors. If the number of errors reaches this threshold, the collection will not continue, but the current error will be merged and thrown directly.

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

In addition to a holistic error policy, Options also provides error handling policies for different types of elements.

*  `invalid_items`: For tuples in lists/sets/tuples, how to dispose of illegal elements in them
*  `invalid_keys`: For a key in a dictionary/map, how to dispose of illegal elements in it
*  `invalid_values`: For values in the dictionary/map, how to dispose of illegal elements in them

These configurations all have the same options.

1.  `'throw'`: Default value, throw error directly
2.  `'exclude'`: Strips illegal elements out of the data, warning only but not throwing an error
3.  `'preserve'` The illegal element is left as a warning but no error is thrown

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

We specified `invalid_items='exclude'` in the parsing options of the Index Schema declaration for the data class, so illegal elements in the list elements will be eliminated, such as the input `['1', '-2', '*', 3]` being converted to

We have also specified `invalid_keys='preserve'` that the dictionary key indicating that the conversion cannot be completed will be retained, so in the data of the field we input `'info'`, the key value that can complete the conversion is converted, and the key value that cannot complete the conversion is also retained

!!! warning

## Field behavior options

Options provides options to adjust the behavior of the field

*  `ignore_required`: Ignore required parameters, that is, make all parameters optional
* Default values are `no_default` ignored. Unsupplied parameters do not appear in the data.
*  `force_default` Force a default value to be specified
*  `defer_default`: Forcibly defer the calculation of the default value, corresponding to the
*  `ignore_constraints`: Ignore constraint validation, type conversion only
*  `immutable` Make all attributes of the data class immutable, that is, they cannot be assigned or deleted.

!!! warning

These options are not enabled by default. Enabling these options is equivalent to forcing the configuration value of the field, so you can refer to the relevant usage.

## Field Alias Option

Options also provides some options for controlling field names and aliases

*  `case_insensitive`: Whether to accept parameters in a case-insensitive manner. The default is False.
*  `alias_generator` Specifies a function used to generate output aliases for fields that are not specified `alias`
*  `alias_from_generator` Specifies a function used to generate input aliases for fields that are not specified `alias_from`
*  `ignore_alias_conflicts`: Whether to ignore alias conflicts in the input data. The default is False.


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


But because Options provides `alias_generator` options, you can specify an output alias conversion function utype for the entire data class. In order to make the naming style conversion more convenient, some commonly used alias generation functions that can generate various naming style fields have been provided in `utype.utils.style.AliasGenerator`.

*  `camel`: Hump naming style, such as
*  `pascal` Pascal naming style, or capitalized hump naming, as in
*  `snake` Lowercase underscore naming style, the recommended variable naming style for languages such as python, such as
*  `kebab`: Lowercase dash naming style, such as
*  `cap_snake`: Uppercase underscore naming style, often used for constant naming, such as
*  `cap_kebab`: capital dash naming style, such as

You only need to use these functions to specify `alias_generator` or `alias_from_generator` to get the corresponding naming style conversion capabilities, such as

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

The parsing option in the example specifies `alias_from_generator` `[AliasGenerator.kebab, AliasGenerator.pascal]`, which means it can convert from the input data in the lowercase dash naming style and the capitalized hump naming style, and which `alias_generator=AliasGenerator.camel` means it will convert the output data to the hump naming style

So we can see that the naming style used for the input data in the example can be correctly recognized and accepted, the corresponding type conversion is completed, and the target alias is output.
