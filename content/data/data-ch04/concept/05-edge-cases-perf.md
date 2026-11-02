# data-ch04 · 边界情形与性能陷阱

> 承接 `01-groupby`、`02-merge`、`03-时间序列`、`04-透视与性能`。本节把前三节最容易在真实数据上翻车的边界情形，和 `apply` 慢在哪、怎么绕开，一并收口。

## 1. 本节定位

前面的例子都是「干净数据」。真实数据有缺失、有重复键、有超长序列——这些才是分组/合并/重采样真正出错的地方。

### 2. groupby 后的索引重建

`groupby` 默认把分组键变成结果索引（`as_index=True`），直接 `merge` 回原表会找不到列。显式 `reset_index()` 或传 `as_index=False`：

```python
# 错误：分组键进了索引，merge 时 on="k" 找不到
g = df.groupby("k")["v"].sum()
df.merge(g, on="k")          # KeyError

# 正确：把键拉回列
g = df.groupby("k", as_index=False)["v"].sum()
df.merge(g, on="k")
```

### 3. 命名聚合 namedAgg 一次算多种统计

需要同时对同一列算不同聚合、或重命名输出列时，用 `namedAgg` 避免事后改列名：

```python
df.groupby("k").agg(
    mean_v=("v", "mean"),
    max_v=("v", "max"),
    n=("v", "size"),
)
```

### 4. merge 的 indicator 与 validate 实战

`indicator=True` 会在结果里加 `_merge` 列（`left_only`/`right_only`/`both`），一眼看出哪些键没对上；`validate=` 在合并前就声明基数，行数不符直接抛错，而不是默默膨胀：

```python
merged = left.merge(right, on="id", how="left", indicator=True, validate="one_to_many")
merged["_merge"].value_counts()   # 检查 right_only 是否异常多
```

### 5. categorical 类型对内存与速度的影响

低基数字符串列（如省份、状态）转 `category` 后，分组和内存都显著改善——分组键比较从字符串变成整数码。但注意：`category` 的类别集合是固定的，出现未见过的类别会成 `NaN`，合并前要确保两边类别一致。

### 6. 多列 groupby 与 dropna 的交互

多键分组时任一键为 `NaN` 的行会被整行丢弃（默认 `dropna=True`）。缺失也要参与统计时，先 `fillna` 成哨兵值或 `groupby(..., dropna=False)`。

### 7. rolling 的 min_periods 与 center

`rolling(n)` 默认窗口左对齐、前 `n-1` 个位置因样本不足返回 `NaN`；`min_periods=k` 允许窗口内至少有 `k` 个非 NaN 才出值；`center=True` 让窗口以当前点为中心（平滑指标常用）。错用会让曲线首尾出现非预期缺口。

### 8. apply 逐行陷阱与向量化替代

`groupby.apply` 在分组内逐行 Python 循环，数据量大时极慢。能用 `agg`/`transform`/向量化表达的就不要 `apply`；必须逐行时，考虑先在组内算好中间量再向量化，或下推到 `numpy` 层。判断标准：**能不能用一列运算替代 for 循环**，能就别用 `apply`。

### 9. 大数据下的分块与类型优化

超过内存的数据用 `pd.read_csv(chunksize=...)` 分块处理，每块 `groupby` 后再合并中间结果；把整数列显式指定 `dtype`、日期列 `parse_dates`，能避免反复类型推断带来的额外开销与内存膨胀。
