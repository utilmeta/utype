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

你不仅可以在函数中使用基本类型，还可以使用 utype 中的约束类型，嵌套类型，逻辑类型，数据类等进行类型注解，utype 都能够正确识别并完成解析

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
    body: List[Dict[str, int]] = None
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

但是使用原生的函数语仅支持声明参数的类型和默认值，如果你需要更多的参数配置，可以使用 utype 提供 Param 类对函数参数进行配置

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
    pos_or_kw,
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

如果你需要让私有参数彻底无法传入，可以将其声明成只允许名称方式传参，如
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

函数的返回值声明的语法都是 `def (...) -> <type>:`，其中 `<type>`  是你为返回值指定的类型，这个类型可以是任意的普通类型，约束类型，嵌套类型，逻辑类型，数据类等

但不同种类的函数对于返回值的声明方式可能有所不同，下面将分别讨论 Python 中的每种函数的返回值声明方式

### 普通函数

为普通的函数声明返回值只需要使用对应的类型直接进行注解即可，如
```python
import utype
from typing import Optional

class PositiveInt(int, utype.Rule):  
    gt = 0

class ArticleSchema(utype.Schema):
	id: Optional[PositiveInt]
	title: str = utype.Field(max_length=100)
	slug: str = utype.Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")

@utype.parse
def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
	return {
		'id': id,
		'title': title,
		'slug': '-'.join([''.join(
			filter(str.isalnum, v)) for v in title.split()]).lower()
	}
```

在例子中我们使用 ArticleSchema 数据类作为函数 `get_article` 的返回类型提示，utype 会自动将函数的返回值转化为一个 ArticleSchema 的实例，比如

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

utype 同样支持使用 `yield` 的生成器函数，使用生成器能够暂存函数的执行状态，优化内存使用，并且实现很多普通函数无法实现的机制，如构造无限循环列表等，我们先来使用一个例子看一下生成器函数的返回值声明方式

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

在这个例子中我们读取了一个字符串格式的 csv 文件，按照行分割，并将 `split(',')` 后的结果迭代出来，我们知道字符串的 `split` 方法会返回一个字符串列表，但由于我们的返回类型声明，当使用 `next(csv_gen)` 进行迭代时会直接得到一个整数元组，这就是 utype 按照你的声明完成的转化

一般的生成器使用 `Generator` 类型进行返回注解，其中需要传入三个顺序参数
1. `yield value` 中值 `value` 的类型，即迭代的元素类型
2. `generator.send(value)` 中值 `value` 的类型，即发送的数据类型，如果不支持数据发送，则传入 None
3. `return value`  中值 `value` 的类型，即返回的数据类型，如果没有返回值，则传入 None

对于生成器函数的 `return` 返回值，我们通过在生成器结束迭代后抛出 StopIteration 错误实例的 `value` 属性进行获取，因为 `read_csv` 函数会把读取的行数返回，所以上面的例子中我们使用 `int` 类型作为生成器函数的返回类型


但对于常用的生成器函数，我们可能只需要 `yield` 出结果，并不需要支持外部发送或者返回值，此时可以使用以下类型作为返回提示

* `Iterator[<type>]`
* `Iterable[<type>]`

其中只需要传入一个参数，就是 `yield` 出的值的类型，比如

```python
import utype
from typing import Tuple, Iterator

@utype.parse
def split_iterator(*args: str) -> Iterator[Tuple[int, int]]:
	for arg in args:
		yield arg.split(',')

params = ['1,2', '-1,3', 'a,b']

iterator = split_iterator(*params)
while True:
	try:
		print(next(iterator))
		# > (1, 2)
		# > (-1, 3)
	except StopIteration:
		break
	except utype.exc.ParseError as e:
		print(e)
		"""
		parse item: ['<generator.yield[2]>'] failed: 
		could not convert string to float: 'a'
		"""
```

在这个例子中，我们把一个字符串列表中的每个元素使用 `split(',')` 分割，并将结果 `yield` 出来，不需要返回值，所以我们使用了 `Iterator[Tuple[int, int]]` 的类型声明，表示  `yield`  出的值的类型是一个整数二元组，而当数据无法完成对应转化时，我们可以使用  `exc.ParseError` 来接收错误，其中会包含定位的信息，精确到生成器中的迭代索引

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


#### 尾递归优化

生成器函数的另一种用法是帮助 Python 解决尾递归优化问题，比如
```python
def fib(n: int, _current: int = 0, _next: int = 1):  
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

!!! note
	Python 普通函数并不支持 “尾递归” 的编写方式，所以当函数递归超过一定限制时（默认在 1000 次左右）就会抛出 `RecursiveError` 错误，但使用尾递归的生成器能够避免这个问题

如果你的尾递归生成器使用 `@utype.parse` 装饰，可以通过声明最终的返回类型来对调用进行简化，当 utype 识别到迭代器 yield 出的仍然是一个生成器时，会继续迭代执行，直到得到结果，所以上面例子中的写法就可以简化为 

```python
import utype
from typing import Iterator

@utype.parse
def fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
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

因为我们在递归调用的时候，用的是装饰后的 `fib` 函数，每次递归都会在 utype 中进行参数解析，所以仍然会发生爆栈
但由于我们在首次调用完成解析后，已经能够保障调用的类型安全了，所以我们可以直接使用 `fib` 的原函数进行调用了，我们可以通过 `utype.raw` 方法获取解析函数的原函数，优化后的代码如下

```python
import utype
from typing import Iterator

@utype.parse
def fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
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

utype 同样支持异步的生成器函数，这种函数一般使用 `AsyncGenerator` 进行返回类型注解，如
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


## 配置函数解析

你可以在 `@utype.parse` 装饰器的参数中转入一些参数来控制函数的解析，包括

* `ignore_params`：是否忽略对函数参数的解析，默认为 False，如果开启，则 utype 不会对函数参数进行类型转化与约束校验
* `ignore_result`：是否忽略对函数结果的解析，默认为 False，如果开启，则 utype 不会对函数结果进行类型转化与约束校验
* `options`：传入一个解析选项来调控解析行为，具体用法可以参考 [Options 解析配置](/zh/references/options)

下面示例一下解析配置的用法
```python
import utype
from typing import Optional

class PositiveInt(int, utype.Rule):  
    gt = 0

class ArticleSchema(utype.Schema):
	id: Optional[PositiveInt]
	title: str = utype.Field(max_length=100)
	slug: str = utype.Field(regex=r"[a-z0-9]+(?:-[a-z0-9]+)*")

@utype.parse(
	options=utype.Options(  
	    addition=False,  
	    case_insensitive=True  
	),
	ignore_result=True,
)
def get_article(id: PositiveInt = None, title: str = '') -> ArticleSchema:
	return {
		'id': id,
		'title': title,
		'slug': '-'.join([''.join(
			filter(str.isalnum, v)) for v in title.split()]).lower()
	}

query = {'ID': '3', 'Title': 'Big shot'}
article = get_article(**query)

print(article)
# > {'id': 3, 'title': 'Big shot', 'slug': 'big-shot'}

try:
	get_article(**query, addon='test')
except utype.exc.ExceedError as e:
	print(e)
	"""
	parse item: ['addon'] exceeded
	"""
```

我们在 `get_article` 函数的 `@utype.parse` 装饰器中声明了解析配置，指定了一个解析选项 Options 实例，其中使用 `addition=False` 表示对于额外的参数会直接报错，`case_insensitive=True` 表示允许大小写不敏感地接受参数

所以我们看到，使用大写参数名称的数据可以被正常地传入处理，由于指定了 `ignore_result=True` ，所以结果并没有进行转化，如果传入了额外的参数，则会直接抛出 `exc.ExceedError` 错误

!!! note
	默认情况下  `@utype.parse`  会忽略额外的参数，这样与数据类的行为保持一致，你可以通过声明 `**kwargs` 参数的方式表示接受额外参数，也可以使用 `Options(addition=False)` 来禁止额外参数


* `eager`：对于生成器函数，异步函数和异步生成器函数，是否在调用函数时就直接对参数进行解析，而不是等到使用 `await`，`next()`，`for`，`async for` 等方法时才进行解析，默认为 False

我们可以来看一下默认情况下异步函数对于异常输入的行为
```python
import asyncio  
import utype

@utype.parse
async def sleep(seconds: float = utype.Param(ge=0)) -> float:  
    if not seconds:  
        return 0 
    await asyncio.sleep(seconds)  
    return seconds

invalid_coro = sleep(-3)   # no error occured

try:
	await invalid_coro
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['seconds'] failed: Constraint: <ge>: 0 violated
	"""
```

异常的输入在调用函数时并不会直接抛出错误，而是会等到使用 `await` 时才抛出。但在开启 `eager=True` 时，在传参时就会直接抛出错误，而不会等到调用 `await`，如

```python
import asyncio  
import utype

@utype.parse(eager=True)
async def sleep(seconds: float = utype.Param(ge=0)) -> float:  
    if not seconds:  
        return 0 
    await asyncio.sleep(seconds)  
    return seconds

try:
	sleep(-3)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['seconds'] failed: Constraint: <ge>: 0 violated
	"""
```

对于生成器函数，在开启 `eager=True` 时，也会在调用时直接进行解析，如

```python
import utype
from typing import Iterator

@utype.parse
def fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
    if not n:  
        yield _current  
    else:  
        yield fib(n - 1, _next, _current + _next)

invalid_gen = fib('abc')

try:
	next(invalid_gen)
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['n'] failed: could not convert string to float: 'abc'
	"""

@utype.parse(eager=True)
def eager_fib(n: int = utype.Param(ge=0), _current: int = 0, _next: int = 1) -> Iterator[int]:  
    if not n:  
        yield _current  
    else:  
        yield fib(n - 1, _next, _current + _next)

try:
	eager_fib('abc')
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['n'] failed: could not convert string to float: 'abc'
	"""
```

`eager=True` 的原理是将生成器函数，异步函数和异步生成器函数都转化为一个同步函数，在调用时就进行解析，然后返回对应的生成器对象 / 协程对象 / 异步生成器对象供用户进行操作

所以在开启了 `eager=True`  以后函数的性质其实发生了改变，但是对于使用者来说除了将参数解析行为提前外，感知不到区别

!!! note
	 `eager=True` 对于普通的同步函数没有意义，因为普通同步函数就是在调用时直接完成解析的


* `parser_cls`：传入你自定义的解析类，默认是 `utype.parser.FunctionParser`，你可以通过继承和扩展它来实现你自定义的函数解析功能


## 在类中的应用

我们有很多函数都是声明在类中的方法，比如

### 实例方法
声明在类中的函数默认就是实例方法，其中第一个参数接受的是类的实例，`@utype.parse` 也支持对实例方法的解析，包括进行初始化的 `__init__` 方法，如

```python
import utype

class IntPower:  
    @utype.parse  
    def __init__(  
        self,  
        base: int = utype.Param(ge=0),  
        exp: int = utype.Param(ge=0),  
    ):  
        self.base = base  
        self.exp = exp  
  
    @utype.parse  
    def power(self, mod: int = utype.Param(None, ge=0)) -> int:  
        return pow(self.base, self.exp, mod=mod)  
  
p = IntPower('3', 3.1)
print(p.base, p.exp)
# > 3 3

print(p.power())
# > 27
print(p.power('5'))
# > 2

try:
	p.power(-5)
except utype.exc.ParseError as e:
	"""
	parse item: ['mod'] failed: Constraint: <ge>: 0 violated
	"""
	print(e)
```

### `@staticmethod` 
在类中，使用  `@staticmethod` 装饰器的函数称为静态方法，其中不包含实例参数或类参数，utype 也支持解析静态访问，无论  `@utype.parse` 装饰器与 `@staticmethod` 的先后顺序如何，如

```python
import utype
from typing import Union

class Power:  
    @staticmethod  
	@utype.parse  
	def int_power(  
	    num: int = utype.Param(ge=0),  
	    exp: int = utype.Param(ge=0),  
	    mod: int = utype.Param(None, ge=0)
	) -> int:  
	    return pow(num, exp, mod)

	@utype.parse
	@staticmethod  
	def float_power(num: float, exp: float) -> Union[float, complex]:  
	    return pow(num, exp)

print(Power.int_power('3', 3.1))
# > 27

print(Power.float_power('2.5', 3))
# > 15.625
```

### `@classmethod`
在类中，使用  `@classmethod` 装饰器的函数称为类方法，类方法的第一个参数是类本身，可以用于访问类属性，其他的类方法或静态方法等，同样也支持 utype 解析

```python
import utype

class Power:  
    MOD = 10007  
    
    @classmethod  
    @utype.parse    
    def cls_power(
	    cls,
	    num: int = utype.Param(ge=0),  
	    exp: int = utype.Param(ge=0),  
	) -> int:  
        return pow(num, exp, mod=cls.MOD)

print(Power.cls_power('123', '321'))
# > 4402
```

### `@property`
在类中，使用  `@property` 装饰器可以使用函数的方式定义属性的访问，赋值，删除等操作，utype 也支持对属性的访问和赋值函数进行解析

```python
import utype

class Request:
    def __init__(self, body: bytes):  
        self.body = body  

    @property  
    @utype.parse    
    def json_body(self) -> dict:  
        return self.body  
  
    @json_body.setter  
    @utype.parse    
    def json_body(self, data: dict):  
        import json  
        self.body = json.dumps(data)  
  
req = Request(b'{"id": 11, "enabled": false}')

print(req.json_body['enabled'])
# > False

req.json_body = '{"id": 11, "enabled": true}'
print(req.json_body['enabled'])
# > True

try:
	req.json_body = '@invalid-payload'
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['data'] failed: Expecting value: line 1 column 1 (char 0)
	"""
```

可以看到，属性在访问时会按照属性函数的返回类型注解进行解析，在赋值时也会按照赋值函数的首个参数的类型进行解析，如果在赋值或取值时无法完成解析，则会抛出错误

!!! note
	需要注意的是，`@utype.parse` 需要施加在 `@property` 装饰器和 `setter` 装饰器的下方

### 应用到整个类

`@utype.parse` 除了可以单独地作用在类的函数中，它还可以直接对类进行装饰，实现的效果是：将该类中的非私有函数（名称不以下划线开头的函数，不包括 `@property`）全部变成解析函数，如

```python
import utype
from typing import Iterator, Union

@utype.parse  
class PowerIterator:  
    def _power(  
        self,  
        num: Union[int, float],  
        exp: Union[int, float],  
    ) -> Union[int, float, complex]:  
        return pow(num, exp, self.mod)  
  
    def iter_int(self, *args: int, exp: int) -> Iterator[int]:  
        for base in args:  
            yield self._power(base, exp)  
  
    @utype.parse  
    def __init__(self, mod: int = None):  
        self.mod = mod

pow_iter = PowerIterator('3').iter_int('3', '4', '5', exp=5)

print(next(pow_iter))
# > 0
print(next(pow_iter))
# > 1
print(next(pow_iter))
# > 2
```

在使用 `@utype.parse`  装饰的类中，所有名称不以 `_` 开头的函数都会被作用一样的解析配置，如例子中的 `iter_int` 生成器函数就获得了解析能力

!!! note
	虽然 `@utype.parse` 施加在类上时不会应用以下划线开头命名的内部方法，但你可以手动为以下划线开头命名的方法装饰，比如例子中就主动为 `__init__` 方法进行了装饰

**utype 中的类装饰器**

utype 提供的很多装饰器都可以作用到类中，但它们的作用各自不同

* `@utype.apply`：为自定义类型施加约束
* `@utype.parse` ：将类中的所有公开方法（不以下划线开头的函数，不包括 `@property` 属性）变成解析函数
* `@utype.dataclass`：生成类中关键的内部方法（如 `__init__`，`__repr__`，`__eq__` 等），使得类获得初始化数据的解析能力，初始化的数据映射和赋值，以及为类的属性（包括普通属性和 `@property` 属性）提供类型解析能力

由于这些装饰器各自的功能互相独立，所以你也可以根据你的需要自由组合使用它们

### 适用场景

相较于普通的函数，utype 在解析函数的调用中完成了额外的类型转化，约束校验和参数映射工作，所以肯定会造成轻微的调用延时，对于单次调用这样的延时可以忽略，但如果你需要高频地大量调用的话，解析产生的性能影响就是不可忽略的。所以 utype 的解析函数更适合作用于

* 类库的入口函数
* 网络编程的 API 接口函数
* 集成第三方接口或类库的函数

由于来自用户，网络或第三方的数据具有不确定性，所以你可以把 utype 作用在这一层，作为输入校验和类型安全的保障，而对于你系统或类库中传参较为稳定，调用较为频繁的内部函数来说，则一般不需要使用 utype 的解析语法

`@utype.parse` 在装饰类时并没有将解析能力应用到全部的方法，而是只作用在公开方法的机制就是为了让开发者建立这样的心智模型，即建议公开的，提供给用户的方法使用 utype 提供的解析能力，而内部的方法则根据实际需要进行判断

