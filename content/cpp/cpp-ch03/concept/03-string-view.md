# std::string_view 零拷贝视图

`std::string_view` 是**不拥有数据的只读视图**（指针 + 长度），避免了为取子串而拷贝整个 `std::string`。

它解决的问题很具体：函数只想"看一眼"字符串，却被迫在传 `std::string` 时接受拷贝、传 `const char*` 时丢掉长度。`string_view` 把这两个参数打包成一个类型，于是既能零拷贝、又能同时接收 `string`/字面量/`char*`。

## 一、它到底是什么：两个字段

```cpp
struct string_view {          // 概念示意，实际实现略有差异
    const char* data_;
    std::size_t size_;
};
```

- **构造不拷贝**：`string_view v(s)` 只记录 `s.data()` 与 `s.size()`。对 `std::string` 是 O(1)。
- **`substr` 不拷贝**：`v.substr(pos, n)` 只调整指针与长度，仍是 O(1)。这是它相对 `string::substr` 最大的价值。
- **`remove_prefix(n)` / `remove_suffix(n)`**：直接挪动指针，O(1)，适合分词/解析。

代价是：`string_view` **不知道底层数据什么时候死**，因为它只有一个裸指针。

## 二、生命周期：唯一的、也是致命的风险

```cpp
std::string_view bad() {
    return std::string("tmp");     // 编译通过，运行时悬垂
}
std::string_view v = std::string("tmp") + "!";
// 这一行结束时临时 string 销毁，v 立即悬垂
```

这两种写法都**编译通过、无告警**（部分编译器对第一种给 `-Wreturn-stack-address` 之外的提示，但不可依赖）。原因是 `string_view` 有从 `const char*` 与 `std::string` 的隐式转换构造，编译器无法区分"底层活得够久"与"底层马上死"。

安全的用法只有三类：

1. **形参**：`void f(std::string_view)`——调用期间底层对象一定存活（调用方持有它）。
2. **指向字面量或静态数据**：`string_view v = "abc";` 字面量有静态存储期。
3. **指向调用方持有的对象**：`string_view v = owner.name;` 只要 `owner` 活着。

不安全的典型：**返回 `string_view`、存进成员、投递给异步任务、在循环里指向临时 `string`**。

```text
string_view 的生命周期契约

  调用方 ──持有──► std::string 所有者
                        │ data() + size()
                        ▼
                    string_view（只观察）
                        │
  规则：视图的存活期必须严格短于底层对象的存活期
        类型系统不检查这一条 —— 全靠接口契约与代码审查
```

## 三、它不保证什么

三个常见误解：

- **不保证 `\0` 结尾**。`v.substr(2)` 可能指向大字符串中间，直接传给 `printf("%s")` 会越界读。需要 C 字符串时先用 `std::string(v)` 拷一份。
- **不是"只读的 string"**。它没有 `c_str()`，没有 `push_back`，不能修改（`data()` 返回 `const char*`）。
- **不支持隐式转换回 `string`**。`std::string s = v;` 在 C++17 起是 explicit 的，要写 `std::string{s}` 或 `std::string(v)`——这个 explicit 是刻意的，防止无意的拷贝被藏起来。

## 四、什么时候该用它

**该用**：

- 函数参数只需要读字符串：`void log(std::string_view msg)`。这比 `const std::string&` 更通用——后者会迫使调用方先构造 `string`（传字面量时会产生临时对象）。
- 解析器/分词器：反复 `substr` + `remove_prefix` 全零拷贝。
- 只读查表：`std::map<std::string, X>` 用 `find(view)` 在 C++14 起可行（异构查找）。

**不该用**：

- 需要存储（成员变量、容器元素）→ 用 `std::string`。
- 需要修改 → `std::string`。
- 需要传给接受 `const char*` 的 C 函数 → 先转 `std::string`。
- 返回给调用方 → 除非指向静态数据，否则 `std::string`。

## 五、与其它"视图类型"的共同模式

C++17 之后标准库引入了成组的视图类型：`string_view`、`span<T>`（C++20）、`function_ref`（提案中）。它们的共同点：

- **不拥有数据**（non-owning）
- **零拷贝构造**
- **生命周期由外部保证**，类型系统不检查

这是"零开销抽象"哲学的直接产物：标准库给你工具，但不给你安全带。相比之下 Rust 的 `&str`/`&[T]` 带生命周期参数，编译期就能拒绝悬垂视图——两种语言在"性能上限"与"默认安全"之间的取舍完全不同。

## 六、边界与陷阱

- **绑定临时 `string` 立即悬垂**：`string_view v = std::string("x");` 是本章头号杀手。
- **不保证 `\0` 结尾**：`substr` 出来的视图不能直接给 C API。
- **`data()` 可能为空且非空 size**：空视图的 `data()` 可以是 `nullptr`，别对它解引用。
- **比较是按字节**：`string_view` 与 `string` 比较语义一致，但混用 `==` 时要注意类型转换方向。
- **不要从函数返回局部 string 的视图**：包括"返回 `s.substr()` 的视图"这种隐蔽形式。
- **`std::string_view` 与 `std::string` 重载冲突**：同时提供 `f(string)` 与 `f(string_view)` 会让字面量调用产生歧义。

## 七、可运行示例：零拷贝分词器

```cpp
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

std::vector<std::string_view> split(std::string_view sv, char sep) {
    std::vector<std::string_view> out;
    std::size_t start = 0;
    while (start <= sv.size()) {
        std::size_t pos = sv.find(sep, start);
        if (pos == std::string_view::npos) {
            out.push_back(sv.substr(start));       // 只改指针与长度
            break;
        }
        out.push_back(sv.substr(start, pos - start));
        start = pos + 1;
    }
    return out;
}

int main() {
    std::string owner = "cpp,string,view,demo";     // 底层数据由 owner 持有
    auto parts = split(owner, ',');
    for (auto p : parts) std::cout << '[' << p << "] ";
    std::cout << "\ncount=" << parts.size() << "\n";

    std::string_view v(owner);
    v.remove_prefix(4);                             // 0 次拷贝
    std::cout << "after_prefix=" << v << " size=" << v.size() << "\n";
}
```

注意 `split` 返回的 `vector<string_view>` **只在 `owner` 存活期间有效**。这正是"不拥有"的契约：函数的返回值没有延长任何生命周期，调用方必须自己保证 `owner` 活得更久。

## 三视角解析

### 🧑‍💻 程序员视角
- `string_view` 只读、不拥有数据：用于**函数参数**避免拷贝是它最大的价值（`void f(std::string_view sv)` 可同时接收 `string`、字面量、`char*`）。
- **绝不能**让它指向已销毁的对象：`std::string_view sv = std::string("tmp");` 这一行结束时底层缓冲就没了，`sv` 立即悬垂（这是最经典的 UB 示例）。
- 返回 `string_view` 时要确认被指向的数据活得比视图久（通常是调用方的对象或静态数据）。
- 解析场景用它替代 `substr`：`find` + `substr` + `remove_prefix` 全零拷贝，是最实用的性能优化之一。

### 🎓 博士生视角
- `string_view` 是「**非拥有视图**」的泛型化包装（指针 + 长度），用引用语义换取零拷贝。它把「生命周期由调用方保证」写成了契约——但**类型系统并不检查**它。
- 这与 Rust 的 `&str` 形成鲜明对比：`&str` 带生命周期参数，编译器会拒绝悬垂的用法。C++ 选择了「零开销 + 零检查」，把责任完全交给程序员，这是语言定位差异的直接体现。
- `string_view` 还带来一个微妙的语义变化：**不保证以 `\0` 结尾**（它可能指向大字符串的中间片段），因此不能直接传给需要 C 字符串的 API（要用 `data()` 且自行确认）。
- 从接口设计看，「视图类型」是 C++17 之后的标准模式（`string_view`、`span`、`function_ref`），共同点是「不拥有 + 零拷贝 + 生命周期外部保证」。
- 另一个易忽略点：`string_view` 的 `data()` 在空视图上可以是任意合法指针（包括 `nullptr`），因此 `sv.data()[0]` 在 `sv.empty()` 时是 UB，标准库实现之间表现可能不同。

### 📚 考研者视角
- 与 C 的「指针 + 长度」双参数约定对应：`string_view` 就是把这两个参数打包成一个类型，从而恢复类型安全与可读性。
- 常考概念题：「`string` 与 `string_view` 的区别」「什么是悬垂引用/悬垂视图」。
- 常考辨析：`string_view::substr` 是 O(1) 视图、`string::substr` 是 O(n) 拷贝——这个差异是复杂度题的常见考点。
- 记忆锚点：**`string_view` 不拥有数据**；**绑定临时 `string` 会立即悬垂**；**不保证 `\0` 结尾**。
