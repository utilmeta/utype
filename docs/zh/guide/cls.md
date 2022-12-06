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

print(dict(article))
# > {'slug': 'my-article', 'content': 'my article body', 'views': 0}
```
你可以直接获得

* 无需声明 `__init__` 便能够接收对应的参数，并且完成类型转化和约束校验
* 提供清晰可读的 `__repr__` 与 `__str__` 函数使得在输出和调试时方便直接获得内部的数据值
* 在属性赋值或删除时根据字段的类型与配置进行保护，避免出现脏数据
* 能够直接作为字典数据进行传参或序列化

所以本篇文档我们来详细介绍数据类的声明和用法

!!! note
	声明数据类还有其他方式，各种声明方式和具体参数将在，在这之前我们先使用最简单的继承 Schema 方式来示例

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

### Field 字段配置
Field 可以为字段配置更多丰富的行为，只需要将 Field 类的实例作为该字段的属性值/默认值，就可以获得其参数中声明的字段配置

常用的配置项有

* **可选性与默认值**：`required`，`default`，`default_factory`，用于指示一个字段是否是必传的，以及它的默认值或制造默认值的工厂函数
* **说明与标记**：`title`，`description`，`example`，`deprecated` 等，用于给字段编写文档说明，示例，或者指示是否弃用
* **约束配置**：包括 [Rule 约束](/zh/references/rule) 中的所有约束参数，如 `gt`, `le`, `max_length`, `regex` 等等，用于给字段以参数的方式指定约束
* **别名配置**：`alias`，`alias_from`，`case_insensitive` 等，用于为字段指定属性名外的名称，以及大小写是否敏感等，可以用于定义属性声明不支持的字段名称
* **模式配置**：`readonly`，`writeonly`，`mode` 等，用于配置数据类或函数在不同的解析模式下的行为
* **输入与输出配置**：`no_input`，`no_output`
* **属性行为配置**：`immutable`，`unprovided`

更完整的 Field 配置参数及用法，可以参考 [Field 字段配置的 API 参考](/zh/references/field)

!!! note
	Field 字段配置只在数据类或函数中声明有效，如果你单独用于声明一个变量，则不会起作用

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
        unprovided=None  
    )  
    tags: List[str] = Field(default_factory=list, no_output=lambda v: not v)
```

我们逐个看一下例子中声明的字段

* `slug`：文章的 URL 路径字段，使用 `regex` 为字段指定了正则约束，并且设置了 `immutable=True`，意味着字段不可被修改，还指定了示例值 `example` 和描述 `description` 用于更好的说明字段的用途
* `content`：文章的内容字段，其中使用 `alias_from` 参数指定了一些可以从中转化的别名，这个特性对于字段的更名和版本兼容非常有用，比如上个版本的内容字段名称是 `'body'`，在当前版本中被废弃并使用了 `'content'` 作为内容字段的名称
* `views`：文章的访问量字段，指定了 `ge` 最小值约束和默认值
* `created_at`：文章的创建时间字段，使用 `alias` 指定了字段在输出时的别名为 `'createdAt'`，使用 `required=False` 标记这是一个可选字段，由于没有提供默认值，它使用了 `unprovided=None` 指定了当没有提供值时，访问属性会得到 None（如果没有指定 `unprovided`，则当该字段没有提供值时，访问属性会抛出 `AttributeError`）

* `tags`：文章的标签字段，指定了默认值的工厂函数为 list，也就是说如果这个字段没有提供，将会制造一个空列表（`list()`） 作为默认值，另外指定了 `no_output` 函数，表示当值为空时不进行输出

下面来看一下我们声明出来的 `ArticleSchema` 的具体行为

```python
article = ArticleSchema(  
    slug=b'test-article',  
    body='article body',  
    tags=[]
)  

print(article)  
# > ArticleSchema(slug='test-article', content='article body', views=0)  

try:  
    article.slug = 'other-slug'  
except AttributeError as e:  
    print(e)  
    """  
    AttributeError: ArticleSchema: Attempt to set immutable attribute: ['slug']    
    """  

from utype import exc  
try:  
    article.views = -3  
except exc.ParseError as e:  
    print(e)  
    """  
    ParseError: parse item: ['views'] failed: Constraint: <ge>: 0 violated    
    """

assert 'createdAt' not in article   # True
assert article.created_at is None   # True
article.created_at = '2022-02-02 10:11:12'  
print(dict(article))  
# {
# 'slug': 'test-article', 
# 'content': 'article body',
# 'views': 0, 
# 'createdAt': datetime.datetime(2022, 2, 2, 10, 11, 12)
# }
```

我们可以发现
* slug 字段指定了 `immutable=True`，所以尝试赋值会抛出 `AttributeError`
* 虽然我们输入的数据中使用 `'body'` 传递文章的内容，但它位于 `content` 字段声明的 `alias_from` 中，所以会被转化为 `content` 字段
* 为 views 字段的赋值违背了它所声明的约束，所以抛出了 `exc.ParseError` 错误
* 虽然我们没有输入 views 字段，但由于它指定了默认值为 0，所以在输出结果中 views 对应的值就是 0
* created_at 字段声明了 `required=False` 且没有声明默认值，所以当输入数据没有提供时，它并不在实例的数据当中，但由于它指定了 `unprovided=None`，所以当你访问这个属性时，会得到 None 值
* 在为 created_at 赋值后，它被转化为了字段的类型 datetime，并且在输出数据（转化为字典的数据）中，created_at 字段的名称变成了它指定的 `alias` 参数的值 `'createdAt'`
* `tags` 字段虽然输入了一个空列表，但是由于它指定的 `no_output` 函数判断当值为空时不进行输出，所以输出的结果中不包含 `'tags'` 字段

!!! warning
	数据类对属性赋值的解析转化只能作用于直接赋值的情况，如果在这个例子中你使用了 `article.tags.append(obj)` 操作 `tags` 字段中的数据的话，就不会获得 utype 提供的解析功能了

### `@property` 属性

```python
from datetime import datetime

class UserSchema(Schema):
	username: str
	signup_time: datetime
	
	@property  
	def signup_days(self) -> int:  
	    return int((datetime.now() - self.signup_time).total_seconds() / (3600 * 24))
```


可以看到，property 属性可以方便地基于数据类字段执行额外的聚合或函数操作，

如果 property 属性没有声明 setter，则它就是不可被赋值的，这样声明不可变更的字段是更加原生的做法

#### 指定 setter 

使用 `@property` 属性，你还可以通过指定 `setter` 来使得属性字段是可输入和赋值的，这也是一种常见的方式来进行关联更新，或者隐藏某些私有字段不暴露
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
    def title(self, val: str = Field(max_length=50)):  
        self._title = val  
        self._slug = '-'.join([''.join(filter(str.isalnum, v))  
                               for v in val.split()]).lower()  
  
```

在例子中的数据类，我们使用 `title.setter` 将完成对 `slug` 字段的关联更新，这样对于这个，用户无需直接操作 `slug`，而是通过赋值 `title` 来影响 slug

!!! note
	在 Schema 数据类中，如果你为属性声明了 setter 并且在初始化时提供了该属性的值，就会与其他的属性一样直接被赋值，从而会执行 setter 中的逻辑



```python
article = ArticleSchema(title=b'My Awesome article!')
print(article.slug)
# > 'my-awesome-article'

try:
	article.slug = 'other value'
except AttributeError:
	pass

article.title = b'Our Awesome article!'
print(dict(article))
# > {'slug': 'our-awesome-article', 'title': 'Our Awesome article!'}
```

!!! note
	这其实也是一般博客网站的做法，直接使用文章标题来生成 URL 路径字符串



### 字段准入规则

* 不以下划线开头，以下划线开头的属性往往作为类的保留属性，utype 不会将其作为字段处理
* 如果一个属性名称在基类中对应着一个方法或者类函数，那么你不能在子类中将其声明为一个数据字段

以上的命名限制都可以通过指定字段别名来解决

* 如果你使用了 ClassVar 作为属性的类型提示，那么表示这个属性是一个类变量，而不是实例变量，所以有这样声明的属性也不会被 utype 作为字段处理

**自定义准入规则**

```python
class BaseParser:
	@classmethod  
	def validate_field_name(cls, name: str):  
	    return not name.startswith("_")
```

你可以通过覆盖这个方法来定义你自己的字段准入规则


### 属性访问行为
* 读取
* 更新
* 删除


## 数据类的用法

### 嵌套与复合

对于更加复杂的数据，除了普通的数值类型外，往往需要更多的嵌套与符合结构，比如字典，列表，元组与集合等，

```python
from utype import Schema, Field

class UserSchema(Schema):
    name: str
    level: int = 0

class GroupSchema(Schema):
	name: str
	creator: UserSchema
	members: List[UserSchema] = Field(default_factory=list)
```

我们额外声明了一个 GroupSchema，在这个类中有两个特殊的字段
* `creator`: 使用 `UserSchema` 作为类型提示，表示需要传入一个符合 UserSchema 结构的数据
* `members`：使用 `List[UserSchema]` 作为类型提示，表示需要传入一个列表，其中的每个元素都需要符合 UserSchema 的结构
``` python
>>> alice = UserSchema(name='Alice', level=1)
>>> bob = UserSchema(name='Bob')
>>> group = GroupSchema(name='Huddle', creator=alice, members=[alice, bob])
>>> group
GroupSchema(name='Huddle', creator=UserSchema(name='Alice', level=1), members=[UserSchema(name='Alice', level=1), UserSchema(name='Bob', level=0)])

>>> group.members.pop()
UserSchema(name='Bob', level=0)
>>> group.members
[UserSchema(name='Alice', level=1)]
```

#### 私有数据类
有些时候，我们需要定义的的某个数据类只会在特定的类中出现，不会被其他的数据引用，这时可以将需要的结构直接作为类定义在数据类中，便于组织代码与隔离命名空间，如

```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
    name: str
    level: int = 0
    
	class KeyInfo(Schema):
		access_key: str
		last_activity: datetime = None
		
	access_keys: List[KeyInfo] = Field(default_factory=list)

print(UserSchema(**{'name': 'Joe', 'access_keys': {'access_key': 'KEY'}}))
# > UserSchema(name='Joe', level=0, access_keys=[UserSchema.KeyInfo(access_key='KEY', last_activity=None)])
```

在这个例子中，我们在 `UserSchema` 中声明了一个名为 `KeyInfo` 的数据类，它并不会作为一个字段，而是会保持原状


### 继承与复用
继承是面向对象编程中复用数据结构与方法的重要手段，同样适用于数据类，只需要按照类继承的方式声明数据类的子类，就可以继承父类的所有字段，比如
```python
from utype import Schema, Field

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

继承自 Schema 或 DataClass 的数据类直接拥有了逻辑运算的能力，因为 Schema 和 DataClass 的元类（`metaclass`，可以理解为类的类型，控制着类的一些行为）

如果你需要让声明出的数据类支持逻辑运算，则需要手动使用 `utype.LogicalMeta` 作为你的数据类的**元类**，用法如下
```python
import utype

@utype.dataclass  
class LogicalUser(metaclass=utype.LogicalMeta):  
    name: str = Field(max_length=10)  
    age: int

one_of_user = LogicalUser ^ Tuple[str, int]

print(one_of_user({'name': 'test', 'age': '1'}))
# > LogicalDataClass(name='test', age=1)

print(one_of_user([b'test', '1']))
# > ('test', 1)
```


## 其他声明方式与参数

之前的示例中我们只介绍了使用继承 Schema 的方式来定义数据类，

在 utype 中有两种声明数据类的方式

1. 继承预定义好的数据类基类，如 Schema
2. 使用 `@utype.dataclass` 装饰器自行制造

其中，utype 目前提供的预定义数据基类有

 * DataClass：没有任何基类，支持逻辑操作
 * Schema：继承自 dict 字典类，提供属性读写与字典的所有方法，支持逻辑操作

我们先来了解使用 `@utype.dataclass` 装饰器制造数据类的方式，其他预定义的数据基类可以视作固定了一些装饰器参数的制造方式

### `@utype.dataclass` 装饰器

就可以使用 `@utype.dataclass` 装饰器对一个类进行装饰，使其变成一个数据类，如
```python
import utype

@utype.dataclass  
class User:  
    name: str = Field(max_length=10)  
    age: int
```

`@utype.dataclass` 装饰器中有一系列的参数，用于自定义数据类的生成行为，包括

* `init_super`：是否在初始化函数中调用 `super().__init__` 方法
* `init_attributes`：是否在初始化时赋值对应的属性，默认为 True
* `init_properties`：是否在初始化时直接计算数据类中定义的 `@property` 的值并将其作为数据的一部分
* `post_init`：传入一个函数，在 `__init__` 函数完成后调用，可以用于编写自定义的校验逻辑
* `set_properties`：是否对字段对应的类属性重新赋值为一个 `property`，这样能够在运行时的属性赋值与删除时获得字段配置的解析能力和保护，默认为 False

我们可以直观比较一下它们的区别
```python
import utype

@utype.dataclass
class UserA:  
    name: str = Field(max_length=10)  
    age: int

@utype.dataclass(set_properties=True)
class UserB:  
    name: str = Field(max_length=10)  
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

默认情况下，`set_properties=False` 类的属性不会被影响，访问它会得到对应的属性值，如果属性值没有被定义，则会直接抛出一个 AttributeError，与普通的类的行为一致

而在开启了 `set_properties=True` 后，所有的字段对应的类属性都会被重新赋值为一个 `property` 实例，使得实例中的字段属性的更新与删除变得可控

* `post_setattr`：在实例的字段属性发生赋值（`setattr`）操作后调用这个函数，可以进行一些自定义的处理行为
* `post_delattr`：在实例的字段属性发生删除（`delattr`）操作后调用这个函数，可以进行一些自定义的处理行为

!!! note
	只有在开启 `set_properties=True` 时，传入 `post_setattr` 和 `post_delattr` 才有意义

* `repr`：是否对类的 `__repr__` 与 `__str__` 方法进行改造，使得当你使用 `print(inst)` 或 `str(inst)`, `repr(inst)` 时，能够得到一个高可读性的输出，将数据类实例中的字段和对应值展示出来，默认为 True

* `parser_cls`：指定负责解析类声明与解析数据的核心解析器类，默认是 `utype.parser.ClassParser`
* `options`：指定一个解析选项用于控制解析行为，具体参数可以参考 [Options 解析选项](/zh/references/options)

!!! note
	 `@utype.dataclass` 装饰器只会对你的类中的某些方法进行调整，并不会影响类的基类或者元类，所以你可以为你的数据类指定任意的基类与元类

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

**Schema 类的字段命名限制**
正是因为 Schema 类继承了字典的方法，所以 Schema 类的字段不能直接使用这些方法的名称作为字段属性的名称

```python
import utype

class DataSchema(utype.Schema):
	items: list = Field(max_length=10)   # wrong
```

正确的声明方式是使用字段的别名来指向它的真实名称，用其他的名称来作为属性值

```python
import utype

class DataSchema(utype.Schema):
	item_list: list = Field(alias='items', max_length=10)   # ok

data = DataSchema(items=(1, 2))   # ok
print(data.item_list)
# > [1, 2]
print(data['items'])
# > [1, 2]
print(data.items)
# > <built-in method items of DataSchema object>
```

这样，你访问这个字段使用的属性是 `item_list`，与字典的 `items()` 方法并不冲突，并且你可以使用 


!!! note
	Schema 类和 DataClass 类都是 utype 预先定义好的数据类，其中有着一定的行为偏好，如果你属性它们的特征和用法可以直接继承使用，如果你需要更多的定制行为，可以通过 `@utype.dataclass` 声明数据类

### DataClass 类
DataClass 类没有任何基类，所以在这个类中声明字段没有名称上的限制，实现更加简洁，但同时无法像 Schema 一样支持字典相关的方法

* `__parser_cls__`：
* `__options__`：

DataClass 类对应的偏好配置是
* `init_attributes=True`
* `init_properties=True`
* `set_properties=True`
* `repr=True`

### 通过 ClassParser 制造

这是最接近底层的一种制造方式，一般不建议使用，

事实上，为数据类提供声明分析和运行时数据解析功能的是来自 `utype.parser.ClassParser` 的类解析器

所有的数据类在声明时都依赖它来进行字段解析和方法制造，从而获得在运行时解析数据的能力


## 数据解析与校验

### 配置解析选项


**运行时解析选项**

* allow_runtime_options


### 自定义 `__init__` 函数

数据类中自定义的 `__init__` 函数默认就会获得函数解析的能力，也就是你可以在 `__init__` 函数中声明类型与字段配置，


!!! note
	在  `__init__` 函数中声明的字段类型和配置仅用于输入数据到初始化函数间的解析，并不会作为数据类的字段，这样避免了重复声明造成的冲突或歧义



### 属性访问钩子

* `post_setattr`
* `post_delattr`

在预定义好的 Schema 和 DataClass 类中，也有着相应的可覆盖函数
* `__post_setattr__`
* `__post_delattr__`


### 整体性校验函数

* `__validate__`
* `__post_init__`


## 序列化编码
当我们需要将一个数据类中的数据通过网络进行传输时，就往往需要使用 JSON，XML 等格式对数据进行序列化编码

### 编码函数

### 注册编码器

TODO