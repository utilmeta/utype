# Rule 类型约束
在 utype 中，Rule 的作用是为类型施加约束，本篇文档我们来详细说明它的用法

## 内置约束
Rule 类已经内置了一系列的约束，当你继承 Rule 的时候，只需要把约束名称作为属性声明出来即可获得该约束的能力。Rule 目前支持的内置约束如下

### 范围约束
范围约束用于限制数据的范围，如最大，最小值等，它们包括

 * `gt` ：输入值必须大于 `gt` 值
 * `ge` ：输入值必须大于等于 `ge` 值
 * `lt` ：输入值必须小于 `lt` 值
 * `le` ：输入值必须小于等于 `le` 值
```python
from utype import Rule, exc

class WeekDay(int, Rule):  
    ge = 1  
    le = 7

assert WeekDay('3.0') == 3

try:
	WeekDay(8)
except exc.ConstraintError as e:
	print(e) 
	"""
	Constraint: <le>: 7 violated
	"""
```

!!! warning
	如果同时设置了最小值最大值，则最大值不得小于最小值，且两者的类型需一致
	
范围约束并没有类型的限制，只要类型声明了对应的比较方法（`__gt__`，`__ge__`，`__lt__`，`__le__`），就可以支持范围约束，比如

```python
from utype import Rule, exc
from datetime import datetime

class Year2020(Rule, datetime):  
    ge = datetime(2020, 1, 1)  
    lt = datetime(2021, 1, 1)

assert Year2020('2020-03-04') == datetime(2020, 3, 4) 

try:
	Year2020('2021-01-01')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <lt>: datetime.datetime(2021, 1, 1, 0, 0) violated
	"""
```

!!! note
	所有的约束在违背时都会抛出一个 `utype.exc.ConstraintError`，其中记录的错误信息，包括约束的名称，约束的值，输入的值等
	不过如果你不确定是由什么因素造成的解析错误，可以使用所有 utype 解析错误的基类 `utype.exc.ParseError` 来捕获


### 长度约束
范围约束用于限制数据的长度，一般用于校验字符串或列表等数据，包括

* `length`:  输入数据的长度必须等于 `length` 值
* `max_length`：输入数据的长度必须小于等于  `max_length` 的值
* `min_length`：输入数据的长度必须大于等于  `min_length` 的值
```python
from utype import Rule, exc

class LengthRule(Rule):
	max_length = 3
	min_length = 1

assert LengthRule([1, 2, 3]) == [1, 2, 3]

try:
	LengthRule('abcde')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_length>: 3 violated
	"""
```

所有的长度约束必须都是正整数，如果设置了 `length` ，就不能再设置 `max_length` 或 `min_length`

!!! note
	如果输入数据的类型没有定义 `__len__` 方法（如整数），将会校验转化为字符串后的长度，也就是说取 `len(str(value))`，所以如果需要校验数字的最大位数，建议使用 `max_digits` 约束


### 正则约束
正则表达式往往能够声明更加丰富的字符串校验规则，用途很多，正则约束如下

* `regex`：指定一个正则表达式，数据必须完全匹配这个正则表达式
```python
from utype import Rule, exc

class Email(str, Rule):  
    regex = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"

assert Email('dev@utype.io') == 'dev@utype.io'

try:
	Email('invalid#email.com')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <regex>: 
	'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\\.[A-Z|a-z]{2,})+' violated
	"""
```

例子中我们声明了一个用于校验邮箱地址的约束类型 Email

### 常量与枚举

* `const`：值得一个常量值，输入数据必须全等于该常量
```python
from utype import Rule, exc

class Const1(Rule):
	const = 1

class ConstKey(str, Rule):
	const = 'SECRET_KEY'

assert ConstKey(b'SECRET_KEY') == 'SECRET_KEY'

try:
	Const1(True)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <const>: 1 violated
	"""
```

如果你为常量约束指定了源类型，则 Rule 会先完成类型转化，再校验常量是否相等，否则会直接进行比较

值得注意的是，`const` 不仅使用 Python 的全等符号（`==`）校验值与常量是否 “相等”，还会判断它们的类型是否相等，因为在 Python 中，通过 `__eq__` 方法能够使得一种类型与任意值相等，比如 `True == 1` 就是为真的，而 True 是 `bool` 类型，1 是 `int` 类型（在 Python 中 `bool` 是  `int` 的子类），所以无法通过 `const` 校验

* `enum`：可以传入一个列表，集合或者一个 Enum 类，数据必须是在 `enum` 规定的取值范围之内
```python
from utype import Rule, exc

class Infinity(float, Rule):  
    enum = [float("inf"), float("-inf")]

assert Infinity('-infinity') == float("-inf")

try:
	Infinity(10.5)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <enum>: [inf, -inf] violated
	"""
```

!!! warning
	即使 `enum` 参数传入了一个 Enum 类，也并不代表会将结果转化为 Enum 类的实例，而是仅使用  Enum 类所声明的数据范围

!!! note 
	在类型声明中，你也可以直接使用 `Literal[...]` 来声明常量或者枚举值 

### 数字约束
数字约束用于对数字类型（int, float, Decimal）施加限制，包括

* `max_digits`：限制数字的的最大位数（不包括符号位或小数点）
* `multiple_of`：数字必须是 `multiple_of` 指定的数值的倍数
```python
from utype import Rule, exc

class Hundreds(int, Rule):
	max_digits = 3
	multiple_of = 100

assert Hundreds('200') == 200

try:
	Hundreds(1000)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_digits>: 3 violated
	"""

try:
	Hundreds(120)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <multiple_of>: 100 violated
	"""
```

!!! note
	如果数据在 0 到 1 之间（比如 `0.0123`），那么最左边的 0 并不算作一位，只计算小数位 4 位，所以 `max_digits` 也可以理解为最大有效位数

* `decimal_places`：限制数字的小数部分的最大位数不能超过这个值
```python
from utype import Rule, exc
import decimal

class ConDecimal(decimal.Decimal, Rule):  
    decimal_places = 2  
    max_digits = 4

assert ConDecimal(1.5) == decimal.Decimal('1.50')

try:
	ConDecimal(123.4)   
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_digits>: 4 violated
	"""

try:
	ConDecimal('1.500')   
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <decimal_places>: 2 violated
	"""
```

如果约束的源类型是是定点数 `decimal.Decimal`，当输入数据的小数位数不足时会先进行补齐，所以数据 `123.4` 会被先补齐到 `Decimal('123.40')` ，再校验 `max_digits` 就无法通过

并且如果传入的数据包含小数位，那么无论末尾是否是 0，都会进行计算，比如 `Decimal('1.500')`，那么就会按照定点数的小数位计算 3 位

!!! warning
	虽然对于数字类型，`max_length` 等长度约束也起作用，但它们会按照 `len(str(value))` 进行校验，得到的长度会包含符号位和小数点，所以建议使用 `max_digits` 对数字的位数进行限制

### 数组约束
数组约束用于对约束列表（list），元组（tuple），集合（set）等可以遍历单个元素的数据，包括

* `contains`：指定一个类型（可以是普通类型或约束类型），数据中必须包含匹配的元素
* `max_contains`：最多匹配 `contains` 类型的元素数量
* `min_contains`：最少匹配 `contains` 类型的元素数量
```python
from utype import Rule, exc

class Const1(int, Rule):
	const = 1

class ConTuple(tuple, Rule):
	contains = Const1
	max_contains = 3

assert ConTuple([1, True]) == (1, True)

try:
	ConTuple([0, 2]) 
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <contains>: Const1(int, const=1) violated: 
	Const1(int, const=1) not contained in value
	"""

try:
	ConTuple([1, True, b'1', '1.0'])
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_contains>: 3 violated: 
	value contains 4 of Const1(int, const=1), 
	which is bigger than max_contains
	"""
```

例子中类型 ConTuple 的 `contains` 约束指定的是转换为整数后为 1 的类型，最大匹配数 `max_contains` 为 3，所以如果数据中没有元素能够与 Const1 类型匹配，或者匹配元素的数量超过 3 个，都会抛出错误

!!! note
	`contains` 约束仅校验元素是否匹配，并不会输出元素的类型转化结果，对元素进行类型转化需要使用嵌套类型的声明方式，或者在类中声明 `__args__` 属性

* `unique_items`：元素是否需要唯一
```python
from utype import Rule, exc, types

class UniqueList(types.Array):
	unique_items = True

assert UniqueList[int]([1, '2', 3.5]) == [1, 2, 3]

try:
	UniqueList[int]([1, '1', True])
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <unique_items>: True violated: value is not unique
	"""
```

例子中我们使用的是 `UniqueList[int]` 进行转化，所以会先转化元素类型，再进行约束校验

!!! note
	如果你约束的源类型是集合（set），那么它在转化后就是去重的，所以无需指定 `unique_items` 了


### Lax 宽松约束

Lax 约束（aka 宽松约束，转化式约束）指的是一种不严格的约束，它实现的效果是：尽最大努力把输入数据向满足约束的目标进行转化

声明宽松约束只需要从 utype 中引入 `Lax` 类，并将约束值使用 Lax 包裹起来，如
```python
from utype import Rule, Lax

class LaxLength(Rule):
	max_length = Lax(3)

print(LaxLength('ab'))
# > ab

print(LaxLength('abcd'))
# > abc
```

例子中当输入 `'abcd'` 不满足宽松约束 `max_length` 时，会直接按照  `max_length` 对数据长度进行截断，输出 `'abc'`，而不是像严格约束那样直接抛出错误

不同的约束在宽松模式下的表现不同，宽松模式支持的约束和各自的表现分别为

* `max_length`：定义一个松散的最大长度，如果值的长度大于它，则截断到给定的最大长度
* `length`：如果数据大于这个长度，则截断到 `length` 对应的长度，如果数据小于这个长度，则抛出错误
* `ge`：如果值小于 `ge`，则直接输出 `ge` 的值，否则使用输入值
* `le`：如果值大于 `le`，则直接输出 `le` 的值，否则使用输入值
* `decimal_places`：不再对小数位数进行校验，而是直接按照 `decimals_places` 对小数位进行保留，与 Python 内置的 `round()` 方法的效果一致
* `max_digits`：如果数字位数超过最大位数，则从小到大舍去小数位，如果仍然无法满足，则抛出错误
* `multiple_of`：如果数据不是 `multiple_of` 的整数倍，则取比输入数据小的最近输入数据的整数倍的值
* `const`：直接输出常量
* `enum`：如果数据不在范围内，则直接输出取值范围的首个值
* `unique_items`：如果数据存在重复，则返回去重后的数据

!!! note
	由于 Lax 模式下的 `decimals_places` 较为常用，所以 Field 提供了一个 `round` 参数进行简化，如使用 `Field(round=3)` 作为 `Field(decimal_places=Lax(3))` 的简写

一般约束只进行校验，但宽松约束却可能会对输入数据进行转化，在转化中虽然可能会出现信息损失，但宽松约束也会保障转化是 **幂等性** 的，也就是一个数据经过多次转化得到的是与单次转化相同的值

!!! note
	由于约束转化只能从给定数据中压缩信息，不能添加数据信息，所以无法为 min_length, gt, lt 等约束采取宽松模式


