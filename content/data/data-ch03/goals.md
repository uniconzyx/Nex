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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67487 | 经典机器学习库官方仓库：算法实现与最佳实践 |
| [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50114 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib） |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49928 | Pandas 官方仓库：API 与内部机制权威来源 |
| [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37525 | 微软官方 10 周数据科学课程 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |
