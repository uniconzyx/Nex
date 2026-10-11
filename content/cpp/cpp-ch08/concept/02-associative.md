# 02 · 关联容器 map/set：红黑树与「有序」的本质

## 一、理论根基：为什么需要「自动有序 + O(log n) 查找」

`vector` 的查找是 O(n)（除非先排序再二分），且插入要保持有序就得 O(n) 搬移。当**数据需要长期保持有序、又频繁增删查**时，我们需要一种「任何时刻都能 O(log n) 插入/删除/查找，且中序遍历天然有序」的结构——这正是**关联容器（associative container）** `std::map`/`std::set`（及其 `multi*` 变体）的角色。

注意 `map`/`set` 是 **有序**关联容器（按 `key` 比较排序）；`unordered_*` 是无序哈希（见 03）。二者都满足 `key` 唯一（`multi` 允许重复 `key`）。

## 二、实现机制：红黑树（Red-Black Tree）

C++ 标准规定 `map`/`set` 是「以 `key` 为序的平衡二叉搜索树」，业界实现（libstdc++ / libc++ / MSVC）统一采用 **红黑树**——一种**自平衡 BST**，通过节点着色（红/黑）+ 旋转维持「黑高平衡」，从而保证：

- 树高 **≤ 2·log₂(n+1)**（近似平衡，最差情况不过分退化成链）。
- 所有查找/插入/删除/`lower_bound` 均为 **O(log n)**。
- 中序遍历即**严格弱序（Strict Weak Ordering）升序**——这是「有序性」的来源。

> 红黑树 vs AVL：AVL 更平衡（查询略快），但插入删除旋转更多；红黑树在「增删频繁」场景下综合更优，是 STL 的默认选择。`std::map` 的每个节点持有一个 `value_type`（对 `map` 是 `std::pair<const Key, T>`，`const Key` 保证 key 不可改——改了就破坏树序）。

节点内部结构（`_Rb_tree_node`）含：左指针、右指针、父指针、颜色位、以及存储的 `value_type`。**指针开销使每个元素多出约 3 个指针 + 1 个颜色位**。

## 三、实现机制：关键接口的语义与复杂度

| 接口 | 语义 | 复杂度 | 工程要点 |
|---|---|---|---|
| `find(k)` | 返回指向 key==k 的迭代器，否则 `end()` | O(log n) | 不插入；找不到返回 `end()` |
| `count(k)` | key==k 的元素个数（0/1；`multi` 可 >1） | O(log n) + O(k) | 仅判断「在不在」用 `find`/`contains`(C++20) 更省 |
| `operator[](k)` | 若 key 不存在则**值初始化插入** `T()`，返回引用 | O(log n) | **会意外插入**；只想查别用 `[]` |
| `at(k)` | 找不到抛 `std::out_of_range` | O(log n) | 只读且不希望插入时用 `at` |
| `lower_bound(k)` | 首个 `>=k` 的迭代器 | O(log n) | 区间查询/前缀范围的核心 |
| `equal_range(k)` | `[lower_bound, upper_bound)` 对 | O(log n) | `multi` 取某 key 全部元素 |
| `insert` / `emplace` | 插入，返回 `{it, inserted}` | O(log n) | `emplace` 就地构造 pair |

> `operator[]` 的「自动插入」是经典陷阱：在一个 `const map` 上不能用 `[]`（非 const 语义）；想安全只读请用 `find`/`at`。C++20 起有 `contains(k)` 做纯判断。

## 四、工程实践：map 还是 unordered_map？

经验法则（详见于 04 章容器选择）：
- 需要**有序遍历 / 范围查询（lower_bound）/ 按 key 取前驱后继** → 用 `map`。
- 仅按 key 点查、不关心顺序、追求平均 O(1) → 用 `unordered_map`（见 03）。
- `set` 用于「**集合 / 去重 / 存在性判断**」且需要有序输出时；只想去重不关心顺序用 `unordered_set`。

## 五、边界与陷阱

- `map` 的 `key` 是 `const`，不能 `it->first = x;`——会破坏红黑树序。
- 比较器必须满足**严格弱序**；用 `std::greater<>` 可得到降序，但不能用「>=」式谓词（会破坏不变量导致 UB）。
- 遍历 `map` 时 `erase`：`it = m.erase(it);`（C++11 起 `erase` 返回下一迭代器），不要 `m.erase(it++)` 的过时写法（对 map 仍对，但通用写法更佳）。
- 自定义 key 类型必须提供「可比较」或自定义比较器；否则编译失败。

## 六、可运行示例：有序性 + operator[] 的副作用

```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> score;
    score["alice"] = 90;
    score["bob"]   = 75;
    score["carol"] = 88;

    std::cout << "遍历（自动按 key 升序）:\n";
    for (auto& kv : score)
        std::cout << kv.first << '=' << kv.second << ' ';
    std::cout << '\n';

    // operator[] 对不存在的 key 会插入（值初始化为 0）
    int& dave = score["dave"];        // 插入 dave=0
    std::cout << "size after [\"dave\"]: " << score.size() << '\n';

    // at() 不会插入，找不到抛异常
    try { score.at("xxx"); }
    catch (const std::out_of_range&) { std::cout << "at(\"xxx\") threw\n"; }

    // lower_bound：首个 >= "b" 的
    auto it = score.lower_bound("b");
    std::cout << "lower_bound(\"b\") -> " << it->first << '\n';
}
```

**输出**：
```
遍历（自动按 key 升序）:
alice=90 bob=75 carol=88
size after ["dave"]: 4
at("xxx") threw
lower_bound("b") -> bob
```

> 观察点：① 遍历输出严格按 `key` 字典序（红黑树中序）；② `operator[]` 悄悄插入了 `dave`；③ `at` 不插入、越界抛异常；④ `lower_bound` 直接定位到 `bob`。

## 七、与 Java 对照

| 维度 | C++ `std::map` | Java `TreeMap` |
|---|---|---|
| 底层 | 红黑树 | 红黑树（同算法） |
| 有序性 | key 升序（可定制比较器） | key 升序（可定制 `Comparator`） |
| 点查/插入 | O(log n) | O(log n) |
| 自动插入 | `[]` 会插入 | `get` 不插入；`put` 插入 |
| key 不可变 | `const Key` | key 由 `Comparator` 约束（不强制 const） |

---

## 三视角解析

### 🧑‍💻 程序员视角
- `map` 用 `[]` 会**默认构造并插入**（查改混用时容易引入脏数据），只读查询请用 `find` 或 C++20 的 `contains`。
- 需要「按 key 有序遍历」或「范围查询（lower_bound/upper_bound）」时，`map`/`set` 是唯一选择；纯查找性能则应换 `unordered_*`。
- `map` 的节点是**独立分配**的，遍历是**指针追逐**，缓存不友好——数据量不大时 `vector` 排序后二分常常更快。

### 🎓 博士生视角
- 红黑树提供**弱平衡**：最长路径 ≤ 2×最短路径，保证 O(log n) 的同时把旋转次数压到常数上界（插入 ≤2、删除 ≤3），这就是工程上它胜过严格平衡的 AVL 的原因——**AVL 查询略快但写代价高**。
- `map` 的迭代器**不因插入失效**（节点地址稳定），只有被删元素本身失效；这与 `vector` 形成鲜明对照。
- 从有序性看，中序遍历即有序序列，`lower_bound` 是对 BST 的**一次下降**，复杂度 O(log n) 且常数极小。

### 📚 考研者视角
- 408 高频：**BST → AVL → 红黑树**的演进动机；AVL 的四种旋转（LL/RR/LR/RL）、平衡因子定义。
- 必会计算：给定序列构造 BST/AVL，求**平均查找长度 ASL**（成功/不成功要分开算）。
- 记忆锚点：**红黑树的「最长路径 ≤ 2×最短路径」**与**「插入旋转 ≤2 次、删除 ≤3 次」**；B/B+ 树见 ch03 的对比（磁盘 IO 视角）。

---
