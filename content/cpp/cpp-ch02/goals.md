# cpp-ch02 · 函数：声明/定义、重载、默认参数与 lambda · 学习目标

- 理解函数的声明（原型）与定义分离，掌握分离式编译思想
- 掌握三种参数传递方式（值 / 引用 / 指针），能正确选择
- 理解函数重载决议规则，能合理使用重载而非堆砌同名函数
- 掌握默认参数的规则与陷阱，会用 `inline` 优化小函数
- 能用 lambda 表达式（含值/引用捕获）简化回调与算法谓词
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,897 | §2.1 函数重载 | §2.1 函数重载的工业规模样本：`include/fmt/base.h` 里 `format_to` 有十几个重载（`OutputIt` 版本、`locale` 版本、`memory_buffer` 版本），参数个数与类型各差一点；读它们之前先问「编译器凭什么在这么多同名函数里选中这一个」，再回 §2.1 看重载决议的排序规则 |
| 2 | [catchorg/Catch2](https://github.com/catchorg/Catch2) | 21,538 | §3.1 捕获方式 | §3.1 捕获方式：`src/catch2/catch_test_macros.hpp` 的 `TEST_CASE`/`SECTION` 宏最终展开成「注册一个 lambda」，`INTERNAL_CATCH_TEST` 里按值捕获比较表达式两侧；看清它为什么不按引用捕获（section 结束后临时对象已经没了） |
| 3 | [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34,813 | §2.2 默认参数 | §2.2 默认参数的替代方案：`sort/` 目录里同一算法常有两个版本——一个只用 `<`，一个多接一个比较器；对照本章说的「默认参数 vs 重载 vs 模板参数」，看真实代码更愿意选哪种、为什么 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（函数定义与调用）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex02`（引用传参交换）核对 |
| 3 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex03`（默认参数）核对 |
| 4 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex04`（函数重载）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
