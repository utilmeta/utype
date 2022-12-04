# 解析器接口

在 utype 中，对于数据类和函数的解析都是由解析器完成的，

* `BaseParser`
* `FunctionParser`：解析函数
* `ClassParser`：解析数据类

你可以通过继承这些解析器自定义和扩展解析行为与功能