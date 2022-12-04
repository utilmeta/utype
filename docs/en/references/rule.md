# Rule - constraint type

在 utype 中，Rule 组件的作用是为类型施加约束，我们通过继承 `utype.Rule` 来使用它

## 基本用法

### 绑定类型
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

### 不绑定类型

```python
from utype import Rule

class LengthRule(Rule):
	max_length = 3
	min_length = 1

>>> LengthRule([1, 2, 3])
[1, 2, 3]
>>> LengthRule('abcde')
ConstraintError: Constraint: <max_length>: 3 violated
```

比如对于 length 约束而言，任何拥有 `__len__` 方法的类型（能够使用 `len()`）都支持，如
* str
* list
* tuple
* dict
* set


## 内置约束

### 范围约束
 * `gt` / `ge` / `lt` / `le` : 这四个参数分别对应着 >, >=, <, <=
```python
>>> rule = Rule(gt=4, le=2)
AssertionError: Rule lt/le (2) must > gt/ge (4)
>>> rule = Rule(ge=0.1, lt=1.0)
>>> rule('0.2')
0.2
>>> rule(1)
ValueError: value <1.0> not less than 1.0
```

!!! note
	如果同时设置了最小值最大值，则最大值不得小于最小值，且两者的类型需一致

### 长度约束
* `length`:  限制数据的**长度**，一般用于校验字符串和列表的长度，对于没有 `__len__` 方法的对象（如整数）将会校验转化为字符串后的长度
* `max_length`: 数据的**最大长度**，需要为一个正整数
* `min_length`: 数据的**最小长度**，需要为一个正整数，如果同时设置了最大长度规则，则最大长度需要大于最小长度
```python
>>> rule = Rule(length=3)
>>> rule(3.14)
ValueError: value <3.14> with length 4 not match the length 3
>>> rule(['A','B','C'])
['A', 'B', 'C']
>>> rule = Rule(max_length=4)
>>> rule('12345')
ValueError: value <'12345'> with length 5 is larger than max_length 4
>>> rule('r')
'r'
>>> rule = Rule(min_length=3)
>>> rule('A Very Long String ...')
'A Very Long String ...'
```

### 正则约束
* `regex`: 数据必须完全匹配这个参数的**正则**表达式
```python
>>> rule = Rule(regex='([A-Za-z0-9]+)')
>>> rule('abcABC123')
'abcABC123'
>>> rule('abc@123')
ValueError: value <'abc@123'> not match the regex '([A-Za-z0-9]+)'
```


### 常量与枚举

* `const`：数据必须全等于该常量

```python
import utype

class Const1(utype.Rule):
	const = 1

class ConstKey(utype.Rule):
	const = 'SECRET_KEY'
	
```

!!! note “全等的校验”
	`const` 不仅使用 Python 的全等符号校验值与常量是否 “相等”，还会判断它们的类型是否相等，因为在 Python 中，通过 `__eq__` 方法能够使得一种类型与任意值相等，另外比如 `True == 1` 是为真的，而 True 是 `bool` 类型，1 是 `int` 类型（在 Python 中 `bool` 是  `int` 的子类），所以无法通过 `const` 校验

* `enum`：数据必须是

* Literal
* Enum

#### 枚举数组

枚举数组是一种基于枚举的常见用法，数组中的每个元素都是枚举中的值
```python
import enum
import utype
from utype.types import Array

class EnumLevel(str, enum.Enum):  
    info = 'INFO'
    warn = 'WARN'
    error = 'ERROR'
  
class EnumLevelArray(list, Array):  
    __args__ = (EnumLevel,)  
```

```python
from utype.types import enum_array

level_array_type = enum_array(
	item_enum=['INFO', 'WARN', 'ERROR'],
	array_type=list,
	unique=True			   
)
```

在例子中我们制造了一个枚举数组类型，其中数组的每个元素都需要在 `['INFO', 'WARN', 'ERROR']` 中，并且数组中的每个元素都需要是唯一的

!!! note
	如果忽略顺序的话，直接将 `array_type` 设置为 `set` 也会获得去除的元素


### 数字约束
下面的约束仅适用于数字类型（int, float, Decimal）
* `max_digits`：规定数字的整数位最多有多少位数（不包括符号位）
* `multiple_of`：
* `round`：

!!! note
	round 并不是一个校验约束，而是一个转化约束，它并不校验当前的数据的小数位有多少，而是使用 Python 的 `round()` 方法将其转化到目标的位数

!!! warning
	虽然对于数字类型，`max_length` 等长度约束也起作用，但它们会校验
	`len(str(-10.1230))`，得到的长度会包含符号位，小数点和小数部分，

### 数组约束

* `contains`
* `max_contains`
* `min_contains`
* `unique_items`


## 扩展约束


## 约束模式

在 Rule 类中可以通过 `strict` 属性控制约束的模式，`strict` 默认为 True，可以在子类中

* `strict=True`：严格校验约束，对不满足的数据直接抛出错误，适合不信任输入数据来源的类型，如处理网络请求
* `strict=False`：尽可能让输入数据符合约束，

* max_length 截断：当数据

对于 min_length 违背，gt/lt 违背，正则违背等情况，无法进行

实际上由于约束支持自行扩展，在扩展或覆盖的约束中你可以调整不同的约束模式下的行为，或者自己声明一种新的约束模式


## 嵌套类型

* List
* Dict
* Tuple
* Set
等等

