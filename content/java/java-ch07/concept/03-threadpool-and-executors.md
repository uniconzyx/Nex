# 03 · 线程池：`ThreadPoolExecutor` 七参数、任务流程与拒绝策略

## 一、理论根基：为什么必须用线程池

线程的创建/销毁成本很高（内核态 `clone()`、栈空间 512KB~1MB 预留、上下文切换）。线程池的三个收益：**复用（降低创建销毁开销）+ 限流（防止无界创建打爆内存）+ 可管理（统一监控、关闭、命名、异常处理）**。

## 二、`ThreadPoolExecutor` 的七个构造参数

```java
new ThreadPoolExecutor(
    int corePoolSize,                    // 1 核心线程数（默认常驻）
    int maximumPoolSize,                 // 2 最大线程数
    long keepAliveTime, TimeUnit unit,   // 3 非核心线程空闲存活时间
    BlockingQueue<Runnable> workQueue,   // 4 任务队列
    ThreadFactory threadFactory,         // 5 线程工厂（命名/守护/优先级）
    RejectedExecutionHandler handler     // 6 拒绝策略
);
```
（第七个是隐含概念：**空闲线程回收策略** `allowCoreThreadTimeOut`。）

## 三、任务提交流程（`execute()` 的判定链）

这是必背的**四步判定**：

```
提交任务
  ├─ 1. 运行中的线程数 < corePoolSize ?           → 新建核心线程执行
  ├─ 2. 否则尝试入队 workQueue.offer(task)  成功 ? → 进队列排队
  ├─ 3. 否则（队满）线程数 < maximumPoolSize ?    → 新建非核心线程执行
  └─ 4. 否则                                     → 触发拒绝策略
```

**这张图解释了两个最具迷惑性的现象**：

1. **`LinkedBlockingQueue`（无界）会让 `maximumPoolSize` 形同虚设**：第 2 步永远成功，所以永远不会走到第 3 步——**池里最多只有 `corePoolSize` 个线程，剩下的任务全在队列里堆着**。这就是 `Executors.newFixedThreadPool` 的经典坑：队列无界 → OOM，且并发度上不去。
2. **`SynchronousQueue`（无容量）会让第 2 步永远失败**：任务必须立即被线程接走，否则走第 3 步。所以 `newCachedThreadPool`（`max = Integer.MAX_VALUE`）在任务暴增时会**无界创建线程**直到 OOM。

## 四、四种拒绝策略

| 策略 | 行为 | 适用 |
|---|---|---|
| `AbortPolicy`（默认） | 抛 `RejectedExecutionException` | 需要调用方感知、可回滚的业务 |
| `CallerRunsPolicy` | **由提交任务的线程自己跑** | 需要**反压（back pressure）**：让上游变慢 |
| `DiscardPolicy` | 静默丢弃 | 可丢的日志/埋点（但**静默**很危险） |
| `DiscardOldestPolicy` | 丢掉队首最老的，再重试提交 | 只要最新数据的场景（如行情快照） |

**生产建议**：用**自定义拒绝策略**（记录日志 + 计数 + 降级），至少不能静默丢。

## 五、四种常用队列的选型

| 队列 | 容量 | 特点 | 陷阱 |
|---|---|---|---|
| `ArrayBlockingQueue` | 有界数组 | 有界、公平可选、单锁 | 必须给足够容量，否则频繁拒绝 |
| `LinkedBlockingQueue` | **默认无界** | 吞吐高于 Array（读写两把锁） | **默认 `Integer.MAX_VALUE`，是 OOM 重灾区** |
| `SynchronousQueue` | 0 | 不存储，直接移交 | 必须配大 `max`，否则拒绝 |
| `PriorityBlockingQueue` | 无界 | 按优先级出队 | 任务必须实现 `Comparable` |

## 六、线程数怎么估？

- **CPU 密集**（纯计算、无阻塞）：`N_cpu + 1`（多 1 个应对偶发缺页中断）。
- **IO 密集**（等 DB/RPC/磁盘）：`N_cpu × (1 + W/C)`，`W`=等待时间、`C`=计算时间。等 90ms、算 10ms → 10 倍 → 8 核约 80 个（实践中还要留安全余量）。
- **现实中用压测修正**：公式只给起点，最终以「吞吐不再上升 / P99 开始恶化」的拐点为准。
- **不同业务用不同线程池**（隔离舱壁模式 / bulkhead）：别让「下单」和「发短信」共用一个池，一个慢调用拖垮全部。

## 七、优雅关闭与监控

```java
pool.shutdown();                                  // 1 不再收新任务，跑完已有任务
if (!pool.awaitTermination(30, SECONDS)) {        // 2 等待
    pool.shutdownNow();                           // 3 中断所有线程
    pool.awaitTermination(5, SECONDS);
}
```

- `shutdown()` vs `shutdownNow()`：前者温和（跑完队列），后者**中断 + 返回未执行的任务列表**。
- 监控必须暴露的四个指标：`getActiveCount()`（正在执行）、`getQueue().size()`（排队）、`getCompletedTaskCount()`（累计完成）、`getLargestPoolSize()`（峰值线程数）。
- **命名线程**（`ThreadFactory` 里 `setName`）几乎是最便宜的排障投资：`jstack` 里 `order-pool-3` 远好过 `pool-1-thread-3`。

## 八、`Executors` 四个工厂方法的误用风险（阿里规约明令禁止）

| 工厂方法 | 实现 | 风险 |
|---|---|---|
| `newFixedThreadPool` | 核心=最大=N，`LinkedBlockingQueue`（无界） | **队列 OOM** |
| `newSingleThreadExecutor` | 同上，N=1 | 同上，且串行成瓶颈 |
| `newCachedThreadPool` | 核心 0，最大 `MAX_VALUE`，`SynchronousQueue` | **线程数 OOM** |
| `newScheduledThreadPool` | `DelayedWorkQueue`（无界） | 任务堆积 OOM |

**结论：用 `new ThreadPoolExecutor(...)` 显式传参**，把「队列容量 + 拒绝策略 + 线程命名」写清楚。

## 九、`CompletableFuture`：从「提交任务」到「编排任务」

线程池只解决「怎么跑」，`CompletableFuture` 解决「怎么把多个异步步骤串起来」：

- **串行**：`thenApply`（同类型转换）/ `thenCompose`（扁平化，避免 `CF<CF<T>>`）。
- **并行汇聚**：`allOf`（等全部）/ `anyOf`（等任一）；`thenCombine` 合并两个结果。
- **异常**：`exceptionally` / `handle`（正常与异常统一出口）。
- **线程池**：**不传 Executor 会默认用 `ForkJoinPool.commonPool()`**，生产上必须显式传业务线程池，否则会与并行流互相干扰。

## 十、可运行代码

`examples/ex06-threadpool-parameters.json`：真实打印 `ThreadPoolExecutor` 在「核心 → 队列 → 非核心 → 拒绝」四步上的计数变化。
`examples/ex07-rejection-policy.json`：对比 `AbortPolicy` 抛异常与 `CallerRunsPolicy` 反压的实际效果。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **绝不用 `Executors` 工厂**（无界队列/无界线程 OOM）；一律 `new ThreadPoolExecutor` 显式指定有界队列 + 命名工厂 + 自定义拒绝策略。
- **一个业务一个池**：隔离舱壁，避免级联雪崩；给池起有意义的名字，`jstack` / 监控面板直接受益。
- 拿不准线程数时给个偏小的初值（宁小勿大）：线程太多会让上下文切换与 GC 一起恶化，`W/C` 公式要用**实测**校准。
- `submit()` 会**吞掉异常**（异常藏在 `Future` 里，不 `get()` 就永远看不到）；日志型任务用 `execute()` 更安全——异常会走 `Thread.UncaughtExceptionHandler`。

### 🎓 博士生视角
- 线程池本质是**「资源池化 + 排队论」的工程实现**：`core/queue/max` 三步判定实际上是在「响应时间」与「资源占用」之间做权衡——`max` 大则响应快但上下文切换多，`max` 小则吞吐稳定但延迟抖动。
- `LinkedBlockingQueue` 用**两把锁**（`putLock`/`takeLock` + 各自的 `Condition`）实现读写并行，吞吐高于 `ArrayBlockingQueue` 的单锁实现，这是「数据规模无界」换来的，代价正是 OOM 风险。
- `CallerRunsPolicy` 是**反压（backpressure）**的最朴素实现：把排队压力回灌到上游调用方，使其自然降速——与响应式流的 `request(n)` 是同一思想的两种形态。
- `CompletableFuture` 默认落在 `ForkJoinPool.commonPool()`，其并行度默认 `N_cpu - 1`；在容器里若 `availableProcessors` 读的是宿主核数，会与 CPU quota 不一致，**这是云原生环境的经典故障源**。

### 📚 考研者视角
- 对应 **408 「死锁 / 进程调度 / 资源分配」与「生产者-消费者问题」**：线程池 = **有界缓冲区的生产者-消费者**，队列满则拒绝 ≈ 「缓冲区满则阻塞/丢弃」策略。
- 常考「银行家算法」与「资源分配图」，与本章的「线程池限流」是同一思想的两种尺度：**预分配 + 拒绝**优于**超额分配 + 崩溃**。
- 「线程数估算公式 `N×(1+W/C)`」是软件工程 / 系统设计简答题的通用素材，建议与「CPU 密集 vs IO 密集」一起记。
- 记忆锚点：**四步判定（核心 → 队列 → 最大 → 拒绝）**、**`FixedThreadPool` 队无界 OOM**、**`CachedThreadPool` 线程无界 OOM**。
