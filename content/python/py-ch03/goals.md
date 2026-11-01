# py-ch03 · 内置数据结构：list / tuple / dict / set 与推导式、深浅拷贝 · 学习目标

## 学习目标
完成本章后，你能：

1. 说出 `list` 在 CPython 中的真实结构（**动态指针数组 + 过度分配**），解释 `append` 为何摊销 O(1)、`insert(0, x)` 为何 O(n)，并能量化扩容代价。
2. 讲清 `dict` 的**开放寻址哈希表**实现：探测序列、负载因子与扩容时机、3.7+ 的紧凑化布局为何让遍历有序，以及"键必须可哈希"的底层含义。
3. 理解 `set` 基于同一套哈希机制、为何元素去重依赖 `__eq__` 与 `__hash__` 的一致性契约。
4. 区分 `tuple` 的**不可变**指的是"引用不可变"而非"内容不可变"，并规避「元组里装列表」的陷阱。
5. 熟练使用**列表/字典/集合推导式**与生成器表达式，知道何时用惰性（大数据流）何时用即时（需多次遍历）。
6. 精确区分**浅拷贝与深拷贝**：共享子对象、`copy.copy` / `copy.deepcopy` / 切片 `[:]` / `list()` 的语义差异，以及循环引用下 `deepcopy` 的备忘录机制。
7. 能根据访问模式（按下标 / 按 key / 去重 / 频繁增删两端）**选型容器**，并给出复杂度与内存占用的工程取舍。

## 前置
- py-ch01：变量与对象模型（名字绑定、可变/不可变）
- py-ch02：函数与作用域（闭包、装饰器，本章推导式会用到）

## 面试权重
- **高频**：dict 底层与哈希冲突、list.append 复杂度、浅/深拷贝、`==` 与 `is`、可变默认参数（见 ch02）。
- **中频**：tuple 不可变性、set 去重条件、生成器 vs 列表推导、`sort` 的 key 与稳定性。
- 属于「Python 岗必考 + 校招通用」的双重高频区。

## 真题依据（真实可查，仅存元数据）
- 《流畅的 Python（第2版）》第 2 章（序列）、第 3 章（字典与集合）。
- CPython 源码：`Objects/listobject.c`、`Objects/dictobject.c`。
- LeetCode 相关题见 `exercises.json`（只存元数据与链接，不复述题面）。

## 验收标准
- 能手写一个简化版哈希表并解释探测与扩容；
- 面对 `a = [[0]] * 3` 的共享陷阱能立即指出根因与修复；
- 能用 `sys.getsizeof` 说明 list 与 tuple 的内存差异。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,666 | 全章 | Python 实现的全部经典算法，含详细注释；本章先读与「list 不是链表，是「过…」「复杂度」相关的部分 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,492 | 全章 | Python 100 天从新手到大师（中文系统教程）；本章先读与「list 不是链表，是「过…」「复杂度」相关的部分 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,785 | 全章 | 微软官方 12 周机器学习入门课程，含 26 课与测验；本章先读与「list 不是链表，是「过…」「复杂度」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | §3.1 推导式 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（list 是动态数组）核对 |
| 2 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | §3.1 推导式 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex02`（列表推导式）核对 |
| 3 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | §1.1 list 不是链表，是「过… | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex03`（字典推导式）核对 |
| 4 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex04`（set 集合运算）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
