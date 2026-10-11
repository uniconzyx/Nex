# 01 · 线程的创建与生命周期：从 `start()` 到六种状态

## 一、理论根基：线程是「操作系统调度单元」在 JVM 中的句柄

Java 线程与内核线程在主流 JVM（HotSpot）上是**一对一**映射的：`new Thread(...)` 只是在 JVM 里造了个 Java 对象，真正创建内核线程发生在 `start()` 调用 `native` 方法的那一刻。这个「延迟创建」是理解 `start()` 与 `run()` 差异的关键。

三种创建方式，本质只有一种：

| 方式 | 写法 | 返回值 | 适用 |
|---|---|---|---|
| 继承 `Thread` | `class T extends Thread { public void run() {...} }` | 无 | 教学；**不推荐**（单继承被占用） |
| 实现 `Runnable` | `new Thread(() -> {...})` | 无 | 最常用；任务与线程解耦 |
| 实现 `Callable` | `FutureTask<T> ft = new FutureTask<>(() -> 42); new Thread(ft).start();` | `get()` 拿结果、可抛受检异常 | 需要返回值或异常传播 |

`Thread` 自身也实现了 `Runnable`，所以 `Callable` 最终也是被包装后交给 `Thread` 执行——**三种方式在字节码层面统一为「一个 `run()` 方法」**。

## 二、`start()` vs `run()`：新线程 vs 普通方法调用

`start()` 的语义是「**启动一个新线程，由新线程回调 `run()`**」，它内部会做两件事：调用 `native` 的 `start0()` 创建内核线程，并把线程状态从 `NEW` 迁移到 `RUNNABLE`。而直接调 `run()` 只是一个**普通方法调用**，仍在**当前线程**的调用栈上执行，不会产生任何并发。

```java
Thread t = new Thread(() -> System.out.println(Thread.currentThread().getName()));
t.run();    // 输出 main  —— 没开新线程
t.start();  // 输出 Thread-0 —— 开了新线程
```

此外，**同一个 `Thread` 对象不能 `start()` 两次**，第二次抛 `IllegalThreadStateException`（状态已是 `TERMINATED`，不可复活）。

## 三、六种状态与迁移条件

`Thread.State` 是 `getState()` 的返回值，六种状态及其**进入条件**：

```
NEW ──start()──> RUNNABLE ──┬─ 等锁（synchronized 未抢到） ──> BLOCKED
                            ├─ wait()/join()/park()      ──> WAITING
                            ├─ sleep(ms)/wait(ms)/join(ms) ─> TIMED_WAITING
                            └─ run() 正常结束/异常退出 ────> TERMINATED
```

几个高频易错点：

1. **`RUNNABLE` 是「可运行」而非「正在运行」**：它同时涵盖了「就绪等 CPU」和「正在跑」，**甚至涵盖阻塞式 IO 等待**（Java 不把 IO 等待单独建模为 BLOCKED）。所以看到 `RUNNABLE` 不等于线程在消耗 CPU。
2. **`BLOCKED` 只对应「等 `synchronized` 监视器锁」**；用 `ReentrantLock.lock()` 抢不到锁时线程处于 **`WAITING`**（因为 AQS 内部用的是 `LockSupport.park()`）。
3. **`WAITING` 与 `TIMED_WAITING` 的差别就是「有没有超时」**：`wait()` 无限等 vs `wait(1000)` 超时等。
4. **`TERMINATED` 之后不可恢复**：想「重启」只能 `new` 一个新线程。

## 四、中断：Java 的协作式取消

`Thread.stop()` 已被废弃（会在任意字节码处抛 `ThreadDeath`，破坏临界区一致性）。正确姿势是**协作式中断**：

- `t.interrupt()` 只是**设置中断标志位**（并唤醒处于 `wait`/`sleep`/`join` 的线程，抛 `InterruptedException` 并**清除标志**）。
- 被中断线程自己决定怎么响应：检查 `Thread.currentThread().isInterrupted()` 或捕获 `InterruptedException`。
- **吞掉 `InterruptedException` 是严重错误**（例如只 `printStackTrace()`），会破坏上层的中断协议。正确做法是「要么继续向上抛，要么 `Thread.currentThread().interrupt()` 恢复标志位」。

## 五、守护线程与线程优先级

- **守护线程（daemon）**：`setDaemon(true)` 必须在 `start()` 之前调用。当**所有非守护线程结束**时，JVM 直接退出，守护线程被抛弃（`finally` 可能不执行）。典型用途：GC、心跳、监控。**不要用它做有副作用的写盘**。
- **优先级**：`setPriority(1..10)` 只是**建议**，映射到操作系统优先级后行为因平台而异（Java 优先级有 5 级被 Windows 归并成 2 级）。**不要用优先级保证正确性**。

## 六、可运行代码

`examples/ex01-thread-lifecycle-states.json`：用「观测者轮询」的方式真实打印出 `NEW → TIMED_WAITING → BLOCKED → TERMINATED` 的状态迁移。
`examples/ex02-volatile-visibility.json`：用 `volatile` 标志位实现线程停止，并打印真实观测到的标志翻转。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **只用 `Runnable`/`Callable`，不要继承 `Thread`**：单继承很宝贵，且任务与线程解耦后才能交给线程池复用。
- 生产代码**别手写 `new Thread()`**，一律走线程池（见 concept 03）；手写线程无法复用、无界、无法统一监控与关闭。
- 判断线程池「卡住」时先看状态：大量 `BLOCKED` 说明**锁竞争**，大量 `WAITING` 说明**在等条件/等队列**，两者排查方向完全不同。
- `t.join()` 是主线程在等，别写反转了；带超时的 `join(ms)` 才是防止无限等待的正确姿势。

### 🎓 博士生视角
- `start0()` 是 `native` 方法，HotSpot 中最终落到 `os::start_thread`，**Java 线程与内核线程 1:1 绑定**（与 Go 的 M:N 协程模型、JDK 21 的虚拟线程有本质区别）。
- `Thread.State` 是 JVM 层面的抽象，**不等于操作系统的 PCB 状态**：`RUNNABLE` 把「就绪 / 运行 / 阻塞式 IO」三种内核态合并了，这正是它最容易误读的地方。
- 中断是**协作式**（cooperative）取消，不是抢占式；它把「如何安全地终止」的决策权交还给被中断方，从而避免 `Thread.stop()` 破坏**临界区的原子性不变量**。
- 守护线程的语义是「不阻止 JVM 退出」，因此它上面挂 `finally` 的可靠性没有保证——这不是实现缺陷，而是「守护」一词的必然推论。

### 📚 考研者视角
- 与 **408 操作系统「线程与进程」** 直接对应：Java 线程对应内核级线程，**用户级线程 vs 内核级线程**的对比是标准考法。
- 常考「线程的五状态（就绪/运行/阻塞/创建/终止）与 Java 六状态的映射」，注意 **408 的「阻塞」≈ Java 的 `BLOCKED` + `WAITING` + `TIMED_WAITING`**，这是口径差异最大的地方。
- 「进程 vs 线程」的经典对比（地址空间、切换开销、通信方式、独立/共享资源）在软件工程与操作系统两张卷里都可能出简答。
- 记忆锚点：**`start()` 才开线程、`run()` 只是方法调用**；**`BLOCKED` 只等 `synchronized`**；**`RUNNABLE` 不代表在耗 CPU**。
