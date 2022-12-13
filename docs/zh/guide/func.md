# 函数的解析

由于目前 Python 没有在运行时解析类型与校验约束的机制，所以当我们编写一个函数时，往往需要先对参数进行类型断言，约束校验等操作，然后才能开始编写真正的逻辑，否则很可能会在运行时发生异常错误，如
```python
def login(username, password):  
    import re  
    if not isinstance(username, str) \  
            or not re.match('[0-9a-zA-Z]{3,20}', username):  
        raise ValueError('Bad username')  
    if not isinstance(password, str) \  
            or len(password) < 6:  
        raise ValueError('Bad password')  
    # 下面才是你真正的处理逻辑
```

所以 utype 提供了函数解析的机制，你只需要把函数参数的类型，约束和配置声明出来，然后使用 `@utype.parse` 装饰器，就可以在函数中拿到类型安全，约束保障的参数值了，如
```python
import utype

@utype.parse
def login(
	username: str = utype.Field(regex='[0-9a-zA-Z]{3,20}'),
	password: str = utype.Field(min_length=6)
):
	# 你可以直接开始编写逻辑了
	return username, password

print(login(b'alice', 123456))
('alice', '123456')

try:
	login('@invalid', 123456)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: 
	Constraint: <regex>: '[0-9a-zA-Z]{3,20}' violated
	"""
```

可以看到，utype 会自动完成参数的类型转化，对于无法完成类型转化或不满足约束条件的输入值，utype 会抛出一个清晰的错误，包含着数据中的定位信息和出错原因

所以本篇文档我们来详细介绍解析函数的声明和用法

## 声明函数参数

utype 支持原生的函数语法，也就是说在最简单的情况下，你只需要声明

```python
import utype

@utype.parse
def add(a: int, b: int) -> int:
	return a + b

print(add('3', 4.1))
# > 7
```

如果你的参数没有声明类型与默认值，它将能够传入任意类型的值

函数参数的类型声明语法与普通变量的类型声明语法相同，都支持普通类型，嵌套类型，特殊

### 传参方式

* position only
* position var
* position or keyword
* keyword only
* keyword var


### 配置 Field

**可选参数的声明限制**
Python 已经限制了


**无效的 Field 参数**

* `no_output`
* `immutable`
* `repr`

* `defer_default`：无法在函数参数中开启这个配置，否则会抛出错误，因为它会阻止默认值在解析时的计算

**模式参数**


**在函数参数中使用模式配置**
相较于在数据类中使用模式字段，在函数参数使用模式配置并不是很常见，

```python
@utype.parse
def feed_user(  
    username: str,  
    password: str = Field(mode='wa', default=None),  
    followers_num: int = Field(readonly=True, default=None),  # or mode='r'  
    signup_time: datetime = Field(  
        mode='ra',  
        default_factory=datetime.now  
    ),  
    __options__: Options = Options(mode='w')
):  
    return locals()
```


* `readonly`
* `writeonly`
* `mode`
因为在函数中指定任何模式参数都需要参数指定默认值（`default`  /  `default_factory`），指定了模式意味着函数参数在某些模式下无法输入


有限制的参数

* `required=False`：必须指定 default
* `no_input=True`：必须指定 default

### 私有参数

以下划线开头的函数参数称为私有参数，私有参数的特征是

* 不参与函数解析
* 不能被以键值方式传参
* 不会出现在函数生成的 API 文档中





```python
import utype
from typing import Optional

class PositiveInt(int, utype.Rule):  
    gt = 0

class ArticleSchema(utype.Schema):
	id: Optional[PositiveInt]
	title: str = Field(max_length=100)
	slug: str = Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")

@utype.parse
def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
	return {
		'id': id,
		'title': title,
		'slug': '-'.join([''.join(
			filter(str.isalnum, v)) for v in title.split()]).lower()
	}

print(get_article('3', title=b'My Awesome Article!'))
#> ArticleSchema(id=3, title='My Awesome Article!', slug='my-awesome-article')

try:
	get_article('-1')
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['id'] failed: Constraint: <gt>: 0 violated
	"""

try:
	get_article(title='*' * 101)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['<return>'] failed: 
	parse item: ['title'] failed: 
	Constraint: <max_length>: 100 violated
	"""
```


!!! note
	虽然按照类型的声明，我们不应该在代码中这样调用函数，但是如果调用函数的是来自网络的 HTTP 请求，就可能会出现例子中的情况



## 配置函数解析

你可以在 `@utype.parse` 装饰器的参数中转入一些参数来控制函数的解析

* `ignore_params`：是否忽略对函数参数的解析，默认为 False，如果开启，则 utype 不会对函数参数进行类型转化与约束校验
* `ignore_result`：是否忽略对函数结果的解析，默认为 False，如果开启，则 utype 不会对函数结果进行类型转化与约束校验
* `options`：传入一个解析选项来调控解析行为，具体用法可以参考 [Options 解析配置](../references/options)
* `parser_cls`：传入你自定义的解析类，默认是 `utype.parser.FunctionParser`，你可以通过继承和扩展它来实现你自定义的函数解析功能

## 使用场景

### 初始化数据类

```python
import utype
  
class PowerSchema(utype.Schema):  
    result: float  
    num: float  
    exp: float  
  
@utype.parse  
def get_power(num: float, exp: float) -> PowerSchema:  
    if num < 0:  
        if 1 > exp > -1 and exp != 0:  
            raise exc.ParseError(f'operation not supported, '  
                                 f'complex result will be generated')  
    return PowerSchema(  
        num=num,  
        exp=exp,  
        result=num ** exp  
    )  
      
power = get_power('3', 3)
```

这种方式比为数据类自定义 `__init__` 函数还要灵活，因为可以声明多种不同的初始化参数与逻辑


```python
import utype  
from typing import List, Dict

class Slug(str, utype.Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"  
  
class ArticleQuery(utype.Schema):  
    id: int  
    slug: Slug = utype.Field(max_length=30)  
  
class ArticleInfo(ArticleQuery):  
    likes: Dict[str, int]  
  
@utype.parse  
def get_article_info(  
    query: ArticleQuery,  
    body: List[Dict[str, int]] = utype.Field(default=list)  
) -> ArticleInfo:  
    likes = {}  
    for item in body:  
        likes.update(item)  
    return {  
        'id': query.id,  
        'slug': query.slug,  
        'likes': likes  
    }

article = get_article_info(
	query='id=1&slug=my-article', 
	body=b'[{"alice": 1}, {"bob": 2}]'
)

print(article)
# > ArticleInfo(id=1, slug='my-article', info={'alice': 1, 'bob': 2})
```

### 装饰 `__init__` 函数

在 utype 中，数据类默认拥有着解析初始化数据的能力，但即使你不将类声明为数据类，也可以单独使用 `@utype.parse` 装饰类的 `__init__` 函数，从而获得解析初始化参数的能力


### `with` 与 `__enter__` 函数

* `with`
* `async with`

### `@classmethod`
TODO

!!! note
	对于 `@classmethod` 函数， `@utype.parse` 与 `@classmethod` 的关系无关紧要，你可以将它放在  `@classmethod` 的上方或下方，utype 都能够处理好

### `@staticmethod`
TODO


你需要避免在 `@staticmethod`

```python
class Object:
	@staticmethod  
	@utype.parse  
	def bad_example(param, value: int = 0):  
	    return param
```

这是因为， `@utype.parse` 收到的函数的特征与普通的实例方法函数的特征是相同的

（实际上也不会造成影响，这个参数照样能传参，而且因为没有类型与默认值声明，所以丝毫不会影响解析

### `@property`
TODO


### 直接应用到类

比起在类的函数中一个个添加 `@utype.parse`，它还可以直接左右到类中

 `@utype.parse` 装饰类的效果是：
将类中的非保留函数（名称不以下划线开头的函数）全部变成解析函数

**注意**：`@utype.parse`  和 `@utype.dataclass` 都可以作用于类，但是它们的作用是不同的， `@utype.parse`  会将类中的所有外部方法（不以下划线开头的函数）变成解析函数

而  `@utype.dataclass` 的作用是生成类中关键的内部方法（如 `__init__`，`__repr__`，`__eq__` 等）

所以 `@utype.parse`  和 `@utype.dataclass` 是相互独立的，可以同时使用

```python
@utype.parse  
@utype.dataclass  
class Data:  
    @classmethod  
    def operation(cls):  
        return cls.generate(param='3')  
  
    @staticmethod  
    def generate(param: int = Field(ge=0)):  
        return param  
  
    @utype.parse  
    def __call__(self, *args, **kwargs):  
        return self, args, kwargs
```


!!! note
	虽然 `@utype.parse` 施加在类上时不会应用以下划线开头命名的内部方法，但你可以手动为以下划线开头命名的方法装饰


对于类来说， `@utype.parse`  不会影响基类中的方法

**适用场景**

由于使用 `@utype.parse` ，

既然 utype 完成了额外的解析转化工作，那么肯定会造成轻微的调用延时，对于单次调用这样的延时可以忽略，但如果你需要高频地调用一个内部函数，

所以 utype 函数更适合用于入口函数，即面向用户的 API 或函数，对于传参较为稳定，调用频繁的内部函数，则一般不需要使用 utype 的解析语法

并且 utype 页提供了一个 `utype.raw` 方法，可以用于获取原始函数，所以如果你能够保障

也就是说，使用 utype 的入口函数可以为你的类库或者 API 保守好类型安全的大门，但没有必要在内部的每个函数中

如果你的内部函数调用来自 utype 入口函数，那么


所以如果你对整个类使用的话，那么类的内部函数建议使用下划线开头的命名，这样会跳过 `@utype.parse` 的应用




## 异步函数与生成器

### 异步函数


### 生成器函数

* Generator
* Iterator
* Iterable


**尾递归优化**
生成器函数的另一种用法是帮助 Python 解决尾递归优化问题

Python 普通函数并不支持 “尾递归” 的编写方式，所以当函数递归超过一定限制时（默认在 1000 次左右）就会抛出 `RecursiveError` 错误

但 Python 的生成器函数能够完成这样的优化，比如

```python
def fib(n: int = Field(ge=0), _current: int = 0, _next: int = 1):  
    if not n:  
        yield _current  
    else:  
        yield fib(n - 1, _next, _current + _next)

res = fib(2000)
while hasattr(res, '__next__'):
	res = next(res)

print(res % 100007)
# > 57937
```

使用 `@utype.parse` 装饰器，并且声明

当 utype 识别到迭代器 yield 出的仍然是一个生成器时，会继续迭代执行，直到得到结果，所以上面例子中的写法就可以简化为 

```python
import utype

@utype.parse
def fib(n: int = Field(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
    if not n:  
        yield _current  
    else:  
        yield fib(n - 1, _next, _current + _next)

res = next(fib('100'))

print(res)
# > 354224848179261915075
```

可以看到，对于尾递归优化的生成器，我们可以直接使用一个 `next()` 得到结果，但是你会发现，如果调用的次数超过 1000 次还是会爆栈抛出错误，这是为什么呢？

```python
try:
	next(fib(2000))
except Exception as e:
	print(e)
	"""
	parse item: ['n'] failed:
	maximum recursion depth exceeded while calling a Python object
	"""
```

因为我们在递归调用的时候，用的是装饰后的 `fib` 函数，每次递归都会在 utype 中进行参数解析，所以仍然会发生爆栈。
但由于我们在首次调用完成解析后，已经能够保障调用的类型安全了，所以我们可以直接使用 `fib` 的原函数进行调用了，我们可以通过 `utype.raw` 方法获取解析函数的原函数，优化后的代码如下

```python
import utype

@utype.parse
def fib(n: int = Field(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
    if not n:  
        yield _current  
    else:  
        yield utype.raw(fib)(n - 1, _next, _current + _next)

res = next(fib('100'))

print(res)
# > 354224848179261915075

res = next(fib(b'2000'))
print(res % 100007)
# > 57937
```

这样既保障了调用的类型安全，也可以获得与尾递归生成器的优化，还优化了多次调用的性能


### 异步生成器函数
