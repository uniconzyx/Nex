# 时间序列：DatetimeIndex、resample 与 rolling

## 1. 先把「时间」变成对的类型

时间序列的一切麻烦，**八成源于时间列还是字符串**。

```python
import pandas as pd

df = pd.read_csv("sales.csv", parse_dates=["ts"])     # ① 读入时就解析
df["ts"] = pd.to_datetime(df["ts"], errors="coerce")  # ② 事后转换（脏值变 NaT）
df["ts"] = pd.to_datetime(df["ts"], format="%Y-%m-%d %H:%M:%S")  # ③ 指定格式（快很多）
```

三条要点：

1. **`errors="coerce"`** 把无法解析的值变成 `NaT`（时间版 NaN），
   否则整列直接抛错。生产环境的脏数据必须用 `coerce` 再接一个「有多少 NaT」的断言；
2. **显式 `format=`** 比自动推断快得多（自动推断要逐行试探多种格式）；
3. `df.dtypes` 里必须是 `datetime64[ns]`，看到 `object` 就说明这一步没做成。

**为什么必须转类型？** 因为只有 `DatetimeIndex` 才支持
`.resample()` / `.rolling()` / `.loc["2026-01":"2026-03"]` / `.dt` 访问器。
字符串列上这些**全部不可用**。

## 2. DatetimeIndex 的切片能力

```python
df = df.set_index("ts").sort_index()     # 排序！很多时间操作要求单调

print(df.loc["2026-01"])                  # 整个 1 月
print(df.loc["2026-01":"2026-03"])        # 区间（含两端）
print(df.loc["2026-01-05"])               # 某一天
```

**`sort_index()` 不是可选项**：`rolling` 在非单调索引上会报错或给出错误结果。
凡是接手别人的时间数据，第一件事就是
`assert df.index.is_monotonic_increasing`。

## 3. resample：时间维度上的 groupby

`resample` 的心智模型就是「**把时间当分组键的 groupby**」：

```python
df.resample("ME")["amount"].sum()      # 按月求和
df.resample("W")["amount"].mean()     # 按周平均
df.resample("QE")["amount"].max()      # 按季度最大
```

常用频率别名：

> ⚠️ **pandas 3.x 已移除旧别名**：`M` / `Q` / `Y` / `H` 会直接抛
> `ValueError: Invalid frequency`，必须写 **`ME`**（月末）/ **`QE`**（季末）/
> **`YE`**（年末）/ **`h`**（小时）。这不是笔误，是 3.0 的**破坏性变更**——
> 从旧代码迁移时最常见的报错之一。

| 别名 | 含义 | 标签落在 |
|---|---|---|
| `"D"` | 日 | 当天 |
| `"W"` | 周 | **周日**（默认 `W-SUN`） |
| `"ME"` | 月末 | **月末最后一天** |
| `"MS"` | 月初 | **月初第一天** |
| `"QE"` | 季末 | 季末最后一天 |
| `"YE"` | 年末 | 年末最后一天 |
| `"h"` / `"min"` / `"s"` | 时/分/秒 | 对应时刻 |

**`M` 与 `MS` 的差别是最经典的一处**：`resample("ME")` 把一整个月的数据
**归到月末那一天**；`resample("MS")` 归到月初。做「月度报表」时用错，
标签就会整体错一个月，而且**数字全对、看不出错**。

`resample` 还支持「上采样」（降频的反向操作）：

```python
df.resample("D").ffill()          # 月频 → 日频，用前值填充
df.resample("D").interpolate()    # 线性插值
```

## 4. rolling / expanding / ewm：三种窗口

```python
df["ma7"]  = df["amount"].rolling(7).mean()        # 固定窗口（最近 7 天）
df["cum"]  = df["amount"].expanding().sum()        # 扩张窗口（从开始至今）
df["ewma"] = df["amount"].ewm(span=7).mean()       # 指数加权（越近权重越大）
```

**窗口的首尾边界必须记清楚**：

- `rolling(7)` 的**前 6 个结果是 `NaN`**，因为不足 7 个观测；
  要拿到带值的首部用 `min_periods=1`：
  ```python
  df["ma7"] = df["amount"].rolling(7, min_periods=1).mean()
  ```
- `rolling(7).mean()` 的第 $t$ 个值是 $[t-6,\ t]$ 这 7 个点的均值，
  即**右对齐、含当前点**。若要看「过去不含今天」，用 `closed="left"`。

**这三种窗口的区别，本质是「权重的分配方式」**：

| 类型 | 权重 |
|---|---|
| `rolling(n)` | 最近 n 个点等权，n 个之前为 0 |
| `expanding()` | 历史全部点等权 |
| `ewm(span=n)` | 权重按 $\alpha = 2/(n+1)$ 指数衰减 |

## 5. 时间运算：shift / diff / pct_change / 同比

```python
df["prev"]        = df["amount"].shift(1)          # 上一期（首行为 NaN）
df["delta"]       = df["amount"].diff(1)           # 差分
df["growth"]      = df["amount"].pct_change()      # 环比增长率
df["yoy"]         = df["amount"].pct_change(12)    # 同比（月度数据 lag 12）
```

`shift` 是「同比/环比」的全部秘密：**同一条折线，往后挪 12 个月再相除，
就是同比**。不用手写循环。

## 6. 时区：能不用就不用，用了就要统一

```python
s = pd.to_datetime(["2026-01-01 08:00"]).tz_localize("Asia/Shanghai")   # 挂本地时区
s.tz_convert("UTC")                                                     # 转 UTC
df.tz_localize(None)                                                    # 去掉时区（回到 naive）
```

**两条铁律**：

1. **存储一律 UTC，展示才转本地**。混用本地时区做聚合，
   会在夏令时切换那一小时出现「重复的一小时」或「消失的一小时」；
2. `tz_localize` 只对 **naive**（无时区）时间有效，已有时区的要用 `tz_convert`。
   搞反了会抛 `TypeError`。中国不使用夏令时，但**代码会跑到别的时区**。

## 7. 三视角：时间索引

### 🧑‍💻 程序员视角
**工程决策顺序（时间序列报错时照此排查）：**

```
① df.dtypes 里 ts 是 datetime64 吗？   否 -> 先 parse_dates / to_datetime
② index 单调递增吗？                   否 -> sort_index()（rolling 会错！）
③ 频率别名用对了吗（ME vs MS）？         错 -> 标签整体错一个月，数字却不报警
④ 缺口怎么处理？                        -> resample 会为「没有数据的区间」补 NaN，
                                          不要盲目 fillna(0)（0 与「没有」语义不同）
⑤ 时区统一了吗？                        -> 存储 UTC，展示转本地
```

**几个实战判据：**

- **残缺月份**：最后一次 resample 的桶可能只覆盖了几天，
  报表上会显示成「断崖式下跌」。习惯做法是**丢掉最后一个不完整周期**，
  或在报表上标注 `*`。
- **`fillna(0)` 之前先问**：这个区间真的发生了 0 次，还是**没有记录**？
  前者填 0 正确，后者填 0 会把「缺失」伪装成「零」——这是数据分析里
  最隐蔽的一类错误（见 `data-ch03` 的填充陷阱）。
- **`pct_change` 遇到 0** 会得到 `inf`，遇到 `NaN` 得到 `NaN`。
  产出报表前一定要 `replace([np.inf, -np.inf], np.nan)`。

### 🎓 博士生视角
**重采样的形式化定义：**

给定时间索引 $\{t_i\}$ 与桶划分 $\{B_k\}$（互不相交、并集覆盖时间轴），
重采样是一个**由点集到区间集合的商映射**：

$$x_k \;=\; \bigoplus_{i:\ t_i \in B_k} x_i$$

它与 `groupby` 共享同一套 split-apply-combine 结构，
唯一的区别是**分组键由时间（连续域）生成，而非由离散标签给出**。
这带来两个独有性质：

1. **桶是稠密的**：即使某区间没有观测，`resample` 也会产出该桶（值为 NaN）。
   这是它与 `groupby` 的关键差异——`groupby` 只产出**出现过的**组；
2. **桶的边界依赖锚点**：`"W"` 默认锚在周日、`"ME"` 锚在月末。
   锚点的选择在跨时区时会改变结果（因为「月末」是本地日历概念）。

**滚动窗口与卷积**：`rolling(n).mean()` 在数学上是与
长度为 $n$ 的矩形核的**离散卷积**：

$$y_t = \frac{1}{n}\sum_{j=0}^{n-1} x_{t-j} = (x * h)_t,\qquad h_j = \tfrac{1}{n}\ \ (0 \le j < n)$$

**这解释了为什么 `ewm` 更快也更平滑**：指数加权把矩形核换成了
$h_j \propto (1-\alpha)^j$，而它可以写成**递推式**
$y_t = \alpha x_t + (1-\alpha) y_{t-1}$，
于是每步只需 $O(1)$ 而非 $O(n)$，总复杂度从 $O(nT)$ 降到 $O(T)$。
这也是「为什么金融里广泛使用 EWMA 而不是简单移动平均」的**计算**原因
（另一个原因是它对近期信息更敏感，更符合对波动率的建模直觉）。

**单调性的必要性**：滑动窗口定义在「序」上，若索引非单调，
「最近 $n$ 个」这一概念本身无定义。因此 Pandas 要求先 `sort_index`——
这不是实现限制，而是**定义域约束**。

### 📚 考研者视角
**笔试/面试标准问法与易错口径：**

- *「`resample("ME")` 和 `resample("MS")` 有什么区别？」*
  → 标签位置：`M` = 月末，`MS` = 月初。
  这是本主题**最高频的送分/送命题**，一定要答到「标签落在哪一天」。
- *「`rolling(7).mean()` 为什么前 6 行是 NaN？」*
  → 不足窗口长度，默认 `min_periods=window`。
  追问「怎么让它从第一行就有值」→ `min_periods=1`。
- *「滚动窗口是左闭右开还是两端都含？」*
  → `rolling(n)` 默认在**右端**闭合，即第 $t$ 个窗口是 $[t-n+1,\ t]$，
  **包含当前点**。想让窗口不含当前点用 `closed="left"`。
- *「`shift` 和 `diff` 的关系？」*
  → `diff(n) = x - x.shift(n)`。`pct_change(n)` 再除以 `shift(n)`。
  三者是同一族算子，答出这条等式能体现理解而非死记。
- *「同比和环比怎么算？」*
  → 环比 `pct_change(1)`，同比看周期长度（月度用 `pct_change(12)`）。
  注意 `pct_change` 在分母为 0 时返回 `inf`，需清洗。
- 易错口径：
  ① 认为 `resample` 与 `groupby` 完全等价——**错**，前者会为**空区间**产出桶；
  ② 认为 `expanding()` 也受 `min_periods` 影响——它默认从第 1 个观测开始；
  ③ 把 `tz_localize` 与 `tz_convert` 混用——对已有时区的索引用 `localize` 会报错。


## 8. 陷阱速查

| 症状 | 真因 | 正确写法 |
|---|---|---|
| `resample` 报 `TypeError` | 索引不是 `DatetimeIndex` | `parse_dates` / `to_datetime` |
| `rolling` 结果全错位 | 索引非单调 | `sort_index()` |
| 月报表标签整体偏一个月 | 用了 `"ME"` 而非 `"MS"` | 按展示口径选 `M`/`MS` |
| 折线末端断崖下跌 | 最后一个桶不完整 | 丢弃末桶或标注 |
| 同比全是 `inf` | 分母为 0 | `replace([inf,-inf], nan)` |
| 时区操作抛 `TypeError` | 对带时区的索引用了 `tz_localize` | 改用 `tz_convert` |
