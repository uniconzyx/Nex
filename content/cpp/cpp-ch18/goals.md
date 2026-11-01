# cpp-ch18 · 性能与底层：内存对齐、缓存友好与内联

## 学习目标
完成本章后，你能：
1. 用 `sizeof` / `alignof` / `offsetof` **实测**任意结构体的内存布局与填充分布，而不是凭直觉猜测。
2. 掌握**内存对齐规则**与 **padding 成因**，并会通过**字段重排**把结构体压缩回最小尺寸。
3. 会用 `alignas` 抬高对齐、用 `#pragma pack` 压缩协议布局，理解二者对访问性能与 ABI 的影响。
4. 理解 **false sharing（伪共享）**的成因，能用 `alignas` / 填充把热点变量分到不同缓存行，并用**确定性判据**（地址是否同行、缓存行迁移计数）验证消除效果。
5. 理解**缓存层次与局部性**（时间/空间局部性、64B 缓存行、硬件预取器），会分析一段循环的访存模式。
6. 能设计**缓存友好数据结构**：AoS vs SoA 的取舍、行优先 vs 列优先遍历、数组 vs 链表的指针追逐成本、`std::vector` 连续性为何重要。
7. 理解**内联**只是建议、`[[likely]]`/`[[unlikely]]` 只是提示、`final` 如何帮助**去虚化（devirtualization）**，以及优化与 ABI 边界的关系。
8. 掌握**简单 profiling 方法论**：`-O2` vs `-O0`、`perf`、火焰图的读法，并知道**性能断言不能用墙钟时间**。
9. 掌握与 C 的 **ABI 兼容**：`extern "C"`、名称修饰（name mangling）、结构体布局一致性、`std::string` 跨 ABI 的坑。
10. 掌握 `[[no_unique_address]]` 与**空基类优化（EBO）** 的适用条件与失效场景。

## 前置
- cpp-ch04 面向对象与对象模型（虚函数、vtable、对象布局基础）
- cpp-ch17 元编程与类型萃取（`type_traits` / `constexpr` / `static_assert`）

## 真题依据（真实可查）
- 各厂 C++/基础架构/游戏/量化岗笔试面试高频：结构体对齐、`sizeof` 计算、伪共享、缓存友好、`extern "C"`。
- LeetCode 867 `transpose-matrix`（矩阵转置，行/列遍历的局部性差异）见 exercises 链接（仅存元数据）。
- 牛客网 C++ 专项「内存对齐 / 结构体」常见题见 exercises 链接（仅存元数据）。

## 验收标准
- 能对给定结构体算出并实测 sizeof / 各成员偏移，并给出重排后的最小尺寸。
- 能解释伪共享为何「结果正确但性能崩塌」，并写出两种消除方案。
- 能对一个双重循环判断其缓存行未命中量级，并改成缓存友好版本。
- 能说清 `inline` / `final` / `[[likely]]` 各自的作用边界。
- 能说明为什么跨 DLL 边界不能直接传 `std::string`。

## 面试权重
- 高：本章是「会写 C++」与「懂机器」的分水岭。内存对齐与缓存行为是性能优化的第一性知识，
  也是区分「背八股」与「真做过性能优化」的关键；`extern "C"` / ABI 则是跨语言、跨模块工程的必备常识。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [simdjson/simdjson](https://github.com/simdjson/simdjson) | 24,491 | §1.1 对齐规则与填充 | §1.1 对齐与 §1.2 显式对齐：`src/generic/stage1/json_structural_indexer.h` 每次吃 64 字节块，用 `SIMDJSON_ALIGNED` 保证输入指针对齐到 64 字节边界（否则 AVX2 加载会慢甚至崩）；这是「对齐不是学究问题，是 SIMD 的硬要求」的第一手证据 |
| 2 | [google/benchmark](https://github.com/google/benchmark) | 10,486 | §3.2 链表 vs 数组，指针追逐… | 配 §3.2 的测量方法：`include/benchmark/benchmark.h` 的 `DoNotOptimize` 阻止编译器把结果删掉、`ClobberMemory` 强制刷新内存可见性；本章讲「链表 vs 数组」时，没有这两个工具测出来的数字基本不可信 |
| 3 | [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse) | 50,637 | §3.1 AoS vs SoA，行优… | §3.1 AoS vs SoA 的极致：`src/Columns/ColumnVector.cpp` 每个数值列就是一条连续 `PODArray`，`src/Common/PODArray.h` 负责带 padding 的增长；读 `ColumnVector::getData()` 直接返回裸指针——因为列存的前提就是「同类型紧挨着」，这正是本章要论证的局部性收益 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §3.2 链表 vs 数组，指针追逐… | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（sizeof / alignof / o）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §3.2 链表 vs 数组，指针追逐… | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（字段重排把 sizeof 从 24 降到）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（alignas 强制对齐与 aligno）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（#pragma pack(1) 与协议/）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
