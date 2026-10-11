# cpp-ch09 · STL 算法与迭代器：sort/find/lambda/范围

## 学习目标
完成本章后，你能：
1. 说出 5 类迭代器（输入/输出/前向/双向/随机访问，C++20 再加连续迭代器）的能力层级，并解释**算法复杂度如何被迭代器范畴约束**。
2. 熟练使用 `sort` / `stable_sort` / `find` / `count` / `transform` / `accumulate` / `partition` 等常用算法，并理解它们的**前置条件与最坏/平均复杂度**。
3. 用 **lambda** 给算法传策略，理解**捕获方式（值/引用/初始化捕获）、无捕获 lambda 可隐式转函数指针**及其对性能的影响。
4. 理解 `sort` 的 **introsort（快排+堆排+插入）混合实现**与「比较器必须满足严格弱序」的硬约束，以及稳定排序的代价。
5. 用 **C++20 ranges** 写出惰性、可组合的管道（`views::filter | transform | take`），并与 Python 生成器 / Java Stream 对比。
6. 识别并规避 **迭代器失效** 等高频陷阱（为后续工程化章节铺垫）。

## 前置
- cpp-ch08 STL 容器：vector/list/map/set/unordered

## 真题依据（真实可查）
- LeetCode 75 颜色分类（`sort-colors`）——`sort` / `partition` 双指针。
- LeetCode 56 合并区间（`merge-intervals`）——排序后线性扫描。
- 牛客 BM89 合并区间（`BM89`）——与 LeetCode 56 同思路。

## 验收标准
- 能解释「为什么 `list::sort` 不能接受随机访问迭代器算法」「为什么 `sort` 的比较器写错会 UB」。
- 能只用 STL 算法（不手写循环）完成一个数据统计小工具（见 project.json）。


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
