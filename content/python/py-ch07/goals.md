# py-ch07 · 并发：threading / asyncio · 学习目标

## 学习目标

学完本章，你应当能够：

1. **说清 GIL 到底是什么、什么时候释放**，并能在一句话内判断"这段代码该用线程、协程还是进程"。
2. **识别竞态条件（race condition）**，区分"语义上不原子"与"实战中能观测到丢失"这两层事实，会用 `Lock` / `RLock` / `queue` 消除临界区。
3. **熟悉 `threading` 的同步原语**：`Lock` / `RLock` / `Semaphore` / `Event` / `Condition` / `Barrier`，并知道各自的适用场景。
4. **掌握 `queue.Queue` 的生产者-消费者模式**，理解它在多线程下为何是安全的、`task_done` / `join` 的配对规则是什么。
5. **会用 `concurrent.futures`**：`ThreadPoolExecutor` / `ProcessPoolExecutor`、`map` 与 `submit`+`as_completed` 的顺序差异、`Future` 的异常传播与超时。
6. **理解协程与事件循环**：`async def` / `await` 的语义、`asyncio.gather` 的保序性、`Task` 的取消与清理、`TaskGroup` 的异常聚合。
7. **能诊断"事件循环被阻塞"**，知道哪些标准库调用是阻塞的、该怎么用 `run_in_executor` 桥接。
8. **写出死锁的最小复现**，并解释如何用「统一加锁顺序」或 `acquire(timeout)` 预防/兜底。

## 前置

- `py-ch02`（函数与作用域）—— 需要理解闭包与 `nonlocal`，因为线程间共享状态常在闭包里传递。
- 基本的 `try / finally` 语法：锁必须放在 `finally` 释放。

## 面试权重

| 主题 | 出现频率 | 常见问法 |
|---|---|---|
| GIL 与线程边界 | **极高** | "Python 多线程有用吗？为什么？" |
| 竞态与锁 | 高 | "`+=` 是原子操作吗？该怎么改？" |
| 线程池参数与选择 | 高 | "线程池开多少个线程合适？" |
| asyncio 与事件循环 | 高 | "`await` 到底做了什么？" |
| 死锁与预防 | 中 | "怎么避免死锁？" |
| 协程 vs 线程 | 中 | "什么时候用协程而不是线程？" |

## 真题依据（真实可查，仅存元数据）

- LeetCode 题库中的**多线程同步**题（如「按序打印」「交替打印 FooBar」「打印零与奇偶数」），仅提供题号与链接，不搬运题面。
- 《流畅的 Python》第 18 章「使用 asyncio 包处理并发」、第 19 章「使用 futures 处理并发」。
- 《Python 并发编程实战》第 1~3 章（GIL、线程、锁）。
- CPython 官方文档 `threading` / `asyncio` / `concurrent.futures` 模块页。

## 验收标准

- [ ] 能画出「IO 密集 / CPU 密集」二维决策表，并各举一个正确的选型。
- [ ] 能用 `Barrier` 构造一个**确定性**的 lost update 复现，并用 `Lock` 修好。
- [ ] 能解释 `gather`（保序）与 `as_completed`（按完成）的行为差异。
- [ ] 能对一段"事件循环被 `time.sleep` 阻塞"的代码说出修法，并用 `run_in_executor` 验证。
- [ ] 能完成 `examples/` 中 12 个示例的复现，且输出与 `expected_output` 一致。
- [ ] 能独立完成 `project.json` 中的并发抓取调度项目。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225266 | Python 实现的全部经典算法，含详细注释 |
| [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187118 | Python 100 天从新手到大师（中文系统教程） |
| [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91310 | 微软官方 12 周机器学习入门课程，含 26 课与测验 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 600 集零基础 | [视频](https://www.bilibili.com/video/BV1ex411x7Em/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 千锋教育 · Python 700 集零基础 | [视频](https://www.bilibili.com/video/BV1R7411F7JV/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 鱼C工作室（小甲鱼）· 零基础入门学习 Python | [视频](https://www.bilibili.com/video/av52080698/) | 本学科配套视频，建议结合本章示例与习题观看 |
