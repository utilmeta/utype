# 数据类的解析

数据类指的是一种常见的类，它有一系列属性（字段），这些字段往往也需要满足某些类型或约束的要求，比如
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
	数据类的使用场景有很多，比如 Web 开发中的 ORM 模型

在定义这样的类时，我们往往需要声明一个 `__init__` 函数来接收它的初始化参数，也需要在其中进行一些类型和约束校验，不然我们可能会得到无法使用的数据，比如

```python
bad_article = Article(title=False, content=123, views='text value')
```

而使用 utype，上述例子中的数据结构可以用更简洁的方式声明，并获得更多的能力，如
```python
from utype import Schema, Rule, Field

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"
    
class ArticleSchema(Schema):
	slug: Slug = Field(max_length=30)
	content: str 
	views: int = Field(ge=0, default=0)
```

它的用法也非常的简单直观
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
你可以直接获得

* 无需声明 `__init__` 便能够接收对应的参数，并且完成类型转化和约束校验
* 提供清晰可读的 `__repr__` 与 `__str__` 函数使得在输出和调试时方便直接获得内部的数据值
* 在属性赋值或删除时根据字段的类型与配置进行解析与保护，避免出现脏数据
* 能够直接作为字典数据进行传参或序列化

所以本篇文档我们来详细介绍数据类的声明和用法

## 声明数据字段

在数据类中声明字段有很多种方式，最简单的方式如下
```python
from utype import Schema

class UserSchema(Schema):
    name: str
    age: int = 0
```

其中声明的字段有

* `name`：仅声明类型为 `str`，是一个必传参数
* `age`：声明了类型为 `int`，并声明了默认值 0，是一个可选参数，如果没有传入则会使用默认值 0 作为实例中的字段值

但是一个字段除了类型与默认值外，往往还需要其他行为的配置，这时就需要使用下面的用法

### 配置 Field 字段
Field 可以为字段配置更多丰富的行为，只需要将 Field 类的实例作为该字段的属性值/默认值，就可以获得其参数中声明的字段配置

下面示例一些常用的 Field 配置的用法，我们还是使用文章的数据结构来示例
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

print(article)  
# > ArticleSchema(slug='test-article', content='article body', views=0)  
```

我们逐个看一下例子中声明的字段

* `slug`：文章的 URL 路径字段，使用 `regex` 为字段指定了正则约束，并且设置了 `immutable=True`，意味着字段不可被修改，还指定了示例值 `example` 和描述 `description` 用于更好的说明字段的用途

```python
try:  
    article.slug = 'other-slug'  
except AttributeError as e:  
    print(e)  
    """  
    ArticleSchema: Attempt to set immutable attribute: ['slug']    
    """  
```

* `content`：文章的内容字段，其中使用 `alias_from` 参数指定了一些可以从中转化的别名，这个特性对于字段的更名和版本兼容非常有用，比如上个版本的内容字段名称是 `'body'`，在当前版本中被废弃并使用了 `'content'` 作为内容字段的名称

* `views`：文章的访问量字段，指定了 `ge` 最小值约束和默认值 0，所以当没有输入时会自动填入默认值 0，当输入的值或赋值的值违背约束时会抛出错误

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

* `created_at`：文章的创建时间字段，使用 `alias` 指定了字段在输出时的别名为 `'createdAt'`，使用 `required=False` 标记这是一个可选字段，并且没有指定默认值，所以当你没有输入该字段时，它不会出现在数据中，如
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

在为 `created_at` 字段赋值后，它被转化为了字段的类型 datetime，并且在输出数据（转化为字典的数据）中，`created_at` 字段的名称变成了它指定的 `alias` 参数的值 `'createdAt'`

* `tags`：文章的标签字段，指定了默认值的工厂函数为 list，也就是说如果这个字段没有提供，将会制造一个空列表（`list()`） 作为默认值，另外指定了 `no_output` 函数，表示当值为空时不进行输出

!!! warning
	数据类对属性赋值的解析转化只能作用于直接赋值的情况，如果在这个例子中你使用了 `article.tags.append(obj)` 操作 `tags` 字段中的数据的话，就不会获得 utype 提供的解析功能了


我们可以从例子中看到，Field 类能提供了很多字段常用的配置项，包括

* **可选性与默认值**：`required`，`default`，`default_factory`，用于指示一个字段是否是必传的，以及它的默认值或制造默认值的工厂函数
* **说明与标记**：`title`，`description`，`example`，`deprecated` 等，用于给字段编写文档说明，示例，或者指示是否弃用
* **约束配置**：包括 [Rule 约束](/zh/references/rule) 中的所有约束参数，如 `gt`, `le`, `max_length`, `regex` 等等，用于给字段以参数的方式指定约束
* **别名配置**：`alias`，`alias_from`，`case_insensitive` 等，用于为字段指定属性名外的名称，以及大小写是否敏感等，可以用于定义属性声明不支持的字段名称
* **模式配置**：`readonly`，`writeonly`，`mode` 等，用于配置数据类或函数在不同的解析模式下的行为
* **输入与输出配置**：`no_input`，`no_output`，用于控制字段的输入和输出行为
* **属性行为配置**：`immutable`，`secret`，用于控制字段对应属性的可变更性，显示行为等

更完整的 Field 配置参数及用法，可以参考 [Field 字段配置的 API 参考](/zh/references/field)

!!! note
	Field 字段配置只在数据类或函数中声明有效，如果你单独用于声明一个变量，则不会起作用

### 声明 `@property` 属性

我们知道在 Python 的类中，可以使用 `@property` 装饰器声明属性，从而使用函数控制属性的访问，赋值和删除

utype 也支持使用  `@property` 声明属性字段，从而更深入地控制属性行为，先看一个简单的例子

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

属性 `signup_days` 通过字段 `signup_time` 来计算注册的天数，声明了 `int` 作为属性类型，这样在获取该属性值时 utype 会将它转化为 `int` 输出

#### 使用 setter 控制赋值行为
使用 `@property` 属性，你还可以通过指定 `setter` 来赋予属性字段输入和赋值的能力，这也是一种常见的方式来进行关联更新，或者隐藏某些私有字段不暴露，比如
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

在例子中的数据类 ArticleSchema 中，我们使用 `title` 属性的 setter 完成对 `slug` 字段的关联更新，也就是说类的使用者无需直接操作 `slug`，而是通过赋值 `title` 来影响 `slug` 字段

如果 property 属性没有声明 setter，则它就是不可被赋值的，这样声明不可变更的字段是更加原生的做法

!!! note
	在 Schema 数据类中，输入的字段都会在初始化中赋值相应的属性，如果属性使用了 setter，就会执行 setter 中的逻辑


#### 为属性配置 Field

属性字段依然支持配置 Field 来调控属性字段的行为，比如
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

Field 实例可以配置到属性的 getter 和 setter 上，它们各自的用法是

**getter**：通过将 Field 实例作为装饰器装饰 `@property` 下的函数，常用的配置有

* `no_output=True`：不将计算结果输出
* `dependencies`：指定属性计算的依赖字段，只有当属性字段的依赖全部提供时，才会进行计算
* `alias`：指定输出的字段别名

!!! note
	在 Schema 实例中，如果属性没有指定 `no_output=True`，那么它就会在初始化时直接进行计算，并将结果保存在自身字典数据中，当 `dependencies` 中的字段发生更新时，会再次计算并赋值，这是因为 Schema 是使用字典存储数据，而不是使用属性存储，所以需要输出的数据都会被强制计算

**setter**：通过在 setter 函数的输入字段的默认值中指定 Field 实例，常用的配置有

* `no_input=True`：表示不接受在初始化时输入，只能使用属性赋值调控
* `immutable=True`：表示不接受属性赋值，只能在初始化时输入
* `alias_from`：指定输入来源的字段别名列表

!!! warning
	同时指定 `no_input` 和 `immutable` 会导致 setter 变得无效

下面来看一下这些属性的行为
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

可以看到，在为 `slug` 指定 `dependencies=title` 后，当 `title` 发生赋值更新后，`slug` 字段也会同步更新

!!! note "行业实践"
	例子中的行为其实也是一般博客网站的做法，直接使用文章标题来生成 URL 路径字符串

字段配置在数据类声明周期的各个环节的作用分别为

* 数据输入 `no_input`：此字段不参与数据输入
* 实例操作 `immutable`：无法在实例中操作此字段（无法被赋值或删除）
* 数据输出 `no_output`：此字段不参与数据输出

### 字段准入规则

并不是所有在 Schema 上声明的属性都会被转化为可以解析校验的字段，utype 的数据类字段有着一定的准入规则

* 以下划线（`'_'`）开头的属性不会作为字段，以下划线开头的属性往往作为类的保留属性，utype 不会将其作为字段处理
* 所有的 `@classmethod`，`@staticmethod` 和类中声明的方法都不会作为字段
* 如果你使用了 `ClassVar` 作为属性的类型提示，那么表示这个属性是一个类变量，而不是实例变量，所以有这样声明的属性也不会被 utype 作为字段处理

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

在例子中 Static 数据类中的几个属性都不具备成为字段的条件，所以无论输入数据如何都不会影响这些属性在实例中的值，并且非字段的属性也不会进行输出

#### 限制条件
当字段名称和声明符合准入规则后，还需要注意一些声明限制

* 如果一个属性名称在基类中对应着一个方法或者类函数，那么你不能在子类中将其声明为一个数据字段
```python
from utype import Schema, Field

try:
	class InvalidSchema(Schema):
		items: list = Field(default_factory=list)  # wrong!
except TypeError as e:
	pass
```

	比如由于 Schema 继承自 dict 字典类，所以字典中的方法名称不可以被声明为一个字段名称，如果需要声明一样的属性名称，可以使用属性别名 `alias`，如
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

* 如果一个字段在父类中使用 `Final` 声明，表示它是不可被再次覆盖或赋值的，所以子类也无法声明同样名称的字段
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
	使用 Final 作为类型的字段也会直接被标记为一个不可变更（`immutable=True`）的字段，如果指定了属性值，则还是不可输入（`no_input=True`）的，即无法通过初始化数据影响它的值


## 数据类的使用

这一节我们主要讨论数据类的使用方式

### 嵌套与复合
我们已经了解过嵌套类型的声明方式，而数据类本身也是一种类型，所以可以使用相同的语法来定义嵌套和符合的数据结构，如

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

我们在声明的数据类 GroupSchema 中使用另一个数据类 MemberSchema 作为字段的类型提示，表示传入的数据需要符合声明的数据类的结构（往往是一个字典，或者 JSON），如
``` python
alice = {'name': 'Alice', 'level': '3'}   # dict format
bob = b'{"name": "Bob"}'                  # json format
  
group = GroupSchema(name='test', creator=alice, members=(alice, bob))  

print(group.creator)
# > MemberSchema(name='Alice', level=3)

assert group.members[1].name == 'Bob'
```

可以看到，字典数据和 JSON 数据都能够被直接转化为数据类实例并进行解析与校验

!!! warning
	你并不能直接把 JSON 数据传入到数据类的初始化函数中，比如 `MemberSchema(b'{"name": "Bob"}')`  是错误的语法，但数据类提供了一个 `__from__` 类方法，所以你可以使用 `MemberSchema.__from__(b'{"name": "Bob"}')` 来转化非字典数据

#### 私有数据类
有些时候，我们需要定义的的某个数据类只会在特定的类中出现，不会被其他的数据引用，这时可以将需要的结构直接作为类定义在数据类中，便于组织代码与隔离命名空间，如

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

在这个例子中，我们在 `UserSchema` 中声明了一个名为 `KeyInfo` 的数据类，由于不满足字段的准入规则，`KeyInfo` 类并不会作为一个字段，而是会保持原状


### 继承与复用
继承是面向对象编程中复用数据结构与方法的重要手段，同样适用于数据类，只需要按照类继承的方式声明数据类的子类，就可以继承父类的所有字段，比如
```python
from utype import Schema, Field
from datetime import datetime

class LoginSchema(Schema):  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
	password: str = Field(min_length=6, max_length=20)
	  
class UserSchema(LoginSchema):  
    signup_time: datetime = Field(readonly=True)  
```

用于处理登录的数据类 `LoginSchema` 被 `UserSchema` 继承，使得其中定义的 `username`, `password` 字段成为了 `UserSchema` 中字段的一部分

你还可以使用多重继承来复用数据结构，或者使用混入（Mixin）的思想将数据结构的通用部分原子化，在需要的结构中组合起来，例如
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

我们为 `username` 和 `password` 声明了对应的混入数据类，那么任何需要它们的数据类都可以对混入类进行继承，以获得对应的字段

### 逻辑运算
继承自 Schema 的数据类与约束类型一样拥有着参与类型逻辑运算的能力，如
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

我们将数据类 `User` 与 Tuple 嵌套类型进行逻辑运算（是的，你可以这么做，尽管 `Tuple[str, int]` 并不是一个类型，utype 会在运算时将其进行转化），使得输入既可以接受字典或 JSON 数据，也可以接受列表或元组数据，只要能够转化到声明的类型

### 用于函数
数据类还可以用于函数中，作为函数参数或返回结果的类型提示，只需要函数使用 `@utype.parse` 装饰器

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

例子中我们声明了一个登录函数，使用 LoginForm 接受登录表单，如果登录成功则返回用户名信息，并将会被转化为 UserInfo 数据类实例

!!! note
	关于函数解析的更多用法请阅读下一篇文档：[函数的解析](/zh/guide/func)


## 数据解析与校验

这一节我们关注如何控制和调整数据类的解析校验行为

### 配置解析选项
utype 提供了一个 Options 类，用于调节数据类和函数的解析行为，它在数据类中的用法如下

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

我们在数据类中声明了一个名为 `__options__` 的属性，并使用一个 Options 的实例进行赋值，参数中传入的就是解析选项

在例子中我们配置的选项是 `addition=True`，表达的是保留字段范围之外的输入数据，解析配置中常用的选项包括：

* **数据处理选项**：`addition`，`max_params`，`min_params`，`max_depth` 等对输入数据的长度，深度等进行限制，并且指定超出字段范围的数据的行为
* **错误处理选项**：`collect_errors`，`max_errors`，配置错误处理行为，比如是否收集所有的解析错误
* **非法数据选项**：`invalid_items`，`invalid_keys`，`invalid_values`，配置对非法数据的处理行为，是丢弃，保留，还是抛出错误
* **解析调节选项**：`ignore_required`，`no_default`，`ignore_constraints` 等一系列对于解析行为和字段行为进行调节的选项
* **字段生成选项**：`alias_generator`，`case_insensitive` 等，用于对字段生成别名，或者指定是否大小写敏感的选项

解析选项在对类型，数据类和函数的解析转化中都是通用的，更全面的解析参数说明请参考 [Options 解析选项](/zh/references/options)

下面示例一种解析选项的使用场景
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

我们逐个分析例子中的解析选项

* `case_insensitive=True`：表示大小写不敏感地接受数据，比如在例子中输入数据使用了 `'UserName'` 来传递  `'username'` 字段的值
* `addition=False`：表示不接受超出字段的输入数据，例子中我们额外输入了一个没有在字段中的参数 `'Token'`，会被检测到并作为错误抛出
* `collect_errors=True`：一般情况下，当 utype 检测到输入数据中存在一个错误时就会直接抛出，而开启 `collect_errors` 能够让 utype 收集数据中的所有错误并一并抛出，这样对于调试会更加方便，我们使用 `exc.CollectedParseError` 便可以捕获抛出的打包错误，比如例子中我们一并捕获了所有参数的错误信息

!!! note
	`addition` 选项默认为 None，表示忽略超出字段的输入，当 `addition=True` 时表示保留超出数据， `addition=False` 时表示遇到超出字段的输入会直接抛出错误

除了声明 Options 实例的方式配置解析选项外，你还可以使用类的方式，如
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


#### 运行时解析选项
除了在类声明中指定解析选项外，utype 还支持在数据类初始化（解析时）时传入一个解析选项来调节运行时的解析行为

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
	LoginForm(**form, __options__=options)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['token'] exceeded
	"""
```

通过在初始化函数中传递 `__options__` 参数，就可以传递一个运行时解析选项，utype 会按照这个选项对数据进行解析

如果你希望在类中约束运行时解析选项的范围，可以在类的 Options 中声明一个参数`allow_runtime_options`，它的取值有

* `'*'`：默认值，允许所有运行时解析选项
* `None`：不允许运行时解析选项
* 字符串列表：只允许列表中的选项

#### 解析选项的继承与覆盖
当你继承一个数据类时，你同样会继承它的解析选项，所以你也可以声明全局的解析选项

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

可以看到，如果子类没有额外声明解析选项，就会直接沿用父类的。这个例子的另一种声明方式是

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

例子中自定义了一个解析选项基类，你可以自由地继承，组合与复用


### 自定义 `__init__` 函数
任何预定义好的解析选项有时也无法代替自定义的函数逻辑带来的灵活度，所以 utype 支持在数据类中自定义初始化  `__init__` 函数，来实现更加定制化的解析逻辑，比如

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

在例子中，我们在调用父类的初始化方法进行解析校验前就先对参数进行联合校验，避免了幂次运算产生复数结果的情况

可以看到，数据类中自定义的 `__init__` 函数默认就会获得类型解析的能力，也就是你可以在 `__init__` 函数中声明类型与字段配置，语法与 [函数的解析](/zh/guide/func) 相同，在调用 `__init__` 函数时会先按照函数的参数声明进行解析，再执行你的初始化逻辑

而且只有当你自定义了  `__init__` 函数，才能使用像例子中一样的顺序参数方式进行初始化

!!! note
	在自定义   `__init__` 函数后，是否支持运行时解析选项就由你的函数参数和逻辑决定了，只有当你在调用 `super().__init__` 方法时传入了 `__options__` 参数才能够支持运行时解析选项，所以在上面的例子中，PowerSchema 并不支持任何运行时解析选项

### 解析后的校验函数
utype 除了支持通过自定义 `__init__` 函数来定制解析前的处理逻辑，还支持声明解析完成后的校验函数 `__validate__`，用法如下
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
我们声明了一个携带 HTTP 请求信息的 Schema 类，在其中定义了  `__validate__` 函数，其中执行了一些校验和赋值的逻辑

### 注册转化器
在 utype 中，所有类型都可以注册转化器函数，来定义从输入数据到调用类型的初始化函数间的转化逻辑，数据类作为一种类型也不例外

默认的数据类转化函数如下

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

它的逻辑主要是
1. 如果输入的数据不是字典或映射（Mapping）类型，则会先进行转化（比如可以完成 JSON 字符串到字典数据的转化）
2. 如果数据类允许传入运行时解析选项，则会进行传递
3. 最后使用转化好的数据调用数据类的初始化函数

比如在如下的例子中
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

GroupSchema 检测到 creator 字段传入的数据类型（字符串）并不符合声明的类型 MemberSchema 时，就会寻找期望类型 MemberSchema 的转化器函数，在找到后会将数据作为参数输入转换器函数，最终得到期望的类型实例

!!! note
	如果无法找到满足条件的转换器，这个类型将会按照解析选项 Options 中配置的 `unresolved_types` 策略处理，默认是直接抛出错误

你可以为自己的数据类注册转化函数，来自定义不符合类型的数据是如何进行转化的。比如你可以选择拒绝所有不是该数据类实例的输入
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

其中，转换器函数的的参数依序分别是

1. 类型转换器 TypeTransformer 实例
2. 输入数据
3. 类型

!!! note
	转换器函数需要在解析发生前注册，才能在解析中生效

## 其他声明方式与参数

之前的示例中我们只介绍了使用继承 Schema 的方式来定义数据类，其实在 utype 中有两种声明数据类的方式

1. 继承预定义好的数据类基类
2. 使用 `@utype.dataclass` 装饰器自行制造

其中，utype 目前提供的预定义数据基类有

 * DataClass：没有任何基类，支持逻辑操作
 * Schema：继承自 dict 字典类，提供属性读写与字典的所有方法，支持逻辑操作

我们先来了解使用 `@utype.dataclass` 装饰器制造数据类的方式，其他预定义的数据基类可以视作固定了一些装饰器参数的制造方式

### `@utype.dataclass` 装饰器

我们可以使用 `@utype.dataclass` 装饰器对一个类进行装饰，使其变成一个数据类，如

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

`@utype.dataclass` 装饰器中有一系列的参数，用于自定义数据类的生成行为，包括

* `no_parse`：开启后将不对数据进行解析校验，仅将输入数据对属性进行映射赋值，默认为 False
* `post_init`：传入一个函数，在 `__init__` 函数完成后调用，可以用于编写自定义的校验逻辑
* `set_class_properties`：是否对字段对应的类属性重新赋值为一个 `property`，这样能够在运行时的属性赋值与删除时获得字段配置的解析能力和保护，默认为 False

我们可以直观比较一下是否开启 `set_class_properties` 的区别
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

默认 `set_class_properties=False` 的数据类的属性不会被影响，直接访问它会得到对应的属性值，如果属性值没有被定义，则会直接抛出一个 AttributeError，与普通的类的行为一致

而在开启了 `set_class_properties=True` 后，所有的字段对应的类属性都会被重新赋值为一个 `property` 实例，使得实例中的字段属性的更新与删除变得可控，控制属性赋值的参数包括

* `post_setattr`：在实例的字段属性发生赋值（`setattr`）操作后调用这个函数，可以进行一些自定义的处理行为
* `post_delattr`：在实例的字段属性发生删除（`delattr`）操作后调用这个函数，可以进行一些自定义的处理行为

!!! note
	只有在开启 `set_class_properties=True` 时，传入 `post_setattr` 和 `post_delattr` 才有意义

* `repr`：是否对类的 `__repr__` 与 `__str__` 方法进行改造，使得当你使用 `print(inst)` 或 `str(inst)`, `repr(inst)` 时，能够得到一个高可读性的输出，将数据类实例中的字段和对应值展示出来，默认为 True
* `contains`：是否生成数据的  `__contains__` 函数，你可以使用 `name in instance` 来判断一个字段是否是在数据类中
* `eq`：是否生成数据类的 `__eq__` 函数，使得数据相等的两个数据类实例会被 `inst1 == inst2`  判定相等

另外还有控制解析器和解析选项的参数

* `parser_cls`：指定负责解析类声明与解析数据的核心解析器类，默认是 `utype.parser.ClassParser`
* `options`：指定一个 Options 解析选项用于控制解析行为

!!! note
	 `@utype.dataclass` 装饰器只会对你的类中的某些方法进行调整，并不会影响类的基类或者元类，所以你可以为你的数据类指定任意的基类与元类

#### 逻辑运算
如果你需要让声明出的数据类支持逻辑运算，则需要使用 `utype.LogicalMeta` 作为你的数据类的**元类**，用法如下
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
	继承自 Schema 或 DataClass 的数据类直接拥有了逻辑运算的能力，因为 Schema 和 DataClass 的元类（`metaclass`，可以理解为类的类型，控制着类的一些行为）就是 `utype.LogicalMeta`

### Schema 类

* `__parser_cls__`：
* `__options__`：

Schema 继承自 dict 字典类，所以你可以直接使用操作字典的方式来操作 Schema 实例

* 字典取值与 `get()`
* 字典赋值与 `setdefault()`
* `keys()`
* `values()`
* `items()`
* `copy()`

还有一些会对字典数据中的内容进行变更的方法，Schema 进行

* `update()`
* `pop()`
* `popitem()`
* `clear()`


**深入：Schema 实例中的数据存储**

由于 Schema 继承自字典类，在 Schema 的实例中，所有的字段数据都是保存在自身的字典结构中的，当我们访问 Schema 实例的属性时，其实是访问了对应的键值

* no_output：被设置或检测到 no_output 的字段，它们会直接设置 `__dict__` 属性值，而不会赋值到内部字典数据中，这样你可以通过属性访问到这个值，但是使用 `key in obj` 将会得到 False，使用 `dict(obj)` 也不会看到该字段的输出
* property：如果一个属性字段的依赖都被提供时，它就会直接在初始化时进行计算，并将结果保存在自身的数据中（除非指定了 no_output）

property 的关联更新：
property  的 getter 中会存在一些依赖字段（或者显式声明 `dependencies`），当这些依赖字段发生变化时，property  也会发生变化

* 初始化时 coerce getter 并赋值到数据中（除非指定了 no_output）
* 如果 property 有 setter， setter 调用时更新 getter
* 如果  property 有 dependencies，那么当 dependencies 中有字段发生更新时调用 getter

!!! warning
	property 无法捕捉到 excluded vars 的更新（比如以下划线开头的非字段属性），所以如果你有这些依赖，需要自行管理，或者让它们只在该 property 的 setter 中更新

对于 delete attr 或者 delete item，即使 default 不是 deferred，此时也不会再赋值，那个键值/属性会被直接删除，并且不会出现在输出结果中，只不过如果 default 是 deferred 的话，那么在删除后访问属性仍然能够得到值而已

对于 Schema，`__dict__` 更像是一个 fallback，属性值和输出值都不从这取

### DataClass 类
DataClass 类没有任何基类，所以在这个类中声明字段没有名称上的限制，实现更加简洁，但同时无法像 Schema 一样支持字典相关的方法

* `__parser_cls__`：
* `__options__`：

DataClass 类对应的偏好配置是

* `init_attributes=True`
* `init_properties=True`
* `set_class_properties=True`
* `repr=True`
* `contains=True`

**深入：DataClass 实例中的数据存储**
与 Schema 类不同，DataClass 实例中的字段数据都是存储在属性 `__dict__` 中的，

* no_output：在实例的属性中并不区分是否 output，DataClass 声明了一个 `__export__` 方法，用于导出数据
* defered default：如果输入数据没有提供，且 default 是 defer 的，那么对应的属性就不会赋值给 `__dict__`，只会在访问到对应数据时才会计算 default，而且每次访问都会计算
* property：property 并不迫使计算，只有在访问时或输出时（没有 no_output）进行计算，所以也无需调控关联更新

contains 行为：与 Schema 一样仅包含可输出的字段


**总结与比较**
* Schema：继承自 dict，拥有字典的全部方法与特性，适合作为 “数据模型”，同时支持键值操作与属性操作，输出的 `@property` 会被立即计算，后续的访问会直接得到计算缓存结果
* DataClass：没有任何基类，适合需要对类的行为有更多定制的场景，只支持属性操作，所有  `@property` 都只在调用时计算


### 属性访问钩子

* `post_setattr`
* `post_delattr`

在预定义好的 Schema 和 DataClass 类中，也有着相应的可覆盖函数
* `__post_setattr__`
* `__post_delattr__`


### 整体性校验函数

* `__validate__`
* `__post_init__`


### 通过 ClassParser 制造

这是最接近底层的一种制造方式，所有的数据类都是通过 ClassParser 制造的，只不过 utype 通过预定义类和装饰器抽象掉了背后的具体工作，如果你希望对于数据类的制造有着更多的掌控，可以直接通过 ClassParser 来制造

事实上，为数据类提供声明分析和运行时数据解析功能的是来自 `utype.parser.ClassParser` 的类解析器

所有的数据类在声明时都依赖它来进行字段解析和方法制造，从而获得在运行时解析数据的能力


## 生成数据模板

### JSON Schema


### 输入-输出

* 在函数参数中使用的是输入模板
* 在函数返回值中使用的是输出模板

另一种视角是 HTTP 请求，在提供给用户的 API 文档中

* 请求参数对应的是输入模板
* 响应参数对应的是输出模板

### 选择模式

以上还可以组合，比如
* 读（`'r'`）模式下，使用输出模板给到用户，作为 API 的响应/结果文档
* 写（`'w'`）模式下，使用输入模板给到用户，作为 API 的请求/参数文档

!!! note
	如果你是一个面向数据库的后端应用，读模式的输入和写模式的输出对应的都是数据库（读 SQL执行的结果与写 SQL 的输入参数）

对于函数而言，参数中的所有模板都是输入模板，返回值类型中的模板都是输出模板

## 序列化编码
当我们需要将一个数据类中的数据通过网络进行传输时，就往往需要使用 JSON，XML 等格式对数据进行序列化编码

### 编码函数

### 注册编码器

TODO