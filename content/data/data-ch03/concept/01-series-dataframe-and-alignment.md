# Series、DataFrame 与「自动对齐」

> 本章要点：Pandas 与 NumPy 最大的差别不是「有列名」，
> 而是**运算时按索引对齐**这一条语义。

## 1. 两个核心数据结构

### 1.1 Series：带索引的一维数组

```python
import pandas as pd
s = pd.Series([10, 20, 30], index=["a", "b", "c"])
```

它的组成是**三个**部分，而不是两个：

```
values : [10, 20, 30]          <- 真正存数据的 ndarray
index  : Index(['a','b','c'])  <- 标签
name   : None                  <- 列名（Series 也有名字）
```

`dtype` 就是 `values` 的 `dtype`。若给了混类型，Pandas 会向上取「公共类型」
（通常是 `object`），**此时向量化失效**——这是性能问题的第一来源。

### 1.2 DataFrame：共享行索引的列字典

DataFrame 可以被理解为「一堆共享同一行索引的 Series」：

```
         price   qty           <- columns（列索引）
apple      3.5     10
banana     1.2     25          <- index（行索引）
cherry     8.0      4
```

它**不是**二维数组的封装，而是**列导向**的：
每一列是一个独立的 `ndarray`（或 `ExtensionArray`）。
这个设计决定了三件事：

1. **每列可以有自己的 `dtype`**（这才是混类型数据的正确表达）；
2. **列是「取出来就对齐」的基本单位**，`df["price"]` 返回 Series；
3. ⚠️ **通过 `df["a"]` 赋值新列时不会对齐到某个 ndarray 的位置，而是对齐索引**。

## 2. 自动对齐：Pandas 的灵魂

### 2.1 一个必须亲手做过一次的实验

```python
a = pd.Series([1, 2, 3], index=["x", "y", "z"])
b = pd.Series([10, 20, 30], index=["z", "y", "x"])

print(a + b)
```

结果是：

```
x    31.0      # 1 + 30
y    22.0      # 2 + 20
z    13.0      # 3 + 10
dtype: float64
```

**注意两件事**：
1. **按标签对齐，不按位置**。如果按位置，结果会是 `[11, 22, 33]`。
2. **结果是按索引排序的**（本例恰好排好；若索引不可排序，则保持「并集的出现顺序」）。

### 2.2 索引不相交时：并集 + NaN

```python
a = pd.Series([1, 2], index=["x", "y"])
b = pd.Series([10], index=["y", "z"])

print(a + b)
```

```
x     NaN      # a 有 b 没有 -> NaN
y    12.0      # 两边都有 -> 相加
z     NaN      # b 有 a 没有 -> NaN
dtype: float64
```

**这是初学者最常见的「数据凭空变大」的原因**：两个表按标签对齐后取了**并集**，
凭空多出来的标签全是 `NaN`。

### 2.3 dtype 的「传染」：int + NaN -> float

上面结果为什么是 `float64`？因为**标准 NumPy 整数类型没有「缺失」的表达**。
Pandas 只能把整数列升级成 `float64`，用 `NaN` 表示缺失。

这带来两个后果：

- 整数 ID 列一旦出现缺失，就会**悄悄变成浮点**，显示成 `1.0`、`2.0`；
- 大整数（超过 $2^{53}$）在 `float64` 下**精度会丢失**（`float64` 只有 53 位有效尾数）。

**解法**：用 **Nullable dtype**（见 concept 04），它有独立的缺失标记，不需要牺牲类型。

### 2.4 `reindex` 与 `align`：显式对齐

如果希望**精确控制对齐结果**（而不是被动接受并集），用：

```python
s.reindex(["x", "y", "z", "w"])        # 指定目标索引，缺失处填 NaN
s.reindex(["x", "y"], fill_value=0)    # 指定填充值
a.align(b, join="inner")               # 只保留交集（join 可为 outer/inner/left/right）
```

**工程含义**：对齐是一个**保序的操作**，但 `reindex` 会**改变行数**。
在流水线里「行数变了」往往意味着 bug，所以对齐后应核对 `shape`。

## 3. 三视角：索引与对齐

### 🧑‍💻 程序员视角
**排查「数据行数变多 / 结果全是 NaN」的固定顺序**：

```python
# ① 先看两边索引是否一致
print(a.index.equals(b.index))       # 快速判断
print(a.index.difference(b.index))   # 只在 a 里的标签
print(b.index.difference(a.index))   # 只在 b 里的标签
print(a.index.has_duplicates, b.index.has_duplicates)   # 有没有重复标签！
```

**重复索引是最隐蔽的坑**：如果 `a` 的索引里有重复标签，`a + b` 会产生
**笛卡尔式的行数膨胀**（标签 `x` 出现 2 次 × 另一边的 3 次 = 6 行）。这不是 bug，
是「标签对齐」在重复标签下的必然结果。

工程决策树：
```
两表相减/相加后行数变多？
├─ 是 → 检查两边索引是否有重复（df.index.has_duplicates）
│        有 → 先 drop_duplicates 或 reset_index 到位置索引
└─ 否 → 检查是否有 NaN
         有 NaN → 用 index.difference 找出不匹配的标签
```

**另一个高频场景**：从数据库读出的两批数据，一批按 `id` 排序、一批按时间排序，
直接相减得到全 `NaN`——因为索引是行号，而两批**行号对应的实体不同**。
正确做法是先 `set_index("id")` 再做运算。

### 🎓 博士生视角
自动对齐本质上是**把「加法」从一个函数提升为一个「带索引的加法」**，
这在代数上等价于**以索引为键的稀疏向量空间运算**：

设 $f: I \to \mathbb{R}$、$g: J \to \mathbb{R}$ 是两个部分函数（只在各自索引上有定义），
则 Pandas 的 `f + g` 定义为

$$(f + g)(k) = \begin{cases} f(k) + g(k) & k \in I \cap J \\ f(k) & k \in I \setminus J \\ g(k) & k \in J \setminus I \end{cases}$$

当缺失以 `NaN` 表示时，第三、四行落在 `NaN` 上（而不是恒等元 $0$）。
**这一点很关键**：如果语义上缺失应当是「加法的单位元」，那么并集语义是正确的
（缺失视为 0）；但如果缺失代表「未知」，那么并集语义会**污染整个结果**。

这就是为什么 Pandas 提供了 `add(fill_value=0)`：

```python
a.add(b, fill_value=0)     # 缺失视为 0，不产生 NaN
```

**语义选择权在使用者手里**，框架不替你决定——这是「显式优于隐式」的设计哲学
在缺失语义上的体现。

另一个值得注意的形式化点：**对齐操作是「按索引的 join」**，
它与关系代数中的 $\bowtie$ 同构，`join` 参数（`inner`/`outer`/`left`/`right`）
就是集合运算的选择。因此**读懂 `merge` 的语义，其实在 NumPy 里就已经有对应物**。

### 📚 考研者视角
数据分析方向**不考这个**，但**调包岗/数据岗面试高频**，标准口径两句话：

1. **Pandas 的运算是按索引对齐的**（不是按位置）——这是与 NumPy 最本质的差别；
2. **对齐取并集，缺失处为 `NaN`**，于是整型列会被提升为 `float64`。

补充两个常被追问的点：

- *「`None` 和 `NaN` 有什么区别？」* → `None` 是 Python 对象（`object` dtype），
  `NaN` 是浮点缺失值（`float64`）。构造 Series 时 Pandas 会把 `None` 尽量转成 `NaN`，
  但一旦列里混入其它对象类型，整列就退化为 `object`。
- *「怎么避免整数列变浮点？」* → 用 **Nullable dtype**，
  如 `pd.array([1, None], dtype="Int64")`（注意大写 `I`）。

---

## 4. 常用构造与查看

| 操作 | 写法 | 说明 |
|---|---|---|
| 从字典构造 | `pd.DataFrame({...})` | 键是列名，值为列数据 |
| 从记录列表 | `pd.DataFrame([{...}, {...}])` | 每条记录一个 dict |
| 从二维数组 | `pd.DataFrame(arr, columns=[...], index=[...])` | 必须显式给列名，否则是 `0..n-1` |
| 看结构 | `df.info()` | 列名、非空计数、dtype、内存 |
| 看数值分布 | `df.describe()` | 只统计数值列（`include="all"` 可含类别列） |
| 看前/后几行 | `df.head(3)` / `df.tail(3)` | 注意 `head` 返回的是**视图还是副本**并不保证 |
| 看维度 | `df.shape` / `df.dtypes` / `df.columns` | 这三个是排查时的第一手信息 |
| 看有无重复索引 | `df.index.has_duplicates` | **对齐前必查** |

**一个容易忽略的细节**：`pd.DataFrame(arr)` 从 NumPy 数组构造时，
**列名默认是整数 `0..n-1`**，不是 `"col0"` 之类。
所以 `df["price"]` 会报 `KeyError: 'price'`，必须显式传 `columns=`。
