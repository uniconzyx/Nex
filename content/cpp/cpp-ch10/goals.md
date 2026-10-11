# cpp-ch10 · 智能指针与 RAII：unique_ptr / shared_ptr / weak_ptr

## 学习目标
完成本章后，你能：
1. 用**博士视角**说清 RAII 的第一性原理：为什么把"资源所有权绑定到对象生命周期"能换来确定性的资源回收，从而让 C++ 无需 GC 也能保证异常安全。
2. 区分 `std::unique_ptr`（独占所有权、零开销、可移动不可拷贝）与 `std::shared_ptr`（共享所有权、引用计数、控制块 + 原子操作），理解各自的**内存布局与运行时开销**。
3. 画出 `shared_ptr` 的**控制块（control block）**结构（强引用计数 / 弱引用计数 / 删除器 / 分配器），解释引用计数加/减为何需要**原子操作**及其代价。
4. 用 `std::weak_ptr` 安全地观察 `shared_ptr` 所管理的对象（`lock()` 提升），并据此**打破循环引用**导致的泄漏。
5. 掌握**自定义删除器**（`unique_ptr` 编译期绑定 vs `shared_ptr` 类型擦除）的取舍，以及 `make_shared` 一次分配的优势与陷阱。
6. 理解 `enable_shared_from_this` 的工作机制与"在构造函数中调用 `shared_from_this()`"的未定义行为陷阱。
7. 在真实工程里**正确选择**智能指针 vs 裸指针：接口边界、工厂函数返回 `unique_ptr`、与 C API / `get()` 混用的边界与红线。

## 前置
- cpp-ch04 指针与内存管理（new/delete、悬垂、泄漏）
- cpp-ch05 类与对象（构造/析构、RAII 雏形、拷贝控制）

## 真题依据（真实可查）
- 牛客 BM101 设计 LRU 缓存（`BM101`）——常用 `shared_ptr`/`unique_ptr` 实现节点所有权。
- 《C++ Primer（第5版）》第 12 章 动态内存 / 第 13 章 拷贝控制（智能指针是 Rule of Zero 的核心支撑）。
- boostorg/smart_ptr（`boostorg/smart_ptr`）——智能指针的标准前身，理解其演进有助掌握设计动机。

## 验收标准
- 能独立写出一个不泄漏的、用 `unique_ptr` 管理资源的小组件，并解释为何它"零开销"。
- 能解释"为什么 `shared_ptr` 的引用计数在控制块里""为何循环引用会泄漏""`weak_ptr` 如何打破"。
- 能指出 `get()` 返回裸指针后混用、构造期调用 `shared_from_this()` 这两类典型误用。


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
