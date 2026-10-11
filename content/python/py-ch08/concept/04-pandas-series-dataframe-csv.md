# 04 · pandas：Series、DataFrame 与 CSV

## 主题一：Series / DataFrame 与索引对齐

`Series` 是「带标签的一维数组」，`DataFrame` 是「共享同一行索引的 Series 字典」。核心差别在于：**pandas 的运算默认按标签对齐，而不是按位置**。

```python
import pandas as pd
s1 = pd.Series([1, 2], index=["x", "y"])
s2 = pd.Series([10], index=["y"])
print((s1 + s2).to_dict())   # {'x': nan, 'y': 12.0}
```

注意发生了两件事：① 结果的索引是**并集**（`x`、`y`）；② 只在一侧出现的标签补 `NaN`。如果不想要这个语义，得显式 `.values` 或 `.to_numpy()` 退化成按位置的 ndarray 运算：

```python
print(s1.to_numpy() + np.array([10, 20]))   # 按位置相加
```

DataFrame 的索引与列也是索引对象（`Index`），切片与选择有两套风格：

| 写法 | 依据 | 切片端点 |
|---|---|---|
| `df.loc[...]` | **标签**（label） | **闭区间**（含右端） |
| `df.iloc[...]` | **位置**（position） | **半开区间**（不含右端） |

```python
df = pd.DataFrame({"v": [10, 20, 30, 40]}, index=list("abcd"))
print(df.loc["b":"d"]["v"].tolist())    # [20, 30, 40] —— 含 d
print(df.iloc[1:3]["v"].tolist())       # [20, 30]     —— 不含索引 3
```

这是 NumPy 用户转 pandas 时最容易出错的一处：**`loc` 的切片端点是闭的，`iloc` 与 Python/NumPy 一样是半开的**。

### 🧑‍💻 程序员视角

**时刻警惕「对齐」带来的隐性 bug。** 两个索引不同的 Series 相加会做并集对齐，结果比预期更长、且带 NaN。业务代码里若不确定索引是否一致，先 `assert s1.index.equals(s2.index)` 再运算，比出事后回溯便宜得多。

**`SettingWithCopyWarning` 的真实含义。** 先切片再赋值（`df[df.a > 0]["b"] = 1`）改的可能是**中间副本**，原 `df` 不变。正确写法一律是**单次 `loc`**：`df.loc[df.a > 0, "b"] = 1`。在新版 pandas（Copy-on-Write 默认开启）下，这类链式赋值只会更明确地「不生效」，而不会侥幸生效。

**CSV 的 dtype 推断是不可靠的。** 带前导零的编号（`007`）会被读成整数 7；电话号码、身份证号要显式 `dtype=str`。金额列若被推断成 `float`，可能出现 `0.1 + 0.2` 的经典误差，宜用 `Decimal` 或整数分。

### 🎓 博士生视角

**BlockManager：DataFrame 的列按 dtype 分块存储。** 同 `dtype` 的列被放在同一块连续内存里，这是「按列取数快、按行取数慢」的结构性原因。跨 dtype 的按行访问要跨块拼装，代价显著。

**Index 是独立的「轴标签空间」。** 它支持重复（非唯一索引）、支持多级（MultiIndex），而 `loc` 在遇到重复标签时返回的是**多行**（一个子集）而不是单值。许多「`loc` 返回了 Series 而不是标量」的困惑都源于索引不唯一。

**Copy-on-Write 的语义。** pandas 3.x 起 CoW 默认开启：任何从 `df` 派生出的对象（切片、协变结果）在被修改时会**自动拷贝**，因此「改子集导致原表变化」被彻底禁止。这消除了 `SettingWithCopyWarning` 的模糊地带，但也意味着「先取子集再原地改」的写法必须改成显式 `df.loc[...] = ...`。

### 📚 考研者视角

**标准问法：「`loc` 与 `iloc` 的区别？」** 三句话答全：① `loc` 按标签、`iloc` 按位置；② `loc` 切片**含右端**、`iloc` **不含**；③ 布尔索引通常与 `loc` 搭配（`df.loc[mask, "col"]`）。

**易错口径：「两个 Series 相加会怎样？」** 按索引**并集**对齐，缺的位置补 `NaN`。这是 pandas「标签优先」的直接体现，与 NumPy 的按位置运算完全不同。

**易错口径：「`dropna()` 和 `fillna()` 改的是原表吗？」** 默认**不改**，返回新对象；要原地修改需 `inplace=True`（新版 pandas 已逐步弃用 `inplace`，推荐重新赋值 `df = df.dropna()`）。

## 主题二：读写 CSV 与分组聚合

`read_csv` 是整章最常用的入口，几个必须掌握的参数：

| 参数 | 作用 | 典型场景 |
|---|---|---|
| `dtype` | 强制列类型 | 编号/电话号码用 `str` |
| `usecols` | 只读需要的列 | 宽表提速 |
| `nrows` | 只读前 N 行 | 快速探查 |
| `chunksize` | 返回迭代器 | 大文件分块处理 |
| `parse_dates` | 解析为日期 | 时间序列 |
| `na_values` | 额外缺失标记 | 既有的 `N/A`、`-` 等 |

分块读取是处理超大 CSV 的标准手法——它把「一次性载入」换成「逐块处理并累加」：

```python
import pandas as pd
total = 0
for chunk in pd.read_csv("big.csv", chunksize=1000):
    total += int(chunk["amount"].sum())
```

分组聚合是 pandas 的看家本领，语义是 SQL 的 `GROUP BY`：

```python
df = pd.DataFrame({
    "city": ["BJ", "SH", "BJ", "SH"],
    "sales": [10, 20, 30, 40],
})
print(df.groupby("city")["sales"].sum().to_dict())     # {'BJ': 40, 'SH': 60}
print(df.groupby("city")["sales"].agg(["sum", "mean"]).to_dict())
print(df["sales"].describe().to_dict())                # count/mean/std/min/25%/50%/75%/max
```

两个默认口径必须记住：① `groupby` **默认丢弃**分组键为 `NaN` 的行（`dropna=True`），要保留得显式 `dropna=False`；② 聚合函数**默认跳过** NaN。

### 🧑‍💻 程序员视角

**`groupby` 先选列再聚合。** `df.groupby("city")["sales"].sum()` 只算需要的列；直接 `df.groupby("city").sum()` 会对所有数值列都算一遍，宽表上很浪费。不需要的列用 `usecols` 在读取时就砍掉更好。

**`value_counts` 是「面试最快的一行」。** 统计类别分布、排查脏数据（`df["city"].value_counts(dropna=False)`）都是它，比 `groupby(...).size()` 更短、且默认按频次降序。

**写 CSV 要显式控制编码与字段。** 中文场景写 `encoding="utf-8-sig"` 让 Excel 能正确识别 BOM；`index=False` 避免多写一列无名索引；含逗号的字段交给 `quoting=csv.QUOTE_MINIMAL` 自动加引号。

### 🎓 博士生视角

**`groupby` 是 split-apply-combine 三步。** 先按键分组（split），对每组应用函数（apply），再把结果拼回（combine）。理解这三步就能预判：聚合结果是「每组一行」（`transform` 则是「与原表等长」），`agg` 可以用字典对**不同列**指定**不同**函数。

**`describe` 的口径。** `count` 不计 NaN；`25%/50%/75%` 是**线性插值**分位数（非「取第 k 个」）；`std` 默认是**样本标准差**（分母 n-1，`ddof=1`），与 NumPy 的 `std` 默认总体标准差（`ddof=0`）**不同**——这是跨库对比数字时对不上的常见原因。

**`read_csv` 的解析是启发式的。** dtype 推断基于「前若干行采样」，所以同一列的推断可能因文件头部内容不同而变化。生产环境里对关键列显式给 `dtype`，本质上是把「猜测」换成「契约」。

### 📚 考研者视角

**标准问法：「怎么按某列分组求均值？」** 答 `df.groupby("col")["target"].mean()`；若要多统计量一起出，用 `.agg(["mean", "sum", "count"])`。

**易错口径：「pandas 的 `std` 和 numpy 的 `std` 一样吗？」** 不一样。pandas 默认样本标准差（`ddof=1`），numpy 默认总体标准差（`ddof=0`）。数值小的时候差异明显。

**易错口径：「`groupby` 会把 NaN 分组保留下来吗？」** 默认**不保留**（`dropna=True`），含 NaN 分组键的行被丢弃。要保留需显式 `dropna=False`。
