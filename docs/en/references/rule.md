# Rule - constraint type
In utype, the role of Rule is to impose constraints on types, and we will explain its use in detail in this document.

## Built-in constraints
The Rule class has a series of built-in constraints. When you inherit from Rule, you only need to declare the constraint name as an attribute to get the ability of the constraint. Rule currently supports the following built-in constraints

### Range constraint
Range constraints are used to limit the range of data, such as maximum, minimum, and so on. They include

 *  `gt`: The input value must be greater than `gt` the value
 *  `ge`: The input value must be greater than or equal to `ge` the value
 *  `lt`: The input value must be less than `lt` the value
 *  `le`: The input value must be less than or equal to `le` the value
```python
from utype import Rule, exc

class WeekDay(int, Rule):  
    ge = 1  
    le = 7

assert WeekDay('3.0') == 3

try:
	WeekDay(8)
except exc.ConstraintError as e:
	print(e) 
	"""
	Constraint: <le>: 7 violated
	"""
```

!!! warning
	
Range constraints are not restricted to types, and can be supported as long as the type declares a corresponding comparison method ( `__gt__`, `__ge__`, `__lt__`, `__le__`), such as

```python
from utype import Rule, exc
from datetime import datetime

class Year2020(Rule, datetime):  
    ge = datetime(2020, 1, 1)  
    lt = datetime(2021, 1, 1)

assert Year2020('2020-03-04') == datetime(2020, 3, 4) 

try:
	Year2020('2021-01-01')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <lt>: datetime.datetime(2021, 1, 1, 0, 0) violated
	"""
```

!!! note


### Length constraint
Range constraints are used to limit the length of data and are typically used to validate data such as strings or lists, including

*  `length`: Length of input data must be equal to `length` value
*  `max_length`: The length of the input data must be less than or equal to `max_length` the value of
*  `min_length`: The length of the input data must be greater than or equal to `min_length`
```python
from utype import Rule, exc

class LengthRule(Rule):
	max_length = 3
	min_length = 1

assert LengthRule([1, 2, 3]) == [1, 2, 3]

try:
	LengthRule('abcde')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_length>: 3 violated
	"""
```

All length constraints must be positive integers. If is `length` set, or cannot be set again.

!!! note


### Regex constraints
Regular expressions are often able to declare richer string validation rules for many purposes. Regular constraints are as follows

*  `regex` Specifies a regular expression that the data must exactly match
```python
from utype import Rule, exc

class Email(str, Rule):  
    regex = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"

assert Email('dev@utype.io') == 'dev@utype.io'

try:
	Email('invalid#email.com')
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <regex>: 
	'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\\.[A-Z|a-z]{2,})+' violated
	"""
```

In the example, we declare a constraint type Email that is used to validate email addresses.

### Const and enum

*  `const`: value is a constant value. The input data must all equal the constant.
```python
from utype import Rule, exc

class Const1(Rule):
	const = 1

class ConstKey(str, Rule):
	const = 'SECRET_KEY'

assert ConstKey(b'SECRET_KEY') == 'SECRET_KEY'

try:
	Const1(True)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <const>: 1 violated
	"""
```

If you specify a source type for a constant constraint, the Rule performs the type conversion first and then checks whether the constant is equal, otherwise it makes a direct comparison

It’s worth noting that Python’s congruence symbol ( `==`) `const` not only verifies that a value is “equal” to a constant, but also that their types are equal, because in Python, a type can be made equal to any value by `__eq__` a method. For example `True == 1`, is true, and True is `bool` of type, 1 is of `int` type (a `int` subclass of in Python `bool`), So it can’t pass the `const` verification.

*  `enum` You can pass in a list, a collection, or an Enum class. The data must be within `enum` the specified value range.
```python
from utype import Rule, exc

class Infinity(float, Rule):  
    enum = [float("inf"), float("-inf")]

assert Infinity('-infinity') == float("-inf")

try:
	Infinity(10.5)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <enum>: [inf, -inf] violated
	"""
```

!!! warning

!!! note

### Numeric constraints
Numeric constraints are used to place restrictions on numeric types (int, float, Decimal), including

*  `max_digits`: Limit the maximum number of digits in a number (excluding the sign bit or decimal point)
*  `multiple_of`: The number must be a `multiple_of` multiple of the specified number
```python
from utype import Rule, exc

class Hundreds(int, Rule):
	max_digits = 3
	multiple_of = 100

assert Hundreds('200') == 200

try:
	Hundreds(1000)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_digits>: 3 violated
	"""

try:
	Hundreds(120)
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <multiple_of>: 100 violated
	"""
```

!!! note

*  `decimal_places` Limit the maximum number of digits in the decimal part of a number to this values
```python
from utype import Rule, exc
import decimal

class ConDecimal(decimal.Decimal, Rule):  
    decimal_places = 2  
    max_digits = 4

assert ConDecimal(1.5) == decimal.Decimal('1.50')

try:
	ConDecimal(123.4)   
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_digits>: 4 violated
	"""

try:
	ConDecimal('1.500')   
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <decimal_places>: 2 violated
	"""
```

If the source type of the constraint is fixed-point number `decimal.Decimal`, when the decimal digits of the input data are insufficient, it will be completed first, so the data `123.4` will be completed first `Decimal('123.40')`, and then the verification `max_digits` will not pass.

And if the incoming data contains a decimal place, it will be calculated whether the end is 0 or not, for example `Decimal('1.500')`, 3 digits will be calculated according to the decimal place of the fixed-point number.

!!! warning

### Array constraint
Array constraints are used to constrain lists, tuples, sets, and other data that can traverse a single element, including

*  `contains`: Specifies a type, which can be a normal type or a constraint type. The data must contain matching elements.
*  `max_contains`: The maximum number of elements of the matching `contains` type
*  `min_contains`: Minimum number of elements of match `contains` type
```python
from utype import Rule, exc

class Const1(int, Rule):
	const = 1

class ConTuple(tuple, Rule):
	contains = Const1
	max_contains = 3

assert ConTuple([1, True]) == (1, True)

try:
	ConTuple([0, 2]) 
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <contains>: Const1(int, const=1) violated: 
	Const1(int, const=1) not contained in value
	"""

try:
	ConTuple([1, True, b'1', '1.0'])
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <max_contains>: 3 violated: 
	value contains 4 of Const1(int, const=1), 
	which is bigger than max_contains
	"""
```

The constraint of `contains` type ConTuple in the example specifies a type of 1 converted to an integer, and the maximum number `max_contains` of matches is 3, so if no element in the data matches the type of Const1, or if the number of matched elements exceeds 3, an error will be thrown

!!! note

*  `unique_items`: Does the element need to be unique
```python
from utype import Rule, exc, types

class UniqueList(types.Array):
	unique_items = True

assert UniqueList[int]([1, '2', 3.5]) == [1, 2, 3]

try:
	UniqueList[int]([1, '1', True])
except exc.ConstraintError as e:
	print(e)
	"""
	Constraint: <unique_items>: True violated: value is not unique
	"""
```

In the example, we use `UniqueList[int]` conversion, so we will convert the element type first, and then check the constraint.

!!! note


### Lax constraint

Lax constraint (aka loose constraint, transformational constraint) refers to a kind of constraint that is not strict, and its effect is to transform the input data to the goal satisfying the constraint as much as possible.

Declaring a relaxed constraint simply requires importing `Lax` the class from the utype and wrapping the constraint value in Lax, as shown in
```python
from utype import Rule, Lax

class LaxLength(Rule):
	max_length = Lax(3)

print(LaxLength('ab'))
# > ab

print(LaxLength('abcd'))
# > abc
```

In the example, when the input `'abcd'` does not meet the loose constraint `max_length`, it will be truncated directly according to `max_length` the length of the data and output `'abc'`, instead of throwing an error directly like the strict constraint.

Different constraints behave differently in the loose mode. The constraints supported by the loose mode and their respective behaviors are

*  `max_length`: Defines a loose maximum length, truncating to the given maximum length if the value is longer than it.
*  `length`: If the data is greater than this length, it is truncated to `length` the corresponding length. If the data is less than this length, an error is thrown.
*  `ge` If the value is less than `ge`, output `ge` the value of directly, otherwise use the input value
*  `le` If the value is greater than `le`, the value of is output `le` directly, otherwise the input value is used
*  `decimal_places`: Instead of checking the decimal place, the decimal place is reserved directly `decimals_places`, which is consistent with the effect of Python’s `round()` built-in method.
*  `max_digits` If the number of digits exceeds the maximum number of digits, round off the decimal places from the smallest to the largest, and throw an error if it still cannot be satisfied.
*  `multiple_of`: If the data is not `multiple_of` an integer multiple of, the value of an integer multiple of the nearest input data that is smaller than the input data is taken.
*  `const`: Direct output constant
*  `enum`: If the data is not within the range, the first value of the range will be output directly
*  `unique_items`: If the data is duplicated, the deduplicated data will be returned

General constraints are only used for verification, but loose constraints may convert the input data. Although information loss may occur during the conversion, loose constraints will also ensure that the conversion is ** Idempotent **, that is, the value obtained from a data after multiple conversions is the same as that obtained from a single conversion
