# 缺失值、dtype 与内存优化

> 本章要点：缺失值是数据清洗的**主战场**；
> 而 dtype 既决定「能不能算对」，也决定「内存够不够用」。

## 1. 缺失值的三种标记

| 标记 | 所属 | 适用场景 | 注意 |
|---|---|---|---|
| `np.nan` | `float64` | 数值列的默认缺失 | **`nan != nan` 为真**，比较必须用 `isna()` |
| `pd.NaT` | `datetime64` | 时间列的缺失 | 「Not a Time」 |
| `pd.NA` | **Nullable dtype** | `Int64` / `boolean` / `string` | 语义最干净，支持三值逻辑 |

### 1.1 `NaN` 的三个反直觉行为

**（1）`NaN` 不等于自己。**

```python
np.nan == np.nan        # False
df[df["v"] == np.nan]   # 永远返回空表！
df[df["v"].isna()]      # ✅ 正确做法
```

**（2）聚合函数默认跳过 `NaN`。**

```python
pd.Series([1.0, np.nan, 3.0]).mean()      # 2.0（分母是 2，不是 3）
pd.Series([1.0, np.nan, 3.0]).sum()       # 4.0
pd.Series([1.0, np.nan, 3.0]).sum(skipna=False)   # NaN
```

**这是「默认行为可能不符合直觉」的典型**：你要的均值是「有效值的均值」还是
「除以总行数」？Pandas 默认前者。若要后者，得自己算 `sum() / len(s)`。

**（3）`NaN` 会传染到整个运算链。**

```python
pd.Series([1.0, 2.0]).add(pd.Series([10.0, 20.0], index=[5, 6]))
# 结果全是 NaN —— 因为索引完全不相交
```

### 1.2 整型列的「被迫升级」

```python
pd.Series([1, 2, None]).dtype       # float64 ！因为 int64 装不下 NaN
pd.Series([1, 2, None], dtype="Int64").dtype   # Int64（Nullable，注意大写 I）
```

Nullable dtype 的好处：**类型不牺牲**（整数就是整数）、
**语义清晰**（`pd.NA` 参与运算遵循三值逻辑）。

三值逻辑的真值表（`pd.NA & True == NA`、`pd.NA | True == True`），
但**在布尔上下文里用 `pd.NA` 会报错**（因为没有「真假」可判），
必须显式 `fillna(False)`。

## 2. 检测与处理缺失

### 2.1 先「体检」再处理

```python
df.isna().sum()                        # 每列缺失数量
df.isna().mean()                       # 每列缺失比例（更直观）
df.isna().sum(axis=1)                  # 每行缺失数量
df.isna().any()                        # 哪些列有缺失
```

**处理前的两个必问**：

1. **缺失是「随机」还是「有信息」？** 若「没填手机号」的用户恰好是特定人群，
   那 `dropna` 就是在**系统性地删掉某一类人**，会让后续分析产生偏差。
2. **缺失的比例是多少？** 若某列缺失 90%，填充的意义可能还不如直接删列。

### 2.2 三种处理策略

| 策略 | 写法 | 何时用 |
|---|---|---|
| **删** | `df.dropna(subset=["v"], how="any"/"all", thresh=n)` | 缺失极少（<5%），且缺失随机 |
| **填** | `df["v"].fillna(0 / mean / median / ffill / bfill)` | 缺失比例中等，且有合理的填充依据 |
| **插值** | `df["v"].interpolate(method="linear"/"time")` | **时间序列**且趋势连续 |

**`dropna` 的关键参数**：

```python
df.dropna()                              # 任一行有缺失就删（默认 how="any"）
df.dropna(how="all")                     # 只有全为空的行才删
df.dropna(subset=["price"])              # 只看这一列
df.dropna(thresh=3)                      # 至少 3 个非空才保留
```

**`fillna` 的进阶用法**：

```python
df["v"].fillna(df["v"].median())          # 中位数填充（比均值抗离群）
df["v"].fillna(method="ffill")            # 用上一个有效值（时间序列常用）
df["v"].fillna(method="ffill", limit=2)   # 最多连续填 2 个
df["group"].fillna("unknown")             # 类别列填成显式类别，而不是"猜"
```

**`interpolate` 的陷阱**：它**假定趋势平滑**。
对「日销售额」这种有周末效应的数据线性插值，会**凭空造出不存在的工作日峰值**。
对时间序列更合适的是 `method="time"`（按真实时间间隔加权）。

### 2.3 填充的三种「造假」风险（务必知道）

1. **均值填充会压缩方差**。所有缺失都被填成同一个值，
   该列的方差被**系统性地低估**，进而影响相关性、回归系数。
2. **`ffill` 在长缺失段会「复制」旧值**。若一段缺失跨越了趋势变化，
   `ffill` 会造出一段**不存在的平稳期**。
3. **填充值参与了后续统计**。用「含填充值的均值」去填充，
   会让均值本身被反复计入，形成**自我强化的偏差**。
   更严谨的做法是用**训练集统计量**填充（避免数据泄漏），
   或直接使用能处理缺失的模型（如 XGBoost）。

## 3. dtype 与内存

### 3.1 内存体检

```python
df.info(memory_usage="deep")                      # 各列占用明细
df.memory_usage(deep=True).sum() / 1024**2        # 总内存（MB）
```

**注意 `deep=True`**：不加 `deep` 时，`object` 列只算**指针大小**（8 字节/个），
完全低估了真实占用——字符串内容存在堆上，必须 `deep=True` 才能量准。

### 3.2 各 dtype 的字节数

| dtype | 字节/元素 | 说明 |
|---|---|---|
| `int8` / `int16` / `int32` / `int64` | 1 / 2 / 4 / 8 | **按取值范围选最小够用的** |
| `uint8` / … / `uint64` | 1 / … / 8 | 无符号 |
| `float32` / `float64` | 4 / 8 | `float32` 有效位约 7 位十进制 |
| `bool` | 1 | |
| `category` | 1~2（+ 一张字典表） | **低基数列的利器** |
| `object` | 8（指针）+ 字符串堆内存 | **最贵** |

### 3.3 三种降内存手段（附量化）

**（1）数值降位。**

```python
df["count"] = pd.to_numeric(df["count"], downcast="integer")   # 自动选最小的整型
df["price"] = pd.to_numeric(df["price"], downcast="float")
```

**（2）低基数列转 `category`。**

```python
df["city"] = df["city"].astype("category")
```

**适用判据**：`nunique() / len(df) < 0.5`（基数远小于行数）。
城市、性别、状态码、国家这类列效果最好。
**反例**：ID 类列（基数≈行数）转 `category` 反而**更费内存**（字典表本身很大）。

**（3）字符串列用 `string` dtype（Nullable）**，但注意它**不省内存**，
只是让类型更明确、缺失值统一为 `pd.NA`。

### 3.4 一个真实的量化对比

对 100 万行、含 `city`（10 个取值）+ `amount`（int64）的数据：

| 做法 | 内存 |
|---|---|
| 默认（`object` + `int64`） | 约 60 MB 以上 |
| `city` 转 `category` | 显著下降（字典表只有 10 项） |
| `amount` 降为 `int32` | 减半 |
| 两者同时 | 可压到原始的几分之一 |

**关键认识**：**`object` 列是内存的绝对大户**，
所以优化顺序永远是「先处理字符串列，再降数值位」。

## 4. 三视角：缺失值与内存

### 🧑‍💻 程序员视角
**内存优化决策树**：

```
df.memory_usage(deep=True).sort_values(ascending=False)   # 先排序，看大户
│
├─ 最大的是 object 列？
│   ├─ nunique()/len() < 0.5 → astype("category")   ← 收益最大
│   └─ 基数很高（如 ID）      → 考虑 drop 或哈希编码，category 会变慢
│
├─ 最大的是 int64 列？
│   └─ to_numeric(downcast="integer")  ← 收益 = 原字节/新字节
│
├─ 最大的是 float64 列？
│   └─ 精度要求不高时 downcast="float"
│
└─ 有大量 NaN 的稀疏列？
    └─ 考虑用稀疏数组或转换存储形式
```

**必须遵守的一条纪律**：**降位前先确认取值范围**。

```python
print(df["count"].min(), df["count"].max())   # 必须是 [0, 127] 才敢降到 int8
```

盲目 `astype("int8")` 会**静默溢出**（`int8` 超出 127 会变成负数），
而且不会报错——这是最危险的一类 bug。

**缺失值处理的顺序建议**：先 `isna().sum()` 定量 → 判断缺失机制 →
能删则删（且记录删了多少行）→ 要填就用**有依据的**值（不要随手填 0）→
**在特征工程里保存「是否缺失」这一指示列**（缺失本身可能是信息）。

### 🎓 博士生视角
「填充缺失值」在统计上等价于**对缺失机制做假设**，
而缺失机制由 Rubin 的三分类刻画：

| 机制 | 含义 | 均值填充是否无偏 |
|---|---|---|
| **MCAR**（完全随机缺失） | 缺失与任何变量无关 | 点估计无偏，但**方差被低估** |
| **MAR**（随机缺失） | 缺失依赖于**可观测量** | 需建模（如回归插补、MICE） |
| **MNAR**（非随机缺失） | 缺失依赖于**缺失值本身** | 无法从数据内部识别，**必有偏** |

**均值填充的偏误来源**可以精确写出来。设真实方差为 $\sigma^2$，
其中比例 $p$ 的观测被替换为常数 $\mu$，则填充后的方差为

$$\mathrm{Var}_{\text{filled}} = (1-p)\,\sigma^2 \;<\; \sigma^2$$

也就是说方差被**按缺失比例压缩**。相关性、回归系数的标准误都会随之失真——
这正是**多重插补（Multiple Imputation）** 被提出的原因：
它不以单一值填充，而是产生 $m$ 组「合理的」填充值，
在每组上独立分析，最后用 Rubin 规则合并结果，
从而**把插补本身的不确定性也计入方差估计**。

在**内存与表示**这一侧，`category` 的本质是**字典编码（dictionary encoding）**：

$$\text{values} \in \{0, 1, \dots, k-1\}^n, \qquad \text{categories} \in \Sigma^k$$

空间从 $O(n \cdot |\Sigma|)$ 降到 $O(n) + O(k \cdot |\Sigma|)$。
这与**列式存储（Parquet / ORC）的字典编码、关系数据库的枚举类型、
信息检索里的倒排索引**是同一思想：
**当取值空间的基数远小于实例数时，存「代号」比存「原值」便宜得多。**

### 📚 考研者视角
无统考考点。面试口径四句话：

1. **`NaN`、`NaT`、`pd.NA` 三类缺失**；`NaN != NaN`，必须用 `isna()`；
2. **聚合默认跳过 `NaN`**（`skipna=True`），所以 `mean()` 的分母是**非空个数**；
3. **整数列的缺失会把 dtype 升为 `float64`**，要保住整数用 `Int64`（Nullable）；
4. **内存优化先处理 `object` 列**（`category` 收益最大），再对数值列降位，
   **降位前必须确认取值范围**。

高频追问：*「`dropna` 和 `fillna` 怎么选？」* →
看缺失比例与机制：比例小且随机（MCAR）→ 删；
比例大或有趋势（时间序列）→ 填/插值；**能解释缺失原因时，把「是否缺失」也作为特征。**
