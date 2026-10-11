# 04 · 结构化绑定、`std::optional` 与 `std::string_view`

## 一、结构化绑定（Structured Bindings，C++17）

语法 `auto [a, b, c] = e;` 把 `e` 的「成员/元素」绑定到一组名字上。可用于：

- `std::pair` / `std::tuple`（按 `get<N>` 拆包）
- 数组（`[x, y]` 解数组前两个元素）
- 有公开数据成员的 `struct`（按声明顺序拆成员）

```cpp
std::map<int, std::string> m{{1,"one"},{2,"two"}};
for (const auto& [key, val] : m) { /* key、val 是引用别名 */ }
```

**底层机制（博士视角）**：`auto [a, b] = m.begin()->...` 实际引入一个匿名对象 `__e` 绑定到原对象，`a`/`b` 是 `__e` 上 `get<0>(__e)` / `get<1>(__e)` 的**引用别名**。因此 `const auto& [k, v]` 时 `k`、`v` 是对 map 节点成员的 `const` 引用，**不会拷贝**；用 `auto [k, v]`（按值）才会把 key/value 拷出来。遍历大对象务必写 `const auto&`。

## 二、`std::optional<T>`：可能有也可能没有的值

表示一个「可能为空」的值，比「用特殊哨兵值（如 -1、nullptr）」更安全、更自文档化：

```cpp
std::optional<int> find_even(int n) {
    if (n % 2 == 0) return n;     // 隐式构造 optional（有值）
    return std::nullopt;          // 明确表示「无值」
}
if (auto r = find_even(4); r) std::cout << *r;   // 用 bool 转换判断，用 * 取值
```

**设计取舍**：
- ✅ 类型安全：调用方**必须**检查是否有值，不能误用哨兵。
- ✅ 不强制堆分配：`optional` 通常在栈上（值内嵌），比返回指针轻。
- ⚠️ `T` 需要可拷贝/可移动；对不可移动的大对象稍重。
- ⚠️ 不要拿 `optional<T&>`（不存在）——要「可能为空的引用」用指针。

## 三、`std::string_view`：零拷贝字符串视图

`std::string_view` 只是 `{const char* ptr, size_t len}` 两个字的**非拥有视图**，不分配内存、不拷贝字符：

```cpp
std::string_view sv = "hello";
auto sub = sv.substr(0, 3);   // O(1)：只调指针与长度，不拷贝 "hel"
```

**设计取舍**：

| 维度 | `std::string` | `std::string_view` |
|---|---|---|
| 内存 | 拥有、可能堆分配 | 不拥有，仅视图 |
| 拷贝成本 | 可能深拷贝 | 指针+长度，常数 |
| 改内容 | 可改 | 只读 |
| 生命周期 | 自己管 | **依赖被引用对象存活** |

**最大陷阱——悬垂（dangling）**：`string_view` 不延长被引用字符串的生命。以下全是 UB：

```cpp
std::string_view bad() {
    std::string s = "temp";
    return s;            // ❌ 返回后 s 被析构，视图悬垂
}
auto d = std::string("x") + "y";   // 临时 string
std::string_view sv = d;           // ❌ 临时已销毁（某些实现会警告）
```

**适用**：函数参数接收「只读字符串」时优先 `string_view`（既能接 `string` 又能接字面量，且零拷贝）；一旦需要**长期持有**字符串，转成 `std::string`。

## 四、工程实践小结

- 拆包用结构化绑定；遍历关联容器永远 `const auto& [k, v]`。
- 函数「可能无结果」用 `optional<T>` 而非哨兵/指针。
- 只读字符串参数用 `string_view`；跨作用域保存字符串用 `string`。
- C++20 还有 `std::span`（数组视图）、`std::string_view` 的 `starts_with`/`contains` 等便捷接口。

## 五、可运行示例（见 examples/ex09.json、ex10.json）

- `ex09`：用 `auto [k, val]` 遍历 `map`，用 `auto [a,b,c]` 拆 `tuple`。
- `ex10`：`string_view` 零拷贝取子串；`optional` 返回/判空/取值。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **结构化绑定**（`auto [k, v] : map`）让遍历 map 可读性大增；注意 `auto [k, v]` 默认是**拷贝**，要引用必须 `auto& [k, v]`。
- **`std::optional<T>`** 是「可能没有值」的零开销（几乎）表达，比「返回 -1 / nullptr / 空字符串」这类哨兵值**类型安全**得多。
- **`std::string_view` 是「不拥有数据的字符串引用」**：传参用它可避免临时 `std::string` 构造；但**绝不能返回指向局部变量的 view**（悬垂）。

### 🎓 博士生视角
- 结构化绑定是对**聚合体/元组协议**的统一解构：它对数组、`std::tuple`、`std::pair`、以及「公有非静态成员全是直接成员」的聚合类都生效，本质是**编译期按位置绑定**（不是运行期反射）。
- `optional` 表达的是**「值语义的 maybe monad」**：把「缺失」编码进类型，迫使调用方显式处理，消除了哨兵值的语义重载（`-1` 到底是「未找到」还是「真的 -1」）。
- `string_view` 是把「**借用语义（borrowing）**」引入标准库的一步：与 Rust 的 `&str` 对应，代价是**生命周期安全靠程序员而非编译器**检查（C++ 无借用检查器）。

### 📚 考研者视角
- 记忆锚点：**结构化绑定默认拷贝，引用要加 `&`**；**`string_view` 不拥有数据、生命周期由调用方保证**。
- 常考对比：`optional<T>` vs 哨兵值 vs 异常——三种「表示失败」的方案，各自适合什么场景（性能敏感→optional，异常路径→exception，哨兵→C 风格接口）。
- 与数据库的 `NULL` 对照：`optional` 就是类型系统层面的「可空」，且比 SQL NULL 的「三值逻辑」更简单明确。

---
