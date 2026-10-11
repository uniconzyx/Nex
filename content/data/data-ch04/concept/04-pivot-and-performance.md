# 透视表、重塑与性能：apply 到底慢在哪

## 1. pivot_table：带默认聚合的 groupby

**透视表的本质**：把「两个分组键」分别铺到**行方向和列方向**。

```python
df.pivot_table(index="city", columns="month", values="sales",
               aggfunc="sum", fill_value=0)
```

等价于「`groupby(["city","month"])` 之后再 `unstack()`」：

```python
df.groupby(["city", "month"])["sales"].sum().unstack(fill_value=0)
```

**记住这条等价关系，就不用再单独背 `pivot_table` 的参数**——
`index` → 分组键之一，`columns` → 另一个分组键，`values` → 聚合列，
`aggfunc` → 聚合函数，`fill_value` → `unstack` 后的填充。

**默认 `aggfunc="mean"`**（不是 sum），这是最容易搞错的一处。

`crosstab` 是 `pivot_table` 的特例——**只做频次统计**：

```python
pd.crosstab(df["city"], df["month"])                       # 计数
pd.crosstab(df["city"], df["month"], normalize="index")    # 行百分比
```

## 2. 重塑：wide ↔ long

```python
wide = long.pivot(index="date", columns="item", values="qty")   # long → wide
long = wide.stack().rename("qty").reset_index()                 # wide → long
long = df.melt(id_vars=["date"], var_name="item", value_name="qty")   # 更通用
```

**`pivot` 与 `pivot_table` 的区别**（高频混淆点）：

| | `pivot` | `pivot_table` |
|---|---|---|
| 重复的 (index, columns) 组合 | **报错**（`ValueError: Index contains duplicate entries`） | 自动聚合 |
| 默认聚合 | 无 | `mean` |
| 用途 | 纯形状变换 | 统计汇总 |

一句话：**能保证唯一就用 `pivot`（更快、更严格），否则用 `pivot_table`。**

## 3. query / eval：让表达式跑得更快

```python
df.query("amount > 100 and city == 'BJ'")
df.eval("total = price * qty", inplace=False)
```

`query` 的优点有三层：

1. **可读性**：不用反复写 `df[...]`，链式条件更接近自然语言；
2. **少写中间变量**：`query("a > 1 and b < 2")` 不用为每个条件建临时 Series；
3. **可能更快**：numexpr 引擎下多条件布尔运算可避免为每个条件物化整列布尔数组。

对**跨列算术表达式**（如 `total = price * qty`）`eval` 的优势更明显。

## 4. apply vs 向量化：先量化，再优化

**规则**：能用内置向量化操作就别用 `apply`。但「慢多少」不该靠感觉，
应该**用可复现的判据**来验证：

```python
def has_promo(text):            # 逐行字符串判断
    return "PROMO" in text

# 写法 A：apply（Python 层逐行调用）
out_a = df["note"].apply(has_promo)

# 写法 B：向量化（C 层批处理）
out_b = df["note"].str.contains("PROMO", regex=False, na=False)

assert out_a.tolist() == out_b.tolist()      # 先确认两者语义一致
# 再比较：这里的正确判据是「是否走了同一套计算路径」，
# 而不是某个具体耗时——耗时随机器/负载波动，不可复现。
```

**为什么 `apply` 慢？** 因为它每行都要：

1. 把标量装箱成 Python 对象；
2. 调用一次 Python 函数（解释器开销）；
3. 把结果拆箱回数组。

向量化把这三步压到 **C 循环**里一次完成。差距的量级取决于
「每行的计算量」与「Python 调用开销」之比——计算越轻，`apply` 越吃亏。

**但 `apply` 不是原罪。** 下列场景它就是最优解：

- 组内需要**排序后取 top-k**（`groupby(...).apply`）；
- 逻辑依赖多个列且不可向量化（如调用外部 API、复杂状态机）；
- 一次性数据探索，**代码清晰度 > 性能**。

判据是：**这段代码在热路径上吗？** 不在热路径上，可读性优先。

## 5. 三视角：性能工程

### 🧑‍💻 程序员视角
**性能优化的正确顺序（不要跳步）：**

```
① 先测量：这段代码占总耗时多少？（不要优化不到 5% 的路径）
② 找瓶颈：是 IO（read_csv）、是 apply、还是 merge 的键 dtype？
③ 换实现：向量化 > 内置聚合 > apply
④ 再测量：确认真的变快了，且结果**逐元素一致**
```

**四条实战经验：**

1. **先 `astype` 再计算**：`category`/`int32` 的 join 与 groupby 显著快于 `object`；
2. **`merge` 前先 `usecols`**：只读需要的列，IO 常常才是真瓶颈；
3. **`apply` 返回标量时优先换 `agg`**（见 concept 01）；
4. **`query` 的列名含空格或特殊字符**会退化成 Python 引擎，速度优势消失。

**「快」的正确验证方式**：不要写 `耗时 12.3 ms` 进文档或期望输出。
应写**可复现的判据**：

```python
print("语义一致:", out_a.tolist() == out_b.tolist())
print("是否走了 C 层:", isinstance(df["note"].str.contains("X").dtype, type(df["note"].dtype)))
```

或者用**操作计数**（例如 `df["v"].apply` 的调用次数 == 行数）作为判据。
机器相关的墙钟耗时**永远不要**写进 `expected_output`——换台机器就失败。

### 🎓 博士生视角
**向量化为什么快：数据布局与调用开销。**

NumPy/Pandas 的向量化性能来自两点，且**必须同时成立**才算「真向量化」：

1. **内存布局连续**：`int64` 列在内存里是一段连续的 8 字节块，
   CPU 可以按 cache line 预取。相反，`object` 列存的是**指针数组**，
   每个元素指向堆上任意位置的 Python 对象——**指针追逐（pointer chasing）**
   会打爆 cache，这是 `object` 列慢的根本原因，而非「Python 慢」；
2. **循环在 C 层**：省掉了每次迭代的解释器分派（dispatch）与对象装箱。
   单次解释器迭代的开销约几十纳秒，而一次 SIMD 加法只需不到一纳秒。

**复杂度层面的差异**：设每行计算量为 $c$（若为常量则记为 $O(1)$），
解释器开销为常数 $k$（$k \gg c$）。

- 向量化：$T_V = n \cdot c$（C 循环，$c$ 极小）；
- `apply`：$T_A = n \cdot (k + c)$。

于是加速比 $T_A / T_V = 1 + k/c$。
**这解释了一个反直觉的现象**：如果每行的计算**本身很重**
（$c$ 很大，例如调用一次网络请求），那么 $k/c \to 0$，`apply` 的开销**可忽略**，
此时「优化掉 apply」几乎没有收益。这也是为什么性能分析**
必须先测量再优化**——不能只凭「apply 慢」这条教条下刀。

**分组聚合的代价模型**：哈希分组是 $O(n)$，
但 `apply` 要为 $|G|$ 个组各物化一次子 DataFrame，
额外开销 $O(n)$（复制数据）$+\ |G|$ 次 Python 调用。
当 $|G|$ 接近 $n$（近乎逐行处理）时，退化为 $O(n)$ 次解释器调用。

### 📚 考研者视角
**笔试/面试标准问法与易错口径：**

- *「`pivot` 和 `pivot_table` 的区别？」*
  → 核心是**重复组合**：`pivot` 遇重复直接报错，`pivot_table` 自动聚合；
  `pivot_table` 默认 `aggfunc="mean"`。三句话答全才算完整。
- *「`pivot_table` 和 `groupby` 什么关系？」*
  → `pivot_table` ≡ `groupby(keys).agg(f).unstack()`。
  **能主动指出这个等价关系是明显加分项**。
- *「`apply` 和 `map` 的区别？」*
  → `Series.map` 是**元素级**映射且支持字典查表；
  `Series.apply` 也是元素级但走 Python 调用；
  `DataFrame.apply` 默认**按列**（`axis=0`），`axis=1` 才按行。
  三者常被混为一谈，答对 axis 默认值是一个区分点。
- *「为什么向量化比 apply 快？」*
  → 标准答法要落到**两点**：内存连续（cache 友好）与循环在 C 层（无解释器分派）。
  只说「因为 NumPy 是 C 写的」不够。
- 易错口径：
  ① 认为 `pivot_table` 默认是 `sum`——错，是 `mean`；
  ② 认为 `df.apply(func)` 是按行——错，默认 `axis=0` 按列；
  ③ 把「向量化一定快」绝对化——每行计算很重时差距可忽略，需实测。


## 6. 陷阱速查

| 症状 | 真因 | 正确写法 |
|---|---|---|
| `pivot` 报 duplicate entries | (index, columns) 组合不唯一 | 改用 `pivot_table`，或先做聚合 |
| 透视结果比预期小/大 | 默认 `aggfunc="mean"` 而非 sum | 显式 `aggfunc="sum"` |
| `query` 用了列名带空格 | 退化为 Python 引擎 | 改列名或用 `df[...]` |
| `df.apply(f)` 结果形状不对 | 默认 `axis=0`（按列） | 需要按行则 `axis=1` |
| 优化后结果与原来不一致 | 向量化改动改变了语义 | **先断言逐元素相等**再比性能 |
| 文档里写了具体耗时 | 机器相关，不可复现 | 改布尔判据或操作计数 |
