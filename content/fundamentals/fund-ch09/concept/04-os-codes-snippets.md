# 进程与调度代码速查：凯喵的七段可运行片段

> 这一篇是配套速查。前三篇讲清了进程线程的模型、六种调度算法的演算、以及同步与死锁的判定，这一篇把它们落成可运行的代码——包括能把调度算法真正「算出来」的模拟器。凯喵的用法是先在纸上手算一遍，再跑代码对答案。

## 一、进程状态机的模拟

进程在就绪、运行、阻塞三种状态间迁移，调度器只在「就绪」集合里挑。

```python
from collections import deque

class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.blocked = []
        self.running = None

    def admit(self, p):
        self.ready.append(p)

    def pick(self):
        if not self.ready:
            return None
        self.running = self.ready.popleft()
        return self.running

    def block(self, p):
        self.running = None
        self.blocked.append(p)

    def wake(self, p):
        self.blocked.remove(p)
        self.ready.append(p)      # 唤醒回到就绪，不是直接运行
```

最后一行是最容易错的地方：被唤醒的进程进入**就绪队列**，需要重新参与调度，而不是立刻抢占 CPU。

## 二、FCFS / SJF / SRTF 的统一模拟框架

三种非抢占/抢占算法可以用同一个框架表达，区别只在「选择函数」。

```python
def simulate(procs, choose, preemptive=False):
    """procs: [(name, arrive, burst)]；choose: 从就绪集里挑一个"""
    t, done, ready, running = 0, [], [], None
    rem = {n: b for n, a, b in procs}
    arrive = sorted(procs, key=lambda x: x[1])

    while len(done) < len(procs):
        while arrive and arrive[0][1] <= t:
            n, a, b = arrive.pop(0)
            ready.append(n)
        if preemptive or running is None:
            if running is not None:
                ready.append(running)
            running = choose(ready, rem) if ready else None
            if running: ready.remove(running)
        if running is None:
            t += 1
            continue
        rem[running] -= 1
        if rem[running] == 0:
            done.append((running, t + 1))
            running = None
        t += 1
    return done
```

把 `choose` 换成 `min(ready, key=lambda n: rem[n])` 就是 SJF/SRTF，换成「先到先服务」就是 FCFS。

## 三、RR 时间片轮转

```python
def simulate_rr(procs, q):
    from collections import deque
    rem = {n: b for n, a, b in procs}
    ready = deque()
    arrive = sorted(procs, key=lambda x: x[1])
    t, done = 0, []

    while len(done) < len(procs):
        while arrive and arrive[0][1] <= t:
            n, a, b = arrive.pop(0)
            ready.append(n)
        if not ready:
            t += 1
            continue
        n = ready.popleft()
        run = min(q, rem[n])
        t += run
        rem[n] -= run
        while arrive and arrive[0][1] <= t:     # 运行期间到达的也要入队
            x = arrive.pop(0); ready.append(x[0])
        if rem[n] == 0:
            done.append((n, t))
        else:
            ready.append(n)                      # 用完时间片回队尾
    return done
```

第二个 `while arrive` 是经典遗漏点：进程运行期间到达的新进程必须先入队，再决定当前进程是否回队尾。

## 四、银行家算法的安全性检查

```python
def is_safe(avail, alloc, need):
    n, m = len(alloc), len(avail)
    work = avail[:]
    finish = [False] * n
    seq = []
    while len(seq) < n:
        progressed = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += alloc[i][j]
                finish[i] = True
                seq.append(i)
                progressed = True
                break
        if not progressed:
            return False, []
    return True, seq
```

`work[j] += alloc[i][j]` 这一句是核心：进程完成后归还它占有的全部资源。漏了这句，安全序列永远找不到。

## 五、信号量实现生产者消费者

```python
import threading

empty = threading.Semaphore(5)     # 空位数
full = threading.Semaphore(0)      # 已有产品数
mutex = threading.Lock()
buf = []

def producer(item):
    empty.acquire()                # 先等空位
    with mutex:
        buf.append(item)
    full.release()                 # 再通知有产品

def consumer():
    full.acquire()
    with mutex:
        item = buf.pop(0)
    empty.release()
    return item
```

两个细节：`empty.acquire()` 必须在 `mutex` 之外（否则会持锁等待，死锁）；`P` 操作的顺序不能交换（先 `full` 后 `mutex` 在消费者里也一样）。

## 六、死锁四条件的检测

```python
def has_cycle(graph):
    """graph: {pid: [等待的pid]}，检测等待图中是否有环"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}

    def dfs(u):
        color[u] = GRAY
        for v in graph.get(u, []):
            if color.get(v, WHITE) == GRAY:
                return True
            if color.get(v, WHITE) == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    return any(color[u] == WHITE and dfs(u) for u in graph)
```

有向图判环必须用三色标记，不能用 bool visited——bool 无法区分「当前递归栈上的祖先」与「已完成的兄弟分支」，会把 DAG 误判成有环。

## 七、上下文切换的代价测量

```python
import time

def measure_switch(n=10000):
    import threading
    cv = threading.Condition()
    turn = [0]

    def worker():
        for _ in range(n):
            with cv:
                while turn[0] % 2 == 0:
                    cv.wait()
                turn[0] += 1
                cv.notify()

    t = threading.Thread(target=worker); t.start()
    t0 = time.perf_counter()
    for _ in range(n):
        with cv:
            turn[0] += 1
            cv.notify()
            while turn[0] % 2 == 1:
                cv.wait()
    t.join()
    return (time.perf_counter() - t0) / n * 1e6   # 微秒/次
```

测出来的数字通常是几微秒到几十微秒，量级上远大于一条指令。这就是「线程数不是越多越好」的物理依据。

## 三视角解析
### 🧑‍💻 程序员视角
凯喵第一次用 `fork()` 写并发服务器，结果子进程把父进程的监听 socket 也继承了，`kill` 父进程后端口仍被占用——`fork` 复制的是整个文件描述符表，父子共享同一个打开文件，必须显式 `close` 不需要的那一端。调度部分踩的坑是「优先级反转」：低优先级线程持有锁，高优先级线程等锁，中优先级线程抢走 CPU，导致高优先级被无限期拖延，解法是优先级继承。排查手段上，`top -H` 看线程级 CPU、`/proc/<pid>/status` 看上下文切换次数、`strace -c` 看系统调用分布，这三个比盲猜快得多。

### 🎓 博士生视角
进程与线程的本质区别在于「资源隔离的粒度」：进程有独立地址空间，线程共享地址空间但各自有栈与寄存器上下文。上下文切换的代价不只是保存寄存器，还包括 TLB 失效（换页表）与缓存污染，这也是「协程比线程轻」的真实原因。调度算法的评价可用「周转时间 = 完成 - 到达」「带权周转时间 = 周转 / 服务时间」两式，SJF 在非抢占下可证明最优（交换论证：把短作业提前不会让任何作业的完成时间变晚），但需要预知服务时间，因此实际系统用「多级反馈队列」用历史行为预测未来。

### 📚 考研者视角
408 进程管理考「算 + 判」：
1. **调度算法计算**：给到达时间与服务时间，画甘特图算平均周转时间、平均带权周转时间。FCFS、SJF、SRTN（抢占式最短剩余）、优先级、时间片轮转，五种都要会。
2. **PV 操作**：生产者-消费者、读者-写者、哲学家进餐的信号量设计。写代码时 `P`（wait）与 `V`（signal）的顺序决定会不会死锁，这是判分点。
3. **死锁**：四个必要条件、银行家算法的安全序列求解（找「需求 ≤ 可用」的进程，假设它完成并归还资源，循环直到全部完成或找不到）。
4. **进程状态转换**：就绪→运行→阻塞→就绪的箭头方向，注意「阻塞不能直接到运行」。

## 收尾

这七段代码的共同价值是「让抽象变具体」。调度算法的加速比、银行家算法的安全序列、死锁的等待图，这些东西在纸上算容易被符号绕晕，跑一遍代码就清楚了。凯喵的建议是：考试前用这些模拟器验证自己的手算结果，错一次就回去看那一步的规则——比反复读教材有效得多，因为计算的每一步都被迫显式化，任何理解偏差都会立刻暴露成「算出来不一样」。
