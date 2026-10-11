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
