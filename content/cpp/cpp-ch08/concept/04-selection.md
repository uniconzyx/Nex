# 04 · 容器选择、迭代器类别与缓存友好：工程决策框架

前面三讲把 `vector`/`list`/`map`/`set`/`unordered_*` 的底层讲清了。本讲回答一个**程序员每天的真实问题**：「这个场景到底该用哪个容器？」并补齐 `list`/`forward_list` 与**迭代器类别（iterator category）**。

## 一、list / forward_list：节点结构为何「缓存不友好」

`std::list` 是**双向链表**，每个节点在堆上单独 `new`，含 `prev`/`next`/`value` 三块；`forward_list` 是**单向链表**（C++11，无 `size()` 成员，更省内存）。它们的本质特征：

- **插入/删除任意位置是 O(1)**（给定迭代器后，只改几个指针，不搬移其他元素），且**不使其他迭代器/引用失效**（这是它相对 `vector` 的最大优势）。
- **致命弱点：内存不连续**。遍历时 CPU 缓存几乎每次都 miss（节点散布在堆各处），prefetcher 无从预测下一节点地址。实测上，**哪怕 `list` 的指针操作是 O(1)，其顺序遍历也常慢于 `vector` 的 O(n) 搬移**——因为 `vector` 连续内存能让缓存行（64 字节）一次喂饱 8~16 个 `int`，且可向量化。

> 博士视角：这是「**算法复杂度 ≠ 实际性能**」的典型案例。现代 CPU 的 memory hierarchy（L1/L2/L3 + prefetch）让「连续访问」比「常数次随机访问」重要得多。结论：**除非频繁在容器中部插入/删除且持有迭代器不希望失效，否则优先 `vector`**。`list` 仅适合「已知位置、频繁增删、且增删远多于遍历」的场景（如 LRU 链表的指针搬运）。

## 二、迭代器类别（Iterator Categories）

迭代器的能力层级决定了哪些算法能用它。按由弱到强：

| 类别 | 能力 | 典型容器 |
|---|---|---|
| 输入/输出迭代器 | 单向读/写一次 | `istream_iterator` |
| 前向迭代器 | 可多次单向遍历 | `forward_list`、`unordered_*` |
| 双向迭代器 | 可 `--`/`++` | `list`、`map`、`set`、`multimap`、`multiset` |
| 随机访问迭代器 | 可 `it+n`、`it1-it2`、`<` | `vector`、`deque`、`array`、`string` |
| 连续内存迭代器（C++20） | 随机访问 + 连续存储 | `vector`、`array`、`string` |

含义：
- `vector` 的随机访问让它兼容 `std::sort`/`std::binary_search` 等要求随机访问的算法（O(n log n)）。
- `list`/`map` 只有双向迭代器，**不能用 `std::sort`（要求随机访问）**，要用成员函数 `list::sort` 或把数据拷到 `vector` 排完再拷回（往往更快，因缓存友好）。
- `unordered_*` 是前向迭代器，**不能 `--`**，也不支持范围序比较。

## 三、容器选择决策树（工程实践）

```
需要频繁随机访问（按下标）？
├─ 是 → vector（默认）/ deque（头尾都频繁）/ array（固定大小）
└─ 否 → 需要保持有序 / 范围查询？
        ├─ 是 → map / set（红黑树，O(log n) 有序）
        └─ 否 → 只去重 / 只点查？
                ├─ 是 → unordered_set / unordered_map（平均 O(1)）
                └─ 否 → 频繁在**中部**插入删除且持有迭代器？
                        ├─ 是 → list / forward_list
                        └─ 否 → vector（再次回到默认）
```

经验法则（可直接背）：
1. **默认 `vector`**，除非有强理由离开它。
2. 要**有序 / `lower_bound` / 前驱后继** → `map`/`set`。
3. 只**点查去重、不关心顺序** → `unordered_*`（先确认哈希质量）。
4. 只在**头部**频繁增删 → `deque`（分段连续，头尾 O(1)，且随机访问）。
5. 只在**中部**频繁增删 + 迭代器稳定 → `list`（但要接受缓存差）。

## 四、内存局部性与缓存友好的量化直觉

- `vector<int>`：每元素 4 字节，一个 64 字节缓存行装 16 个 `int`；顺序遍历近乎零 cache miss。
- `list<int>`：每节点至少 `4(value)+8(prev)+8(next)+padding` ≈ 32 字节，且地址随机；遍历每步可能一次 cache miss，且无法向量化。
- `map`/`unordered_map`：节点更重（红黑树 3 指针 + 颜色，或哈希节点 + 桶指针），**缓存更不友好**；仅当 O(log n)/O(1) 查找能换来「更少的总访问次数」时才划算。例如「100 万元素里查 1000 次」用 `unordered_map` 远快于 `vector` 线性扫；但「100 元素遍历 1 次」`vector` 完胜。

> 结论：**先算「访问模式 × 复杂度」，再考虑缓存**。`unordered_map` 的哈希计算 + 指针跳转本身有固定成本，小数据量时可能不如 `vector` 直接线性扫。

## 五、与 Java 容器对照速查

| C++ | Java | 备注 |
|---|---|---|
| `vector` | `ArrayList` | 连续、扩容、随机访问 |
| `deque` | `ArrayDeque` | 双端队列 |
| `list` | `LinkedList` | 双向链表（Java 版也缓存差，官方不推荐） |
| `map` | `TreeMap` | 红黑树、有序 |
| `unordered_map` | `HashMap` | 哈希、平均 O(1) |
| `unordered_set` | `HashSet` | 哈希、去重 |
| `set` | `TreeSet` | 红黑树、有序去重 |
| `array` | 无直接等价（基本类型数组 / `Arrays.asList`） | 固定大小栈/静态区 |

> 关键差异：Java 容器**只能装对象**（基本类型要装箱），有额外对象头与 GC 压力；C++ 模板可直接存 POD，`vector<int>` 内存布局与 C 数组一致，零开销抽象（zero-overhead abstraction）名副其实。

## 六、可运行示例：vector 遍历 vs list 遍历计时对比

```cpp
#include <iostream>
#include <vector>
#include <list>
#include <chrono>

int main() {
    const int N = 5'000'000;
    std::vector<int> v(N, 1);
    std::list<int>   l(N, 1);

    auto t0 = std::chrono::steady_clock::now();
    long s = 0; for (int x : v) s += x;
    auto t1 = std::chrono::steady_clock::now();

    long s2 = 0; for (int x : l) s2 += x;
    auto t2 = std::chrono::steady_clock::now();

    auto dv = std::chrono::duration<double, std::milli>(t1 - t0).count();
    auto dl = std::chrono::duration<double, std::milli>(t2 - t1).count();
    std::cout << "vector sum=" << s  << "  time=" << dv << " ms\n";
    std::cout << "list   sum=" << s2 << "  time=" << dl << " ms\n";
    std::cout << "list/vector ratio ~ " << (dl / dv) << "x\n";
}
```

**输出**（机器相关，示意；list 通常慢数倍）：
```
vector sum=5000000  time=4.2 ms
list   sum=5000000  time=28.7 ms
list/vector ratio ~ 6.8x
```

> 观察点：同样的 500 万元素求和，`list` 因缓存不友好比 `vector` 慢 **数倍**——即便二者都是 O(n) 遍历。这正是「缓存友好 > 表面复杂度」的铁证。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **默认决策树**：要随机访问 → `vector`；要按序/范围 → `map`/`set`；要 O(1) 查找且键可哈希 → `unordered_*`；两端增删 → `deque`；频繁中间插删且已持迭代器 → `list`。
- **先量后优**：先用 `vector` 写出来，profile 出热点后再换容器——「以为 list 快」是极常见误判。
- 迭代器类别决定可用算法：`list` 只有双向迭代器，不能用 `std::sort`（需要随机访问），要用成员 `sort`。

### 🎓 博士生视角
- 容器选择本质是**「访问模式 vs 存储层次」的匹配问题**：连续内存（vector）赢在预取与 cache line 利用率，链式结构（list/map）赢在「已定位点的 O(1) 改动」与「引用稳定性」。
- 迭代器分类（输入/输出/前向/双向/随机访问/连续）是一套**概念契约**：算法按其要求的最低类别编写，编译器据此选择最优实现（如 `advance` 对随机访问迭代器直接 `+= n`）。
- C++20 的 `contiguous_iterator` 概念把「连续内存」这一**物理属性**写进了类型系统，使 `std::copy` 可以对连续区间退化为 `memmove`。

### 📚 考研者视角
- 408 容器选择等价于**数据结构选型**：反复考「什么场景用什么结构」，答案要落到「查找/插入/删除/遍历」四种操作的复杂度与空间开销上。
- 记忆锚点：**「链表插入 O(1)」的前提是有前驱指针**；**哈希表不必有序，有序表不必哈希**。
- 若考 STL 层次：容器适配器（stack/queue/priority_queue）**不是独立容器**，而是对底层容器的**接口裁剪**。

---
