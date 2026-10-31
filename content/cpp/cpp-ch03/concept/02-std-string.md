# std::string 常用接口

`std::string` 是可增长的字符序列，自带长度与丰富接口，替代易出错的 C 字符串。本章聚焦**接口的正确用法与代价**——同一个目标往往有多种写法，选错的那种会慢一个数量级。

## 一、容量、长度与 SSO

`string` 有三个与"大小"相关的量：

- `size()` / `length()`：当前字符数（两者等价，`length` 是历史遗留同义词）。
- `capacity()`：当前分配可容纳的字符数（不含结尾 `\0`）。
- `max_size()`：理论上限。

短字符串（libstdc++ 15 字节、libc++ 22 字节以内）走 **SSO**，内容存在对象内部，`capacity()` 会报告一个不小于 15 的值但**没有堆分配**。所以"`capacity() > size()` 就是已分配堆"的推断是错的。

```text
string 的接口分层

  观察类   size / length / empty / capacity / max_size
  访问类   operator[]（无检查） / at（抛异常） / front / back / data / c_str
  修改类   append / push_back / insert / erase / replace / clear / resize
  查找类   find / rfind / find_first_of / find_last_of （未找到 → npos）
  视图类   substr（拷贝） / compare（不拷贝）
```

## 二、查找：`npos` 不是 `-1`

`find` 系列返回 `size_type`（无符号），未找到时返回 `std::string::npos`，其值是 `size_type` 的最大值——**不是 `-1`**，尽管在很多实现里它的位模式与 `-1` 相同。

```cpp
if (s.find("x") == std::string::npos) { /* 未找到 */ }   // 正确
if (s.find("x") < 0) { /* 永远为假 */ }                  // 错误且无告警
```

后者的错误在于：无符号值与 0 比较永远不小于 0。这类 bug 编译器通常只在开启 `-Wtype-limits` 时提示。

`find` 的第二个参数是起始位置，循环查找要 `pos = s.find(t, pos + 1)`，注意 `+1` 而不是用返回值本身（否则原地死循环）。

## 三、修改：什么时候会重新分配

- `append` / `push_back` / `+=`：容量足够时原地追加；不足时扩容（成倍增长）并搬移。
- `insert(pos, ...)`：**总是**搬移 `pos` 之后的全部字符，O(n)。
- `erase(pos, n)`：同样搬移，O(n)。反复 `erase` 头部是 O(n²)。
- `replace`：等长替换可以原地做，变长替换等同"删 + 插"。
- `resize(n)`：增大时补字符（默认 `\0`），缩小时不释放容量。

**循环拼接的写法差别很大**：

```cpp
std::string s;
s.reserve(1000);                  // 一次分配
for (int i = 0; i < 1000; ++i) s += std::to_string(i);   // 均摊 O(n)
```

不 `reserve` 也不会是 O(n²)——因为扩容是成倍的，均摊 O(n)。真正 O(n²) 的是 `s = s + x`：每次构造一个临时对象再赋值，多一次完整拷贝。

## 四、与 C 接口互转

- `c_str()`：返回以 `\0` 结尾的 `const char*`，**在下次修改或销毁后失效**。
- `data()`：C++11 起与 `c_str()` 等价（也保证 `\0` 结尾）；C++17 起有非 const 重载，可写。
- `std::string(const char*, n)`：从指针与长度构造，**即使没有 `\0` 也能安全构造**（这是接收二进制数据的正确姿势）。
- `s.assign(p, n)` / `s.append(p, n)`：同上。

接收外部数据时优先用"指针 + 长度"构造，而不是假定 `\0` 结尾——网络包、文件块里常常没有 `\0` 终止符。

## 五、比较与排序

`string` 的 `operator<` 按**逐字节字典序**比较，`std::string` 因此可直接放进 `std::set`/`std::map`/`std::sort`。

注意 `compare()` 与 `operator<` 的区别：`compare` 返回负/零/正表示大小关系，适合三路比较场景；`operator<` 只给布尔。C++20 起可用 `<=>`。

还要注意**编码**：UTF-8 的字节序比较等于码点序（因为 UTF-8 的设计保证了这一点），但 `std::string` 不知道编码，`toupper` 之类的字符处理对多字节字符是错的。

## 六、边界与陷阱

- **`find` 与 `npos` 比较**：别写 `< 0`；也不要把 `npos` 当 `-1` 参与算术（`npos + 1` 回绕成 0，可能造成死循环）。
- **`c_str()` 跨修改使用**：任何可能扩容的操作都会让旧指针悬垂。
- **`substr` 是拷贝**：循环里 `s = s.substr(1)` 是 O(n²)，改用索引或 `string_view`。
- **`operator[]` 不检查**：`s[s.size()]` 在 C++11 起是合法的（返回 `\0` 的引用），但**修改它**是 UB。
- **`std::string` 不等于 UTF-8 字符串**：`size()` 是字节数，`s[i]` 是字节，不是字符。
- **`erase` 的返回值**：C++11 起返回 `*this` 的引用，可链式；老代码里有的实现返回 `iterator`，注意版本。

## 七、可运行示例：验证 npos、SSO 与拷贝代价

```cpp
#include <iostream>
#include <string>

int main() {
    std::string s = "hello world";
    std::cout << "find=" << s.find("world") << " npos=" << (s.find("xyz") == std::string::npos) << "\n";
    std::cout << "substr=" << s.substr(6, 5) << " len=" << s.substr(6, 5).size() << "\n";

    std::string short_s = "abc";
    std::string long_s(100, 'x');
    std::cout << "short cap=" << short_s.capacity() << " long cap=" << long_s.capacity() << "\n";

    std::string built;
    built.reserve(64);
    for (int i = 0; i < 5; ++i) { built += std::to_string(i); built += ','; }
    std::cout << "built=" << built << " size=" << built.size() << " cap=" << built.capacity() << "\n";

    const char raw[] = {'a', 'b', 'c'};        // 没有 \0
    std::string safe(raw, 3);                  // 用长度构造，安全
    std::cout << "raw_len=" << safe.size() << " content=" << safe << "\n";
}
```

最后三行演示了一个容易忽略的点：没有 `\0` 的字节块用 `(ptr, n)` 构造是安全的，用 `std::string(raw)` 则会越界读。

## 三视角解析

### 🧑‍💻 程序员视角
- 循环里拼接字符串别写 `s = s + x`（每次都可能重新分配，整体 O(n²)）；用 `+=` 并配合 `reserve` 预分配。
- `find` 找不到时返回 `std::string::npos`（不是 −1）；判断要写 `if (s.find(t) == std::string::npos)`。
- `c_str()` 返回的指针在 `string` 被修改或销毁后**立即失效**，传给 C API 时不要在期间改动字符串。
- 接收外部二进制数据用 `std::string(ptr, len)`，不要假设 `\0` 结尾。

### 🎓 博士生视角
- `string` 的容量增长与 `vector` 类似（成倍增长），并有 **SSO**：短字符串内容存在对象内部的缓冲里，因此「构造小字符串不分配堆内存」。
- `c_str()` 保证返回以 `\0` 结尾的连续缓冲，但这个缓冲的**生命周期与 string 绑定**——修改 string 可能触发重新分配，旧指针随之悬垂。这是「非拥有视图」问题的又一实例。
- `string` 与 `string_view` 的分工体现「所有权」设计：`string` 拥有并管理缓冲，`string_view` 只观察；C++ 把「谁负责生命周期」显式交给程序员，因此接口设计必须明确标注「不拥有」。
- 与 C 的 `char*` 对比：`string` 把长度与容量一并维护，消除了「长度与缓冲不同步」这类 C 语言的常态风险。
- `std::string` 的复杂度保证由标准固定：`size`/`capacity`/`operator[]`/`back` 为 O(1)，`find` 未规定上限（实际是朴素匹配或实现自选的优化算法），`insert`/`erase` 为 O(size)。

### 📚 考研者视角
- 与 408 的**串**（顺序存储 / 堆分配存储 / 块链存储）及模式匹配对应。
- 常考：串的基本操作（求子串、比较、连接）的实现与复杂度；KMP 的 next 数组推导（见 fund-ch18）。
- 常考辨析：`substr` 是拷贝还是视图（拷贝）；`find` 失败返回什么（`npos`）。
- 记忆锚点：**`c_str()` 的指针会在 string 修改后失效**；**循环拼接要先 `reserve`**；**`npos` 是无符号最大值，不能当 -1 用**。
