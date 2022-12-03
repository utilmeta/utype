# Field 字段配置

## 可选与默认值

* `required`：字段是否必传，默认为 True，你可以声明 `required=False` 得到一个可选字段，也可以通过声明默认值得到

!!! note
	当必传的字段没有出现在输入数据中时，会抛出一个 `exc.AbsenceError` 错误，其中的 `item` 属性指出了缺失的字段名称

* `default`：给出一个默认值，当字段没有在输入数据中提供时将会使用该默认值作为字段的值，默认为空，也就是说默认情况下

!!! note
	当你在函数参数或者类属性中没有声明 Field 作为对应值而是使用一个其他的值时，那个值就会自动作为字段的默认值
```python
class User(Schema):
	name: str = ''
	age: int = Field(ge=1, default=0)

print(User())
# > User(name='', age=0)
```

* `default_factory`：给出一个制造默认值的工厂函数，会在解析时调用它得到默认值
```python
class Schema(Schema):
	info: dict = Field(default_factory=dict)
	current_time: datetime = Field(default_factory=datetime.now)
```

以下情况推荐使用 `default_factory`
* 你的默认值（dict, list, tuple, set 等）
* 你需要在解析时动态得出默认值，如当前的时间


### 缺省字段
如果你的字段是可选的（ `required=False`）且没有声明默认值，那么它就是一个缺省字段，它有着如下的特点
* 如果你指定了字段配置中 `unprovided` 参数的值，那么你访问缺省字段会得到该值
* 否则在数据类实例中访问缺省字段的属性会抛出 `AttributeError`
* 无法在函数参数中使用，因为那样会使得参数的值出现歧义

## 说明与标记

* `title`：字段的标题字符串，仅用于提高可读性，与输入数据中的字段名称无关
* `description`：字段的描述文档字符串
* `example`：给出该字段的一个示例数据
* `decprecated`：是否弃用（不鼓励使用）这个字段，默认为 False，如果开启，则当输入数据包含整个字段时，会给出一个 `DeprecatedWarning` 警告（不会抛出错误，但会看到警告输出信息）


## 约束配置

Field 中也支持使用参数方式来为类型配置约束，其中参数与 Rule 中的内置约束相同

```python
```


更完整的约束参数及用法可以直接参考 [Rule 类型约束](./rule)，只不过 Field 将 Rule 中以类属性声明约束的方式转化为通过实例化参数来声明

!!! note
	一般来说，如果你声明的约束需要被多个字段复用，那么建议使用继承 Rule 的方式声明类型约束，否则可用使用 Field 来直接声明
	事实上，Field 中声明的约束也是通过制造一个新的 Rule 类来实现约束功能的


## 别名配置
* `alias`：指定字段的别名
* `alias_from`
* `case_insensitive`

!!! note
	如果你的别名配置是针对整个数据类的，可以使用  Options 进行统一声明，具体用法可以参考 [Options 的别名配置](./options)



## 模式配置
你声明出的数据类可能需要支持多种场景的，而字段可能在不同的场景有着不同的行为，如
* 读取模式：将数据表中的数据通过 SQL 读取出来并转化为 Schema 实例进行返回
* 更新模式：将 HTTP 请求体中的数据转化为 Schema 实例并对目标资源进行更新

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
* `password` ：声明了 `writeonly=True`，也就是说它只用于写模式，不能用于读取
* `signup_time` ：声明了 `readonly=True`，也就是说它只用于读模式，不能用于更新
* `username`：没有模式声明，可以用于读写


utype 提供了这种机制，使得你只需要声明一个数据类，就能够在不同的模式中有着不同的表现

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

@utype.parse(mode='w')
def update_user(user: UserSchema):
	pass

```

这样将会按照 `'w'`（写模式）对参数进行解析，在例子的函数中即使对 `user` 参数传入了 `signup_time` 字段也不会被接收（因为声明了 `readonly=True`）

### 模式的扩展

在 mode 参数中你可以声明自定义的模式，一般来说模式使用一个英文小写字母来表示

然后只需要在 

utype 支持按照不同的模式输出 json-schema 文档，所以你可以只用一个数据类得到它在读取，更新，创建等多种模式场景下的输入和输出模板

## 输入与输出

* `no_input`
* `no_output`

`no_input=True` 的字段虽然不能在数据中输入，但是可以
* 应用 `default` 或 `default_factory` 的默认值
* 在数据类中被属性赋值


!!! warning
	`no_output` 中 “输出” 的概念仅适用于数据类，所以在函数字段中声明 `no_output=True` 是没有意义的 

### 动态判断

 `no_input` 和 `no_output` 参数都可以传入一个函数来根据字段的值来动态判断是否接受输入或接受输出

```python
class DynamicSchema(Schema):
	title: Optional[str] = Field(no_output=lambda v: v is None)
	content: str = Field(no_input=lambda v: not v)

print(dict(DynamicSchema(title=None, content='test')))
# > {'content': 'test'}
```
 
title 字段使用 `Optional[str]` 方式标识它接受字符串或者 None 作为输入，而在 `no_output` 参数中我们指定了一个函数，标识如果输入为 None 的话则不进行输出

!!! note
	在数据类 Schema 中，“输出” 的含义就是其字典数据中存放的值，你可以直接通过 `dict(inst)` 得到字典类型的数据，或者 `json.dumps(inst)` 得到 JSON 数据
	如果一个字段接受输入但不提供输出，那么你可以通过实例的属性访问到那个字段的值，但是它不会出现在  `dict(inst)` 的结果中


### 属性字段

使用 `@property` 可以定义更加原生的输入输出字段

你可以更精细的控制字段的输入和输出行为，而且可以通过一个字段来影响其他字段或内部私有属性的值


### 输入与输出模板

* 在函数参数中使用的是输入模板
* 在函数返回值中使用的是输出模板

另一种视角是 HTTP 请求，在提供给用户的 API 文档中
* 请求参数对应的是输入模板
* 响应参数对应的是输出模板


## 属性配置

* `unprovided`：当属性对应的字段没有在数据中提供时（也没有默认值），访问属性得到的值，当没有设置时访问属性会抛出 AttributeError

* `immutable`：该属性是否是不可变的，如果开启，则你无法对数据实例的该属性进行赋值或删除操作

!!! note
	严格意义上，在 Python 中，你无法让实例的属性彻底无法变更，如果开发者执意要做，可以通过操作 `__dict__` 等方法来变更属性，`immutable` 参数实际上承担着一种标记和提示的作用，提醒开发者这个字段是不应该被变更的



!!! warning
	属性配置仅在数据类中使用，在函数参数中声明没有意义

以数据类为例，如果把它的声明周期分为
* 数据输入
* 实例操作
* 数据输出

那么字段配置的作用分别为
* `no_input`：此字段不参与数据输入
* `immutable`：无法在实例中操作此字段（无法被赋值或删除）
* `no_output`：此字段不参与数据输出


## 错误处理

* `on_error`

这个参数有几个可选值
* `'throw'`：默认值，抛出错误
* `'exclude'`：将字段从结果中剔出（如果字段是必传的，则不能使用这个选项）
* `'preserve'`：将字段保留在结果中，也就是允许结果中有校验不通过的字段

!!! note
	即使在校验不通过时不抛出错误，utype 也会给出一个 warning，来指示相应的字段

一般来说，不建议使用 `'preserve'` 选项，

如果你希望配置针对整个数据类的错误处理策略，可以参考 [Options 错误处理](./options)



## 隐藏字段信息

* `secret`：是否是一个隐秘字段（如密码，密钥等），如果是，则数据类在打印或日志中相应的属性将会以 `'******'` 来表示，防止了密钥通过输出信息泄漏
!!! warning
	`secret` 参数并不影响数据的类型或者字段的输出，也就是说如果你直接将对应的字段打印出来，如果你需要参数以任意方式输出都是 `'******'` ，请使用 `SecretStr`

在 utype 的全局中有一个 `secret_names` 设置，默认将一些


## 字段依赖


* *`dependencies`