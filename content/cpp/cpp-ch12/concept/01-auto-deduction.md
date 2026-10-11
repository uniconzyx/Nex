# 01 · `auto` 的类型推导规则（与模板推导一致）

## 一、理论根基：为什么 `auto` 的推导规则就是模板推导规则

C++11 引入 `auto` 作为「类型占位符」：编译器在初始化时根据 `=` 右侧的表达式**推导**出类型。
关键事实：**`auto` 的推导与函数模板的实参推导（template argument deduction）使用完全相同的规则**（见 C++ 标准 [dcl.spec.auto] 与 [temp.deduct]）。

```cpp
auto x = expr;      // 等价于把 expr 作为实参传给模板 void f(T param); 推导 T
auto& y = expr;     // 等价于模板 void f(T& param);
```

`auto` 不「自动选择最通用类型」，它严格按初始化表达式的**值类别与 cv 限定**走模板推导。

## 二、实现机制：`auto` / `auto&` / `const auto&` / `decltype(auto)` 的差别

| 写法 | 推导来源 | 保留引用？ | 保留 const？ | 典型用途 |
|---|---|---|---|---|
| `auto x = e;` | 按值（decay：去引用、去顶层 cv） | 否（拷贝） | 否 | 想要一份独立副本 |
| `auto& x = e;` | `T&` 规则 | 是 | 是 | 想改原对象/避免大拷贝 |
| `const auto& x = e;` | `const T&` 规则 | 是 | 是 | 只读、绑定临时也安全 |
| `auto* x = e;` | 指针 | 否 | 是（指向的对象 const 保留） | 明确是指针 |
| `decltype(auto) x = e;` | `decltype(e)` 规则 | 完全按 `e` 的形式（引用/const 原样） | 是 | 完美转发返回值、保留引用 |

**反直觉点（陷阱核心）**：`auto` 按值推导会**丢失引用和顶层 const**。

```cpp
int   n = 0;
int&  r = n;
const int c = 1;

auto a = r;          // a 是 int（引用被丢掉，得到副本）
auto b = c;          // b 是 int（顶层 const 被丢掉）
auto& br = r;        // br 是 int&（保留）
```

## 三、工程实践：什么时候该/不该用 `auto`

- **适合**：迭代器（`for (auto it = v.begin(); ...)`）、lambda 类型、长类型名（`std::unordered_map<...>::iterator`）、范围 for 的元素变量。
- **不适合**：函数返回类型（会隐藏接口契约）、容器元素类型需要明确语义时、需要引用/const 语义但忘了加 `&`/`const` 时。
- **`decltype(auto)` 的黄金场景**：转发函数的返回值，使「返回引用还是返回值」由被调用方决定：
  ```cpp
  decltype(auto) lookup() { return table[idx]; }   // 若 table[idx] 是引用，则 lookup 也返回引用
  ```

## 四、边界与陷阱

1. **`auto` 在列表初始化时会推导成 `std::initializer_list`**（C++11）：
   ```cpp
   auto x = {1, 2, 3};   // x 的类型是 std::initializer_list<int>
   auto y{1};            // C++17 起：y 是 int（窄化检查，单元素另一种规则）
   ```
2. **丢失引用导致意外拷贝**（见 ex02/ex03）：`auto a = getVec();` 拿到的是副本；要拿原对象用 `auto&`/`decltype(auto)`。
3. **`auto` 与 cv**：`const auto&` 才能同时「零拷贝 + 只读 + 能绑定临时」。
4. **`auto` 不能用于数组退化**：`auto arr = (int[]){1,2};` 会被推导成指针（decay 仍发生）。

## 五、可运行示例（见 examples/ex01.json、ex02.json、ex03.json）

- `ex01`：用 `static_assert` 证明 `auto i`→`int`、`auto d`→`double`、`const auto`→`const int`。
- `ex02`：`auto a = v`（副本）与 `auto& b = v`（引用）对后续 `push_back` 的影响不同。
- `ex03`：`auto x` 拷贝 vs `decltype(auto) y` 保留引用，修改 `y` 影响原始静态对象。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`auto` 默认按值推导（丢弃引用与顶层 const）**：`auto x = f();` 若 `f()` 返回引用，`x` 是拷贝。想要引用语义必须写 `auto&` / `const auto&`。
- 遍历大对象用 `const auto&` 避免拷贝；遍历 `vector<bool>` 这类代理对象要小心 `auto&&`。
- `decltype(auto)` 用于「原样保留值类别」的转发场景（如包装函数返回值）；`auto&&` 是万能引用绑定。

### 🎓 博士生视角
- `auto` 的推导规则**与模板实参推导同源**（去引用、去顶层 const、数组/函数退化为指针），保证了「`auto` = 少写一个模板参数」的一致性。
- 值类别（lvalue/xvalue/prvalue）决定绑定能力：`auto&&` 是**转发引用**，对左值推导为 `T&`、对右值推导为 `T&&`（引用折叠规则 `&& & → &`）。
- `decltype(expr)` 与 `decltype((expr))` 有微妙差异：前者得声明类型，后者因加括号变成左值而得到引用类型——这是 C++ 类型系统里少见的「括号改变类型」现象。

### 📚 考研者视角
- 408 不考 `auto`，但**「编译期类型推导」**作为「静态类型语言特性」可在简答中出现。
- 记忆锚点：**`auto` 丢引用丢 const**；**`auto&&` 万能引用（转发引用）不是右值引用**。
- 与 Java 对照：Java 的 `var` 是**类型推断但仍是引用语义**，C++ 的 `auto` 是**按值拷贝语义**——这个差别常被混淆。

---
