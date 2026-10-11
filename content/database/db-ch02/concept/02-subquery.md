# 02 · 子查询：分类、相关 vs 非相关，与 MySQL 的优化

> 子查询是"把查询结果当值/集合/表再用"的能力。博士看语义（标量/表/存在量词），程序员看执行计划（物化/半连接）。

## 1. 理论根基：子查询的四种形态

| 形态 | 返回 | 出现位置 | 例子 |
|---|---|---|---|
| 标量子查询 | 单个值 | `SELECT`/`WHERE`/`SET` | `WHERE salary > (SELECT AVG(salary) FROM emp)` |
| 列子查询 | 一列多行 | `WHERE col IN (...)` | `WHERE dept_id IN (SELECT id FROM dept WHERE loc='BJ')` |
| 行子查询 | 一行多列 | `WHERE (a,b) = (SELECT ...)` | `WHERE (dept_id,salary) = (SELECT ...)` |
| 表子查询（派生表） | 一张表 | `FROM` 子句 | `FROM (SELECT ... ) t` |

**相关子查询（Correlated Subquery）**：内层引用了外层表的列，内层对外层每一行都要**重新执行一次**（行数级 O(M·N) 执行）；**非相关子查询**：内层独立，只算一次。

## 2. 实现机制：MySQL 如何"拆掉"子查询

现代优化器会尽量避免"逐行执行相关子查询"，手段：
- **子查询物化（Materialization）**：把非相关子查询的结果物化成一张临时表并建立哈希索引，外层直接探测 → 从 O(M·N) 降到接近 `O(M+N)`。
- **半连接（Semi-Join）**：针对 `WHERE col IN (SELECT ...)` / `EXISTS`，优化器把它**重写成 JOIN**（"只要存在即返回，不去重也不展开成多行"）。Semi-join 有 5 种策略：`DuplicateWeedout`、`FirstMatch`、`LooseScan`、`MaterializedScan`、`MaterializedLookup`。这是 `IN` 子查询常常比手写 `JOIN` 还快的原因。
- **反连接（Anti-Join）**：针对 `NOT IN` / `NOT EXISTS` / `LEFT JOIN ... IS NULL`，优化器用同样的"存在性"语义去重，避免对每行做子查询。
- **派生表合并（Derived Merge）**：当派生表简单（无 `GROUP BY`/`DISTINCT`/`LIMIT` 等）时，优化器把派生表"内联"进外层查询，避免物化临时表；否则物化为临时表（`EXPLAIN` 出现 `DERIVED` 行）。

## 3. `IN` vs `EXISTS`：别再背"小表用 IN、大表用 EXISTS"

老经验说"外表大用 EXISTS、内表大用 IN"，但在 **MySQL 5.6+ 有 semi-join 优化后**，优化器会把两者都转成等价的 semi-join 执行，**性能差异通常可忽略**。真正要警惕的是：

- **`NOT IN (子查询)` 的 NULL 陷阱**：若子查询返回值里**含 `NULL`**，整个 `NOT IN` 表达式结果变为 `UNKNOWN`，查询返回**空集**。`NOT EXISTS` 不受此影响（它只看"是否存在行"，NULL 行只是不匹配）。所以"找 A 中不在 B 里的行"用 `NOT EXISTS` 或 `LEFT JOIN ... IS NULL` 更安全。
- **`IN` 列表过长**：`col IN (1,2,3,...,10000)` 超过 `range_optimizer_max_mem_size` 会被优化器放弃，退化成全表。

## 4. 工程实践

- 能写成 JOIN 的，优先写 JOIN（语义更直观、优化器选择更多）；但 `IN`/`EXISTS` 在"存在性判断"上可读性更好，**不必强行改 JOIN**。
- 派生表（FROM 子查询）只保留必要列，避免物化出巨大临时表。
- 相关子查询写在 `SELECT` 列表会产生"对外表每行执行一次"的 N+1 行为，批查询应改用 `JOIN` + 聚合。

## 5. 可运行代码

见 `examples/ex04-scalar-subquery.json`（标量子查询）、`examples/ex05-in-subquery.json`（IN 子查询 + semi-join）、`examples/ex06-exists-anti.json`（EXISTS / NOT EXISTS）、`examples/ex07-derived-table.json`（派生表）、`examples/ex08-not-in-null.json`（NOT IN 的 NULL 陷阱）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **相关子查询对每一行执行一次**，是性能黑洞；能改写成 JOIN 或 `EXISTS` 就改写。用 `EXPLAIN` 看是否出现 `DEPENDENT SUBQUERY`。
- 经典坑：`WHERE x NOT IN (SELECT y FROM t)` —— 若子查询结果含 NULL，整体**恒为空**。要么 `WHERE y IS NOT NULL`，要么改 `NOT EXISTS`。
- 选择建议：`EXISTS` 对「存在性判断 + 大表」更优；`IN` 对「小结果集」更直观。

### 🎓 博士生视角
- 相关子查询与非相关子查询的**执行模型不同**：非相关可一次性求值并物化；相关必须按外层行逐次求值（除非优化器做「相关子查询去相关化」）。
- MySQL 会把 `IN` 子查询**物化并转成半连接（semijoin）**来优化，而 `NOT IN` / `NOT EXISTS` 难以同样优化（反连接），这是二者性能差异的来源。
- `NULL` 的三值逻辑让 `NOT IN` 的反直觉行为成为**语义层面的必然**：`x NOT IN (a, NULL)` 等价于 `x<>a AND x<>NULL`，后半永远 UNKNOWN，故整体不为 TRUE。

### 📚 考研者视角
- 自命题常考：**子查询与 `EXISTS` / `ANY` / `ALL` 的等价改写**，以及「相关子查询」与「非相关子查询」的区分。
- 对应关系代数：`IN` ↔ 半连接、`NOT IN` ↔ 反连接（差运算）。
- 记忆锚点：**`NOT IN` 的子查询里出现 NULL，结果必为空**——这是选择题与生产事故的双料高频点。
