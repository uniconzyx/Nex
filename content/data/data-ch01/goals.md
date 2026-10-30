# data-ch01 · NumPy 基础：ndarray 与向量化

> 先修：py-ch01（Python 语法基础）。衔接：data-ch02（Pandas）、data-ch03（爬虫与数据清洗）。
> 面试权重：★★★☆☆（数据分析岗必考，后端岗常考向量化思维与内存意识）

## 本章目标

学完你应该能：

1. **解释为什么 ndarray 比 list 快 10~100 倍**，而且能说清这是三个独立因素的叠加：
   同构连续内存、消除类型分派（无需逐元素查 PyObject 类型）、SIMD 向量化指令。
2. **在「视图」与「拷贝」之间做正确选择**：能用 `base` 与 `np.shares_memory` 判定，
   知道哪些操作是 view（切片、reshape、transpose）、哪些一定拷贝（花式索引、astype、ravel 非连续时）。
3. **不查文档写出广播规则**：三条规则 + 从尾维对齐，能手工推导任意两个 shape 是否可广播。
4. **用 strides 解释 transpose 为什么几乎免费**，以及为什么「转置后再 ravel」会偷偷拷贝。
5. **把显式循环改写成向量化表达**：识别 reduce / map / mask 三类模式，并用 `np.where` 取代 Python 层 if。

## 性能目标（要有数量级直觉）

| 操作 | 相对耗时（N = 10^6） |
|---|---|
| Python for 循环 | ~100 ms |
| list comprehension | ~50 ms |
| `np.sum(a)`（向量化） | **~1 ms** |
| 说明 | 差距来自解释器开销 + 内存局部性 + SIMD |
## 软前置（可选，不阻断学习）

- Python 语法基础（py-ch01）：本线**独立自足**，若你已会用 Python 写循环/函数/列表，可直接从本章开始；若不熟悉，建议先花 1~2 小时过一遍 Python 基础语法，本章不依赖其进阶内容。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67,957 | 全章 | 经典机器学习库官方仓库：算法实现与最佳实践；本章先读与「先看一个反直觉的事实」「list 的内存模型」相关的部分 |
| 2 | [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50,229 | 全章 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib）；本章先读与「先看一个反直觉的事实」「list 的内存模型」相关的部分 |
| 3 | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49,928 | 全章 | Pandas 官方仓库：API 与内部机制权威来源；本章先读与「先看一个反直觉的事实」「list 的内存模型」相关的部分 |
| 4 | [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37,525 | 全章 | 微软官方 10 周数据科学课程；本章先读与「先看一个反直觉的事实」「list 的内存模型」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 数据分析全套<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | §1.4 strides | 从 numpy/pandas 到清洗、可视化、案例的完整链路，配真实的电商与招聘数据集；看完回 `ex01`（list 与 ndarray 的内存占用）核对 |
| 2 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | §1.4 strides | API 速查：广播、索引、合并、透视各一集，10 分钟能补齐一个操作；看完回 `ex02`（dtype、itemsize 与 ast）核对 |
| 3 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | §3.5 聚合的 axis 语义 | 数据分析绕不开 SQL：查询、聚合、窗口函数与索引，看前 1/3 足够支撑取数；看完回 `ex03`（形状变换与 strides）核对 |
| 4 | Pandas 数据分析从入门到实战<br><sub>蚂蚁学Python</sub> | [BV1UJ411A7Fs](https://www.bilibili.com/video/BV1UJ411A7Fs/) | 全章 | 偏实战：时间序列、缺失值、多表关联这几节比教科书细；看完回 `ex04`（视图 vs 拷贝的判定与污染实验）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《利用 Python 进行数据分析（第 3 版）》McKinney |
| 2 | 《Python 数据科学手册》VanderPlas |
| 3 | 《统计学（第 8 版）》贾俊平 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
