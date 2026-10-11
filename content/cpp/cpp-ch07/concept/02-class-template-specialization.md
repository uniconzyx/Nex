# 02 · 类模板与特化：全特化、偏特化与特化优先级

## 一、理论根基：为什么类也需要模板与"特化"

容器是类模板最自然的载体：`std::vector<T>` 对所有 `T` 共享同一套"大小/扩容/下标"逻辑，但**行为在某些类型上应当不同**——例如 `std::vector<bool>` 在 C++ 标准里被特化为**位压缩存储**（每个 bool 占 1 bit 而非 1 byte）。这种"**通用配方 + 特定类型的定制实现**"就是**模板特化（template specialization）**。

特化解决的核心矛盾：**通用实现追求统一，而特定类型追求最优/正确**。模板机制允许你为某些实参组合提供一份"覆盖默认"的专属定义，而不必为所有类型写分支。

## 二、实现机制：类模板与实例化

```cpp
template <typename T>
class Stack {
    std::vector<T> data_;
public:
    void push(const T& x) { data_.push_back(x); }
    void pop()            { data_.pop_back(); }
    T top() const         { return data_.back(); }
    bool empty() const    { return data_.empty(); }
};
```

- 使用 `Stack<int>` 时编译器**隐式实例化**出 `Stack<int>` 类及其成员函数定义；从未被使用的成员**不会被实例化**（所以即便某成员对某个 T 不合法，只要不用就编译通过——这叫"惰性实例化"）。
- `Stack<int>` 与 `Stack<double>` 是**两个完全无关的类型**，彼此不能互相赋值/转换。

### 非类型模板参数（Non-type Template Parameter, NTTP）

模板参数不限于类型，也可以是**编译期常量**：整型、枚举、`nullptr_t`、指针/引用（C++17 起还能是 `auto` 与字面量类类型）。

```cpp
template <typename T, std::size_t N>   // N 是编译期常量
struct Array { T buf[N]; };
Array<int, 8> a;   // N=8 是类型的一部分
```

NTTP 的价值：**把"规模"编码进类型**，使数组大小成为编译期信息，可 `constexpr` 使用、利于内联与循环展开，且不同 `N` 是不同类型（可防止 `Array<int,8>` 误赋给 `Array<int,4>`）。C++20 把 NTTP 扩展到**类类型字面量**与 `auto`，催生了 `std::array` 风格的"编译期值作为参数"范式（如 `template <auto V> struct`）。

## 三、实现机制：全特化（Full / Explicit Specialization）

为某一**具体类型组合**完全重写一份定义，所有模板参数都被固定：

```cpp
template <>
class Stack<bool> {            // 全特化：T 固定为 bool
    unsigned bits_ = 0;
public:
    void push(bool b) { bits_ = (bits_ << 1) | (b ? 1u : 0u); }
    bool top() const { return bits_ & 1u; }
    // ...
};
```

- 语法 `template <>` 后跟 `class Stack<bool>`：空尖括号表示"这是某个模板的特化"，`<bool>` 给出具体实参。
- 全特化是**一个新的独立类定义**，与原始模板没有继承关系，可拥有完全不同的成员。

## 四、实现机制：偏特化（Partial Specialization）

只固定**部分**模板参数，或对参数施加**模式约束**，其余仍参数化：

```cpp
// 主模板
template <typename T, typename U>
struct Pair { /* 异构对 */ };

// 偏特化 ①：两个类型相同
template <typename T>
struct Pair<T, T> { /* 同类型对的优化实现 */ };

// 偏特化 ②：第二个参数为指针
template <typename T, typename U>
struct Pair<T, U*> { /* 指针特化 */ };
```

- 偏特化**不是新模板，而是主模板的"备选配方"**；它不引入新名称，只是当实参匹配该模式时优先采用。
- **匹配优先级（偏序 / partial ordering）**：更"具体/受限"的特化胜出。`Pair<int,int>` 同时匹配主模板与 `Pair<T,T>`，后者更特化 → 选中偏特化。若两个偏特化都匹配且无可比特化关系 → **歧义错误**。

> 偏序判定的直觉：把 `Pair<T,T>` 的 `T` 同时代入 `Pair<A,B>` 的两个参数都得 `T`；反过来不行——所以 `Pair<T,T>` 更特化。

## 五、工程实践：特化的正确用法与陷阱

1. **特化的"主模板要先于特化可见"**：特化声明必须出现在主模板之后，且特化版本对原模板"不可见"内部成员不做任何隐式继承。
2. **函数模板几乎没有偏特化**（语言禁止函数模板偏特化，只允许重载与全特化）。需要"按类型分支的函数行为"时，标准做法是用**类模板偏特化 + 一个转发函数模板**：
   ```cpp
   template <typename T> struct Impl { static void run(); };
   template <> struct Impl<int> { static void run(); };   // 全特化（函数用类承载）
   template <typename T> void run() { Impl<T>::run(); }
   ```
3. **特化优先级顺序**：全特化 > 偏特化（越具体越优先）> 主模板；多个偏特化之间按偏序，无法比较则报歧义。
4. **优先用 `if constexpr` / concept 替代大量特化**（C++17/20 起），减少类爆炸与维护成本。

## 六、边界与陷阱

- 偏特化的参数模式必须**能唯一确定**主模板参数；否则歧义。
- `Stack<bool>` 全特化与 `Stack<int>` 是不同类型，不能互相赋值。
- NTTP 的 `N` 必须是**编译期常量表达式**；用变量会导致实例化失败。

## 七、可运行示例：眼见为实

```cpp
#include <iostream>

// 主模板
template <typename T, typename U>
struct Pair { static const char* tag() { return "two types"; } };

// 偏特化：两类型相同
template <typename T>
struct Pair<T, T> { static const char* tag() { return "same type"; } };

// 偏特化：第二参数为指针
template <typename T, typename U>
struct Pair<T, U*> { static const char* tag() { return "second is pointer"; } };

// 全特化：Pair<void*, void*>
template <>
struct Pair<void*, void*> { static const char* tag() { return "void* void* full spec"; } };

int main() {
    std::cout << Pair<int, double>::tag() << '\n';   // 主模板
    std::cout << Pair<int, int>::tag()    << '\n';   // 偏特化①（更特化）
    std::cout << Pair<int, char*>::tag()  << '\n';   // 偏特化②
    std::cout << Pair<void*, void*>::tag()<< '\n';   // 全特化（最优先）
}
```

**输出**：
```
two types
same type
second is pointer
void* void* full spec
```

> 关键结论：匹配按"**越具体越优先**"——全特化 `Pair<void*,void*>` 压过所有偏特化，偏特化 `Pair<T,T>` 压过主模板；这正是一段模板代码在真实工程里"按类型分发行为"的底层机制。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **全特化改行为、偏特化改结构**：`std::hash<MyType>` 用全特化；对「指针/容器」统一加一层处理用偏特化（如 `is_pointer<T*>`）。
- 常见坑：特化必须写在**同名模板可见之后**且在同一命名空间；漏了会「静默使用主模板」，编译通过但行为不对。
- 实战用途：类型萃取（traits）几乎全靠偏特化撑起来——`remove_reference`、`decay`、`iterator_traits` 都是。

### 🎓 博士生视角
- 特化优先级是**偏序关系**：实例 → 偏特化 → 主模板，编译器在偏特化之间再按**「更特化者胜」**做偏序比较（`T*` 比 `const T*` 更一般）。
- 全特化不再是一个模板（它是**具体类型**），所以不参与偏序；这也是「函数模板不能偏特化，只能重载」的根因——函数模板没有偏序可依赖，语言选择用重载解决。
- 从类型论看，偏好特化等价于**模式匹配的分支选择**，主模板是 catch-all 分支。

### 📚 考研者视角
- 考研对模板特化通常只要求「知道有全特化/偏特化、能说出区别」，属于**概念题**（选择题/简答）。
- 记忆锚点：**类模板可以偏特化，函数模板不能偏特化只能重载**——这条几乎每年以选择题形式出现。
- 若考「模板实例化时机」：答**编译期**，且特化版本在**编译期就完成选择**。

---
