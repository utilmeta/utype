# uType

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

utype 是一个基于 Python 类型注解的数据类型声明与解析库，能够在运行时根据你声明的类型和数据结构对数据进行解析转化

* 版本：`0.1.1`【内测】
* 中文官方文档：[https://utype.io/zh](https://utype.io/zh)
* 源码仓库：[https://github.com/utilmeta/utype](https://github.com/utilmeta/utype)


### 核心特性

* 基于 Python 类型注解在运行时对类型，数据结构，函数参数与结果等进行解析转化
* 支持类型约束，类型的逻辑运算等，以声明更复杂的解析条件
* 高度可扩展，所有类型的转化函数都可以注册，覆盖与扩展，并提供高度灵活的解析选项
* 支持输出 json-schema 格式的文档，兼容 OpenAPI 

### 安装

```shell
pip install -U utype
```

utype 需要 Python >= 3.7，无其他第三方依赖

### 用法示例

更多用法请参考官方文档：[https://utype.io/zh](https://utype.io/zh)

### RoadMap 与贡献

utype 还在成长中，目前规划了以下将在新版本中实现的特性

* 完善解析错误的处理机制，包括错误处理钩子函数等
* 支持命令行参数的声明与解析
* 支持 Python 泛型，类型变量等更多类型注解语法
* 开发 Pycharm / VS Code 插件，支持对约束，逻辑类型和嵌套类型的 IDE 检测与提示
* 从 json-schema 生成 utype 数据类代码

也欢迎你来贡献 feature 或者提交 issue ~

### 用户交流与答疑

中文答疑 QQ 群：

### 开源协议

Apache 2.0