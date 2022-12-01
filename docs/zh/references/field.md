# Field 字段配置

## 可选与默认值




## 说明与标记


* title
* description
* example


## 约束配置

Field 中也支持使用参数方式来为类型配置约束，一般用于基本类型

!!! note
	如果你声明的约束需要被多个字段复用，那么建议使用继承 Rule 的方法声明类型约束，否则可用使用 Field 来声明 

Field 中的约束参数与 Rule 中的内置约束相同

!!! note
	事实上，utype 会根据你的类型声明和 Field 中的约束声明生成一个对应的 Rule 类作为这个字段的输入校验类型


## 别名配置

* alias
* alias_from
* case_insensitive

!!! note
	如果你的别名配置是针对整个数据类的，可以使用  Options 进行统一声明，具体用法可以参考 [Options 的别名配置](./options)



## 模式配置


具体模式的定义取决于你的使用场景，比如
* 读模式：将数据表中的数据通过 SQL 读取出来并转化为 Schema 实例进行返回
* 写模式：将 HTTP 请求体中的数据转化为 Schema 实例并对目标资源进行更新

如果你需要只声明一个数据类，但能够对不同的模式

* `mode`
* `readonly`：是 `mode='r'` 的一个常用简化表示
* `writeonly`：是 `mode='w'` 的一个常用简化表示

readonly, writeonly 与 mode 间只能指定一个参数

```python
from utype import Schema, Field
from datetime import datetime

class UserSchema(Schema):
	username: str
	email: str = Field(mode='rw')
	password: str = Field(writeonly=True)
	signup_time: datetime = Field(readonly=True)
```

```python
class UserRead(UserSchema):
	__mode__ = 'r'

class UserWrite(UserSchema):
	__mode__ = 'w'
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

utype 支持按照不同的模式输出 json-schema 文档，


## 输入与输出


### 属性字段

使用 `@property` 可以定义更加原生的输入输出字段


## 属性配置

* `unprovided`：当属性对应的字段没有在数据中提供时（也没有默认值），访问属性得到的值，当没有设置时访问属性会抛出 AttributeError

* `immutable`：该属性是否是不可变的，如果开启，则你无法对数据实例的该属性进行赋值或删除操作

!!! note
	严格意义上，在 Python 中，你无法让实例的属性彻底无法变更，如果开发者执意要做，可以通过操作 `__dict__` 等方法来变更属性，`immutable` 参数实际上承担着一种标记和提示的作用，提醒开发者这个字段是不应该被变更的



!!! warning
	属性配置仅在数据类中使用，在函数参数中声明没有意义


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

