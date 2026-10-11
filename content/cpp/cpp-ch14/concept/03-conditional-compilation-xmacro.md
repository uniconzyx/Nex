# 03 · 条件编译、X-Macro 与 static_assert 替代宏

## 一、理论根基：条件编译是「编译期的 if」

`#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif` 在**预处理阶段**根据常量表达式（或宏是否定义）决定**哪些代码进入翻译单元**。它处理的是「同一份源码在不同平台/配置下编译出不同产物」的需求，与运行期 `if` 截然不同——被 `#if 0` 排除的代码**根本不会被编译器看到**。

常用谓词：
- `#ifdef X` / `#ifndef X`：宏 `X` 是否定义。
- `#if defined(X) && !defined(Y)`：`defined` 运算符可组合复杂条件。
- `#if __cplusplus >= 201703L`：按语言标准版本分支。

## 二、X-Macro：用一张表驱动「枚举 + 字符串 + 分支」

重复维护「枚举值」与「对应的字符串/分支」是典型痛点（漏改一处就错位）。X-Macro 用**一个宏列表**作为单一事实来源，靠 `#define X(...)` 在不同位置「展开同一张表」生成多份代码：

```cpp
#define COLORS \
    X(Red,   1) \
    X(Green, 2) \
    X(Blue,  4)
enum class Color { #define X(n,v) n = v, COLORS #undef X };
const char* name(int v){ switch(v){
    #define X(n,v) case v: return #n; COLORS #undef X
    default: return "Unknown"; } }
```

新增一种颜色只需改 `COLORS` 一处，枚举、字符串表、switch 分支**自动同步**——这正是 nlohmann/json 等库管理错误码/枚举的惯用法。

## 三、用 static_assert / constexpr 替代「可编译期计算」的宏

传统 C 用宏表达「编译期常量与断言」：
```cpp
#define SIZE 1024
#define ASSERT(c) typedef char _a[(c)?1:-1]   // 丑陋的编译期断言
```
现代 C++ 提供了**类型安全、可读、可诊断**的替代：
- `constexpr`/`const` 变量取代「对象宏常量」：`constexpr int size = 1024;`（带类型、可参与重载与模板推导）。
- `static_assert(cond, "msg")` 取代编译期断言：条件为假时在编译期给出清晰错误信息，且**不生成任何运行期代码**。
- `enum class` 取代「无类型枚举宏」，避免名字污染与隐式转换。

> 取舍：**凡是能在编译期用 `constexpr`/`static_assert`/模板表达的，都应放弃宏**。宏只保留在「必须做文本级变换」的场景（`#`/`##`、条件编译、`__FILE__`/`__LINE__`）。

## 四、边界与陷阱

1. `#if` 中未定义的宏名视为 `0`（不会报错），容易把拼写错误的宏名静默当成 false —— 可改用 `#ifdef` + 显式定义提升可读性。
2. 条件编译过度使用会让代码出现大量「死分支」，降低可维护性；应优先用模板/策略类表达差异。
3. X-Macro 的 `#undef X` 必须紧跟使用之后，避免宏名泄漏到别处。

## 五、可运行示例：X-Macro 与 static_assert

```cpp
#include <iostream>
#define COLORS X(Red,1) X(Green,2) X(Blue,4)
enum class Color { #define X(n,v) n = v, COLORS #undef X };
const char* colorName(int v){
    switch(v){ #define X(n,v) case v: return #n; COLORS #undef X
        default: return "Unknown"; }
}
int main(){
    static_assert(sizeof(int)==4, "int must be 4 bytes");
    std::cout << (int)Color::Red << ' ' << colorName(4) << '\n';
}
```

**输出**：
```
1 Blue
```
> 观察点：① 枚举与字符串表由同一张 `COLORS` 表生成，改一处即可同步；② `static_assert` 在编译期校验不变量，零运行期开销。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **条件编译用于跨平台与调试开关**：`#ifdef _WIN32`、`#ifndef NDEBUG`；但过多的 `#if` 会让代码难以阅读与测试。
- **X-Macro** 是「一处定义、多处展开」的实用技巧：把枚举与名字表写在同一个 `.def` 里，避免枚举与字符串表不同步。
- 新代码优先 `static_assert`（有类型、有作用域、错误信息清晰）替代 `#if` + `#error` 的组合。

### 🎓 博士生视角
- 条件编译是**编译期分支裁剪**，被裁掉的代码连**语法都不检查**（只在预处理阶段消失）——这是它比 `if constexpr` 更弱的地方（后者仍要求语法正确）。
- X-Macro 利用的是**「宏展开可重复」**：同一份 `LIST` 宏在不同 `#define` 上下文中多次展开，生成不同代码——这是「编译期代码生成」的轻量形式。
- `static_assert` 与 `constexpr` 把「编译期断言/计算」纳入**类型系统**（有作用域、可参与重载），代表着从「预处理器元编程」向「模板元编程」的迁移趋势。

### 📚 考研者视角
- 记忆锚点：**条件编译在预处理阶段完成、被排除的代码不参与编译**。
- 常考辨析：**`#ifdef`（预处理期，无类型检查）vs `if constexpr`（编译期，仍检查语法、有作用域）**。
- 工程常识：**`assert` 在 `NDEBUG` 下被移除**——这与条件编译是同一套机制（`assert` 本身就是宏）。

---
