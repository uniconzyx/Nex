# cpp-ch17 · 元编程与类型萃取：type_traits / constexpr / SFINAE / concept

## 学习目标
完成本章后，你能：
1. 理解**模板元编程**与「编译期计算」的动机：把错误尽可能前移到编译期、消除运行时分支、生成针对类型的特化实现。
2. 掌握 `<type_traits>`：`is_same` / `remove_reference` / `decay` / `is_destructible` 等萃取，并用于重载/特化选择。
3. 掌握 `std::enable_if` 与 **SFINAE**：用「替换失败不是错误」在编译期施加约束、实现重载决议。
4. 掌握 `constexpr` 函数 + `static_assert`：在编译期完成计算，并用 `static_assert` 证明计算发生在编译期。
5. 掌握 **`if constexpr`**：在模板内按类型裁剪分支，避免对不适用的类型实例化非法代码。
6. 掌握**模板特化（全特化）**与**偏特化**：为特定类型或类型模式定制行为。
7. 掌握**变参模板**与**折叠表达式**：泛型地聚合任意数量参数。
8. 掌握**完美转发** `std::forward`：在泛型代码中保持参数的原始值类别（左值/右值）。
9. （C++20）掌握 **`concept`** 与 **`requires`**：用清晰、可读的语法表达类型约束，取代冗长的 SFINAE。

## 前置
- cpp-ch07 模板基础（函数模板 / 类模板 / 模板参数）
- cpp-ch12 移动语义、引用折叠与 `std::forward` 基础

## 真题依据（真实可查）
- 各厂 C++ 岗笔试/面试高频：`type_traits`、`SFINAE`、`constexpr` 是泛型库与标准库实现的核心技法；
- LeetCode 50 `powx-n`（快速幂）可用 `constexpr` 在编译期预计算（见 exercises 链接，仅存元数据）。
- 牛客网 C++ 专项中「模板/泛型」相关题目（见 exercises 链接，仅存元数据）。

## 验收标准
- 能写出一个由 `type_traits` 驱动的「根据类型选择实现」的工具函数。
- 能解释 `SFINAE` 与 `concept` 的关系与历史演进。
- 能写出一个编译期计算（如斐波那契）并用 `static_assert` 证明其确在编译期求值。
- 能区分 `if constexpr` 与普通 `if` 在模板中的语义差异。

## 面试权重
- 高：元编程是区分「会用模板」与「懂模板」的分水岭；`type_traits` / `SFINAE` / `constexpr` 在泛型库、标准库与面试中极常见，且极易暴露候选人深度。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/STL](https://github.com/microsoft/STL) | 11,177 | §1.3 三、is_destructible 与「类型是否可销毁」 | 读 `microsoft/STL` 的 `stl/inc/type_traits`：`is_destructible` 靠 `declval<T>().~T()` 的 SFINAE 探测，`conjunction`/`disjunction` 用短路继承避免多余实例化；把这几处读完，`<type_traits>` 就不再是「查表用的魔法」——本章 §1.2「模板特化与偏特化」讲的机制，在这里就是两行 `true_type`/`false_type` 分支 |
| 2 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,899 | §3.2 二、C++20 concept：可读的约束 | 读 `include/fmt/base.h` 里 `is_formattable`：它同时有 C++20 concept 版（`requires` 表达式）与旧编译器的 SFINAE 版，两份实现并列；对照它们能看清 concept 把「替换失败」从错误信息里救出来这件事有多实际——SFINAE 版报错指向模板定义处，concept 版直接说「T 不满足 formattable」 |
| 3 | [abseil/abseil-cpp](https://github.com/abseil/abseil-cpp) | 18,177 | §3.1 一、SFINAE：替换失败不是错误 | 读 `abseil/abseil-cpp` 的 `absl/meta/type_traits.h`：`absl::void_t`、`type_identity`、`is_comparable` 都是为「检测某操作是否合法」准备的积木；读 `is_comparable` 的 `decltype` 表达式，是本章 SFINAE 一节最干净的例题——它同时检测 `a == b` 与 `a != b` 两侧，缺一个就整体失败，而本章 §3.3「requires 表达式与约束组合」用 `requires requires` 能写成两条并列约束 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（std）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §1.2 模板特化与偏特化 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（if constexpr 按类型在编译期）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（type_traits 萃取）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | §3.3 requires 表达式与… | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（type_traits 萃取）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
