# Data Classes

dataclass is a class that has a set of properties that are also required to satisfy certain types or constraints, such as
```python
class Article:  
    slug: str  
    content: str  
    views: int = 0  
  
    def __init__(self, slug: str, content: str, views: int = 0):  
		import re
		if not isinstance(slug, str) \  
				or not re.findall(slug,  r"[a-z0-9]+(?:-[a-z0-9]+)*") \  
				or len(slug) > 30:  
			raise ValueError(f'Bad slug: {slug}')  
		if not isinstance(content, str):  
			raise ValueError(f'Bad content: {content}')  
		if not isinstance(views, int) or views < 0:  
			raise ValueError(f'Bad views: {views}')  
		self.slug = slug  
		self.content = content  
		self.views = views
```

!!! note
	There are many usage of the above dataclass, such as ORM model 

When defining such class, we often need to declare a `__init__` function to receive its initialization parameters, and do type and constraint checking in it, otherwise we may get unusable data, such as

```python
bad_article = Article(title=False, content=123, views='text value')
```

With utype, the above data structur can be declared in a more concise way and gain more capabilities, such as
```python
from utype import Schema, Rule, Field

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"
    
class ArticleSchema(Schema):
	slug: Slug = Field(max_length=30)
	content: str 
	views: int = Field(ge=0, default=0)
```

It’s also very straightforward to use
```python
article = ArticleSchema(slug='my-article', content=b'my article body')
print(article)
#> ArticleSchema(slug='my-article', content='my article body', views=0)
print(article.slug)
#> 'my-article'

from utype import exc

try:
	article.slug = '@invalid slug'
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['slug'] failed: 
	Constraint: <regex>: '[a-z0-9]+(?:-[a-z0-9]+)*' violated
	"""

article.views = '3.0'   # will be convert to int

print(dict(article))
# > {'slug': 'my-article', 'content': 'my article body', 'views': 3}
```
You can get

* Automatic `__init__` to take input data, perform validation and attribute assignment
* Providing  `__repr__` and `__str__` to get the clearly print output of the instance
* parse and protect attribute assignment and deletion to avoid dirty data

So in this document, we will introduce the declaration and usage of data classes in detail.

## Define fields

There are many ways to declare a field in a dataclass, the simplest being
```python
from utype import Schema

class UserSchema(Schema):
    name: str
    age: int = 0
```

The declared fields are

* `name`:  only with type `str`, which is a required parameter
* `age`: declared `int` type , and default value 0. which makes It an optional parameter. If not passed in, the default value 0 will be used as the field value in the instance.

However, in addition to the type and default value, a field often needs to be configured with other behaviors, so the following usage is needed.

### Configure Field
in utype, `Field` can be used to configure the behaviors for a field. The following examples show the usage of some common Field configurations.
```python
from utype import Schema, Field  
from datetime import datetime  
from typing import List  
  
  
class ArticleSchema(Schema):  
    slug: str = Field(  
        regex=r"[a-z0-9]+(?:-[a-z0-9]+)*",  
        immutable=True,  
        example='my-article',  
        description='the url route of an article'  
    )  
    content: str = Field(alias_from=['text', 'body'])  
    # body: str = Field(required=False, deprecated=True)  
    views: int = Field(ge=0, default=0)  
    created_at: datetime = Field(  
        alias='createdAt',  
        required=False,  
    )  
    tags: List[str] = Field(default_factory=list, no_output=lambda v: not v)


article = ArticleSchema(  
    slug=b'test-article',  
    body='article body',  
    tags=[]
) 
```

In the example.

* `slug`: the URL route of an article. the `regex` constraint is specified for the field and is set `immutable=True`, meaning that the field cannot be assigned to or be deleted

```python
from utype import exc

try:  
    article.slug = 'other-slug'  
except exc.UpdateError as e:  
    print(e)  
    """  
    ArticleSchema: Attempt to set immutable attribute: ['slug']    
    """  
```

Sample values `example` and descriptions `description` are also specified to better describe the purpose of the field.

* `content`: the content field of the article, which uses `alias_from` to specify some aliases that can be converted from. This feature is very useful for field renaming and version compatibility. For example, the content field name of the previous version is `'body'`. Is deprecated and used `'content'` as the name of the content field in the current version

* `views`: the page view field of the article, specifies a `ge` minimum value constraint and a default value 0, so the default value 0 is automatically filled in when there is no input, and an error is thrown when the input value or the assigned value violates the constraint.

```python
from utype import exc  

assert article.views == 0
try:  
    article.views = -3  
except exc.ParseError as e:  
    print(e)  
    """  
    parse item: ['views'] failed: Constraint: <ge>: 0 violated    
    """
```

* `created_at`: the creation time field of the article, using `alias` to specify the output name `'createdAt'`, using `required=False` to declare an optional field with no default value, so if the field not provided in the input data, it will not be in the instance, such as
```python
assert 'createdAt' not in article   # True
article.created_at = '2022-02-02 10:11:12'  
print(dict(article))  
# {
# 'slug': 'test-article', 
# 'content': 'article body',
# 'views': 0, 
# 'createdAt': datetime.datetime(2022, 2, 2, 10, 11, 12)
# }
```

When a value is assigned to `created_at`, it is converted to the field’s type (`datetime`), and in the output data, the field is using the `alias` specified name `'createdAt'`

* `tags`: the label field of the article specifies that the factory function of the default value is list, which means that if this field is not provided, an empty list ( `list()`) will be created as the default value. In addition, the `no_output` function is specified, which means that no output will be made when the value is empty.

!!! warnings
	utype can parse attribute assignment only if you assign it directly (like the above example), if you use something like `article.tags.append(obj)` to operate `tags`, you will not gain the parsing ability

`Field` provided many configuration params, including

* **Optional and default**: `required`, `default`, `default_factory` to indicate the optional field and it's default value / factory method
* **Description and marking**: `title`, `description`, `example`, `deprecated` etc. used to document a field, specify an example, or to indicate whether it is deprecated
* **Constraintsn**: includes all constraints in [Rule](/references/rule), such as `gt`, `le`, `max_length`, `regex` 
* **Alias configuration**: `alias`, `alias_from`, `case_insensitive`, etc. used to specify aliases for fields other than attribute name
* **Mode configuration**: `readonly`, `writeonly` `mode`, etc., to support multiple parse mode and control the behavior of field in certain mode.
* **Input and output**: `no_input`, `no_output`, used to control the input and output behavior of the field
* **Attribute behaviors**: `immutable`, `secret` used to control the immutability and display behavior of the corresponding attribute of the field.

For more complete parameters and usage of `Field`, you can read [Field API References](/references/field)

!!! note
	Field only take effect in a dataclass attribute or function paramaters with `@utype.parse`, for an isolated variable, it won't work

### Declare `@property`

In Python classes, you can use `@property` decorators to declare properties, and then use functions to control access, assignment, and deletion of properties.

utype also supports the use of `@property` to gain more control of property behavior, let's start with a simple example.
```python
from utype import Schema
from datetime import datetime

class UserSchema(Schema):
	username: str
	signup_time: datetime
	
	@property  
	def signup_days(self) -> int:  
	    return (datetime.now() - self.signup_time).total_seconds() / (3600 * 24)

user = UserSchema(username='test', signup_time='2021-10-11 11:22:33')

assert isinstance(user.signup_days, int)
```

The property `signup_days` counts the number of registered days using the field `signup_time` and is declared as type `int`,  so that utype will convert the result of getter function to `int` when accessing the property

#### Control assignment using setter

With `@property` attributes, you can also control the assignment by declare `setter`, which is also a common practice to make dependencies updates, or to hide certain private fields from exposure, such as
```python
from utype import Schema, Field  

class ArticleSchema(Schema):  
    _slug: str  
    _title: str  
  
    @property  
    def slug(self) -> str:  
        return self._slug  
  
    @property  
    def title(self) -> str:  
        return self._title  
  
    @title.setter  
    def title(self, val: str):  
        self._title = val  
        self._slug = '-'.join([''.join(filter(str.isalnum, v))  
                               for v in val.split()]).lower()  
  
```

In the example, we use the setter of `title` to update `slug` property. so user of the class do not need to operate `slug` directly.

If the property does not declare a setter, it is not assignable (immutable), so it is more native to declare an immutable field.

!!! note
	In dataclasses, all params in initialization will be assigned to the corresponding attribute, which will trigger the setter for property

#### Configure Field for properties

utype supports configuring the `Field` to `@property`, such as
```python
from utype import Schema, Field  

class ArticleSchema(Schema):  
    _slug: str  
    _title: str  
  
    @property  
    def title(self) -> str:  
        return self._title  
  
    @title.setter  
    def title(self, val: str = Field(max_length=50)):  
        self._title = val  
        self._slug = '-'.join([''.join(filter(str.isalnum, v))  
                               for v in val.split()]).lower()  
	  
    @property  
    @Field(dependencies=title, description='the url route of article')
    def slug(self) -> str:  
        return self._slug  
```

`Field` can be configured on the getter and setter of the property, and their usages are

**getter**: use `Field` instance as a decorator to decorate the underlying function for `@property`, common params are

* `no_output=True`: do not output the calculated property value
* `dependencies`: specify the dependency fields for getter calculation. The calculation will be performed only when all the dependencies of the attribute field are provided.
* `alias`: specifies the field alias for the output

**setter**: use `Field` instance as default value for the input param of setter function,  common params are

* `no_input=True`: indicates that input is not accepted during initialization, and only can be assigned by attribute assignment
* `immutable=True`: indicates that the attribute assignment is not accepted and can only be entered at initialization time.
* `alias_from`: specify a list of field aliases

!!! warning
	if you specify both `no_input=True` and `immutable=True` will make the setter useless

Let’s take a look at the behavior of these properties
```python
article = ArticleSchema(title='My Awesome article!')
print(article.slug)
# > 'my-awesome-article'

try:
	article.slug = 'other value'   # cannot set attribute
except AttributeError:
	pass

article.title = b'Our Awesome article!'
print(article['slug'])
# > 'our-awesome-article'

print(dict(article))
# > {'slug': 'our-awesome-article', 'title': 'Our Awesome article!'}

from utype import exc
try:
	article.title = '*' * 100
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['title'] failed: Constraint: <max_length>: 50 violated
	"""
```

After specified `dependencies=title` for `slug`, when `title` is assigned, `slug` is also updated

### Field Restrictions

Not all attributes declared on a Schema are converted to fields that can be parsed and validated, and utype’s data class fields have certain restrictions

* Attributes that begin with an underscore (`'_'`) are not treated as fields. which tend to be reserved for classes and are not treated as fields by utype
* All  `@classmethod`, `@staticmethod`, and instance methods will not be treated as fields
* If you use a `ClassVar` to annotate an attribute, it means that the attribute is a class variable, not an instance variable, which will aslo not treated as a field.

```python
from utype import Schema
from typing import ClassVar, Final

class Static(Schema):
	_private: int = 0

	@classmethod
	def generate(cls): pass
	
	VERSION: ClassVar[tuple] = (0, 2, 1)

static = Static()
print(static.VERSIOn)
# > (0, 2, 1)

print(dict(static))
# > {}
```

In the example, several attributes in the Static dataclass are not qualified to be fields, so the values of these properties in the instance are not affected by the input data, thus the output data

#### Restrictions
When field names and declarations meet the naming restrictions, there are also some declaration restrictions to be aware of

* If field name corresponds to a method or class function in a base class, you cannot declare it as a data field in a subclass.
```python
from utype import Schema, Field

try:
	class InvalidSchema(Schema):
		items: list = Field(default_factory=list)  # wrong!
except TypeError as e:
	pass
```

	For example, Schema inherits from the `dict`, the method name in the `dict` cannot be declared as a field name. If you need to declare the same property name, you can use `alias`, such as
```python
from utype import Schema, Field

class ItemsSchema(Schema):
	items_list: list = Field(alias='items', default_factory=list)

data = ItemsSchema(items=(1, 2))   # ok
print(data.item_list)
# > [1, 2]
print(data['items'])
# > [1, 2]
print(data.items)
# > <built-in method items of ItemsSchema object>
```

* If a field declared `Final` annotation in a parent class, it means that it cannot be overridden or assigned again, so a subclass cannot declare a field of the same name
```python
from utype import Schema
from typing import Final

class Base(Schema):
	base_name: Final[str] = 'base'

try:
	class Child(Base):
		base_name = 'child'   # wrong!
except TypeError as e:
	pass
```

!!! note
	Using `Final` as type annotation also marks the field `immutable=True`, if a value assigned to `Final` field, then it is also `no_input=True`, which meets the declaration of `Final`

## Usage of data classes

In this section, we’ll focus on how dataclasses are used.

### Nesting and compounding
dataclass is itself a type, so we can use the same syntax to define nested data structures, as shown in

```python
from utype import Schema, Field
from typing import List

class MemberSchema(Schema):
    name: str
    level: int = 0

class GroupSchema(Schema):
	name: str
	creator: MemberSchema
	members: List[MemberSchema] = Field(default_factory=list)
```

We use `MemberSchema` as a type annotation for the field in the `GroupSchema`, indicating that the incoming data needs to conform to the structure of the declared data class (often a dictionary, or JSON), such as
``` python
alice = {'name': 'Alice', 'level': '3'}   # dict format
bob = b'{"name": "Bob"}'                  # json format
  
group = GroupSchema(name='test', creator=alice, members=(alice, bob))  

print(group.creator)
# > MemberSchema(name='Alice', level=3)

assert group.members[1].name == 'Bob'
```

As you can see, both `dict` and JSON data can be directly converted into data class instances for parsing and validation.

#### Private dataclass
Sometimes, a data class we need to define will only appear in a specific class and will not be referenced by other data. In this case, the required structure can be directly defined as a class in the data class to facilitate code organization and namespace isolation, such as

```python
from utype import Schema, Field
from datetime import datetime
from typing import List

class UserSchema(Schema):
    name: str
    level: int = 0
    
	class KeyInfo(Schema):
		access_key: str
		last_activity: datetime = None
		
	access_keys: List[KeyInfo] = Field(default_factory=list)

user = UserSchema(**{'name': 'Joe', 'access_keys': {'access_key': 'KEY'}})
print(user.access_keys)
# > [UserSchema.KeyInfo(access_key='KEY', last_activity=None)]
```

In this example, we `UserSchema` have declared a data class named `KeyInfo` in, but because the admission rules for the field are not met, `KeyInfo` the class is not treated as a field, but remains as it is


### Inheritance and reuse
Inheritance is an important means of reusing data structures and methods in object-oriented programming. It is also applicable to data classes. You can inherit all fields of the parent class only by declaring the subclass of the data class in the way of class inheritance, such as
```python
from utype import Schema, Field
from datetime import datetime

class LoginSchema(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
	password: str = Field(min_length=6, max_length=20)
	  
class UserSchema(LoginSchema):  
    signup_time: datetime = Field(readonly=True)  
```

The data class `LoginSchema` used to handle the login is `UserSchema` inherited so that the `username` `password` fields defined in it are part of the fields `UserSchema` in.

You can also use multiple inheritance to reuse data structures, or use the idea of Mixin to atomize common parts of a data structure and combine them in the desired structure, for example
```python
from utype import Schema, Field
from datetime import datetime

class UsernameMixin(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  

class PasswordMixin(Schema):  
    password: str = Field(min_length=6, max_length=20)

class ProfileSchema(UsernameMixin):  
    signup_time: datetime = Field(readonly=True)  

class LoginSchema(UsernameMixin, PasswordMixin):
	pass

class PasswordAlterSchema(PasswordMixin):
	old_password: str
```

We declare corresponding mixin data classes for `username` and `password`, so any data class that needs them can inherit from the mixin class to get the corresponding fields.

### Logic operation
Like constraint types, data classes that inherit from Schema have the ability to participate in type logic operations, as shown in
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

We logically combine the data class `User` with the Tuple nested type (yes, you can do this, although `Tuple[str, int]` it’s not a type, utype will convert it at the time of operation), so that the input can either accept dictionary or JSON data. You can also accept list or tuple data, as long as you can convert to the declared type.

### For functions
Data classes can also be used in functions, as type hints for function arguments or returned results, simply requiring the function to use `@utype.parse` decorators

```python
from utype import Schema, Field, parse
from typing import Optional

class UserInfo(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
  
class LoginForm(UserInfo):  
    password: str = Field(min_length=6, max_length=20)  

password_dict = {"alice": "123456"}
# pretend this is a database

@parse
def login(form: LoginForm) -> Optional[UserInfo]:
	if password_dict.get(form.username) == form.password:
		return {"username": form.username}
	return None

request_json = b'{"username": "alice", "password": 123456}'

user = login(request_json)
print(user)
# > UserInfo(username='alice')
```

In the example, we declare a login function, which uses LoginForm to accept the login form. If the login is successful, the user name information will be returned and will be converted to the UserInfo data class instance.


## Data parse and validation

In this section, we focus on how to control and adjust the parsing and validation behavior of the data class.

### Configure Options
Utype provides an Options class to mediate the parsing behavior of data classes and functions, which is used in the data class as follows

```python
from utype import Schema, Options

class UserPreserve(Schema):  
    __options__ = Options(addition=True)  
    
    name: str  
    level: int = 0

user = UserPreserve(name='alice', age=19, invite_code='XYZ')
print(user)
# > UserPreserve(name='alice', level=0, age=19, invite_code='XYZ')
print(user.age)
# > 19
```

We declare a property named `__options__` in the data class and assign it using an instance of Options. The resolution options are passed in as parameters.

In the example, the option we configured is `addition=True` to express the input data outside the reserved field range. The commonly used options in the parsing configuration include:

* **Data processing options**: `addition`, `max_params`, `min_params`, `max_depth` etc. Limit the length, depth, etc. Of the input data and specify the behavior of the data beyond the range of the field.
* **Error handling options**:  `max_errors` `collect_errors` Configure error-handling behavior, such as whether to collect all parse errors.
* **Illegal data option**: `invalid_items`, `invalid_keys`, `invalid_values`, Configure the processing behavior of illegal data, whether to discard, keep, or throw an error.
* **tuning options**: A series of options for adjusting parsing behavior and field behavior, such as `ignore_required`, `no_default`, `ignore_constraints`, etc.
* **alias options**: `alias_generator`, `case_insensitive` etc., to generate aliases for fields, or to specify options that are case-sensitive or not


The following is an example of a usage scenario for the parse option
```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    __options__ = Options(  
	    case_insensitive=True,  
        addition=False,
        collect_errors=True
    )  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)  
  
form = {  
    'UserName': '@attacker',  
    'Password': '12345',  
    'Token': 'XXX'  
}

try:
	LoginForm(**form)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['Token'] exceeded
	"""
```

Let’s look at the parsing options in the example one by one.

*  `case_insensitive=True` Indicates to accept data in a case-insensitive way, as in the example where the input data is `'UserName'` used to pass `'username'` the value of the field.
*  `addition=False`: Indicates that input data outside the field is not accepted. In the example, we entered an extra parameter `'Token'` that is not in the field, which will be detected and thrown as an error.
*  `collect_errors=True`: In general, when utype detects that there is an error in the input data, it will throw it directly. However, opening `collect_errors` utype allows utype to collect all the errors in the data and throw them together, which is more convenient for debugging. We can use `exc.CollectedParseError` it to catch the packaging error thrown, for example, in the example, we catch the error information of all parameters together.

In addition to configuring resolution options by declaring an instance of Options, you can also use a class approach, such as
```python
from utype import Schema, Options, Field

class LoginForm(Schema):  
    class __options__(Options):  
        addition = False  
        collect_errors = True  
        case_insensitive = True  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)
```


#### Runtime parsing option
In addition to specifying parsing options in the class declaration, utype also supports passing in a parsing option at data class initialization (at parsing time) to tune the parsing behavior at run time

```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)

options = Options(  
	addition=False,
	collect_errors=True
) 

form = {  
    'username': '@attacker',  
    'password': '12345',  
    'token': 'XXX',
}

try:
	LoginForm.__from__(form, options=options)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['token'] exceeded
	"""
```

By passing `options` parameters in the function of `__from__` the data class, you pass a runtime parsing option that utype will parse the data according to.


#### Inheritance and Extend
When you inherit a data class, you also inherit its parsing options, so you can also declare global parsing options.

```python
import utype

class Schema(utype.Schema):
	__options__ = utype.Options(
		 case_insensitive=True,
		 collect_errors=True,
	)

class LoginForm(Schema): 
	username: str = utype.Field(regex='[0-9a-zA-Z]{3,20}')  
	password: str = utype.Field(min_length=6, max_length=20)

print(LoginForm.__options__)
# > Options(collect_errors=True, case_insensitive=True)
```

As you can see, if the subclass does not declare additional resolution options, it will directly follow the parent class. Another way to state this example is

```python
import utype

class Options(utype.Options):
	 case_insensitive = True
	 collect_errors = True
	 
class LoginForm(utype.Schema): 
	class __options__(Options): pass
	
	username: str = utype.Field(regex='[0-9a-zA-Z]{3,20}')  
	password: str = utype.Field(min_length=6, max_length=20)

print(LoginForm.__options__)
# > Options(collect_errors=True, case_insensitive=True)
```

The example defines a custom parsing option base class that you can freely inherit, combine, and reuse.


### Custom `__init__` function
Any predefined parsing options sometimes cannot replace the flexibility brought by custom function logic, so utype supports custom initialization `__init__` functions in data classes to achieve more customized parsing logic, such as

```python
from utype import Schema, exc

class PowerSchema(Schema):  
    result: float  
    num: float  
    exp: float  
  
    def __init__(self, num: float, exp: float):  
        if num < 0:  
            if 1 > exp > -1 and exp != 0:  
                raise exc.ParseError(f'operation not supported, '  
                                     f'complex result will be generated')  
        super().__init__(  
            num=num,  
            exp=exp,  
            result=num ** exp  
        )

power = PowerSchema('3', 3)
assert power.result == 27

try:
	PowerSchema(-0.5, -0.5)
except exc.ParseError as e:
	print(e)
	"""
	operation not supported, complex result will be generated
	"""
```

In the example, we perform joint verification on the parameters before calling the initialization method of the parent class for parsing verification, so as to avoid the situation that the power operation produces a complex result.

As you can see, the custom `__init__` function in the data class will get the ability of type resolution by default, that is, you can declare the type and field configuration in the `__init__` function, and the syntax is identical to [Function](/en/guide/func) . When the function is called `__init__`, it will be parsed according to the parameter declaration of the function, and then execute your initialization logic.

And only if you define the `__init__` function, you can use the order parameter method to initialize as in the example.


### Post-parse function
In addition to customizing the processing logic before parsing through user-defined `__init__` functions, utype also supports declaring the check function `__validate__` after parsing. The usage is as follows
```python
from utype import Schema, Field
from urllib.parse import urlparse

class RequestSchema(Schema):  
    url: str  
    method: str = Field(enum=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])  
    body = None  
    secure: bool = None
  
    def __validate__(self):  
        if self.method == 'GET':
	        if self.body:
		        raise ValueError('GET method cannot specify body')
		parsed = urlparse(self.url)
		if not parsed.scheme:
			raise ValueError('URL schema not specified')
		self.secure = parsed.scheme in ['https', 'wss']
```
We declare a Schema class that carries HTTP request information, define `__validate__` functions in it, and perform some checksum assignment logic in it.

### Register the transformer
In utype, all types can register converter functions to define the conversion logic from input data to the initialization function of the calling type, and the data class as a type is no exception.

The default data class conversion function is as follows

```python
@register_transformer(
    attr="__parser__",
    detector=lambda cls: isinstance(getattr(cls, "__parser__", None), ClassParser),
)
def transform(transformer, data, cls):
    if not isinstance(data, Mapping):
        # {} dict instance is a instance of Mapping too  
        if transformer.no_explicit_cast:
            raise TypeError(f"invalid input type for {cls}, should be dict or Mapping")
        else:
            data = transformer(data, dict)
    if not transformer.context.vacuum:
        parser: ClassParser = cls.__parser__
    if parser.context.allowed_runtime_options:
        # pass the runtime options  
        data.update(__options__=transformer.context)
    return cls(**data)
```

Its logic is mainly
1. If the input data is not of dictionary or Mapping type, it will be converted first (for example, the conversion from JSON string to dictionary data can be completed).
2. If the data class allows run-time parsing options to be passed in, they are passed
3. Finally, the converted data is used to call the initialization function of the data class

such as in the following examples
```python
from utype import Schema

class MemberSchema(Schema):
    name: str
    level: int = 0

class GroupSchema(Schema):
	name: str
	creator: MemberSchema
  
group = GroupSchema(name='test', creator='{"name": "Bob"}')  
```

When GroupSchema detects that the data type (`str`) passed in the creator field does not conform to the declared type Member Schema, it will look for the converter function of the expected type Member Schema, and input the data as a parameter to the converter function after finding it. Finally, get the desired type instance.

You can register conversion functions for your data classes to customize how nonconforming data is converted. For example, you can choose to reject all input that is not an instance of the data class.
```python
from utype import Schema, exc, register_transformer

class StrictUser(Schema):
    name: str
    level: int = 0

@register_transformer(StrictUser)  
def transform(transformer, data, cls):  
	raise TypeError('type mismatch')

class GroupSchema(Schema):
	name: str
	creator: StrictUser

try:
	GroupSchema(name='test', creator='{"name": "Bob"}')  
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['creator'] failed: type mismatch
	"""
```

The parameters of the converter function are, in order,

1. Type converter TypeTransformer instance
2. the input data
3. the type class


## Other declaration methods

In the previous example, we only introduced the use of inheritance Schema to define data classes, in fact, there are two ways to declare data classes in utype.

1. Inherit the base class of the predefined data class
2. Make your own using `@utype.dataclass` decorators

Among them, utype currently provides the following predefined data base classes

 * **DataClass**: does not have any base class and supports logical operations
 * **Schema**: Inherited from dict dictionary class, providing all methods of attribute reading and writing and dictionary, and supporting logical operation

Let’s look at the way data classes are manufactured using `@utype.dataclass` decorators. Other predefined data base classes can be thought of as manufacturing with some decorator parameters fixed.

###  `@utype.dataclass` Decorator

We can use `@utype.dataclass` decorators to decorate a class to make it a data class, such as

```python
import utype

@utype.dataclass
class User:  
    name: str = utype.Field(max_length=10)  
    age: int

user = User(name='bob', age='18')
print(user)
# > User(name='bob', age=18)
```

There are a series of parameters in `@utype.dataclass` the decorator to customize the generation behavior of the data class, including

*  `no_parse`: When enabled, data will not be parsed and verified, and only the input data will be mapped and assigned to the attribute. The default value is False.
*  `post_init`: a function is passed in and called after the `__init__` function is completed. It can be used to write custom validation logic.
*  `set_class_properties`: Whether to reassign the class attribute corresponding to the field to one `property`, so as to obtain the parsing capability and protection of the field configuration during attribute assignment and deletion at runtime. The default is False.

We can intuitively compare the difference between whether it is enable `set_class_properties` or not.
```python
import utype

@utype.dataclass
class UserA:  
    name: str = utype.Field(max_length=10)  
    age: int

@utype.dataclass(set_class_properties=True)
class UserB:  
    name: str = utype.Field(max_length=10)  
    age: int

print(UserA.name)
# > <utype.parser.field.Field object>
print(UserB.name)
# > <property object>

try:
	print(UserA.age)
except AttributeError as e:
	print(e)
	"""
	AttributeError: type object 'UserA' has no attribute 'age'
	"""

print(UserB.age)
# > <property object>
```

The attribute of the default `set_class_properties=False` data class will not be affected. If you access it directly, you will get the corresponding attribute value. If the attribute value is not defined, an AttributeError will be thrown directly, which is consistent with the behavior of the ordinary class.

After it is enabled `set_class_properties=True`, the class attributes corresponding to all fields will be re-assigned as an `property` instance, so that the update and deletion of the field attributes in the instance become controllable. The parameters controlling the attribute assignment include

*  `post_setattr`: This function is called after the field attribute of the instance is assigned ( `setattr`), and some custom processing behaviors can be performed.
*  `post_delattr`: This function is called after the delete ( `delattr`) operation of the field property of the instance, and some custom processing behaviors can be performed.

*  `repr`: Are the classes `__repr__` and `__str__` methods modified so that you get a highly readable output when you use `print(inst)` or `str(inst)` `repr(inst)`, Display the fields and corresponding values in the data class instance. The default value is True.
* A `__contains__` `contains` function you can use `name in instance` to determine whether a field is in the data class.
*  `eq` Whether to generate a function of the data class `__eq__` so that two instances of the data class whose data are equal are `inst1 == inst2` judged to be equal.

There are also parameters that control the parser and parsing options.

*  `parser_cls`: Specifies the core parser class responsible for parsing class declarations and parsing data. The default is.
*  `options`: Specify an Options to control parsing behavior

#### Logic operation
If you need to declare a data class to support logical operations, you need to use `utype.LogicalMeta` as the metaclass
```python
import utype
from typing import Tuple

@utype.dataclass  
class LogicalUser(metaclass=utype.LogicalMeta):  
    name: str = utype.Field(max_length=10)  
    age: int

one_of_user = LogicalUser ^ Tuple[str, int]

print(one_of_user({'name': 'test', 'age': '1'}))
# > LogicalUser(name='test', age=1)

print(one_of_user([b'test', '1']))
# > ('test', 1)
```
