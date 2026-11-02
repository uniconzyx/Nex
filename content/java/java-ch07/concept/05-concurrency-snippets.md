# java-ch07 · 并发实战片段

> 把 §1–§4 的机制落成可粘贴运行的最小例子。并发的坑几乎都在「可见性、原子性、有序性」三件事上。

### Thread 创建与生命周期

```java
Thread t = new Thread(() -> System.out.println("running"));
t.start();          // 启动新线程，不要直接调 run()
t.join();           // 等它结束
// 状态：NEW → RUNNABLE → BLOCKED/WAITING → TERMINATED
```

### 可见性与 volatile

```java
volatile boolean stop = false;   // 保证多线程间可见，避免缓存导致读不到新值
// 不保证复合操作（i++）的原子性，只保证单次读写的可见性
```

### 原子类与 CAS

```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();         // 基于 CAS，无锁且原子，比 synchronized 轻
```

### 线程池参数与拒绝策略

```java
ExecutorService pool = new ThreadPoolExecutor(
    4, 8, 60, TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(100),
    new ThreadPoolExecutor.CallerRunsPolicy()); // 队列满时由调用线程执行，温和反压
```

### Lock 与 synchronized 对比

`synchronized` 自动释放、不可中断；`ReentrantLock` 可 `tryLock(timeout)`、可公平、可多条件变量，灵活但需手动 `unlock()`（放 `finally`）。

### JUC 并发容器

`ConcurrentHashMap`（分段/桶级锁）、`CopyOnWriteArrayList`（读多写少）、`BlockingQueue`（生产者消费者）替代手动加锁的集合。

### Future 与异常捕获

```java
Future<?> f = pool.submit(() -> { throw new RuntimeException("boom"); });
try { f.get(); }                 // 不调 get()，异常被静默吞掉
catch (ExecutionException e) { log.error(e.getCause()); }
```

### ThreadLocal 与内存泄漏

```java
static ThreadLocal<User> ctx = new ThreadLocal<>();
ctx.set(user);
try { /* 业务 */ } finally { ctx.remove(); }  // 必须 remove，否则线程池复用会串数据/泄漏
```

### 中断协作取消

```java
while (!Thread.currentThread().isInterrupted()) {
    doWork();
}
// 用 interrupt() 而非 Thread.stop()（已废弃，破坏临界区一致性）
```

### 死锁四个必要条件

互斥、占有且等待、不可抢占、循环等待。破坏任一即可避免：按固定顺序加锁、用 `tryLock`、一次性申请全部资源。

## 三视角解析
### 🧑‍💻 程序员视角
`volatile` 只保证可见性与禁止重排序，不保证原子性——`count++` 用它依然会丢更新，得用 `AtomicInteger`。线程池参数不设队列上限，任务堆积到 OOM 才暴露；`Executors.newFixedThreadPool` 用的是无界队列，生产环境应手动 `new ThreadPoolExecutor` 并指定有界队列与拒绝策略。`ThreadLocal` 用完不 `remove`，线程池复用线程时会把上一个请求的数据带给下一个请求，这是最隐蔽的数据串号。

### 🎓 博士生视角
Java 内存模型（JMM）用 `happens-before` 定义跨线程可见性：`volatile` 写与读建立同步边、`synchronized` 的解锁与加锁建立同步边、`final` 字段的正确构造保证安全发布。`CAS` 是 `AtomicInteger` 的底层，依赖 CPU 的 `cmpxchg` 指令，失败时自旋重试；高竞争下自旋浪费 CPU，Java 8 的 `LongAdder` 用分段累加缓解。线程池的核心是「核心线程 → 队列 → 最大线程 → 拒绝策略」的四级决策，理解这个顺序才能解释「为什么任务先排队而不是先扩容」。

### 📚 考研者视角
笔试高频：
1. **线程状态**：`NEW`/`RUNNABLE`/`BLOCKED`/`WAITING`/`TIMED_WAITING`/`TERMINATED` 六态与转换。
2. **`synchronized` 与 `Lock`**：前者自动释放、后者需 `finally` 解锁但支持可中断、超时、公平锁。
3. **线程池七参数**：核心数、最大数、空闲存活、时间单位、工作队列、线程工厂、拒绝策略。
4. **`volatile` 的两个语义**：可见性、有序性（禁止指令重排），不含原子性。
