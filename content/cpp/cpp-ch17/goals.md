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
