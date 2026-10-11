# 03 · 慢查询定位与 SQL 改写实战

## 一、先把慢 SQL 找出来

```sql
SHOW VARIABLES LIKE 'slow_query_log';          -- 是否开启
SHOW VARIABLES LIKE 'long_query_time';         -- 阈值（秒），默认 10
SHOW VARIABLES LIKE 'log_queries_not_using_indexes';

SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;                -- 生产建议 0.5~1s
SET GLOBAL log_queries_not_using_indexes = ON; -- 记录未走索引的查询（日志量大，谨慎）
```

日志是纯文本，用 `mysqldumpslow -s t -t 10 slow.log` 排序取 Top10，
或用 `pt-query-digest` 做**指纹聚合**（把字面值归一化成 `?` 后分组统计）。
**聚合才有意义**：单条 `WHERE id = 123` 慢不可怕，
可怕的是「同一种写法每分钟跑 5000 次」。

## 二、深分页：`LIMIT offset, n` 的线性代价

```sql
SELECT * FROM orders ORDER BY id LIMIT 1000000, 20;
```

MySQL 必须**先扫描并丢弃前 1000000 行**才能返回 20 行——代价随 `offset` 线性增长。
`EXPLAIN` 里看不出这一点（它显示的是排序后的计划），**要靠 `rows` 与业务量判断**。

**改写 ①：延迟关联**（先只用索引取主键，再回表取数据）

```sql
SELECT o.* FROM orders o
JOIN (SELECT id FROM orders ORDER BY id LIMIT 1000000, 20) t ON o.id = t.id;
```

内层子查询**只扫索引**（若 `ORDER BY` 列上有索引则是覆盖扫描），
外层只回表 20 行。前提：`ORDER BY` 的列有索引，且能覆盖到主键。

**改写 ②：游标法（keyset pagination）**

```sql
SELECT * FROM orders WHERE id > :last_id ORDER BY id LIMIT 20;
```

彻底避免 `offset`，代价恒定。**前提**：必须有唯一且单调的排序列（`id`、创建时间），
且业务允许「不能跳页」。

## 三、JOIN 优化：小表驱动大表

**原理**：嵌套循环连接的代价 ≈ `驱动表行数 × 被驱动表每次查找的代价`。
因此 **驱动表（外层循环）行数越少越好**，且**被驱动表的关联列必须有索引**
（否则每次查找都全表扫，退化为 `Using join buffer`）。

```sql
-- 假设 dept 只有 10 行，emp 有 100 万行
SELECT * FROM dept d JOIN emp e ON e.dept_id = d.id;
-- 优化器会选 dept 作驱动表：10 次外层 × 每次走 e.dept_id 索引
-- 若反过来以 emp 驱动：100 万次外层 × 每次查 dept（无索引则全扫）→ 灾难
```

**观察点**：`EXPLAIN` 中 `Using join buffer (Block Nested Loop)` 意味着
被驱动表**没走索引**，MySQL 不得不把驱动表的结果集缓存起来做块嵌套循环。
看到它就该给被驱动表的关联列加索引。

**`STRAIGHT_JOIN`** 可强制驱动顺序（`FROM a STRAIGHT_JOIN b` 表示强制 `a` 为驱动表），
仅在优化器明显选错时使用——它是症状治疗，不是常规手段。

## 四、子查询 vs JOIN

- `IN (SELECT ...)` 在 5.6+ 常被优化器**半连接（semi-join）改写**为 JOIN，多数情况下不慢。
- **派生表（`FROM (SELECT ...) t`）可能被物化**，导致中间结果集落地；
  MySQL 5.7+ 支持**派生表合并**（`derived_merge`），但含 `GROUP BY`/`LIMIT`/聚合时无法合并。
- `EXISTS` 与 `IN` 的选择：**外表小用 `IN`，内表小用 `EXISTS`**——本质还是「少的那边驱动」。

## 五、排序与分组：消灭 filesort 与 temporary

**`ORDER BY` 能用索引有序性消除 `filesort` 的条件**：
1. `ORDER BY` 的列顺序与索引顺序**一致**（或完全相反，可反向扫）；
2. 排序方向一致（不能 `a ASC, b DESC` 混用，除非 8.0 的降序索引）；
3. `WHERE` 也符合最左前缀（否则索引无法用来排序）。

```sql
-- 索引 KEY idx(a, b)
SELECT * FROM t WHERE a = 1 ORDER BY b;        -- 可消除 filesort
SELECT * FROM t WHERE b = 1 ORDER BY a;        -- 需要 filesort（缺左前缀 a）
SELECT * FROM t ORDER BY a, b DESC;            -- 需要 filesort（方向不一致）
```

**`GROUP BY` 的优化**：`GROUP BY` 隐含排序（MySQL 8.0 前），
若 `GROUP BY` 的列能用索引有序性，则可同时消除 `temporary` 与 `filesort`；
否则会出现 `Using temporary; Using filesort` 组合——这是最需要警惕的信号。

## 六、其他高频改写

| 慢写法 | 快写法 | 原因 |
|---|---|---|
| `SELECT *` | 只取需要的列 | 减少回表、可能命中覆盖索引、减少网络传输 |
| `COUNT(*)` 全表 | 维护计数表 / 用近似值 | InnoDB 的 `COUNT(*)` 需要遍历索引 |
| 逐条 `INSERT` | 批量 `INSERT ... VALUES (...),(...)` | 减少网络往返与事务开销 |
| `UNION` | `UNION ALL`（若无需去重） | `UNION` 隐含去重（可能用临时表） |
| `UPDATE ... WHERE a=1 OR b=2` | 拆成两条或加索引 | 与索引失效同因 |
| 大事务里做 DDL/长查询 | 拆分事务 | 减少锁持有时间与 undo 膨胀 |

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
深分页的两种改写各有硬前提，**选错会白忙**：延迟关联要求 `ORDER BY` 列上有索引
（否则内层子查询自己就要 filesort）；游标法要求排序列唯一且单调，且产品上能接受「不能跳页」。
很多系统最后选的是「**限制最大页数**」这个最朴素也最有效的方案——
第 1000 页之后的访问占比通常极低，直接拒绝比优化更划算。
JOIN 的实操要点：**先看 `EXPLAIN` 里被驱动表的 `type`**，
出现 `ALL` 或 `Using join buffer` 就补索引，这一条能解决大部分 JOIN 慢查询。
另外，把 `long_query_time` 调到 1 秒并开启慢日志，是**投入产出比最高**的运维动作。

### 🎓 博士生视角
深分页的线性代价来自**「扫描-丢弃」模型**：`LIMIT offset, n` 的语义要求定位到第 `offset+1` 行，
而 B+ 树只提供按序遍历、不提供「第 k 行」的 O(log n) 定位（除非用序号列做键）。
因此代价 Θ(offset + n) 是**语义决定的**，不是实现缺陷——这也是延迟关联能奏效的原因：
它把「取数据」与「跳过」解耦，让跳过只发生在**索引层**（页密度高，同一次 I/O 覆盖更多行）。
游标法把 Θ(offset) 降为 Θ(1)，代价是需要一个**全序键**——这与分布式系统里
「基于游标的分页（cursor-based pagination）」是同一思想，也是它比 offset 分页更适合
一致快照读的原因（offset 分页在并发写入下会出现**行漂移**）。
`Using join buffer` 对应块嵌套循环（BNL）算法：代价从
`|R| × log|S|`（有索引）退化为 `|R| × |S| / B`（无索引，`B` 为缓冲区页数），
量级完全不同——这就是「被驱动表必须有索引」的形式化依据。

### 📚 考研者视角
- **深分页为什么慢？** 因为要**先扫描并丢弃**前 `offset` 行，代价随 `offset` 线性增长；
  优化手段：**延迟关联**（子查询只取主键）与**游标法**（`WHERE id > last_id`）。
  这两个名字是固定考点。
- **小表驱动大表**的原理：嵌套循环连接的外层次数决定总代价；
  并记住「**被驱动表的关联列必须有索引**」，否则退化为块嵌套循环。
- **`ORDER BY` 用不上索引的三种情况**：不满足最左前缀、排序方向不一致、排序列与索引列顺序不一致。
- **`GROUP BY` 与 `ORDER BY` 的关系**：MySQL 8.0 之前 `GROUP BY` 隐含排序（8.0 起默认不再隐含），
  因此旧版本里 `GROUP BY` 常伴随 `Using filesort`。
- **`UNION` 与 `UNION ALL`**：`UNION` 会去重（可能用临时表），`UNION ALL` 不去重、更快；
  明确无需去重时必须写 `UNION ALL`。
- **`COUNT(*)` / `COUNT(1)` / `COUNT(列)`**：前两者等价（都统计行数），
  `COUNT(列)` 会**跳过该列为 NULL 的行**——这是固定辨析题。
- **`IN` 与 `EXISTS`**：外表小用 `IN`，内表小用 `EXISTS`（本质仍是少的一边驱动）。
