# py-ch01 · 语法与数据类型：变量/流程控制/字符串/列表/字典/元组/集合/推导式 · 学习目标

- 理解 Python 动态类型与"变量即名字绑定"的语义，区分可变与不可变对象
- 掌握条件分支（if/elif/else）与循环（for/while、range、break/continue）流程控制
- 熟练使用不可变字符串及其切片、格式化（f-string）等基础操作
- 掌握四种内建容器：列表 list、字典 dict、元组 tuple、集合 set 的增删查改
- 能用列表推导式（及集合/字典推导式）写出简洁、可读的批量生成代码
- 能编写可独立运行的小程序，理解 `if __name__ == "__main__"` 的入口约定
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,569 | 全章 | Python 实现的全部经典算法，含详细注释 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,492 | 全章 | Python 100 天从新手到大师（中文系统教程） |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,785 | 全章 | 微软官方 12 周机器学习入门课程，含 26 课与测验 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | 全章 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（变量与基本运算）核对 |
| 2 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | 全章 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex02`（条件分支）核对 |
| 3 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex03`（for 循环与 range）核对 |
| 4 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex04`（字符串操作）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
