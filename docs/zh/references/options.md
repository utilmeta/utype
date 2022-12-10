# Options 解析选项


## 类型转化选项

* `transformer_cls`
* `no_explicit_cast`
* `no_data_loss`
* `unresolved_types`

## 数据处理选项

* `addition`


* `max_depth`：限制数据嵌套的最大深度

这个参数主要用于限制自引用或循环引用的数据结构，避免出现递归栈溢出

* `max_params`
* `min_params`

**与长度约束的区别**

虽然使用 Rule 约束参数的  `max_length` 和 `min_length` 也能够约束字典的长度，但是它们与 `max_params` / `min_params` 在作用上是有区别的

`max_params` / `min_params` 是在所有的字段解析开始之前对输入数据进行的校验，其中 `max_params` 是为了避免输入数据过大而耗费解析资源

而  `max_length` / `min_length` 在作用于数据类中，是用于在所有字段解析结束后，用于限制 **输出** 的数据的长度

并且 `max_params` / `min_params` 可以用于限制函数参数的输入， `max_length` / `min_length` 只能限制普通类型和数据类

## 错误处理

* `collect_errors`
* `max_errors`

### 非法数据处理

* `invalid_items`
* `invalid_keys`
* `invalid_values`

## 解析行为调节

* `ignore_required`
* `force_required`
* `no_default`
* `force_default`
* `ignore_constraints`
* `ignore_no_input`
* `ignore_no_output`
* `ignore_alias_conflicts`
* `ignore_dependencies`


## 字段生成选项

* `case_insensitive`
* `alias_generator`
* `alias_from_generator`


### 命名风格转化

不同的编程语言或开发者都可能有着不同的习惯命名风格，而如果你需要提供

比如在 Python 中一般使用小写和下划线方式命名字段，

```python
class Article:
	liked_num: int = Field(alias='likedNum') 
	created_at: str = Field(alias='createdAt')
```

在 `utype.utils.style.AliasGenerator` 中 提供了一些常用的能够生成各种命名风格字段的别名生成函数

* `camel`：驼峰命名风格，如 `camelCase`
* `pascal`：帕斯卡命名风格，或称首字母大写的驼峰命名，如 `PascalCase`
* `snake`：小写下划线命名风格，python 等语言的推荐变量命名风格，如 `snake_case`
* `kebab`：小写短横线命名风格，如 `kebab-case`
* `cap_snake`：大写下划线命名风格，常用于常量的命名，如 `CAP_SNAKE_CASE`
* `cap_kebab`：大写短横线命名风格，如 `CAP-KEBAB-CASE`

```python
from utype.utils.style import AliasGenerator

class ArticleSchema(Schema):
    __options__ = Schema.Options(
        alias_from_generator=[
            AliasGenerator.kebab,
            AliasGenerator.pascal,
        ],
        alias_generator=AliasGenerator.camel
    )

	slug: str
	liked_num: int
	created_at: datetime

data = {
	'Slug': 'my-article',                # pascal case
	'LikedNum': '3',                     # pascal case
	'created-at': '2022-03-04 10:11:12'  # kebab case
}
article = ArticleSchema(**data)
print(article)

print(dict(article))
# {
#	'slug': 'my-article',
#	'likedNum': 3,
#	'createdAt': datetime.datetime(2022, 3, 4, 10, 11, 12)
# }
```

你可以灵活运用别名转化函数来接受不同命名风格的参数字段，并转化为统一的命名风格

### 用于函数



## 属性控制
* `secret_names`
* `immutable`

## 运行时
* `allow_runtime_options`