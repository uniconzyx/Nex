# 类型推导与 auto

C++11 引入 `auto`，让编译器根据**初始化表达式**推导变量类型，减少冗余且避免截断。它的价值不只是"少打字"：它让代码在类型改变时自动跟随（例如把 `std::map` 换成 `std::unordered_map`，迭代器写法不用改），也让一些根本写不出来的类型变得可写——lambda 的闭包类型就没有名字，只能用 `auto` 接。

## 一、`auto` 的推导规则：和模板一模一样

`auto` 的推导规则**刻意与模板参数推导保持一致**：把 `auto` 换成 `T`，就得到一个函数模板。所以理解 `auto` 等于理解 `template<typename T> void f(T)`。

关键点在于「按值推导等于做一次 decay」：

- **丢弃引用**：`int& r = a; auto x = r;` → `x` 是 `int`，是**副本**，改 `x` 不动 `a`。
- **丢弃顶层 const**：`const int c = 1; auto x = c;` → `x` 是 `int`，可修改。底层 const 保留（`const char* const p` → `auto x = p` 得到 `const char*`）。
- **数组与函数退化**：`int arr[3]; auto x = arr;` → `x` 是 `int*`，不是数组。
- **保留引用/const 要显式写**：`auto&`、`const auto&`、`auto&&`。

### `auto&&` 是转发引用，不是右值引用

```cpp
template <typename T>
void relay(T&& v) { sink(std::forward<T>(v)); }   // T&& 在模板中是转发引用
```

`auto&&` 与模板的 `T&&` 同源：当实参是左值时，`T` 被推导为 `U&`，经引用折叠得到左值引用；实参是右值时，`T` 为 `U`，得到右值引用。这就是"万能引用"（标准术语：转发引用）的机制。它必须**紧贴一个待推导类型**才有这个性质——`std::vector<int>&&` 就是普通右值引用。

### `decltype` 与 `decltype(auto)` 是另一套规则

`decltype(e)` 分三种情况：

1. `e` 是**未加括号的标识符**（id-expression）→ 返回其声明类型，引用与 cv 全保留。
2. `e` 是**左值表达式**（其他形式）→ 返回 `T&`。
3. `e` 是右值 → 返回 `T`。

这个"加不加括号结果不同"的规则会咬人：`decltype(x)` 得到 `int`，`decltype((x))` 得到 `int&`。`decltype(auto)` 用 `decltype` 的规则去推导 `auto`，因此**能保留引用**——这是完美转发返回值的正确工具，写 `auto` 会把返回的引用悄悄变成副本。

```text
推导规则对照（设 int a = 1; const int c = 2; int& r = a;）

  auto        x = r;   → int             丢掉引用
  auto&       x = r;   → int&            保留引用
  const auto& x = r;   → const int&      既能绑左值也能绑临时对象
  auto        x = c;   → int             丢掉顶层 const
  decltype(r) x = r;   → int&            声明类型原样
  decltype((r)) x = r; → int&            带括号 → 左值 → T&
  auto        x = arr; → int*            数组退化为指针（arr 为 int[3]）
```

## 二、花括号与 `auto` 的历史坑

`auto x{1}` 的推导在标准演进中改过一次：C++11/14 中 `auto x{1}` 被推导为 `std::initializer_list<int>`，C++17 起改为 `int`（N3922）。**同一行代码在不同标准下类型不同**，跨编译器会出诡异问题。

结论是：`auto` 配花括号时，要么明确写 `auto x = std::vector<int>{1,2,3}`（带类型名），要么只用 `auto x{1}` 这种单值且确认 C++17 起步。想表达"列表"就显式写容器类型。

## 三、`auto` 在工程里的真实收益与代价

**收益**：

- 闭包类型不可命名，lambda 只能 `auto` 接。
- 迭代器写法大幅简化：`for (auto it = m.begin(); it != m.end(); ++it)`，容器类型改名时不用改循环。
- 避免隐式窄化：`auto n = v.size()` 得到 `size_t`，不会像 `int n = v.size()` 那样悄悄截断。

**代价**：

- **类型不写在纸面上，review 时看不出代价**。`auto s = f();` 可能是拷贝了一个大对象。规范做法是：**返回值涉及所有权/拷贝时写全类型或写 `const auto&`**。
- 代理类（proxy）会伪装成值：`std::vector<bool>` 的 `operator[]` 返回代理对象，`auto b = v[0]` 拿到的是代理而非 `bool`，一旦 `v` 被修改就可能悬垂。这就是"`auto` 推导出意外类型"的经典案例。

## 四、范围 for 的三种写法

```cpp
for (auto x : v)        { /* 拷贝，改 x 不影响 v；大对象慎用 */ }
for (auto& x : v)       { /* 引用，可修改 v */ }
for (const auto& x : v) { /* 只读引用，无拷贝 —— 遍历的默认选择 */ }
```

范围 for 展开后是 `auto&& __range = v; auto __begin = begin(__range); ...`。注意两点：**遍历时不要修改容器结构**（`push_back` 会让迭代器失效，UB）；临时容器也能被遍历，因为 `__range` 是引用绑定，生命周期被延长。

## 五、边界与陷阱

- **`auto` 按值推导会丢引用与顶层 const**：`auto x = ref;` 是拷贝，要保留就得写 `auto&` 或 `const auto&`。
- **`size()` 返回无符号**：`for (auto i = 0; i < v.size(); ++i)` 中 `auto i` 推出 `int`，与 `size_t` 比较会触发符号告警；写 `std::size_t` 或范围 for。
- **`decltype(auto)` 用在返回值**：`auto` 会丢掉返回的引用，`decltype(auto)` 才保留；但如果返回的是 `return (x);` 这种带括号的左值，会返回引用导致悬垂可能。
- **`auto` 与 `std::vector<bool>` 代理**：见上，`auto&&` 接代理可以避免拷贝，但生命周期仍跟随容器。

## 六、可运行示例：一张表验完三种推导

```cpp
#include <cstddef>
#include <iostream>
#include <typeinfo>
#include <vector>

int main() {
    int a = 1;
    const int c = 2;
    int& r = a;
    int arr[3] = {1, 2, 3};

    auto           x1 = r;      // int（丢引用）
    auto&          x2 = r;      // int&
    const auto&    x3 = c;      // const int&
    auto           x4 = c;      // int（丢顶层 const）
    decltype(r)    x5 = r;      // int&
    decltype((r))  x6 = r;      // int&
    auto           x7 = arr;    // int*

    std::cout << typeid(x1).name() << ' ' << typeid(x2).name() << ' '
              << typeid(x5).name() << ' ' << typeid(x7).name() << '\n'
              << "same=" << (&x2 == &a) << ' ' << (&x5 == &a) << ' '
              << (&x6 == &a) << ' ' << (x7 == arr) << '\n'
              << "sizeof_ptr=" << sizeof(x7) << '/' << sizeof(arr) << '\n';
}
```

`typeid(...).name()` 的输出是**实现相关**的修饰名（GCC 会给 `i`、`Ri` 这类缩写，`c++filt` 才能还原可读形式），所以这段程序只用它做"三种写法是否同类"的对比，不把它当字符串匹配的判据——这是跨编译器可移植的写法。

## 三视角解析

### 🧑‍💻 程序员视角
- **`auto` 按值推导会丢引用与顶层 `const`**：`auto x = ref;` 是拷贝！要保留就得写 `auto&` 或 `const auto&`。
- 范围 for 中想避免拷贝写 `for (const auto& x : v)`；想修改写 `for (auto& x : v)`。
- `auto&&` 是**转发引用**（原称万能引用），配合 `std::forward` 才能完整转发值类别。
- 团队规范建议：**局部变量、迭代器、lambda 用 `auto`；函数返回值与成员变量写全类型**，让接口成本可见。

### 🎓 博士生视角
- `auto` 的推导规则**与模板参数推导完全一致**（这是刻意的设计一致性）：按值推导会做**数组到指针、函数到函数指针的退化（decay）**，并丢弃引用与顶层 `const`。
- `decltype` 走的是另一套规则：对**标识符（id-expression）**返回其声明类型（保留引用与 cv），对其他左值表达式返回 `T&`，对右值返回 `T`。`decltype(auto)` 则用 `decltype` 的规则去推导 `auto`，因此**能保留引用**——这是转发返回值的正确工具。
- 花括号初始化与 `auto` 的组合是著名陷阱：`auto x{1}` 在 C++17 起推导为 `int`（早期常推导为 `initializer_list<int>`），因此想要 `vector` 时要用 `auto v = std::vector<int>{1,2}`。
- 从类型论看，这体现的是「按值传递 = 去掉引用与 cv 的规范化（decay）」这一约定，与 `std::decay` 的语义一致。
- 引用折叠规则（`& &&`→`&`、`&& &&`→`&&`）是转发引用能工作的底层机制：正因为折叠，`T` 推导为 `U&` 时 `T&&` 仍能绑定左值。

### 📚 考研者视角
- 与编译原理的**类型推导（类型推断）**、以及显式/隐式类型转换对应。
- 常考概念题：「`auto` 与 `decltype` 的区别」「为什么 `auto` 会丢引用」。
- 记忆锚点：**`auto` 会 decay（丢引用、丢顶层 const、数组退化）**；**`decltype(auto)` 保留引用**；**`decltype((x))` 比 `decltype(x)` 多一层引用**。
