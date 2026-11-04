# cpp-ch08 · STL 容器：vector/list/map/set/unordered

## 学习目标
完成本章后，你能：
1. 讲清 `vector` 的**连续内存模型**与 **amortized 2× 扩容策略**，理解 `size`/`capacity`/`reserve`/`resize` 的语义差异。
2. 掌握 `list`/`forward_list` 的**节点式（非连续）结构**及其缓存不友好本质，能对比其与 `vector` 的遍历局部性。
3. 理解 `map`/`set` 的**红黑树（自平衡 BST）底层**与**有序性**，说清 `operator[]`/`at`/`find`/`lower_bound` 的复杂度与语义。
4. 理解 `unordered_map`/`unordered_set` 的**哈希桶 + 链地址法**实现、**负载因子（load factor）**与**再哈希（rehash）**，以及哈希质量对最坏复杂度的影响。
5. 背记并能在编码中正确应用各容器的**迭代器失效规则**（尤其 `vector` 扩容、`erase` 循环中迭代器的处理）。
6. 依据**内存局部性、增删查复杂度、缓存友好度**为具体场景选对容器，并能与 Java `ArrayList`/`HashMap` 做等价映射。

## 前置
- cpp-ch03 数组与字符串（`std::string`、连续存储直觉）
- cpp-ch05 类与对象（RAII、`std::vector` 作为 RAII 成员）

## 真题依据（真实可查）
- LeetCode 1 两数之和（`two-sum`）——哈希表 `unordered_map` 计数/索引。
- LeetCode 49 字母异位词分组（`group-anagrams`）——`unordered_map<key, vector>` 归类。
- LeetCode 347 前 K 个高频元素（`top-k-frequent-elements`）——`unordered_map` 频次统计 + 选择。
- 牛客 BM50 两数之和（`BM50`）——哈希表解法。

## 验收标准
- 能独立画出 `vector` 扩容前后三指针（`start`/`finish`/`end_of_storage`）的变化，并推导 `push_back` 的摊还 O(1)。
- 能在 `for` 循环里用 `it = v.erase(it)` 正确删除元素而不触发 UB。
- 能解释「为什么 `unordered_map` 最坏查询是 O(n)」以及负载因子如何控制平均复杂度。
- 对给定场景（频繁随机访问 / 频繁中间插入 / 需要有序遍历 / 只需要去重）能选对容器并说出理由。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/STL](https://github.com/microsoft/STL) | 11,177 | §1.2 二、实现机制：amortized 2× 扩容到底发生了什么 | 读 `microsoft/STL` 的 `stl/inc/vector`：`_Calculate_growth` 做 `max(size + size/2, requested)` 再对齐，`_Emplace_reallocate` 分配新块、搬移旧元素、释放旧块——三步全在这里；注意 MSVC 实际取的是 **1.5×**（`size + size/2`）而不是 2×，对照本章算的摊销 O(1)，能看出倍数只影响常数、不影响均摊结论，但会影响「旧块能否被后续分配复用」——这正是 §1.3「迭代器/引用/指针的失效规则」的由来 |
| 2 | [redis/redis](https://github.com/redis/redis) | 77,127 | §3.3 三、实现机制：负载因子与再哈希（rehash） | 读 `redis/redis` 的 `src/dict.c`：`dictExpand` 建两张表，`dictRehash` 每次只搬 `n` 个桶（渐进式 rehash），查找时两张表都要看；这是「不一次性搬完以免卡顿」的工程答案，与 `unordered_map` 的一次性 rehash 形成对照——标准容器为了满足 §3.2「桶数组 + 链地址法」的迭代器语义只能整体重建，而 Redis 单线程服务可以接受「两张表短暂并存」 |
| 3 | [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34,827 | §4.3 三、容器选择决策树（工程实践） | 读 `TheAlgorithms/C-Plus-Plus` 的 `graph/` 与 `sorting/` 目录：同一个结构常有邻接矩阵版与邻接表版两种实现，排序也区分「适合 vector」与「只能链表做」的算法；把本章 §4.1「list / forward_list：节点结构为何缓存不友好」与 §4.4「内存局部性与缓存友好的量化直觉」的判据拿过来，逐目录验证一遍你的判断——同一份代码换成链表版，性能差的那部分就是节点指针跳转的代价 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（vector 扩容观察）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §4.1 list / forwar… | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（vector reserve 预分配）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | §4.4 内存局部性与缓存友好的量化… | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（vector erase 循环正确写法）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（vector insert 返回新迭代器）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。