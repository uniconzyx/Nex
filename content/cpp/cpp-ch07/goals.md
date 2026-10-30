# cpp-ch07 · 模板与泛型：函数模板、类模板与特化

## 学习目标
完成本章后，你能：
1. 定义**函数模板**与**类模板**，理解模板参数（类型参数 / 非类型参数）与模板实参推导。
2. 讲清**模板实例化**的三种形态：隐式实例化、显式实例化、特化（全/偏），以及它们生成的代码。
3. 理解**两阶段编译（two-phase lookup）**与依赖名（dependent name）为何需要 `typename` / `template` 关键字。
4. 编写**模板特化**：全特化与偏特化，并掌握特化之间的优先级与匹配规则。
5. 使用**可变参数模板**与**折叠表达式（C++17）**进行参数包展开。
6. 用 **SFINAE / `std::enable_if`** 做编译期重载筛选，并理解 C++20 `concept` 如何优雅取代它。
7. 能从**底层视角**对比 C++ 模板（生成真实代码）与 Java 泛型（类型擦除），评估**代码膨胀与编译期成本**。

## 前置
- cpp-ch05 类与对象（封装、运算符重载、成员函数）
- cpp-ch02 函数重载决议（模板重载与之同源）

## 真题依据（真实可查）
- 牛客 BM90 最小覆盖子串（`BM90`）——可借泛型滑动窗口模板复用（仅存元数据+链接，不存题面）。
- LeetCode / 牛客「设计」类题（如 707 设计链表、146 LRU 缓存）常以类模板泛化存储类型。

## 验收标准
- 能独立写出一个泛型 `Stack<T>` 并为其做 `bool` 全特化。
- 能解释「为什么模板实现通常放在头文件里（包含模型）」。
- 能用 `std::enable_if` 区分整型/浮点型重载，并说出 SFINAE 的全称与含义。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,897 | §2.3 全特化 | §2.3 全特化的实战：`include/fmt/base.h` 的 `template <typename T, typename Char> struct formatter` 主模板故意不实现 `format()`，谁要支持格式化就特化谁（`formatter<std::string>`、`formatter<int>`）；读主模板那条注释，它写清了「为什么主模板要留空」 |
| 2 | [nlohmann/json](https://github.com/nlohmann/json) | 50,813 | §3.3 SFINAE —— 替换失… | §3.3 SFINAE 的工程写法：`include/nlohmann/json.hpp` 里 `is_compatible_type`、`has_to_json`、`has_from_json` 全靠「替换失败不算错」来探测用户类型有没有提供 `to_json`/`from_json`；顺着 `has_to_json` 的 `decltype` 表达式看，能看清 SFINAE 到底在哪一步生效 |
| 3 | [microsoft/STL](https://github.com/microsoft/STL) | 11,172 | §3.3 SFINAE —— 替换失… | §3.3 与 §3.5 的底层：`stl/inc/type_traits` 里 `void_t`、`enable_if`、`conjunction` 的真实实现；看完再读 `stl/inc/concepts`（若你所看的版本已含 C++20 约束），就能对照出「SFINAE 时代」与「concept 时代」表达同一约束的成本差 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（函数模板基本用法（max））核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §4.5 与 Java 泛型 / 类… | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（显式指定模板实参与显式实例化）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（函数模板与普通函数重载决议）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（类模板）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
