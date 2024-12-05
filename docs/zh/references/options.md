# Options 解析选项
在 utype 中，Options 可以用来调控数据类与函数的解析行为，本篇文档我们来详细说明它的用法

## 类型转化选项

在数据解析中，类型转化是其中最关键的部分，Options 中提供了一些选项来调控类型转化的行为

### 转化偏好

* `no_explicit_cast`：无显式类型转化，默认为 False

无显式类型转化的含义是尽量不发生预期之外的类型转化，实现上会将类型按照基本类型分组

1. `null`：None
2. `boolean`：0, 1, True, False
3. `number`：int/float/decimal 等数字
4. `string`：str/bytes/bytearray 等字符串与二进制字节
5. `array`：list/tuple/set
6. `object`：dict/mapping

开启 `no_explicit_cast` 后，同组的类型之间可以互相转化，不同组的类型之间不能相互转化，但存在一定的特例，比如 Decimal（定点数） 允许从 str 转化，因为从浮点数转化会出现失真；datetime 等类型也支持从日期字符串与时间戳转化，因为没有更原生的类型表达方式

我们举例来说明以下，默认情况下，utype 允许字符串到列表/字典的转化，前提是满足某些模式，比如
```python
from utype import type_transform

print(type_transform('[1,2,3]', list))
# > [1, 2, 3]
print(type_transform('{"value": true}', dict))
# > {'value': True}
```

但是在开启 `no_explicit_cast` 参数后，不会允许这样的转化
```python
from utype import type_transform, Options

try:
	type_transform('[1,2,3]', list, options=Options(no_explicit_cast=True))
except TypeError:
	pass

try:
	type_transform('{"value": true}', dict, options=Options(no_explicit_cast=True))
except TypeError:
	pass
	
print(type_transform((1, 2), list, options=Options(no_explicit_cast=True)))
# > [1, 2]
```

 * `no_data_loss`：不允许转化中发生信息损耗，默认为 False

默认情况下我们允许在类型转化中存在信息的损耗，比如

```python
from utype import type_transform

print(type_transform("Some Value", bool))
# > True

print(type_transform(3.1415, int))
# > 3

from datetime import date
print(type_transform('2022-03-04 10:11:12', date))
# 2022-03-04
```

这些例子中，输入数据的信息都在进行类型转化时发生了不可逆的压缩或损耗，如果开启 `no_data_loss`，则这些发生了信息损耗的转化都会报错

```python
from utype import type_transform, Options

try:
	type_transform(3.1415, int, options=Options(no_data_loss=True))
except TypeError:
	pass
```

只接受没有信息损失的转化，比如

 1. `bool`：只接受 `True`, `False`, `0`, `1` 和一些明显表示布尔值的字符串，如 `'true'`，`'f'`，`'no'` 等
 2. `int`：不接受有有效小数位的 `float` 和 `Decimal`，比如 `3.14`
 3. `date`：不接受从 `datetime` 或包含时分秒部分的字符串进行转化

!!! note
	需要注意的是，这些偏好只是给转换器函数的 “**提示**” 或者 flag，Python 本身没有什么机制能够强制保障这些条件，它们会在具体的类型转化函数中实施，如果你自己定义了类型转化函数，也需要自行判断这些 flag 并实施对应的转化策略

### 未知类型的处理

如果一个类型无法在 utype 中找到匹配的转换器（包括由开发者自行注册的转换器）就会被称为未知类型，对于未知类型的转化处理（与输入数据不匹配），utype 在解析选项 Options 中提供的配置参数为

* `unresolved_types`：指定处理未知类型的行为，它有几个取值

	1. `'ignore'`：忽略，不再转化，而是直接使用输入值作为结果
	2. `'init'`：尝试使用 `t(data)` 对未知类型进行初始化
	3. `'throw'`：直接抛出错误，不再转化，这个选项是默认值

```python
from utype import Schema, Options

class MyClass:  
    def __init__(self, value):  
        self.value = value  
          
class MySchema(Schema):  
    __options__ = Options(  
        unresolved_types='init',  
    )  
      
    inst: MyClass = None  
  
data = MySchema(inst=3)

print(data.inst.value)
# > 3
```


## 数据处理选项

Options 提供了一些选项用于对函数的参数以及数据类的输入数据进行整体调控或限制，包括

* `addition`：调控超出声明范围之外的参数，有几个选项可以指定

	1. `None`：默认选项，直接忽略，不进行接收和处理
	2. `True`：接受额外的参数作为数据的一部分
	3. `False`：禁止额外参数，如果输入中包含额外参数，则直接抛出错误
	4. `<type>`：指定一个类型，表示额外参数的值都需要转化到这个类型

下面来示例一下 `addition` 的用法
```python
from utype import Schema, Options, exc

class User(Schema):  
    name: str  
    level: int = 0

data = {'name': 'Test', 'code': 'XYZ'}
print(dict(User.__from__(data)))   # default: addition=None
# > {'name': 'Test', 'level': 0}

user = User.__from__(data, options=Options(addition=True))
print(dict(user))
# > {'name': 'Test', 'level': 0, 'code': 'XYZ'}

try:
	User.__from__(data, options=Options(addition=False))
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['code'] exceeded
	"""
```

!!! note
	对于函数而言，可以通过声明 `**kwargs` 参数来表示调控额外参数的接受和类型，所以一般不需要声明 `addition` 参数，除非需要禁止额外参数，则声明 `addition=False` 即可


* `max_depth`：限制数据嵌套的最大深度。这个参数主要用于限制自引用或循环引用的数据结构，避免出现递归栈溢出

```python
from utype import Schema, Options, exc

class Comment(Schema):  
    __options__ = Options(max_depth=3)  
    content: str  
    comment: 'Comment' = None  
  
comment = {'content': 'stuck'}  
comment['comment'] = comment 

try:  
    Comment(**comment)  
except exc.ParseError as e:  
    print(e)  
    """  
    parse item: ['comment'] failed:    
    parse item: ['comment'] failed:   
    parse item: ['comment'] failed: max_depth: 3 exceed: 4  
    """
```

在例子中我们构造了一个自引用的字典，如果一直按照数据类声明进行解析，会一直解析到 Python 抛出递归错误，通过限制 `max_depth` 就可以控制解析的最大深度


另外 Options 还提供了控制传入参数数量的限制调节

* `max_params`：设置传入的参数的最大数量
* `min_params`：设置传入的参数的最小数量

这两个选项往往在开启了 `addition=True` 时使用，用于在解析前控制输入参数的数量，避免输入数据过大而耗费解析资源

```python
from utype import Schema, Options, exc

class Info(Schema):  
    __options__ = Options(  
        min_params=2,  
        max_params=5,  
        addition=True  
    )  
    version: str  
  
data = {  
    'version': 'v1',  
    'k1': 1,  
    'k2': 2,  
    'k3': 3  
}  
print(len(Info(**data)))
# > 4  

try:  
    Info(version='v1')
except exc.ParamsLackError as e:  
    print(e)  
    """
    min params num: 2 lacked: 1
    """

try:  
    Info(**data, k4=4, k5=5)
except exc.ParamsExceedError as e:  
    print(e)  
    """
    max params num: 5 exceed: 6
    """
```

可以看到，当输入参数数量少于 `min_params` 时，会抛出 `exc.ParamsLackError`，当输入参数数量大于 `max_params` 时，会抛出 `exc.ParamsExceedError`

**与长度约束的区别**

虽然使用 Rule 约束参数的  `max_length` 和 `min_length` 也能够约束字典的长度，但是它们与`max_params` / `min_params` 在作用上是有区别的

`max_params` / `min_params` 是在所有的字段解析开始之前对输入数据进行的校验，其中 `max_params` 是为了避免输入数据过大而耗费解析资源。而  `max_length` / `min_length` 在作用于数据类中，是用于在所有字段解析结束后，用于限制 **输出** 的数据的长度

并且 `max_params` / `min_params` 可以用于限制函数参数的输入，`max_length` / `min_length` 只能限制普通类型和数据类


## 错误处理

Options 提供了一系列错误处理选项，用于控制解析错误的行为，包括

* `collect_errors`：是否收集所有的错误，默认为 False

utype 对于数据类和函数的参数在解析时，如果发现出错的数据（无法完成类型转化或者无法满足约束），当 `collect_errors=False` 时，会直接将错误作为 `exc.ParseError` 进行抛出，也就是 ”快速失败“ 策略

但当 `collect_errors=True` 时，utype 会继续解析，并继续收集遇到的错误，当输入数据解析完毕后再将这些错误合并位一个  `exc.CollectedParseError` 进行抛出，从这个合并错误中能够获取到所有的输入数据错误信息

```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    __options__ = Options(  
        addition=False,
        collect_errors=True
    )  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)  
  
form = {  
    'username': '@attacker',  
    'password': '12345',  
    'token': 'XXX'  
}

try:
	LoginForm(**form)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	parse item: ['token'] exceeded
	"""
	print(len(e.errors))
	# > 3
```

!!! note
	当然，在 `collect_errors=True` 时，应对非法输入的性能会有适当下降，这样的配置更适合在调试期间使用，方便定位输入错误


* `max_errors`：在收集错误 `collect_errors=True` 模式下，设置一个错误数量阈值，如果错误数量达到这个阈值，则不再继续收集，而是直接将当前收集到的错误合并抛出

```python
from utype import Schema, Options, Field, exc

class LoginForm(Schema):  
    __options__ = Options(  
        addition=False,
        collect_errors=True,
        max_errors=2
    )  
  
    username: str = Field(regex='[0-9a-zA-Z]{3,20}')  
    password: str = Field(min_length=6, max_length=20)  
  
form = {  
    'username': '@attacker',  
    'password': '12345',  
    'token': 'XXX'  
}

try:
	LoginForm(**form)
except exc.CollectedParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated;
	parse item: ['password'] failed: Constraint: <min_length>: 6 violated;
	"""
	print(len(e.errors))
	# > 2
```

### 非法数据处理

除了整体性的错误错误策略外，Options 还提供了针对特定种类元素的错误处理策略

* `invalid_items`：如何处置列表/集合/元组中的非法元素
* `invalid_keys`：如何处置字典/映射中非法的键
* `invalid_values`：如何处置字典/映射中非法的值

这些配置都有着一样的可选项

1. `'throw'`：默认值，直接抛出错误
2. `'exclude'`：将非法元素从数据中剔除，只进行警告但不抛出错误
3. `'preserve'`：将非法元素保留，只进行警告但不抛出错误

我们来具体看一个例子
```python
from utype import Schema, Options, exc
from typing import List, Dict, Tuple

class IndexSchema(Schema):  
    __options__ = Options(  
        invalid_items='exclude',  
        invalid_keys='preserve',  
    )  
  
    indexes: List[int]  
    info: Dict[Tuple[int, int], int]  
  
data = {  
    'indexes': ['1', '-2', '*', 3],  
    'info': {  
        '2,3': 6,  
        '3,4': 12,  
        'a,b': '10'  
    }  
}

index = IndexSchema(**data)
# UserWarning: parse item: [2] failed: could not convert string to float: '*'
# UserWarning: parse item: ['a,b<key>'] failed: could not convert string to float: 'a'

print(index)
# > IndexSchema(indexes=[1, -2, 3], info={(2, 3): 6, (3, 4): 12, 'a,b': 10})
```

我们为数据类 IndexSchema 声明的解析选项中指定了 `invalid_items='exclude'`，所以在列表元素中非法的元素将会被剔除，比如输入的 `['1', '-2', '*', 3]` 被转化到了 `[1, -2, 3]`

我们还指定了 `invalid_keys='preserve'`，表示无法完成转化的字典键会得到保留，所以在我们输入的 `'info'` 字段的数据中，能够完成转化的键值进行了转化，无法完成转化的键值也得到了保留

!!! warning
	除非你知道自己在做什么，否则尽量不要使用 `'preserve'` 作为非法处理选项，这样会破坏类型安全的保障

## 字段行为调节

Options 提供了一些用于调节字段的行为的选项，包括

* `ignore_required`：忽略必传参数，也就是将所有的参数都变为可选参数
* `no_default`：忽略默认值，没有提供的参数不会出现在数据中
* `force_default`：强制指定一个默认值
* `defer_default`：强制推迟默认值计算，对应着 Field 配置中的 `defer_default`
* `ignore_constraints`：忽略约束校验，只进行类型转化
* `immutable`：让数据类的全部属性都变得不可变更，即不能赋值与删除

!!! warning
	`no_default`， `defer_default` 与 `immutable`  选项只能用于数据类，不能用于函数

* `ignore_delete_nonexistent`：在数据类中，你可以使用 `del data.attr` 这样的方式去删除数据实例的 `attr` 属性，如果这个属性并不存在（对应的数据键不存在）， 会抛出 `DeleteError`，但你可以通过开启 `ignore_delete_nonexistent=True` 来忽略这种情况，不抛出错误

> 版本 0.6.2 及以上支持

这些选项默认都没有开启，开启这些选项相当于强制给字段的配置值，所以相关的用法可以参考 [Field 字段配置](/zh/references/field)

## 字段别名选项

Options 还提供了一些用于控制字段名称和别名的选项

* `case_insensitive`：是否大小写不敏感地接收参数，默认为 False
* `alias_generator`：指定一个用于为没有指定 `alias` 的字段生成输出别名的函数
* `alias_from_generator`：指定一个用于为没有指定 `alias_from` 的字段生成输入别名的函数
* `ignore_alias_conflicts`：是否忽略输入数据中的别名冲突，默认为 False


### 命名风格转化

不同的编程语言或开发者都可能有着不同的习惯命名风格，所以你提供的 API 函数很可能需要从不同的命名风格中转化

比如在 Python 中一般使用小写和下划线方式命名字段，而如果你的客户端需要接收 camelCase 的数据的话，一般你需要这样声明

```python
from utype import Schema, Field

class ArticleSchema(Schema):
	slug: str
	liked_num: int = Field(alias='likedNum') 
	created_at: str = Field(alias='createdAt')
```


但由于 Options 提供了 `alias_generator` 选项，所以你可以为整个数据类指定一个输出别名的转化函数，如

```python
from utype import Schema
from utype.utils.style import AliasGenerator
from datetime import datetime

class ArticleSchema(Schema):
    __options__ = Schema.Options(
        alias_from_generator=[
            AliasGenerator.kebab,
            AliasGenerator.pascal,
        ],
        alias_generator=AliasGenerator.camel
    )

	slug: str
	liked_num: int
	created_at: datetime

data = {
	'Slug': 'my-article',                # pascal case
	'LikedNum': '3',                     # pascal case
	'created-at': '2022-03-04 10:11:12'  # kebab case
}
article = ArticleSchema(**data)
print(article)

print(dict(article))
# {
#	'slug': 'my-article',
#	'likedNum': 3,
#	'createdAt': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```


utype 为了使得命名风格的转化更加方便，在 `utype.utils.style.AliasGenerator` 中已经提供了一些常用的能够生成各种命名风格字段的别名生成函数

* `camel`：驼峰命名风格，如 `camelCase`
* `pascal`：帕斯卡命名风格，或称首字母大写的驼峰命名，如 `PascalCase`
* `snake`：小写下划线命名风格，Python 等语言的推荐变量命名风格，如 `snake_case`
* `kebab`：小写短横线命名风格，如 `kebab-case`
* `cap_snake`：大写下划线命名风格，常用于常量的命名，如 `CAP_SNAKE_CASE`
* `cap_kebab`：大写短横线命名风格，如 `CAP-KEBAB-CASE`

你只需要使用这些函数指定  `alias_generator` 或 `alias_from_generator` 即可获得对应的命名风格转化能力，如在例子中的解析选项指定的 `alias_from_generator` 为 `[AliasGenerator.kebab, AliasGenerator.pascal]`，表示能够从小写短横线命名风格和首字母大写的驼峰命名风格的输入数据中进行转化，而 `alias_generator=AliasGenerator.camel` 表示会将输出数据转化为驼峰命名风格

所以我们看到例子中的输入数据使用的命名风格都能被正确地识别和接受，完成了对应的类型转化，并输出到了目标的别名
