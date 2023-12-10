# Functions

Currently, Python does not have the mechanism to guarantee types at runtime, so when we write a function, we often need to perform type assertion and constraint checking on parameters before we can start writing the actual logic. such as
```python
def login(username, password):  
    import re  
    if not isinstance(username, str) \  
            or not re.match('[0-9a-zA-Z]{3,20}', username):  
        raise ValueError('Bad username')  
    if not isinstance(password, str) \  
            or len(password) < 6:  
        raise ValueError('Bad password')  
    # below is your actual logic
```

So utype provides a function parsing mechanism. You just need to declare the type, constraint and configuration of the function parameter, and use `@utype.parse` to decorate the function, then the function will be type-safe and constraint-guaranteed at runtime
=== "Using Annotated"  
	```python
	import utype
	from utype.types import Annotated
	
	@utype.parse
	def login(
		username: Annotated[str, utype.Param(regex='[0-9a-zA-Z]{3,20}')],
		password: Annotated[str, utype.Param(min_length=6)]
	):
		# you can directly start coding
		return username, password
	
	print(login('alice', 123456))
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

=== "Using default"
	```python
	import utype
	
	@utype.parse
	def login(
		username: str = utype.Param(regex='[0-9a-zA-Z]{3,20}'),
		password: str = utype.Param(min_length=6)
	):
		# you can directly start coding 
		return username, password
	
	print(login('alice', 123456))
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

as you can see, utype will automatically convert the types for input parameters. For input values that cannot complete the type conversion or violate the constraints, utype will throw a clear error, which contains the position and reason of the error

So in this document, we will introduce the declaration and usage of function parsing in detail.

## Declare parameters

utype supports native function syntax, which means that in the simplest case, you just need to add a `@utype.parse` decorator to your function to get the ability of parsing

```python
import utype

@utype.parse
def add(a: int, b: int) -> int:
	return a + b

print(add('3', 4.1))
# > 7
```

!!! note
	Function parsing requires type annotation for parameters, if a param is not type-annotated, any type of value can be passed in

You can use not only primitive types in functions, but also constraint types, nested types, logical types, dataclasses, etc. and utype can correctly identify and complete parsing.

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
# > ArticleInfo(id=1, slug='my-article', likes={'alice': 1, 'bob': 2})
```

However, using the native function syntax only supports declaring the type and default value of the parameter. If you need more parameter configuration, you can use `utype.Param` to configure the function parameter.

### Configure Param
The `Param` class can configure a series behaviors for function parameters, including default values, descriptions, constraints, aliases, input behaviors, etc. You only need to use an instance of the `Param` class as the default value of a function parameter to obtain the field configuration declared in it

Here are some examples of common configuration usage. Let’s write a function to create a user.
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

Function `create_user` in above example declared the following params

* `username`: declares `str` type, specifies `regex` constraint for regex validation, and uses `example` describe the example value.
* `password`:  declares `str` type, specifies `min_length` and `max_length` constraints for length validation
* `avatar`: declares `Optional[str]` type, indicating that a string or None can be passed in. the first parameter of the `Param` is used to specify the default value of `None`, and `description` is used to document the field,  `alias_from` specifies some aliases that can be converted from, which can be used for compatibility with legacy parameters.
* `signup_time`: declares `datetime` type. specifies `no_input=True`, which means that the user input is not accepted, that is to say, the default value function `default_factory`  will be directly called and filled at function calling, which fills in the current time to be the registration time of the new user

Let’s call this function and see how it works.

```python
bob = create_user(b'bob_007', 1234567)
print(bob)
# > {'username': 'bob_007', 'password': '1234567', 'avatar': None, 'signup_time': datetime(...)}

from utype import exc

# - Invalid input
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

As you can see

1. The type of the input data is converted to the type of the corresponding function parameter declaration
2. If the input data does not satisfy the constraints of the function arguments, an error is thrown containing position and reason of the error.
3. Because `avatar` specified `alias_from` containing `'headImg'`, we can also correctly identify and convert it into a `avatar` parameter by using `'headImg'` as a parameter name.
4. Since `signup_time` is specified `no_input=True`, even if the corresponding field is passed in, it will be ignored and the current time will be filled in according to `default_factory`

!!! note
	`Param` is actually a subclass of `Field` with more simplify and convenient params for function, so you can still get the detail usage of `Param` in [Field API References](/references/field)

### Using `Annotated`
You can also use `Annotated` to define `Param` as part of type annotation, like

```python
import utype
from datetime import datetime
from typing import Optional, Annotated

@utype.parse  
def create_user(  
    username: Annotated[str, utype.Param(regex='[0-9a-zA-Z_-]{3,20}', example='alice-01')],  
    password: Annotated[str, utype.Param(min_length=6, max_length=50)],  
    signup_time: Annotated[datetime, utype.Param(  
        no_input=True,  
        default_factory=datetime.now  
    )],
    avatar: Annotated[Optional[str], utype.Param(
        description='avatar url of the new user',  
        alias_from=['picture', 'headImg'],  
    )] = None,  
) -> dict:  
    return {  
        'username': username,  
        'password': password,  
        'avatar': avatar,  
        'signup_time': signup_time,  
    }
```

By using `Annotated`, you can define the default value of the argument in native way, and get more precise static type checking (such as mypy)


!!! warning
	`Annotated` is supported in Python 3.9+, to compat 3.7/3.8, you should use `from utype.types import Annotated`

### Parameter restrictions
Characteristics of the function brings more restrictions to declare the field configuration in the function than in the dataclass. Let’s take a look.

**Parameter passing for Python function**

Before introducing the declaration restrictions of fields, let’s review the parameter types of Python functions and how they are passed.
```python
def add(a: int, b: int) -> int:
	return a + b

add(1, 2)      # positional
add(a=1, b=2)  # keyword
add(1, b=2)    # mixed
# > 3
```
In Python, you can pass function params in two ways

* Positonal: Passed in the order in which parameter are declared
* Keyword: Pass by the name of the function parameter.

Different types of parameters support different ways of passing. The following is an example that covers all types of parameters.
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
The properties of each class of parameters are

* `pos_only`: Parameters declared before the symbol `/` can only be passed in positional way (supported Python >=3.8 only)
* `pos_or_kw`: The default parameter category, which supports both positional and keyword passing
* `*args`: Variable positional parameters, that is, postional parameters beyond the declared parameter are received by this parameter. (`args` will get a `tuple` instance)
* `kw_only`: Parameters after `*args`  or a single `*` symbol can only be passed by keyword
* `**kwargs`: Variable keyword parameters. If the passed parameter name is outside the scope of your declaration, it will be accepted by this parameter.  (`kwargs` will get a `Dict[str, Any]`)

Next, we’ll look at specific parameter declaration restrictions, which may vary for different categories of parameters

**Restrictions for required parameters**

Required parameters that support positional passing cannot be declared after optional parameters in Python functions, such as

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

In utype, because the parameter using `Param` as the default value may also be a required parameter, there is also such a restriction, such as the following is an inappropriate declaration.

```python
import utype

@utype.parse
def bad_example(opt: int = utype.Param(None), req: str = utype.Param()):
	pass

# UserWarning: non-default argument: 'req' follows default argument: 'opt'
```

That is, if a parameter supports passing in order, do not declare a required parameter after an optional parameter, which makes the optional parameter meaningless. If such a parameter supports passing by keyword, utype will only warn, but if such a parameter only supports passing in positional, it will throw an error directly, as shown in
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

However, you can make such a declaration if your parameters support name passing only, as shown in
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


**Restricted Param Configuration**

Because function parameters must pass in a meaningful value (either an input value or a default value), the use of some parameters in the Param configuration is restricted, and/must be specified if they are used.

* `required=False`
* Use `no_input`
* Use `mode` / `readonly` / `writeonly`

**Invalid Param configuration**

For params that only support positional passing, some `Param` configuration is invalid, such as

* `alias_from`
* `case_insensitive`

###  `*args` & `**kwargs`

In Python functions, arguments like `*args` and `**kwargs` represent positional and keyword variable-length arguments. utype also support value declaration types for `*args` and `**kwargs`, and correctly identify and complete the parsing, such as

```python
from utype import Rule, parse, exc
from typing import Dict

class Index(int, Rule):  
    ge = 0

@parse  
def call(*series: int, **mapping: Index | None) -> Dict[str, int]:  
	print('series:', series)
	print('mapping:', mapping)
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
# > series: (-1, 3, 4)
# > mapping: {'k1': 1, 'k2': None, 'k3': 0}

print(res)
# > {'k1': 3, 'k3': -1}

# - Invalid Input for `*series`
try:
	call('a', 'b')
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['*series:0'] failed: could not convert string to float: 'a'
	"""

# - Invalid Input for `**mapping`
try:
	call(1, 2, key=-3)
except exc.ParseError as e:
	print(e)
	"""
	parse item: ['**mapping:key'] failed: Constraint: <ge>: 0 violated;
	"""
```


By default, `*args` will receive a tuple ( `tuple`) whose elements are of unknown type, but when you use a type annotation on it, you’ll get a tuple whose elements are all of that type (that is `Tuple[<type>,...]`,). In the above example, `series` will be `Tuple[int, ...]` in the function

`**kwargs` will receive a dictionary ( `Dict[str, Any]`) by default. but when you use a type annotation on it, you will get a dictionary with a fixed value type ( `Dict[str, <type>]`), in the above example, `mapping` will gets a dictionary with an integer value greater than or equal to zero or `None`.

And in the example, we see that when the input variable parameter fails to complete the corresponding type conversion, it will throw a parsing error, which contains specific positioning information and failure reasons.


### Private parameters

In utype, function param that begin with an underscore ( `_` ) are called private parameter, which has following features

* Does not participate in function parsing
* Cannot be passed as a keyword
* Will not appear in the API document generated by the function (not visible to the client)

This feature is often used for
* When a function is provided for external calling, such as being called by an HTTP/RPC client, the client is often required to specify the name of the parameter to pass in, so the private parameter is invisible to the outside, and cannot be passed in by name
* When the function is called in the internal code, parameters can be passed directly in positional. In this case, private parameters can be passed in

For example
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

As you can see, a private parameter passed in as a name is ignored, but a private parameter passed in positional is accepted and processed

If you need to prevent private parameters from being passed in at all, you can declare that they are only allowed to be passed by name, as shown in
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
	this way is same as declaring `no_input=True`

## Parse return value
utype also supports parse the return value of function

The syntax for annotate the return value type of a function is `def (...) -> <type>:`, where `<type>` is the type you specify for the return value, which can be any normal type, constrained type, nested type, logical type, dataclass, etc.

However, different kinds of functions may have different ways to declare the return type

### Normal function

To declare a return value for an ordinary function, you only need to annotate it directly with the corresponding type, as shown in
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

In the example, we use `ArticleSchema` as the return type of the function `get_article`, and utype will automatically convert the return value of the function into an instance of `ArticleSchema`

```python
print(get_article('3', title=b'My Awesome Article!'))
#> ArticleSchema(id=3, title='My Awesome Article!', slug='my-awesome-article')

# - Invalid params
try:
	get_article('-1')
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['id'] failed: Constraint: : 0 violated
	"""

# - Invalid return
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

As you can see, whether the parameter fails to parse or the returned result fails to parse, an error is thrown

### Asynchronous function
utype also supports parsing asynchronous functions, which are declared in the same way as synchronous functions. Let’s use an asynchronous HTTP client code as an example.

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

In the example, we used the `aiohttp` library to make asynchronous HTTP requests, and used `fetch_urls` to aggregate several asynchronous request tasks to avoid network I/O blocking.

API `'https://httpbin.org/get'` will return the parameter information of the request in JSON. In the `fetch()` function, we only convert the result to a string, but in the `fetch_urls()` function, we use `Dict[str, dict]` to annotate the result type. The JSON string in the response will be converted to the Python dictionary, and finally we can directly use the key value to access the corresponding items for output.

That is to say, whether it is a synchronous function or an asynchronous function, the use of `@utype.parse` + type declaration can guarantee the type safety of function calls.

### Generator function

utype also supports generator function using `yield`. The generator can temporarily store the execution state of the function, optimize memory usage, and implement many mechanisms that cannot be implemented by ordinary functions, such as constructing an infinite loop list. Let’s first use an example to see how the return value of the generator function is declared.

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

In this example, we read a CSV file in string format, split it by line, and iterate over the splited results. We know that the `split` string method will return a list of strings, but because of our return type declaration, When you use `next(csv_gen)` to iterate, you get an integer tuple directly

Generator functions often use a `Generator` type for the return annotation, where three positional parameters are passed in.
1. The type `value` of `yield value`, that is, the element type of the iteration
2. The type `value` of `generator.send(value)`, that is, the type of data to be sent. you can pass None if no data will be sent
3. The type `value` of `return value`, you can pass None if no value is returned

For the return value of the generator function `return`, we get it by access the `value` attribute of the `StopIteration` error after the generator iterates, In the example above, we used `int` type as the return type of the generator function to covert the return value (number of lines read) to `int`

However, for common generator functions, we may only need to `yield` results, and do not need to support external sending or return values. In this case, the following types can be used as return annotation

* `Iterator[<type>]`
* `Iterable[<type>]`

Only one parameter needs to be passed in, which is the type `value` of `yield value`, such as

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

In this example, we use `split(',')` to split each item of a string list and `yield` the result, so we use `Iterator[Tuple[int, int]]` as return annotation
When the data cannot complete parsing, we can use `exc.ParseError` to receive the error, which will contain the positioning information, accurate to the iteration index in the generator.

#### Generator.send(value)

you can send the value into the generater by using `send(value)`, and annotate the type of the `value` by using the second parameter in the `Generator`, such as

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

In our example, we declare a generator function `echo_round` that supports sending values , which can round the value sent, and record the number of times sent in the function and return it as the result.

The type we specify for `send(value)` 's value is `float`, so the data sent will be converted to float type, which can be directly used for subsequent operations.


#### Tail recursive optimization

Another use of the generator function is to help Python solve tail-recursive optimization problems, such as
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
	Ordinary Python function does not support tail-recursion, so if the call stack depth exceed certain limit (default to 1000 or so), execution will be failed and a `RecursiveError` is raised, but using generator-style tail-recursion can solve this problem

If your tail-recursive generator uses `@utype.parse` decoration, you can simplify the call by declaring the final return type. When utype recognizes that the iterator yield is still a generator, it will continue to iterate until it gets the result, so the above example can be simplified to

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

As you can see, for the tail recursion optimized generator, we can directly use one `next()` to get the result, but you will find that if the `n` exceeds 1000, the stack will still overflow and throw an error. Why?

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

Because we use a decorated `fib` function when we call recursively, each recursion will parse parameters in utype, so stackoverflow will still occur, but because we have been able to guarantee the type safety of the call after the first call has been parsed. So we can directly use `fib` the original function to call. We can get the original function of the parsing function through `utype.raw` the method. The optimized code is as follows.

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

This not only ensures the type safety of the call, but also optimizes the tail recursion generator and the performance of multiple calls.

### Asynchronous generator

utype also supports asynchronous generator functions, which are typically `AsyncGenerator` annotated with return types, such as
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

The return value of the asynchronous generator needs to be `AsyncGenerator` annotated with the type, which has two parameters.

* The type of the value `yield value` in `value` the
* The type of the value `generator.asend(value)` sent `value`

If your asynchronous generator doesn’t need to accept `asend()` data, you can use it directly.

* `AsyncIterable`
* `AsyncIterator`

Only one type needs to be passed in, which is the type of the value generated by the asynchronous generator `yield`.

!!! note
	in Python, asynchronous generator does not support return value

## Configure function parsing

There are some params in `@utype.parse` decorator to control the parsing of the function, including

* `ignore_params`: Whether to ignore the parsing of function parameters. The default is False. If it is enabled, utype will not perform type conversion and constraint validation on function parameters.
* `ignore_result`: Whether to ignore the parsing of function return values. The default is False. If it is enabled, utype will not perform type conversion and constraint validation on function return values.
* `options`: Pass in a parsing option to control the parsing behavior. Please refer to the specific usage in  [Options API References](/references/options).

The following is an example of the use of the parse configuration
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

# > Invalid params
try:
	get_article(**query, addon='test')
except utype.exc.ExceedError as e:
	print(e)
	"""
	parse item: ['addon'] exceeded
	"""
```

We declare the parsing configuration in `get_article` the function’s `@utype.parse` decorator, specifying an instance of the parsing `Options`, where using `addition=False` indicates that additional parameters is not allowed, and `case_insensitive=True` to indicates that case-insensitive parameters is allowed.

So we see that data that uses an uppercase parameter name can be passed in and mapped to param correctly, and because `ignore_result=True` is specified, the result is not converted, and if an extra parameter is passed in, an `exc.ExceedError` error is thrown directly.

!!! note
	By default, utype will ignore the additional params to stay identical to dataclass, you can absorb the additional params by declare  `**kwargs`, or use `Options(addition=False)`  to ban any additional params

* `eager`: For generator functions, async functions and async generator functions, whether the parameters are parsed directly when the function is called, rather than when methods such as `await`, `next()`, `for`, `async for`. The default is False

Let’s take a look at the default behavior ( `eager=False` ) of asynchronous functions for abnormal input.
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

The invalid input does not throw an error directly when the function is called, but rather when it is used `await`. However, when `eager=True`, an error will be thrown directly when the parameter is passed, instead of waiting for the `await` statement, such as

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

For the generator function, when `eager=True`, params will also be parsed directly when it is called, such as

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

the underlying principle of `eager=True` is to convert the generator function, asynchronous function and asynchronous generator function into a synchronous function, parse params when it is called, and then return the corresponding generator object/coroutine object/asynchronous generator object for the user to operate.

So the category of the function actually changes after the `eager=True` decorate, but for the user, there is no difference except to advance the parameter parsing behavior.

!!! note
	`eager=True` has no meaning for synchronous function

* `parser_cls`: pass in your custom parsing class. By default `utype.parser.FunctionParser`, you can implement your custom function parsing by inheriting and extending it.


## Application in Class

Many of functions are methods declared in classes, they can also use utype to parse params and returns, such as

### Instance method
Functions declared in a class are instance methods by default, where the first parameter accepts an instance of the class. `@utype.parse` also supports to parse instance methods, including initialization `__init__` methods, such as

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

# > Invalid params
try:
	p.power(-5)
except utype.exc.ParseError as e:
	"""
	parse item: ['mod'] failed: Constraint: <ge>: 0 violated
	"""
	print(e)
```

### `@staticmethod`
In a class, functions that use `@staticmethod` decorators are called static methods, which contain no instance or class parameters. utype also supports to parse staticmethods, regardless the order of `@utype.parse`  and`@staticmethod`, as shown in

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
In a class, functions that use `@classmethod` decorators are called class methods. The first parameter of a class method is the class itself, which can be used to access class properties, other class methods, or static methods. It also supports utype parsing.

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
In the class, `@property` can be used to define the access, assignment, deletion and other operations of attributes in the form of functions, and utype also supports the access of attributes and the parsing of assignment functions.

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

the property will be parsed according to the return type annotation of getter, and will also be parsed during assignment. If the parsing cannot be completed during assignment or getter calculation, an error will be thrown.

!!! note
	`@utype.parse` must under `@property` decorator

### Apply to entire class

`@utype.parse` can also decorate a class directly, with the effect of turning all non-private functions in the class (functions whose names do not begin with an underscore, excluding `@property`) into analytic functions, such as

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

In `@utype.parse` decorated class, all functions with names that do not begin with `_` will be used with the same parsing configuration, such as the generator function in `iter_int` the example.

!!! note
	you can manually decorate the private function, just like the above example has decorated `__init__` manually

**Class decorators in utype**

Many of the decorators provided by utype can be applied to classes, but their roles are different.

* `@utype.apply`: Enforce constraints for custom types
* `@utype.parse`: Turn all public methods in the class into parsing functions
* `@utype.dataclass` Generates key internal methods in the class (such as `__init__`, `__repr__` `__eq__`, etc.) That give the class the ability to parse, map initialized data, and assign values. And provide type parsing for the properties of a class

Since these decorators are independent of each other, you can use them in any combination you want.

### Applicable scenarios

Compared with ordinary functions, utype performs additional type conversion, constraint validation and parameter mapping in the call of parsing functions, so it will certainly cause slight latency, which can be ignored for a single call, but if you need to make a large number of frequent calls, the performance impact of parsing can not be ignored. So utype’s analytic functions are better suited to be used at

* Entry function of class library
* API function in network programming
* Functions that integrate third-party interfaces or class libraries

Because of the uncertainty of data from users, networks, or third parties, you can use utype in this layer as a guarantee of input validation and type safety. For internal functions in your system or class library that pass parameters more stably and call more frequently, you generally do not need to use utype’s parsing syntax.

When  `@utype.parse` decorating a class, the parsing ability is not applied to all methods, but only to public methods. The purpose of the mechanism is to allow developers to build such a mental model, that is, to suggest that public methods provided to users use the parsing capability provided by utype, while internal methods are judged according to actual needs.

