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
