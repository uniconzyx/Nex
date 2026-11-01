# py-ch02 · 函数与作用域：def、参数解包、lambda、闭包、命名空间 · 学习目标

完成本章后，你能：

1. 理解 Python 对象模型：一切皆对象、名字绑定（而非"盒子"）、引用语义与可变/不可变对象（CPython 引用计数、GIL 背景）。
2. 掌握 `def` 定义函数，区分位置/默认/`*args`/`**kwargs` 参数，并会用 `*seq` / `**dict` 解包传入调用。
3. 理解 LEGB 作用域链与命名空间（局部/闭包/全局/内建），会用 `global` / `nonlocal` 改写外层变量。
4. 掌握 lambda 表达式与"一等公民函数"：函数可赋值、传参、返回、存容器（字典分发、回调、高阶函数）。
5. 理解闭包：自由变量绑定、延迟绑定陷阱（循环 lambda）与修复，能写出有状态工厂函数。
6. 规避可变默认参数陷阱，掌握 `None` 哨兵惰性初始化惯用法。
7. 理解装饰器基于闭包的原理（含 `functools.wraps` 与叠放顺序），并能读懂/写出基础装饰器。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,745 | 全章 | Python 实现的全部经典算法，含详细注释；本章先读与「命名空间与作用域」「可运行代码」相关的部分 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,609 | 全章 | Python 100 天从新手到大师（中文系统教程）；本章先读与「命名空间与作用域」「可运行代码」相关的部分 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,917 | 全章 | 微软官方 12 周机器学习入门课程，含 26 课与测验；本章先读与「命名空间与作用域」「可运行代码」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | §2.1 函数是一等对象、被延迟创建 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（函数定义与参数）核对 |
| 2 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | §5.2 装饰器原理 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex02`（参数解包）核对 |
| 3 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex03`（lambda 与 map/filter/）核对 |
| 4 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex04`（LEGB 作用域链）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
