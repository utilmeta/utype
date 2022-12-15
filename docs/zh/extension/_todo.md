
# TYPE


### 类型转化器与转化函数

utype 提供的类型转换器可以通过 `from utype import TypeTransformer, type_transform` 来引入

* `TypeTransformer`
* `type_transform`：接受

1. 如果输入值的类型完全匹配目标类型，则直接返回，无需转化
2. 在

### 转化偏好
utype 已经内置了一些转化偏好选项，通过解析选项 Options 声明，其中包括

* `no_explicit_cast`
* `no_data_loss`


**不要注册万用类型**
按照这种语法，如果你声明一个 `object` 作为 `*classes` 或者 `type` 作为 `metaclass` 将会匹配到所有的类型，即所有的类型都会使用你的这个 ”万用类型“ 函数作为转化函数，但是 utype 并不建议这样的声明方式，你可以直接继承 TypeTransformer 类并覆盖其中的  `__call__` 函数达到处理所有类型的效果



# CLS

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

!!! warning
	本节的功能尚未在当前版本实现，可以忽略该文档

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

!!! warning
	本节的功能尚未在当前版本实现，可以忽略该文档
	
当我们需要将一个数据类中的数据通过网络进行传输时，就往往需要使用 JSON，XML 等格式对数据进行序列化编码

### 编码函数

### 注册编码器


# Rule
## 声明方式

### 类型绑定
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

>>> v = PositiveInt('3')
>>> type(v)
<class 'int'>
```

你会发现，
需要注意的是，Rule 只为

如果你绑定了类型，在转化中，Rule 会先完成类型的转化，再进行约束的校验

**多重继承顺序**

按照 MRO 来说，

实际上，由于 Rule 类并不是使用 `__init__` 方式来完成解析校验，而是使用元类的 `__call__` 方法，


**使用属性绑定类型**

* `__origin__`：源类型
* `__args__`：内部参数，实际上对应着嵌套类型中

* List/Set：比如对于列表，这个参数表示内部元素的类型，
* Tuple
* Dict


### 泛型约束

```python
from utype import Rule

class LengthRule(Rule):
	max_length = 3
	min_length = 1

assert LengthRule([1, 2, 3]) == [1, 2, 3]
assert LengthRule('123') == '123'

str_len = LengthRule[str]
arr_len = LengthRule[list]

```

比如对于 length 约束而言，如果没有绑定类型，任何拥有 `__len__` 方法的类型（能够使用 `len()`）都可以支持进行校验

!!! note
	如果没有绑定类型，并且没有指定任何约束，单纯的 Rule 类的行为就像 `typing.Any` 类型一样，可以接受任意类型的任意值，将输入值原样返回

```python
class LengthRule(Rule):  
    min_length = 1  
    max_length = 3  
  
str_len = LengthRule[str]
arr_len = LengthRule[list]
arr_int_len = LengthRule[list][int]

print(arr_int_len((1, '2', b'3')))
# > [1, 2, 3]
```

### 混入与复用

使用 Rule 声明出的约束类型，自然可以被继承和复用

你可以混入多组约束，但是只能指定一个源类型

如果你需要指定多个源类型，需要使用类型的逻辑运算，将它们以一定的逻辑运算符组合起来，组合完成后新的逻辑类型还可以被视为单个源类型


### `@utype.apply` 装饰器



## 扩展约束

### 增加约束

* `constraints_cls`
* `__constraints__`

### 调节约束校验逻辑

### 调节约束校验顺序

* `__constraints__`


## 调控解析

* `pre_validate`
* `post_validate`
* `parse`


# Field

## 限制与扩展

Field 支持通过继承来对字段配置进行限制或扩展

### 限制参数

utype 自身就提供了一个受到限制的 Field 子类，名为 `Param`，用于配置函数参数的行为，它去掉了一些仅在数据类中起作用的声明参数，比如

* `required`：无需传入，没有指定默认值的参数就是必传参数
* `defer_default`：
* `no_output`
* `immutable`
* `repr`

一些配置的作用页不尽相同
* `alias`：函数参数只需要通过 `alias_from` 指定能够从中转化的别名即可，


由于函数中的参数必须提供值，要么是传入的值，要么是默认值，无法像数据类中那样能够更精细的控制输出等行为

并且把 `default` 参数作为了类初始化的第一个参数，可以直接使用 `Param(None)` 来指定默认值为 None


### 扩展参数

扩展 Field 的参数也需要继承，只不过

Field 是 utype 中声明字段配置的接口类，但并不是字段行为控制的实现类，

Field 自身并不实现字段行为的控制功能，而是通过 `utype.parser.field.ParserField` 类来实现的

所以如果你需要将 Field 扩展的参数对字段行为造成影响

就需要你继承 ParserField，并覆盖你需要扩展的方法，

我们来进行一下示例

```python

class CustomeField(Field):
	pass

class CustomParserField(ParserField):
	field_cls = CustomeField
```


# Options


* `secret_names`


在 Options 选项中有一个 `secret_names` 选项，默认将一些常用的密钥和密码字段名称
* `'password'`
* `'secret'`
* `'dsn'`
* `'private_key'
* `'session_key'
* `'pwd'
* `'passphrase'

如果你的字段使用 `secret_names` 中的名称命名，且没有自定义 `repr` 参数，则会自动使用 `'******'` 来表示对应的名称



## 运行时选项

* `override`：如果在类的解析选项中声明了 `override=True`，即表示这个选项是不可被覆盖的，如果没有指定这个选项，并且在运行时的选项中指定了 `override=True`，那么运行时选项就会覆盖当前数据类的解析选项

不过这个 ”覆盖“ 行为其实指的是在 context 中传递给字段中数据类的解析参数，相当于隔着一级，比如函数的 options 传入到函数某个参数的数据类中，

但如果是 **同级** 的指定，比如使用 `init_dataclass` 或者 `cls.__from__` 方法指定的 options，那就是用于当前数据的初始化解析，所以会直接应用 （`options or parser.options`），而不会关心其中是否指定了 override


**运行时 Options 的传递性问题**

* 默认产生的 `RuntimeOptions` 是 `override=False`，（Options 的 `override` 与 RuntimeOptions 的 `override` 含义不同），此时传递到新的数据类中，原有的 options 会被忽略，转而使用该数据类的 options
* 忽略了 options 时传递的 RuntimeOptions 实际上只传递一个 context，包括解析深度，收集到的解析错误等信息
* 如果对应的字段数据中已经有了 `'__options__'` 字段

另一种 ”运行时“ 解析方法


```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	password: str = Field(mode='wa')
	followers_num: int = Field(readonly=True)  # or mode='r'
	signup_time: datetime = Field(
		mode='ra', 
		no_input='a',
		default_factory=datetime.now
	)

# runtime
class UserRead(UserSchema):
	__options__ = Options(mode='r')

class UserUpdate(UserSchema):
	__options__ = Options(mode='w')

class UserCreate(UserSchema):
	__options__ = Options(mode='a')
```

实际上，由于数据类可以接受子类的实例，所以如果需要达到 runtime options 的需求，完全可以子类化目标数据类，指定不同的 options，然后实例化进行传递

这样的好处是对于一个特定的类的实例化，不会因为输入数据中的

如果需要显式的运行时选项实例，我们需要强制使用 `__from__` 等方法，从 `__new__` 开始创建空实例，然后往其中喂解析好的数据，这样与 `__init__` 方法直接地区分开，确保对于普通的输入数据来说，无法对输入数据作手脚进行选项调整，只能开发者通过代码的方式显式

也就是说，禁用 ”数据“ 中的动态能力，保留 ”代码“ 中的动态能力

用户可以选择把 `__from__` 方法关闭，然后禁止 allow_subclasses，来禁用其他的选项配置
（尽管开发者仍然可以自己 `__new__` 一个出来，自己完成解析数据的注入，我们无法突破语言层面的动态性）


在嵌套的

`init_dataclass`
* `cls`：类
* `data`：数据，可以是原始的 str/bytes 数据
* `options`：可以传入一个运行时解析选项，默认使用
* `context`：传入当前的 runtime 语境，可以传递数据的相对路径，深度，已收集的错误等信息，每当进入一个新的数据类实例时，都会生成一个新的 context，使用传入的 options 或类本身的静态 options 作为解析选项



输入模板： 
* 如果指定了 `__init__` 函数，那就使用 `__init__` 函数的参数模板吗？


首先：为了支持数据初始化， `__init__` 函数不能声明  POSITIONAL ONLY ARGS 或 POSITIONAL VAR，所有参数都支持通过 kw 传递

**注入与覆盖性问题**

一个数据类使用的运行时 options 能否影响到它的字段中的其他数据类的解析？

默认是不影响，无论字段中的数据类是否声明 options，都会在解析对应的数据类时以它的 options 为准

如果指定了 `override=True`，运行时
如果对应的字段中的数据类依然声明了 `override=True`，则依然以它为主，否则按照运行时的 options 解析

