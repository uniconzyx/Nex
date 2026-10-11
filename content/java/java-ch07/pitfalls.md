# java-ch07 · 陷阱清单：并发代码中最容易写错的十件事

1. **直接调用 `run()` 而不是 `start()`** —— `run()` 只是普通方法调用，仍在**当前线程**执行，完全没有并发；必须 `start()` 才会创建新线程回调 `run()`。判断方法：打印 `Thread.currentThread().getName()`，若还是 `main` 就说明写错了。

2. **把 `volatile` 当原子变量用** —— `volatile int count; count++` **不安全**：`count++` 是「读 → 加 → 写」三步，`volatile` 只保证每步可见，不保证三步整体原子。正确写法：`AtomicInteger.incrementAndGet()`，或把复合操作放进 `synchronized`。

3. **用 `Executors.newFixedThreadPool` 处理无界任务** —— 它的队列是 `LinkedBlockingQueue`（默认容量 `Integer.MAX_VALUE`），任务堆积时**队列 OOM**，且 `maximumPoolSize` 形同虚设（第 2 步永远成功，走不到第 3 步）。正确写法：`new ThreadPoolExecutor(n, n, 0, MS, new ArrayBlockingQueue<>(1000), factory, handler)`。

4. **用 `Executors.newCachedThreadPool` 处理突发流量** —— `maximumPoolSize = Integer.MAX_VALUE` + `SynchronousQueue`，队满（无容量）就直接建线程，突发流量下**线程数 OOM**。正确写法：显式给 `max` 加上界。

5. **`ReentrantLock` 忘记在 `finally` 中 `unlock()`** —— 一旦 `try` 块内抛异常，锁**永久泄漏**，后续线程全部挂死。正确写法：`lock.lock(); try { ... } finally { lock.unlock(); }`。

6. **在 `ConcurrentHashMap` 上写「两步复合操作」** —— `if (map.get(k) == null) map.put(k, v)` 中间存在竞态，两个线程可能都判空并各自写入。正确写法：`map.computeIfAbsent(k, x -> v)` / `map.merge(k, 1, Integer::sum)`。

7. **吞掉 `InterruptedException`** —— 捕获后只 `printStackTrace()` 会**清除中断标志**，破坏上层的中断协议，导致线程池 `shutdownNow()` 无法真正停下任务。正确写法：要么继续向上抛，要么 `Thread.currentThread().interrupt()` 恢复标志位后返回。

8. **双重检查锁定（DCL）单例漏写 `volatile`** —— `volatile` 禁止「引用赋值」与「对象初始化」重排序；漏写会让其他线程拿到**非 `null` 但字段未初始化的半成品对象**。正确写法：`private static volatile Singleton inst;`。

9. **`submit()` 提交的任务异常被静默吞掉** —— `submit()` 返回 `Future`，异常被包在里面，**不调用 `get()` 就永远看不到**（连日志都没有）。要么改用 `execute()`（异常会走 `UncaughtExceptionHandler`），要么对 `Future` 调用 `get()` 并处理 `ExecutionException`。

10. **用 `Thread.stop()` 或靠线程优先级保证正确性** —— `Thread.stop()` 会在任意字节码处抛 `ThreadDeath`，破坏临界区一致性，已废弃；线程优先级只是**建议**，跨平台行为不一致，**绝不可用于保证正确性或时序**。正确写法：`interrupt()` + 标志位协作取消。
