# 04 · JUC 锁与并发容器：AQS、`ConcurrentHashMap` 与同步工具

## 一、理论根基：AQS —— JUC 的「半成品锁」

`AbstractQueuedSynchronizer`（AQS）是 `ReentrantLock`、`Semaphore`、`CountDownLatch`、`ReadWriteLock` 的共同底座。它用两个零件撑起了整个 JUC 同步器家族：

1. **一个 `volatile int state`**：表示同步状态（`ReentrantLock` 用它记重入次数；`Semaphore` 用它记许可数；`CountDownLatch` 用它记剩余计数）。
2. **一个 CLH 变体的双向 FIFO 等待队列**：抢不到状态的线程被包装成 `Node` 入队，通过 `LockSupport.park()` 挂起，前驱释放时 `unpark()` 唤醒后继。

**模板方法模式**：AQS 把「怎么算抢到」（`tryAcquire`）留给子类，把「排队、挂起、唤醒」这套**易错的状态机**统一实现——这就是它的设计价值。

## 二、`ReentrantLock` vs `synchronized`

| 维度 | `synchronized` | `ReentrantLock` |
|---|---|---|
| 加锁/释放 | 隐式（代码块/方法） | **必须 try/finally 手动 `unlock()`** |
| 可中断 | 否 | `lockInterruptibly()` **可响应中断** |
| 超时 | 否 | `tryLock(timeout)` **可避免死等** |
| 公平性 | 非公平 | **可选公平/非公平** |
| 条件队列 | 1 个（`wait`/`notify`） | **多 `Condition`，可精确唤醒** |
| 性能 | JDK 6 后已优化，差距很小 | 功能更丰富时才用 |

**锁的两条纪律**：
- `unlock()` 必须写在 `finally` 里，否则异常路径会**永久泄漏锁**。
- **公平锁吞吐低于非公平锁**（非公平允许「插队」，减少唤醒抖动），只在「饥饿会出问题」时才用公平锁。

## 三、`ConcurrentHashMap`：两次重构与「弱一致」

**JDK 7：分段锁（Segment）**——把桶数组切成 N 段，每段一把 `ReentrantLock`，锁粒度 = 段。并发度 = 段数（默认 16），扩容只扩段内。

**JDK 8：CAS + `synchronized` + 链表/红黑树**——去掉分段锁，改成：

- **桶（bin）为空** → 用 **CAS** 直接放头节点（无锁）。
- **桶非空** → 对**桶的头节点** `synchronized`（锁粒度细到「一个桶」）。
- **链表长度 ≥ 8 且表长 ≥ 64** → 转**红黑树**（查询从 O(n) 降到 O(log n)）；**< 6 退回链表**。
- **`size()`** → 用 `baseCount` + `CounterCell[]` 分段计数（与 `LongAdder` 同思路），所以 `size()` 是**弱一致**的近似值，不保证精确。

**为什么迭代器是「弱一致（weakly consistent）」**：`CHM` 的迭代器**不加锁、不抛 `ConcurrentModificationException`**，返回的是「创建迭代器那一刻及之后某时刻」的近似快照。这与 `HashMap` 的 fail-fast（快速失败，modCount 变化即抛 CME）是两种截然不同的设计哲学。

**必须用原子复合方法**：`get` + `put` 两步在 CHM 上依然有竞态，正确写法是：

```java
map.merge(k, 1, Integer::sum);                               // 原子计数（推荐）
map.compute(k, (k2, old) -> old == null ? 1 : old + 1);      // 原子读-改-写
// 注意：computeIfAbsent 只保证「创建映射」这一步原子，
// 它返回的集合本身若线程不安全（如 ArrayList），后续 add 仍会丢更新！
map.computeIfAbsent(k, k2 -> new CopyOnWriteArrayList<>()).add(v);
```

## 四、`CopyOnWriteArrayList`：写时复制

每次写都**复制整个数组**再替换内部 `volatile` 引用。因此：**读完全无锁（极快）+ 写代价 O(n)（很贵）+ 迭代器是快照（永不 CME）**。

**适用**：**读多写极少**、数据集小、且要求迭代期间绝对安全——典型是「监听器列表」「白名单/配置」。**不适用**：写频繁的列表（每次写都复制整个数组，会疯狂产生垃圾并把 GC 拖垮）。

## 五、四种阻塞队列的选型

| 队列 | 结构 | 有界性 | 场景 |
|---|---|---|---|
| `ArrayBlockingQueue` | 数组 + 单锁 | **必须指定容量** | 通用有界缓冲 |
| `LinkedBlockingQueue` | 链表 + 双锁 | 默认无界 | 高吞吐，**须显式给容量** |
| `SynchronousQueue` | 不存储 | 0 | 直接移交（`CachedThreadPool`） |
| `PriorityBlockingQueue` | 堆 | 无界 | 按优先级出队 |
| `DelayQueue` | 优先队列 | 无界 | 延迟任务、缓存过期 |

生产者-消费者用阻塞队列时，**四个 API 一定要分清**（面试常问）：

| 操作 | 抛异常 | 返回特殊值 | **阻塞** | **超时** |
|---|---|---|---|---|
| 插入 | `add(e)` | `offer(e)`→false | `put(e)` | `offer(e, t, u)` |
| 移除 | `remove()` | `poll()`→null | `take()` | `poll(t, u)` |

## 六、同步工具类四件套

| 工具 | 语义 | 是否可重用 | 典型场景 |
|---|---|---|---|
| `CountDownLatch` | **一次性倒计数**，计数到 0 后所有等待者放行 | **否**（到 0 就废了） | 主线程等 N 个子任务就绪 |
| `CyclicBarrier` | **栅栏**，N 个线程互相等待到齐后一起继续 | **是**（可循环） | 分阶段并行计算 |
| `Semaphore` | **许可**，限流/限并发 | 是 | 限流到 N 个并发 |
| `Phaser` | 更灵活的分阶段同步 | 是 | 多阶段、动态增减参与者 |

**它们都能用 AQS 实现**：`CountDownLatch` 的 `state` 就是计数、`Semaphore` 的 `state` 就是许可——这也是理解 AQS 的一条捷径。

## 七、死锁：四条件、排查与破坏

**死锁四必要条件**（缺一不可）：**互斥 + 占有且等待 + 不可抢占 + 循环等待**。工程上最好下手的是**循环等待**——**给所有锁定义全局顺序，所有线程按同一顺序加锁**。

**排查手段**：
- `jstack <pid>`：JVM 会直接打印 `Found one Java-level deadlock:` 段落，列出互相等待的线程与堆栈。
- 代码内自检：`ManagementFactory.getThreadMXBean().findDeadlockedThreads()` 返回死锁线程 id 数组（**这是公开 API，可用于监控告警**）。

**其他破坏手段**：`tryLock(timeout)`（破坏「不可抢占」的无限等待）、资源一次性申请（破坏「占有且等待」）、减少锁持有范围与嵌套。

## 八、可运行代码

`examples/ex08-concurrent-collections.json`：对比 `ConcurrentHashMap` 的原子复合操作与「`get`+`put`」两步写法在并发下的计数差异。
`examples/ex10-deadlock-detect-and-prevent.json`：用 `ThreadMXBean` **真实检测出**两把锁交叉加锁造成的死锁，再用**锁排序**修掉并验证不再死锁。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `ReentrantLock` 的 `unlock()` **必须进 `finally`**；这是最常见的锁泄漏。能用 `synchronized` 就别上 `ReentrantLock`（少一类 bug）。
- CHM 上永远用 `computeIfAbsent` / `merge` / `compute`，**别写 `if (map.get(k)==null) map.put(...)`**——那两步之间别的线程可以插进来。
- **但 `computeIfAbsent` 不是万能的**：它保证的是「创建映射」原子，返回的集合若是 `ArrayList`，后续 `add` 依然会丢数据（实测 8 线程 × 100 次插入得到 781 而非 800）。正确做法是值本身用 `CopyOnWriteArrayList` / 并发容器，或改用 `ConcurrentHashMap.newKeySet()`。
- `CopyOnWriteArrayList` 只适合读多写少；写频繁时它会因为「每次写复制整个数组」把 GC 打爆。
- 死锁排查口诀：**先 `jstack` 看有没有 deadlock 段，再找「互相持有的两把锁」，最后按全局锁序重排加锁顺序**。

### 🎓 博士生视角
- AQS 是**模板方法模式**的教科书案例：把「同步语义」（`tryAcquire`）与「排队机制」（CLH 队列 + `park/unpark`）解耦，使 `Semaphore`/`Latch`/`Lock` 能用不到 100 行代码实现。
- `ConcurrentHashMap` 从「粗粒度分段锁」到「细粒度 CAS + 单桶 `synchronized`」的演进，反映了一个通用规律：**锁粒度越小 → 竞争越低，但实现复杂度与一致性推理成本越高**。
- CHM 的**弱一致性迭代器**刻意放弃了「线性一致性」，换取「无锁遍历 + 不抛 CME」；这是一种**CAP 式的工程取舍**——在同一数据结构内部，对「一致性强度」和「可用性/吞吐」做了取舍。
- 死锁四条件是**必要条件而非充分条件**：破坏其一即可避免死锁，但「持有并等待」的破坏（一次性申请全部资源）会显著降低资源利用率——这正是「避免死锁」与「提高并发」的张力所在。

### 📚 考研者视角
- 死锁四条件、银行家算法、资源分配图化简是 **408 操作系统必考大题**；本章的 `ThreadMXBean` 检测对应「**死锁检测**」策略，锁排序对应「**死锁预防**」，`tryLock` 对应「**死锁避免**」——三条路线务必分清。
- 生产者-消费者（有界缓冲区）是**信号量经典应用**：`mutex` + `empty` + `full` 三个信号量的 P/V 顺序**不能颠倒**（先 P 资源再 P 互斥），这是最常见的扣分点。阻塞队列就是它的库化实现。
- 「读者-写者问题」对应 `ReadWriteLock` / `CopyOnWriteArrayList`：读优先、写优先、公平三种策略要能写出伪代码。
- 记忆锚点：**AQS 一状态一队列**、**CHM 桶空 CAS / 桶非空锁头节点**、**死锁四条件「互请不循」**。
