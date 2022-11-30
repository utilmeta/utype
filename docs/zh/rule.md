


Rule 的作用是施加约束，

```python
from utype import Rule

class PositiveInt(int, Rule):  
    gt = 0

>>> v = PositiveInt('3')
>>> type(v)
<class 'int'>
```

你会发现，

## 嵌套类型声明

* List
* Dict
* Tuple
* Set
等等


## 制造真类型

一般情况下，Rule 都是对基本类型施加约束与参数等，

```python
import utype

@utype.apply(gt=0, le=12)  
class Month(int):  
    @utype.parse
    def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

>>> mon = Month(b'12')
>>> mon.get_days('2020')
```
