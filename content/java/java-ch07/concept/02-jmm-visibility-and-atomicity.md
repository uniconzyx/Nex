# 02 · JMM、可见性与原子性：`volatile` 与 `synchronized` 到底保证了什么

## 一、理论根基：并发三大问题

多线程访问共享可变状态时，只有同时解决下面三件事才是安全的：

| 问题 | 含义 | 反例 |
|---|---|---|
| **原子性** | 一个或多个操作要么全做、要么全不做 | `count++` 编译成「读-改-写」三条指令，可被打断 |
| **可见性** | 一个线程的写，另一个线程能立刻看到 | 写进 CPU 缓存/寄存器，未及时刷回主存 |
| **有序性** | 代码按编写顺序生效 | 编译器/CPU 为了流水线重排序指令 |

`volatile` 解决**可见性 + 有序性**，`synchronized` 三者都解决，**原子类**解决特定复合操作的原子性。

## 二、happens-before：JMM 给出的「可见性合同」

JMM 不用「缓存/主存」这类硬件术语规定行为，而是用 **happens-before（HB）** 这个抽象关系来定义什么读写一定可见。规则（背下来）：

1. **程序顺序**：同一线程内，前面的操作 HB 后面的操作。
2. **监视器锁**：对同一把锁的 `unlock` HB 于后续的 `lock`。
3. **`volatile` 变量**：对 `volatile` 字段的写 HB 于后续对该字段的读。
4. **线程启动**：`t.start()` HB 于 `t` 中的所有操作。
5. **线程终止**：`t` 中所有操作 HB 于 `t.join()` 之后。
6. **传递性**：A HB B，B HB C ⟹ A HB C。

**关键推论**：只要存在一条 HB 链把「写」连到「读」，读就一定能看到写的值——哪怕中间隔了线程和线程池。这也是「`final` 字段安全发布」的根据。

## 三、`volatile` 的两条语义与一个不保证

**语义一（可见性）**：写 `volatile` 立即刷回主存并使其他 CPU 缓存行失效；读 `volatile` 强制从主存读。

**语义二（有序性）**：JMM 在 `volatile` 写前后插入 **StoreLoad 屏障**，禁止屏障两侧的重排序。这使 `volatile` 成为「轻量级的同步」——**没有互斥**，只有可见性与有序性。

**不保证（原子性）**：`volatile int count; count++` **仍然不安全**，因为它不是一个动作而是「读 → 加 → 写」三步。**这是面试最爱的陷阱**。

`volatile` 的正确用法有两种，别记岔：
- **状态标志位**：`volatile boolean shutdown;` —— 一写多读。
- **双重检查锁定（DCL）单例的第二重检查**：

```java
class Singleton {
    private static volatile Singleton inst;          // volatile 不可省
    static Singleton get() {
        if (inst == null) {                          // 第一次检查：避免每次加锁
            synchronized (Singleton.class) {
                if (inst == null) inst = new Singleton();   // 第二次检查：防重复创建
            }
        }
        return inst;
    }
}
```

**为什么必须 `volatile`**：`new Singleton()` 会编译成「分配内存 → 初始化对象 → 把引用赋给 `inst`」，其中**初始化与赋值可能被重排序**。若线程 A 走到「已分配、未初始化」时线程 B 做第一次检查，就会拿到一个「非 null 但字段全是默认值」的半成品对象。`volatile` 禁止这个重排序。

## 四、`synchronized` 的三重语义与锁升级

`synchronized` 同时提供 **互斥（原子性）+ 可见性 + 可重入**：

- **互斥**：同一监视器（monitor）同一时刻只允许一个线程进入。
- **可见性**：锁释放前把工作内存刷回主存，获取锁时清空本地内存副本并重读——等价于「unlock HB lock」。
- **可重入**：同一线程可重复获得同一把锁（monitor 内部有**重入计数**），这解决了「同步方法互相调用」的死锁问题。

**对象头 Mark Word 与锁升级**（HotSpot 优化路径，面试高频）：

```
无锁 ──(首次竞争)──> 偏向锁 ──(第二个线程来)──> 轻量级锁(自旋 CAS)
                                                    │
                                          自旋失败/竞争激烈
                                                    ↓
                                              重量级锁(操作系统 mutex，挂起线程)
```

要点：**升级不可逆**（重量级不会退回偏向），偏向锁在 JDK 15 起默认关闭（JDK 18 移除）。`synchronized` 在 JDK 6 之后经过大量优化，**不要再说「synchronized 一定比 `ReentrantLock` 慢」**。

`synchronized` 的三种加锁形式：修饰**实例方法**（锁 `this`）、**静态方法**（锁 `Class` 对象）、**代码块**（锁括号里的对象）。**锁的对象不同 = 锁不同**，这是「两个线程各锁各的 `this`，同步失效」的根因。

## 五、CAS 与原子类：无锁并发的基石

CAS（Compare-And-Swap）是一条 CPU 原语：`if (当前值 == 期望值) { 写入新值; return true; } else return false;`。Java 通过 `sun.misc.Unsafe`（JDK 9+ 用 `VarHandle`）暴露它，`AtomicInteger.incrementAndGet()` 就是一个「读-算-CAS 失败重试」的自旋循环：

```java
public final int incrementAndGet() {
    while (true) {
        int cur = get();
        int next = cur + 1;
        if (compareAndSet(cur, next)) return next;   // 失败就重来
    }
}
```

**CAS 的三个问题**：
1. **ABA 问题**：值从 A→B→A，CAS 误判「没变过」。金融/链表场景会出事故。解法：`AtomicStampedReference`（值 + 版本戳）或 `AtomicMarkableReference`。
2. **自旋开销**：高竞争下大量 CAS 失败，CPU 空转。
3. **只能保证单个变量**：多变量要 `AtomicReference` 打包成对象，或改用锁。

**高竞争场景用 `LongAdder` 而不是 `AtomicLong`**：`LongAdder` 把累加分散到多个 `Cell` 上（分段累加），最后 `sum()` 汇总，写竞争大幅下降，代价是 `sum()` 不精确（弱一致）。

## 六、可运行代码

`examples/ex03-atomic-counter.json`：同一份自增任务分别用 `int` / `volatile int` / `AtomicInteger` / `LongAdder` 执行，用**布尔判据**证明前两者会丢更新。
`examples/ex04-cas-aba.json`：复现 ABA 误判，并展示 `AtomicStampedReference` 如何修复。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **别用 `volatile` 当锁用**：`volatile count++` 是最经典的面试送命题，等价的正确写法是 `AtomicInteger` 或把整个复合操作放进 `synchronized`。
- **优先选高层工具**：能用 `AtomicInteger` / `ConcurrentHashMap` / `CompletableFuture` 就别手写 `wait`/`notify`；能用不可变对象共享就别共享可变状态。**共享可变状态是并发的万恶之源**。
- 锁粒度：尽量锁**私有 final 对象**，别锁 `this`、别锁字符串常量、别锁 `Integer`（缓存对象可能被全局共享）。
- 只在**确有多线程可读**时才加 `volatile`；单线程可见的字段加 `volatile` 只会白白损失优化。

### 🎓 博士生视角
- JMM 是**语言级的内存模型**，用 happens-before 这套**偏序关系**而非硬件缓存术语来规定语义——目的是让同一份代码在 x86（强内存模型）与 ARM（弱内存模型）上行为一致。
- `volatile` 写插入 StoreLoad 屏障、读插入 LoadLoad 屏障，代价是**禁止重排序 + 清缓存行**，因此「锁粒度越小越好」在这里体现为「`volatile` 比锁轻但比普通变量重」。
- DCL 的 `volatile` 必要性，本质是 **`final` 字段的安全发布**问题：没有 `volatile`，引用赋值可能逃逸到构造完成之前，破坏「构造期内不发布 `this`」不变量。
- CAS 的 ABA 在链表/无锁栈中会导致**引用悬空**（已经释放又复用的节点被当成原节点），所以无锁算法普遍需要「版本戳 / 危险指针 / RCU」等附加机制。

### 📚 考研者视角
- 直接对应 **408 操作系统的「进程同步与互斥」**：临界区、忙等、信号量 P/V 操作、管程。Java 的 `synchronized` ≈ **管程（monitor）**，`wait/notify` ≈ **条件变量**。
- 常考「临界区四原则」：空闲让进、忙则等待、**有限等待**、**让权等待**——注意 `synchronized` 提供的是**阻塞等待**（满足让权等待），而 CAS 自旋属**忙等**（不满足让权等待，但有界自旋可近似满足有限等待）。
- 「原子性/可见性/有序性」是软考与后端面试的标准三件套，答题时务必**把三者与具体手段一一对应**：`synchronized` → 三者；`volatile` → 可见性 + 有序性；`Atomic*` → 特定操作的原子性。
- 记忆锚点：**`volatile` 可见不原子、`synchronized` 三合一、CAS 有 ABA**。
