# 04 · Set 与有序映射：HashSet/TreeSet/TreeMap 的本质

## 一、理论根基：Set 是「约束后的 Map」

`Set` 承诺「元素不重复」。JDK 的实现极其务实：**`HashSet` 内部就是一个 `HashMap`，元素作键、value 是一个共享的空对象 `PRESENT`**；`add` 即 `map.put(e, PRESENT)`，靠 `HashMap` 的键唯一性保证去重。同理 `TreeSet` 内部是 `TreeMap`。

## 二、实现机制

### HashSet / LinkedHashSet
- `HashSet`：基于 `HashMap`，去重完全依赖键的 `equals`/`hashCode` 契约（见 concept 03）。顺序不保证。
- `LinkedHashSet`：在 `HashMap` 节点上额外维护一条**双向链表**记录插入顺序，代价是每个节点多两个指针，但能按插入序迭代（常用于「去重且保序」）。

### TreeSet / TreeMap（红黑树）
- `TreeMap` 用**红黑树**（自平衡二叉搜索树）按 key 排序存储，查找/插入/删除均为 O(log n)。key 必须可比较：要么实现 `Comparable`，要么构造时传入 `Comparator`。
- `TreeSet` 是 `TreeMap` 的键视图。它提供 `first()/last()/subSet()/headSet()/tailSet()` 等有序区间操作，这是哈希集合做不到的。
- **选择依据**：需要「去重」用 `HashSet`（O(1)）；需要「按 key 排序 / 区间查询」用 `TreeMap/TreeSet`（O(log n)）；需要「保插入序」用 `LinkedHashSet`。

### PriorityQueue（二叉堆）
- `PriorityQueue` 不是树，而是用**数组实现的二叉小（大）顶堆**。`offer`/`poll` 为 O(log n)，`peek` 为 O(1)。它**不保证遍历顺序**，只保证 `poll` 出的总是当前极值。默认最小堆，可用 `Comparator.reverseOrder()` 改最大堆。常用于 Top-K、任务调度。

## 三、工程实践：去重与排序的正确姿势

- 用 `HashSet` 去重前，确保元素类型正确实现了 `equals/hashCode`（见 `examples/ex05-hashset-dedup.json`：自定义 `Point` 去重）。
- 排序：少量数据用 `Collections.sort(list)`（TimSort，稳定）；需要「键有序的 Map」用 `TreeMap`；需要「按自然序或定制序的集合」用 `TreeSet`。
- `PriorityQueue` 做 Top-K：维护一个大小为 K 的堆，时间与空间都优于全排序。

## 四、边界与陷阱

1. **`TreeSet` 的 Comparator 必须和 equals 一致**：若 `compareTo` 认为相等但 `equals` 认为不等，Set 会「当作重复」丢弃，破坏 Set 语义（`Set` 的契约是「不含 equals 相等的元素」）。
2. **`HashSet` 的迭代顺序在不同 Java 版本/运行中可能不同**（依赖 hash 种子随机化），不要依赖它排序。
3. **`PriorityQueue` 的 `iterator()` 不保证有序**，只有 `poll` 保证出极值。

## 五、可运行代码

- `examples/ex04-treemap-sort.json`：自然序与逆序 `TreeMap` 的键顺序。
- `examples/ex05-hashset-dedup.json`：自定义键 `Point` 的 `equals/hashCode` 去重实证。
- `examples/ex06-priorityqueue-heap.json`：最小堆出队顺序 1 3 5 7 9。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 去重用 `HashSet`；要**保持插入顺序**用 `LinkedHashSet`；要**排序与范围查询**用 `TreeSet` / `TreeMap`。
- `TreeSet` 的元素必须实现 `Comparable` 或构造时传 `Comparator`，否则运行期抛 `ClassCastException`。
- 需要「按 key 找最近的前驱/后继」时，`TreeMap` 的 `floorKey` / `ceilingKey` 比手写二分方便得多。

### 🎓 博士生视角
- `HashSet` 就是「**只有 key 的 HashMap**」（内部直接持有一个 `HashMap`），因此去重语义完全继承哈希表的等价类划分。
- `LinkedHashSet` 在哈希表之外额外维护一条**双向链表**以保留插入顺序——用「多一份指针」换「可预测的迭代顺序」，代价是内存与插入开销略增。
- `TreeSet` / `TreeMap` 底层是**红黑树**：操作 O(log n)，并天然支持有序遍历与范围查询（`subSet` / `headSet` / `tailSet`）。这解释了「为什么有序容器必须用树而不是哈希表」——哈希表破坏顺序以获得 O(1) 查找，树保留顺序以获得 O(log n) 的范围能力。

### 📚 考研者视角
- **408 直接对应**：**红黑树 / BST** 的性质、插入删除与旋转、时间复杂度；「有序查找」与「哈希查找」的适用场景对比。
- 常考：为什么 `TreeMap` 是 O(log n) 而 `HashMap` 是 O(1)（平均），以及各自适合什么查询模式。
- 记忆锚点：**`HashSet` = `HashMap` 的 key 集**；**`TreeSet`/`TreeMap` 是红黑树**。
