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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [chenshuo/muduo](https://github.com/chenshuo/muduo) | 16,279 | §2.2 二、实现机制：三种 RAII 锁的差异 | 读 `chenshuo/muduo` 的 `muduo/base/Mutex.h`：`MutexLockGuard` 只在构造/析构里加解锁；配套 `muduo/base/Condition.h` 的 `wait()` 内部「解锁 → 等待 → 重新加锁」，`muduo/net/EventLoop.cc` 则示范 one loop per thread——三处合起来就是本章 §4.2「实现机制：wait 的三件事」的完整实现；注意 `wait` 必须传加锁的 guard，否则「检查条件」与「进入等待」之间存在丢唤醒窗口 |
| 2 | [taskflow/taskflow](https://github.com/taskflow/taskflow) | 12,214 | §5.3 三、线程池：为什么必要 | 读 `taskflow/taskflow` 的 `taskflow/core/executor.hpp`：`Executor` 预先起 `_config.num_workers` 个线程，每个 worker 在自己的 `_wsq`（work-stealing queue）上取任务，空闲时从别人队尾偷；读 `_wait_for_task` 与 `_steal` 两个函数，就懂「任务图 + 工作窃取」如何避免线程空转——这正是本章 §5.1「高层并发抽象」里说的「比裸线程多出来的那一层价值」 |
| 3 | [apache/brpc](https://github.com/apache/brpc) | 17,638 | §5.1 一、理论根基：高层并发抽象 | 读 `apache/brpc` 的 `src/bthread/bthread.h`：`src/bthread/` 用 M:N 调度（大量 bthread 跑在少量 pthread 上），把「阻塞等待」换成用户态挂起；对照 `std::thread` 的 1:1 模型，能看清本章说的「线程池解决的是创建成本，协程解决的是调度成本」——两者叠加才是 §5.2「async 的启动策略」要权衡的全貌 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（thread 启动与 join（无共享状）核对 |
| 2 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | §3.2 三种内存序 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex02`（mutex + lock_guard 保）核对 |
| 3 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex03`（scoped_lock 一次性安全锁两把）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（条件变量生产者-消费者（带谓词）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
