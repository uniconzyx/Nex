# std::string 与 std::vector 入门

字符串与动态数组是日常开发最高频的容器，标准库已提供成熟实现，不要手搓 C 风格字符数组。

## 要点

- `std::string`：`+` 拼接、`size()`/`length()`、`operator[]`、`substr(pos, len)`
- `std::vector<T>`：动态数组，`push_back` 追加、`pop_back` 删除尾部、`size()` 长度
- 遍历优先用范围 for；随机访问用下标 `v[i]`
- `vector` 在尾部增删是 O(1) 均摊；中间插入是 O(n)

```cpp
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::string name = "Cpp";
    std::string greet = "Hello " + name;     // 拼接
    std::cout << greet << " len=" << greet.size() << "\n";

    std::vector<int> nums;
    nums.push_back(10);
    nums.push_back(20);
    std::cout << "sum=";
    int s = 0;
    for (int x : nums) s += x;
    std::cout << s;
}
```

---

## 三视角解析

### 🧑‍💻 程序员视角
- `std::string` 是**字节序列**：存 UTF-8 时 `size()` 返回字节数而不是「字符数」，处理中文/emoji 要格外小心。
- `std::vector` 是默认容器选择；已知规模就 `reserve`，能省掉多次扩容与搬移。
- 短字符串有 **SSO（小字符串优化）**：小字符串直接存在对象内部，不触发堆分配——这解释了为什么大量短字符串的容器并不像想象中那么慢。

### 🎓 博士生视角
- **SSO** 把短字符串（通常 15 或 22 字节以内，取决于实现）存在 `string` 对象自身的缓冲里，用「对象变大」换「避免堆分配」。这是「小对象优化」思路在标准库中的经典落地。
- `vector` 的实现通常是**三指针模型**（`begin` / `end` / `capacity_end`），因此 `size()` 与 `capacity()` 都是指针相减（O(1)）。
- **扩容会导致所有迭代器、指针、引用失效**，而 `list`/`map` 只有被删元素失效——这一差异是「连续存储」与「节点存储」的直接后果，也是迭代器失效规则的分类依据。
- 与之相关的是移动语义：`vector` 扩容时**优先移动**（前提是元素的移动构造标了 `noexcept`），否则退化为拷贝——这就是 `noexcept` 在性能上的实际影响点。

### 📚 考研者视角
- **408 数据结构直接对应**：顺序表（`vector`）、串（`string`）的存储结构与操作；动态数组的**均摊 O(1)** 追加。
- 常考计算：顺序表插入/删除的平均移动次数、扩容后的容量变化。
- 记忆锚点：**`string` 是字节序列（`size()` 是字节数）**；**`vector` 扩容会让所有迭代器失效**。
