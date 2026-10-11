# 类型推导与 auto

C++11 引入 `auto`，让编译器根据**初始化表达式**推导变量类型，减少冗余且避免截断。

## 要点

- `auto x = 3.14;` → 推导为 `double`；`auto n = 42;` → 推导为 `int`
- 范围 for：`for (int x : container)` 遍历容器，避免手写迭代器
- `auto` 与 `const`/`&` 组合：`const auto&` 常用于只读遍历大对象，避免拷贝
- C++14 起 lambda 可用 `auto` 参数：`[](auto a, auto b) { return a + b; };`

```cpp
#include <iostream>
#include <vector>

int main() {
    auto pi = 3.14;                 // double
    std::vector<int> v{1, 2, 3};
    for (const auto& x : v) {       // 只读引用，免拷贝
        std::cout << x << " ";
    }
}
```

> 陷阱：`auto` 会忽略顶层 `const` 与引用（`auto&` 才保留引用），`auto x = v.size();` 中 `size()` 返回 `size_t`，用 `int` 接可能截断。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`auto` 按值推导会丢引用与顶层 `const`**：`auto x = ref;` 是拷贝！要保留就得写 `auto&` 或 `const auto&`。
- 范围 for 中想避免拷贝写 `for (const auto& x : v)`；想修改写 `for (auto& x : v)`。
- `auto&&` 是**转发引用**（原称万能引用），配合 `std::forward` 才能完整转发值类别。

### 🎓 博士生视角
- `auto` 的推导规则**与模板参数推导完全一致**（这是刻意的设计一致性）：按值推导会做**数组到指针、函数到函数指针的退化（decay）**，并丢弃引用与顶层 `const`。
- `decltype` 走的是另一套规则：对**标识符（id-expression）**返回其声明类型（保留引用与 cv），对其他左值表达式返回 `T&`，对右值返回 `T`。`decltype(auto)` 则用 `decltype` 的规则去推导 `auto`，因此**能保留引用**——这是转发返回值的正确工具。
- 花括号初始化与 `auto` 的组合是著名陷阱：`auto x{1}` 在 C++17 起推导为 `int`（早期常推导为 `initializer_list<int>`），因此想要 `vector` 时要用 `auto v = std::vector<int>{1,2}`。
- 从类型论看，这体现的是「按值传递 = 去掉引用与 cv 的规范化（decay）」这一约定，与 `std::decay` 的语义一致。

### 📚 考研者视角
- 与编译原理的**类型推导（类型推断）**、以及显式/隐式类型转换对应。
- 常考概念题：「`auto` 与 `decltype` 的区别」「为什么 `auto` 会丢引用」。
- 记忆锚点：**`auto` 会 decay（丢引用、丢顶层 const、数组退化）**；**`decltype(auto)` 保留引用**。
