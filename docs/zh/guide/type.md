# 类型与约束

## Python 中的类型

在开始介绍 utype 的用法之前，我们先来回顾一下 Python 中的类型以及类型注解语法
!!! note
	如果你已经掌握了 Python 中的类型以及类型注解语法，可以直接阅读下一部分

在 Python 中，每个类（`class`）都是一个类型，当你使用 `type` 函数调用它的实例时就会得到这个类本身，如
```python
class MyClass:
	pass

my_inst = MyClass()
assert type(my_inst) == MyClass
assert isinstance(my_inst, MyClass)
```

!!! note
	Python 是一门 **强类型** 的 **动态类型** 语言，强类型意味着每个值都有着唯一确定的类型，改变值的类型必须进行 **显式** 的类型转化，动态类型意味着在编程语言层面上不提供运行时的类型保证，比如函数可以接受任意类型的传参

Python 中已经有一些内置的类型，我们无需导入就可以直接引用，如

* `int`：整数
* `float`：浮点数
* `bool`：布尔值，表示真（True）或假（False）
* `str`：字符串
* `bytes`：字节串，以二进制字节序列保存数据，可以与 str 进行互相转化
* `list`：列表，长度和元素均可变
* `tuple`：元组，长度固定，且不可修改其中的元素
* `set`：集合，内部元素唯一且无序
* `dict`：字典，提供着键与值的映射关系

还有一些标准库也提供了常用的类型，我们无需安装第三方依赖就可以直接导入，比如

* `datetime`：日期时间库，提供了 `datetime`，`date`，`time`，`timedelta` 等类型来表示日期，时间和时长
* `enum`：提供了 `Enum` 类型来表示枚举值（取值范围固定的值）
* `uuid`：提供了 `UUID` 类型来表示一个全局唯一标识
* `decimal`：提供了 `Decimal` 类型，用于表示十进制定点数
除此之外还有很多由标准库或第三方库提供的类型，不再一一列举

### 类型注解语法

在 Python 3.6 以后版本引入了一种类型注解机制，它可以声明一个变量的类型，如
```python
name: str = 'test'
age: int = 1
```

当你为变量添加了类型注解后，如果试图在代码中去访问该类型不支持的方法或操作，IDE 就会向你给出警告提示，这样能够在开发时减少不必要的 bug

但需要注意的是，Python 本身并不提供对类型注解的保障，也就是说变量的实际值可能跟声明的类型不相符，或者被赋值改变了，如
```python
age: int = 'nonsense'
age += 1   # TypeError: can only concatenate str (not "int") to str
```

!!! note
	`utype` 就是基于 Python 的类型注解语法，把这种提示性的注解声明变成可以依赖的运行时类型安全保障机制，所以使用 `utype` 需要先掌握 Python 的类型注解

### 嵌套类型
除了直接使用类型本身作注解外，Python 还支持嵌套类型的语法来用于更多的场景，比如声明一个元素都是字符串的列表类型
```python
from typing import Any, List, Dict

class Series:
	names: List[str] = ['n1', 'n2']
	values: List[float] = [0.1, 0.2]
	metadata: Dict[str, Any] = {'version': '0.1.1'}
```

我们先从 typing 标准库中引入了声明嵌套类型所需要的组件，其中 `Any` 表示不固定类型，允许任意值，而  typing 提供的嵌套类型中常用的有

* `List`：声明一个列表，需要在方括号中传入一个类型，表示其元素的类型
* `Set`：声明一个集合，需要在方括号中传入一个类型，表示其元素的类型
* `Tuple`：声明一个元组，可以在方括号中传入多个类型，用于表示在元组中对应位置元素的类型
* `Dict`：声明一个字典，需要在方括号中传入两个类型，分别表示键的类型和值的类型

如果你使用的是 Python 3.9+ ，那么你可以直接使用 `list`, `set` 等类型来代替 typing 提供的组件，可以达到一样的效果，如
```python
from typing import Any

class Series:
	names: list[str] = ['n1', 'n2']
	values: list[float] = [0.1, 0.2]
	metadata: dict[str, Any] = {'version': '0.1.1'}
```

### 特殊注解类型
除了以上的类型注解外，Python 还支持一些常用的特殊注解类型，比如

* `Union`：可以使用 `Union[X, Y]` 的语法表示对应值是 X 类型或 Y 类型中的一种
* `Optional`：`Optional[X]` 其实就是 `Union[X, None]` 的简写，用于表示允许 X 类型和 None 值

```python
from typing import Union, Optional

class Form:
	name: str = 'alice'
	address: Optional[str] = None
	phone_number: Union[str, int] = 12345
```

如果你使用的是 Python 3.10+，那么 Union 类型可以使用更简洁的或（`|`）运算符声明
```python
class Form:
	name: str = 'alice'
	address: str | None = None
	phone_number: str | int = 12345
```

!!! warning
	`Optional` 并不用于表示一个字段是 “可选的” 还是 “必传的”，这种特性是通过声明默认值或者在 [Field 字段配置](/zh/references/field) 中使用  `required` 参数实现的

* `Callable`：声明一个可调用对象，往往用于注解函数对象，如 `Callable[[int], str]` 表示一个把整数转为字符串的函数
* `Type`：声明一种类型本身，如
```python
from typing import Type

class MyClass:
	pass

class Collection:
	int_type: Type[int] = int
	my_type: Type[MyClass] = MyClass
```

* `Literal`：用于声明一个常量或者一系列枚举值，如
```python
from typing import Literal

class File:
	fmt: Literal['binary'] = 'binary'
	mode: Literal['r', 'rb', 'w', 'wb'] = 'rb'
	opening: Literal[1, True, 'true'] = True
```

### 函数类型注解
在函数中你也可以使用同样的方式对函数参数和返回值进行类型提示，比如

=== "Python 3.6 以上"  
	```python
	from typing import Dict, Optional
	
	password_dict: Dict[str, str] = {}   
	# pretend this is a database that store user passwords
	
	def login(username: str, password: str) -> Optioanl[Dict[str, str]]:
		if password_dict.get(username) == password:
			return {
				'username': username,
			}
		return None
	```  

=== "Python 3.10 以上"
	```python
	password_dict: Dict[str, str] = {}
	# pretend this is a database that store user passwords
	
	def login(username: str, password: str) -> dict[str, str] | None:
		if password_dict.get(username) == password:
			return {
				'username': username,
			}
		return None
	```

!!! note
	有一些特殊的函数需要特殊的返回值提示，如生成器函数，异步生成器函数等，我们将在 [函数类型解析](/zh/guide/func) 中具体介绍

### 类型引用字符串
在类型声明中除了传入类型本身的引用外，还可以传入在全局命名空间有定义的类型的名称字符串来进行注解，这样的方式主要用于

1. **类属性中引用类本身**
简称自引用，如
```python
class Comment:
	content: str
	on_comment: 'Comment' = None
	comments: List['Comment']
```

2. **引用尚未被定义的类型**
这种用法很常见，如循环引用
```python
class Article:
	title: str
	comments: List['Comment']
	
class Comment:
	content: str
	on_article: Article = None
```

3. **需要引用的类型已在局域空间中被污染**
比如在局域的命名空间中，你需要的类型的名称已经被占用了，那么你可以使用字符串引用来在全局命名空间中引用对应的类型
```python
from datetime import datetime

class Article:
	str: str = 'placeholder'
	title: 'str'
	datetime: datetime = datetime.now()
	created_at: 'datetime'
```
!!! warning
	在上面这种情况下，如果 title 使用的是 `title: str` 作为类型注解，那么实际上注解的是对应局域命名空间中的字符串 `'placeholdr'`，没有意义

需要注意的是，使用字符串引用的类型必须在全局命名空间（`globals()`）中定义，你不能使用函数中的局域变量进行引用提示，比如
```python
def not_working():
    class Article:
		title: str
		comments: List['Comment']     # will not work properly
		
	class Comment:
		content: str
		on_article: Article = None    # this will work
```

### 延申资料
以上的文档只列举了最常用的语法和类型，如果你想了解更多的 Python 类型注解语法，可以参考以下文档

* <a href="https://docs.python.org/zh-cn/3/library/typing.html" target="_blank">Python 类型注解官方文档</a>
* <a href="https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html" target="_blank">Mypy Type hints cheat sheet</a>


## 约束类型
在 utype 中，所有的校验和解析转化都是围绕着类型的，utype 除了支持上一节中提到的 Python 类型注解语法对类型完成转化外，还支持为类型施加 **约束**

约束的概念很简单，比如我需要一个正数，或者我一个长度在 10 到 20 间的字符串，那么使用基本类型 `int`, `str` 就无法表达，但使用 utype 只需要如下简短的声明就可以完成
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

class MyStr(str, Rule):
	min_length = 10
	max_length = 20
```

utype 支持使用声明式的语法为类型施加常用的约束，目前内置支持的约束包括

* **范围约束**：约束值的最大值，最小值（`gt`,  `ge`,  `lt`,  `le`）
* **长度约束**：约束值的长度或者长度范围（`length`，`max_length`，`min_length`）
* **常量与枚举约束**：约束值必须为某个常量或者在固定的取值范围中（`const`，`enum`）
* **正则约束**：约束值必须满足一个正则表达式（`regex`）
* **数字约束**：约束数字值的最大数字长度，保留位数等（`max_digits`，`round`）
* **列表约束**：约束列表值的元素唯一性，包含的类型等（`unique_items`，`contains`）

!!! note
	更全面的约束参数介绍请参考 [Rule 类中的约束](../references/rule)

这些内置约束基本就能覆盖到常见的大部分场景，除此之外 utype 还支持自定义约束和自定义校验逻辑等，我们将会在后面介绍

在 utype 中为类型施加约束的方式有两种，下面我们一一介绍

### Rule 混入继承
最常用的一种方式是声明一个新类，使用源类型和 Rule 类作为基类，在这个类的属性中声明你需要的约束，如
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0
    
num = PositiveInt('3')
print(type(num))
# > <class 'int'>
```
这里需要说明的是，调用混入了 Rule 的约束类型得到的结果仍然是源类型，Rule 类只进行了约束的校验，比如在上面的例子中

* 源类型：`int`
* 约束类型：`PositiveInt`
* 约束：`gt=0`（值大于零）
* 调用的结果类型：`int`（源类型）

所以，可以理解为 **约束类型 = 源类型 + Rule 类 + 约束属性**，调用约束类型得到的结果是 **符合约束** 的源类型实例（不符合约束或无法完成转化则抛出错误）

源类型并不需要是基本类型，还可以是自定义的类型，如
```python
import utype

class MonthType(int):
    def get_days(self, year: int) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

class Month(MonthType, utype.Rule):
	gt = 0
	le = 12

mon = Month(b'11')
assert isinstance(mon, MonthType)

print(mon.get_days(2020))
# > 30
```

### `@utype.apply` 装饰器
另一种为类型施加约束的方式是使用 `@utype.apply` 装饰器，直接为目标类型以装饰器参数的方式声明约束，如
```python
import utype

@utype.apply(gt=0, le=12)  
class Month(int):  
    @utype.parse
    def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

mon = Month(b'11')
assert isinstance(mon, Month)

print(mon.get_days(2020))
# > 30
```

!!! note
	其实使用 `@utype.apply` 装饰器方式本质上是在 utype 内部完成的 Rule 混入继承，声明更加简洁方便，但对应约束校验逻辑的调整空间有限

**isinstance 检测**
在 Python 中，一般使用 `isinstance(obj, t)` 来测试对象 obj 是否是类型 t 的实例（包括 t 的子类的实例），而对于约束类型，这个行为实际上检测的是对象是否是约束类型的源类型的实例，并且满足约束条件，所以
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

print(isinstance(1, PositiveInt))
# > True
print(isinstance(-2, PositiveInt))
# > False
print(isinstance(b'3', PositiveInt))
# > False
```
这个特性可以用于检测值是否符合约束类型的要求

### 内置的约束类型

utype 已经声明好了一些常用的约束类型，你可以直接从 `utype.types` 中进行引用，如

* PositiveInt：正数，不包括 0
* NaturalInt：自然数，包括 0
* Month：月数，1 到 12
* Day：天数，1 到 31
* Week：周数，1 到 53
* WeekDay：周中的天数，1 到 7
* Quater：季度，1 到 4
* Hour：小时，0 到 23
* Minute：分钟，0 到 59
* Second：秒，0 到 59
* SlugStr：常用于文章 URL 的字符串格式，由小写字母，数字和连字符 `-` 组成
* EmailStr：满足邮箱地址格式要求的字符串

其实这些类型的声明非常简单，你也完全可以自己声明实现，utype 建议把常用的约束声明为固定的约束类型，这样你就可以直接在代码中引用它进行类型注解了

## 嵌套类型

我们知道在类型注解中可以使用如 `List[int]` 的语法声明嵌套类型，但是它无法直接作为一个可以进行转化和校验的类型，utype 提供了一些可嵌套的类型，提供与类型注解语法一致的声明方式，但是声明出的类型可以直接用于校验与转化，如
```python
import enum  
from utype import types, exc
  
class EnumLevel(str, enum.Enum):  
    info = 'INFO'  
    warn = 'WARN'  
    error = 'ERROR'  
  
level_array = types.Array[EnumLevel]

print(level_array(['INFO', 'WARN']))
# > [<EnumLevel.info: 'INFO'>, <EnumLevel.warn: 'WARN'>]

try:
	level_array(['OTHER'])
except exc.ParserError as e:
	print(e)
	"""
	ParseError: 'OTHER' is not a valid EnumLevel
	"""

value = ('1', True, b'2.3')

print(Array[int](value))
# > [1, 1, 2]
```

可以看到在例子中我们声明了一个名为 `level_array` 的嵌套类型，使用 `Array` 作为主类型，其中嵌套的元素类型是一个枚举类，这个嵌套类型就能够直接被调用并完成数据的解析转化了

utype 目前支持的嵌套类型有
* `types.Array`：支持为列表，元组，集合等序列结构声明元素类型和约束，默认源类型是 `list`
* `types.Object`：支持为字典，映射声明元素类型和约束，默认源类型是 `dict`

你可以继承这些嵌套类型，赋予约束并指定其他的源类型等，用法和 Rule 相似（因为这些嵌套类型也是继承自 Rule）
```python
from utype import types

class UniqueTuple(types.Array):  
	__origin__ = tuple
    unique_items = True

unique_tuple = UniqueTuple[int, int, str]
print(unique_tuple(['1', '2', 't']))
# > (1, 2, 't')

try:
	unique_tuple(['1', '1', '3'])
except exc.ParserError as e:
	print(e)
	"""
	ConstraintError: Constraint: <unique_items>: True violated: value is not unique
	"""
```

对于嵌套类型的继承，我们使用 `__origin__` 属性来覆盖默认的源类型，而不是继承的方式，这样能够不与嵌套类型默认的源类型发生冲突

!!! note
	目前由于嵌套类型使用的并不是 Python 的泛型注解，所以 IDE 还无法对嵌套的内部元素进行类型提示，接下来会考虑通过编写 IDE 插件的方式增加这方面的易用性


## 类型的逻辑运算
utype 支持使用 Python 的原生逻辑运算符对类型进行逻辑运算，用于组合更加复杂的类型条件，如
```python
from utype import Rule, exc
from typing import Literal

class IntWeekDay(int, Rule):  
	gt = 0
	le = 7

weekday = IntWeekDay ^ Literal['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

assert weekday('6') == 6
assert weekday(b'tue') == 'tue'

try:
	weekday('8')
except exc.ParseError as e:
	print(e)
	"""
	Constraint: <le>: 7 violated;
	Constraint: <enum>: ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun') violated
	"""

from datetime import date

weekday_or_date = weekday | date

assert weekday_or_date(b'5') == 5
assert weekday_or_date('fri') == 'fri'
assert weekday_or_date('2000-1-1') == date(2000, 1, 1)
```

在例子中我们声明的 `weekday` 类型是使用异或运算符连接了 IntWeekDay 和一个 Literal 枚举列表，也就是说  `weekday` 类型需要输入值匹配这两个类型中的一个，utype 支持的逻辑运算符有

- 或（`|`）：数据需要至少匹配其中一个类型
- 异或（`^`）：数据必须匹配其中的一个条件，不能是多个或0个
- 非（`~`）：数据必须不匹配对应的类型
- 和（`&`）：数据必须同时匹配所有的类型

!!! note
	utype 可以支持任意层数的逻辑嵌套，所以理论上你可以使用这种语法声明任意复杂的类型逻辑条件，但在实践中并不建议使用过于复杂的类型，那样会使得开发和调试都变得困难

**常用场景：反选排除**
一种逻辑组合的常见的场景是需要使用某个类型，但排除一些值，比如作为被除数就需要排除 0，此时我们就可以先把需要排除的值用约束声明出来，再取反后与源类型结合，就能够得到我们需要的排除类型了

```python
from utype import Rule, exc
	
class Zero(Rule):
	const = 0

Divisor = float & ~Zero

try:
	Divisor('0')
except exc.ParseError as e:
	print(e)
	"""
	 Negate condition: Zero(const=0) is violated
	"""
```

使用和（`&`）逻辑会依序对条件进行转化，在例子中我们声明了一个被除数类型 Divisor，是 float 类型排除了 0，在解析时，首先会将输入数据转化为 float，然后再判断能否完成对 Zero 的匹配，如果匹配，则解析失败（因为对应的条件为非），否则解析成功

除了可以使用 `const` 约束排除一个值，还可以使用 `enum` 约束指定排除的枚举值，如

```python
from utype import Rule, exc

class Infinity(Rule):  
    enum = [float("inf"), float("-inf")]  
  
FiniteFloat = float & ~Infinity

assert FiniteFloat(b'3.3') == 3.3

try:
	FiniteFloat('inf')
except exc.ParseError as e:
	print(e)
	"""
	Negate condition: Infinity(enum=[inf, -inf]) is violated
	"""
```

### 限制与版本兼容

需要注意的是，要想使用 utype 提供的逻辑类型功能，参与逻辑运算的类型中必须至少有一个是使用 utype 的约束类型，因为 Python 原生对类型逻辑运算的支持很有限

* `Python < 3.10`：不支持任何类型逻辑运算，使用 `str | int` 这样的语法会报错 `TypeError: unsupported operand type(s) for |: 'type' and 'type'`
* `Python >= 3.10`：支持对类型使用或（`|`）运算符得到 Union 类型，可以用于类型注解但无法用于类型转化，也不支持使用其他运算符，如异或（`^`）或者非（`~`）

但只要使用 utype 的约束类型，在 `Python >= 3.7` 以上都能支持所有的逻辑运算符操作，并且声明出的类型不仅可以用于类型注解，还能直接进行解析转化

为了方便声明，在 `utype.types` 中已经提供了一些不包含约束属性的约束类型，如 `Int`，`Str`，`Bool`，`Float` 等，你可以直接把它们作为 **可以参与逻辑运算的** 基本类型

```python
from utype.types import Int

any_of1 = Int | bool | str   # ok
any_of2 = bool | Int | str   # ok

xor_type1 = Int ^ bool ^ str  # ok
xor_type2 = bool ^ Int ^ str  # ok
xor_type3 = bool ^ str ^ Int  # TypeError: unsupported operand type(s) for ^

revert_type = ~int     # TypeError: bad operand type for unary ~: 'type'
revert_type = ~Int     # ok
print(revert_type | xor_type2)
# > AnyOf(Not(Int(int)), OneOf(bool, Int(int), str))
```

!!! warning
	在逻辑运算表达式中，约束类型必须至少是其中的第一个或第二个元素，否则第一个元素和第二个元素会先结合，对应的元素不支持相应的操作则会直接报错


需要注意的是，只有使用 utype 约束类型参与的逻辑类型才能够提供按照逻辑条件的转化功能，你不能直接使用 Python 原生类型进行或操作后调用值
```python
(str | int)('some value')
# Python >= 3.6 TypeError: unsupported operand type(s) for |: 'type' and 'type'
# Python >= 3.10 TypeError: Cannot instantiate typing.Union
```

## 调节与扩展类型转化

!!! note
	这一节属于高级章节，适合于已经掌握 utype，希望自定义或者扩展类型转化用法的读者，如果你刚开始上手，可以直接阅读下一篇文档


Python 原生并没有提供任意类型值转化到其他任意类型的安全有效的方式，所有的类型转化逻辑都是由 utype 通过一个个转化函数提供的，但是由于每个开发者对类型的校验严格程度与转化方式都可能有着自己的偏好，所以 utype 的类型转化机制提供了多个可调整的偏好参数，并且支持对类型转化函数进行动态地注册，覆盖与扩展，这一节我们主要来介绍这部分内容


### 类型转化器与转化函数

utype 提供的类型转换器位于

* `TypeTransformer`
* `type_transform`：接受

1. 如果输入值的类型完全匹配目标类型，则直接返回，无需转化
2. 在

### 转化偏好
utype 已经内置了一些转化偏好选项，通过解析选项 Options 声明，其中包括

#### `no_explicit_cast` - 无显式类型转化

其实是尽量不发生预期之外的类型转化，实现上会将类型按照基本类型分组

* `null`：None
* `boolean`：0，1,  True, False
* `number`：int/float/decimal 等数字
* `string`：str/bytes/bytearray 等字符串与二进制字节
* `array`：list/tuple/set
* `object`：dict/mapping

开启这个选项后，同组的类型之间可以互相转化，但是不同组的类型之间不能相互转化

特例
*  **Decimal**：Decimal 允许从 str 转化，因为从浮点数转化会出现失真
* **日期与时间**：支持从日期字符串与时间戳转化，因为没有更原生的类型表达方式

最明显的一个区别是，默认情况下，允许字符串到列表/字典的转化，前提是满足某些模式，比如
```python
from utype import type_transform

print(type_transform('[1,2,3]', list))
# > [1, 2, 3]
print(type_transform('{"value": true}', dict))
# > {'value': True}
```

但是在开启 `no_explicit_cast` 参数后，不会允许这样的转化

#### `no_data_loss` - 无信息损耗

在默认情况下为 False，也就是接受信息出现损耗的转化，比如

* `bool`："Some Value" -> True
* `int`：3.1415 -> 3
* `date`： datetime.now()  -> datetime.now().date()
* `dict`：`[{"a": 1}, {"b": 2}]`  -> `{"a": 1}`

这些例子中，输入数据的信息都在进行类型转化时发生了不可逆的压缩或损耗，如果开启 `no_data_loss`，则表示只接受没有信息损耗的转化，如

* bool：只接受 True, False, 0, 1, None，和一些明显表示布尔值的字符串，如 `'true'`，`'f'`，`'no'` 等
* int:  "3"  ->  3
* datetime: date(2000,1,1) -> datetime(2000,1,1)
* list: "1,2,3" -> [1,2,3]
* list：any iterable -> list(iter(iterable))
* dict: "a=b&c=d" -> {"a": "b", "c“: "d"}
* dict: [{"a": 1}]   -> {"a": 1}     (only 1 item)
* str:  {'a': 1} -> "{"a": 1}"

!!! note
	需要注意的是，这些偏好只是给转换器函数的 “**提示**”或者 flag，Python 本身没有什么机制能够强制保障这些条件，它们会在具体的类型转化函数中实施，如果你自己定义了类型转化函数，也需要自行判断这些 flag 并实施对应的转化策略


### 转化器的注册

转换器的转化发生在类的初始化 **之前**，也就是说如果你直接调用类的初始化函数制造实例是不会调用到转换器函数的，除非你使用 `type_transform(data, t)`  函数，或者在函数，数据类中解析对应类型时

* `*classes`
* `metaclass`
* `attr`
* `detector`
* `allow_subclasses`
* `priority`
* `to`：可以指定转换器注册的 `TypeTransformer` 类，默认情况下你注册的转化器是全局的，指定一个  `TypeTransformer`  子类后仅对这个类生效，你可以在 Options 中声明类型的转化类

默认情况下，越晚注册的转换器优先级越高，所以能够实现 “覆盖” 的效果


**不要注册万用类型**
按照这种语法，如果你声明一个 `object` 作为 `*classes` 或者 `type` 作为 `metaclass` 将会匹配到所有的类型，即所有的类型都会使用你的这个 ”万用类型“ 函数作为转化函数，但是 utype 并不建议这样的声明方式，你可以直接继承 TypeTransformer 类并覆盖其中的  `__call__` 函数达到处理所有类型的效果


### 未知类型的处理
如果一个类型无法在 utype 中找到匹配的转换器（包括由开发者自行注册的转换器）就会被称为未知类型，对于未知类型的转化处理（与输入数据不匹配），utype 在解析选项 Options 中提供了一个 `unresolved_types` 来指定其行为，它有几个取值

* `'ignore'`：忽略，不再转化，而是直接使用输入值作为结果
* `'init'`：尝试使用 `t(data)` 对未知类型进行初始化
* `'throw'`：直接抛出错误，不再转化，这个选项是默认值

### 兼容其他类库

#### 兼容 `pydantic`


#### 兼容 `attrs`


#### 兼容 `dataclasses` 标准库