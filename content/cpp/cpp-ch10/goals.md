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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [google/leveldb](https://github.com/google/leveldb) | 39,514 | §1.2 析构调用到底是怎么被"插入… | §1.2「析构调用是编译器插入的」：`db/db_impl.cc` 的 `DBImpl::~DBImpl()` 里显式停后台线程、删 memtable、释放文件锁——所有清理都钉在析构里，因此 `DB::Open` 失败时只要 `delete impl` 就干净；注意 leveldb 用的是裸指针 + `delete`，正好用来对照「手写 RAII 与 unique_ptr 的等价关系」 |
| 2 | [abseil/abseil-cpp](https://github.com/abseil/abseil-cpp) | 18,177 | §1.2 析构调用到底是怎么被"插入… | §1.2 的通用化：`absl/cleanup/cleanup.h` 的 `absl::Cleanup` 把「析构时执行一段代码」抽成可组合对象，`absl/synchronization/mutex.h` 的 `MutexLock` 用它管锁；这两处合看，就明白 RAII 不是「智能指针专用技巧」，而是资源管理的通用形态 |
| 3 | [protocolbuffers/protobuf](https://github.com/protocolbuffers/protobuf) | 72,137 | §2.2 unique_ptr 为何… | §2.2 与 §3.3 的所有权边界：`src/google/protobuf/arena.h` 里 `Arena` 用 `unique_ptr` 管自己的块，但 `CreateMessage` 在 arena 上创建的对象由 arena 统一回收（不逐个 delete）；这是「所有权不在指针、而在容器」的典型，也解释了自定义删除器为什么要做类型擦除 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（unique_ptr 独占所有权（移动而）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex02`（unique_ptr 自定义删除器（编译）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（shared_ptr 引用计数（use_）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（unique_ptr<T[]> 管理数组）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
