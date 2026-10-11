# 01 · vector：连续内存、2× 扩容与迭代器失效

## 一、理论根基：为什么需要「可增长数组」

高级语言的第一性需求之一，是**在保留数组 O(1) 随机访问的同时，又能按需增长**。C 风格数组长度固定，手动 `realloc` 既繁琐又易错。C++ 的标准答案是 `std::vector`——它是一个**将「连续裸数组 + 长度/容量簿记」封装为 RAII 对象」的序列容器**。

它的本质可以抽象为三个指针（libstdc++ 的 `_Vector_impl` 即如此）：
- `start`：首元素地址
- `finish`：最后一个有效元素的下一个位置（`size() = finish - start`）
- `end_of_storage`：已分配内存块的末端（`capacity() = end_of_storage - start`）

> 关键点：**逻辑长度 `size` 与物理容量 `capacity` 解耦**。`size` 是用户看到的元素数，`capacity` 是已向堆申请、尚未归还的内存能容纳的元素数。正是这一解耦，带来了「摊还 O(1) 扩容」。

## 二、实现机制：amortized 2× 扩容到底发生了什么

当 `push_back` 时发现 `finish == end_of_storage`（空间已满），容器必须扩容，标准流程是：

1. 计算新容量：标准只要求「不小于旧容量的某种增长」。**主流实现（libstdc++ / libc++）采用近似 2 倍**（实际是 `max(2*old, need)`，且通常向上取到 `_M_max_size` 等约束），MSVC 的 Dinkumware 历史上用过 1.5 倍。本章以 2× 为讲解模型。
2. 分配新块：`allocate(new_cap)`（通常 `new` 一块连续内存）。
3. **移动/拷贝**旧元素到新块（C++11 起对可移动类型用移动构造，否则拷贝）。
4. 释放旧块（`deallocate`），更新三个指针。

为什么 2× 能保证 `push_back` 摊还 O(1)？设第 i 次扩容容量为 `C_i`。在第 i 次扩容时，我们为 `C_i` 个元素「一次性搬了 `C_{i-1}` 个」。把 n 次 `push_back` 的总搬运量加起来是一个**等比数列** `1+2+4+...+n < 2n`，故均摊到每次操作是 `O(1)`。若每次只 +1（线性增长），总搬运量是 `1+2+...+n = O(n²)`，均摊 O(n)，不可接受——这正是「指数级扩容换摊还常数」的精髓。

> **reserve / resize 区别**（程序员极易混）：
> - `reserve(n)`：只改 `capacity`（必要时扩容），**不改 `size`**，不构造元素。用于「已知大概要装多少」时避免反复扩容。
> - `resize(n)`：改 `size`——`n>size` 时**在尾部构造** `n-size` 个值初始化元素（或指定值），`n<size` 时**析构**多余元素。`resize` 会触发 `capacity` 增长但不缩减 `capacity`。
> - `shrink_to_fit()`：非强制请求把 `capacity` 降到 `size`（实现可忽略）。

## 三、实现机制：迭代器/引用/指针的失效规则

因为扩容是「搬家到新地址」，旧块上的所有指针/引用/迭代器全部悬空。规则（[vector.modifiers]，C++ 标准）：

| 操作 | 失效范围 |
|---|---|
| `push_back` / `emplace_back`（**发生扩容**） | **所有**迭代器、引用、指针失效 |
| `push_back`（未扩容） | 仅 `end()` 迭代器失效；元素引用/迭代器仍有效 |
| `insert`/`emplace`（中间/头部） | 插入点及之后**所有**迭代器、引用、指针失效 |
| `erase(pos)` | `pos` 及之后所有迭代器、引用、指针失效 |
| `resize` 导致扩容 | 同 `push_back` 扩容 |

> 注意 `swap` 和 `clear`：`clear()` 使所有元素迭代器失效但 `capacity` 不变；`swap` 后两个容器的迭代器/引用**互换有效范围**（各自指向对方原来的元素块），C++11 起这是 O(1) 指针交换。

## 四、工程实践：什么时候用 vector，怎么用

1. **默认首选容器**：只要没有「频繁在头部/中间插入删除」的硬性需求，`vector` 几乎永远是对的——它缓存最友好（连续内存顺序遍历能打满 prefetch），算法最多（`<algorithm>` 全部适配随机访问迭代器）。
2. **预分配**：已知规模就 `reserve`，既省扩容开销又避免扩容导致的迭代器失效（见 pitfalls）。
3. **尾部增删用 `emplace_back` 而非 `push_back`**：`emplace_back(args...)` 在容器内**就地构造**，少一次移动/拷贝；`push_back(T(args...))` 先在外部构造临时对象再移动。
4. **删除用 `erase` + 返回值推进**：`it = v.erase(it);` 不要 `v.erase(it++` 的过时写法（对 vector 仍对，但 `it=erase(it)` 更通用、对 list 也正确）。

## 五、边界与陷阱

- `operator[]` **不做越界检查**（为性能），越界是 UB；`at()` 抛 `std::out_of_range`，调试期想要安全用 `at`。
- 在 `range-for`（`for (auto& x : v)`）体内 `push_back` 可能触发扩容使 `x` 悬空——这是 UB。
- 保存 `v.data()` 或 `&v[0]` 的裸指针跨任何可能扩容/缩容的操作后必须重新取。
- `capacity` 增长策略是实现定义的，不要依赖「恰好 2×」写死逻辑；写测试时只断言「容量不减到更小」。

## 六、可运行示例：眼见为实

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v;
    std::cout << "empty: size=" << v.size() << " cap=" << v.capacity() << '\n';
    for (int i = 0; i < 9; ++i) {
        v.push_back(i);
        std::cout << "after push " << i
                  << ": size=" << v.size()
                  << " cap=" << v.capacity() << '\n';
    }
    // reserve 后不再扩容
    v.reserve(100);
    std::cout << "after reserve(100): cap=" << v.capacity() << '\n';
}
```

**输出**：
```
empty: size=0 cap=0
after push 0: size=1 cap=1
after push 1: size=2 cap=2
after push 2: size=3 cap=4
after push 3: size=4 cap=4
after push 4: size=5 cap=8
after push 5: size=6 cap=8
after push 6: size=7 cap=8
after push 7: size=8 cap=8
after push 8: size=9 cap=16
after reserve(100): cap=100
```

> 观察点：容量序列 `0→1→2→4→8→16` 正是「指数扩容」；`reserve(100)` 后容量一次到位，后续 `push_back` 不再搬移，迭代器稳定。

## 七、与 Java 对照

| 维度 | C++ `std::vector` | Java `ArrayList` |
|---|---|---|
| 底层 | 连续堆数组，RAII 自动释放 | 连续堆数组，`Object[]`，GC 回收 |
| 扩容因子 | 通常 2× | 1.5×（JDK `old + (old >> 1)`） |
| 随机访问 | `v[i]`，O(1) | `list.get(i)`，O(1) |
| 元素类型 | 可存 `int` 等 POD（无装箱） | 自动装箱 `Integer`（有对象开销） |
| 扩容失效 | 引用/迭代器失效（UB 风险） | 迭代器 fail-fast 抛 `ConcurrentModificationException` |

> C++ 把「是否失效」交给程序员自律（不检查、零开销）；Java 用运行时异常兜底——这是两种语言哲学差异的缩影。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`reserve` 是最廉价的性能优化**：已知规模先 `reserve`，避免多次扩容与整体搬移（实测常见 2–3 倍差距）。
- **迭代器失效是 vector 最大的坑**：任何可能扩容的操作（`push_back`、`insert`、`resize`）都会让**全部**迭代器/引用失效；循环里删元素请用「下标 + 手动 --i」或 `erase-remove` 惯用法。
- 首选 `emplace_back` 构造、`push_back(std::move(x))` 移动已有对象；`shrink_to_fit` 只是请求，不保证释放。

### 🎓 博士生视角
- 扩容倍率（libstdc++/MSVC 常为 2×、libc++ 为 1.5×）决定**均摊 O(1)** 的证明：等比增长下总搬移次数为**几何级数**，和 ≤ 2n，故单次摊还 O(1)。**常数因子 1.5 vs 2 是「可复用已释放内存」与「总搬移量」的权衡**。
- vector 是**缓存最优**的容器：顺序访问的 cache miss ≈ n·sizeof(T)/64，是「数组几乎总是默认答案」的物理依据。
- 引用/指针失效与**内存重分配**绑定；`reserve` 的本质是把「多次重分配」提前成「一次」。

### 📚 考研者视角
- 408 顺序表考点：**插入/删除的平均移动次数**（插入 n/2、删除 (n−1)/2）、扩容的**均摊分析**（等比增长 → 摊还 O(1)）。
- 常考辨析：顺序表「随机访问 O(1)」vs 链表「插入删除 O(1)（前提是已定位前驱）」。
- 记忆锚点：**动态数组扩容是均摊 O(1)，不是每次 O(1)**；这个「摊还」概念是 408 与算法课共同的重点。

---
