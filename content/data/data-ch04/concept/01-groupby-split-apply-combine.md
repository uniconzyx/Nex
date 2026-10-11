# groupby：split-apply-combine 与四种聚合器

## 1. 心智模型：split → apply → combine

`groupby` 不是「一个函数」，而是一套**三步流水线**：

```
   ┌── split ──┐     ┌── apply ──┐     ┌── combine ──┐
   │ 按 key 把  │     │ 对每个子集 │     │ 把子结果按  │
   │ 行切成若干组│ ──▶ │ 施加一个函数│ ──▶ │ 组标签拼回  │
   └───────────┘     └───────────┘     └─────────────┘
```

这条流水线解释了 90% 的「结果形状为什么是这样」的疑问：

- **split 决定了结果的行索引**（组标签，默认就是 key 的取值）；
- **apply 决定了结果的列**（函数返回什么，就是什么）；
- **combine 决定了结果的拼接方式**（同一组多行 → 多行结果；返回标量 → 一行）。

```python
import pandas as pd

df = pd.DataFrame({
    "city": ["BJ", "BJ", "SH", "SH", "SH"],
    "sales": [10, 20, 5, 15, 25],
})

g = df.groupby("city")           # 此时还没算任何东西（惰性）
print(g["sales"].sum().to_dict())        # {'BJ': 30, 'SH': 45}
print(g["sales"].mean().to_dict())       # {'BJ': 15.0, 'SH': 15.0}
```

**注意 `groupby` 对象是惰性的**：`df.groupby("city")` 只记录了「怎么分组」，
真正的计算发生在你调用聚合函数的那一刻。这一点和 Spark 的
`groupBy` 一样（见 `bd-ch04`），也是为什么它**不能**直接 `print` 出有用信息。

## 2. 四种聚合器：返回形状决定用途

这是本章最容易记混、也最常考的一组对比：

| 方法 | 返回形状 | 索引 | 典型用途 |
|---|---|---|---|
| `agg` | **每组一行**（或每列一行） | 组标签 | 出报表：每组一个汇总数 |
| `transform` | **和原表同长** | 保留原索引 | 加一列「组内均值」做对比 |
| `apply` | **任意**（你说了算） | 你说了算 | 复杂逻辑、组内排序、多列联动 |
| `filter` | **原表的行子集** | 保留原索引 | 只留满足条件的组 |

```python
df["city_mean"] = df.groupby("city")["sales"].transform("mean")
# transform 返回和 df 一样长的 Series，可以直接赋值成新列
```

`transform` 是**唯一能把「组级统计量」广播回原表**的聚合器。
用 `agg` 做不到：

```python
df["city_mean"] = df.groupby("city")["sales"].agg("mean")   # 报错/长度不匹配
```

**为什么 `transform` 能对齐？** 因为它的契约是「输入 n 行，输出 n 行，
第 i 行的值由第 i 行所属的组决定」。这条契约让 Pandas 可以直接做索引对齐，
不需要你手工 `merge` 回去。

## 3. 分组键的六种形态

`groupby` 的第一参数远不止「列名」：

```python
df.groupby("city")                       # ① 列名
df.groupby(["city", "month"])            # ② 多列（结果是 MultiIndex）
df.groupby(df["sales"] > 15)             # ③ 布尔 Series（二分）
df.groupby(lambda i: i % 2)              # ④ 按索引位置分奇偶
df.groupby(df["city"].str.upper())       # ⑤ 任意 Series（可与 df 无关，需长度相同）
df.groupby(level="city")                 # ⑥ 按索引层级（index 已经 set_index 过时）
```

真正常用的是 ① ① ② 和 ⑥。③ 有一个高频用法是**分箱**：

```python
bins = pd.cut(df["sales"], bins=[0, 10, 20, 100], labels=["低", "中", "高"])
df.groupby(bins, observed=True)["sales"].count()
```

`pd.cut` + `groupby` 就是「按区间统计分布」的标准写法。
注意 `observed=True`：对 `Categorical` 分组时，默认会保留**所有**类别组合
（包括数据里根本没出现的），在大基数类别上会**炸内存**。

## 4. 命名聚合（Named Aggregation）：一次出多指标

旧写法用字典，新写法推荐用 `numpy` 风格的关键字：

```python
out = df.groupby("city").agg(
    销售额=("sales", "sum"),
    订单数=("sales", "size"),
    最大值=("sales", "max"),
)
```

`agg` 的 `**kwargs` 形式（`新列名=(源列, 函数)`）比 `{"sales": ["sum", "size"]}`
可读得多，而且**列名是平的**，不用再处理 MultiIndex 列。

## 5. 三视角：分组语义

### 🧑‍💻 程序员视角
**工程上先问三个问题，再动手写 groupby：**

1. **结果要不要回到原表？** 要 → `transform`；不要 → `agg`。
   这是最常见的一个错误来源，写成 `df["m"] = df.groupby(...).mean()`
   必然因长度不匹配而失败。
2. **分组键有多少个唯一值？** 用 `df["key"].nunique()` 先看一眼。
   超过几万就要警惕：`apply` 会为每组建一个子 DataFrame，开销是 O(组数)；
   `observed=True` 与 `sort=False` 都能显著提速。
3. **组内有没有缺失的键？** `groupby` **默认丢弃** key 为 `NaN` 的组
   （`dropna=True`）。做「缺失也算一类」的统计时必须显式 `dropna=False`。

**排查顺序**（结果不对时按此顺序）：

```
① 形状不对？        -> 用了哪个聚合器（agg/transform/apply）
② 行数变少？        -> key 里有 NaN 被 dropna 丢了 / 组被 filter 掉了
③ 列名变成元组？    -> 多函数聚合产生了 MultiIndex 列，用命名聚合拍平
④ 内存爆了？        -> Categorical 分组没加 observed=True
```

**性能红线**：`groupby(...).apply(func)` 中 `func` 返回**标量**时，
Pandas 会退化到逐组 Python 调用，比 `agg` 慢 1~2 个数量级。
能用内置聚合名（`"sum"`/`"mean"`/`"max"`）就不要写 lambda。

### 🎓 博士生视角
**为什么 split-apply-combine 是「分组运算」的通用范式？**

从代数的角度，一个分组聚合可以被形式化为三元组
$(G,\ \oplus,\ \iota)$：$G$ 是分组标签集合，
$\oplus$ 是**满足结合律**的组内归约算子，$\iota$ 是单位元。
只有当 $\oplus$ 满足结合律时，「先分组算、再合并」与「整体算」才等价：

$$\bigoplus_{g \in G} \left(\bigoplus_{x \in S_g} x\right) \;=\; \bigoplus_{x \in S} x$$

这条恒等式正是**可分块计算**的充要条件。于是：

- `sum`/`count`/`min`/`max` 满足结合律 → 可流式、可并行、可分块（见 `data-ch03` 的分块陷阱）；
- `mean` 本身不满足结合律，但 `(sum, count)` **二元组**满足 →
  所以工程上用「累积充分统计量」而不是「累积结果」；
- `median`/`quantile` 不满足 → 必须保留全量或使用近似算法（`t-digest`）。

**`transform` 的语义是什么？**
它是一个**从组到组内元素的下标映射**：
$\text{transform}(x_i) = f(S_{g(i)})$，即「第 $i$ 行的输出 = 它所属组的组级统计量」。
数学上这是把商集上的函数**沿投影拉回**到原集合——这就是它能保持行数不变的根本原因。

**`apply` 的代价为什么高？**
split 阶段要物化 $|G|$ 个子 DataFrame，combine 阶段要重新拼接索引。
当 $|G| \to |S|$（每组一行）时，开销从「一次向量化」退化为 $|S|$ 次
Python 层函数调用与对象构造——**从 $O(n)$ 的向量化退化为 $O(n)$ 次解释器开销**，
常数差两到三个数量级。这不是 Pandas 的实现缺陷，而是**通用接口的必然代价**。

### 📚 考研者视角
**笔试/面试标准问法与易错口径：**

- *「`agg` 和 `transform` 的区别？」*
  → 标准答法要落到**返回形状**：`agg` 每组一行（压缩），
  `transform` 与原表同长（广播）。追问「要给原表加一列组内均值用哪个」→ `transform`。
- *「`groupby` 后缺失的 key 怎么处理？」*
  → 默认 `dropna=True` **丢弃**，这是最常被忽略的一处；
  易错口径：很多人答「NaN 单独成一组」，错。
- *「`groupby` 的 `size()` 和 `count()` 有什么区别？」*
  → `size()` 数**行数（含 NaN）**，`count()` 数**非空值个数**。
  这是经典送分题，也是经典送命题。
- *「`apply` 一定比 `agg` 慢吗？」*
  → 不能说「一定」。要分情况：返回标量时 `agg` 明显更快；
  但若逻辑本身就不可向量化（如组内排序取 top-k），`apply` 是合理选择。
  **答「一定」是错的**。
- *「`groupby` 之后是什么类型？」*
  → `DataFrameGroupBy`（惰性对象），**不是** DataFrame。
  这点在「为什么 `print` 出来是一堆地址」的题里会考。
- 易错口径提醒：`groupby(...)[["a","b"]]` 选多列返回 DataFrameGroupBy，
  `groupby(...)["a"]` 返回 SeriesGroupBy，两者的 `agg` 行为不同。


## 6. 常见陷阱速查

| 症状 | 真因 | 正确写法 |
|---|---|---|
| 赋值新列报长度不匹配 | 用了 `agg` | 改用 `transform` |
| 结果少了几组 | key 含 `NaN` 被丢弃 | `groupby(..., dropna=False)` |
| 内存暴涨 | Categorical 分组保留了空组合 | `observed=True` |
| 列名变成 `("sales","sum")` | 多函数聚合产生 MultiIndex 列 | 命名聚合 `agg(名=(列,函数))` |
| 慢得离谱 | `apply` 返回标量 | 换内置聚合名，或先 `sort=False` |
