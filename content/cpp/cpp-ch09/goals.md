# cpp-ch09 · STL 算法与迭代器：sort/find/lambda/范围

## 学习目标
完成本章后，你能：
1. 说出 5 类迭代器（输入/输出/前向/双向/随机访问，C++20 再加连续迭代器）的能力层级，并解释**算法复杂度如何被迭代器范畴约束**。
2. 熟练使用 `sort` / `stable_sort` / `find` / `count` / `transform` / `accumulate` / `partition` 等常用算法，并理解它们的**前置条件与最坏/平均复杂度**。
3. 用 **lambda** 给算法传策略，理解**捕获方式（值/引用/初始化捕获）、无捕获 lambda 可隐式转函数指针**及其对性能的影响。
4. 理解 `sort` 的 **introsort（快排+堆排+插入）混合实现**与「比较器必须满足严格弱序」的硬约束，以及稳定排序的代价。
5. 用 **C++20 ranges** 写出惰性、可组合的管道（`views::filter | transform | take`），并与 Python 生成器 / Java Stream 对比。
6. 识别并规避 **迭代器失效** 等高频陷阱（为后续工程化章节铺垫）。

## 前置
- cpp-ch08 STL 容器：vector/list/map/set/unordered

## 真题依据（真实可查）
- LeetCode 75 颜色分类（`sort-colors`）——`sort` / `partition` 双指针。
- LeetCode 56 合并区间（`merge-intervals`）——排序后线性扫描。
- 牛客 BM89 合并区间（`BM89`）——与 LeetCode 56 同思路。

## 验收标准
- 能解释「为什么 `list::sort` 不能接受随机访问迭代器算法」「为什么 `sort` 的比较器写错会 UB」。
- 能只用 STL 算法（不手写循环）完成一个数据统计小工具（见 project.json）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/STL](https://github.com/microsoft/STL) | 11,177 | §2.2 sort 的 intros… | §2.2 sort 的真实实现：`stl/inc/algorithm` 的 `sort` 调 `_Sort_unchecked`，内部是「快排分区 → 递归深度超限就转堆排 → 小区间用插排」三段式（introsort）；找到那个深度阈值常量，就明白本章说的「最坏 O(n log n) 靠什么兜底」 |
| 2 | [simdjson/simdjson](https://github.com/simdjson/simdjson) | 24,491 | §1.1 迭代器是「算法与容器之间的… | §1.1「迭代器是算法与容器的契约」：`include/simdjson/dom/array.h` 的 `iterator` 只提供 `operator*`/`operator++`/`operator!=`，够 `std::distance` 与范围 for 用，却不暴露底层实现；再看 `ondemand` 版的迭代器语义差异，能体会「迭代器范畴决定算法能用多强」 |
| 3 | [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34,827 | §1.2 范畴如何被编译器强制 | §1.2 范畴差异的实际后果：`numeric/` 与 `sort/` 里 `std::accumulate`、`std::sort`、`std::reverse` 各自要求输入迭代器/随机访问迭代器；把同一段代码的容器从 `list` 换成 `vector` 再编译，报错信息就是范畴不够用的证据 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（sort）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（stable_sort）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（find / find_if）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（count / count_if）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
