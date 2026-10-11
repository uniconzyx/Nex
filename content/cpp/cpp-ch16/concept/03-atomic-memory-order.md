# 03 · atomic 与内存序：无锁编程的边界

## 一、理论根基：原子操作解决什么

`std::atomic<T>` 保证对它的操作是**不可分割**的（读-改-写一步完成，不被其他线程插入），从而**无数据竞争**。它比 mutex 轻：通常是单条 CPU 指令（`lock xadd` 等），且不会阻塞线程。

- **第一性原理**：原子性只保证「该变量自身」的单个操作不被撕裂；但**多个原子变量之间、原子与周围代码的可见性顺序**，取决于**内存序（memory order）**。

## 二、实现机制：三种内存序

1. **`memory_order_relaxed`**：只保证原子性，**不保证顺序/可见性**——只适合「纯计数器」，不能用来同步其他内存。
2. **`memory_order_acquire` / `release`**：建立**同步关系（synchronizes-with）**——release 之前的写，对 acquire 之后可见。这是无锁队列/自旋锁的基石。
3. **`memory_order_seq_cst`**（默认）：在所有线程间建立**单一全序**，最强、最易推理，但代价最高（可能插入内存屏障/刷 store buffer）。

> 一句话：relaxed 管「自己不被撕裂」，acq/rel 管「配套数据的安全传递」，seq_cst 管「所有事按一个全局顺序」。绝大多数业务用默认 seq_cst 即可；追求极致性能才下沉到 relaxed/acq-rel，且必须严格论证。

## 三、无锁编程的边界

- **不是所有场景都能无锁**：原子只保护单个变量；「检查再行动」（如 `if (empty) push`）需要 CAS 循环（`compare_exchange`），且仍可能 ABA 问题。
- **无锁 ≠ 无等待**：lock-free 只保证「系统整体前进」，某线程可能饿死。
- 误用 relaxed 导致「计数对了但关联数据没同步」是高频隐蔽 bug。

## 四、可运行示例（见 examples/ex05-atomic-fetch-add.md 对应 ex05）

```cpp
#include <iostream>
#include <atomic>
#include <thread>
#include <vector>

std::atomic<int> cnt{0};

int main() {
    std::vector<std::thread> ts;
    for (int i = 0; i < 4; ++i)
        ts.emplace_back([]{ for (int k = 0; k < 2500; ++k) cnt.fetch_add(1, std::memory_order_relaxed); });
    for (auto& t : ts) t.join();
    std::cout << "cnt=" << cnt << '\n';   // 确定性：4*2500=10000
}
```

**输出**：`cnt=10000`（确定性，因为原子保证总数不丢）

---

## 三视角解析

### 🧑‍💻 程序员视角
- **默认用 `memory_order_seq_cst`**（最直观、最安全）；只有确认性能瓶颈且理解语义后才降级到 `acquire/release` / `relaxed`。
- `relaxed` 只保证**原子性**，不保证顺序：经典用途是**计数器**（`fetch_add` 累加统计），不用于「用标志位传递数据」。
- **别用 `volatile` 做同步**：它只禁止编译器优化读写，不提供原子性与内存屏障，多线程下完全错误（这是高频面试陷阱）。

### 🎓 博士生视角
- C++ 内存模型定义了 **happens-before** 关系：`release` 写与 `acquire` 读配对建立同步，使前者之前的所有写在后者之后可见——这是「无锁编程正确性」的判据。
- `seq_cst` 要求**全局单一总序**（在所有线程看来操作顺序一致），实现上需要 full fence（x86 上 `mfence` 或 `lock` 前缀），因此最贵；`acquire/release` 在 x86 上几乎零额外指令（TSO 已保证），在 ARM 上才需要显式屏障。
- 无锁数据结构正确性极难证明（ABA 问题、内存回收），因此工程上「无锁」通常意味着**「用原子做轻量同步」**而非「完全不用锁」。

### 📚 考研者视角
- 记忆锚点：**`volatile` 不保证原子性、不是同步原语**（这是 408 与面试共同的高频点）。
- 常考辨析：**原子性 vs 可见性 vs 有序性**——`atomic` 三者都管（按 memory_order）、`mutex` 三者都管、`volatile` 一个都不管。
- 与 OS 对照：**临界区/同步机制的本质是「保证互斥 + 建立内存可见性」**，硬件层面靠缓存一致性协议（MESI）与内存屏障实现。

---
