# 01 · EXPLAIN 输出解读：type、key、rows 与 Extra

## 一、EXPLAIN 的每一列在说什么

```
+----+-------------+-------+------+---------------+---------+---------+-------+------+-----------------------+
| id | select_type | table | type | possible_keys | key     | key_len | ref   | rows | Extra                 |
+----+-------------+-------+------+---------------+---------+---------+-------+------+-----------------------+
|  1 | SIMPLE      | o     | ref  | idx_user_id   | idx_uid | 8       | const |   12 | Using index condition |
+----+-------------+-------+------+---------------+---------+---------+-------+------+-----------------------+
```

| 列 | 含义 | 关键判读 |
|---|---|---|
| `id` | 查询序号 | 越大越先执行；相同则从上到下执行 |
| `select_type` | 查询类型 | `SIMPLE` / `PRIMARY` / `SUBQUERY` / `DERIVED` / `UNION` |
| `table` | 正在访问的表 | — |
| **`type`** | **访问类型（最重要）** | 优劣阶梯见下节 |
| `possible_keys` | 理论上可用的索引 | 为 `NULL` 说明**没有可用索引** |
| **`key`** | **实际选中的索引** | 为 `NULL` 说明**没走索引**（应重点排查） |
| `key_len` | 索引被使用的字节数 | 可反推**用到几列**（联合索引的关键线索） |
| `ref` | 与索引比较的对象 | `const` / 列名 / `func` |
| `rows` | **估算**扫描行数 | 是估值，不是精确值；优化器用统计信息推算 |
| `filtered` | 过滤后剩余百分比 | 与 `rows` 相乘可估最终结果行数 |
| **`Extra`** | **补充信息（第二重要）** | 见下文 |

**`key_len` 的算法**（`utf8mb4` 下）：`int` = 4 字节；`bigint` = 8；`datetime` = 5~8；
`varchar(n)` = `4n + 2`（可变长 + 长度前缀）；`char(n)` = `4n`；
**可为 NULL 的列额外 +1 字节**。例：`KEY(a int NOT NULL, b varchar(20))`，
若 `key_len = 4` 说明只用到 `a`，若为 `4 + 82 = 86` 才说明两列都用上了。

## 二、type 的优劣阶梯（面试必背）

```
system > const > eq_ref > ref > fulltext > ref_or_null > index_merge
       > unique_subquery > index_subquery > range > index > ALL
```

| type | 含义 | 例子 | 评价 |
|---|---|---|---|
| `system` | 表只有一行 | 系统表 | 最好（几乎不出现） |
| `const` | 主键/唯一索引等值命中**至多一行** | `WHERE id = 1` | 极好 |
| `eq_ref` | 连接中**被驱动表**用主键/唯一索引等值匹配 | `ON a.id = b.id` | 很好 |
| `ref` | 非唯一索引等值匹配（可能多行） | `WHERE user_id = 5` | 好 |
| `range` | 索引范围扫描 | `WHERE id BETWEEN 1 AND 100`、`> <`、`IN` | 尚可 |
| `index` | **全索引扫描**（扫整棵索引树，不回表但仍是全扫） | 覆盖索引全扫 | 偏差 |
| **`ALL`** | **全表扫描** | 无索引或无可用索引 | 最差，必须整改 |

**判据**：线上核心 SQL 的 `type` **至少要达到 `range`**，单点查询必须到 `ref` 及以上；
出现 `index` 或 `ALL` 且 `rows` 很大时，就是优化目标。

## 三、Extra 的关键信号

| Extra 值 | 含义 | 态度 |
|---|---|---|
| `Using index` | **覆盖索引**：只读索引就够，**不回表** | 最优信号 |
| `Using index condition` | **索引下推（ICP）**：过滤条件下推到存储引擎层 | 好，减少回表 |
| `Using where` | Server 层再做过滤（索引没能完全过滤） | 中性，看 `filtered` |
| `Using filesort` | 排序无法利用索引有序性，需额外排序 | **关注**：小结果集可容忍 |
| `Using temporary` | 用了临时表（常见于 `GROUP BY` / `DISTINCT` / `UNION`） | **关注**：大表上代价高 |
| `Using join buffer` | 被驱动表没走索引，用了连接缓冲（BNL/哈希连接） | **警告**：被驱动表该加索引 |
| `Using MRR` | 多范围读，把随机 IO 合并成顺序 IO | 好 |

## 四、rows 与 filtered 是「估算」，不是事实

优化器靠**统计信息**（索引基数 `cardinality`、数据分布直方图）估算代价。
因此会出现「`rows` 估 10 实际扫 100 万」的情况，常见原因：
- 统计信息过期（大量增删改后未更新）→ `ANALYZE TABLE t;`
- 数据分布倾斜严重（如 99% 的行 `status = 0`）→ 直方图能改善
- 条件里有函数或隐式转换，优化器无法估算选择性

**`rows × filtered / 100`** 才是估算的最终行数；只看 `rows` 会误判。
当优化器选错索引（明明有更好的索引却选了差的），可以用 `FORCE INDEX` 强制，
但那是**症状治疗**，根因通常是统计信息不准或查询写法让代价估算失真。

## 五、更细的观察手段

```sql
EXPLAIN FORMAT=JSON SELECT ...;          -- 结构化输出，含 cost_info
EXPLAIN ANALYZE SELECT ...;              -- 8.0.18+，实际执行并给出真实耗时与行数
EXPLAIN FOR CONNECTION <id>;             -- 看正在运行的连接的执行计划
SHOW STATUS LIKE 'Last_query_cost';      -- 上一条查询的估算代价
```

`EXPLAIN ANALYZE` 的价值在于**对照**：把「估算 rows」与「实际 rows」并排看，
差异巨大处就是优化器判断失误的地方。

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
标准排查动作：先 `EXPLAIN` 看 `type` 与 `key`，再看 `Extra`，最后看 `rows`。
**三步定位法**：
① `key = NULL` → 索引没被用上 → 去查失效场景（函数包裹、类型隐式转换、前导 `%`、`OR`）；
② `key` 有值但 `type = ALL` → 说明选错了/索引选择性太差 → 看 `cardinality`；
③ `Extra` 有 `filesort` / `temporary` → 排序分组没吃到索引有序性 → 考虑调整索引列顺序或改写。
`rows` 只是估算，**不要用它做容量规划**；要真实数据就上 `EXPLAIN ANALYZE`。
上线前把核心 SQL 的 `EXPLAIN` 结果贴进评审记录——这是最便宜的性能回归防护。

### 🎓 博士生视角
`EXPLAIN` 暴露的是**优化器的代价模型选择结果**。代价模型的核心是
**代价 = 磁盘 I/O 次数 × 单位代价 + CPU 代价**，其中随机 I/O 的权重远高于顺序 I/O
（InnoDB 默认 `innodb_flush_neighbors`/预读策略下顺序读更便宜）。这解释了几件事：
为什么「回表」的代价要用随机 I/O 系数折算；为什么覆盖索引（`Using index`）几乎总是更优——
它把随机 I/O 变成了顺序扫索引。
`type` 阶梯本质是**访问路径的枚举与代价比较**：优化器在
「全表扫描 / 走二级索引 + 回表 / 走覆盖索引 / 范围扫描 / 索引合并」等候选路径中取估算代价最小者，
因此**它可能选错**——代价估算是近似，且依赖统计信息。
`Using filesort` 的代价是 O(n log n) 比较加可能的磁盘落盘（`sort_buffer_size` 不足时用磁盘归并）；
`Using temporary` 则是构造中间结果集，常见于无法利用索引有序性完成的 `GROUP BY`。
从数据库理论视角，这些都属于**查询处理（query processing）** 阶段的物理算子选择问题，
与《数据库系统概念》第 13 章的「选择运算实现的代价比较」是一回事。

### 📚 考研者视角
高频口径，逐条背：
- **`type` 优劣阶梯（必背顺序）**：`system > const > eq_ref > ref > range > index > ALL`。
  常考「哪些 type 算好」→ `ref` 及以上；「`index` 和 `ALL` 哪个好」→ `index`（只扫索引树，不回表），
  但它仍是**全扫**，只是扫的对象不同。
- **`key = NULL` 与 `possible_keys = NULL` 的区别**：前者是「没走索引」，后者是「压根没有可用索引」。
- **`key_len` 能反推用了几列** —— 联合索引最左前缀的实际验证手段。
- **`Using index` 是覆盖索引（好），`Using filesort` 是额外排序（坏）**，`Using temporary` 用了临时表（坏）。
- **`rows` 是估算值**，这一点常作为判断题陷阱（「`rows` 表示实际扫描行数」→ 错）。
- **`EXPLAIN` 不会真正执行 SQL**（`EXPLAIN ANALYZE` 才会）。
- 索引失效经典场景：对索引列使用函数、隐式类型转换（字符串列传数字）、
  `LIKE '%x'` 前导模糊、`OR` 连接非索引列、违反最左前缀。
- **`ORDER BY` 想用索引有序性，必须满足**：排序顺序与索引顺序一致、且 `WHERE` 也符合最左前缀。
