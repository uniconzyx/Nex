# 04 · 条件变量与虚假唤醒

## 一、理论根基：为什么需要条件变量

mutex 只能「互斥」，不能「等待某条件成立」。条件变量（condition_variable）让线程**阻塞等待**直到被通知「条件可能变了」，配合 mutex 实现「生产者-消费者」「信号量」等同步。

- **第一性原理**：条件变量解决「**等一个谓词变真**」的问题；它不携带数据，只负责**阻塞/唤醒**。

## 二、实现机制：wait 的三件事

```cpp
std::unique_lock<std::mutex> lk(m);
cv.wait(lk, []{ return ready; });   // 等价：while(!ready){ cv.wait(lk); }
```

`wait(lk, pred)` 原子地做：**释放锁 → 阻塞 → 被唤醒后重新加锁 → 检查 pred**。

- **虚假唤醒（spurious wakeup）**：即使无人 `notify`，线程也可能被唤醒（系统/实现层面）。若 `wait` 只用 `cv.wait(lk)` 不加谓词，醒来后**未验证条件就继续**，会读到一个还没准备好的状态 → bug。
- **正确写法**：**永远用带谓词的 `wait`**（或 `while(!pred) wait;`）。谓词把「虚假唤醒」和「被 notify 但条件仍不成立」都挡在门外。

## 三、工程实践

- 通知用 `notify_one`（唤醒一个）或 `notify_all`（唤醒全部，如状态翻转影响所有等待者）。
- 修改谓词与 `notify` 必须在**同一把锁**保护下（先改谓词再解锁再 notify，或持有锁 notify，均可，但谓词修改必须受锁保护）。
- 不要在持有锁时长时间工作；临界区越小越好。

## 四、可运行示例（见 examples/ex04-condvar-pc.md 对应 ex04）

```cpp
// 生产者-消费者：生产者放入 5 个，消费者取 5 个，最终汇总总数（确定性）
#include <iostream>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <thread>

std::mutex m; std::condition_variable cv; std::queue<int> q; bool done = false;
int consumed = 0;

void consumer() {
    while (true) {
        std::unique_lock<std::mutex> lk(m);
        cv.wait(lk, []{ return !q.empty() || done; });   // 谓词防虚假唤醒
        while (!q.empty()) { q.pop(); ++consumed; }
        if (done && q.empty()) break;
    }
}
```

**输出（确定性汇总）**：`consumed=5`（见完整示例 ex04）

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`wait` 必须配谓词**：写成 `cv.wait(lock, []{ return !q.empty(); });`，它内部处理了「虚假唤醒」与「通知丢失」；裸 `wait(lock)` 必须自己在 `while` 里循环。
- `notify_one/all` 可以在**不持锁**时调用（性能更好），但要注意「先改状态、后通知」的顺序不可颠倒。
- 忘记通知、或通知时未修改谓词条件，会导致线程永久阻塞——这是生产事故的常见根因。

### 🎓 博士生视角
- 虚假唤醒（spurious wakeup）是**允许的**（源于 OS 实现与性能考虑），因此「用 `while` 而非 `if` 检查条件」是硬性要求，不是防御性编程的教条。
- `wait` 的语义是**原子地「释放锁 + 挂起」**，唤醒后重新获取锁——这个原子性由 condvar 与 mutex 协同实现（futex 的 `FUTEX_WAIT` + 用户态竞争处理）。
- 「谓词 + `notify_all`」的组合保证了**状态变更与通知的顺序安全性**：持锁改状态使通知不会在状态变更之前被观察到（避免丢失唤醒）。

### 📚 考研者视角
- 408 同步考点：**生产者-消费者问题**是条件变量的经典映射（缓冲区满/空两个条件），也是信号量 P/V 的经典例题。
- 记忆锚点：**条件变量必须与互斥锁配合、且必须用 `while`/谓词检查条件**（防虚假唤醒）。
- 常考辨析：**条件变量（等待某条件成立）vs 信号量（计数资源）**——前者是「事件通知」、后者是「资源计数」。

---
