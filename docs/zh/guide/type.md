# 类型的声明与约束


## 约束类型

约束类型可以看作是 **源类型**+**约束条件** 组成的

源类型通过


### 类型的逻辑运算
utype 支持 Python 的原生逻辑运算符，能够对类型与数据结构进行逻辑运算，包括

- 和（&）：数据必须同时满足所有条件（AllOf）
- 或（|）：数据需要至少满足其中的一个条件（AnyOf）
- 异或（^）：数据必须满足其中的一个条件，不能是多个或0个（OneOf）
- 非（~）：数据必须不满足类型的条件（Not）


## 真类型

约束类型转化的结果是满足约束的源类型实例，但如果你需要声明一个类型，

### 为真类型施加约束

第一种方式就是把你需要的真类型作为新的约束类型的源类型，虽然说起来比较绕，但实现上很简单：
```python
import utype

class MonthType(int):
	@utype.parse
    def get_days(self, year: int = utype.Field(ge=2000, le=3000)) -> int: 
        # you will get 'year' of int type and satisfy those constraints 
        from calendar import monthrange  
        return monthrange(year, self)[1]

class Month(MonthType, utype.Rule):
	gt = 0
	le = 12

mon = Month(b'11')
assert type(mon) == MonthType

print(mon.get_days('2020'))
```

第二种方式是使用 `@utype.apply` 装饰器，直接为目标类型声明约束，如
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
assert type(mon) == Month

print(mon.get_days('2020'))
```


## TypeTransformer

### 注册转化器

* `*classes`
* `metaclass`
* `attr`
* `detector`
* `allow_subclasses`
* `priority`
* `to`：可以指定转换器注册的 `TypeTransformer` 类，默认情况下你注册的转化器是全局的，指定一个  `TypeTransformer`  子类后仅对这个类生效，你可以在 Options 中声明类型的转化类

默认情况下，越晚注册的转换器优先级越高，所以能够实现 “覆盖” 的效果


## ForwardRef 类型引用


ForwardRef 会在