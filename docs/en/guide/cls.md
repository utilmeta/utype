# Dataclasses

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

So in this document, we will introduce the declaration and usage of dataclasses in detail.

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
in utype, `Field` can be used to configure behaviors for a field. The following examples show the usage of some common `Field` configurations.
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

In Python classes, you can use `@property` decorator to declare properties, and then use functions to control access, assignment, and deletion of properties.

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

#### Control assignment

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

### Field restrictions

Not all attributes declared on a Schema are converted to fields that can be parsed and validated, utype’s dataclass fields have certain restrictions

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

In the example, several attributes in the `Static` dataclass are not qualified to be fields, so the values of these properties in the instance are not affected by the input data, thus the output data

#### Restrictions
When field names and declarations meet the restrictions, there are also some declaration restrictions to be aware of

* If field name corresponds to a method or class function in a base class, you cannot declare it as a data field in a subclass.
```python
from utype import Schema, Field

try:
	class InvalidSchema(Schema):
		items: list = Field(default_factory=list)  # wrong!
except TypeError as e:
	pass
```

	For example, Schema inherits from `dict`, the method names in the `dict` class cannot be declared as a field name in Schema. If you need to declare the same field name, you can use `alias`, such as
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

## Usage of dataclasses

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

We use `MemberSchema` as a type annotation for the field in the `GroupSchema`, indicating that the incoming data needs to conform to the structure of the declared dataclass (often a `dict` or JSON), such as
``` python
alice = {'name': 'Alice', 'level': '3'}   # dict format
bob = b'{"name": "Bob"}'                  # json format
  
group = GroupSchema(name='test', creator=alice, members=(alice, bob))  

print(group.creator)
# > MemberSchema(name='Alice', level=3)

assert group.members[1].name == 'Bob'
```

As you can see, both `dict` and JSON data can be directly converted into dataclass instances for parsing and validation.

!!! warning
	You CANNOT put JSON string / bytes directly to inititialize the dataclass, such as  `MemberSchema(b'{"name": "Bob"}')`. but dataclass provided a method called  `__from__`  to absorb such data, so you can use `MemberSchema.__from__(b'{"name": "Bob"}')`  to transform the non-dict input

#### Private dataclass
Sometimes, a dataclass will only appear in a specific class and will not be referenced by other data. In this case, the required structure can be directly defined as a class in the dataclass to facilitate code organization and namespace isolation, such as

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

In this example, `UserSchema` have declared a dataclass named `KeyInfo` in it's attributes, `KeyInfo`  is not treated as a field for not meeting the field restrictions


### Inheritance and reuse
Inheritance is an important means of reusing data structures and methods in object-oriented programming. It is also applicable to dataclasses in utype. You can inherit all fields of the parent class only by class inheritance, such as
```python
from utype import Schema, Field
from datetime import datetime

class LoginSchema(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
	password: str = Field(min_length=6, max_length=20)
	  
class UserSchema(LoginSchema):  
    signup_time: datetime = Field(readonly=True)  
```

`UserSchema` is inherit from `LoginSchema` so that `username`, `password` fields in  `LoginSchema` become a part of `UserSchema`

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

We declare corresponding mixin dataclasses for `username` and `password` fields, so any dataclass that needs them can inherit from the mixin class to get the corresponding fields.

### Logic operation
Like constraint types, dataclasses that inherit from Schema have the ability to participate in logic operation of types, as shown in
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

We logically combine the dataclass `User` with the Tuple nested type (yes, you can do that, although `Tuple[str, int]` it’s not a type, utype will convert it at the time of the operation), so that the input can either accept dictionary or JSON data (convert to `User`). or list / tuple data (convert to `Tuple[str, int]` )

### For functions
Dataclasses can also be used in functions, as type annotations for function params or returns, simply requiring the function to use `@utype.parse` decorators

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

In the example, we declared a login function, which uses `LoginForm` to accept the login form data. If the login is successful, the user name information will be returned and will be converted to the `UserInfo` instance.

!!! note
	More about function parsing: [Function parsing](/guide/func)


## Data parse and validation

In this section, we focus on how to control and adjust the parsing and validation behavior of the dataclass.

### Configure Options
utype provides an Options class to tune the parsing behavior of dataclasses and functions, which is used in the dataclass as follows

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

We declare an attribute named `__options__` in the dataclass and assign it using an instance of Options. The resolution options are passed in as parameters.

In the example, we configured `Options(addition=True)` to preserve the additional input data outside the dataclass fields. so that  `age` and `invite_code` are reserved in the output data, the commonly used options in the parsing configuration are:

* **Data processing**: `addition`, `max_params`, `min_params`, `max_depth` etc. to limit the length, depth of the input data and specify the behavior of the additional data.
* **Error handling**:  `max_errors` `collect_errors`. configure error-handling behavior, such as whether to collect all parse errors or "fail-fast"
* **invalid data**: `invalid_items`, `invalid_keys`, `invalid_values`, Configure the processing behavior of illegal/invalid data, whether to discard, keep, or throw an error.
* **parse tuning**: A series of options for adjusting parsing behavior and field behavior, such as `ignore_required`, `no_default`, `ignore_constraints`, etc.
* **alias generation**: `alias_generator`, `case_insensitive` etc., to generate aliases for fields, or to specify options that are case-sensitive or not

!!! note
	Options control the parsing and transformation for types, dataclasses and functions in utype, for more info, you can refer to [Options API References](/references/options)

You can also decalre Options for class by class decorator, such as
```python
from utype import Schema, Options

@Options(addition=True)  
class UserPreserve(Schema):  
    name: str  
    level: int = 0
```

The following is an example of a usage for the parsing Options
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

Let’s take a look at the options in the above example

* `case_insensitive=True`: accept input data case-insensitive, as in the example where the input data pass `'UserName'` for the value of `'username'`.
* `addition=False`: Indicates that any additional data will raises an error. In the example, we input an additional parameter `'Token'`, which will be detected and thrown as an error.
* `collect_errors=True`: collect all the errors in the data and throw them together, which is more convenient for debugging. We can use `exc.CollectedParseError` it to catch the packaging error thrown, for example, in the example, we catch the error information of all parameters together. (`collect_errors` is False by default)

!!! note
	`addition` is None by default, means ignores additional input, `addition=True` means preserve additional input, `addition=False` means throw an error for additional input

Options also supports other declaration methods. such as

**Class inheritance**
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

**Class decorator**
```python
from utype import Schema, Options

@Options(addition=True)  
class UserPreserve(Schema):  
    name: str  
    level: int = 0
```

#### Runtime parsing option
utype supports passing in a parsing option at dataclass initialization (at parsing time) to tune the parsing behavior at runtime

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

By passing `options` parameters in the function `__from__` of the dataclass, you can pass a runtime Options that utype will parse the data according to.


#### Inheritance and Extend
When you inherit a dataclass, you also inherit its parsing options, so you can also declare global parsing options.

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

As you can see, if the subclass does not declare options, it will directly inherit the parent class. Another way is

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
Any predefined parsing options sometimes cannot replace the flexibility brought by custom function logic, so utype supports custom initialization `__init__` functions in dataclasses to achieve more customized parsing logic, such as

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

In the example, we perform verification before calling the initialization method of the parent class (by `super()`) in custom `__init__`, so as to avoid the situation that the power operation produces a complex result.

As you can see, the custom `__init__` function in the dataclass will get the ability of type resolution by default, that is, you can declare the type and field configuration in the `__init__` function, and the syntax is identical to [Function](/guide/func) . When the function is called `__init__`, it will be parsed according to the parameter declaration of the function, and then execute your initialization logic.

And only if you define the `__init__` function, you can pass positional parameters to initialize dataclass as in the example.

!!! note
	after customize  `__init__` , if you still want to support runtime Options, you should accept and pass `__options__` to `super().__init__` , otherwise (like in the example) dataclass will no longer support runtime options

### Post-parse function
utype also supports declaring the post-parse function `__validate__` to call after parsing. The usage is as follows
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
We declare a Schema class that carries HTTP request information, define `__validate__` functions in it, and perform some validation and assignment logic in it.

## Other declaration methods

In the previous example, we only introduced the use of inheritance Schema to define dataclasses, in fact, there are two ways to declare dataclasses in utype.

1. Inherit the base class of the predefined dataclass
2. Make your own using `@utype.dataclass` decorators

Among them, utype currently provides the following predefined data base classes

 * **DataClass**: does not have any base class and supports logical operations
 * **Schema**: Inherited from dict dictionary class, providing all methods of attribute reading and writing and dictionary, and supporting logical operation

Let’s look at the way dataclasses are manufactured using `@utype.dataclass` decorators. Other predefined data base classes can be thought of as manufacturing with some decorator parameters fixed.

### `@utype.dataclass` Decorator

We can use `@utype.dataclass` decorators to decorate a class to make it a dataclass, such as

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

`@utype.dataclass` has some params to customize the generation behavior of the dataclass, including

* `no_parse`: When enabled, data will not be parsed and verified, but only be mapped and assigned to the attribute. The default value is False.
* `post_init`: a function is passed in and called after the `__init__` function is completed. It can be used to write custom validation logic.
* `set_class_properties`: Whether to reassign the class attribute corresponding to the field to one `property`, so as to obtain the parsing capability and protection of the field configuration during attribute assignment and deletion at runtime. The default is False.

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

`UserA` with `set_class_properties=False` will not be affected. If you access it directly, you will get the corresponding attribute value. If the attribute value is not defined, an AttributeError will be thrown directly, which is consistent with the behavior of the ordinary class.

But when enabled `set_class_properties=True`, the class attributes will be re-assigned as an `property` instance, so that the assignment and deletion of the field attributes in the instance become controllable (perform type parsing at assignment, perform protection at deletion)

`@utype.dataclass` also provides some hook function params for attribute assignment and deletion

* `post_setattr`: This function is called after the field attribute of the instance is assigned ( `setattr`), and some custom processing behaviors can be performed.
* `post_delattr`: This function is called after the delete ( `delattr`) operation of the field property of the instance, and some custom processing behaviors can be performed.

!!! note
	you can only pass `post_setattr` or `post_delattr` when setting `set_class_properties=True`

`@utype.dataclass` also provides some dataclass function generation params, including

* `repr`: provide `__repr__` and `__str__` methods so that you get a highly readable output when you use `print(inst)` or `str(inst)` `repr(inst)`, displaying the fields and corresponding values. default is True.
* `contains`: provide `__contains__` function so that you can use `name in instance` to determine whether a field is in the dataclass, default is False
* `eq`: provide `__eq__` function so that two instances of the dataclass with identical data can use `inst1 == inst2` to determine, default is False

There are also parameters that control the parser and parsing options.

* `parser_cls`: Specifies the core parser class responsible for parsing class declarations and parsing data. The default is `utype.parser.ClassParser`.
* `options`: Specify a `Options` instance to control parsing behavior

#### Logic operation
If you need to declare a dataclass to support logical operations, you need to use `utype.LogicalMeta` as the metaclass
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

!!! note
	dataclass that inherit from `Schema` or `DataClass` will directly gain the logicla operation ability, because their metaclass is  `utype.LogicalMeta` already
