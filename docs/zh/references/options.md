# Options 解析选项


## 类型转化选项

* `transformer_cls`
* `no_explicit_cast`
* `no_data_loss`
* `unresolved_types`

## 数据处理选项

* `addition`


* `max_depth`：限制数据嵌套的最大深度

这个参数主要用于限制自引用或循环引用的数据结构，避免出现递归栈溢出

* `max_params`
* `min_params`

**与长度约束的区别**

虽然使用 Rule 约束参数的  `max_length` 和 `min_length` 也能够约束字典的长度，但是它们与 `max_params` / `min_params` 在作用上是有区别的

`max_params` / `min_params` 是在所有的字段解析开始之前对输入数据进行的校验，其中 `max_params` 是为了避免输入数据过大而耗费解析资源

而  `max_length` / `min_length` 在作用于数据类中，是用于在所有字段解析结束后，用于限制 **输出** 的数据的长度

并且 `max_params` / `min_params` 可以用于限制函数参数的输入， `max_length` / `min_length` 只能限制普通类型和数据类

## 错误处理

* `collect_errors`
* `max_errors`

### 非法数据处理

* `invalid_items`
* `invalid_keys`
* `invalid_values`

## 解析行为调节

* `ignore_required`
* `no_default`
* `force_default`
* `defer_default`
* `ignore_constraints`


## 字段生成选项

* `case_insensitive`
* `alias_generator`
* `alias_from_generator`

* `ignore_alias_conflicts`


### 命名风格转化

不同的编程语言或开发者都可能有着不同的习惯命名风格，而如果你需要提供

比如在 Python 中一般使用小写和下划线方式命名字段，

```python
class Article:
	liked_num: int = Field(alias='likedNum') 
	created_at: str = Field(alias='createdAt')
```

在 `utype.utils.style.AliasGenerator` 中 提供了一些常用的能够生成各种命名风格字段的别名生成函数

* `camel`：驼峰命名风格，如 `camelCase`
* `pascal`：帕斯卡命名风格，或称首字母大写的驼峰命名，如 `PascalCase`
* `snake`：小写下划线命名风格，python 等语言的推荐变量命名风格，如 `snake_case`
* `kebab`：小写短横线命名风格，如 `kebab-case`
* `cap_snake`：大写下划线命名风格，常用于常量的命名，如 `CAP_SNAKE_CASE`
* `cap_kebab`：大写短横线命名风格，如 `CAP-KEBAB-CASE`

```python
from utype.utils.style import AliasGenerator

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

你可以灵活运用别名转化函数来接受不同命名风格的参数字段，并转化为统一的命名风格

### 用于函数



## 属性控制
* `secret_names`
* `immutable`

在 Options 选项中有一个 `secret_names` 选项，默认将一些常用的密钥和密码字段名称
* `'password'`
* `'secret'`
* `'dsn'`
* `'private_key'
* `'session_key'
* `'pwd'
* `'passphrase'

如果你的字段使用 `secret_names` 中的名称命名，且没有自定义 `repr` 参数，则会自动使用 `'******'` 来表示对应的名称




## 运行时

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
