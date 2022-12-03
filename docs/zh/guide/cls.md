# 解析数据类
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

## 数据类的用法

 * Schema：继承自 dict 字典类，提供属性读写与字典的所有方法，支持逻辑操作
 * DataClass：没有任何基类，支持逻辑操作


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


## 自定义 `__init__` 函数


## 自定义数据类

