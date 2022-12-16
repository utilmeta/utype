# Types and Constraints

## Types in Python

Before we get into the use of utype, let’s review types and type annotation syntax in Python!!! note

In Python, each class ( `class`) is a type, and when you call an instance of it with a `type` function, you get the class itself, as shown in
```python
class MyClass:
	pass

my_inst = MyClass()
assert type(my_inst) == MyClass
assert isinstance(my_inst, MyClass)
```

!!! note

There are already built-in types in Python that we can reference directly without importing, such as

*  `int`: integer, such as `1`
*  `float` Floating-point numbers, such as
*  `bool` Boolean value, such as `True` true or `False` false
*  `str`: string, such as
*  `bytes` Byte string, which stores data as a sequence of binary bytes and can be converted to and from str, such as
*  `list` List, with variable length and elements, such as
*  `tuple`: a tuple whose length is fixed and whose elements cannot be modified, such as
*  `set`: collection, with unique and unordered internal elements, such as
*  `dict`: dictionary that provides a mapping of keys to values, such as

Some standard libraries also provide common types that we can import directly without installing third-party dependencies, such as

*  `datetime` Date and time library, which provides `datetime`, `date`, `time`, `timedelta` and other types to represent date, time, and duration
*  `enum` Provides a `Enum` type to represent an enumeration value (a value with a fixed range of values)
*  `uuid` Provides the `UUID` type to represent a globally unique identifier
*  `decimal`: Type is provided `Decimal` to represent the number of decimal points
In addition, there are many types provided by the standard library or third-party libraries, which are not listed here.

### Type annotation syntax

Python versions after 3.6 introduced a type annotation mechanism that can declare the type of a variable, such as
```python
name: str = 'test'
age: int = 1
```

When you add a type annotation to a variable, the IDE will warn you if you try to access a method or operation that is not supported by the type in your code, which can reduce unnecessary bugs during development.

However, it is important to note that Python itself does not provide guarantees for type annotations, which means that the actual value of a variable may not match the declared type, or may be changed by assignment, such as
```python
age: int = 'nonsense'
age += 1   # TypeError: can only concatenate str (not "int") to str
```

!!! note

### Nested type
In addition to annotating directly with the type itself, Python also supports the syntax of nested types for more scenarios, such as declaring a list type whose elements are strings.
```python
from typing import Any, List, Dict

class Series:
	names: List[str] = ['n1', 'n2']
	values: List[float] = [0.1, 0.2]
	metadata: Dict[str, Any] = {'version': '0.1.1'}
```

We first introduced the components needed to declare nested types from the typing standard library, which `Any` represent unfixed types and allow arbitrary values, and the nested types provided by typing are commonly used.

* To `List` declare a list, you need to pass in a type in square brackets that represents the type of its elements.
* To `Set` declare a collection, you need to pass in a type in square brackets that represents the type of its elements.
*  `Tuple`: Declare a tuple. Multiple types can be passed in square brackets to represent the type of the element at the corresponding position in the tuple.
* To `Dict` declare a dictionary, you need to pass two types in square brackets, representing the type of the key and the type of the value.

If you are using Python 3.9 +, you can directly use `list` types such as, `set` instead of typing provided components to achieve the same effect, such as
```python
from typing import Any

class Series:
	names: list[str] = ['n1', 'n2']
	values: list[float] = [0.1, 0.2]
	metadata: dict[str, Any] = {'version': '0.1.1'}
```

### Special note type
In addition to the above type annotations, Python also supports some common special annotation types, such as

* The syntax that `Union` can be used `Union[X, Y]` indicates that the corresponding value is either of type X or type Y.
*  `Optional`: `Optional[X]` is `Union[X, None]` actually a shorthand for to indicate that X types and None values are allowed.

```python
from typing import Union, Optional

class Form:
	name: str = 'alice'
	address: Optional[str] = None
	phone_number: Union[str, int] = 12345
```

If you’re using Python 3.10 +, the Union type can be declared using the more concise or ( `|`) operator
```python
class Form:
	name: str = 'alice'
	address: str | None = None
	phone_number: str | int = 12345
```

!!! warning

*  `Callable`: Declares a callable object, often used to annotate function objects, such as `Callable[[int], str]` representing a function that converts an integer to a string.
*  `Type`: declare a type itself, as in
```python
from typing import Type

class MyClass:
	pass

class Collection:
	int_type: Type[int] = int
	my_type: Type[MyClass] = MyClass
```

*  `Literal`: Used to declare a constant or a series of enumeration values, such as
```python
from typing import Literal

class File:
	fmt: Literal['binary'] = 'binary'
	mode: Literal['r', 'rb', 'w', 'wb'] = 'rb'
	opening: Literal[1, True, 'true'] = True
```

### Function type annotation
You can also use type hinting for function arguments and return values in the same way in functions, such as

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
	password_dict: Dict[str, str] = {}
	# pretend this is a database that store user passwords
	
	def login(username: str, password: str) -> dict[str, str] | None:
		if password_dict.get(username) == password:
			return {
				'username': username,
			}
		return None
	```

!!! note

### Type reference string
In the type declaration, in addition to passing in the reference of the type itself, you can also pass in the name string of the type defined in the global namespace for annotation, which is mainly used for

The class itself is ** referenced in the ** class attribute

Self-reference for short, such as
```python
class Comment:
	content: str
	on_comment: 'Comment' = None
	comments: List['Comment']
```

** Reference to a type ** that has not been defined

This usage is common, such as circular references.
```python
class Article:
	title: str
	comments: List['Comment']
	
class Comment:
	content: str
	on_article: Article = None
```

** The type that needs to be referenced has been tainted in the local space **

For example, if the name of the type you need is already occupied in the local namespace, you can use a string reference to refer to the corresponding type in the global namespace.
```python
from datetime import datetime

class Article:
	str: str = 'placeholder'
	title: 'str'
	datetime: datetime = datetime.now()
	created_at: 'datetime'
```
!!! warning

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

### Extension data
The above documentation lists only the most commonly used syntax and types. If you want to know more about Python type annotation syntax, you can refer to the following documentation.

* <a href="https://docs.python.org/3/library/typing.html" target="_blank"> Python Type Annotations Official Documentation</a>
* <a href="https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html" target="_blank">Mypy Type hints cheat sheet</a>


## Constraint type
In utype, all the validation and parsing conversions are around types, and utype supports the Python type annotation syntax mentioned in the previous section to perform conversions on types, as well as to impose

The concept of a constraint is very simple. For example, if I need a positive number, or if I need a string with a length between 10 and 20, then I can’t express it using primitive types `int` `str`, but using utype can be done with the following short declaration.
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

class MyStr(str, Rule):
	min_length = 10
	max_length = 20
```

Utype supports the use of declarative syntax to impose common constraints on types. The constraints currently supported by utype include

* ** Range constraint **: Maximum of constraint value, minimum ( `gt`, `ge`, `lt`, `le`)
* ** Length constraint **: The length or length range of the constraint value ( `length`, `max_length`, `min_length`)
* ** Constants and enumeration constraints **: Constraint value must be a constant or in a fixed range ( `const`, `enum`)
* ** Regular constraints **: The constraint value must satisfy a regular expression ( `regex`)
* ** Numeric constraints **: Constraints on the maximum digit length of a numeric value, the number of digits reserved, etc. ( `max_digits`, `round`)
* ** List constraints **: Constraints list values on element uniqueness, contained types, etc. ( `unique_items`, `contains`)

!!! note

These built-in constraints can basically cover most common scenarios. In addition, utype also supports custom constraints and custom verification logic, which we will introduce later.

There are two ways to impose constraints on types in utype, which we describe below

### Rule mixes in inheritance
One of the most common ways is to declare a new class, using the source type and the Rule class as the base class, and declare the constraints you need in the attributes of this class, such as
```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0
    
num = PositiveInt('3')
print(type(num))
# > <class 'int'>
```
It should be noted here that the result of calling the constraint type mixed with Rule is still the source type, and the Rule class only checks the constraint, such as in the above example.

* Source Type: `int`
* Constraint type: `PositiveInt`
* Constraint: `gt=0` (value greater than zero)
* Result type of call: `int` (source type)

Therefore, it can be understood ** Constraint Type = Source Type + Rule Class + Constraint Attribute ** that the result of calling a constraint type is ** Conform to the constraint ** an instance of the source type (an error is thrown if the constraint is not met or the conversion cannot be completed).

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

###  `@utype.apply` Decorator
Another way to impose a constraint on a type is to use a `@utype.apply` decorator, declaring the constraint directly for the target type as a decorator parameter, as shown in
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

print(mon.get_days(2020))
# > 30
```

!!! note

** isinstance detection **

In Python, it is generally used `isinstance(obj, t)` to test whether the object obj is an instance of type t (including instances of subclasses of t), while for constraint types, this behavior actually detects whether the object is an instance of the source type of the constraint type and satisfies the constraint conditions, so
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
This feature can be used to check whether a value meets the requirements of a constraint type

### Built-in constraint type

The utype has already declared some common constraint types that you can reference directly from `utype.types`, such as

* Positive Int: a positive number, excluding 0
* Natural Int: natural number, including 0
* Month: Number of months, 1 to 12
* Day: The number of days, from 1 to 31
* Week: Number of weeks, 1 to 53
* WeekDay: Day of the week, 1 to 7
* Quater: Quarter, 1 to 4
* Hour: hours, 0 to 23
* Minute: minutes, 0 to 59
* Second: seconds, 0 to 59
* SlugStr: String format commonly used for post URLs, consisting of lowercase letters, numbers, and hyphens `-`
* EmailStr: a string that meets the requirements of the mailbox address format

In fact, the declaration of these types is very simple, and you can declare and implement them yourself. Utype suggests declaring common constraints as fixed constraint types, so that you can directly refer to them in code for type annotation.

## Nested type

We know that a nested type can be declared in a type annotation using syntax such as `List[int]`, but it cannot be directly used as a type that can be converted and verified. Utype provides some types that can be nested, providing a declaration consistent with the syntax of the type annotation, but the declared type can be directly used for verification and conversion, such as
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

As you can see, in the example we declare a `level_array` nested type named, using `Array` as the primitive type, where the nested element type is an enumeration class, the nested type can be called directly and the data can be parsed and converted

The nested types currently supported by utype are
*  `types.Array`: Supports declaration of element types and constraints for list, tuple, set, and other sequence structures. The default source type is
*  `types.Object`: Supports declaring element types and constraints for dictionaries, mappings. The default source type is

You can inherit these nested types, assign constraints, specify other source types, etc. The usage is similar to Rule (because these nested types also inherit from Rule).
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

For nested type inheritance, we use `__origin__` the attribute to override the default source type instead of the inheritance method, so that it does not conflict with the default source type of the nested type.

!!! note


## Logical operation of type
Utype supports logical operations on types using Python’s native logical operators for combining more complex type conditions, such as
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

In our example, we declared `weekday` a type that concatenates IntWeekDay with a Literal enumeration list using the exclusive-or operator, which means that `weekday` the type requires input values to match one of the two types. The logical operators supported by utype are

- Or ( `|`): Data needs to match at least one of these types
- Xor ( `^`): The data must match one of the criteria, not more than one or zero
- Not ( `~`): Data must not match the corresponding type
- And ( `&`): Data must match all types simultaneously

!!! note

** Common Scenario: Reverse Selection and Exclusion **

A common scenario of logical combination is that a certain type needs to be used, but some values need to be excluded. For example, 0 needs to be excluded as a dividend. In this case, we can first declare the value to be excluded with a constraint, and then negate it and combine it with the source type to get the excluded type we need.

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

Using and ( `&`) logic will convert the conditions in order. In the example, we declare a dividend type Divisor, which is a float type excluding 0. When parsing, we will first convert the input data to float, and then determine whether the matching of Zero can be completed. The parsing fails (because the corresponding condition is not), otherwise the parsing succeeds

In addition to using `const` constraints to exclude a value, you can use `enum` constraints to specify excluded enumeration values, such as

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

### Restrictions are compatible with the version

It is important to note that to use the logical type functionality provided by utype, at least one of the types participating in the logical operation must be a constraint type that uses utype, because Python has limited native support for type logical operations.

*  `Python < 3.10`: does not support any type of logical operation. Using `str | int` this syntax will result in an error.
*  `Python >= 3.10`: Supports the use of the or ( `|`) operator on types to obtain Union types, which can be used for type annotations but cannot be used for type conversions, and does not support the use of other operators, such as Xor ( `^`) or not ( `~`).

However, as long as the constraint type of utype is used, all logical operator operations can be supported in the `Python >= 3.7` above, and the declared type can not only be used for type annotation, but also be directly parsed and converted

For ease of declaration, `utype.types` some constraint types that do not contain constraint attributes have been provided in, such as `Int`, `Str`, `Bool`, `Float` etc. You can use them directly as ** Capable of participating in logical operations. ** base types.

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


It should be noted that only logical types that use utype constraint type participation can provide the conversion function according to logical conditions, and you cannot directly use Python native types to perform or call values after operation.
```python
(str | int)('some value')
# Python >= 3.6 TypeError: unsupported operand type(s) for |: 'type' and 'type'
# Python >= 3.10 TypeError: Cannot instantiate typing.Union
```


## Regulation and extended type transformation

!!! note


Python natively does not provide a safe and effective way to convert any type value to any other type. All type conversion logic is provided by utype through conversion functions. However, each developer may have his own preference for the strictness of type verification and conversion method. Therefore, utype’s type conversion mechanism provides multiple adjustable preference parameters, and supports dynamic registration, coverage, and extension of type conversion functions, which we will mainly introduce in this section.


### Register type conversion function

In utype, each type is converted through type conversion functions, but these functions are not fixed, but can be registered flexibly, such as

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

The registered conversion function does not affect the behavior of the method of the class `__init__`, because the conversion of the converter occurs at the initialization ** Before ** of the class. In the following scenario, the conversion function is called

* When resolving the source type of a constraint type
* When a field of a data class is resolved
* When analyzing the parameters of a function

When the corresponding field/parameter is resolved, if the type of the data is exactly the same as the declared type ( `type(data) == t`), the resolution will be skipped directly, otherwise, the conversion function will be sought for calling

!!! note

The parameters to register the decorator `@register_transformer` are as follows

* Register a conversion function for a list of classes `*classes` passed in
*  `allow_subclasses`: Whether to accept subclasses. The default is True. If True, `*classes` subclasses in will also apply the same conversion function if they are not registered.
*  `metaclass`: Pass in a metaclass to specify the conversion function for all instance types of the metaclass.
*  `attr` Passing in an attribute name character specifies the conversion function for all classes that have that attribute.
*  `detector`: a detection function is passed in, and the conversion function is specified for all classes satisfying the function detection.
*  `priority`: Specify the priority of the conversion function. The higher it is, the higher it is used. By default, the later it is registered, the higher its priority is.
*  `to`: You can specify the class where the converter is registered `TypeTransformer`. By default, the converter you register is global. Specifying a `TypeTransformer` subclass only works for this class. You can declare a conversion class of type in Options.

By default, the later the converter is registered, the higher the priority, so it can achieve the effect of “overwrite”.

!!! warning

### Compatible with other class libraries

With the registration capability of type conversion, we can be compatible with other class libraries by registering conversion functions.

#### Compatible `pydantic`

Pydantic is a data parsing and validation library, which also has the ability of type conversion and constraint validation. BaseModel is similar to the data class in utype.

Compatible `pydantic` conversion functions are as follows
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

#### Compatible `attrs`

Attrs is a library that simplifies class declarations, allowing you to map initialization parameters to attributes without declaring `__init__` functions, but does not have the ability to type resolve and check constraints

Compatible `attrs` conversion functions are as follows
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

#### Compatible `dataclasses`

The dataclasses is a standard library for Python, similar to attrs, which also provides convenient methods for initializing classes, but again without the ability for type resolution

The following function registers the type of the class that uses `@dataclasses.dataclass` the decoration, which completes the compatibility of the dataclasses library.

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

