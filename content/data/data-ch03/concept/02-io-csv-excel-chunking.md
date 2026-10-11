# 读写 CSV / Excel 与分块处理

> 本章要点：IO 是数据流水线里**最容易出错也最容易被忽视**的一环。
> 编码、分隔符、`dtype`、分块——四件事决定后面所有分析是否可信。

## 1. `read_csv` 的关键参数

### 1.1 最小可用的读入

```python
import pandas as pd
df = pd.read_csv("data.csv")
```

**默认假设**：UTF-8 编码、逗号分隔、第一行是表头、`NA`/`NaN`/空串视为缺失。

这些假设在真实数据里**经常不成立**，于是需要逐项覆盖：

### 1.2 参数速查（按重要度排序）

| 参数 | 何时必须显式指定 |
|---|---|
| `encoding` | 中文 CSV 常是 `gbk` / `gb18030`；Excel 导出的 CSV 常带 **BOM** → 用 `utf-8-sig` |
| `sep` | TSV 用 `"\t"`；欧洲数据有时用 `";"`；正则分隔用 `sep=r"\s+"` + `engine="python"` |
| `dtype` | **强烈建议**：显式指定每一列的类型，避免「ID 被读成整数丢前导零」 |
| `usecols` | 只读需要的列，**大幅降低内存**（大宽表尤其明显） |
| `nrows` | 调试时先读前 N 行看结构 |
| `chunksize` | 文件大于内存时**必须**用（见第 3 节） |
| `parse_dates` | 指定列解析为日期时间；否则会读成字符串 |
| `na_values` | 补充自定义的缺失标记（如 `"N/A"`、`"-"`、`"NULL"`、`"9999"`） |
| `skiprows` / `skipfooter` | 文件前面有说明行 / 后面有汇总行 |

### 1.3 编码：三个最常见的坑

**坑 1：中文乱码。** 报错通常是
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc4 ...`。
解决顺序：先试 `utf-8`，再试 `gb18030`（`gbk` 的超集，覆盖面更广）。

**坑 2：BOM。** 若用 Excel「另存为 CSV UTF-8」，文件头会多出 3 个字节 `EF BB BF`。
此时读进来的**第一列名会变成 `"\ufeffid"`**，于是 `df["id"]` 报 `KeyError`。
修复：用 `encoding="utf-8-sig"`（`sig` 表示吃掉 BOM）。

**坑 3：推断失败。** `pd.read_csv` 默认只**采样前若干行**推断 dtype。
如果第 10 万行出现一个非数字值，读入时不会报错，但那一列会被推断成 `object`，
后续数值运算直接失败或退化为逐元素运算。

**工程做法**：解析阶段永远**显式传 `dtype`**，把「类型」从推断变成契约。

### 1.4 写出：`to_csv` 的注意点

```python
df.to_csv("out.csv", index=False, encoding="utf-8-sig", na_rep="")
```

- **`index=False`**：否则会多写一列无名索引，再读回来时又多一列；
- **`encoding="utf-8-sig"`**：让 **Excel 能正确打开中文**（Excel 对无 BOM 的 UTF-8 支持不好）；
- **`na_rep`**：控制缺失值写出的形式（默认是空串）。

## 2. Excel 的读与写

```python
df = pd.read_excel("book.xlsx", sheet_name="Sheet1", dtype={"id": str})
with pd.ExcelWriter("out.xlsx", engine="openpyxl") as w:
    df.to_excel(w, sheet_name="cleaned", index=False)
    summary.to_excel(w, sheet_name="summary", index=False)
```

**实际约束**：

- 读 Excel 需要 `openpyxl`（`.xlsx`）或 `xlrd`（旧的 `.xls`）；
- **写多表必须用 `ExcelWriter`**，连续两次 `to_excel(path)` 会**互相覆盖**；
- Excel 的**行数上限是 1,048,576**、列数 16,384——超了要换格式（CSV/Parquet）；
- Excel 里「看起来是数字」的单元格可能被读成浮点（`123` → `123.0`），
  尤其是 ID 类字段，务必 `dtype=str`。

**性能提醒**：Excel 的读写**比 CSV 慢一个数量级**（要解析 XML）。
流水线的中间产物应优先用 **Parquet**（列式、带类型、压缩率高）。

## 3. 分块读：文件比内存大怎么办

`chunksize` 让 `read_csv` 返回一个**迭代器**，每次产出一个不超过 N 行的 DataFrame：

```python
total = 0
for chunk in pd.read_csv("huge.csv", chunksize=100_000, usecols=["amount"]):
    total += chunk["amount"].sum()
print(total)
```

**这就是「流式聚合」**：内存里任何时刻只有一个 chunk。

### 3.1 三种分块模式

| 需求 | 做法 |
|---|---|
| **可累加的聚合**（求和、计数、最大值） | 逐块计算再合并（上例） |
| **需要全局信息的操作**（去重、排序、分组） | 第一遍收集「键集合」或「分组累加器」，第二遍再处理 |
| **需要写出的转换** | 逐块处理后 `to_csv(..., mode="a", header=(first))` 追加写 |

### 3.2 分块聚合的正确姿势

不要这样（会重复读文件、且慢）：

```python
# ❌ 错误：每块单独算平均，再平均 —— 分块大小不等时会算错！
avg = sum(c["v"].mean() for c in pd.read_csv("f.csv", chunksize=1000)) / n_chunks
```

**原因**：平均数的平均 ≠ 整体的平均（除非每块行数相同）。
正确做法是**累加分子与分母**：

```python
s = cnt = 0
for c in pd.read_csv("f.csv", chunksize=100_000):
    s += c["v"].sum()
    cnt += c["v"].count()
print(s / cnt)          # 这才是正确的整体均值
```

**这类错误的本质**：`mean` 不是**可结合的**（associative），
而 `sum` 与 `count` 是可结合的。分块计算只允许使用**可结合**的统计量。

### 3.3 分块 + 分组：用累加器代替 `groupby`

`groupby` 的结果不能跨块直接相加（每块的分组集合不同），
但**分组后的和与计数可以**：

```python
from collections import defaultdict
gsum, gcnt = defaultdict(float), defaultdict(int)
for c in pd.read_csv("f.csv", chunksize=100_000, usecols=["city", "amount"]):
    for city, grp in c.groupby("city")["amount"]:
        gsum[city] += grp.sum()
        gcnt[city] += grp.count()
```

## 4. 三视角：IO 与分块

### 🧑‍💻 程序员视角
**「读进来不对」的四类症状与对策**：

| 症状 | 根因 | 对策 |
|---|---|---|
| `UnicodeDecodeError` | 编码不对 | 试 `gb18030` |
| 列名带 `\ufeff` 前缀 | UTF-8 BOM | `encoding="utf-8-sig"` |
| 列数是 1（全挤在一列） | 分隔符不对 | 显式 `sep=";"` 或 `sep="\t"` |
| ID 变成 `1.0`（丢了前导零） | 被推断成数值 | `dtype={"id": str}` |
| 数字列变成 `object` | 列里混了 `"-"` 之类的脏值 | `na_values=["-", "N/A"]` |

**排查顺序建议**：

```python
# 1. 先看原始字节，确认编码与分隔符
#    head -c 200 data.csv | xxd | head      （命令行）
# 2. 读前 5 行看结构
df = pd.read_csv("data.csv", nrows=5)
print(df.dtypes, df.shape)
# 3. 再全量读，仍然显式给 dtype
```

**分块的性能参数怎么定**：`chunksize` 太小 → 迭代开销占比高；太大 → 内存峰值高。
经验起点是**让单块占几十 MB 内存**，用 `df.memory_usage(deep=True).sum()` 量一下再调。

### 🎓 博士生视角
分块计算的理论约束是**「统计量必须是可结合的 commutative monoid」**。

形式化地看，一个聚合若要支持分块，需要存在一个**累积状态** $S$ 与两个运算：

$$S_0 = \text{单位元}, \qquad S_{k+1} = \mathrm{combine}(S_k, f(\text{chunk}_k)), \qquad \text{result} = \mathrm{finalize}(S)$$

- `sum` / `count` / `min` / `max`：$S$ 就是标量，`combine` 是 `+` / `min` / `max`，天然可结合；
- `mean`：$S = (\text{sum}, \text{count})$ 是**二元组**，`combine` 分量相加，
  `finalize` 再做除法——**这就是「均值不可直接平均、但 (sum,count) 可」的代数解释**；
- `median` / `std` / `quantile`：$S$ 需要保留**整个数据集**（或近似结构如 t-digest），
  所以严格来说**不可结合**，只能近似或两遍扫描；
- `count(distinct)`：$S$ 是**集合**，可结合但内存随基数增长，
  于是有了 **HyperLogLog** 这类近似算法（用 $O(\log\log n)$ 空间估计基数）。

**这就是「流式算法（streaming algorithm）」这一子领域要解决的问题**：
在**单遍、亚线性空间**的约束下完成聚合。
Pandas 的 `chunksize` 只是把它暴露给了使用者；Flink / Spark Streaming 把它做成了基础设施。

### 📚 考研者视角
数据分析方向无统考考点。面试口径按「三句话」准备：

1. **编码**：中文 CSV 常见 `gb18030`；Excel 导出的 UTF-8 CSV 带 BOM，要用 `utf-8-sig`；
2. **`chunksize`**：文件大于内存时用，返回迭代器，逐块处理；
3. **分块陷阱**：**平均值不能分块后再平均**，必须累加 `(sum, count)`。

补充一个常被追问的点：*「为什么 ID 读进来变成浮点了？」* →
因为该列存在缺失值，`int64` 不支持 `NaN`，Pandas 只能升级为 `float64`
（或用 Nullable 的 `Int64`）。
