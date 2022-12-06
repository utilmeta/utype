# 数据类的解析

```python
from utype import Schema, Rule, Field
from datetime import datetime

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"
    
class ArticleSchema(Schema):
	slug: Slug = Field(max_length=30)
	content: str = Field(alias_from=['body', 'text'])
	views: int = Field(ge=0, default=0)
	created_at: datetime = Field(required=False)

print(ArticleSchema(slug='my-article', text=b'my article body'))
#>
```

`<name>: <type> = <field>`

## 声明数据类

 * Schema：继承自 dict 字典类，提供属性读写与字典的所有方法，支持逻辑操作
 * DataClass：没有任何基类，支持逻辑操作

### Schema 类


### DataClass 类


### `@utype.dataclass` 装饰器

Schema 类和 DataClass 类都是 utype 预先定义好的数据类，其中有着一定的行为偏好，如果你需要自己重新生成一个数据类，并能够调控数据类的具体行为，就可以使用 `@utype.dataclass` 装饰器

```python
import utype

@utype.dataclass  
class DataClass:  
    name: str = Field(max_length=10)  
    age: int
```


`@utype.dataclass` 装饰器还可以传入一系列参数用于自定义数据类的生成行为
* `set_properties`
* `init_super`：是否在初始化函数中
* init_attributes
* init_properties
* post_init
* post_setattr
* post_delattr
* repr
* allow_runtime
* parser_cls
* options

!!! note
	 `@utype.dataclass` 装饰器只会对你的类中的某些方法进行调整，并不会影响类的基类或者元类

## 声明数据字段

最简单声明

```python
from utype import Schema

class UserSchema(Schema):
    name: str
    level: int = 0
```

* 仅声明类型
* 声明类型并声明一个值作为字段的默认值

但是一个字段除了类型与默认值外，往往还需要其他行为的配置，这时就需要使用

### Field 字段配置

我们已经在示例中了解过 Field 类的用法了，只需要将 Field 类的实例作为字段的属性值，就可以获得

常用的配置项有

* 可选性与默认值
* 说明与标记
* 约束配置
* 别名配置
* 模式配置
* 输入与输出配置
* 属性行为配置

如果你需要更全面地了解 Field 中的配置参数及用法，可以参考 [Field 字段配置的 API 参考](/zh/references/field)

!!! note
	Field 字段配置只在数据类或函数中声明有效，如果你单独用于声明一个变量，则不会起作用


### `@property` 属性


### 属性访问行为
* 读取
* 更新
* 删除


## 数据类的用法

### 嵌套与复合


### 继承与复用



### 逻辑运算

如果你需要让声明出的数据类支持逻辑运算，则需要手动使用 `utype.LogicalMeta` 作为你的数据类的**元类**，用法如下
```python
import utype

@utype.dataclass  
class LogicalDataClass(metaclass=utype.LogicalMeta):  
    name: str = Field(max_length=10)  
    age: int

one_of_type = LogicalDataClass ^ Tuple[str, int]

print(one_of_type({'name': 'test': 'age': '1'}))
# > LogicalDataClass(name='test', age=1)

print(one_of_type(['test', '1']))
# > ('test', 1)
```



## 数据的解析校验

### 配置解析选项


运行时解析选项

### 自定义 `__init__` 函数

### 整体性校验函数

* `__validate__`
* `__post_init__`
