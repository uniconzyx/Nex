# py-ch08 · 数据分析：numpy/pandas 入门 · 学习目标

## 学习目标

学完本章，你应当能够：

1. **说清 `ndarray` 与 Python `list` 的本质差异**：为什么前者能做「一次调用算完整张表」，而后者的运算必须自己写循环。
2. **掌握形状操作**（`reshape` / `ravel` / `transpose` / `reshape(-1)`），并能用 `strides` 解释「为什么转置不复制数据」。
3. **判断一次索引返回的是视图还是副本**：基本切片是视图，花式索引与布尔索引是副本；会用 `np.shares_memory` 实证。
4. **掌握广播（broadcasting）规则**：能预判两个形状能否广播、广播后的结果形状是什么，并识别「内存被静默放大」的写法。
5. **掌握 `axis` 语义**（`axis=0` 沿行方向压、`axis=1` 沿列方向压），会用 `keepdims`、`np.newaxis` 显式补齐维度。
6. **会用 pandas 的 `Series` / `DataFrame`**：构造、`loc` vs `iloc`（含切片端点差异）、布尔筛选与 `query`。
7. **会读写 CSV**，理解 `dtype` 推断、缺失值表示（`NaN` / `pd.NA`）与 `read_csv` 的分块读取。
8. **会做分组聚合与基础统计**（`groupby` / `agg` / `describe` / `value_counts`），并知道「聚合时 NaN 被跳过」这一默认口径。
9. **能识别两类真实事故**：链式赋值（`SettingWithCopyWarning`）与索引对齐（`+` 自动并集而非按位置相加）。

## 前置

- `py-ch01`（基本语法）—— 需要列表、字典、推导式的基础。
- `py-ch05`（文件 IO 与编码）—— 读写 CSV 时编码与换行处理会直接复用。

本章**不依赖任何第三方服务的网络访问**，所有示例都在本地用 `numpy 2.5.3` + `pandas 3.0.6` 真实运行。

## 面试权重

| 主题 | 出现频率 | 常见问法 |
|---|---|---|
| 视图 vs 副本 | **极高** | 「`arr[1:3]` 改一下原数组会变吗？」 |
| 广播规则 | 高 | 「`(3,1)` 与 `(4,)` 能相加吗？结果形状？」 |
| `axis` 语义 | 高 | 「`axis=0` 和 `axis=1` 分别在做什么？」 |
| `loc` vs `iloc` | 高 | 「两者切片端点有什么区别？」 |
| pandas 对齐 | 中 | 「两个索引不同的 Series 相加会发生什么？」 |
| NaN 传播 | 中 | 「`sum()` 遇到 NaN 会怎样？想跳过得怎么写？」 |

## 真题依据（真实可查，仅存元数据）

- LeetCode 题库中与数组运算、矩阵相关的题（仅提供题号与链接，不搬运题面正文）。
- 《利用 Python 进行数据分析》Wes McKinney 第 4 章（NumPy 基础）、第 5 章（pandas 入门）。
- NumPy 官方文档：Quickstart、Broadcasting、Indexing on ndarrays。
- pandas 官方文档：10 minutes to pandas、Indexing and selecting data。

## 验收标准

- [ ] 能用 `np.shares_memory` 逐条实证「哪些切片是视图、哪些是副本」。
- [ ] 能对一组形状预判广播结果，并与 `numpy` 实际结果比对无误。
- [ ] 能用一行 `axis` 参数完成「按行均值」「按列均值」，并解释差在哪。
- [ ] 能写出一个 `loc` 与 `iloc` 结果不同的切片，并说明原因。
- [ ] 能完成 `examples/` 中 12 个示例的复现，且输出与 `expected_output` 一致。
- [ ] 能独立完成 `project.json` 中的销售数据分析项目。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,745 | §1.1 | 讲「纯 Python 与向量化的差距」时读 `sorts/` 的实现：纯 Python 循环排序在十万级数据上比 `numpy.sort` 慢两个数量级，这是「为什么数值计算要用 ndarray」的最直观对照 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,609 | §3.1 | 讲「pandas 的索引与切片」时看 `Day41-55/` 的数据分析篇：`loc` 按标签、`iloc` 按位置，混用是「取出来的数据不对」的头号原因 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,917 | §2.2 | 讲「特征矩阵的形状」时看入门课的回归案例：`X` 是 `(样本数, 特征数)`、`y` 是 `(样本数,)`，形状对不上是 `fit` 报错的第一排查点 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | 全章 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（ndarray 创建、dtype 推导与）核对 |
| 2 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex02`（形状变换与 strides）核对 |
| 3 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex03`（基本切片是视图、花式索引与布尔索引是副本）核对 |
| 4 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | 全章 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex04`（布尔索引、where 与 select ）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
