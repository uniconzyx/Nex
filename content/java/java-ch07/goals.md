# java-ch07 · 并发：Thread、线程池与 JUC 并发容器 · 学习目标

- 掌握 **线程的三种创建方式**（继承 `Thread` / 实现 `Runnable` / 实现 `Callable` + `FutureTask`）与各自适用场景
- 厘清 **线程的六种状态**（`NEW` / `RUNNABLE` / `BLOCKED` / `WAITING` / `TIMED_WAITING` / `TERMINATED`）与状态迁移的触发条件，区分 `start()` 与 `run()` 的本质差异
- 理解 **Java 内存模型（JMM）** 与 **happens-before 规则**，能解释「可见性」「有序性」「原子性」三者在 Java 中的具体落地手段
- 掌握 **`volatile`** 的语义边界（保证可见性与禁止重排序，**不保证复合操作原子性**）与 **`synchronized`** 的互斥、可见性、可重入三重语义
- 掌握 **CAS 与原子类**（`AtomicInteger` / `AtomicReference` / `LongAdder`），理解 **ABA 问题**及 `AtomicStampedReference` 的解法
- 掌握 **`ThreadPoolExecutor` 的七个构造参数**与任务提交流程（核心线程 → 阻塞队列 → 非核心线程 → 拒绝策略），理解 `Executors` 四个工厂方法在**生产环境的误用风险**
- 能按任务类型估算**线程数**（CPU 密集 / IO 密集），并实现线程池监控与**优雅关闭**
- 掌握 **JUC 并发容器**：`ConcurrentHashMap` 的演进（分段锁 → CAS + `synchronized` + 红黑树）、`CopyOnWriteArrayList` 与四种阻塞队列的选型
- 掌握 **同步工具类**：`CountDownLatch` / `CyclicBarrier` / `Semaphore` / `CompletableFuture` 编排
- 能识别并**排查死锁**（`jstack` / `ThreadMXBean.findDeadlockedThreads()`），给出破坏死锁四条件的工程手段

## 前置
- java-ch02（对象模型、`equals`/`hashCode`）
- java-ch03（多态、接口、lambda 与函数式接口）

## 真题依据（真实可查）
- LeetCode 1114 按序打印（`print-in-order`）—— 用并发同步原语保证执行顺序
- LeetCode 1115 交替打印 FooBar（`print-foobar-alternately`）—— 条件同步与唤醒
- LeetCode 1116 打印零与奇偶数（`print-zero-even-odd`）—— 状态机式线程协作

## 验收标准
- 能写出三种创建方式，并说明为什么 `run()` 不会开新线程
- 能画出六种线程状态的迁移图，并说出 `BLOCKED` 与 `WAITING` 的差别
- 能用 happens-before 解释一段无锁代码为什么「可能读到旧值」，并给出两种修法
- 能说出 `ThreadPoolExecutor` 提交任务时的完整判定链，并指出 `newFixedThreadPool` 在什么情况下会 OOM
- 能说出 `ConcurrentHashMap` 在 JDK 8 为什么不再用分段锁，以及为什么它的迭代器是**弱一致**的
- 能用 `ThreadMXBean` 检测出一段两把锁交叉加锁造成的死锁，并用**锁排序**修掉


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计 |
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | Spring 官方生态的系统化代码教程仓库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Java 零基础（宋红康） | [视频](https://www.bilibili.com/video/BV1Qb411g7cz/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚学堂 · 高淇 Java 300 集 | [视频](https://www.bilibili.com/video/BV1ct411n7oG/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 求知课堂 · Java 入门到精通 | [视频](https://www.bilibili.com/video/BV1CJ411m7gg/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · 谷粒商城（分布式实战项目） | [视频](https://www.bilibili.com/video/BV1np4y1C7Yf/) | 本学科配套视频，建议结合本章示例与习题观看 |
