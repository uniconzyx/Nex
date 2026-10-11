# cpp-ch16 · 并发与多线程：thread / mutex / atomic / async

## 学习目标
完成本章后，你能：
1. 用 `std::thread` 启动线程，理解 `join`（等待）/ `detach`（分离）的语义与「必须二选一」的硬约束。
2. 讲清**数据竞争**与**内存模型（happens-before）**，知道「为什么不加保护地 `++` 会出错」。
3. 用 `std::mutex` + `lock_guard` / `unique_lock` / `scoped_lock` 做 RAII 式加锁，理解死锁四条件与避免（锁序、`std::lock`、超时）。
4. 用 `std::atomic` 做无锁计数，理解内存序（relaxed / acquire-release / seq_cst）的差异与边界。
5. 用**条件变量**做生产者-消费者，并正确处理**虚假唤醒**（用谓词）。
6. 用 `std::async` / `future` / `promise` 取结果、传异常；理解默认启动策略的同步陷阱。
7. 理解**线程池**为何必要，以及 `std::jthread`（C++20）自动 join + 协作取消的设计动机。

## 前置
- cpp-ch05 类与对象（RAII 思想基础）
- cpp-ch10 智能指针与 RAII（资源管理范式）

## 真题依据（真实可查）
- LeetCode 1114 按序打印（`print-in-order`）——用条件变量/信号量控制执行序。
- LeetCode 1226 哲学家进餐（`the-dining-philosophers`）——经典死锁/活锁案例。

## 验收标准
- 能写出一个「线程安全计数器」，用 mutex 或 atomic 得到确定性总数。
- 能复现并修复一把以上死锁（用 `std::lock` 或固定锁序）。
- 能解释 `async(std::launch::async)` 与默认策略在「是否真正并行」上的差异。

## 面试权重
- 高：数据竞争、内存序、死锁规避、条件变量虚假唤醒、`async` 异常传递是并发面试核心；
  与「操作系统调度、缓存一致性、无锁编程」深度挂钩，是区分候选人的重要维度。


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
