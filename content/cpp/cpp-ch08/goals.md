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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 286133 | 项目驱动的多语言实战教程合集（含 C/C++ 专题） |
| [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34742 | C++ 实现的经典算法与数据结构合集，可直接编译运行 |
| [ssloy/tinyrenderer](https://github.com/ssloy/tinyrenderer) | 24335 | 从零手写软件渲染器，C++ 底层与内存布局的极佳教材 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 侯捷 · C++ 面向对象高级开发 | [视频](https://www.bilibili.com/video/BV14s411E772/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++11/14 新标准 | [视频](https://www.bilibili.com/video/BV1p4411v7Dh/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++ 内存管理机制 | [视频](https://www.bilibili.com/video/BV1Kb411B7N8/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++ STL 标准库与泛型编程 | [视频](https://www.bilibili.com/video/BV1db411q7B8/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 黑马程序员 · C++ 入门到精通 | [视频](https://www.bilibili.com/video/BV1Tb411j7uM/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 郑莉 · C++ 语言程序设计（清华大学） | [视频](https://www.bilibili.com/video/BV1PA411b75a/) | 本学科配套视频，建议结合本章示例与习题观看 |
