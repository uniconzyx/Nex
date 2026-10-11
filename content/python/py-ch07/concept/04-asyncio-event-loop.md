# 04 · asyncio：协程、事件循环与取消

## 4.1 协程是「可暂停的函数」

`async def` 定义的函数调用后**不会执行**，而是返回一个协程对象；必须交给事件循环（`await`、`asyncio.run`、`create_task`）才会跑。

```python
import asyncio

async def hello(tag: str, n: int) -> str:
    print("start", tag)
    await asyncio.sleep(0)      # 主动让出控制权（模拟 IO 等待）
    print("end", tag)
    return f"{tag}-{n}"

async def main():
    print(await asyncio.gather(hello("a", 1), hello("b", 2)))

asyncio.run(main())
```

`await` 的语义：**把当前帧挂起、交还事件循环**，等目标就绪后从挂起点继续。它不阻塞线程，只让出**这一个协程**。

## 4.2 `gather` / `TaskGroup` / `wait`

| API | 行为 | 异常 |
|---|---|---|
| `asyncio.gather(*aws)` | **保序**返回结果列表 | 默认首个异常立即向上抛（其余任务继续跑，需 `return_exceptions=True` 才收集） |
| `asyncio.TaskGroup()`（3.11+） | 需显式 `create_task` | 任一子任务异常 → **取消其余**并抛 `ExceptionGroup` |
| `asyncio.wait(...)` | 返回 `(done, pending)` | 不自动抛，需自己看 `task.exception()` |

**保序 vs 完成顺序的实验**（确定性，因为 `sleep(0)` 的让出顺序由创建顺序决定）：

```python
async def tag(i, d):
    await asyncio.sleep(d)
    return i

async def main():
    # 完成顺序：sleep 短的先完成
    order = []
    async def done(i, d):
        await asyncio.sleep(d)
        order.append(i)
    await asyncio.gather(done(1, 0.02), done(2, 0.01), done(3, 0.0))
    print("完成顺序:", order)                       # [3, 2, 1]
    print("保序结果:", await asyncio.gather(tag(1, 0.02), tag(2, 0.0)))   # [1, 2]
```

## 4.3 Task 与取消

`create_task` 把协程**立即**排进事件循环（这点与 `gather` 的"稍后"不同）：

```python
async def worker():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("被取消，做清理")
        raise                    # 惯例：清理后重新抛出
    finally:
        print("finally 一定执行")

async def main():
    t = asyncio.create_task(worker())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    print("cancelled() =", t.cancelled())
```

**取消的纪律**：`CancelledError`（3.8+ 继承自 `BaseException`）**必须重新抛出**，否则会被上层当成"正常完成"；清理写在 `finally` 或 `except ... : raise` 之前。

## 4.4 最大的坑：阻塞事件循环

事件循环是**单线程**的。任何同步阻塞调用都会卡死所有协程：

```python
import time, asyncio, concurrent.futures

async def bad():
    time.sleep(0.5)              # ❌ 整个循环停摆

async def good():
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, time.sleep, 0.5)   # ✅ 丢到线程池
```

**该换的**：`time.sleep` → `asyncio.sleep`；`requests` → `httpx` / `aiohttp`；阻塞文件读 → `run_in_executor` 或 `aiofiles`；CPU 重活 → `run_in_executor(ProcessPoolExecutor(), ...)`。

## 4.5 asyncio vs threading 选型

| 维度 | `threading` | `asyncio` |
|---|---|---|
| 并发单位成本 | 1~8 MB 栈 + 内核对象 | 几 KB，纯用户态 |
| 上限 | 数百~数千 | 数万~数十万 |
| 切换成本 | 内核态、微秒级 | 用户态、函数调用级 |
| 阻塞库可用性 | 任意库 | **必须**异步库或 `run_in_executor` |
| 抢占 | 抢占式（切换间隔） | **协作式**（只在 `await` 让出） |
| 调试 | 难（交错不可预知） | 较易（切换点显式） |

**一句话**：调用链全异步 → `asyncio`；有阻塞库 / CPU 活 → 线程池或进程池；两者混用 → `run_in_executor` 桥接。

### 🧑‍💻 程序员视角

**选型决策树**（贴墙版）：

1. 你用（或愿意换）的 IO 库有 async 版本吗？有 → `asyncio`（并发量大时优势最大）。
2. 依赖里有**不可替换的同步阻塞库**（老 SDK、`pymysql`）→ 线程池，或 `run_in_executor` 包起来。
3. 有 CPU 重活 → `run_in_executor(ProcessPoolExecutor(), ...)`，**别放在事件循环里**。
4. 并发量 < 几十 → 线程池足够，`asyncio` 的复杂度不划算。

**排查顺序**：`asyncio` 服务"变慢/超时"时，先搜代码里有没有 `time.sleep` / `requests` / 同步文件 IO / 大循环 —— **90% 的 asyncio 事故是阻塞调用**，而不是 `await` 写错。

**取消与清理**：给每个长任务挂 `finally` 释放资源；用 `TaskGroup` 让"一个失败全体收摊"，避免孤儿任务泄漏。

### 🎓 博士生视角

事件循环可视为一个**就绪队列 + 选择器（selector）**的调度器：循环体反复执行「取出就绪回调 → 运行到下一个 `await` → 注册新的等待事件」。设就绪任务集 $\mathcal{R}$，单次循环的工作量为 $\sum_{t \in \mathcal{R}} w(t)$，因此**任一任务的阻塞时长直接加到所有其他任务的延迟上**：

$$L_{\text{others}} \ge \text{block}(t)$$

这就是「阻塞事件循环」的形式化表述 —— 它不是"变慢"，而是**延迟的硬下界**。相反，使用 `run_in_executor` 把阻塞移出循环后，该下界被消除，代价是线程池的上下文切换。

协程的挂起/恢复在实现上是**状态机变换**：编译器把 `async def` 的函数体转换为一个可暂停的有限状态机（每个 `await` 是一个状态转移点），挂起时保存局部变量到帧对象，恢复时从对应状态继续。这解释了"协程切换为什么便宜"：**没有内核栈，只有一次 Python 帧的保存与恢复**。

**结构化并发（structured concurrency）**的语义价值：`TaskGroup` 保证子任务的作用域不逃逸 —— 退出 `async with` 块时，**所有**子任务必定已经终结（完成 / 取消 / 异常）。这消除了"孤儿任务"这一整类泄漏，与「作用域资源管理（RAII / `with`）」是同一种设计哲学：**生命周期由语法结构而非程序员记性保证**。

### 📚 考研者视角

高频问法与标准口径：

1. **「`await` 做了什么？」** 挂起当前协程、把控制权交还事件循环，等目标就绪后从挂起点继续。**关键补充**：它不阻塞线程，只让出这一个协程；且只有 `await`（或结束）处才可能切换，这是"协作式"的含义。
2. **「`gather` 和 `TaskGroup` 的区别？」** `gather` **保序**返回列表、默认首个异常上抛但**其余任务继续跑**；`TaskGroup` 在任一子任务异常时**取消其余**并抛 `ExceptionGroup`（结构化并发）。
3. **「协程里还要用锁吗？」** 通常不需要 —— 同一事件循环内单线程执行，只要**不在临界区里 `await`**，就不存在交错。若确实跨 `await` 保护状态，用 `asyncio.Lock`（不是 `threading.Lock`）。
4. **「为什么 `time.sleep` 会拖慢整个 `asyncio` 服务？」** 事件循环单线程，阻塞调用让所有协程停摆，延迟下界 = 阻塞时长。修法：换 `asyncio.sleep` / 异步库，或用 `run_in_executor` 移出循环。
5. **易错口径**：`asyncio.gather` **不是**"一等一切"；`create_task` 立刻入队而 `gather` 的协程在 `await` 时才被驱动；`CancelledError` 在 3.8+ 继承 `BaseException`，**`except Exception` 抓不到**，这是"取消后资源没释放"的常见成因。

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
