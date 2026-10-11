# 03 · 集合操作：UNION / INTERSECT / EXCEPT

> 关系代数里的 ∪（并）、∩（交）、−（差）。博士看"多重集语义"，程序员看"去重是否触发排序"。

## 1. 理论根基：多重集（Multiset）语义

SQL 表是**多重集**（允许重复行），集合操作默认带 `DISTINCT` 去重：
- `UNION` = 去重并集；`UNION ALL` = 不去重并集（纯拼接）。
- `INTERSECT` = 交集；`EXCEPT`（MySQL 中等价于 `MINUS`/MariaDB 的 `EXCEPT`）= 差集。
- **版本注意**：MySQL 在 **8.0.31 之前不支持 `INTERSECT` / `EXCEPT`**，只能用 `JOIN` / `IN` / `EXISTS` 改写；8.0.31+ 才原生支持。写示例时若面向老版本需改写。

## 2. 实现机制：去重为什么慢

`UNION`（带去重）的实现是：把两结果集**合并后做一次 `filesort`（或哈希去重）**，复杂度 `O((m+n) log(m+n))`。`UNION ALL` 只是把两游标顺序输出，**O(m+n)**，无排序、无临时表。

所以经验法则：**能用 `UNION ALL` 就别用 `UNION`**——尤其当你**确定两结果集不会重叠**（例如按互斥条件拆分：`WHERE status='A'` UNION ALL `WHERE status='B'`），去重纯属浪费。

## 3. 等价改写（程序员必会）

- `A INTERSECT B` ≈ `SELECT * FROM A WHERE EXISTS (SELECT 1 FROM B WHERE B.k = A.k)` 或 `INNER JOIN ... GROUP BY` 去重。
- `A EXCEPT B` ≈ `SELECT * FROM A WHERE NOT EXISTS (SELECT 1 FROM B WHERE B.k = A.k)` 或 `LEFT JOIN B ON ... WHERE B.k IS NULL`。

注意：`UNION` 要求**列数相同、对应列类型兼容**；结果列名取**第一个 SELECT** 的列名。

## 4. 工程实践与坑

- `ORDER BY` 只能出现在整个 `UNION` 之后，且只能引用"第一个 SELECT 的列名或别名"，不能引用后续 SELECT 的私有列（除非用派生表包一层）。
- 每个分支的 `WHERE` 过滤要写在各自分支里；写在最外层只过滤"合并之后"的结果。
- 分页 `LIMIT` 若想"每个分支取前 N 再合并"，必须给每个分支加 `LIMIT`，否则先合并再去重再 LIMIT，语义和数据量都不同。

## 5. 可运行代码

见 `examples/ex09-union-all.json`、`examples/ex10-union-dedup.json`、`examples/ex12-intersect-except.json`（演示 8.0.31+ 原生写法与低版本 JOIN 改写）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **能不去重就用 `UNION ALL`**：`UNION` 要隐式排序/哈希去重，代价显著；统计总量、日志合并场景优先 `UNION ALL`。
- MySQL 直到 **8.0.31** 才有原生 `INTERSECT` / `EXCEPT`，更早版本只能用 `JOIN` / `NOT EXISTS` 模拟——升级或跨库迁移时要留意。
- 列数、列类型必须一致，列名取第一个查询的——这是常见报错来源。

### 🎓 博士生视角
- 集合语义要求**去重**，去重需要排序或哈希：这就是 `UNION` 慢的本质，与算法层的排序/哈希去重完全对应。
- SQL 默认是**多重集（bag）**语义，`DISTINCT` / `UNION` 才把结果拉回集合语义；而关系代数默认集合语义——这一差异是「SQL 不是纯关系代数」的核心例证。
- 从类型论看，集合运算要求两操作数**类型兼容**（并集要求同一「域」），这也是列数/列类型必须一致的数学理由。

### 📚 考研者视角
- 与关系代数的**并（∪）、差（−）、交（∩）**一一对应，答题时能把 `UNION/EXCEPT/INTERSECT` 映射回关系代数符号会加分。
- 常考：用关系代数表达「查询 A 但不属于 B 的元组」（差运算），以及由此改写成 SQL。
- 记忆锚点：**`UNION` 去重、`UNION ALL` 不去重**；**关系代数默认集合语义、SQL 默认多重集语义**。
