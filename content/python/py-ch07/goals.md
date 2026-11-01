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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,666 | 全章 | Python 实现的全部经典算法，含详细注释；本章先读与「1 GIL 是什么」「2 GIL 什么时候释放」相关的部分 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,492 | 全章 | Python 100 天从新手到大师（中文系统教程）；本章先读与「1 GIL 是什么」「2 GIL 什么时候释放」相关的部分 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,785 | 全章 | 微软官方 12 周机器学习入门课程，含 26 课与测验；本章先读与「1 GIL 是什么」「2 GIL 什么时候释放」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | §4.1 1 协程是「可暂停的函数」 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（线程的创建、join 与确定性顺序基线）核对 |
| 2 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex02`（GIL 与工作量守恒）核对 |
| 3 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex03`（用 Barrier 强制交错复现确定性的）核对 |
| 4 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | 全章 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex04`（加 Lock 后同样交错节奏下不再丢失）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
