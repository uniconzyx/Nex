# cpp-ch14 · 预处理与宏：include/define/条件编译/头文件守卫

## 学习目标
完成本章后，你能：
1. 理解 C/C++ 翻译流程中**预处理阶段**的位置与职责（翻译阶段 1-4），以及 `#include` 的「文本包含」语义。
2. 掌握头文件守卫（`#ifndef`/`#define`/`#endif`）与 `#pragma once` 的写法、差异与局限。
3. 区分**对象宏**与**函数宏**，理解宏的「卫生问题」：参数不加括号、多重求值副作用，并用 `do{}while(0)` 包裹多语句宏。
4. 使用 `#`（字符串化）与 `##`（记号拼接）运算符，理解 X-Macro 在「枚举 + 字符串表」同步中的价值。
5. 用条件编译（`#if`/`#ifdef`/`#ifndef`/`defined`）做平台/调试开关；用 `static_assert`/`constexpr` 替代可编译期计算的宏；用 `__FILE__`/`__LINE__` 实现日志宏。

## 前置
- cpp-ch01 基础语法（宏是独立于类型系统之上的文本替换层，前置要求低）

## 真题依据（真实可查）
- nlohmann/json 等单头文件库大量使用头文件守卫与条件编译，是工程范本。
- 面试高频：宏与 inline 函数取舍、`#pragma once` 的坑、宏参数括号与多重求值。

## 验收标准
- 能解释为什么多语句宏必须用 `do{}while(0)` 包裹，并写出一个安全的日志宏。
- 能指出 `SQUARE(x++)` 的缺陷并改用 `inline` 函数或模板。
- 能为自己的头文件正确添加守卫，并说清 `#pragma once` 相比传统守卫的优劣。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DaveGamble/cJSON](https://github.com/DaveGamble/cJSON) | 13,063 | §1.2 #include 的「文本… | §1.2 与 §1.3 头文件守卫的现实版：`cJSON.h` 顶部 `#ifndef cJSON__h` / `#define cJSON__h`，`CJSON_PUBLIC` 宏负责导出符号、`CJSON_EXPORT_SYMBOLS` 控制静态/动态；整个头文件只有声明——把「头文件该放什么」这件事做到了教科书级 |
| 2 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,899 | §2.4 宏与 inline 的取舍 | §2.4 宏与 inline 的取舍：`include/fmt/base.h` 的 `FMT_BEGIN_NAMESPACE`/`FMT_END_NAMESPACE`、`FMT_API`、`FMT_INLINE` 三层宏分别管「命名空间版本化、符号可见性、强制内联」；看清每个宏存在的理由，就明白为什么现代库仍需要宏——跨编译器差异无法用 C++ 语法表达 |
| 3 | [include-what-you-use/include-what-you-use](https://github.com/include-what-you-use/include-what-you-use) | 4,781 | §1.2 #include 的「文本… | §1.2 的量化工具：`iwyu.cc` 是主分析器，`iwyu_include_picker.cc` 维护「哪个头文件该由谁包含」的映射表；拿它跑一遍本章的示例工程，`#include` 的传递闭包会被直接列出——这是「文本包含」语义最硬的证据 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（对象宏 vs 函数宏的括号陷阱）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex02`（# 与 ## 运算符）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（条件编译开关（#if / #elif /）核对 |
| 4 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex04`（头文件守卫效果演示（#ifndef 防重）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
