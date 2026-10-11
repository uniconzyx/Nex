# 03 · queue 与线程池：生产/消费与 Future

## 3.1 `queue.Queue`：天生线程安全

`queue.Queue` 内部已经用锁 + 条件变量实现好了「入队阻塞 / 出队阻塞」，你不需要再加锁：

```python
import queue, threading
q = queue.Queue(maxsize=10)     # maxsize>0 时 put 会阻塞（背压）

def producer():
    for i in range(20):
        q.put(i)                 # 队列满则阻塞，天然反压
    q.put(None)                  # 哨兵：通知消费者收工

def consumer():
    total = 0
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        total += item
        q.task_done()            # 与 get 一一配对
    print("sum =", total)

t = threading.Thread(target=consumer); t.start()
producer(); t.join(); q.join()
```

**三条纪律**：

1. **`task_done()` 必须与 `get()` 一一配对**，否则 `q.join()` 永远不返回。
2. **收工信号用哨兵**（`None` 或自定义对象）；不要用 `q.empty()` 判断结束 —— 那一刻可能只是"暂时空"。
3. **`maxsize` 是背压阀门**：生产远快于消费时，设了 `maxsize` 会阻塞生产者，把内存增长挡在门外。

## 3.2 线程池：别再手写 `Thread`

手写 `Thread` 的三大问题：线程数无上限（可能开成千上万个）、创建开销重复付、异常无人收集。`ThreadPoolExecutor` 一次解决：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(url: str) -> int:
    return len(url)                      # 演示用，真实场景是网络请求

urls = ["a" * 10, "b" * 20, "c" * 30]
with ThreadPoolExecutor(max_workers=4) as ex:
    print(ex.map(fetch, urls))                    # 惰性迭代器
    print(list(ex.map(fetch, urls)))              # 保序！
    # submit 立刻返回 Future
    futs = [ex.submit(fetch, u) for u in urls]
    for f in as_completed(futs):                  # 按完成顺序
        print(f.result())
```

| API | 返回 | 顺序 | 异常 |
|---|---|---|---|
| `map` | 迭代器 | **保序**（按输入顺序） | 迭代到时才抛 |
| `submit` + `result()` | `Future` | 任意 | 调用 `result()` 时抛 |
| `submit` + `as_completed` | 迭代器 | **按完成** | 迭代到时抛 |

**线程数怎么定**：IO 密集从 `min(32, (os.cpu_count() or 1) * 5)` 量级起步（这是 CPython 默认值），再按实测调；CPU 密集用 `os.cpu_count()`。**不要设成"越多越好"**。

## 3.3 Future 与异常传播

`Future` 是"未来会有结果"的占位对象。**异常不会在 `submit` 时抛出，而是在 `result()` 时重新抛出**，且**同一个 Future 可重复取**：

```python
f = ex.submit(lambda: 1 / 0)
try:
    f.result()
except ZeroDivisionError as e:
    print("捕获:", type(e).__name__)
```

这也解释了最常见的静默失败：**只 `submit` 不 `result()`，异常就永久沉默**。

## 3.4 进程池：CPU 密集的出口

```python
from concurrent.futures import ProcessPoolExecutor

def heavy(n: int) -> int:
    return sum(i * i % 7 for i in range(n))

with ProcessPoolExecutor() as ex:
    print(list(ex.map(heavy, [100_000] * 4)))
```

**代价与纪律**：

- 参数与返回值必须 **pickle 可序列化**（lambda、局部函数、打开的文件对象都不行）。
- **子进程不共享内存**：全局变量改了不会同步回父进程。
- **必须在 `if __name__ == "__main__":` 下调用**（Windows 用 spawn 启动，否则无限递归创建进程）。

### 🧑‍💻 程序员视角

**线程池使用清单**：

1. 用 `with ThreadPoolExecutor(...)` 而不是裸 `Thread` —— 退出时自动 `join`。
2. 永远收集 `Future`：`list(ex.map(...))` 或遍历 `as_completed`。**裸 `submit` 不取结果 = 吞异常**。
3. 需要「按输入顺序」用 `map`；需要「谁先好谁先处理」用 `as_completed`。
4. 给任务加**超时**：`f.result(timeout=5)`。否则任务卡住会拖住整个池。
5. 别在池里做「任务再提交子任务并等待」——**会死锁**（池被父任务占满，子任务永远排不到）。要嵌套就用独立池或 `asyncio`。

**生产者-消费者的背压设计**：`maxsize` 设小（如 100）能让上游"感知到下游慢"，这比让内存涨到 OOM 更可控。这也是消息队列"限流"的微缩版。

### 🎓 博士生视角

**Amdahl 定律**给出线程池收益的上界。设任务中可并行比例 $p$、串行比例 $1-p$，用 $k$ 个 worker 的加速比：

$$S_k = \frac{1}{(1-p) + p/k}$$

当 $k \to \infty$ 时 $S_\infty = 1/(1-p)$。若一段代码有 20% 是必须串行的（单线程写日志、全局锁），则**无论开多少线程，加速比都不会超过 5**。这是"加线程无感"的理论解释，比"GIL 的锅"更普适 —— 即使换成多进程也逃不掉。

**排队论视角**（`maxsize` 的意义）：把队列看成一个 $M/M/1$ 或 $M/M/c$ 系统，到达率 $\lambda$ 与服务率 $\mu$。当 $\lambda \to \mu$ 时，平均队长 $\mathbb{E}[L] \to \infty$（发散），这就是"无界队列必定 OOM"的数学形态；而 $c$ 个服务台（worker）与有限缓冲 $K$（`maxsize`）把系统变成 $M/M/c/K$，**丢包/阻塞**替换了"无限排队"。**背压不是权宜之计，是稳定性定理的要求**。

**`Future` 的本质**是 Promise/Future 模式：一个可写一次的单元（single-assignment cell）加上唤醒机制。它的异常传播语义（在 `result()` 处重抛）之所以正确，是因为它保住了「异常沿调用链向上传播」这一结构化编程的基本性质 —— 只不过传播路径被显式地延后到取值时刻。

### 📚 考研者视角

高频问法与标准口径：

1. **「线程池线程数怎么定？」** 分场景：**IO 密集** $N_{\text{cpu}} \times (1 + \frac{T_{\text{wait}}}{T_{\text{cpu}}})$（等得越久开得越多）；**CPU 密集** 取 $N_{\text{cpu}}$ 或 $N_{\text{cpu}}+1$。标准答法要体现"按等待/计算比"这个思路，而不是背一个数字。
2. **「`map` 和 `as_completed` 的区别？」** `map` **保序**（结果顺序 = 输入顺序）；`as_completed` **按完成顺序**产出。前者适合"要整齐的结果表"，后者适合"谁先好先处理"。
3. **「为什么 `submit` 了但异常没报错？」** 异常直到 `result()` 才抛出；只提交不取值等于**静默吞掉**。要么 `map` + 迭代，要么 `as_completed` + `result()`。
4. **「`q.join()` 不返回是怎么回事？」** 有 `get()` 没配对的 `task_done()`。计数没归零，`join()` 就一直等。
5. **易错口径**：`Queue.empty()` **不可用于判断"生产者已结束"**（存在竞态，官方文档明确警告"不可靠"）；`ProcessPoolExecutor` 在 Windows/macOS 用 **spawn** 启动，必须有 `if __name__ == "__main__":` 保护。

## 三视角解析

### 🧑‍💻 程序员视角

**写代码时先问三句**：这段活儿是等 IO 还是烧 CPU？临界区到底有多大（几条指令 / 几微秒 / 几毫秒）？失效时我要的是"重试"还是"降级"？

- **IO 密集**（网络、磁盘、数据库）→ 线程池或协程，别单线程硬扛。
- **CPU 密集**（数值计算、序列化、加解密）→ 进程池（`ProcessPoolExecutor`），或把重活推给 C 扩展（numpy / 原生库释放 GIL）。
- **临界区极小**（一个计数器自增）→ 优先用 `itertools.count` / `queue.Queue` / 原子替代品，而不是给整段逻辑上大锁。

排查并发的固定顺序：**先确认有没有共享可变状态 → 再确认临界区边界 → 再看锁的获取顺序是否全局一致 → 最后才怀疑解释器**。90% 的"玄学 bug"死在前两步。

### 🎓 博士生视角

CPython 的 GIL 是**每个解释器进程一把**的互斥锁，它保护的是「字节码执行 + 引用计数增减」这一对不可分割的操作。它的第一性理由是 **CPython 的引用计数内存管理不是线程安全的**：`ob_refcnt` 的加减若不被串行化，一个刚分配就被引用的对象可能被另一个线程提前回收（use-after-free）。

形式化地看，GIL 让 CPython 的多线程在**纯 Python 字节码层**退化为"协作式时分复用"，切换点由 `sys.setswitchinterval()`（默认 5ms）与字节码边界共同决定。由此推出两个可证明的结论：

1. **CPU-bound 纯 Python 多线程加速比 ≈ 1**（甚至 < 1，因为多了上下文切换与锁争抢），这是"串行化不变量"的直接推论，不是实现缺陷。
2. **IO-bound 仍能加速**，因为阻塞系统调用前解释器会**主动释放 GIL**，此时其他线程可以真正并行。

协程的数学对象是**续体（continuation）**：`await` 把当前栈帧挂起并交还控制权，恢复成本是一次函数调用量级（无内核态切换、无栈复制到内核）。所以协程的并发度上限由**内存**而非线程数决定（每协程约几 KB 栈），而线程受 1~8 MB 栈与调度开销约束。

### 📚 考研者视角

笔试面试的高频问法与标准口径：

1. **「Python 多线程是假的吗？」** 不是假，是被 GIL 限制了并行度。标准答法：IO 密集有效、CPU 密集无效；CPU 密集用多进程。**切忌答"Python 不支持多线程"**。
2. **「GIL 什么时候释放？」** 三处：`sys.setswitchinterval()` 到期（默认 5ms）、执行到字节码边界、**以及进入阻塞 IO 时主动释放**。第三点最常被漏答。
3. **「`+=` 是原子操作吗？」** 不是。`x += 1` 编译为 `LOAD_FAST / LOAD_CONST / BINARY_OP / STORE_FAST` 四步。**但注意口径**：GIL 让这四步之间**通常**不被打断（3.10+ 的自适应解释器下更少被打断），所以"不原子"是**语义事实**，"实战中能观察到丢失"是**概率事件**——答题时要说清这层区别。
4. **「`Lock` 和 `RLock` 的区别？」** 同一线程重复获取：`Lock` 直接死锁，`RLock` 计数重入（必须等量释放）。
5. **「`asyncio` 和多线程怎么选？」** IO 密集且调用链全是异步库 → `asyncio`；有阻塞库/CPU 活 → 线程/进程池；两者混用要用 `loop.run_in_executor` 桥接。
6. **易错口径**：`asyncio.gather` **保序**返回、`as_completed` **按完成**产出；`TaskGroup` 在任一子任务异常时**取消其余任务**并抛 `ExceptionGroup`（3.11+）。
