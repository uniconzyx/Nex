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
