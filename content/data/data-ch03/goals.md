# data-ch03 · Pandas 基础：Series 与 DataFrame

> 学科：`data`（数据分析实操线）
> 前置：`data-ch01`（NumPy 基础）——**本章只依赖同一条线**，不依赖其他学科。
> 环境：`pandas 3.0.6` / `numpy 2.5.3`（本仓库的 `pyenv-cppmind` 虚拟环境）

## 一、为什么 Pandas 值得单独一章

NumPy 的抽象是**同质的稠密数组**：所有元素同一 `dtype`，靠整数位置索引。
真实数据几乎从来不是这个样子——它有**列名**、有**混类型**、有**缺失**、有**标签**。

Pandas 的两次抽象升级正好对应这些需求：

| 需求 | NumPy | Pandas |
|---|---|---|
| 列名 | 只能用位置 `a[:, 0]` | `df["price"]` |
| 混类型 | 被迫整体转成 `object`，失去向量化 | 每列独立 `dtype` |
| 缺失值 | `np.nan` 只能用于浮点，整数列无处安放 | `NaN` / `NaT` / `NA` + Nullable dtype |
| 标签索引 | 无 | `loc` 按标签、`iloc` 按位置 |
| 对齐 | 无（靠 shape 隐式） | **按索引自动对齐** |

**本章的核心线索**：理解 Pandas，其实就是理解它比 NumPy 多了两个东西——
**索引（index）** 与 **列（columns）**——以及由此派生的「自动对齐」语义。

## 二、学完之后你应该能做到

| 能力 | 验收方式 |
|---|---|
| 说清「自动对齐」的规则 | 能预测两个索引不同的 `Series` 相加后是什么 |
| 用对索引器 | 知道 `loc` 是**闭区间**、`iloc` 是**左闭右开**，不会混用 |
| 处理缺失值 | 能按场景选 `dropna` / `fillna` / `interpolate`，并说清各自的副作用 |
| 读懂 dtype 与内存 | 会用 `df.info(memory_usage="deep")` 定位内存大户并降位 |
| 分块读大文件 | 会用 `chunksize` 处理超过内存的 CSV |
| 避开链式赋值 | 明白 `SettingWithCopyWarning` 的成因与正确写法 |

## 三、本章结构

| 文件 | 内容 |
|---|---|
| `concept/01-series-dataframe-and-alignment.md` | Series/DataFrame 结构、索引语义、自动对齐（与 NumPy 最大的差异） |
| `concept/02-io-csv-excel-chunking.md` | 读写 CSV/Excel：编码、分隔符、`dtype` 指定、`chunksize` 分块 |
| `concept/03-iloc-loc-and-chained-assignment.md` | `iloc` / `loc` / 直接下标的行为差异、切片端点、链式赋值与 Copy-on-Write |
| `concept/04-missing-values-dtype-and-memory.md` | 缺失值三类标记与 Nullable dtype、填充策略、dtype 降位与 `category` |
| `pitfalls.md` | 12 个高频陷阱 |
| `examples/` | 12 个 venv 实测示例（对齐、索引器、缺失值、dtype 内存、分块…） |
| `exercises.json` | 6 题：基础 4 + 算法 2 |
| `interview.json` | 6 条面经 |
| `project.json` | 一个「脏 CSV 清洗与内存优化」项目 |

## 四、动手实践（建议顺序）

1. **制造一次自动对齐**：让两个索引顺序不同、且有部分不相交的 `Series` 相加，
   亲眼看到结果里出现了 `NaN`——这是 Pandas 最容易被忽略的行为。
2. **对比三种索引器**：对同一张 DataFrame 分别用 `df[0:2]`、`iloc[0:2]`、`loc[0:2]`，
   观察**行数与是否报错**的差异。
3. **做一次内存体检**：构造 100 万行数据，用 `memory_usage(deep=True)` 看各列占用，
   再把低基数列转成 `category`、把 `int64` 降到 `int8`，量化节省比例。
4. **跑一次分块聚合**：用 `chunksize` 读一个较大的 CSV，逐块累加统计量，
   与一次性读入的结果对比，确认一致。

## 五、自检清单

- [ ] 我能解释「Pandas 的自动对齐」并按索引对齐两个 Series
- [ ] 我知道 `loc[1:3]` 与 `iloc[1:3]` 各取几行
- [ ] 我能说出 `NaN`、`None`、`pd.NA` 的区别
- [ ] 我知道为什么整数列的 `NaN` 会把它变成 `float64`
- [ ] 我能用 `category` 与降位把 DataFrame 内存压下来
- [ ] 我明白 `SettingWithCopyWarning` 的两种正确修法
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67,957 | §4.2 2. 检测与处理缺失 | 读 `sklearn/impute/_base.py`：`SimpleImputer` 的 `strategy` 与 pandas 的 `fillna` 是两套语义（前者在管道内、后者在数据上），混用时要注意「训练/推理口径一致」；本章 §4.1「缺失值的三种标记」正是这条差异的根源：`np.nan` / `None` / `pd.NaT` 三者被判空的方式不同，`SimpleImputer` 只认 `np.nan` 与 `NaN` 语义 |
| 2 | [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50,277 | §3.2 2. `iloc` 与 `loc` 的完整能力 | 读 `notebooks/03.02-Data-Indexing-and-Selection.ipynb`：`loc` 闭区间、`iloc` 左闭右开——两种切片的边界规则不同，混用就是「取出来的行数不对」；本节 §3.3「链式赋值与 `SettingWithCopyWarning`」也在这里埋下伏笔：`df[df.a > 0]['b'] = 1` 取到的是副本，赋值等于没做 |
| 3 | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 50,278 | §1.1 1. 两个核心数据结构 | 读 `pandas/core/frame.py` 与 `pandas/core/internals/managers.py`：DataFrame 不是「行列表」，而是「按 dtype 分块的二维结构」，这解释了「混类型列会让操作变慢」；本章 §1.2「自动对齐：Pandas 的灵魂」在这个结构上才说得通——对齐发生在每个 Series/Block 的索引上，而不是整行 |
| 4 | [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37,860 | §2.3 3. 分块读：文件比内存大怎么办 | 读 `pandas/io/parsers/readers.py` 里 `read_csv` 的 `chunksize` 参数实现：它返回的是一个迭代器，每次只解析一块，而不是「先全读进来再切」；这正是本节「文件比内存大」的答案，也解释了本章 §2.1「`read_csv` 的关键参数」里 `dtype` 为什么必须显式给——分块读时若靠推断，每一块的 dtype 可能都不同 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 数据分析全套<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | §1.2 自动对齐 | 从 numpy/pandas 到清洗、可视化、案例的完整链路，配真实的电商与招聘数据集；看完回 `ex01`（自动对齐）核对 |
| 2 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | §1.2 自动对齐 | API 速查：广播、索引、合并、透视各一集，10 分钟能补齐一个操作；看完回 `ex02`（重复索引导致对齐后行数膨胀（笛卡尔积））核对 |
| 3 | Pandas 数据分析从入门到实战<br><sub>蚂蚁学Python</sub> | [BV1UJ411A7Fs](https://www.bilibili.com/video/BV1UJ411A7Fs/) | §1.2 自动对齐 | 偏实战：时间序列、缺失值、多表关联这几节比教科书细；看完回 `ex03`（Series 的三要素与 DataFra）核对 |
| 4 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | 全章 | 数据分析绕不开 SQL：查询、聚合、窗口函数与索引，看前 1/3 足够支撑取数；看完回 `ex04`（loc / iloc / 直接下标）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《利用 Python 进行数据分析（第 3 版）》McKinney |
| 2 | 《Python 数据科学手册》VanderPlas |
| 3 | 《统计学（第 8 版）》贾俊平 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
