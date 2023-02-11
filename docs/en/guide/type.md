# Types and Constraints

## Types in Python

Before we dive into utype, let’s review types and type annotation in Python

!!! note
	If you are familiar with Python type annotation already, please read next chapter directly

In Python, each class ( `class` ) is a type, and when you use `type()` on it's instance, you get the class itself, as shown in
```python
class MyClass:
	pass

my_inst = MyClass()
assert type(my_inst) == MyClass
assert isinstance(my_inst, MyClass)
```

!!! note
	Python is a **strongly typed** **dynamic type** language. Strong typing means that each value has a unique type. every type changes of the value must go through **explicit** type cast. Dynamic typing means that runtime type guarantees are not provided at the language level. For example, functions can accept any type of input parameter

There are some built-in types in Python that we can reference directly without importing, like

*  `int`: integer, such as `1`
*  `float`: Floating-point numbers, such as `3.14`
*  `bool`: Boolean value, such as `True` or `False`
*  `str`: string value, such as   `'text'`
*  `bytes`: Byte string, which stores data as a sequence of binary bytes and can be converted to and from str, such as   `b'binary'`
*  `list`: List, with variable length and elements, such as   `[1, 2]`
*  `tuple`: a tuple whose length is fixed and whose elements cannot be modified, such as   `(1, 'a')`
*  `set`: collection, with unique and unordered internal elements, such as   `{'b', 'a', 'c'}`
*  `dict`: dictionary that provides a mapping of keys to values, such as   `{'a': 1, 'b': 2}`

Some standard libraries also provide common types that we can import directly without installing third-party dependencies, such as

*  `datetime` Date and time library, which provides `datetime`, `date`, `time`, `timedelta` and other types to represent date, time, and duration
*  `enum` Provides a `Enum` type to represent an enumeration value (a value with a fixed range of values)
*  `uuid` Provides the `UUID` type to represent a globally unique identifier
*  `decimal`: Type is provided `Decimal` to represent the number of decimal points
In addition, there are many types provided by the standard library or third-party libraries, here is no need to enumerate all the discussions here

### Type annotation syntax

Python >= 3.6 introduced a type annotation mechanism that can annotate the type of a variable, such as
```python
name: str = 'test'
age: int = 1
```

When you add a type annotation to a variable, the IDE will warn you if you try to access a method or operator that is not supported by the type in your code, which can reduce unnecessary bugs during development.

However, it is important to note that Python itself does not provide guarantees for type annotations, which means that the actual value of a variable may not match the declared type, or may be changed by assignment, such as
```python
age: int = 'nonsense'
age += 1   # TypeError: can only concatenate str (not "int") to str
```

!!! note
	`utype` is based on Python type annotation, and turns the annotation  into a runtime type guarantee that can be relied on

### Nested type
Python also supports the annotation of nested types, such as declaring a list type whose elements are strings.
```python
from typing import Any, List, Dict

class Series:
	names: List[str] = ['n1', 'n2']
	values: List[float] = [0.1, 0.2]
	metadata: Dict[str, Any] = {'version': '0.1.1'}
```

In the example, we can see that typing provided a set of type aliases that support nested operation

*  `List`: declare a list, you need to pass in a type in square brackets that represents the type of its elements.
* `Set`: declare a set, you need to pass in a type in square brackets that represents the type of its elements.
*  `Tuple`: declare a tuple. Multiple types can be passed in square brackets to represent the type of the element at the corresponding position in the tuple.
* `Dict`: declare a dictionary, you need to pass two types in square brackets, representing the type of the key and the type of the value.

If you are using Python 3.9 +, you can directly use `list`, `set` instead of typing aliases to achieve the same effect, such as
```python
from typing import Any

class Series:
	names: list[str] = ['n1', 'n2']
	values: list[float] = [0.1, 0.2]
	metadata: dict[str, Any] = {'version': '0.1.1'}
```

### Special annotations
Python also supports some specia type annotations, such as

* `Union`: use `Union[X, Y]` to indicates that the corresponding value is either of type X or type Y.
* `Optional`: use `Optional[X]` indicates that type X or None are allowed, which is a shortcut for `Union[X, None]`

```python
from typing import Union, Optional

class Form:
	name: str = 'alice'
	address: Optional[str] = None
	phone_number: Union[str, int] = 12345
```

If you’re using Python 3.10 +, the Union type can be declared using the or ( `|` ) operator
```python
class Form:
	name: str = 'alice'
	address: str | None = None
	phone_number: str | int = 12345
```

!!! warning
	`Optional` is not incidating the "required" / "optional" property of a field, this feature is archieved by declaring the `default` or `required` params in [Field configuration](/references/field)

*  `Callable`: declares a callable object, often used to annotate function objects, such as `Callable[[int], str]` representing a function that takes an integer as input to output a string.
*  `Type`: declare the type itself, for example
```python
from typing import Type

class MyClass:
	pass

class Collection:
	int_type: Type[int] = int
	my_type: Type[MyClass] = MyClass
```

*  `Literal`: used to declare a constant or a series of enumeration values, such as
```python
from typing import Literal

class File:
	fmt: Literal['binary'] = 'binary'
	mode: Literal['r', 'rb', 'w', 'wb'] = 'rb'
	opening: Literal[1, True, 'true'] = True
```

### Annotate functions
You can also use type annotation for function arguments and return value in the same way, such as

=== "Python 3.6 and above"
	```python
	from typing import Dict, Optional
	
	password_dict: Dict[str, str] = {}   
	# pretend this is a database that store user passwords
	
	def login(username: str, password: str) -> Optioanl[Dict[str, str]]:
		if password_dict.get(username) == password:
			return {
				'username': username,
			}
		return None
	```  

=== "Python 3.10 and above"
	```python
	password_dict: dict[str, str] = {}
	# pretend this is a database that stores user passwords
	
	def login(username: str, password: str) -> dict[str, str] | None:
		if password_dict.get(username) == password:
			return {
				'username': username,
			}
		return None
	```

!!! note
	Some special functions requires specific annotations, like generator functions or async generator functions, we will discuss it in [Function parsing](/guide/func)

### ForwardRef string

Python supports the use of strings to reference types in the global namespace, which is also called **ForwardRef**, often used in the following cases

**Referencing class itself inside class**

aka "Self-reference", such as
```python
class Comment:
	content: str
	on_comment: 'Comment' = None
	comments: List['Comment']
```

**Referencing to a type that has not been defined**

This usage is common, such as circular references.
```python
class Article:
	title: str
	comments: List['Comment']
	
class Comment:
	content: str
	on_article: Article = None
```

**Referencing globals from tainted locals**

If the name of the type you need to annotate is already occupied in the local namespace, you need to use a string reference to reference it in the global namespace.
```python
from datetime import datetime

class Article:
	str: str = 'placeholder'   # name <str> is occupied
	title: 'str'
	datetime: datetime = datetime.now()
	created_at: 'datetime'
```
!!! warning
	In the above case, if `title` attribute use  `title: str` as type annotation, the actual annotated type is a string `'placeholder'` in the locals, which has no meaning

Note that types that use string references must be defined in the global namespace ( `globals()`), and you cannot use local variables in functions for reference hints, such as
```python
def not_working():
    class Article:
		title: str
		comments: List['Comment']     # will not work properly
		
	class Comment:
		content: str
		on_article: Article = None    # this will work
```

### Further reading
The above documentation lists only the most commonly used syntax and types. If you want to know more about Python type annotation syntax, you can refer to the following documentation.

* <a href="https://docs.python.org/3/library/typing.html" target="_blank">Python Type Annotations Official Documentation</a>
* <a href="https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html" target="_blank">Mypy Type hints cheat sheet</a>


## Constrainted type
In utype, all the validations are around types, utype not only supports parsing Python type annotations, but also supports constraints

The concept of a constraint is very simple. For example, if I need a positive number, or a string with a length between 10 and 20, then I can’t express it using primitive types `int` `str`, but it can be done simply using utype
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

class MyStr(str, Rule):
	min_length = 10
	max_length = 20
```

utype supports declarative constraints. including

* **Range constraints**: constrain the maximum and minimum of the value ( `gt`, `ge`, `lt`, `le`)
* **Length constraints**: constrain the length or length range of the value ( `length`, `max_length`, `min_length`)
* **Constants and enumeration**: constrain value to be a constant or in a fixed values range ( `const`, `enum`)
* **Regex constraints**: constrain value to satisfy certain regular expression (`regex`)
* **Numeric constraints**: constraint the maximum digit length of a numeric value, etc. ( `max_digits`, `decimal_places`)
* **Array constraints**: constrain element uniqueness, contained types for list values ( `unique_items`, `contains`)

!!! note
	For more elaborated constraint params, please refer to [Rule API References](/references/rule)

These built-in constraints can basically cover most use cases, In addition, utype also supports custom constraints and custom verification logic, which we will introduce later.

There are two ways to declare constraints in utype, which we describe below

### Rule mixin
One of the most common ways is to declare a new class, using the source type and the Rule class as the base class, and declare the constraints you need in the attributes of this class, such as
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0
    
num = PositiveInt('3')
print(type(num))
# > <class 'int'>
```
It should be noted here that the result of calling the constrainted type is still the source type, the Rule class only checks the constraints, as in the above example:

* Source Type: `int`
* Constrainted type: `PositiveInt`
* Constraints: `gt=0` (value greater than zero)
* Result type of calling: `int` (source type)

Here is an equation to help understanding:  
**Constrainted-Type = Source-Type + Rule + Constraint-Attributes**

the result of calling a constrainted type is an instance of the source type that satisfy all the constraint validations (otherwise an error is throwed).

The source type does not need to be a base type, but can also be a custom type, such as
```python
import utype

class MonthType(int):
    def get_days(self, year: int) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

class Month(MonthType, utype.Rule):
	gt = 0
	le = 12

mon = Month(b'11')
assert isinstance(mon, MonthType)

print(mon.get_days(2020))
# > 30
```

###  `@utype.apply` decorator
Another way to constrain type is to use a `@utype.apply` decorator, declaring the constraints directly for the target type in decorator parameters, as shown in
```python
import utype

@utype.apply(gt=0, le=12)  
class Month(int):  
    @utype.parse
    def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

mon = Month(b'11')
assert isinstance(mon, Month)

print(mon.get_days('2020'))
# > 30
```

!!! note
	The essence of `@utype.apply` is still an internal Rule mixin

**isinstance detection**

we can use `isinstance(obj, t)` in Python to test whether the object obj is an instance of type t (including instances of subclasses of t), but for constrainted types, this behavior actually detects whether the object is an instance of the source type of the constraint type and satisfies the constraint validations, so
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

print(isinstance(1, PositiveInt))
# > True
print(isinstance(-2, PositiveInt))
# > False
print(isinstance(b'3', PositiveInt))
# > False
```
This feature can be used to check whether a value meets the requirements of a constrainted type

### Built-in constrainted type

utype has already declared some common constrainted types that you can import directly from `utype.types`, such as

* `PositiveInt`: a positive number, excluding 0
* `NaturalInt`: natural number, including 0
* `Month`: number of months, 1 to 12
* `Day`: number of days in a month, from 1 to 31
* `Week`: number of weeks in a year, 1 to 53
* `WeekDay`: day of the week, 1 to 7
* `Quater`: quarter of the year, 1 to 4
* `Hour`: hours of a day, 0 to 23
* `Minute`: minutes of an hour, 0 to 59
* `Second`: seconds of a minute, 0 to 59
* `SlugStr`: String format commonly used for post URLs, consisting of lowercase letters, numbers, and hyphens `-`
* `EmailStr`: a string that meets the requirements of the email address format

In fact, the declaration of these types is very simple, and you can declare and implement them yourself. utype suggests declaring common constraints as constrainted types, so that you can directly refer to them in  type annotation elsewhere.

## Nested type

We can use nested type annotation such as `List[int]`, but it cannot be directly used to convert input data.
utype provides some nested types, using the same syntax as typing, but can be directly used for validation and conversion, such as
```python
import enum  
from utype import types, exc
  
class EnumLevel(str, enum.Enum):  
    info = 'INFO'  
    warn = 'WARN'  
    error = 'ERROR'  
  
level_array = types.Array[EnumLevel]

print(level_array(['INFO', 'WARN']))
# > [<EnumLevel.info: 'INFO'>, <EnumLevel.warn: 'WARN'>]

try:
	level_array(['OTHER'])
except exc.ParseError as e:
	print(e)
	"""
	ParseError: 'OTHER' is not a valid EnumLevel
	"""

value = ('1', True, b'2.3')

print(types.Array[int](value))
# > [1, 1, 2]
```

in the example we declared a `level_array` nested type, using `Array` as the primitive type, where the nested element type is an Enum class, the nested type can be called directly and the data can be parsed and validated

The nested types currently supported by utype are
* `types.Array`: Supports declaration of element types and constraints for list, tuple, set, and other sequence structures. The default source type is `list`
* `types.Object`: Supports declaring element types and constraints for dictionaries, mappings. The default source type is `dict`

You can also inherit these nested types, assign constraints, specify other source types, etc. The usage is similar to Rule (because these nested types also inherit from Rule).
```python
from utype import types

class UniqueTuple(types.Array):  
	__origin__ = tuple
    unique_items = True

unique_tuple = UniqueTuple[int, int, str]
print(unique_tuple(['1', '2', 't']))
# > (1, 2, 't')

try:
	unique_tuple(['1', '1', '3'])
except exc.ParseError as e:
	print(e)
	"""
	ConstraintError: Constraint: <unique_items>: True violated: value is not unique
	"""
```

In the example, we declared `UniqueTuple` by inheriting the nested type `Array`, we use `__origin__` to override the default source type, so that it does not conflict with the default source type of the nested type; we also declared a `unique_items=True` constraint, which indicates that the elements of the input data must be unique

!!! note
	Currently, utype are not using Generic type for nested type, so IDE cannot hint properly for the inner elements, so utype plans to implement some IDE plugins in the further

## Logical operations of type
utype supports logical operations on types using Python’s native logical operators for combining more complex type conditions, such as
```python
from utype import Rule, exc
from typing import Literal

class IntWeekDay(int, Rule):  
	gt = 0
	le = 7

weekday = IntWeekDay ^ Literal['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

assert weekday('6') == 6
assert weekday(b'tue') == 'tue'

try:
	weekday('8')
except exc.ParseError as e:
	print(e)
	"""
	Constraint: <le>: 7 violated;
	Constraint: <enum>: ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun') violated
	"""

from datetime import date

weekday_or_date = weekday | date

assert weekday_or_date(b'5') == 5
assert weekday_or_date('fri') == 'fri'
assert weekday_or_date('2000-1-1') == date(2000, 1, 1)
```

In our example, we declared `weekday` that concatenates `IntWeekDay` with a `Literal` enumeration list using the exclusive-or operator, which means that `weekday` requires input values to match one of the two types. The logical operators supported by utype are

- Or ( `|` ): Data needs to match at least one of these types
- Xor ( `^` ): The data must match one of the criteria, not more than one or zero
- Not ( `~` ): Data must not match the corresponding type
- And ( `&` ): Data must match all types simultaneously

!!! note
	utype can support logical nesting at any level, so technically you can use this syntax to declare any logical conditions, but in practice it is not recommended to use overly complex types, which will make development and debugging difficult

**Common use case: Reverse Selection and Exclusion**

A common use case of logical combination is that a certain type needs to be used, but some values need to be excluded. For example, 0 needs to be excluded as a dividend for `float`. In this case, we can first declare the value to be excluded with a constraint, and then negate it and combine it with the source type to get the excluded type we need.

```python
from utype import Rule, exc
	
class Zero(Rule):
	const = 0

Divisor = float & ~Zero

try:
	Divisor('0')
except exc.ParseError as e:
	print(e)
	"""
	Negate condition: Zero(const=0) is violated
	"""
```

Using and ( `&` ) logic will convert the conditions in order. In the example, we declared `Divisor`, which is a float type excluding 0. When parsing, we will first convert the input data to float, and then to `~Zero`, which fails if value match Zero, otherwise the parsing is done

You can use `enum` constraint to specify excluded enumeration values, such as
```python
from utype import Rule, exc

class Infinity(Rule):  
    enum = [float("inf"), float("-inf")]  
  
FiniteFloat = float & ~Infinity

assert FiniteFloat(b'3.3') == 3.3

try:
	FiniteFloat('inf')
except exc.ParseError as e:
	print(e)
	"""
	Negate condition: Infinity(enum=[inf, -inf]) is violated
	"""
```

### Restrictions and version compat

To use the logical type functionality provided by utype, at least one of the types participating in the logical operation must be a constrainted type of utype, because Python has limited native support for type logical operations.

* `Python < 3.10`: does not support any type of logical operation. Using syntax like `str | int` will result in an error.
* `Python >= 3.10`: Supports the use of the or ( `|` ) operator on types to obtain Union types, which can be used for type annotations but cannot be used for type conversions, and does not support the use of other operators, such as Xor ( `^` ) or not ( `~` ).

However, as long as the constrainted type of utype is used, all logical operator operations can be supported in `Python >= 3.7`, and logical type can not only be used for type annotation, but also be used to parse data

To make life easier, `utype.types` already provide some types corresponding the the primitive types, to be used in logical operations, such as `Int`, `Str`, `Bool`, `Float` etc. you can treat them as "primitive types that support logical operations"
```python
from utype.types import Int

any_of1 = Int | bool | str   # ok
any_of2 = bool | Int | str   # ok

xor_type1 = Int ^ bool ^ str  # ok
xor_type2 = bool ^ Int ^ str  # ok
xor_type3 = bool ^ str ^ Int  # TypeError: unsupported operand type(s) for ^

revert_type = ~int     # TypeError: bad operand type for unary ~: 'type'
revert_type = ~Int     # ok
print(revert_type | xor_type2)
# > AnyOf(Not(Int(int)), OneOf(bool, Int(int), str))
```

!!! warning
	In the logic operation expression, the constrainted type must be at least the first or second element, otherwise the first element and the second element will be combined first, which will throw an error directly if such operation is not supported by Python

It should be noted that only logical types that use utype constrainted type  can provide the conversion functionalities, you cannot use Python native types directly to parse values after logical operation.
```python
try:
	(str | int)('some value')
except TypeError as e:
	print(e)
	# Python >= 3.10
	"""
	Cannot instantiate typing.Union
	"""
	# Python < 3.10
	"""
	unsupported operand type(s) for |: 'type' and 'type'
	"""
```


## Tune type transformation

!!! note
	This is an advanced section for the developer who has mastered utype  and seeking for customization, if you just get started, you can read the next document directly

Python does not provide a safe and effective way to convert any type value to any other type natively . All type conversion logic is provided by utype through conversion functions.
However, each developer may have his/her own preference for the strictness of type conversion method. Therefore, utype’s type conversion mechanism provides multiple adjustable preference parameters, and supports dynamic registration, which we will mainly introduce in this section.


### Register type transformer

In utype, each type is converted through type transformer functions, but these functions are not fixed, and can be registered flexibly, such as

```python
from utype import Rule, Schema, register_transformer
from typing import Type

class Slug(str, Rule):  
    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"

@register_transformer(Slug)
def to_slug(transformer, value, t: Type[Slug]):
	str_value = transformer(value, str)
	return t('-'.join([''.join(
	filter(str.isalnum, v)) for v in str_value.split()]).lower())


class ArticleSchema(Schema):
	slug: Slug

print(dict(ArticleSchema(slug=b'My Awesome Article!')))
# > {'slug': 'my-awesome-article'}
```

The registered transformer function does not affect the behavior of the method of the class `__init__`,  In the following scenario, the conversion function is called

* Parsing the source type of a constrainted type
* Parsing a field of dataclass with certain type
* Parsing a param of function with certion type

When parsing a field/parameter, if the type of the data is exactly the same as the declared type ( `type(data) == t`), the parsing will be skipped directly, otherwise, the transformer function will be resolved for calling

!!! note
	if the transformer function cannot be found for certain type, that type is called an unresolved type, you can tune it's behaviour by the param `unresolved_types` of [Options - tuning parse](/references/options)

The parameters to register the decorator `@register_transformer` are as follows

* `*classes` pass the type classes to be registered
* `allow_subclasses`: whether to accept subclasses. The default is True. If True, `*classes` subclasses in will also apply the same transformer function if they are not registered.
* `metaclass`: pass in a metaclass to specify the transformer function for all instance types of the metaclass.
* `attr`: pass in an attribute name specifies the transformer function for all classes that have that attribute.
* `detector`: pass in a detection function, and the transformer function is specified for all classes satisfying the detection.
* `priority`: specify the priority of the conversion function. The higher it is, the higher it is used. By default, the later it is registered, the higher its priority is.
* `to`: You can specify the `TypeTransformer` subclass where the converter is registered . By default, the converter you register is global. Specifying a `TypeTransformer` subclass will only register for this class. You can declare a transformer class of type in Options.

By default, the later the converter is registered, the higher the priority, so it can achieve the effect of “override”.

!!! warning
	You cannot register for nested types, such as `Union[int, str]` or `List[int]`

### Compat other libraries

With the registration capability of type transformer, utype can be compatible with other class libraries by registering transformer functions.

#### Compat `pydantic`

`pydantic` is a data parsing and validation library, which also has the ability of type conversion and constraint validation. it's BaseModel is similar to the dataclass (Schema/DataClass) in utype.

Transformer function to compat `pydantic` is as follows
```python
from utype import register_transformer  
from collections.abc import Mapping  
from pydantic import BaseModel  
  
@register_transformer(BaseModel)  
def transform_pydantic(transformer, data, cls):  
    if not transformer.no_explicit_cast and not isinstance(data, Mapping):  
        data = transformer(data, dict)  
    return cls(**data)
```

#### Compat `attrs`

`attrs` is a library that simplifies class declarations, allowing you to map initialization parameters to attributes without declaring `__init__` functions, but does not have the ability to convert type and validate constraints

Transformer function to compat `attrs` is as follows
```python
from utype import register_transformer  
from collections.abc import Mapping  

@register_transformer(attr='__attrs_attrs__')  
def transform_attrs(transformer, data, cls):  
    if not transformer.no_explicit_cast and not isinstance(data, Mapping):  
        data = transformer(data, dict)
    names = [v.name for v in cls.__attrs_attrs__]  
    data = {k: v for k, v in data.items() if k in names}  
    return cls(**data)
```

#### Compat `dataclasses`

`dataclasses` is a standard library for Python, similar to `attrs`, which also provides convenient methods for initializing classes, but also without the ability for type conversion

Transformer function to compat `dataclasses` is as follows

```python
from utype import register_transformer  
from collections.abc import Mapping  

@register_transformer(attr='__dataclass_fields__')  
def transform_dataclass(transformer, data, cls):  
    if not transformer.no_explicit_cast and not isinstance(data, Mapping):  
        data = transformer(data, dict)
    data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}  
    return cls(**data)
```

