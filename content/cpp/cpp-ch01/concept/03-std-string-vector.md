# std::string 与 std::vector 入门

字符串与动态数组是日常开发最高频的容器。标准库已提供成熟实现：`std::string` 管理字节序列的所有权与扩容，`std::vector<T>` 是唯一的连续动态数组。手搓 C 风格字符数组几乎总是错的选择——除非你在写不依赖标准库的内核或嵌入式代码。

## 一、`std::string` 是什么：带所有权语义的字节容器

`std::string` 的本质是 `std::basic_string<char>`：**一段连续的 `char`，加长度，加容量**。它不含编码信息——"字符串"在 C++ 里就是字节序列，UTF-8 的中文一个字占 3 字节，`size()` 返回的是字节数而不是字数。

核心操作与代价：

- `+`/`append`：追加，容量不足时扩容（一般按 1.5~2 倍增长）。
- `substr(pos, len)`：**返回新字符串**，是拷贝，不是视图。
- `find`/`rfind`：子串查找，无额外分配。
- `c_str()`：返回 `const char*` 供 C 接口使用，指针在下次修改后失效。
- `[]`：不做边界检查；`at()` 做检查并抛 `std::out_of_range`。

### SSO：短字符串为什么快

短字符串优化（Small String Optimization）把较短的内容（GCC/libstdc++ 是 15 字节，libc++ 常见 22 字节）直接存进对象内部的缓冲，**完全不触发堆分配**。所以 `std::string s = "hi";` 一次 `malloc` 都没有。

代价是对象本身变大（32 字节左右），且**移动一个短字符串仍需逐字节拷贝**（因为它存在栈上的对象体内，不能只搬指针）。这解释了一个反直觉现象：大量短字符串的容器，瓶颈常在对象体积而不是堆分配。

```text
std::string 的两种存储形态（libstdc++，64 位）

  短串（≤15 字节）      长串（>15 字节）
  ┌──────────────┐      ┌──────────────┐
  │ ptr ────────►│ 指向  │ ptr ─────────┼──► 堆上缓冲
  │ size         │ 自身  │ size         │
  │ 内联缓冲 16B │ 缓冲  │ capacity     │
  └──────────────┘      └──────────────┘
  无堆分配              1 次分配 + 扩容时搬移
```

## 二、`std::vector<T>` 是什么：三指针 + 扩容策略

`vector` 的经典实现是**三个指针**：`begin`（首元素）、`end`（末尾后一位）、`capacity_end`（容量末尾）。因此 `size()` 与 `capacity()` 都是指针相减，O(1)，且 `size()` 不需要额外字段。

- `push_back`：均摊 O(1)。容量满时按倍数扩容（2 倍或 1.5 倍），把旧元素搬过去再释放旧块。
- `insert`/`erase` 中间位置：O(n)，因为要搬移后续元素。
- `reserve(n)`：一次分配到位，**只改 capacity 不改 size**。
- `resize(n)`：改 size，新增元素被值初始化。
- `shrink_to_fit()`：请求释放多余容量，非强制。

**扩容会让所有迭代器、指针、引用失效**。这是"连续存储"的直接代价，也是 `vector` 与 `list`/`map` 迭代器失效规则不同的根源——后两者只有被删元素失效。

```cpp
std::vector<int> v;
v.reserve(1000);            // 一次分配，避免 10 次扩容
for (int i = 0; i < 1000; ++i) v.push_back(i);
```

`reserve` 是最高性价比的优化之一：知道规模时先预留，扩容次数从 O(log n) 降到 0。

### 移动还是拷贝：`noexcept` 的真实作用

扩容时 `vector` 要搬移旧元素。若元素的移动构造是 `noexcept`，用移动（快）；否则**退化为拷贝**——因为移动一旦抛异常，原容器已被破坏，无法回滚到强异常安全。这就是标准库大量给移动构造标 `noexcept` 的原因，也是自定义类型该跟着标的原因。

## 三、与 C 风格接口的边界

`std::string` 与 `std::vector` 都能和 C API 互操作，但边界上容易出事：

```cpp
std::string s = "abc";
const char* p = s.c_str();     // 仅在下一次修改前有效
s += "def";                    // 可能扩容 → p 悬垂
```

`std::vector<char>` 的 `data()` 同理。给 C 函数传缓冲时，注意三点：**缓冲生命周期、是否以 `\0` 结尾、长度由谁传**。`string` 保证 `c_str()` 以 `\0` 结尾，`vector<char>` 不保证。

## 四、选型：什么时候不用 `vector`

- 需要**稳定地址**（元素被外部持有指针）→ `std::deque` 或 `std::list`。
- 需要**频繁头部插入** → `std::deque`。
- 需要**按键查找** → `std::unordered_map`（哈希）或 `std::map`（有序）。
- 需要**只读视图、不拷贝** → `std::string_view`（见 cpp-ch03）或 `std::span`。

`vector` 是默认选择，因为它对缓存最友好：连续内存让预取器有活干，这是它在实测中常常比"理论上更快"的链表快一个数量级的原因。

## 五、边界与陷阱

- **`size()` 是无符号**：`for (int i = 0; i < v.size(); ++i)` 会触发符号比较告警，且 `v.size() - 1` 在空容器上回绕成巨大值。
- **`operator[]` 不检查边界**：越界是 UB，不抛异常。调试期可用 `at()` 或开了 `_GLIBCXX_ASSERTIONS` 的构建。
- **`reserve` 不等于 `resize`**：`reserve` 后 `size()` 仍是 0，直接 `v[0]` 访问是 UB。
- **`substr` 是拷贝**：循环里 `s = s.substr(1)` 会退化成 O(n²)，改用 `std::string_view` 或索引。
- **`std::vector<bool>` 不是普通容器**：位压缩特化，`&v[0]` 拿不到 `bool*`，不能当 C 数组传给 C API。
- **范围 for 中修改容器**：`for (auto& x : v) v.push_back(x);` 迭代器失效，UB。

## 六、可运行示例：观察容量增长与 SSO

```cpp
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::string name = "Cpp";
    std::string greet = "Hello " + name;
    std::cout << greet << " len=" << greet.size() << "\n";

    std::vector<int> nums;
    std::size_t last_cap = 0;
    for (int i = 0; i < 20; ++i) {
        nums.push_back(i);
        if (nums.capacity() != last_cap) {          // 只在扩容时打印
            std::cout << "size=" << nums.size()
                      << " cap=" << nums.capacity() << "\n";
            last_cap = nums.capacity();
        }
    }

    std::vector<int> reserved;
    reserved.reserve(16);
    std::cout << "after_reserve size=" << reserved.size()
              << " cap=" << reserved.capacity() << "\n";
}
```

这段程序同时验证了三件事：容量按倍数增长（次数是 O(log n)）、`reserve` 只改容量不改长度、`string` 直接拼接可用。容量增长的**具体倍数由实现决定**（libstdc++ 是 2 倍，libc++ 常见 1.5 倍），所以别把具体数字写进断言。

## 三视角解析

### 🧑‍💻 程序员视角
- `std::string` 是**字节序列**：存 UTF-8 时 `size()` 返回字节数而不是「字符数」，处理中文/emoji 要格外小心。
- `std::vector` 是默认容器选择；已知规模就 `reserve`，能省掉多次扩容与搬移。
- 短字符串有 **SSO（小字符串优化）**：小字符串直接存在对象内部，不触发堆分配——这解释了为什么大量短字符串的容器并不像想象中那么慢。
- 接口边界上，返回 `const std::string&` 比返回 `std::string` 少一次拷贝；但**返回局部变量的引用是悬垂**，要返回就走值（依靠 RVO/NRVO）。

### 🎓 博士生视角
- **SSO** 把短字符串（通常 15 或 22 字节以内，取决于实现）存在 `string` 对象自身的缓冲里，用「对象变大」换「避免堆分配」。这是「小对象优化」思路在标准库中的经典落地。
- `vector` 的实现通常是**三指针模型**（`begin` / `end` / `capacity_end`），因此 `size()` 与 `capacity()` 都是指针相减（O(1)）。
- **扩容会导致所有迭代器、指针、引用失效**，而 `list`/`map` 只有被删元素失效——这一差异是「连续存储」与「节点存储」的直接后果，也是迭代器失效规则的分类依据。
- 与之相关的是移动语义：`vector` 扩容时**优先移动**（前提是元素的移动构造标了 `noexcept`），否则退化为拷贝——这就是 `noexcept` 在性能上的实际影响点。
- 摊还分析给出 `push_back` 的均摊 O(1)：设倍增因子为 k>1，n 次插入的总搬移量是几何级数，上界为 n·k/(k−1)，故均摊为常数。

### 📚 考研者视角
- **408 数据结构直接对应**：顺序表（`vector`）、串（`string`）的存储结构与操作；动态数组的**均摊 O(1)** 追加。
- 常考计算：顺序表插入/删除的平均移动次数（插入平均 n/2、删除平均 (n−1)/2）、扩容后的容量变化。
- 常考辨析：顺序表 vs 链表在查找/插入/删除上的复杂度、缓存局部性差异。
- 记忆锚点：**`string` 是字节序列（`size()` 是字节数）**；**`vector` 扩容会让所有迭代器失效**；**`reserve` 改容量不改长度**。
