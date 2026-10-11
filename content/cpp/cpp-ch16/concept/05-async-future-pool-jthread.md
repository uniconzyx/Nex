# 05 · async / future / 线程池 与 jthread

## 一、理论根基：高层并发抽象

`std::async` 把「跑一个任务 + 取结果」封装成 `future`，比手动 `thread`+共享变量优雅；`promise`/`future` 是**一次性单向通道**，用来在线程间传递值或**异常**。

- **异常传递**：工作线程抛的异常不会就地炸主线程，而是被**捕获并存储**在 `future`，直到主线程 `get()` 时**重新抛出**——这是 async 比 raw thread 安全的关键。

## 二、实现机制：async 的启动策略

```cpp
std::future<int> f = std::async(std::launch::async, task);  // 真开新线程
// std::async(std::launch::deferred, task);                  // 惰性：get() 时才在调用线程同步执行
// std::async(task);                                         // 默认 = async|deferred，由实现决定！
```

- **默认策略的坑**：默认是 `async | deferred`，实现**可能选择 deferred**——此时 `get()` 在**调用线程同步执行**，**根本没有并行**！若代码依赖并行（如同时跑多个任务缩短时间），必须显式 `std::launch::async`。
- **`get()` 只能调一次**，且会**阻塞**直到结果就绪。

## 三、线程池：为什么必要

每次 `std::thread` 创建都有内核开销（栈分配、调度注册）；高并发短任务场景下，「来一个建一个线程」成本高且易耗尽资源。**线程池**预先建 N 个常驻线程，任务提交到队列，线程复用——控制并发度、降开销。

- **实现要点**：`mutex`+`condition_variable` 保护的任务队列；worker 循环 `wait` 取任务；优雅关闭靠 `stop` 标志 + `notify_all`。
- **`std::jthread`（C++20）**：在 `std::thread` 基础上：析构**自动 join**（不再 terminate）、并带**协作式取消（stop_token）**——worker 可定期检查 `stop_requested()` 主动退出。它是「忘了 join 就崩」这一历史坑的官方解法。

## 四、可运行示例（见 examples/ex06-async-future.md、ex07-jthread.md 对应 ex06/ex07）

```cpp
#include <iostream>
#include <future>

int main() {
    auto f = std::async(std::launch::async, []{ return 6 * 7; });
    std::cout << "answer=" << f.get() << '\n';   // 阻塞取结果，异常也会在此重抛
}
```

**输出**：`answer=42`

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`std::async` 的启动策略是坑**：`std::launch::async` 强制新线程、`deferred` 变成惰性求值（在 `get()` 时才执行，且**在当前线程**跑）——不指定则实现可自选，行为可能随实现变化。
- `future` 的 `get()` **只能调用一次**（第二次是 UB），且 `get()` 会阻塞等待；异常会通过 `future` **重新抛出**（这是它相对回调的优势）。
- **线程池优于裸 `thread`**：摊薄创建成本、限制并发数、复用栈；C++20 的 `std::jthread` 补上了「析构自动 join + 协作式停止（`stop_token`）」两块短板。

### 🎓 博士生视角
- `future/promise` 建立了一条**单向的数据通道 + 同步点**：`set_value` 与 `get` 之间构成 happens-before，异常被封装在**共享状态（shared state）**里跨线程传递。
- `async` 的「延迟执行」本质是**把任务变成惰性值**——这带来一个隐蔽问题：若不调用 `get()`，deferred 任务可能永不执行；而返回的 `future` 析构若持有 async 任务会**阻塞等待**（这是易被忽略的同步点）。
- `jthread` 的 `stop_token` 实现了**协作式取消**：线程自己轮询 token 决定是否退出（无强制终止），这是唯一安全的线程终止模型（强杀线程会留下不一致状态与泄漏锁）。

### 📚 考研者视角
- 408 并发考点：**线程池的设计动机**（减少创建销毁开销、控制并发度、复用资源）——这是「池化技术」的统一动机（与连接池、内存池同源）。
- 记忆锚点：**线程的强杀不安全，只能协作式退出**（对应 `stop_token`）。
- 常考辨析：**同步（阻塞等待）vs 异步（回调/`future`）**；`future` 是「异步结果的同步获取点」，本质是**生产者-消费者的一次性握手**。

---
