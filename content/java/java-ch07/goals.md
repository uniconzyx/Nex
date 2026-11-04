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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §2.2 happens-before：JMM 给出的「可见性合同」 | 读 `docs/java/concurrent/` 的并发基础问答：`volatile` 给可见性与有序性、不给原子性，`count++` 用它照样丢更新——本章的可运行代码会把这个结论跑出来；先读 §2.1 并发三大问题，才知道要分别用哪条语义去解 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §3.2 `ThreadPoolExecutor` 的七个构造参数 | 看 `mall-portal` 里的异步任务配置：核心数、队列、拒绝策略三者的组合决定了「任务堆积时是先扩容还是先拒绝」，无界队列会让 OOM 来得更晚但更猛；这正是 §3.3「execute() 的判定链」在真实项目里的落点 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §3.3 任务提交流程（`execute()` 的判定链） | 对照 `docs/high-concurrency/threadpool.md`：核心线程 → 队列 → 最大线程 → 拒绝策略的四级判定，它用图示说明了「为什么不是先扩容」；配合 §3.8「Executors 四个工厂方法的误用风险」，就明白 `newFixedThreadPool` 的无界队列坑在哪 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §4.1 理论根基：AQS —— JUC 的「半成品锁」 | 看 `core-java` 的锁示例：公平锁与非公平锁的吞吐差异、`tryLock` 的超时语义，样例里能直接改参数对比；读完再回 §4.2「ReentrantLock vs synchronized」，取舍标准才对得上有依据 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（六种线程状态实测）核对 |
| 2 | 黑马程序员 · Java 并发编程（JUC）<br><sub>黑马程序员</sub> | [BV16J411h7Rd](https://www.bilibili.com/video/BV16J411h7Rd/) | §2.1 并发三大问题 | synchronized 监视器、volatile 内存语义、AQS 与线程池参数逐个拆开讲，并发章的唯一主线；看完回 `ex02`（volatile 与 synchroni）核对 |
| 3 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | 全章 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex03`（int / volatile int /）核对 |
| 4 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | §1.1 线程是「操作系统调度单元」… | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex04`（CAS 的 ABA 问题与 Atomic）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
