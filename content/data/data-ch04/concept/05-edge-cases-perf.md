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

## 三视角解析
### 🧑‍💻 程序员视角
凯喵做订单聚合，`groupby` 之后 `merge` 总是多出几行，最后发现是分组键里有 `NaN`——`groupby` 默认丢弃 `NaN` 组，而 `merge` 会把 `NaN` 当普通值匹配，两边口径不一致就炸了，必须显式 `dropna=False`。`merge` 的 `validate` 参数是被低估的工具：`validate='one_to_one'` 会在键重复时直接抛错，比事后对数快一百倍。`categorical` 类型能把百万级字符串列的内存砍掉 90%，但代价是「不能直接加新类别」，`loc` 赋值一个未声明的类别会静默变成 `NaN`。

### 🎓 博士生视角
`groupby` 的实现是「哈希分组 + 聚合」，其复杂度为 O(n)，但常数受键的基数与哈希冲突影响；`categorical` 本质是字典编码（dictionary encoding），把字符串映射为整数码，聚合时比较整数而非字符串，这是列式存储（Parquet/Arrow）普遍采用的技术。`rolling` 的 `min_periods` 决定窗口未满时是否输出，`center` 决定窗口是否居中——这两个参数在时间序列对齐时直接决定结果的语义，误用会导致「未来信息泄漏」或「前期全 NaN」。

### 📚 考研者视角
数据分析面试常见：
1. **merge 的四种连接**：inner/left/right/outer 的结果行数如何变化；`indicator=True` 查未匹配行。
2. **groupby 的 agg 写法**：`agg({'col': ['mean', 'max']})` 与 `named_agg` 的区别，后者能命名输出列。
3. **缺失值处理**：`dropna` 的 `how`/`thresh` 参数、`fillna` 的前向/后向填充。
4. **内存优化**：`astype('category')`、降精度（`float64 → float32`）、分块读取 `chunksize`。
答题时给出「数据量级 + 具体做法 + 预期收益」三件套，比罗列 API 更能体现工程能力。

```text
05-edge-cases-perf.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 2. groupby 后的索引重建  (python)
    |
    v
  [02] 3. 命名聚合 namedAgg 一次算多种统计  (python)
    |
    v
  [03] 4. merge 的 indicator 与 validate 实战  (python)
    |
    v
  [04] 5. categorical 类型对内存与速度的影响  (-)
    |
    v
  [05] 6. 多列 groupby 与 dropna 的交互  (-)
    |
    v
  [06] 7. rolling 的 min_periods 与 center  (-)
    |
    v
  [07] 8. apply 逐行陷阱与向量化替代  (-)
    |
    v
  [08] 9. 大数据下的分块与类型优化  (-)
    |
    v
  [END] 三视角解析收口
```
