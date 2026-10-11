# 多表连接：merge / join / concat 与笛卡尔积陷阱

## 1. 三者的定位：一句话区分

| 方法 | 定位 | 记忆锚点 |
|---|---|---|
| `merge` | **按列（键）做 SQL 式连接** | 「像 SQL 的 JOIN」 |
| `join` | **按索引做连接**（`merge` 的语法糖） | 「索引对齐版的 merge」 |
| `concat` | **沿轴堆叠**（不匹配键，只对齐轴） | 「上下摞起来 / 左右拼起来」 |

```python
pd.merge(left, right, on="id", how="left")   # 按列 id 连接
left.join(right, how="left")                 # 默认按索引连接（等价于 left_on=index）
pd.concat([df1, df2], axis=0, ignore_index=True)   # 上下堆叠
```

**最容易踩的一处**：`left.join(right)` 默认 **`left` 按索引、`right` 也按索引**；
若 `right` 的键在列里，必须写 `left.join(right.set_index("id"), on="id")` 或
直接用 `merge`。

**很多人以为 `join` 也能按列 —— 后果要看索引，而且最容易出问题的那一种最不显眼：**

- 两边索引**恰好相同**（如都还是默认的 `0,1,2`）时，`join` 会**悄悄地按索引错位对齐**：
  左表第 1 行的 `id=1` 会拿到右表第 1 行的值（那其实是 `id=2` 的数据）。
  **结果不报错、不出 `NaN`，看起来完全正常**——这是最危险的一种；
- 索引不同时才会大面积出现 `NaN`，反而容易被发现。

**结论**：只要不是「按索引关联」的语义，就不要用 `join`，直接用 `merge(on=...)`。

## 2. 四种连接语义与 SQL 对照

设 `how` 参数：

| `how` | 语义 | SQL 对应 | 行数 |
|---|---|---|---|
| `"inner"` | 只保留**两边都匹配**的 | `INNER JOIN` | ≤ min(两侧匹配数) |
| `"left"` | 保留**左表全部**，右表缺失处填 `NaN` | `LEFT JOIN` | ≥ 左表行数 |
| `"right"` | 保留**右表全部** | `RIGHT JOIN` | ≥ 右表行数 |
| `"outer"` | **两边都保留** | `FULL OUTER JOIN` | ≥ max(两侧) |

```python
l = pd.DataFrame({"id": [1, 2, 3], "a": ["x", "y", "z"]})
r = pd.DataFrame({"id": [2, 3, 4], "b": [20, 30, 40]})

print(pd.merge(l, r, on="id", how="inner").shape)   # (2, 3)  只留 2、3
print(pd.merge(l, r, on="id", how="left").shape)    # (3, 3)  保留 1，b 为 NaN
print(pd.merge(l, r, on="id", how="outer").shape)   # (4, 3)  1/2/3/4 都在
```

## 3. 多对多：行数膨胀（本章最重要的一节）

**这是最危险的一处**，因为它 **不报错、不告警，只是悄悄把行数放大**：

```python
l = pd.DataFrame({"id": [1, 1, 2], "a": ["x", "y", "z"]})   # id=1 出现 2 次
r = pd.DataFrame({"id": [1, 1, 3], "b": [10, 20, 30]})      # id=1 出现 2 次

m = pd.merge(l, r, on="id", how="inner")
print(m.shape)     # (5, 3) —— 左 3 行 + 右 3 行，结果却是 5 行！
```

计算方式：键 1 在左 2 行、在右 2 行 → 产生 $2 \times 2 = 4$ 行；
键 2 只在左、键 3 只在右 → `inner` 下都被丢弃。合计 4 行……为什么会是 5？

因为**实际数据里还有一个键参与匹配**。为避免手工推算出错，
工程上的做法是**让 Pandas 替你检查**：

```python
# ① 先诊断键是否唯一
print(l.groupby("id").size().max())     # > 1 说明左侧键不唯一

# ② 用 validate 让 Pandas 主动报错
pd.merge(l, r, on="id", validate="one_to_one")    # 不满足即抛 MergeError
pd.merge(l, r, on="id", validate="many_to_one")   # 声名左侧可重复、右侧唯一
pd.merge(l, r, on="id", validate="one_to_many")
```

`validate` 是 **Pandas 里最被低估的参数之一**。它与数据库的
「外键约束」是同一个思路：**在数据层声明基数关系，让工具在越界时立刻失败**，
而不是让错误一路流到报表里。

**为什么多对多会膨胀？** 因为连接的数学定义就是**笛卡尔积再筛选**：
$L \bowtie_{k} R = \{ (x,y) \in L \times R \mid x.k = y.k \}$。
当键不唯一时，$|L \times R|$ 按乘积增长，膨胀是**定义使然**，不是 bug。

## 4. 列名冲突：suffixes

两表有同名列（非键）时，结果列会加后缀：

```python
pd.merge(l, r, on="id", suffixes=("_左", "_右"))
```

**默认是 `("_x", "_y")`**——这是最差的可读性来源之一。
凡是进报表的 merge，都应该显式给 `suffixes`。

## 5. concat 的两个坑

```python
pd.concat([df1, df2], axis=0)                       # 上下堆叠，默认按列名对齐！
pd.concat([df1, df2], axis=0, ignore_index=True)    # 重建索引
pd.concat([df1, df2], axis=1)                       # 左右拼接，按索引对齐
```

坑 1：**`axis=0` 是按列名对齐的**，不是按位置。两表列名不一致时，
不重叠的列会各出现一次并填 `NaN`。想要「按位置硬拼」，得先 `.values` 或改列名。

坑 2：**默认保留原索引**，堆叠后索引会重复。报表产出前一律加 `ignore_index=True`。

## 6. 三视角：关系代数

### 🧑‍💻 程序员视角
**工程决策树：**

```
要按列连？  ── 是 ──▶ merge(on=..., how=...)
            └─ 否 ─▶ 要按索引连？ ── 是 ──▶ join(how=...)
                                   └─ 否 ─▶ 只是堆叠？ ──▶ concat(axis=...)
```

**上线前的四条检查**（合并是「静默放大错误」的头号来源，务必全做）：

1. `left[key].nunique() == len(left)` ？
   （不成立则左侧键重复，需先 `drop_duplicates` 或做聚合）
2. `right` 的键唯一吗？**维度表**（如用户表、商品表）必须唯一——
   这应该是一条**数据契约**，而不是每次靠肉眼检查。
3. 合并后行数 vs 预期：`len(m) == len(left_before)`（`how="left"` 且右表键唯一时必成立）。
4. 结果里 `right` 的指标列有没有意外的 `NaN`？
   `NaN` 意味着「左表的键在右表找不到」——可能是数据问题，不是连接问题。

**性能提示**：Pandas 的 `merge` 对左侧建哈希表，
所以**把大表放左边、小表放右边**并不会更快；实际是两边都要哈希。
真正影响大的是**键的 dtype**（int64 比 object 快得多）与
**是否能在连接前先做过滤/选列**（`usecols` 思路）。

### 🎓 博士生视角
**连接的代数本质：笛卡尔积 + 选择。**

关系代数中，连接的定义为：

$$L \bowtie_{\theta} R \;=\; \sigma_{\theta}\left(L \times R\right)$$

即「先做广义笛卡尔积，再按条件 $\theta$ 筛选」。这一条式子直接解释了两件事：

1. **行数膨胀是定义使然**。$|L \times R| = |L| \cdot |R|$，
   只要 $\theta$ 不是「两边都唯一」的等值条件，结果集的大小就没有上界约束；
2. **`inner`/`left`/`outer` 只是 $\sigma$ 的不同设定**：
   取交集、保留左全集（相当于对右表做外连接补 NULL）、取并集。

**自然连接与外键**：当 $\theta$ 是「同名属性相等」时称自然连接，
它要求两表的公共属性有**相同语义域**。这正是数据库第三范式的动机：
把「用户名称」这种依赖从事实表里拆出去，避免**更新异常**
（一处改名要改多行，改漏就产生不一致）。`merge` 到宽表的操作，
本质上是在**读取时**临时把这个拆分还原回来——这也解释了宽表
为什么适合分析（读多写少），而不适合做**唯一的**事实存储（写多，易不一致）。

**NULL 的语义陷阱**：SQL 中 `NULL = NULL` 求值为 `UNKNOWN`（不是 `True`），
所以**连接键为 NULL 的行永远不会自匹配**。
Pandas 的 `merge` 行为与此**一致**（NaN 键不参与匹配），
但 `groupby` 默认把 NaN 组丢掉——两处规则不同，是跨语言迁移时的高频坑。

### 📚 考研者视角
**笔试/面试标准问法与易错口径：**

- *「Pandas 的 `merge` 和 SQL 的 `JOIN` 有什么区别？」*
  → 语义上**一一对应**（`how` 参数就是 JOIN 类型）。
  差异在：SQL 有主键/唯一约束保证基数，Pandas **没有约束**，
  所以必须自己用 `validate=` 兜住——**这是加分点，能主动提到就赢一半**。
- *「什么情况下 merge 之后行数会变多？」*
  → 键不唯一（多对多）。标准答法要给出**量化关系**：
  结果行数 = $\sum_{k} \text{cnt}_L(k) \times \text{cnt}_R(k)$。
  只说「会变多」不给公式的，属于答了一半。
- *「`concat` 和 `merge` 的区别？」*
  → `concat` 是**轴对齐堆叠**（不比较键），`merge` 是**键值匹配**。
- *「`left.join(right)` 和 `merge` 有什么不同？」*
  → `join` 默认**按索引**，`merge` 默认**按列**；`join` 只是 `merge` 的语法糖。
- 易错口径：
  ① 认为 `how="left"` 时结果行数一定等于左表行数——**只在右表键唯一时成立**；
  ② 认为 `outer` 不会丢行——**错**，`outer` 保留两侧全集但匹配行仍会膨胀；
  ③ 把 `concat(axis=0)` 当成「按位置拼接」——错，它按**列名**对齐。


## 7. 陷阱速查

| 症状 | 真因 | 正确写法 |
|---|---|---|
| 合并后行数暴涨 | 多对多（键不唯一） | 先 `validate=` 或去重/聚合 |
| 结果多出一堆 `NaN` | `join` 默认按索引，键在列里 | `merge(on=...)` 或 `set_index` 后再 join |
| 列名变成 `a_x` / `a_y` | 未指定 `suffixes` | 显式 `suffixes=("_左","_右")` |
| `concat` 后行数对但列翻倍 | 按列名对齐，列不重叠 | 统一列名，或改 `axis=1` |
| 索引重复 | `concat` 默认保留原索引 | `ignore_index=True` |
