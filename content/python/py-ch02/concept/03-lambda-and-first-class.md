# 03 · lambda 与一等公民函数

## 一、理论根基：函数作为值

一等公民（first-class）意味着函数与其它值（int、对象）地位相同：能赋给变量、作参数、作返回值、存容器。高阶函数（`map`/`filter`/`sorted(key=)`）依赖此特性。

## 二、实现机制：lambda 是匿名函数对象

`lambda x: x*2` 编译为与 `def` 相同的 `<function>` 对象，只是**没有名字、只能有一个表达式体**（结果即该表达式的值）。它同样有 `__globals__`、`__code__`，可被 `dis` 反汇编。单一表达式限制是**语法层**而非能力层——复杂逻辑应抽成 `def` 以保持可读。

## 三、对比 C++/Java 的 lambda

- C++11 lambda：`[capture](args){body}` 可 by-value/by-ref 捕获，能隐式内联，零开销抽象（编译进调用点），可 `mutable`、`std::function` 化。
- Java 8 lambda：函数式接口（单抽象方法）实例，捕获 effectively-final 变量；类型由目标上下文推断。
- Python lambda：捕获是**按名 + 延迟**（见第 4 讲延迟绑定陷阱），且捕获变量而非值；无类型强制但支持 annotation。

## 四、工程实践

- 用 lambda 做轻量 key/sort/predicate：`sorted(users, key=lambda u: u.age)`。
- 别把多行逻辑塞进 lambda；复杂可读逻辑用 `def`。
- 闭包捕获循环的延迟绑定是高频面试点（见第 4 讲与 `examples/ex06-closure-late-binding.json`）。

## 五、可运行代码

见 `examples/ex03-lambda-basic.json`、`examples/ex09-first-class-function.json`。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `lambda` 只能写**单个表达式**，不能有语句/多行体/文档串；超过一行就用 `def`。
- 最常用场景：`sorted(key=...)`、`max(key=...)`、`map/filter`（但推导式通常更清晰）。
- 别给 lambda 起名字再赋值（`f = lambda x: ...`），那违反 PEP 8 且丢掉了 traceback 里的函数名。

### 🎓 博士生视角
- 函数是**一等公民**：可赋值给变量、可作为参数、可作为返回值、可存入容器。这是函数式编程的入场券，也是装饰器与闭包的前提。
- `lambda` 与 `def` 生成的都是同一类 `function` 对象，差异仅在于：lambda 体被限制为单表达式、没有名字（`__name__ == "<lambda>"`）、没有 docstring。它不是「更快的函数」。
- 一等函数 + 闭包共同支撑了**高阶函数**与**装饰器**；在类型论中对应「指数对象（exponential）」与笛卡尔闭范畴，这是函数式语言的理论根基。

### 📚 考研者视角
- 与 C 的**函数指针**、C++ 的 `std::function` / lambda 表达式形成对照：Python 的函数是对象，C 的函数指针是地址。
- 若考程序设计语言原理，常考「一等函数」「高阶函数」「闭包」的定义与示例。
- 记忆锚点：**`lambda` 是「匿名单表达式函数」，与 `def` 是同一种对象**。
