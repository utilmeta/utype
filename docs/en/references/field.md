# Field - config param

In utype, Field is used to configure data class attributes and function parameters to adjust their behavior. In this document, we will explain its usage in detail.

## Optional and Default

Declaring whether a field is optional and specifying the default value of the field is the most commonly used field configuration, even if you do not use Field, such as
```python
from utype import Schema, parse

class UserSchema(Schema):
    name: str
    age: int = 0

@parse
def init_user(name: str, age: int = 0): pass
```
When the default value of an attribute value of a data class or a function parameter is not a Field instance, it is treated as the default value of the field, where

1. No default value is `name` provided, and an `exc.AbsenceError` error is thrown if it does not appear in the input data
2.  `age`: a default value of 0 has been specified. This is optional. The default value is automatically populated when no data is provided.

However, to coordinate with other field configuration parameters, Field also provides optional and default configuration parameters, including

*  `required`: Specify whether the field must be passed. The default is True. You can declare `required=False` an optional field, or you can declare the default value to
* The default value `default` passed into the field, which will be used as the value of the field when it is not supplied in the input data

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

*  `default_factory` Given a factory function that makes a default value, it will be called at parse time to get the default value.
```python
from utype import Schema, Field
from datetime import datetime

class InfoSchema(Schema):
	metadata: dict = Field(default_factory=dict)
	current_time: datetime = Field(default_factory=datetime.now)
```

Some examples of the recommended use `default_factory` of parameters are shown in the examples
1. When your default type is `dict`, `list` `set`, etc., you should not want the default to be shared by all instances, so you can just use their type as the factory function that makes the default. For example, the field in `metadata` the example will be called `dict()` to get an empty dictionary by default.
2. You need to get the default value dynamically at the time of parsing, for example, the `current_time` dictionary in the example will be called `datetime.now()` to get the current time by default.

*  `defer_default` If enabled, the default value will not be populated as part of the data when no data is entered, but will only be evaluated when the default attribute is accessed.
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

As you can see, when specified `defer_default=True`, the default value is not directly populated at parse time, so the default `'metadata'` field in the example does not appear in the data, but when this property is accessed, it triggers the calculation of the default value. The feature is that data that is not passed in or assigned can be accessed through the property, but is not output.

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

### Function arguments

For function parameters, it is more convenient to use Param, a subclass of the Field class provided by utype, to declare them, where `default` Param is the first parameter of the Param class, and the `required` `defer_default` configuration is cancelled. If no default value is declared (no `default` or `default_factory`), it will be regarded as a required parameter, such as

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
If your field is optional ( `required=False`) and no default value is specified, then the field is an unstable field, because when the field is not passed in, if you access the property of the field, it will throw `AttributeError`, and if you use the key to access the field, it will also throw `KeyError`, such as
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


## Constraints

Field also supports the use of parameters to configure constraints for types, where the parameters are the same as the built-in constraints in Rule, as shown in

```python
from utype import Schema, Field  
  
class ArticleSchema(Schema):  
    slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*") 
    title: str = Field(min_length=1, max_length=50) 
    views: int = Field(ge=0, default=0)  
```

For more complete constraint parameters and usage, you can refer to [Rule](/en/references/rule) directly. Field just declares the built-in constraints in Rule by instantiating the parameters.

!!! note

Field also provides shorthand for some common built-in constraint declarations, such as
*  `round`: provides a `decimal_places=Lax(value)` shorthand for the Lax constraint of, which is used to directly use the Python `round()` method to preserve the corresponding decimal places of the data, such as
```python
from utype import Schema, Field  

class Index(Schema):
	ratio: float = Field(round=2)

index = Index(ratio='12.3456')
print(index.ratio)
# 12.35
```

## Alias configuration

By default, utype takes the name of a class attribute or a function parameter as the name of a field. You can only use a consistent name for input to be recognized as the corresponding field for parsing. However, this may not meet our naming requirements in certain cases, such as

1. The field name does not conform to the field’s admission rules, such as starting with an underscore
2. Fields cannot be declared as Python variable names, such as with special characters
3. Field name is a duplicate of an internal method of the current data class or a parent class

So utype provides some parameters that control field aliases, including

*  `alias`: Specifies an alias for the field. An alias can be used to represent the field in the input, such as
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
1.  `seg_key`: The name `__key__` of a data field contains a double underscore and is not recognized as a field because it is a property name.
2. The name `@param` of a `at_param` data field contains special characters and cannot be declared as a variable in Python.
3.  `item_list`: The name `items` of the data field is an inherent method of the dictionary type and cannot be directly used as the field property name of the Schema data class.

In the instance, you can still access the value of the field using the corresponding property name, and in the data class, `alias` it is also the name of the output field by default.

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

*  `alias_from`: Specifies a list of aliases from which you can convert, such as
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

For example, in the example, we have specified multiple input aliases for `content` fields such as, `created_at`, which can be used to be compatible with the old version of the interface, or to access data APIs from different sources. There is no need to manually identify and convert one by one.

For example, the old version of the article content field name is `'body'` or `'text'`, which is obsolete in the current version and used `'content'` as the name of the content field, so it is used `Field(alias_from=['text', 'body'])` to be compatible with the old version of data entry.

As you can see, `alias_from` the specified input is used only to identify the input data, not for output or property access, but for key-value access, or to determine whether the field is in the data

!!! warning


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

We wrote a generating function `pascal_case` to generate the capitalized hump names, such as `'created_at'` the, and passed `'CreatedAt'` the function in as a field `alias` or `alias_from` as an argument. Uch that the corresponding alias can be generated directly from the attribute name

### Case insensitive
Field recognition is case-sensitive by default, but you can adjust this behavior by turning on the following parameter

*  `case_insensitive`: False by default. When enabled, the field can be identified in a case-insensitive manner, such as

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

Moreover, it can be seen that the case-insensitive configuration also supports key access and field inclusion ( `in`) recognition, which will be recognized and mapped to the `'created_at'` field by Schema when used `'CREATED_AT' in article`.

!!! note



## Description and marks

Field provides some descriptive and marked parameters, which will not affect the parsing, but can more clearly describe the purpose of the field, examples, etc., and can be integrated into the generated API document, such as

*  `title`: Pass in a string to specify the title of the field (not related to the name or alias, just for description purposes)
*  `description`: a string is passed in to describe the purpose or usage of the field.
*  `example` Give a sample of data for this field

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

*  `deprecated`: Whether the field is deprecated (not encouraged to be used). The default is False.

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

In our example, we declared a data class called RequestSchema that supports both deprecated old-version fields `querystring` `body` and new-version `query` and `data` fields. A `DeprecatedWarning` warning is given when the input data contains deprecated fields

In the function of the `__validate__` data class, we manually convert the deprecated fields to the new version. Although you can also use the `alias_from` automatic conversion processing in the alias configuration for the compatibility of the old version fields, this method in the example provides more control. For example, this method can be used when the data of the new and old versions may use different encoding methods or parsing rules and need to be processed by user-defined logic.


## Input and output

Field also provides configuration to regulate the input and output behavior of data at the field level. In utype, input and output represent:

* Initialize the data of a ** Input ** data class, or call a function to pass parameters.
* ** Output **: Use the data class instance to pass parameters. The actual data used in serialization refers to its own dictionary data for the Schema class, and the data exported by using `__export__` the method for other data classes.

Where the control parameter for the input behavior of the field I

*  `no_input`: Specifies whether the field cannot be entered. The default is False.

 `no_input=True` The field cannot be entered in the data, but it can be populated `default` or `default_factory` defaulted by default, or assigned by a property in the data class, for example

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

1. The field in `slug` the example is specified `no_input=True`, so even if `'slug'` the field appears in the input data, it will be ignored. In the function called `__validate__` after initialization, we `slug` assign the field. So it will show up in the results.
2. The field in `update_at` the example does not accept data input, but will use `default_factory` the function in to fill the current time when the data class is initialized, and this field can be output normally, which means that subsequent operations (such as updating data to the database) will be performed together with other output fields.

!!! note

In contrast, the parameters that control the output behavior of the field are

*  `no_output`: Specifies whether the field cannot be output. The default is False.

 `no_output=True` Although not used for data output, can be accessed using properties, which can be used as dependent values for computing other data, such as
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

In this example, we declare a `no_output=True` field `access_key`, which is not output, but can be accessed by using the attribute name, so that the `key_sketch` attribute can be calculated, which is a common key semi-hidden processing scenario. The key field itself ( `access_key`) is not output, only the processed result field ( `key_sketch`) is output


!!! warning

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
 
In the example, `title ` we specify a function in the `no_output` parameter of the field, indicating that if the input is `None`, it will not be output, so in the example, when the data class is just initialized, `'title'` The field is not in the data (although you can access it using the property); `content` the field specifies that it is not entered when the value is empty, so it remains in the data when a non-empty value is passed in.

!!! note


## Mode configuration

Utype supports a more advanced “mode configuration” feature that allows the same field of a data class to behave differently in different “modes”. For example, if we need a field to be “read-only”, we actually only need it to support input and output in “read mode”

Let’s look at an example.
```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(writeonly=True)
	signup_time: datetime = Field(readonly=True)
```

In our example, we declared a User Schema data class that

1.  `username`: has no schema declaration and can be used in any schema
2.  `password`: is declared `writeonly=True`, which means that it is only used for ** Write ** schema, not for reading.
3.  `signup_time`: is `readonly=True` declared, which means that it is only used for ** Read ** schemas, not for updates.

The mechanism provided by utype allows you to declare a single data class that behaves differently in different schemas. Field provides several parameters for specifying the schema supported by the field.

*  `mode`: Specifies a pattern string in which each character represents a supported pattern. For example `mode='rw'`, the default is null, which means the field supports all patterns.
*  `readonly`: is `mode='r'` a common simplified representation of
*  `writeonly`: is `mode='w'` a common simplified representation of

!!! warning

Commonly used schema names and corresponding meanings are as follow

1.  `'r'`: Read the schema and perform information acquisition operations that do not affect the system state, such as reading the data in the data table through SQL and converting it into a Schema instance for return.
2.  `'w'`: The write/update mode is often used to update the resources of the current system, such as converting the data in the HTTP request body into a Schema instance and updating the target resources.
3.  `'a'`: Append/create mode, add a new resource to the current system, for example, convert the data in the HTTP request body into a Schema instance and create a new corresponding resource in the system

!!! Note “Distinguish `readonly`/ `immutable`”

### How the pattern is used

Although we have agreed on a common pattern name and scenario, it is actually up to you to specify and use the pattern. We can look at a few examples to understand how to use the pattern.

In these examples, we use the `'r'`/ `'w'`/ `'a'` pattern to illustrate a typical user class data read/update/create scenario

** Inherit and specify resolution options ** for different modes

The [Options](/en/references/options) configuration `mode` mode parameter is supported in to specify the mode used by the current data class or function, so you can specify different parsing options to provide data subclasses in different modes by inheriting data classes, such as
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

In that UserSchema data clas we wrote, we specified the follow fields

*  `username`: No mode is specified, indicating that input and output can be performed in any mode.
*  `password`: Specified `mode='wa'`, indicating input and output only in `'w'` mode and `'a'` mode
*  `followers_num`: a field for the number of followers of the user. If is `readonly=True` specified, indicates that only reading is supported, and creating or updating is not supported.
*  `signup_time`: user’s registration time field, if specified `mode='ra'`, indicates that only read and create modes are supported, and if specified `no_input='a'`, that is, no input is accepted in create mode, and the current time is directly calculated by using `default_factory` the function in as the registration time of the new user.

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

In the example, we can see that when data is initialized using the UserUpdate data class with the specified schema `'w'`, `'w'` data that is not supported in the schema will not be entered and will not take effect even if you try to assign it. The resulting output data is `'w'` the data fields supported in the schema.

Specifying Modes ** ** with Runtime Parsing Options

You can also use the method of the data class `__from__` for initialization, in which the first parameter is passed in data, and the support `options` parameter specifies a runtime parsing option, which can be used for dynamic specification of the mode, such as
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

Specify the mode ** in the ** function resolution option

You can also use the function’s parse option to specify the parsing mode for all data class parameters in the function, as shown in
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

Extension ** of the ** pattern

The utype does not restrict the semantics and scope of the pattern, so you can freely declare a custom pattern in the parameters of the `mode` field. Generally speaking, the pattern is represented by a lowercase letter.

Utype supports json-schema document output in different modes, so you can use only one data class to get its input and output templates in multiple mode scenarios such as read, update, create, and so on

### Modes and I/O

To specify a field as a certain mode is actually to specify that the input and output of the field are disabled in other modes. For example, if the mode of the field is `'r'` and the current parsing mode is `'w'`, then the field is invalid and will not be used for input or output.

In fact, input and output parameters can also be configured as a pattern string, such as

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

The schema fields declared for the data class Article in the example are

*  `slug`: Inputs are disabled on update ( `'w'`) and create ( `'a'`), but outputs are not disabled (that is, if assigned, they can be output as fields in the result), and inputs and outputs in other modes (such as read) are not restricted.
*  `created_at`: The mode is specified as read ( `'r'`) and create ( `'a'`), and the input in create ( `'a'`) mode is disabled. The input is ignored when creating the mode resolution, and the default value is filled in, that is, the current time, which conforms to the semantics of the field. Input and output are supported normally when reading

So you can see that when we use the create mode ( `'a'`) to initialize the article data, the input in `'"created_at"'` the data will be ignored directly, and `slug` the field will not accept the input. The function called `__validate__` after the data is initialized defines `slug` the assignment logic of the field by default, so the final result includes the passed in `title`, assigned `slug`, and filled with the default value.

## Attribute configuration

Field also supports the configuration of properties for the data class, such as

*  `immutable`: Whether the attribute is immutable. The default is False. If enabled, you cannot assign or delete the corresponding attribute of the data class instance.

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

As you can see, for `immutable=True` the field, whether you use attribute assignment or deletion, or use the dictionary method of Schema to update or delete the dictionary, an error will be thrown (thrown when updating `exc.UpdateError`, thrown `exc.DeleteError` when deleting).

!!! note

*  `repr` You can specify a Boolean variable, string, or function to control the display behavior of the field, that is, the display value in `__repr__` the and `__str__` functions, which represent the
1. `bool`: Whether to display. The default is True. If it is specified as False, the field will not be displayed even if it is provided in the data.
2. `str`: Specify a fixed display value, which is often used to hide the information of these fields
3. `Callable`: Provide a function that accepts the data value corresponding to the field as input and outputs a representation function.

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

In the example, we automatically specify a display function for `access_key` that intercepts only the first few digits for display, for `secret_key` that we specify a fixed string for display, and for `last_activity` the field, we directly disable its display


## Error handling

Field can also configure the error handling strategy for the field, that is, how to handle when the data corresponding to the field fails to pass the parsing verification. Its corresponding parameter is

*  `on_error` Configures the error handling behavior of a field. This parameter has several optional values.

1. `'throw'`: Default, throw error
2. `'exclude'`: Exclude the field from the result (this option cannot be used if the field is mandatory)
3. `'preserve'`: Keep the field in the result, that is, allow the field in the result that does not pass the verification

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

When specified `on_error='throw'` (which is also the default value), the invalid data passed by the field will be thrown directly as an error; when `on_error='exclude'` the invalid data is encountered, a warning will be given, but it will be ignored and not added to the result; when `on_error='preserve'` the invalid data is encountered, it will still be added to the result after a warning is given

!!! warning

If you want to configure an error handling policy for an entire data class, refer to


## Field dependency

Field supports specifying a series of dependent fields for the field, that is, when the input data provides the field, the dependent fields must also be provided. The parameters are as follows

*  `dependencies` Specifies a list of strings, where each string represents the name of a dependent field. Dependent fields must be defined in the current data class.

```python
from utype import Schema, Field

class Account(Schema):  
    name: str  
    billing_address: str = Field(default=None)  
    credit_card: str = Field(required=False, dependencies=['billing_address'])
```

In our declaration of the Account data class, `credit_card` the field specifies a dependency of `['billing_address']`, which means

* Must be provided if a field is provided `credit_card`
* If no field is provided `credit_card`, it `billing_address` follows its own configuration

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

As you can see, when `credit_card` a field is not provided, it can be parsed regardless of whether it is passed in `billing_address`, because `billing_address` it is an optional field, but when the data provides a `credit_card` field, it must be provided `billing_address`. Otherwise, an `exc.DependenciesAbsenceError` error is thrown.


### Attribute dependency

Field dependencies can also act on attribute fields ( `@property`), such as
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

In the data class User Schema declared in the example, the calculation `signup_days` needs to be provided `signup_time`, so it is declared as the dependency of the entire attribute.

It can be seen that the difference between attribute dependency and field dependency is that when the attribute dependency is not provided, the attribute will not be calculated or output, but will not report an error.

