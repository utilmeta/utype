# Field 字段配置
在 utype 中，Field 的作用是对数据类属性与函数参数进行字段配置，从而调节它们的行为，本篇文档我们来详细说明它的用法

## 可选与默认值

声明字段是否是可选的，以及指定字段的默认值是最常用的字段配置，即使不使用 Field 也可以声明，如
```python
from utype import Schema, parse

class UserSchema(Schema):
    name: str
    age: int = 0

@parse
def init_user(name: str, age: int = 0): pass
```
当数据类的属性值或函数参数的默认值不是一个 Field 实例时，它将会被处理为字段的默认值，其中

1. `name`：没有提供默认值，如果没有出现在输入数据中时，则会抛出一个 `exc.AbsenceError` 错误
2. `age`：指定了默认值 0，是可选的，当数据没有提供时会自动填充默认值

但是为了配合其他字段配置参数，Field 也提供了可选与默认值的配置参数，包括

* `required`：指定字段是否必传，默认为 True，你可以声明 `required=False` 得到一个可选字段，也可以通过声明默认值得到
* `default`：传入字段的默认值，当字段没有在输入数据中提供时将会使用该默认值作为字段的值

所以下面的写法与上面的例子是等价的
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

除此之外 Field 还提供了一些默认值的高级配置

* `default_factory`：给出一个制造默认值的工厂函数，会在解析时调用它得到默认值
```python
from utype import Schema, Field
from datetime import datetime

class InfoSchema(Schema):
	metadata: dict = Field(default_factory=dict)
	current_time: datetime = Field(default_factory=datetime.now)
```

例子中示例了一些建议使用 `default_factory` 参数的情况
1. 当你的默认值类型是 `dict`, `list`, `set` 等时，你应该不希望这个默认值被所有的实例共享引用，所以可以仅使用它们的类型作为制造默认值的工厂函数，比如例子中的 `metadata` 字段在缺省时会调用 `dict()` 得到一个空字典
2. 你需要在解析时动态得出默认值，比如例子中的 `current_time` 字典在缺省时会调用 `datetime.now()` 得到当前的时间

* `defer_default`：如果开启，这时默认值将不会在数据没有输入时填充作为数据的一部分，而只会在访问缺省的属性时被计算

```python
class InfoSchema(Schema):
	metadata: dict = Field(default_factory=dict, defer_default=True)
	current_time: datetime = Field(default_factory=datetime.now)

info = InfoSchema()   # no fields provided

print('metadata' in info)
# > False
print('current_time' in info)
# > True
```

可以看到，指定 `defer_default=True` 后，默认值不会在解析时直接进行填充，所以例子中缺省的 `'metadata'` 字段也不会出现在数据中，但是当访问这个属性时，会触发默认值的计算。这样带来的特性是没有传入或赋值的数据可以通过属性访问到值，但不会进行输出

需要注意的是，当你指定的是 `default_factory` 且数据缺省时，每次访问都会生成新的对象，所以你直接对属性对象进行操作是不会反映到数据中的，除非你对属性先赋值，后操作，如
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
	`defer_default` 仅对数据类有效，对函数无效，因为函数参数一定需要传入一个有意义的值，所以会直接计算 default 进行传入

### 不稳定字段
如果你的字段是可选的（ `required=False`），并且没有指定默认值，那么该字段就是一个不稳定的字段，因为当该字段没有传入时，如果你访问该字段的属性将会抛出 `AttributeError`，使用键访问字段也会抛出 `KeyError`，如
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
	在函数中不能声明这样的字段作为参数，对于可选的字段必须指定默认值，因为函数参数必须传入一个有意义的值


## 约束配置

Field 中也支持使用参数方式来为类型配置约束，其中参数与 Rule 中的内置约束相同，如

```python
from utype import Schema, Field  
  
class ArticleSchema(Schema):  
    slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*") 
    title: str = Field(min_length=1, max_length=50) 
    views: int = Field(ge=0, default=0)  
```

更完整的约束参数及用法可以直接参考 [Rule 类型约束](/zh/references/rule)， Field 只是使用实例化参数的方式声明 Rule 中的内置约束

!!! note
	一般来说，如果你声明的约束需要被多个字段复用，那么建议使用继承 Rule 的方式声明约束类型，否则可用使用 Field 来直接声明
	事实上，Field 中声明的约束也是通过制造一个新的 Rule 类来实现约束功能的

Field 也提供了一些常用的内置约束声明的简写，如
* `round`：提供了 `decimal_places=Lax(value)` 的 Lax 约束的简写，作用是直接将数据使用 Python 的 `round()` 方法保留相应的小数位，如
```python
from utype import Schema, Field  

class Index(Schema):
	ratio: float = Field(round=2)

index = Index(ratio='12.3456')
print(index.ratio)
# 12.35
```

## 别名配置

默认情况下，utype 会将类属性的名称或函数参数的名称作为字段的名称，你只能使用一致的名称进行输入才会被识别为对应的字段，从而进行解析，但是这在一定情况下可能无法满足我们的命名要求，比如

1. 字段名称不符合字段的准入规则，比如以下划线开头
2. 字段无法声明为 Python 变量名称，比如含有特殊字符
3. 字段名称与当前数据类或父类的内部方法重复

所以 utype 提供了一些控制字段别名的参数，包括

* `alias`：指定字段的别名，别名可以用于在输入中表示该字段，如
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
1. `seg_key`：数据字段的名称 `__key__` 含有双下划线，作为属性名称则无法被识别为字段
2. `at_param`：数据字段的名称 `@param` 含有特殊字符，无法在 Python 中声明为一个变量
3. `item_list`：数据字段的名称 `items` 是字典类型的固有方法，不能直接作为 Schema 数据类的字段属性名称

在实例中，你仍然可以使用对应的属性名称访问到字段的值，并且在数据类中，`alias` 也默认作为输出字段的名称

```python
print(inst.item_list)
# > [1, 2]
print(inst['@param'])
# > 3
print(dict(inst))
# > {'__key__': 'value', '@param': 3, 'items': [1, 2]}
```

而且，即使字段声明了别名，你还是可以通过字段的属性名称对数据进行输入
```python
attr_inst = AliasSchema(seg_key='value', item_list=[1, 2], at_param=3)
print(dict(attr_inst))
# > {'__key__': 'value', '@param': 3, 'items': [1, 2]}
```

除了使用 `alias` 指定单个别名外，utype 提供了指定多个输入别名的方式

* `alias_from`：指定一系列可以从中转化的别名，如
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

比如例子中我们为 `content`，`created_at` 等字段指定了多个输入别名，可以用于兼容旧版本的接口，或者接入不同来源的数据 API，无需再进行手工的逐个识别转化

比如旧版本的文章内容字段名称是 `'body'` 或 `'text'`，在当前版本中被废弃并使用了 `'content'` 作为内容字段的名称，所以使用 `Field(alias_from=['text', 'body'])` 来兼容老版本的数据输入

可以看到，`alias_from` 指定的输入只会用于识别输入数据，不会用于输出或属性访问，但可以用于键值访问，或者判断字段是否在数据中

!!! warning
	在同一个数据类或函数中，字段的别名不可以重合，或者与其他的字段的属性名或别名冲突，即所有字段的属性名和别名整体都不能存在重复，这样无论数据中的字段是以属性名还是别名的形式传递，数据类或函数都能够正确地识别和解析，并且可以在多次转化中保持幂等


### 别名生成函数
如果你的别名能够从属性名称以一定的规律进行生成，可以直接指定一个函数用于生成别名，如

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

我们编写了一个用于生成首字母大写的驼峰命名的生成函数 `pascal_case`，比如调用 `'created_at'` 就会得到 `'CreatedAt'`，然后将函数作为字段的 `alias` 或 `alias_from` 参数传入，使得对应的别名能够直接从属性名称生成

### 大小写不敏感
默认情况下字段的识别是大小写敏感的，但你可以通过开启下面的参数调整这个行为

* `case_insensitive`：默认为 False，开启后可以大小写不敏感地识别字段，如

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

大小写不敏感的配置会应用于字段的所有的别名，包括属性名称，`alias` 与 `alias_from`，所以你使用任意的大小写输入任意的别名都可以被识别出来

而且可以看到，大小写不敏感的配置还支持键值访问与字段的包含（`in`）识别，如使用 `'CREATED_AT' in article` 时会被 Schema 识别到并映射至 `'created_at'` 字段

!!! note
	如果你需要针对整个数据类或函数进行别名配置或大小写敏感性配置，可以直接使用 Options 解析选项，具体用法可以参考 [Options 的别名配置](/zh/references/options)



## 说明与标记

Field 提供一些说明与标记的参数，它们虽然不会对解析产生影响，但是可以更加清楚的描述字段的用途，示例等，并且可以被整合到生成的 API 文档中，比如

* `title`：传入一个字符串指定字段的标题（与名称或别名无关，仅起到说明作用）
* `description`：传入一个字符串用于描述字段的用途或使用说明
* `example`：给出该字段的一个示例数据

```python
from utype import Schema, Field  

class ArticleSchema(Schema):  
    slug: str = Field(  
		title='Article Slug'
        description='the url route of an article',
        example='my-awesome-article',    
    )  
    content: str = Field(description='the content of an article')  
```

除此之外 Field 还提供了一些有用的标记字段

* `deprecated`：是否弃用（不鼓励使用）该字段，默认为 False

弃用标志 `deprecated` 可以用于兼容旧版本的字段，并给出弃用提示，示例如下
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

在例子中，我们声明了一个名为 RequestSchema 的数据类，同时支持了弃用的旧版本字段 `querystring` 和 `body` 和新版本的 `query` 与 `data` 字段， 则当输入数据包含弃用的字段时，会给出 `DeprecatedWarning` 警告

在数据类的 `__validate__` 函数中，我们手动对弃用的字段转化到了新版本，虽然对于老版本字段的兼容，你也可以使用别名配置中的 `alias_from` 来进行自动的转化处理，但例子中的这种方法提供了更多的可控制性，比如新旧版本的数据可能使用了不同的编码方式或解析规则，需要分别用自定义的逻辑来处理时，就可以使用这种方法


## 输入与输出

Field 还提供了在字段级别调控数据的输入输出行为的配置，在 utype 中，输入与输出分别表示：

* **输入**：数据类的数据初始化，或者函数的调用传参
* **输出**：使用数据类实例进行传参，序列化的时候使用的实际数据，对于 Schema 类来说指的就是其自身的字典数据，对于其他数据类指的是使用 `__export__` 方法导出的数据

其中，字段输入行为的控制参数是

* `no_input`：指定字段是否不能进行输入，默认为 False

`no_input=True` 的字段虽然不能在数据中输入，但是可以在缺省是填充 `default` 或 `default_factory` 的默认值，或者在数据类中被属性赋值，例如

```python
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

我们可以看到

1. 例子中的 `slug` 字段指定了 `no_input=True`，所以即使 `'slug'` 字段出现在输入数据中，也会被忽略，在初始化完成后调用的 `__validate__` 函数中我们对 `slug` 字段进行了赋值，所以它会出现在结果中
2. 例子中的 `update_at` 字段，不接受数据输入，但在数据类初始化时会使用 `default_factory` 中的函数填充当前的时间，而且这个字段可以正常输出，也就意味着会与其他输出字段一并进行后续的操作（比如将数据更新到数据库中）

!!! note
	如果你除了需要禁用输入，还需要禁止属性被赋值的话，可以使用 `Field(no_input=True, immutable=True)`

而与之相对的，控制字段输出行为的参数是

* `no_output`：指定字段是否不能进行输出，默认为 False

 `no_output=True` 的字段虽然不能用于数据输出，但是可以使用属性访问到，从而可以作为计算其他数据的依赖值，例如
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

在这个例子中我们声明了一个 `no_output=True` 的字段 `access_key`，它虽然不进行输出，但是可以使用属性名称访问到，从而能够计算出 `key_sketch` 属性，这就是一种常见的密钥半隐藏处理场景，密钥字段本身（`access_key`）不会进行输出，只有处理后的结果字段（`key_sketch`）会进行输出


!!! warning
	`no_output` 中 “输出” 的概念仅适用于数据类，所以在函数字段中声明 `no_output=True` 是没有意义的 

### 使用函数动态判断

 `no_input` 和 `no_output` 参数都可以传入一个函数来根据字段的值来动态判断是否接受输入或接受输出

```python
from utype import Schema, Field  

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
 
在例子中，`title `字段在 `no_output` 参数中我们指定了一个函数，标识如果输入为 `None` 的话则不进行输出，所以例子中当数据类刚初始化时，`'title'` 字段是不在数据中的（尽管你可以使用属性访问到它）；而 `content` 字段指定的是当值为空时不进行输人，所以当传入非空值时会保留在数据中

!!! note
	在数据类 Schema 中，“输出” 数据的含义就是其字典数据中存放的值，因为你可以直接通过 `dict(inst)` 得到字典类型的数据，通过 `func(**inst)` 调用其他函数，或者 `json.dumps(inst)` 得到 JSON 数据
	如果一个字段接受输入但不提供输出，那么你可以通过实例的属性访问到那个字段的值，但是它不会出现在  `dict(inst)` 的结果中


## 模式配置

我们有时会需要某个字段拥有 “只读的” 或者 “只写的” 性质，这其实是我们需要支持 "读模式" 和 “写模式”，并让字段在不同模式中表现出不同的行为，

我们来看一个例子
```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(writeonly=True)
	signup_time: datetime = Field(readonly=True)
```

在例子中我们声明了一个 UserSchema 数据类，其中

* `username`：没有模式声明，可以用于读写
* `password` ：声明了 `writeonly=True`，也就是说它只用于写模式，不能用于读取
* `signup_time` ：声明了 `readonly=True`，也就是说它只用于读模式，不能用于更新


你声明出的数据类可能需要支持多种场景的，而字段可能在不同的场景有着不同的行为，如

* 读取模式：将数据表中的数据通过 SQL 读取出来并转化为 Schema 实例进行返回
* 更新模式：将 HTTP 请求体中的数据转化为 Schema 实例并对目标资源进行更新


utype 提供了这种机制，使得你只需要声明一个数据类，就能够在不同的模式中有着不同的表现， Field 提供了几个参数用于指定的字段支持的模式

* `mode`
* `readonly`：是 `mode='r'` 的一个常用简化表示
* `writeonly`：是 `mode='w'` 的一个常用简化表示

readonly, writeonly 与 mode 间只能指定一个参数

```python
class UserRead(UserSchema):
	__options__ = Options(mode='r')

class UserWrite(UserSchema):
	__options__ = Options(mode='w')
```


除此之外，你也可以在函数参数解析的装饰器 `@utype.parse` 中定义解析模式，如
```python
import utype

@utype.parse(options=Options(mode='w'))
def update_user(user: UserSchema):
	pass

```

这样将会按照 `'w'`（写模式）对参数进行解析，在例子的函数中即使对 `user` 参数传入了 `signup_time` 字段也不会被接收（因为声明了 `readonly=True`）

!!! warning
	在函数的参数字段中无法声明模式字段，函数模式是对所有的数据类参数作用的

### 模式的扩展

在 mode 参数中你可以声明自定义的模式，一般来说模式使用一个英文小写字母来表示

然后只需要在 

utype 支持按照不同的模式输出 json-schema 文档，所以你可以只用一个数据类得到它在读取，更新，创建等多种模式场景下的输入和输出模板

一般建议使用的模式名称有
* `'r'`：读取，进行不影响系统状态的信息获取操作
* `'w'`：写入/更新，往往是对当前系统的资源进行更新
* `'a'`：追加/创建，向当前系统新增一个资源

由于具体模式的赋值与使用场景都是由你决定，所以 utype 并不会

### 模式与输入输出

指定一个字段为某个模式，实际上就是指定字段在其他模式中禁用输入与输出，比如字段的模式为 `'r'`，而当前的解析模式为 `'w'`，那么此时这个字段就不会用于输入，自然也不会进行输出

事实上输入输出参数也可以配置为一个模式字符串

```python

class Article(Schema):
	slug: str = Field(no_input='wa')
```

* 在更新与创建时禁用输入，但不禁用输出（也就是如果被赋值了，可以作为结果中的字段进行输出）
* 没有限制读取时的输入输出，所以可以从数据源中读入，并且输出给请求的客户端


## 属性配置

* `immutable`：该属性是否是不可变的，默认为 False，如果开启，则你无法对数据类实例的对应属性进行赋值或删除操作

!!! note
	严格意义上，在 Python 中，你无法让实例的属性彻底无法变更，如果开发者执意要做，可以通过操作 `__dict__` 等方法来变更属性，`immutable` 参数实际上也承担着一种标记和提示的作用，提醒开发者这个字段是不应该被变更的


* `secret`：是否是一个隐秘字段（如密码，密钥等），如果是，则数据类在打印或日志中相应的属性将会以 `'******'` 来表示，防止了密钥通过输出信息泄漏

!!! warning
	`secret` 参数并不影响数据的类型或者字段的输出，也就是说如果你直接将对应的字段打印出来，如果你需要参数以任意方式输出都是 `'******'` ，请使用 `SecretStr`

在 Options 选项中有一个 `secret_names` 选项，默认将一些常用的密钥和密码字段名称

* `'password'`
* `'secret'`
* `'dsn'`
* `'private_key'
* `'session_key'
* `'pwd'
* `'passphrase'


!!! warning
	属性配置仅在数据类中使用，在函数参数中声明没有意义

以数据类为例，如果把它的声明周期分为

那么字段配置的作用分别为
* 数据输入 `no_input`：此字段不参与数据输入
* 实例操作 `immutable`：无法在实例中操作此字段（无法被赋值或删除）
* 数据输出 `no_output`：此字段不参与数据输出


## 错误处理

Field 还可以为字段配置错误处理策略，也就是当字段对应的数据无法通过解析校验时如何处理，它对应的参数是

* `on_error`：配置字段的错误处理行为，这个参数有几个可选值

1. `'throw'`：默认值，抛出错误
2. `'exclude'`：将字段从结果中剔出（如果字段是必传的，则不能使用这个选项）
3. `'preserve'`：将字段保留在结果中，也就是允许结果中有校验不通过的字段

我们来看一个例子
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

当指定 `on_error='throw'` （也是默认值），字段传递的非法数据会被直接抛出错误；当 `on_error='exclude'` 时，遇到非法数据会给出警告，但是会将其忽略，不添加到结果中；当 `on_error='preserve'`，遇到非法数据会在给出警告后依然将其添加到结果中

!!! warning
	除非你知道自己在做什么，否则最好不要指定 `on_error='preserve'`，那样会破坏类型声明的保证，导致你访问到的数据不满足声明的类型，从而在运行时产生预期之外的错误

如果你希望配置针对整个数据类的错误处理策略，可以参考 [Options 错误处理选项](/zh/references/options)


## 字段依赖


* `dependencies`

使用属性声明依赖
