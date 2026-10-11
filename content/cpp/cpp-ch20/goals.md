# cpp-ch20 · 综合项目与面试冲刺：系统设计、代码规范与复盘

> C++ 学习线收官章。前三阶段（基础语法 -> 面向对象与 STL -> 模板/并发/现代 C++）已搭好骨架，
> 本章把零散能力**收口成可交付的工程**：自己造一遍 STL 组件、写一个能用的线程池与 HTTP 服务器、
> 把代码规范与异常安全落到可执行的标准上，最后用高频八股与系统设计答法串讲面试。

## 一、学习目标

1. **造一遍 STL，把 RAII / 拷贝-移动语义 / 异常安全 / 迭代器失效学透**
   - 迷你 `vector`：容量倍增策略、`reserve` 语义、迭代器失效（对应 ex01 / ex02 / ex12）。
   - 迷你 `shared_ptr`：控制块与引用计数、`weak_ptr` 打破循环引用（对应 ex03 / ex04）。
   - RAII 守卫：把释放钉死在析构函数里，正常/异常/提交三条路径都不漏（对应 ex05）。
2. **实现一个真实并发组件：线程池 + 简易 HTTP 服务器**
   - 任务队列 + 条件变量 + 优雅关闭（对应 ex06）。
   - 请求行解析：纯字符串确定性解析（对应 ex07）。
3. **把异常安全等级与代码规范变成可判断的标准**
   - 基本保证 / 强保证 / 不抛（对应 ex08）。
   - 移动语义与 RVO、对象模型与虚表（对应 ex09 / ex10 / ex11）。
4. **面试冲刺**：用白板题（LRU Cache，对应 ex13）与高频八股，把知识收敛成能讲、能写、能比的状态。

## 二、与已验证示例的对应关系

| 示例 | 承载的能力点 | 本章落点 |
|---|---|---|
| ex01 迷你 vector 容量倍增与 reserve | 容量策略、引用/迭代器失效 | concept-01、pitfalls-1 |
| ex02 深拷贝、移动与 copy-and-swap | 移动语义、自赋值安全 | concept-01、pitfalls-2/3 |
| ex03 迷你 shared_ptr 控制块 | 引用计数、控制块布局 | concept-01、pitfalls-4 |
| ex04 循环引用与 weak_ptr | 内存泄漏根因、打破手段 | concept-01、pitfalls-5/6 |
| ex05 RAII 守卫三路径 | 资源释放钉死在析构 | concept-02/03、pitfalls-7/9 |
| ex06 线程池优雅关闭 | 并发组件工程化 | concept-02、pitfalls-15 |
| ex07 HTTP 请求行解析 | 确定性协议解析 | concept-02 |
| ex08 异常安全等级 | 基本/强/不抛 | concept-03、pitfalls-8 |
| ex09 移动 vs 拷贝计数 | 移动消除收益量化 | concept-04、pitfalls-10/11 |
| ex10 RVO / 移动消除 | NRVO、不要画蛇添足 move | concept-04、pitfalls-10/11 |
| ex11 虚函数表与对象模型 | vptr、动态绑定、切片 | concept-04、pitfalls-12/13 |
| ex12 STL 迭代器失效 | 容器复杂度与失效边界 | concept-04、pitfalls-14 |
| ex13 LRU Cache | 白板题参考实现 | concept-05、pitfalls-15 |

## 三、学完本章你将具备什么 / 进阶方向

- **能独立设计一个带所有权语义的 C++ 组件**：不再调 STL 就行，而是知道每个容器的失效边界、
  每个智能指针的代价，能在需要时拼出可用实现。
- **能写出异常安全、const 正确、RAII 彻底的代码**：这是区分会写和写得专业的分水岭。
- **能应对 C++ 高频面试**：虚表、移动语义、智能指针、迭代器失效、编译链接与内存布局都能讲清原理而非背结论。
- **进阶方向**：① 读源码（libstdc++ / folly / abseil）；② 参与开源（从修文档与单测起步）；
  ③ 跟进 C++23 新特性（`std::expected`、`std::mdspan`、`std::generator`、deducing this）。


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
