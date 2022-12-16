# Functions

Currently, Python does not have a mechanism to resolve types and check constraints at runtime, so when we write a function, we often need to perform type assertion, constraint checking and other operations on the parameters before we can start writing the real logic. Otherwise, an exception may occur at runtime, such as
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

So utype provides a function parsing mechanism. You just need to declare the type, constraint and configuration of the function parameter, and then use `@utype.parse` the decorator to get the type-safe and constraint-guaranteed parameter value in the function, such as
```python
import utype

@utype.parse
def login(
	username: str = utype.Param(regex='[0-9a-zA-Z]{3,20}'),
	password: str = utype.Param(min_length=6)
):
	# you can directly start coding
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

It can be seen that utype will automatically complete the type conversion of parameters. For input values that cannot complete the type conversion or do not meet the constraint conditions, utype will throw a clear error, which contains the positioning information in the data and the reason for the error.

So in this document, we will introduce the declaration and usage of parsing function in detail.

## Declare function parameters

Utype supports native function syntax, which means that in the simplest case, you just need to add a `@utype.parse` decorator to your function to get the ability to parse

```python
import utype

@utype.parse
def add(a: int, b: int) -> int:
	return a + b

print(add('3', 4.1))
# > 7
```

!!! note

You can use not only primitive types in functions, but also constraint types, nested types, logical types, data classes, etc. In utype for type annotation, and utype can correctly identify and complete parsing.

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

However, using the native function language only supports declaring the type and default value of the parameter. If you need more parameter configuration, you can use utype to provide the Param class to configure the function parameter.

### Configure the Param parameters
The Param class can configure rich behaviors for function parameters, including default values, descriptions, constraints, aliases, input behaviors, etc. You only need to use an instance of the Field class as the default value of a function parameter to obtain the field configuration declared in it

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

*  `username`: The user name parameter declares the str string type, specifies the regular constraint `regex` for the field in the parameter configuration, and uses `example` the parameter to describe the example value.
*  `password`: password parameter, str string type is declared, and minimum length and maximum length constraints are used `min_length` and `max_length` specified in the parameter configuration
*  `avatar`: The avatar parameter is declared `Optional[str]`, indicating that a string or None can be passed in. The first parameter of the Param class is used to specify the default value of `None`, and `description` the format and use of the field are documented. And the use `alias_from` specifies some aliases that can be converted from, which can be used for compatibility with old version parameters.
*  `signup_time`: The time parameter is registered and the date type is declared `datetime`. It is configured `no_input=True` in the parameter configuration, which means that the user input is not accepted. That is to say, the default value of the `default_factory` manufacturing will be directly filled when it is called, that is, the current time. Registration time as a new user

Let’s call this function and see how it works.

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

You can see
1. The type of the input data is converted to the type of the corresponding function parameter declaration
2. If the input data does not satisfy the constraints of the function arguments, an error is thrown containing the positioning information and the reason for failure.
3. Because `avatar` the parameter specified `alias_from` in the field contains `'headImg'`, we can also correctly identify and convert it into a `avatar` parameter by using `'headImg'` it as a parameter name.
4. Since `signup_time` is specified `no_input=True`, even if the corresponding field is passed in, it will be ignored and the current time will be filled in according to `default_factory` the configuration of

!!! note


### Parameter declaration restrictions
Because of the characteristics of the function, there are more restrictions to declare the field configuration in the function than in the data class. Let’s take a look.

Parameter passing mode ** of ** Python function

Before introducing the declaration restrictions of fields, let’s review the parameter types of Python functions and how they are passed.
```python
def add(a: int, b: int) -> int:
	return a + b

add(1, 2)      # positional
add(a=1, b=2)  # keyword
add(1, b=2)    # mixed
# > 7
```
In Python, you can pass function arguments in two ways

* Pass in order. The function parameters are passed in the order in which they are declared
* Pass by name. Pass by the name of the function parameter.

Different types of parameters support different ways of passing parameters. The following is an example that covers all types of parameters.
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

*  `pos_only`: Parameters declared before the symbol `/` can only be passed in sequential mode
*  `pos_or_kw`: The default parameter category, which supports both sequential and name passing
* Variable length parameters that are passed in order are `*args` used, that is, sequential parameters beyond the declared parameter are received by this parameter.
* Parameters after `*args` `kw_only` or a single `*` symbol can only be passed by name
* Variable length parameter passed `**kwargs` by name. If the passed parameter name is outside the scope of your declaration, it will be accepted by this parameter.

Next, we’ll look at specific parameter declaration restrictions, which may vary for different categories of parameters

Declared restrictions ** on ** optional parameters

Required parameters that support sequential passing cannot be declared after optional parameters in Python functions, such as

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

In utype, because the parameter using Param configuration as the default value may also be a required parameter, there is also such a restriction, such as the following is an inappropriate declaration.

```python
import utype

@utype.parse
def bad_example(opt: int = utype.Param(None), req: str = utype.Param()):
	pass

# UserWarning: non-default argument: 'req' follows default argument: 'opt'
```

That is, if a parameter supports passing in order, do not declare a required parameter after an optional parameter, which makes the optional parameter meaningless. If such a parameter supports passing by key, utype will only warn, but if such a parameter only supports passing in order, it will throw an error directly, as shown in
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


** Restricted Param Configuration **

Because function parameters must pass in a meaningful value (either an input value or a default value), the use of some parameters in the Param configuration is restricted, and/must be specified if they are used.

* `required=False`
* Use `no_input`
* Use `mode`//

Invalid Param configuration ** under ** certain conditions

Some of the parameters that support only sequential input are invalid, such as

* `alias_from`
* `case_insensitive`

Because these are all working on the name of the parameter support.

###  `*args` & `**kwargs`

In Python functions, arguments like `*args` and `**kwargs` represent sequential and key variable-length arguments, respectively. The parsing functions in utype also support value declaration types in bits `*args` or `**kwargs`, And correctly identify and complete the parsing, such as

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


By default, a sequential variable-length argument ( `*args`) will receive a tuple ( `tuple`) whose elements are of unknown type, and when you use a type declaration on it, you’ll get a tuple whose elements are all of that type (that is `Tuple[<type>,...]`,). For example, in the `series` example, the parameter will get a tuple whose element is an integer int, and the key value variable length parameter ( `**kwargs`) will receive a dictionary ( `Dict[str, Any]`) whose key is a string type and whose value type is unknown by default. You will get a dictionary with a fixed value type ( `Dict[str, <type>]`), such as the example where the `mapping` parameter gets a dictionary with an integer value greater than or equal to zero or None.

And in the example, we see that when the incoming variable length parameter fails to complete the corresponding type conversion, it will throw a parsing error, which contains specific positioning information and failure reasons.


### Private parameter

In function arguments, function arguments that begin with an underscore are called private arguments, which are characterized by

* Does not participate in function resolution
* Cannot be passed as a key
* Will not appear in the API document generated by the function (not visible to the client)

This condition is often used for
* When a function is provided for external calling, such as being called by an HTTP/RPC client, the client is often required to specify the name of the parameter to pass in, so the private parameter is invisible to the outside, and the page cannot be passed in by name
* When the function is called in the internal code, parameters can be passed directly in sequence. In this case, private parameters can be passed in

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

As you can see, a private parameter passed in as a name is ignored, but a private parameter passed in as a sequential parameter is accepted and processed

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

** Get the primitive function **

For parsing functions that use `@utype.parse` decorations, if you really need to pass private parameters or `no_input=True` parameters in the code, although it cannot be done by calling the function directly, you can `utype.raw` get the original function of the parsing function, such as

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


## The analytic function returns a value
The utype can not only parse the parameters of the function, but also parse the return value of the function to the declared type.

The syntax for declaring the return value of a function is `def (...) -> <type>:`, where `<type>` is the type you specify for the return value, which can be any normal type, constraint type, nested type, logical type, data class, etc.

However, different kinds of functions may have different ways to declare the return value, and the return value declaration of each function in Python will be discussed separately below.

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

In the example, we use the ArticleSchema data class as the return type hint of the function `get_article`, and utype will automatically convert the return value of the function into an instance of ArticleSchema, such as

```python
print(get_article('3', title=b'My Awesome Article!'))
#> ArticleSchema(id=3, title='My Awesome Article!', slug='my-awesome-article')

try:
	get_article('-1')
except utype.exc.ParseError as e:
	print(e)
	"""
	parse item: ['id'] failed: Constraint: : 0 violated
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

As you can see, whether the parameter fails to complete the conversion or the returned result fails to complete the conversion, an error is thrown

### Asynchronous function
Utype also supports the type resolution of asynchronous functions, which are declared in the same way as synchronous functions. Let’s use an asynchronous HTTP client code as an example.

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

The interface of our request `'https://httpbin.org/get'` will return the parameter information of the request in JSON. In the `fetch()` function, we only convert the result to a string, but in the `fetch_urls()` function, we use `Dict[str, dict]` to annotate the result type. The JSON string in the response will be converted to the Python dictionary, and finally we can directly use the key value to access the corresponding element for output.

That is to say, whether it is a synchronous function or an asynchronous function, the use of `@utype.parse` + type declaration can guarantee the type safety of function calls.

### Generator function

The utype also supports the use `yield` of the generator function. The generator can temporarily store the execution state of the function, optimize memory usage, and implement many mechanisms that cannot be implemented by ordinary functions, such as constructing an infinite loop list. Let’s first use an example to see how the return value of the generator function is declared.

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

In this example, we read a CSV file in string format, split it by line, and `split(',')` iterate over the results. We know that the `split` string method will return a list of strings, but because of our return type declaration, When you use `next(csv_gen)` to iterate, you get an integer tuple directly, which is what utype does with your declaration.

Generic generators use a `Generator` type for the return annotation, where three order parameters are passed in.
1. The type of the `yield value` median `value`, that is, the element type of the iteration
2. The type of the `generator.send(value)` value `value`, that is, the type of data to be sent. If data sending is not supported, None is passed in
3. The type of the `return value` value `value`, that is, the data type returned. If no value is returned, None is passed in

For the return value of the generator function `return`, we get it by throwing the property of the StopIteration error instance `value` after the generator iterates, because `read_csv` the function returns the number of rows read. So in the example above, we used `int` type as the return type of the generator function.


However, for common generator functions, we may only need to `yield` output results, and do not need to support external sending or return values. In this case, the following types can be used as return prompts

* `Iterator[<type>]`
* `Iterable[<type>]`

Only one parameter needs to be passed in, which is `yield` the type of the value, such as

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

In this example, we split each element `split(',')` of a string list and return the result `yield` without returning a value, so we use `Iterator[Tuple[int, int]]` the type declaration of to indicate that `yield` the type of the value is an integer tuple. When the data cannot complete the corresponding transformation, we can use `exc.ParseError` to receive the error, which will contain the positioning information, accurate to the iteration index in the generator.

#### The generator sends the value

The generator can not only accept `yield` the value iterated out, but also send the value to the generator by using `send()` the method. You can use the second parameter in the Generator type to specify `send()` the type of the value passed by the method, such as

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

In our example, we declare a function that supports sending values `echo_round`, which can round the value sent, and record the number of `cnt` times sent in the function and return it as the result.

The type we specify for `send()` the sent value is `float`, so the data sent will be converted to float type, and the variable used to receive `sent` in the function will be a floating point number, which can be directly used for subsequent operations.


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

As you can see, for the tail recursion optimized generator, we can directly use one `next()` to get the result, but you will find that if the number of calls exceeds 1000, the stack will still burst and throw an error. Why?

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

Because we use a decorated `fib` function when we call recursively, each recursion will parse parameters in utype, so stack burst will still occur, but because we have been able to guarantee the type safety of the call after the first call has been parsed. So we can directly use `fib` the original function to call. We can get the original function of the parsing function through `utype.raw` the method. The optimized code is as follows.

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

### Asynchronous generator function

Utype also supports asynchronous generator functions, which are typically `AsyncGenerator` annotated with return types, such as
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


## Configure function parsing

You can put some arguments in the `@utype.parse` decorator’s arguments to control the parsing of the function, including

*  `ignore_params`: Whether to ignore the resolution of function parameters. The default is False. If it is enabled, utype will not perform type conversion and constraint verification on function parameters.
*  `ignore_result`: Whether to ignore the parsing of function results. The default is False. If it is enabled, utype will not perform type conversion and constraint verification on function results.
*  `options`: Pass in a parsing option to control the parsing behavior. Please refer to the specific usage.

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

try:
	get_article(**query, addon='test')
except utype.exc.ExceedError as e:
	print(e)
	"""
	parse item: ['addon'] exceeded
	"""
```

We declare the parsing configuration in `get_article` the function’s `@utype.parse` decorator, specifying an instance of the parsing option Options, where using `addition=False` indicates that errors will be reported directly for additional parameters, and `case_insensitive=True` that case-insensitive acceptance of parameters is allowed.

So we see that data that uses an uppercase parameter name can be passed in for processing normally, and because it is `ignore_result=True` specified, the result is not converted, and if an extra parameter is passed in, an `exc.ExceedError` error is thrown directly.

!!! note


*  `eager`: For generator functions, async functions and async generator functions, whether the parameters are resolved directly when the function is called, rather than when methods such as, `next()`, `for`, `async for` are used `await`. The default is False

Let’s take a look at the default behavior of asynchronous functions for abnormal input.
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

The input of the exception does not throw an error directly when the function is called, but rather when it is used `await`. However, when it is opened `eager=True`, an error will be thrown directly when the parameter is passed, instead of waiting for the call `await`, such as

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

For the generator function, when it is turned on `eager=True`, it will also be resolved directly when it is called, such as

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

 `eager=True` The principle is to convert the generator function, asynchronous function and asynchronous generator function into a synchronous function, parse it when it is called, and then return the corresponding generator object/coroutine object/asynchronous generator object for the user to operate.

So the nature of the function actually changes after it is opened `eager=True`, but for the user, there is no difference except to advance the parameter parsing behavior.

!!! note


*  `parser_cls`: Pass in your custom parsing class. By default `utype.parser.FunctionParser`, you can implement your custom function parsing by inheriting and extending it.


## Application in Class

Many of our functions are methods declared in classes, such as

### Instance method
Functions declared in a class are instance methods by default, where the first parameter accepts an instance of the class. `@utype.parse` It also supports the resolution of instance methods, including initialization `__init__` methods, such as

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

###  `@staticmethod`
In a class, functions that use `@staticmethod` decorators are called static methods, which contain no instance or class parameters. Utype also supports resolving static access, regardless `@utype.parse` of the order of the decorators and `@staticmethod`, as shown in

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
In the class, `@property` the decorator can be used to define the access, assignment, deletion and other operations of attributes in the form of functions, and utype also supports the access of attributes and the parsing of assignment functions.

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

It can be seen that the attribute will be parsed according to the return type annotation of the attribute function during access, and will also be parsed according to the type of the first parameter of the assignment function during assignment. If the parsing cannot be completed during assignment or value taking, an error will be thrown.

!!! note

### Apply to entire class

 `@utype.parse` In addition to acting separately on the functions of a class, it can also decorate a class directly, with the effect of turning all non-private functions in the class (functions whose names do not begin with an underscore, excluding `@property`) into analytic functions, such as

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

In `@utype.parse` a decorated class, all functions with names that do not begin with `_` will be used with the same parsing configuration, such as the generator function in `iter_int` the example.

!!! note

Class decorators ** ** in utype

Many of the decorators provided by utype can be applied to classes, but their roles are different.

*  `@utype.apply`: Enforce constraints for custom types
*  `@utype.parse`: Turn all public methods in the class (functions that do not begin with an underscore, not including `@property` properties) into parsing functions
*  `@utype.dataclass` Generates key internal methods in the class (such as `__init__`, `__repr__` `__eq__`, etc.) That give the class the ability to parse initialized data, map initialized data, and assign values. And provide type resolution for the properties of a class, both normal and `@property` attributes

Since these decorators are independent of each other, you can use them in any combination you want.

### Applicable scenarios

Compared with ordinary functions, utype performs additional type conversion, constraint checking and parameter mapping in the call of parsing functions, so it will certainly cause slight call delay, which can be ignored for a single call, but if you need to make a large number of frequent calls, the performance impact of parsing can not be ignored. So utype’s analytic functions are better suited to act on

* Entry function of class library
* API interface function of network programming
* Functions that integrate third-party interfaces or class libraries

Because of the uncertainty of data from users, networks, or third parties, you can use utype in this layer as a guarantee of input validation and type safety. For internal functions in your system or class library that pass parameters more stably and call more frequently, you generally do not need to use utype’s parsing syntax.

 `@utype.parse` When decorating a class, the parsing capability is not applied to all methods, but only to public methods. The purpose of the mechanism is to allow developers to build such a mental model, that is, to suggest that public methods provided to users use the parsing capability provided by utype, while internal methods are judged according to actual needs.

