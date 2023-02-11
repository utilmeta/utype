# Field - configure param

In utype, `Field` is used to configure dataclass attributes and function parameters to control their behavior. In this document, we will explain its usage in detail.

## Optional and default

Declaring whether a field is optional and specifying the default value of the field is the most commonly used field configuration, even if you do not use `Field`, for example
```python
from utype import Schema, parse

class UserSchema(Schema):
    name: str
    age: int = 0

@parse
def init_user(name: str, age: int = 0): pass
```
Using the native Python syntax, if you assign a default value for a param/attribute, then you are making it optional, if input data does not contains such param, it will populate the default value, such as

1. `name`: no default value provided, an `exc.AbsenceError` error is thrown if it does not appear in the input data
2. `age`: a default value of 0 has been specified, which makes it optional, the default value is automatically populated when no data is provided.

However, to coordinate with other field configuration parameters, `Field` also provides optional and default configuration parameters, including

* `required`: specify whether the field must be passed. The default is True. You can use `required=False` to declare an optional field
* `default`: pass in the default value of the field, which will be used as the value of the field when it is not provided in the input data

So the following is equivalent to the above example.
```python
from utype import Schema, Field, parse

class UserSchema(Schema):
    name: str = Field(required=True)  # or Field()
    age: int = Field(default=0)

@parse
def init_user(
	name: str = Field(required=True), # or Field()
	age: int = Field(default=0)
):
	pass
```

In addition, Field provides some advanced configuration of default values.

* `default_factory`: given a factory function that makes a default value, it will be called at parse time to get the default value.
```python
from utype import Schema, Field
from datetime import datetime

class InfoSchema(Schema):
	metadata: dict = Field(default_factory=dict)
	current_time: datetime = Field(default_factory=datetime.now)
```

In the example
1. When your default type is `dict`, `list` `set`, etc., you should not want the default to be shared by all instances, so you can just use their type as the factory function that makes the default. For example, the field  `metadata`  in the example will be called `dict()` to get an empty dictionary by default.
2. You need to get the default value dynamically at the time of parsing, for example, the `current_time` in the example will be called `datetime.now()` to get the current time by default.

* `defer_default`: if enabled, the default value will not be populated as part of the data when no data is entered, but will only be evaluated when the default attribute is accessed.
```python
from utype import Schema, Field
from datetime import datetime

class InfoSchema(Schema):
	metadata: dict = Field(default_factory=dict, defer_default=True)
	current_time: datetime = Field(default_factory=datetime.now)

info = InfoSchema()   # no fields provided

print('metadata' in info)
# > False
print('current_time' in info)
# > True
```

As you can see, when specified `defer_default=True`, the default value is not directly populated at parse time, so the default `'metadata'` field in the example does not appear in the data, but when this property is accessed, it triggers the calculation of the default value. so unprovided data can be accessed through the attribute.

It should be noted that when you specify `default_factory` and the data is default, a new object will be generated every time you access it, so your direct operation on the attribute object will not be reflected in the data, unless you assign the attribute first and then operate it, such as
```python
info.metadata.update(key='value')
print(info.metadata)   # just generated a new one
# > {}

info.metadata = {'version': 3}   # set a value, so no default will be used
info.metadata.update(key='value')
print(info.metadata)
# > {'version': 3, 'key': 'value'}
```

!!! note
	`defer_default` only works for dataclass, and is invalid for function, because function params need to provide a value when calling, so it will be directly passed with default value

### Function parameters

For function parameters, it is more convenient to use `Param`, a subclass of the `Field` class provided by utype, to declare them, where `default` is the first parameter of the `Param` class, If no default value is declared (no `default` or `default_factory`), it will be regarded as a required parameter, such as

```python
from utype import Param, parse

@parse
def init_user(
	name: str = Param(),
	age: int = Param(0)
):
	pass
```

### Unstable field
If your field is optional ( `required=False` ) and no default value is specified, then the field is an unstable field, because when the field is not passed in, if you access the property of the field, it will throw an `AttributeError`, and if you use the key to access the field, it will also throw `KeyError`, such as
```python
from utype import Schema, Field

class UserSchema(Schema):
    name: str 
    age: int = Field(required=False)

user = UserSchema(name='test')
print(user)
# > UserSchema(name='test')

try:
	print(user.age)
except AttributeError as e:
	print(e)
	"""
	UserSchema: 'age' not provided in schema instance
	"""

try:
	print(user['age'])
except KeyError as e:
	print(e)
	"""
	KeyError: 'age'
	"""
```

!!! warning
	You cannot declare such field in the function, for optional fields, you must specify a default value

## Constraints

`Field` also supports to configure constraints for types, where the parameters are the same as the built-in constraints in Rule, as shown in

```python
from utype import Schema, Field  
  
class ArticleSchema(Schema):  
    slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*") 
    title: str = Field(min_length=1, max_length=50) 
    views: int = Field(ge=0, default=0)  
```

For more complete constraint parameters and usage, you can refer to [Rule API References](/references/rule) directly. `Field` just declares the built-in constraints in Rule by instantiating the parameters.

!!! note
	In common practice, if your constrants will be reused by many fields, it is recommended to use constrained type by inheriting `Rule`, otherwise you can declare them in the `Field`

Field also provides shortcut for some common built-in constraint declarations, such as
* `round`: provides a `decimal_places=Lax(value)` shortcut, which is used to directly use the Python `round()` method to preserve the corresponding decimal places of the data, such as
```python
from utype import Schema, Field  

class Index(Schema):
	ratio: float = Field(round=2)

index = Index(ratio='12.3456')
print(index.ratio)
# 12.35
```

## Alias configuration

By default, utype takes the name of a class attribute or a function parameter as the name of a field. You can only use a consistent name for input to be recognized as the corresponding field for parsing. However, this may not meet your naming requirements in certain cases, such as

1. The field name does not conform to the field’s admission rules, such as starting with an underscore (`'_'`)
2. Fields cannot be declared as Python variable names, such as contains special characters or being a Python syntax keyword
3. Field name is a duplicate of an internal method of the current dataclass or a parent class

So utype provides aliases configuration in `Field`, including

* `alias`: specifies an alias for the field. An alias can be used to represent the field in the input, such as
```python
from utype import Schema, Field  

class AliasSchema(Schema):
    seg_key: str = Field(alias='__key__')
    at_param: int = Field(alias='@param')
    item_list: list = Field(alias='items')

data = {
	'__key__': 'value',
	'items': [1, 2], 
	'@param': 3
}

inst = AliasSchema(**data)
print(inst)
# > AliasSchema(seg_key='value', at_param=3, item_list=[1, 2])
```
1. `seg_key`: the name `__key__` of a data field contains a double underscore and is not recognized as a field
2. `at_param`: the name `@param` of a data field contains special characters and cannot be declared as a variable in Python.
3. `item_list`: the name `items` of the data field is an inherent method of the `dict` and cannot be directly used as the field property name of the Schema dataclass.

In the instance, you can still access the value of the field using the corresponding attribute name, and in the dataclass, `alias` is also the name of the output field by default.

```python
print(inst.item_list)
# > [1, 2]
print(inst['@param'])
# > 3
print(dict(inst))
# > {'__key__': 'value', '@param': 3, 'items': [1, 2]}
```

Also, even if the field is declared as an alias, you can still enter data through the field’s property name.
```python
attr_inst = AliasSchema(seg_key='value', item_list=[1, 2], at_param=3)
print(dict(attr_inst))
# > {'__key__': 'value', '@param': 3, 'items': [1, 2]}
```

In addition to using to `alias` specify a single alias, utype provides a way to specify multiple input aliases

* `alias_from`: specifies a list of aliases from which you can convert, such as
```python
from utype import Schema, Field  
from datetime import datetime

class Article(Schema):
	slug: str
	content: str = Field(alias_from=['text', 'body'])
	created_at: datetime = Field(
		alias='createdAt', 
		alias_from=['created_time', 'added_time']
	)

article = Article(**{
	'slug': 'my-article',
	'body': 'article content',
	'created_time': '2022-03-04 10:11:12'
})

print('created_at' in article)
# > True
print('added_time' in article)
# > True

print(dict(article))
# {
# 'slug': 'my-article', 
# 'content': 'article content', 
# 'createdAt': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```

In the example, we have specified multiple input aliases for `content`, `created_at`, which can be used to be compatible with the old version of the API, or to access data APIs from different sources. There is no need to manually identify and convert one by one.

For example, the old version of the article content field name is `'body'` or `'text'`, which is obsolete in the current version and used `'content'` as the name of the content field, so it is used `Field(alias_from=['text', 'body'])` to be compatible with the old version requests.

As you can see, `alias_from` the specified input is used only to identify the input data, not for output or attribute access, but can be used to determine whether the field is in the data

!!! warning
	In the same dataclass or function, the aliases of the fields cannot overlap, or conflict with attribute names of other fields, so that no matter which name the input use, dataclass and function can always recognize and parse correctly and stay idempotent in multiple conversions

### Alias generation function
If your alias can be generated from the attribute name with a certain regularity, you can directly specify a function to generate the alias, such as

```python
from utype import Schema, Field  
from datetime import datetime

def pascal_case(name: str):
	return "".join(name.capitalize() for word in name.split('_'))

class Article(Schema):
	slug: str = Field(alias=pascal_case)
	liked_num: int = Field(alias=pascal_case)
	created_at: datetime = Field(
		alias_from=[pascal_case, 'created_time'],
	)

article = Article(**{
	'Slug': 'my-article',
	'liked_num': '3',
	'CreatedAt': '2022-03-04 10:11:12'
})
print(article)
# > Article(slug='my-article', liked_num=3, created_at=datetime.datetime(2022, 3, 4, 10, 11, 12))

print(dict(article))
# {
# 'slug': 'my-article', 
# 'LikedNum': 3, 
# 'created_at': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```

We wrote a generating function `pascal_case` to generate the PascalCase names, such as  `'CreatedAt'` for  `'created_at'`, and the function can be passed in to `alias` or `alias_from`. so that the corresponding alias can be generated directly from the attribute name

### Case insensitive
Field recognition is case-sensitive by default, but you can adjust this behavior by turning on the following parameter

* `case_insensitive`: False by default,wWhen enabled, the field can be identified in a case-insensitive manner, such as

```python
from utype import Schema, Field  
from datetime import datetime

class Article(Schema):
	slug: str = Field(case_insensitive=True)
	liked_num: int = Field(case_insensitive=True)
	created_at: datetime = Field(
		case_insensitive=True,
		alias_from=['created_time'],
	)

article = Article(**{
	'SLUG': 'my-article',
	'LIKED_num': '3',
	'CREATED_time': '2022-03-04 10:11:12'
})
print(article)
# > Article(slug='my-article', liked_num=3, created_at=datetime.datetime(2022, 3, 4, 10, 11, 12))

print('created_time' in article)
# > True

print('CREATED_AT' in article)
# > True

print(dict(article))
# {
# 'slug': 'my-article', 
# 'LikedNum': 3, 
# 'created_at': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```

Case-insensitive configuration applies to all field aliases, including attribute names, `alias` and `alias_from`, so any alias you enter using any case will be recognized

Moreover, it can be seen that the case-insensitive configuration also supports key access and field inclusion ( `in` ) recognition, which will be recognized and mapped to the `'created_at'` field by Schema when used `'CREATED_AT' in article`.

!!! note
	If you are going to make the whole dataclass/function case-insensitive, you can directly use `Options(case_insensitive=True)`. for specific usage, you can refer to [Options API References](/references/options)


## Description and marks

Field provides some descriptive and marked parameters, which will not affect the parsing, but can more clearly describe the purpose of the field, examples, etc., and can be integrated into the generated API document (JSON-schema / OpenAPI), such as

* `title`: pass in a string to specify the title of the field (not related to the name or alias, just for description purposes)
* `description`: passe in a string to describe the purpose or usage of the field.
* `example`: give a sample of data for this field

```python
from utype import Schema, Field  

class ArticleSchema(Schema):  
    slug: str = Field(  
		title='Article Slug',
        description='the url route of an article',
        example='my-awesome-article',    
    )  
    content: str = Field(description='the content of an article')  
```

In addition, Field provides some useful tag fields.

* `deprecated`: whether the field is deprecated (not encouraged to be used). The default is False.

The deprecation flag `deprecated` can be used for fields that are compatible with older versions and gives a deprecation prompt. Examples are as follows
```python
from utype import Schema, Field  

class RequestSchema(Schema):  
    url: str  
  
    query: dict = Field(default=None)  
    querystring: dict = Field(  
        default=None,  
        deprecated=True,  
        description='"query" is prefered'  
    )  
  
    data: bytes = Field(default=None)  
    body: bytes = Field(default=None, deprecated='data')  
  
    def __validate__(self):  
        if self.querystring:  
            self.query = self.querystring  
            del self.querystring  
        if self.body:  
            self.data = self.body  
            del self.body

old_data = {  
    'url': 'https://test.com',  
    'querystring': {'key': 'value'},  
    'body': b'binary'  
}  
request = RequestSchema(**old_data)
# DeprecationWarning: 'querystring' is deprecated
# DeprecationWarning: 'body' is deprecated, use 'data' instead

print(request)
# > RequestSchema(url='https://test.com', query={'key': 'value'}, data=b'binary')
```

In our example, we declared a data class called `RequestSchema` that supports both deprecated old-version fields `querystring`, `body` and new-version `query` and `data` fields. A `DeprecatedWarning` is given when the input data contains deprecated fields

In  `__validate__` function of dataclass, we manually convert the deprecated fields to the new version. Although you can also use `alias_from` to do so, this method in the example provides more control. For example, this method can be used when the data of the new and old versions may use different encoding methods or parsing rules and need to be processed by user-defined logic.


## Input and output

`Field` also provides configuration to regulate the input and output behavior of data at the field level. In utype, input and output represent:

* **Input**: initialize the dataclass, or call a function to pass parameters.
* **Output**: the actual data used in serialization or param-passing refers to its own dictionary data for the Schema class, and the data exported by using `__export__` for other dataclasses.

Where the control parameters of input is

* `no_input`: specifies whether the field cannot be input. The default is False.

For `no_input=True`, the field cannot be input to the data, but it can be populated `default` or `default_factory`, or assigned by an attribute in the dataclass, for example

```python
from utype import Schema, Field
from datetime import datetime

class ArticleSchema(Schema):  
	slug: str = Field(no_input=True)
	title: str
    updated_at: datetime = Field(default_factory=datetime.now, no_input=True)

	def __validate__(self):
		print('slug' in self)
		# > False
		self.slug = '-'.join([''.join(filter(str.isalnum, v))  
                               for v in self.title.split()]).lower()

article = ArticleSchema(title='My Awesome Article', slug='ignored')
print(article)
# > ArticleSchema(title='My Awesome Article', updated_at=datetime.datetime(...), slug='my-awesome-article')
```

We can see

1. The `slug` field i  the example specified `no_input=True`, so even if `'slug'` the field appears in the input data, it will be ignored. In the  `__validate__` function after initialization, we assigned the `slug` field, so it will show up in the results.
2. The `update_at` field in the example does not accept data input, but will use `default_factory` to fill the current time when the data class is initialized, and this field can be output normally, which means that subsequent operations (such as updating data to the database) will be performed together with other output fields.

!!! note
	If you need not only to disable the input, but also disable the attribute assignment, you can use `Field(no_input=True, immutable=True)`, in this case only default value will be populated

In contrast, the parameters that control the output behavior of the field are

* `no_output`: specifies whether the field cannot be output. The default is False.

Although the `no_output=True` field does not used for data output, it can be accessed using attribute accessing, which can be used as dependent values for computing other data, such as
```python
from utype import Schema, Field  
from datetime import datetime  

class KeyInfo(Schema):  
    access_key: str = Field(no_output=True)  
    last_activity: datetime = Field(default_factory=datetime.now, no_input=True)  
  
    @property  
    def key_sketch(self) -> str:  
        return self.access_key[:5] + '*' * (len(self.access_key) - 5)

info = KeyInfo(access_key='QWERTYUIOP')
print(info.access_key)
# > QWERTYUIOP
print('access_key' in info)
# > False
print(dict(info))
# > {'last_activity': datetime.datetime(...), 'key_sketch': 'QWERT*****'}
```

In this example, we declare a `no_output=True` field `access_key`, which will not output, but can be accessed by using the attribute name, so that the `key_sketch` attribute can be calculated, which is a common key semi-hidden scenario. The key field itself ( `access_key` ) is not output, only the processed result ( `key_sketch` ) is outputed

!!! warning
	The "output" concepts only applies to dataclass, so using `no_output=True` in function params has no meaning

### By function

`no_input` And `no_output` parameters can be passed in a function that dynamically determines whether to accept input or output based on the value of the field.

```python
from utype import Schema, Field  
from typing import Optional

class ArticleSchema(Schema):
	title: Optional[str] = Field(no_output=lambda v: v is None)
	content: str = Field(no_input=lambda v: not v)

article = ArticleSchema(title=None, content='test')

assert article.title is None  # True
print('title' in article)
# > False

print('content' in article)
# > True

article.title = 'My title'
print('title' in article)
# > True

print(dict(article))
# > {'content': 'test', 'title': 'My title'}
```
 
In the example, we specify a function in the `no_output` parameter for `title` , indicating that if the input is `None`, it will not be output, so in the example, when the dataclass is just initialized, `'title'` is not in the data (although you can access it using the attribute); `content` specifies that it will not input when the value is empty, so it remains in the data when a non-empty value is passed in.

!!! note
	In Schema, "output" means the data in the `dict` structure, because you can get it by using `dict(inst)`, passing to function using `func(**inst)`, or use `json.dumps(inst)` to get the JSON output
	If a field is no_output but accept input, then you can access the value through attribute, but it will not show up in the result of `dict(inst)`

## Mode configuration

utype supports a more advanced “mode configuration” feature that allows the same field to behave differently in different “modes”. For example, if we need a field to be “read-only”, we actually only need it to support input and output in “read mode”

Let’s look at an example.
```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(writeonly=True)
	signup_time: datetime = Field(readonly=True)
```

In our example, we declared a `UserSchema` dataclass that has

1. `username`: has no mode declaration and can be used in any mode
2. `password`: declared `writeonly=True`, which means that it is only used for **Write** mode, not for reading.
3. `signup_time`: declated `readonly=True`, which means that it is only used for **Read** mode, not for updates.

The mechanism provided by utype allows you to declare a single dataclass that behaves differently in different schemas. `Field` provides several parameters for specifying the modes supported by the field.

* `mode`: specifies a mode string in which each character represents a supported mode. For example `mode='rw'` represents `'r'` and `'w'` modes, the default is null, which means the field supports all modes.
* `readonly`: is a shortcut for `mode='r'`
* `writeonly`: is a shortcut for  `mode='w'`

!!! warning
	Since `readonly` and `writeonly` are only shortcuts for `mode`, only one of these params can be specified

Commonly used modes and corresponding meanings are as follow

1. `'r'`: Read/Query/Retrieve operations that do not affect the system state, such as reading the data from database through SQL and converting it into a Schema instance for return.
2. `'w'`: Write/Update mode is often used to update the resources of the system, such as converting the data in the HTTP request body into a Schema instance and updating the target resources.
3. `'a'`: Append/Create mode, add a new resource to the system, for example, convert the data in the HTTP request body into a Schema instance and create a new corresponding resource in the system

!!! note “Distinguish `readonly` / `immutable`”
	`readonly` is a mode shortcut for `mode='r'`, which means only support input and output in `'r'` mode, thus does not control the "immutability" in the instance, such feature is controlled by `immutable`, irrelevant to modes

### How mode is used

Although we see the common modes, it is actually up to you to specify and use the mode. We can look at a few examples to understand how to use the mode.

In these examples, we use the `'r'`/ `'w'`/ `'a'` mode to illustrate a typical user class data read/update/create scenario

**Inherit with different modes**

[Options](/references/options) also support `mode` paramete to specify the mode used by the current dataclass or function, so you can specify different parsing options to provide sub-dataclasses in different modes by inheriting dataclasses, such as
```python
from utype import Schema, Field, Options
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(mode='wa')
	followers_num: int = Field(readonly=True)  # or mode='r'
	signup_time: datetime = Field(
		mode='ra', 
		default_factory=datetime.now
	)

class UserRead(UserSchema):
	__options__ = Options(mode='r')

class UserUpdate(UserSchema):
	__options__ = Options(mode='w')

class UserCreate(UserSchema):
	__options__ = Options(mode='a')
```

In `UserSchema`, we specified the follow fields

* `username`: no mode is specified, indicating that input and output can be performed in any modes.
* `password`: specified `mode='wa'`, indicating input and output only in `'w'` mode and `'a'` mode
* `followers_num`: the number of followers of the user. specified `readonly=True`, indicates that only reading is supported, and creating or updating is not supported.
* `signup_time`: user’s registration time field, specified `mode='ra'`, indicates that only read and create modes are supported, and ispecified `no_input='a'`, that is, no input is accepted in create mode, and the current time is directly calculated by using `default_factory` the function in as the registration time of the new user.

Let’s look at how the schema configuration is reflected in the data parsing.
```python
user_updated_data = {  
    'username': 'new-username',  
    'password': 'new-password',  
    'followers_num': '3',  
    'signup_time': '2022-03-04 10:11:12',  
}  
updated_user = UserUpdate(**user_updated_data)
print(updated_user)
# > UserUpdate(username='new-username', password='new-password')

updated_user.followers_num = 3  # will not work
print(updated_user)
# > UserUpdate(username='new-username', password='new-password')
```

In the example, we can see that when data is initialized using the `UserUpdate` dataclass with the specified schema `'w'`, data that is not supported in the `'w'` mode will not be input and will not take effect even if you try to assign it. The resulting output is the fields supported in the `'w'`  mode

**Modes in runtime Options** 

You can also use the method of the dataclass `__from__` for initialization, in which the first parameter is passed in data, and the `options` parameter can specifies a runtime parsing Options, which can be used for dynamic specification of the mode, such as
```python
from utype import Schema, Field, Options
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(mode='wa')
	followers_num: int = Field(readonly=True)  # or mode='r'
	signup_time: datetime = Field(
		mode='ra', 
		default_factory=datetime.now
	)

new_user_form = 'username=new-user&password=123456'
new_user = UserSchema.__from__(new_user_form, options=Options(mode='a'))
print(new_user)
# > UserSchema(username='new-user', password='123456', signup_time=datetime(...))

user_query_result = {  
    'username': 'current-user',  
    'followers_num': '3',  
    'signup_time': '2022-03-04 10:11:12',  
}  
queried_user = UserSchema.__from__(user_query_result, options=Options(mode='r'))
print(queried_user)
# > UserSchema(username='new-user', followers_num=3, signup_time=datetime(...)))
```

**Modes in function decorator** 

You can also use the function’s parse Options to specify the parsing mode for all dataclass parameters in the function, as shown in
```python
from utype import Schema, Field, Options, parse
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(mode='wa')
	followers_num: int = Field(readonly=True)  # or mode='r'
	signup_time: datetime = Field(
		mode='ra', 
		default_factory=datetime.now
	)

@parse(options=Options(mode='a', override=True))
def create_user(user: UserSchema):
	return dict(user)
	
new_user_form = 'username=new-user&password=123456'

print(create_user(new_user_form))
# {
# 'username': 'new-user', 
# 'password': '123456', 
# 'signup_time': datetime.datetime(...)
# }
```

!!! note
	Declaring an Options that affect the dataclass params (like `user` in the example) requires to specify `override=True` in Options, otherwise dataclass will parse data with its own Options

**Modes extension**

utype does not restrict the semantics and scope of the mode, so you can freely declare a custom mode in `mode` param. a mode is usually represented by a signle lowercase letter.

utype supports json-schema document output in different modes, so you can use only one dataclass to get its input and output templates in multiple mode scenarios such as read, update, create, and so on

### Modes and input/output

To specify a field as a certain mode is actually to specify that the input and output of the field are disabled in other modes. For example, if the mode of the field is `'r'` and the current parsing mode is `'w'`, then the field is invalid and will not be used for input or output.

In fact, input and output parameters can also be configured as a mode string, such as

```python
from utype import Schema, Field
from datetime import datetime

class Article(Schema):
	slug: str = Field(no_input='wa')
	title: str
	created_at: datetime = Field(
		mode='ra', 
		no_input='a',
		default_factory=datetime.now
	)
	
	def __validate__(self):
		if 'slug' not in self:
			self.slug = '-'.join([''.join(filter(str.isalnum, v))  
	                               for v in self.title.split()]).lower()

new_article_json = b'{"title": "My Awesome Article", "created_at": "ignored"}'  
new_article = Article.__from__(new_article_json, options=Options(mode='a'))

print(new_article)
# > Article(title='My Awesome Article', created_at=datetime(...), slug='my-awesome-article')
```

Modes declared for the dataclass `Article` in the example are

* `slug`: inputs are disabled on update ( `'w'` ) and create ( `'a'` ), but outputs are not disabled (that is, if assigned, they can be output as fields in the result), and inputs and outputs in other modes (such as read) are not restricted.
* `created_at`: mode is specified as read ( `'r'` ) and create ( `'a'` ), and the input in create ( `'a'` ) mode is disabled. The input is ignored when parsing in `'a'` mode, and the default value (current time) is filled in, which conforms to the semantics of the field. Input and output are supported normally when reading

So you can see that when we use the create mode ( `'a'` ) to initialize the article data, the `'"created_at"'`  in input will be ignored directly, and `slug` will also not accept the input. The  `__validate__` function calle after initialization assigns the `slug` if not provided
so the final result includes the passed in `title`, assigned `slug`, and `created_at` with the populated default value.

## Attribute configuration

`Field` also supports the configuration of attribute features for the dataclass, such as

* `immutable`: whether the attribute is immutable. The default is False. If enabled, you cannot assign or delete the corresponding attribute of the dataclass instance.

```python
from utype import Schema, Field, exc
from datetime import datetime

class UserSchema(Schema):
	username: str = Field(immutable=True)
	signup_time: datetime = Field(
		no_input=True,
		immutable=True,
		default_factory=datetime.now
	)
	
new_user = UserSchema(username='new-user')

print(new_user)
# > UserSchema(username='new-user', signup_time=datetime(...))

try:
	new_user.username = 'changed-user'
except exc.UpdateError as e:
	print(e)
	"""
	UserSchema: Attempt to set immutable attribute: ['username']
	"""

try:
	del new_user.username
except exc.DeleteError as e:
	print(e)
	"""
	UserSchema: Attempt to delete immutable attribute: ['username']
	"""

try:
	new_user.pop('signup_time')
except exc.DeleteError as e:
	print(e)
	"""
	UserSchema: Attempt to pop immutable item: ['signup_time']
	"""
```

As you can see, for `immutable=True` field, whether you use attribute assignment or deletion, or use the `dict` method of Schema to update or delete the data, an error will be thrown (thrown `exc.UpdateError` for updating, thrown `exc.DeleteError` for deleting).

!!! note
	Technically, you cannot make attributes immutable entirely in Python, if developer is intended,
	mutation can be done by manipulating `__dict__`, so `immutable` is actual also a mark to notice the developer that this field is not meant to be mutate

* `repr`: you can specify a boolean, string, or function to control the display behavior of the field, that is, the display value in `__repr__` the and `__str__` functions, which represent the
	1. `bool`: whether to display. The default is True. If it is specified as False, the field will not be displayed even if it is provided in the data.
	2. `str`: specify a fixed display value, which is often used to hide the information of these fields
	3. `Callable`: provide a function that accepts the data value corresponding to the field as input and outputs a representation function.

```python
from utype import Schema, Field
from datetime import datetime

class AccessInfo(Schema):
	access_key: str = Field(repr=lambda v: repr(v[:3] + '*' * (len(v) - 3)))
	secret_key: str = Field(repr='<secret key>')
	last_activity: datetime = Field(default_factory=datetime.now, repr=False)

access = AccessInfo(access_key='ABCDEFG', secret_key='qwertyu')
print(access)
# > AccessInfo(access_key='ABC****', secret_key=<secret key>)

print('last_activity' in access)
# > True

print(dict(access))
# > {'access_key': 'ABCDEFG', 'secret_key': 'qwertyu', 'last_activity': datetime(...)}
```

In the example, we specify a display function for `access_key` that intercepts only the first few characters for display, for `secret_key` that we specify a fixed string for display, and for `last_activity` the field, we directly disable its display

!!! warning
	`repr` configuration is only appied when using `print()`, `str()` or `repr()` to output the entire dataclass instance, if you print a single attribute like `print(access.secret_key)`, it will be displayed directly

!!! note
	attribute configuration ( `immutable`, `repr` ) only applies for dataclass, it has no meaning in function params

## Error handling

`Field` can also configure the error handling strategy for the specific field, that is, how to handle when the data corresponding to the field fails to pass the parsing validation. Its corresponding parameters is

* `on_error`: configures the error handling behavior of a field. This parameter has several optional values.
	1. `'throw'`: default, throw error
	2. `'exclude'`: exclude the field from the result (this option cannot be used if the field is required)
	3. `'preserve'`: keep the field in the result, which allow the field in the result that does not pass the validation

Let’s look at an example.
```python
from utype import Schema, Field, exc

class ErrorSchema(Schema):  
    throw: int = Field(on_error='throw', ge=0, required=False)  
    exclude: int = Field(on_error='exclude', ge=0, required=False)  
    preserve: int = Field(on_error='preserve', ge=0, required=False)  
  
try:
    ErrorSchema(throw='-1')  
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['throw'] failed: Constraint: <ge>: 0 violated
	"""
  
inst = ErrorSchema(exclude='-1', preserve='-1')  
# UserWarning: parse item: ['exclude'] failed: Constraint: <ge>: 0 violated
# UserWarning: parse item: ['preserve'] failed: Constraint: <ge>: 0 violated
print('exclude' in inst)
# > False
print('preserve' in inst)
# > True

print(dict(inst))
# > {'preserve': '-1'}
```

When specified `on_error='throw'` (which is also the default value), the invalid data passed by the field will be thrown directly as an error; 
when `on_error='exclude'` field encounter the invalid data, a warning will be given, but it will be ignored and not added to the result; 
when `on_error='preserve'` field encounter the invalid data, it will still be added to the result after a warning is given

!!! warning
	Unless you known what you are doing, do not specify `on_error='preserve'`, for that will break the type-safe guarantee in the runtime

If you want to configure error handling for an entire dataclass / function, please refer to [Options API References](/references/options)


## Field dependency

Field supports specifying a series of dependencies for the field, that is, when the input data provides the field, the dependency fields must also be provided. The parameters are as follows

* `dependencies`: specifies a list of strings, where each string represents the name of a dependency field. Dependency fields must be defined in the current dataclass.

```python
from utype import Schema, Field

class Account(Schema):  
    name: str  
    billing_address: str = Field(default=None)  
    credit_card: str = Field(required=False, dependencies=['billing_address'])
```

In `Account` dataclass, `credit_card` specifies a dependency of `['billing_address']`, which means

* `billing_address` must be provided if `credit_card` is provided
* If no value is provided for `credit_card`, `billing_address` follows its own optional configuration

Let’s take a look at the specific usage.
```python
bill = Account(name='bill')  
bob = Account(name='bill', billing_address='my house')  

alice = Account(name='alice', billing_address='somewhere', credit_card=123456)  
assert alice.credit_card == '123456'  

from utype import exc
try:
    Account(name='alice', credit_card=123456)
except exc.DependenciesAbsenceError as e:
	print(e)
	"""
	required dependencies: {'billing_address'} is absence
	"""
```

As you can see, when `credit_card` is not provided, it can be parsed regardless of whether `billing_address` is passed in, because `billing_address` is an optional field, but when the data provides a `credit_card` field, `billing_address` must be provided. Otherwise, an `exc.DependenciesAbsenceError` error is thrown.


### Property dependency

Field dependencies can also act on `@property` fields, such as
```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	signup_time: datetime = Field(required=False)
	
	@property
	@Field(dependencies=['signup_time'])
	def signup_days(self) -> int:  
	    return (datetime.now() - self.signup_time).total_seconds() / (3600 * 24)

new_user = UserSchema(username='test')
print('signup_days' in new_user)
# False

signup_user = UserSchema(username='test', signup_time='2021-10-11 11:22:33')
print('signup_days' in signup_user)
# True

assert isinstance(signup_user.signup_days, int)  # True 
```

In the `UserSchema` dataclass declared in the example, the calculation `signup_days` needs `signup_time` to be provided, so it is declared as the dependency of the property

It can be seen that the difference between property dependency and field dependency is that when the property dependency is not provided, the attribute will not be calculated or output, but will not report an error.
