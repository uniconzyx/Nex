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
