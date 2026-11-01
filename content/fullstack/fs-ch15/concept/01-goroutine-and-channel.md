# Goroutine 与 Channel：轻量并发与「不要通过共享内存通信」

Go 的并发哲学可以浓缩成一句话：**「不要通过共享内存来通信；要通过通信来共享内存。」**
这句话是理解 Go 后端一切并发代码的总纲。它和 Java 的「synchronized / Lock / 线程池」路线
在底层目标上一样（安全地让多件事同时发生），但在「推荐手段」上截然相反。

## 一、模型本体：goroutine 与 channel

### Goroutine 有多轻

```text
   G(goroutine) ─▶ P(逻辑处理器, 数量≈CPU) ─▶ M(系统线程) ─▶ 核
        │                │
        └──── channel 通信 ──── 代替「共享内存 + 锁」
   「不要通过共享内存来通信，而要通过通信来共享内存」
```


操作系统线程（如 Java 的 `Thread`）默认栈就有 1MB 左右，开几万个就内存爆炸；Goroutine 初始
栈只有 **2KB**，按需增长，同一进程里轻松开几十万、上百万个。代价是 Go 自己在用户态做了一层
调度——这就是 **GMP 模型**：G（goroutine）被放进 P（processor，逻辑处理器）的本地队列，由 M
（machine，操作系统线程）真正执行；当某个 G 阻塞在系统调用上时，M 可以和 P 解绑，让别的 M 顶上，
于是「少量 OS 线程」就能驱动「海量 goroutine」，且阻塞不会拖垮整个进程。这和 Java 的「一个任务
占用一个线程、阻塞就空转一个线程」形成鲜明对比。

### Channel 作为同步原语

在 Java 里，多个线程协作通常靠「共享一个变量 + 锁保护」。Go 的推荐做法是：**不要共享那个变量，
而是开一个 channel，让 goroutine 之间只通过 channel 传数据**。channel 本身承担了「同步」与
「传递所有权」两件事：一个无缓冲 channel 上的 `send` 会一直阻塞，直到有 `receive` 接住——这一
次握手天然完成了「我生产好了、你拿走」的同步，不需要任何锁。

无缓冲 channel 是「会合（rendezvous）」语义：发送者和接收者必须同时就位，数据直接从一方交给
另一方，不经过任何中间缓冲。缓冲 channel（`make(chan T, N)`）则允许发送者在缓冲未满时直接返回，
像一个小仓库，能容忍短暂的生产/消费速率差。选无缓冲还是缓冲，本质是「要不要容忍速率差、要不要
用缓冲来削峰」。

## 二、与其他运行时对照

### 与 Java 线程 / 线程池 / CompletableFuture 对照

- **Java `Thread` / 线程池**：任务是「被线程执行的对象」，共享内存靠锁；goroutine 是「语言一等
  公民」，启动成本低到可以「来一个请求开一个」。
- **Java `CompletableFuture`**：用回调/组合表达异步流程；Go 用 `go func()` + channel 表达，
  更接近「顺序写的同步代码」却获得并发效果，可读性往往更好。
- **Java `BlockingQueue`**：最接近 Go channel 的东西，但它是「显式的共享队列 + 锁」实现，而
  channel 把「同步」内建进语言，且能 `select` 多路复用。

### 一个反例：用共享内存计数

如果 N 个 goroutine 都去 `count++` 一个共享变量，在 Go 里这依然是数据竞争（data race），
`-race` 检测器会报警。正确的做法是让它们各自把「+1」这个事件发到 channel，由一个专门的
goroutine 来汇总——数据永远只在「那一个汇总者」手里，根本不需要锁。这正是「通过通信共享内存」
的落地：我们不是在共享 `count`，而是在传递「+1 这个意图」。

### 在 Node 里体会这个模型

下面用一段 JS 模拟「N 个 goroutine 各自通过 channel 汇报完成、单一收集者汇总」：channel 保证
完成信号被安全传递而非共享计数器，最终汇总数恒等于 N，且全程无锁。

## 工程落地时的几个决策点

### 决策点一：每个 go 都要能回答「何时结束」

goroutine 的「轻」是有代价的：它太便宜了，便宜到你会忘记它也需要被管理。最常见的事故是 goroutine 泄漏——一个 goroutine 因为「永远等不到的 channel / 永远不会关闭的 ticker / 忘了 cancel 的 context」而永远挂起，数量随时间累积，最终拖垮调度或撑爆内存。所以经验法则是：每个你 `go` 出去的函数，都要能回答「它什么时候结束」。最可靠的手段是传一个 `context.Context`，在退出路径上用 `ctx.Done()` 通知它停；对于纯 channel 场景，则约定「由唯一发送方关闭 channel」，并让接收方用 `v, ok := <-ch` 感知关闭。

### 决策点二：channel 还是 mutex

第二个决策点是「共享状态到底用 channel 还是 mutex」。本章强调「用 channel 通信」，但这不意味着 mutex 是错的。经验判据是：如果数据天然属于「单一所有者按顺序处理」（比如一个计数器、一个状态机），channel 更清晰；如果数据需要被多方高频读写、且访问模式不规则，强行用 channel 反而会把逻辑切碎、更难懂，这时 `sync.Mutex` 或 `atomic` 反而更直接。Go 社区的说法是「不要通过共享内存来通信」是箴言不是教条——它反对的是「无保护的共享」，而不是「所有共享」。

### 决策点三：无缓冲还是有缓冲

第三个决策点是「无缓冲还是有缓冲 channel」。无缓冲提供最强的同步保证（发送即会合），代价是发送方和接收方必须同时在场，任何一方慢都会直接拖住对方——这在「要求严格顺序、不容忍积压」时正好，但在「生产者可能突发」时是性能杀手。有缓冲 channel 则像一个小仓库，能吸收速率差、提升吞吐，代价是「缓冲里的数据可能在崩溃时丢失、且背压信号被软化」。选型标准很简单：要强同步用无缓冲，要削峰用缓冲，且缓冲容量要显式地想清楚。

### 关闭 channel 的责任必须唯一

还有一个 Go 特有的坑：向「已关闭的 channel」发送或重复关闭，会直接 panic。多生产者场景下，「谁负责关闭」必须用约定或 `sync.WaitGroup` 收敛成唯一关闭者，否则极易在并发关闭时炸。这个 panic 如果没被 `recover` 兜住，会直接带走整个进程。对照 Java，你不会因「往一个关闭的队列里放东西」而让 JVM 崩溃——这是 Go 在「简单」和「安全」之间偏向简单的一个典型体现，也意味着写 Go 并发时，关闭 channel 的责任要像「谁释放资源」一样被严肃对待。

### 与虚拟线程（Loom）对照

最后，把 goroutine 和 Java 虚拟线程（Project Loom）对照着看会更有收获：两者都走「M:N 用户态调度」的路线，都能开海量轻量并发。区别在编程模型——Go 用 channel 做同步原语、Java 用 `synchronized`/`Lock`/`BlockingQueue` 并逐步引入结构化并发。理解这条脉络，你就不会把「Go 的轻」当成魔法，而会把它看作「把并发成本从 OS 挪到了 runtime，再用 channel 当作配套约束」的一整套设计。

### 排查工具：-race 与 pprof

在排查并发 bug 时，`go run -race` 是 Go 给开发者最好的礼物之一：它能静态注入并在运行时检出数据竞争，很多「偶现、难复现」的 bug 在它面前无所遁形。与之配套的还有 `pprof`——当 goroutine 数异常增长（泄漏）或服务变慢时，抓一份 goroutine profile，几乎总能直接看到「卡在哪个 channel 接收、哪个锁上」。把这两个工具接进日常开发与 CI，比任何代码规范都更能保证并发质量。另一个实务建议：给关键 goroutine 起名或在 context 里带 trace id，出事时日志里才能分辨「是哪个任务的哪个 goroutine」。这些是 Go 并发从「能写」到「可靠」的最后一公里。

### channel 的成本与 fan-out/fan-in

值得一提的是，channel 并非没有成本：每次发送/接收都涉及调度协调，高吞吐场景下「一个 channel 串行传递所有数据」可能成为瓶颈。此时常见优化是「fan-out/fan-in」——多个 worker 从一个 channel 取、往多个 channel 发，或用 sync.Pool 复用临时对象。换句话说，channel 是写对并发的默认起点，但当它成为瓶颈时，该下沉到更底层的同步原语就下沉，不要为了「纯粹」而牺牲性能。

```js
// 见 EXAMPLES[fs-ch15]：goroutine 并发 + channel 汇总、unbuffered rendezvous 等
```

## 三视角解析

### 🧑‍💻 程序员视角
- 开 goroutine 便宜到可以这样写：`go handle(req)` 每个请求一个，不用先想线程池——但要记得 goroutine 也会泄漏，别忘了退出条件。
- 需要协作就开 channel，不要先想 `mutex`；无缓冲做会合、缓冲做削峰，选哪个看要不要容忍速率差。
- 多个 goroutine 改同一个变量一定是竞态，交给一个汇总 goroutine 通过 channel 收，比上锁简单也更不容易错。
- 对照 Java：把 goroutine 当「超轻 Thread」、channel 当「内建同步的 BlockingQueue」、select 当「多队列多路等待」。

### 🎓 博士生视角
- GMP 是「多对多（M:N）调度」的用户态实现：M 个 OS 线程调度 G 个 goroutine，P 是「可运行 G 的本地队列 + 资源」的中间层，目的是让调度尽量不发生 syscall 切换、且某个 G 阻塞系统调用时不拖垮整个 M。
- 「通过通信共享内存」是 CSP（Communicating Sequential Processes，Hoare 1978）模型的工程化：用消息传递取代共享状态，从数学上规避了锁带来的「竞态/死锁/优先级反转」整类问题。
- 无缓冲 channel 的 rendezvous 语义，等价于两个进程在「发送」与「接收」两个事件上的一次同步屏障（barrier）；缓冲 channel 则把这个屏障软化成容量有限的异步队列。

### 📚 考研者视角
- 与 408「进程/线程」对照：goroutine 是「用户态线程（green thread / 协程）」，由 runtime 而非 OS 调度；Java 虚拟线程（Loom）走的是类似路线，可一并比较。
- 常考辨析：Go channel 与 Java BlockingQueue 的区别——前者是语言内建的同步原语且可 select 多路，后者是库级别的共享队列。
- 记忆锚点：**goroutine 2KB 栈 + GMP 调度；channel 是会合/缓冲的同步原语；用通信代替共享内存**。
