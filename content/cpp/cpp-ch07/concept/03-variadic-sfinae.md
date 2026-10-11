# 03 · 可变参数模板与 SFINAE：参数包展开、折叠表达式与编译期重载筛选

## 一、理论根基：为什么需要"参数个数可变"的模板

C 的可变参靠 `std::va_list`，但**完全丢失类型信息、无类型安全、靠约定读取个数**。C++11 引入**可变参数模板（variadic templates）**：把"参数包（parameter pack）"作为一等公民带入模板，每个元素都保有真实类型，由编译器在实例化时**展开（expand）**。

```cpp
template <typename... Ts>   // Ts 是类型参数包
void f(Ts... args);         // args 是函数参数包
```

核心机制是**包展开（pack expansion）**：`args...` 在实例化 `f(1, 2.5, "x")` 时展开为 `1, 2.5, "x"`；`Ts...` 展开为 `int, double, const char*`。展开几乎可出现在任何"逗号分隔列表"的位置，常见模式：

- 递归展开（C++11 经典）：用一个参数 + 剩余包递归，`print(first, rest...)`；
- **折叠表达式（fold expression，C++17）**：`(args + ...)` 把二元运算符对整包做归约，**无需递归、无额外开销**，是现代首选；
- 模式展开：`g(args)...` 对每个元素套用 `g`。

## 二、实现机制：折叠表达式（C++17，强烈推荐）

`(包 op ...)`（一元左折叠）等价于 `(((e1 op e2) op e3) ... op en)`。支持所有二元运算符，并可为空包提供初值：`(args + ... + 0)`。

```cpp
template <typename... Ts>
auto sum(Ts... ts) { return (ts + ...); }        // 左折叠求和

template <typename... Ts>
void print_all(Ts... ts) { (std::cout << ... << ts) << '\n'; }  // 逗号式链式输出
```

- 折叠的"节点"在编译期确定，生成的代码等价于手写 `a+b+c+d`，**零运行时间接**。
- 可配合 `&&`（逻辑与，短路）、`,`（逗号，顺序求值）等做编译期遍历，是 `std::forward`、tuple 遍历、日志库的基石。

## 三、理论根基：SFINAE —— 替换失败并非错误

**SFINAE = Substitution Failure Is Not An Error**（[temp.deduct]）。在模板实参推导与**替换（substitution）**阶段，如果某一候选模板在把实参代入其**声明签名**时产生"非良构（ill-formed）"的类型，该候选**被悄悄丢弃**，而不是报错；只要还有别的候选能匹配，整体仍然合法。

这正是 §一 提到的"推导失败不是错误"的正式名称，但 SFINAE 的威力远超重载：它让我们能**在编译期根据类型属性筛选重载**。

### 经典手段：`std::enable_if` + `type_traits`

`std::enable_if<B, T>::type` 在 `B==true` 时"存在"（是 `T`），`B==false` 时**整个 `type` 成员不存在**。把它放在返回类型（一个非推导上下文）里，配合 trait：

```cpp
template <typename T>
typename std::enable_if<std::is_integral<T>::value, T>::type
process(T v) { /* 仅当 T 是整型才存在此重载 */ }

template <typename T>
typename std::enable_if<std::is_floating_point<T>::value, T>::type
process(T v) { /* 仅当 T 是浮点才存在此重载 */ }
```

调用 `process(10)`：第一份替换成功（整型→`type` 存在）、第二份因 `is_floating_point` 为 false 使 `type` 缺失 → 替换失败 → 被丢弃（SFINAE，不是错误），只剩第一份，编译通过。`process(3.14)` 同理选中第二份。`process("s")` 两份都失败 → 真正报错（"无匹配"）。

> 关键认知：SFINAE 只发生在**替换阶段**，且只针对"**签名中依赖于模板参数的部分**"。函数体内部出错**不属于** SFINAE，会直接是硬错误。这也解释了为什么 trait 检测要放在返回类型/默认模板参数/函数参数这种"签名位置"。

## 四、实现机制：检测"是否有某成员"（SFINAE 实战）

用"伪表达式 + `decltype` 替换"探测类型能力（C++17 前标准库 `void_t` 惯用法）：

```cpp
template <typename T, typename = void>
struct has_size : std::false_type {};
template <typename T>
struct has_size<T, std::void_t<decltype(std::declval<T>().size())>> : std::true_type {};
```

`std::void_t<...>` 把任意类型塌缩为 `void`；若 `T` 没有 `size()`，则 `decltype(...)` 替换失败 → 偏特化被丢弃 → 退回主模板（false）。这就是 `type_traits` 大量"能力探测"的实现原理。

## 五、concept 的前世今生：SFINAE 的终结者

SFINAE + `enable_if` + `void_t` 虽强大，但**错误信息如天书**（满屏"替换失败"），且写法晦涩、易出错。C++20 引入 **concept / `requires`** 从根本上解决：

1. **起源**：concept 思想早可追溯至 2003 年 Sutter/Stroustrup 的提案与 Boost.Concept_check；C++11 `type_traits` 与 `static_assert` 是过渡；C++17 `void_t` 把"能力探测"标准化。
2. **C++20 落地的 `concept`**：把"对模板参数的约束"变成**一等公民**，可读、可组合、可诊断：
   ```cpp
   template <typename T>
   requires std::integral<T>
   T process(T v);
   // 或简写：template <std::integral T> T process(T v);
   ```
3. **为什么取代 SFINAE**：
   - **错误信息友好**：约束不满足时直接说"T 不满足 integral"，而非展开 200 行替换失败；
   - **约束可被"偏序"优选**：多个 concept 重载按"更受限者优先"，规则清晰；
   - **可直接用于变量/函数/类模板**与 `requires` 表达式，表达力覆盖 SFINAE 90% 场景；
   - **编译更快**：概念是"谓词"，无需真的做失败替换来试探。

> 工程师视角：新项目首选 `concept`；读老代码（STL 实现、Boost、fmtlib）仍需懂 SFINAE——大量库在 C++17 及以下仍以 `enable_if`/`void_t` 实现约束。二者是同一目标（编译期类型约束）的两代技术。

## 六、工程实践与陷阱

- 折叠表达式优先于递归展开：更短、更易内联、错误更少。
- `enable_if` 放返回类型时，两个重载的"启用条件"必须**互斥**，否则同时启用 → 歧义。
- SFINAE 只在签名替换期生效；想约束构造/析构等无返回类型处，用 `enable_if` 的**默认模板参数**位（`template<typename T, typename=enable_if_t<...>>`）。
- 用 `static_assert` 给约束失败补一句人话（比裸 SFINAE 报错友好）。

## 七、可运行示例：眼见为实

```cpp
#include <iostream>
#include <type_traits>

// ---- 可变参数 + 折叠表达式 ----
template <typename... Ts>
auto sum(Ts... ts) { return (ts + ...); }               // 左折叠求和

template <typename... Ts>
void print_all(Ts... ts) { (std::cout << ... << ts); std::cout << '\n'; }

// ---- SFINAE：按类型属性筛选重载 ----
template <typename T>
typename std::enable_if<std::is_integral<T>::value, T>::type
process(T v) { std::cout << "integral:" << v << '\n'; return v; }

template <typename T>
typename std::enable_if<std::is_floating_point<T>::value, T>::type
process(T v) { std::cout << "floating:" << v << '\n'; return v; }

int main() {
    std::cout << "sum=" << sum(1, 2, 3, 4) << '\n';
    print_all("x=", 1, " y=", 2.5);

    process(10);       // 命中整型重载
    process(3.14);     // 命中浮点重载
    // process("s");   // 两份都替换失败 → 真正报错（取消注释可见 SFINAE 边界）
}
```

**输出**：
```
sum=10
x=1 y=2.5
integral:10
floating:3.14
```

> 关键结论：① 折叠表达式 `(ts + ...)` 一行实现任意长参数求和，零运行时间接；② `process(10)`/`process(3.14)` 靠 `enable_if` + `is_xxx` 在编译期被分到不同重载——SFINAE 把"类型不满足"从硬错误变成"该候选出局"。这正是 `concept` 问世前 C++ 泛型约束的标准写法。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **可变参数模板**是「完美转发 + 工厂」的基础：`make_unique<T>(args...)` 就靠它把任意参数原样透传给构造函数。
- 折叠表达式（C++17）把「递归展开」压成一行：`(args + ...)`、`(out << ... << args)`，可读性显著优于手写递归基。
- **SFINAE 是历史包袱**：新代码优先用 `if constexpr`（C++17）与 `concept`（C++20），只在维护老库时才需要读懂 `enable_if` 长串。

### 🎓 博士生视角
- **SFINAE 全称「替换失败非错误」**：重载决议时若模板参数替换导致**紧邻语境（immediate context）**的无效类型/表达式，该候选被静默移除而不报错；但若错误发生在**模板体内部**（非紧邻语境）则是硬错误。这条边界是很多「编译报错的报错」的根因。
- 折叠表达式有四种形式（一元左/右、二元左/右），二元形式允许提供初值，语义是**编译期语法树层面的左/右结合**，不是运行时循环。
- `if constexpr` 未选中的分支**仍须语法正确**，但其中的依赖表达式不会被实例化——这是它替代 SFINAE 的关键：把「重载筛选」变成「分支裁剪」。

### 📚 考研者视角
- 考研（408）**不考模板元编程**，但「C++ 泛型 vs Java 泛型」的对比常出现在专业课题或复试中。
- 记忆锚点：**C++ 模板是编译期实例化（单态化），Java 泛型是类型擦除**——前者运行时无开销但代码膨胀，后者代码紧凑但丢失运行时类型信息。
- 若问「模板为什么放头文件」：答**实例化需要完整定义可见**（包含模型）。

---
