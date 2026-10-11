# cpp-ch13 · 输入/输出与文件：iostream、fstream 与格式化

## 学习目标
完成本章后，你能：
1. 理解 iostream 体系的分层结构（`istream`/`ostream`/`iostream` 与 `streambuf` 的分工），并用状态位 `good/eof/fail/bad` 判断与恢复流的错误。
2. 解释 `cin` 与 C 标准库 `scanf` 的同步开销，掌握 `std::ios::sync_with_stdio(false)` 与 `cin.tie(nullptr)` 的加速原理与代价。
3. 用操纵符（`setw`/`setprecision`/`fixed`/`setfill`/`left`/`right`）做可控的格式化输出，理解浮点默认精度丢失的成因。
4. 用 `fstream` 以文本/二进制模式读写文件，掌握打开模式（`in/out/app/trunc/binary`）、文件位置（`seekg`/`seekp`/`tellg`）与 `is_open()` 检查。
5. 用 `stringstream` 做字符串解析与格式化，并理解它与 `std::format`（C++20）各自的取舍。

## 前置
- cpp-ch03 数组与字符串（`std::string`/`string_view` 基础）

## 真题依据（真实可查）
- 牛客/LeetCode 大量题目依赖快速 IO（如 `sync_with_stdio(false)` 提速），属工程基本功。
- 文件 IO 与格式化是「读入数据 + 输出报表」类项目的核心（如 nlohmann/json 流式解析）。

## 验收标准
- 能写出一个健壮的输入循环：读失败后用 `clear()` 恢复、用 `getline` 与 `>>` 混用时不残留换行。
- 能正确用 `setprecision`/`fixed` 控制浮点位数，区分文本与二进制模式。
- 能解释 iostream 的性能来源（虚函数 + 本地化 facet）以及何时该改用 `std::format` 或 `printf`。


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
