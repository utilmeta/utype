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
```

我们逐个看一下例子中声明的字段

* `slug`：文章的 URL 路径字段，使用 `regex` 为字段指定了正则约束，并且设置了 `immutable=True`，意味着字段不可被修改，还指定了示例值 `example` 和描述 `description` 用于更好的说明字段的用途

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

在为 `created_at` 字段赋值后，它被转化为了字段的类型 (`datetime`)，并且在输出数据（转化为字典的数据）中，`created_at` 字段的名称变成了它指定的 `alias` 参数的值 `'createdAt'`

* `tags`：文章的标签字段，指定了默认值的工厂函数为 list，也就是说如果这个字段没有提供，将会制造一个空列表（`list()`） 作为默认值，另外指定了 `no_output` 函数，表示当值为空时不进行输出

!!! warning
	数据类对属性赋值的解析转化只能作用于直接赋值的情况，如果在这个例子中你使用了 `article.tags.append(obj)` 操作 `tags` 字段中的数据的话，就不会获得 utype 提供的解析功能了


我们可以从例子中看到，Field 类能提供了很多字段常用的配置项，包括

* **可选性与默认值**：`required`，`default`，`default_factory`，用于指示一个字段是否是必传的，以及它的默认值或制造默认值的工厂函数
* **说明与标记**：`title`，`description`，`example`，`deprecated` 等，用于给字段编写文档说明，示例，或者指示是否弃用
* **约束配置**：包括 [Rule 约束](/zh/references/rule) 中的所有约束参数，如 `gt`, `le`, `max_length`, `regex` 等等，用于给字段以参数的方式指定约束
* **别名配置**：`alias`，`alias_from`，`case_insensitive` 等，用于为字段指定属性名外的名称，以及大小写是否敏感等，可以用于定义属性声明不支持的字段名称
* **模式配置**：`readonly`，`writeonly`，`mode` 等，用于支持多种解析模式，配置字段在不同的解析模式下的行为
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
	在数据类中，输入的字段都会在初始化中赋值相应的属性，如果属性使用了 setter，就会执行 setter 中的逻辑


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
	同时指定 `no_input=True` 和 `immutable=True` 会导致 setter 变得无效

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

* 数据输入 `no_input=True`：字段不参与数据输入
* 实例操作 `immutable=True`：无法在实例中操作此字段（无法被赋值或删除）
* 数据输出 `no_output=True`：字段不参与数据输出

### 字段准入规则

并不是所有在 Schema 上声明的属性都会被转化为可以解析校验的字段，utype 的数据类字段有着一定的准入规则

* 以下划线（`'_'`）开头的属性不会作为字段，以下划线开头的属性往往作为类的保留属性，utype 不会将其作为字段处理
* 所有的 `@classmethod`，`@staticmethod` 和类中声明的方法都不会作为字段
* 如果你使用了 `ClassVar` 作为属性的类型注解，那么表示这个属性是一个类变量，而不是实例变量，所以也不会作为字段处理

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
	使用 `Final` 作为类型的字段也会直接被标记为一个不可变更（`immutable=True`）的字段，如果为属性指定了值，则还是不可输入（`no_input=True`）的，即无法通过初始化数据影响它的值


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

我们在声明的数据类 GroupSchema 中使用另一个数据类 MemberSchema 作为字段的类型注解，表示传入的数据需要符合声明的数据类的结构（往往是一个字典，或者 JSON），如
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

我们将数据类 `User` 与 Tuple 嵌套类型进行了异或（XOR）逻辑运算（是的，你可以这么做，尽管 `Tuple[str, int]` 并不是一个类型，utype 会在运算时将其进行转化），使得输入既可以接受字典或 JSON 数据（转化到 `User`），也可以接受列表或元组数据（转化到 `Tuple[str, int]` ）

### 用于函数
数据类还可以用于函数中，作为函数参数或返回结果的类型注解，只需要函数使用 `@utype.parse` 装饰器

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

在例子中我们配置的选项是 `addition=True`，含义是保留数据类字段范围之外的额外输入，所以例子中不属于类字段的 `age` 和 `invite_code` 键值保留到了输出数据中，解析配置中常用的选项包括：

* **数据处理选项**：`addition`，`max_params`，`min_params`，`max_depth` 等对输入数据的长度，深度等进行限制，并且指定超出字段范围的数据的行为
* **错误处理选项**：`collect_errors`，`max_errors`，配置错误处理行为，比如是否收集所有的解析错误
* **非法数据选项**：`invalid_items`，`invalid_keys`，`invalid_values`，配置对非法数据的处理行为，是丢弃，保留，还是抛出错误
* **解析调节选项**：`ignore_required`，`no_default`，`ignore_constraints` 等一系列对于解析行为和字段行为进行调节的选项
* **字段生成选项**：`alias_generator`，`case_insensitive` 等，用于对字段生成别名，或者指定是否大小写敏感的选项

!!! note
	解析选项调控着 utype 对类型，数据类和函数的解析转化，更全面的解析参数说明请参考 [Options 解析选项](/zh/references/options)

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

Options 还支持以下声明方式

**类继承声明**
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

**类装饰器声明**
```python
from utype import Schema, Options

@Options(addition=True)  
class UserPreserve(Schema):  
    name: str  
    level: int = 0
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
	LoginForm.__from__(form, options=options)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['token'] exceeded
	"""
```

通过在数据类的 `__from__` 函数中传递 `options` 参数，就可以传递一个运行时解析选项，utype 会按照这个选项对数据进行解析


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
	在自定义  `__init__` 函数后，是否支持运行时解析选项就由你的函数参数和逻辑决定了，只有当你在调用 `super().__init__` 方法时传入了 `__options__` 参数才能够支持运行时解析选项，所以在上面的例子中，PowerSchema 并不支持任何运行时解析选项

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

@utype.dataclass(set_class_properties=False)
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

设置 `set_class_properties=False` 的数据类 UserA 的属性不会被影响，直接访问它会得到对应的属性值，如果属性值没有被定义，则会直接抛出一个 AttributeError，与普通的类的行为一致

而在开启了 `set_class_properties=True` 后，所有的字段对应的类属性都会被重新赋值为一个 `property` 实例，使得实例中的字段属性的更新与删除变得可控（在属性赋值能够按照声明进行类型解析，在删除时能够按照 `required` 与 `immutable` 属性进行保护）

除了上述默认的属性行为外，在 `@utype.dataclass` 装饰器中还提供了能够传入调控属性赋值与删除的钩子函数的参数，如

* `post_setattr`：在实例的字段属性发生赋值（`setattr`）操作后调用这个函数，可以进行一些自定义的处理行为
* `post_delattr`：在实例的字段属性发生删除（`delattr`）操作后调用这个函数，可以进行一些自定义的处理行为

!!! note
	只有在开启 `set_class_properties=True` 时，传入 `post_setattr` 和 `post_delattr` 才有意义

装饰器还提供了一些调节类行为的函数生成选项

* `repr`：是否生成类的 `__repr__` 与 `__str__` 方法，使得当你使用 `print(inst)` 或 `str(inst)`, `repr(inst)` 时，能够得到一个高可读性的输出，将数据类实例中的字段和对应值展示出来，默认为 True
* `contains`：是否生成数据的  `__contains__` 函数，你可以使用 `name in instance` 来判断一个字段是否是在数据类中，默认为 False
* `eq`：是否生成数据类的 `__eq__` 函数，使得数据相等的两个数据类实例会被 `inst1 == inst2`  判定相等，默认为 False

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
