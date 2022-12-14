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
	username: str = utype.Param(regex='[0-9a-zA-Z]{3,20}'),
	password: str = utype.Param(min_length=6)
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

utype 支持原生的函数语法，也就是说在最简单的情况下，你只需要为你的函数添加一个 `@utype.parse` 装饰器，即可获得解析的能力

```python
import utype

@utype.parse
def add(a: int, b: int) -> int:
	return a + b

print(add('3', 4.1))
# > 7
```

!!! note
	进行函数解析需要你使用 Python 类型注解的语法为参数声明类型，如果你的参数没有声明类型，那它将能够传入任意类型的值


但是使用原生的函数语法仅支持声明参数的类型和默认值，如果你需要更多的参数配置，可以使用 utype 提供 Param 类对函数参数进行配置

### 配置 Param 参数
Param 类可以为函数参数配置丰富的行为，包括默认值，说明，约束，别名，输入行为等，只需要将 Field 类的实例作为函数参数的默认值，就可以获得其中声明的字段配置

下面示例一些常用的配置的用法，我们来编写一个创建用户的函数
```python
import utype
from datetime import datetime
from typing import Optional

@utype.parse  
def create_user(  
    username: str = utype.Param(regex='[0-9a-zA-Z_-]{3,20}', example='alice-01'),  
    password: str = utype.Param(min_length=6, max_length=50),  
    avatar: Optional[str] = utype.Param(
	    None,
        description='avatar url of the new user',  
        alias_from=['picture', 'headImg'],  
    ),  
    signup_time: datetime = utype.Param(  
        no_input=True,  
        default_factory=datetime.now  
    )  
) -> dict:  
    return {  
        'username': username,  
        'password': password,  
        'avatar': avatar,  
        'signup_time': signup_time,  
    }
```

* `username`：用户名参数，声明了 str 字符串类型，在参数配置中使用 `regex` 为字段指定了正则约束，还使用 `example` 参数进行了示例值的说明
* `password`：密码参数，声明了 str 字符串类型，在参数配置中使用 `min_length` 和 `max_length` 指定了最小长度和最大长度的约束
* `avatar`：头像参数，声明了 `Optional[str]`，表示可以传入字符串或者 None，使用了 Param 类的首个参数指定了默认值为 `None`， 并使用 `description` 对字段的格式和用途进行了文档说明，并且使用 `alias_from` 指定了一些可以从中转化的别名，可以用于兼容旧版本参数
* `signup_time`：注册时间参数，声明了 `datetime` 日期类型，在参数配置中配置了 `no_input=True`，表示不接受用户输入，也就是说在调用时会直接填充其使用 `default_factory` 制造的默认值，也就是当前的时间，作为新用户的注册时间

我们来调用一下这个函数，试验一下它的效果

```python
bob = create_user(b'bob_007', 1234567)
print(bob)
# > {'username': 'bob_007', 'password': '1234567', 'avatar': None, 'signup_time': datetime(...)}

from utype import exc

try:
	create_user('@invalid$input', '1234567')
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['username'] failed: Constraint: 
	<regex>: '[0-9a-zA-Z_-]{3,20}' violated
	"""

alice = create_user('alice-001', 'abc1234', headImg='https://fake.avatar', signup_time='ignored')

print(alice)
# {
# 'username': 'alice-001', 
# 'password': 'abc1234', 
# 'avatar': 'https://fake.avatar', 
# 'signup_time': datetime.datetime(...)
# }
```

可以看到
1. 输入数据的类型会被转换为对应函数参数声明的类型
2. 如果输入数据不满足函数参数的约束，则会抛出错误，包含定位信息与失败原因
3. 由于 `avatar` 字段指定的 `alias_from` 参数中包含 `'headImg'`，所以我们使用 `'headImg'` 作为参数名进行传参也能被正确地识别并转化为 `avatar` 参数
4. 由于 `signup_time` 指定了 `no_input=True`，所以即使传入了对应的字段也会进行忽略，并按照 `default_factory` 的配置填入当前时间

!!! note
	Param 类其实是 utype 的 Field 类的子类，只不过对配置选项进行了精简，使得声明函数参数配置更加方便，所以详细的参数与用法可以参考 [Field 字段配置的 API 参考](/zh/references/field)


### 参数声明限制
由于函数的特点，在函数中声明字段配置比在数据类中声明字段多了一定的限制，我们来了解一下

**Python 函数的传参方式**
在介绍字段的声明限制之前，我们先来回顾一下 Python 函数的参数类型与传参方式
```python
def add(a: int, b: int) -> int:
	return a + b

add(1, 2)      # positional
add(a=1, b=2)  # keyword
add(1, b=2)    # mixed
# > 7
```
在 Python 中，可以使用两种方式传递函数参数

* 顺序传递，按照函数参数的声明顺序传递
* 名称传递，按照函数参数的名称传递

不同类别的参数支持的传参方式不同，下面是一个囊括了全部类别参数的示例
```python
def example(  
    # positional only  
    pos_only,  
    /,  
    # positional or keyword  
    pos_or_kw  
    # positional var  
    *args,  
    # keyword only  
    kw_only,  
    # keyword var  
    **kwargs
): pass
```
每类参数的性质为

* `pos_only`：在符号 `/` 前声明的参数，只能使用顺序方式传递
* `pos_or_kw`：默认的参数类别，既可以支持顺序方式传递，也支持名称方式传递
* `*args`：使用顺序传递的变长参数，即超出了声明参数外的顺序参数会被这个参数接收
* `kw_only`：在 `*args` 或者单个 `*` 符号之后的参数只能使用名称方式传递
* `**kwargs`：使用名称传递的变长参数，如果传入的参数名称超出了你声明的范围就会被这个参数接收

接下来我们来介绍具体的参数声明限制，不同类别的参数的限制可能会有所不同

**可选参数的声明限制**
在 Python 函数中，不能将支持顺序方式传递的必传参数声明在可选参数后面，如

```python
try:
	 def bad(opt: int = 0, req: str):
		 pass
except SyntaxError:
	print(e)
	"""
	non-default argument follows default argument
	"""
```

而在 utype 中，由于使用 Param 配置作为默认值的参数也可能是必传参数，所以也有着这样的限制，如以下就是一个不合适的声明

```python
import utype

@utype.parse
def bad_example(opt: int = utype.Param(None), req: str = utype.Param()):
	pass

# UserWarning: non-default argument: 'req' follows default argument: 'opt'
```

也就是说，如果参数支持以顺序的方式传递，那么就不要在可选参数的后面声明必传参数，这样会使得可选参数失去意义
如果这样的参数能够支持以键值方式传递，那么 utype 仅会进行警告，但如果这样的参数只支持顺序传递，就会直接抛出错误，如
```python
import utype

try:
	@utype.parse
	def error_example(
		opt: int = utype.Param(None), 
		req: str = utype.Param(), /
	):
		pass
except SyntaxError:
	print(e)
	"""
	non-default argument: 'req' follows default argument: 'opt'
	"""
```

但是，如果你的参数是仅支持名称传递的，就可以进行这样的声明，如
```python
import utype

@utype.parse
def ok_example(
	*,
	opt: int = utype.Param(None), 
	req: str = utype.Param(),
):
	pass
```


**受限的 Param 配置**
由于函数参数必须传入一个有意义的值（无论是输入值还是默认值），所以 Param 配置中的一些参数的使用是受到限制的，如果使用它们则必须指定 `default`  /  `default_factory`

* `required=False`
* 使用 `no_input`
* 使用 `mode` / `readonly` / `writeonly`

**某些条件下无效的 Param 配置**
对只支持顺序传入的参数中，有一些参数是无效的，如

* `alias_from`
* `case_insensitive`

因为这些都是在对参数支持的名称起作用

### `*args` 与 `**kwargs`

在 Python 函数中，类似 `*args` 与 `**kwargs` 的参数分别表示的是顺序变长参数和键值变长参数
utype 中的解析函数也支持位 `*args` 或 `**kwargs` 中的值声明类型，并正确识别并完成解析，如

```python
from utype import Rule, parse, exc
from typing import Dict

class Index(int, Rule):  
    ge = 0

@parse  
def call(*series: int, **mapping: Index | None) -> Dict[str, int]:  
    result = {}  
    for key, val in mapping.items():  
        if val is not None and val < len(series):  
            result[key] = series[val]  
    return result

mp = {  
    'k1': 1,  
    'k2': None,  
    'k3': '0'  
}
res = call(-1.1, '3', 4, **mp)

print(res)
# > {'k1': 3, 'k3': -1}

try:
	call('a', 'b')
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['*series:0'] failed: could not convert string to float: 'a'
	"""

try:
	call(1, 2, key=-3)
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['**mapping:key'] failed: Constraint: <ge>: 0 violated;
	"""
```


默认情况下，顺序变长参数（`*args`）会收到一个元素类型未知的元组（`tuple`），当你对它使用类型声明时，就会得到一个元素都是该类型的元组（即 `Tuple[<type>, ...]`），如例子中 `series` 参数会得到一个元素为整数 int 的元组
而键值变长参数（`**kwargs`）默认会收到一个键为字符串类型，值类型未知的字典（`Dict[str, Any]`），如果对它使用类型声明，将会得到值类型固定的字典（`Dict[str, <type>]`），如例子中 `mapping` 参数会得到一个值为大于等于零的整数或 None 的字典

而且在例子中我们看到，当传入的变长参数无法完成对应的类型转化时，会抛出解析错误，其中包含具体的定位信息和失败原因等


### 私有参数

在函数参数中，以下划线开头的函数参数称为私有参数，私有参数的特征是

* 不参与函数解析
* 不能被以键值方式传参
* 不会出现在函数生成的 API 文档中（对客户端不可见）

这种情况常用于
* 当函数提供外部进行调用，如被 HTTP / RPC 客户端调用时，往往需要客户端指明参数的名称进行传入，所以私有参数做到了对外不可见，而且页无法以名称方式传入
* 函数在内部代码中调用时，可以直接进行顺序传参，此时可以传入私有参数

例如 
```python
import utype

@utype.parse
def fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1):  
    if not n:  
	    return _current  
    else:  
        return fib(n - 1, _next, _current + _next)

print(fib('10'))
# > 55
print(fib('10', _current=5, _next=8))
# > 55

print(fib('10', 5, 8))
# > 610
```

可以看到，以名称方式传入的私有参数会被忽略，但是以顺序参数方式传入的私有参数会被接受和处理

如果你需要让私有参数彻底无法传入，可以将其声明成只允许名称方式传参
```python
import utype
from datetime import datetime

@utype.parse
def get_info(
	id: int, *, 
	_ts: float = utype.Param(default_factory=lambda :datetime.now().timestamp())
):
	pass
	
```

!!! note
	这样的效果其实与声明 `no_input=True` 配置相同

**获取原函数**
对于使用 `@utype.parse` 装饰的解析函数，如果你确实需要在代码中传入私有参数或者 `no_input=True` 的参数，虽然直接调用函数无法完成，但是可以通过 `utype.raw` 获取解析函数的原函数，如

```python
import utype
from datetime import datetime

@utype.parse
def get_info(
	id: int, *, 
	_ts: float = utype.Param(default_factory=lambda :datetime.now().timestamp())
):
	return id, _ts

raw_get_info = utype.raw(get_info)

print(raw_get_info('1', None))
# > ('1', None)
```

!!! warning
	原函数就是在你的 `@utype.parse` 下声明的 Python 函数，直接调用原函数不会应用 utype 中的任何功能，所以不提供任何类型安全保障，请谨慎使用这个特性


## 解析函数返回值
utype 不仅可以对函数的参数进行解析，也能够将函数的返回值解析到声明的类型

函数的返回值声明的语法都是 `def (...) -> <type>: pass`，其中 `<type>`  是你为返回值指定的类型，这个类型可以是任意的普通类型，嵌套类型，逻辑类型，数据类等

但不同种类的函数对于返回值的声明方式可能有所不同，下面将分别讨论 Python 中的每种函数的返回值声明方式

### 普通函数

为普通的函数声明返回值只需要使用对应的类型直接进行提示即可，如
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
```

在例子中我们使用 ArticleSchema 数据类作为函数 `get_article` 的返回类型提示，utype 会自动将函数的返回值转化为一个 ArticleSchema 的实例，用法如下

```python
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

可以看到，无论是参数无法完成转化，还是返回结果无法完成转化，都会抛出错误

### 异步函数
utype 同样支持异步函数的类型解析，声明的方式与同步函数一致，我们来通过一段异步的 HTTP 客户端代码来示例

```python
import aiohttp  
import asyncio  
from typing import Dict  
import utype  
  
@utype.parse  
async def fetch(url: str) -> str:  
    async with aiohttp.ClientSession() as session:  
        async with session.get(url) as response:  
            return await response.text()  

@utype.parse  
async def fetch_urls(*urls: str) -> Dict[str, dict]:  
    result = {}  
    tasks = []  
  
    async def task(loc):  
        result[loc] = await fetch(loc)  
  
    for url in urls:  
        tasks.append(asyncio.create_task(task(url)))  
  
    await asyncio.gather(*tasks)  
    return result  

async def main():  
    urls = [  
        'https://httpbin.org/get?k1=v1',  
        'https://httpbin.org/get?k1=v1&k2=v2',  
        'https://httpbin.org/get',  
    ]  
    result_map = await fetch_urls(*urls)  
    for url, res in result_map.items():  
        print(url, ': query =', res['args'])  
        # https://httpbin.org/get?k1=v1 : query = {'k1': 'v1'}
		# https://httpbin.org/get?k1=v1&k2=v2 : query = {'k1': 'v1', 'k2': 'v2'}
		# https://httpbin.org/get : query = {}
  
if __name__ == "__main__":  
    loop = asyncio.get_event_loop()  
    loop.run_until_complete(main())  
    # asyncio.run(main())
```

在例子中我们使用了 `aiohttp` 库进行异步的 HTTP 请求，使用 `fetch_urls` 将几个异步的请求任务进行聚合，避免了网络 I/O 的阻塞

我们请求的 `'https://httpbin.org/get'` 接口会返回 JSON 形式的请求的参数信息，在 `fetch()` 函数中，我们仅将结果转化为了字符串，但在 `fetch_urls()` 函数中，我们使用 `Dict[str, dict]` 来注解结果类型，会使得响应中的 JSON 字符串完成对 Python 字典的转化，最终我们可以直接使用键值访问对应的元素进行输出

也就是说无论是同步函数还是异步函数，使用 `@utype.parse` + 类型声明都能保障函数调用的类型安全

### 生成器函数

```python
import utype  
from typing import Tuple, Generator

csv_file = """  
1,3,5  
2,4,6  
3,5,7  
"""  

@utype.parse  
def read_csv(file: str) -> Generator[Tuple[int, ...], None, int]:
	lines = 0
    for line in file.splitlines():  
        if line.strip():  
            yield line.strip().split(',')
            lines += 1
	return lines

csv_gen = read_csv(csv_file)
print(next(csv_gen))
# > (1, 3, 5)
print(next(csv_gen))
# > (2, 4, 6)
print(next(csv_gen))
# > (3, 5, 7)

try:
	next(csv_gen)
except StopIteration as e:
	print(f'total lines: {e.value}')
	# total lines: 3
```

一般的生成器使用 `Generator` 类型进行返回注解，其中需要传入三个顺序参数
* `yield value` 中值 `value` 的类型，即迭代的元素类型
* `generator.send(value)` 中值 `value` 的类型，即发送的数据类型，如果不支持数据发送，则传入 None
* `return value`  中值 `value` 的类型，即返回的数据类型，如果没有返回值，则传入 None

但对于常用的生成器函数，可能只进行 `yield` ，这时可以

* `Iterator`
* `Iterable`

其中只需要传入一个参数，就是 `yield` 出的值的类型

#### 生成器发送值

生成器不仅可以接受 `yield` 迭代出的值，还可以使用 `send()` 方法向生成器中发送值，你可以使用 Generator 类型中的第二个参数约定  `send()` 方法传递的值的类型，如

```python
import utype  
from typing import Generator

@utype.parse  
def echo_round() -> Generator[int, float, int]:  
    cnt = 0  
    sent = 0  
    while True:  
        sent = yield round(sent)  
        if not sent:  
            break  
        cnt += 1  
    return cnt  
  
echo = echo_round()  
next(echo)  

print(echo.send('12.1'))
# > 12
print(echo.send(b'0.05'))
# > 0
print(echo.send(3.9))
# > 4

try:  
    next(echo)  
except StopIteration as e: 
	print(f'echo count: {e.value}')
    # echo count: 3
```

我们在例子中声明了一个支持发送值的 `echo_round`，能够对发送的值得出其四舍五入的结果，同时函数中记录了发送的次数 `cnt`，并作为结果返回

我们为 `send()` 发送值指定的类型为 `float`，所以发送的数据都会被转化为 float 类型，在函数中用于接收的 `sent` 变量得到的就是一个浮点数，可以直接进行后续操作

我们通过在生成器结束迭代后抛出 StopIteration 错误实例的 value 属性接收生成器的返回值

#### 尾递归优化

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

对于使用 `@utype.parse` 装饰的函数，当 utype 识别到迭代器 yield 出的仍然是一个生成器时，会继续迭代执行，直到得到结果，所以上面例子中的写法就可以简化为 

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

utype 不仅支持解析普通函数，还支持生成器函数，异步函数和异步生成器函数，它们的用法都是一致的，只需要正确地声明对应的类型注解
```python
import utype  
import asyncio  
from typing import AsyncGenerator  

@utype.parse  
async def waiter(rounds: int = utype.Param(gt=0)) -> AsyncGenerator[int, float]:  
    assert isinstance(rounds, int)  
    i = rounds  
    while i:  
        wait = yield str(i)  
        if wait:  
            assert isinstance(wait, float)  
            print(f'sleep for: {wait} seconds')
            await asyncio.sleep(wait)  
        i -= 1  
  
async def wait():  
    wait_gen = waiter('2')  
    async for index in wait_gen:  
        assert isinstance(index, int)  
        try:  
            await wait_gen.asend(b'0.5')  
            # sleep for: 0.5 seconds  
        except StopAsyncIteration:  
            return  
  
if __name__ == '__main__':  
    asyncio.run(wait())
```

异步生成器的返回值需要使用 `AsyncGenerator` 类型用注解，其中有两个参数

* `yield value` 中的 `value` 值的类型
* `generator.asend(value)` 发送的 `value` 值的类型

如果你的异步生成器不需要接受 `asend()` 数据，可以直接使用

* `AsyncIterable`
* `AsyncIterator`

其中只需要传入一个类型，就是异步生成器 `yield` 出的值的类型

!!! note
	在 Python 中，异步生成器不支持返回值

可以看到，虽然我们在传参和 `yield` 中使用了字符等类型，它们全部都按照声明转化为了期望的数字类型（当然在无法完成转化时会抛出错误）


## 配置函数解析

你可以在 `@utype.parse` 装饰器的参数中转入一些参数来控制函数的解析

* `ignore_params`：是否忽略对函数参数的解析，默认为 False，如果开启，则 utype 不会对函数参数进行类型转化与约束校验
* `ignore_result`：是否忽略对函数结果的解析，默认为 False，如果开启，则 utype 不会对函数结果进行类型转化与约束校验
* `options`：传入一个解析选项来调控解析行为，具体用法可以参考 [Options 解析配置](../references/options)
* `parser_cls`：传入你自定义的解析类，默认是 `utype.parser.FunctionParser`，你可以通过继承和扩展它来实现你自定义的函数解析功能

## 在类中的应用


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

在参数中使用嵌套类型

```python
import utype  
from typing import List, Dict

class Slug(str, utype.Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"  
  
class ArticleQuery(utype.Schema):  
    id: int  
    slug: Slug = utype.Param(max_length=30)  
  
class ArticleInfo(ArticleQuery):  
    likes: Dict[str, int]  
  
@utype.parse  
def get_article_info(  
    query: ArticleQuery,  
    body: List[Dict[str, int]] = utype.Param(default_factory=list)  
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


### 运行时解析配置

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

而  `@utype.dataclass` 的作用是生成类中关键的内部方法（如 `__init__`，`__repr__`，`__eq__` 等），以及为类的属性（包括普通属性和 `@property` 属性）提供类型解析能力

所以 `@utype.parse`  和 `@utype.dataclass` 是相互独立的，也可以同时使用

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


