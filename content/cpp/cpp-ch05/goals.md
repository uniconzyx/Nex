# cpp-ch05 · 类与对象：封装、构造/析构、拷贝与运算符重载

## 学习目标
完成本章后，你能：
1. 定义类与访问控制（`public` / `protected` / `private`），理解封装的意义。
2. 编写构造函数（含初始化列表）、析构函数，并理解其调用时机。
3. 实现拷贝构造函数与拷贝赋值运算符，掌握**三/五法则**（Rule of Three/Five）。
4. 编写 `const` 成员函数、静态成员、友元与运算符重载。
5. 用类封装资源，初步理解 RAII 思想（为 ch10 智能指针铺垫）。

## 前置
- cpp-ch02 函数与参数传递
- cpp-ch04 指针与内存管理

## 真题依据（真实可查）
- LeetCode 707 设计链表（`design-linked-list`）——用类封装节点与链表。
- 牛客 BM101 设计 LRU 缓存（`BM101`）——类封装哈希 + 双向链表。

## 验收标准
- 能独立写出一个满足 Rule of Three 的字符串包装类。
- 能解释 `const` 成员函数、`const` 对象、运算符重载的返回值类型选择。


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
