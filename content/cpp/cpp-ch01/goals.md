# cpp-ch01 · C++ 基础语法 · 学习目标

- 掌握基本类型、变量与常量、运算符与表达式
- 理解引用与指针的区别，能正确选择传值/传引用
- 会使用 `std::string`、`std::vector` 完成基本数据处理
- 能独立搭建编译环境并编译运行单文件程序
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34,827 | 全章 | 本章讲「值传参 vs 引用传参」时，先看 `math/greatest_common_divisor.cpp` 与 `math/lcm.cpp`：参数写成 `int` 还是 `const T&` 不是风格问题——内建类型按值、可能很大的对象按 const 引用，这份仓库把两种写法放在同一个目录里，一眼能对照出选择依据 |
| 2 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,899 | 全章 | 讲「引用绑定与类型退化」看 `include/fmt/base.h` 的 `type_mapper`（v11 起；v10 及以前在 `core.h`）：它把 `T`、`const T&`、`T&` 分别映射成同一套呈现方式，这是标准库 `std::decay` 之外最实用的「引用到底绑到了什么」的工业样本 |
| 3 | [nlohmann/json](https://github.com/nlohmann/json) | 50,829 | 全章 | 讲「类型别名与 const 正确性」看 `include/nlohmann/json.hpp` 顶部的 `using string_t = StringType;`、`using number_integer_t = ...`：全部用 `using` 而不是 `typedef`，且返回 `const string_t&` 不返回副本，正是本章「引用避免拷贝」那一条的落地 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（引用交换两个数）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex02`（整数除法截断（错误示范 vs 正确写法））核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex03`（遍历 vector 并打印）核对 |
| 4 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex04`（auto 类型推导）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
