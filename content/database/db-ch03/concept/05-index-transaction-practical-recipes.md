# 索引与事务实战手记：凯喵从一条慢查询查到 MVCC 的十二个现场

> 这一章讲 B+ 树索引、覆盖索引与最左前缀、ACID 与隔离级别、redo/undo 与锁。概念在八股文里都有，但真到线上一查，坑全在「执行计划为什么没走索引」和「事务为什么没生效」这两类。这篇手记用十二个现场把这条链路走一遍。

## 开场：慢查询的归因顺序

凯喵的固定流程是四步，从不跳步：

1. **看执行计划**（`EXPLAIN`），确认走了什么索引、扫了多少行。
2. **看索引定义**，确认「该走的索引存在且可用」。
3. **看数据分布**，确认优化器选择是否合理（区分度、回表代价）。
4. **看锁与事务**，确认是不是被阻塞而不是真的慢。

跳步的代价是：直接去加索引、改 SQL，最后发现根因是锁等待。

### 现场一：`EXPLAIN` 的 `type` 全是 `ALL`，说明在扫全表

```sql
EXPLAIN SELECT * FROM orders WHERE user_id = 10086;
-- type: ALL, rows: 1200000, Extra: Using where
```

`type` 的执行效率排序（从好到差）：`system > const > eq_ref > ref > range > index > ALL`。

看到 `ALL` 就是全表扫。但**不要立刻加索引**——先看 `rows` 和 `filtered`：如果表只有 2000 行、查询又不频繁，全表扫反而是最优选择（优化器可能已经算过，加索引后回表的代价更大）。

加索引前必问：**这个条件的区分度是多少？** `WHERE status = 'paid'` 在 99% 都是 paid 的表上，索引几乎无效（要回表 99% 的行，不如顺序扫）。

### 现场二：给 `status` 建了索引，还是全表扫

```sql
CREATE INDEX idx_status ON orders(status);
EXPLAIN SELECT * FROM orders WHERE status = 'paid';
-- type: ALL   ← 加了索引还是不走
```

两个常见原因：

```sql
-- 原因一：区分度太低，优化器算出来走索引更贵
SELECT COUNT(DISTINCT status) / COUNT(*) FROM orders;   -- 0.02，几乎没区分度

-- 原因二：要回表的行太多，覆盖不到
-- 如果查的是 SELECT *，走二级索引要「先查索引拿主键，再回表拿整行」
-- 回表 90% 的行，成本高于顺序扫
```

解法：**要么改成覆盖索引**（把需要的列都放进索引），**要么建联合索引让区分度前置**：

```sql
-- 联合索引：区分度高的列在前
CREATE INDEX idx_user_status ON orders(user_id, status);
-- 现在 WHERE user_id=? AND status=? 的区分度是 user_id 贡献的，很有效
```

### 现场三：最左前缀被破坏，联合索引只用了一半

```sql
CREATE INDEX idx_abc ON t(a, b, c);

-- 有效：用上 a
SELECT * FROM t WHERE a = 1;
-- 有效：用上 a、b
SELECT * FROM t WHERE a = 1 AND b = 2;
-- 有效：用上 a、b、c
SELECT * FROM t WHERE a = 1 AND b = 2 AND c = 3;

-- 只用上 a：b 被跳过，c 无法使用
SELECT * FROM t WHERE a = 1 AND c = 3;

-- 完全用不上：缺最左列 a
SELECT * FROM t WHERE b = 2 AND c = 3;
```

记住这个比喻：**联合索引像电话簿按「姓、名」排序**——你能查「姓张」，也能查「姓张名三」，但查不了「名叫三的所有人」。

两个容易忽略的细节：

```sql
-- 范围查询会截断后续列
SELECT * FROM t WHERE a = 1 AND b > 2 AND c = 3;
-- a 用于定位，b 用于范围扫，c 无法用于索引定位（但可用于覆盖/ICP）

-- 排序也吃最左前缀
SELECT * FROM t WHERE a = 1 ORDER BY b, c;   -- 能用索引顺序，免排序
SELECT * FROM t WHERE a = 1 ORDER BY c;      -- 不能，会 filesort
```

### 现场四：在索引列上做运算，索引直接失效

```sql
-- 失效：函数包住列
SELECT * FROM orders WHERE DATE(created_at) = '2026-11-01';
-- 改成范围查询
SELECT * FROM orders WHERE created_at >= '2026-11-01' AND created_at < '2026-11-02';

-- 失效：隐式类型转换（user_id 是 varchar，传了数字）
SELECT * FROM users WHERE user_id = 10086;
-- 改成字符串
SELECT * FROM users WHERE user_id = '10086';

-- 失效：前导通配的 LIKE
SELECT * FROM users WHERE name LIKE '%kaimao%';   -- 无法用索引
SELECT * FROM users WHERE name LIKE 'kaimao%';    -- 可以用
```

这三条的共同本质是：**索引存的是列的原始值，一旦你对列做了变换，B+ 树的有序性就用不上了**。判断方法很简单——看 `WHERE` 里等号左边的列是不是「裸列」。

### 现场五：`SELECT *` 把覆盖索引变成回表

```sql
CREATE INDEX idx_user_time ON orders(user_id, created_at);

-- 需要回表：要拿 * 里的其他列
SELECT * FROM orders WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10;

-- 覆盖索引：只取索引里有的列，EXPLAIN 显示 Using index
SELECT user_id, created_at FROM orders WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10;
```

`Extra` 出现 `Using index` 就是覆盖索引——全程只在索引 B+ 树上走，不回表。这在分页场景下差异极大：回表 10 次和走索引 10 次，在千万级表上可能是 10ms 和 1ms 的区别。

实践技巧：**深分页先用覆盖索引拿主键，再回表取详情**：

```sql
-- 慢：LIMIT 1000000, 10 要扫描并丢弃 100 万行
SELECT * FROM orders ORDER BY id LIMIT 1000000, 10;

-- 快：先用覆盖索引定位主键，再关联取详情
SELECT o.* FROM orders o
JOIN (SELECT id FROM orders ORDER BY id LIMIT 1000000, 10) t USING (id);
```

### 现场六：以为「加了索引就一定快」，索引本身也有成本

一个表上建了 12 个索引，写入 QPS 一高就撑不住。原因：每次 `INSERT`/`UPDATE`/`DELETE` 都要维护所有相关索引的 B+ 树。

成本清单：

```text
写放大：一次 INSERT 可能触发多个索引页的分裂与写盘
空间：每个二级索引都存一份「索引列 + 主键」，宽表上很可观
优化器负担：索引太多时选错索引的概率上升
```

凯喵的清理标准：**连续 30 天没有被任何慢查询使用的索引，删掉**。MySQL 8.0 可以查：

```sql
SELECT * FROM sys.schema_unused_indexes;
SELECT * FROM sys.schema_redundant_indexes;   -- 找重复索引，比如 (a) 和 (a,b) 的前缀重复
```

### 现场七：`WHERE a=1 AND b=2` 建了 (a,b)，又建了 (b,a)，其实冗余

`(a,b)` 和 `(b,a)` 不是冗余（因为最左前缀不同）。真正冗余的是：

```sql
INDEX idx_a   (a)
INDEX idx_ab  (a, b)     -- idx_a 是 idx_ab 的前缀，完全冗余
```

`(a,b)` 已经能服务所有 `a` 上的查询，单独的 `(a)` 纯属浪费写入性能。清理时用 `sys.schema_redundant_indexes` 一眼就能看出来。

反之，`(a)` 和 `(b,a)` **不**冗余——因为 `(b,a)` 服务不了「只有 a」的查询（缺最左列 b）。

### 现场八：事务隔离级别记成「RR 完全无幻读」

标准 SQL 定义的四个级别：

```text
                脏读    不可重复读    幻读
READ UNCOMMITTED 可能    可能        可能
READ COMMITTED   不可能  可能        可能
REPEATABLE READ  不可能  不可能      可能（标准定义）
SERIALIZABLE     不可能  不可能      不可能
```

但 **InnoDB 的 RR 通过 MVCC + 间隙锁（next-key lock）在快照读下避免了大部分幻读**，所以很多资料说「InnoDB RR 没有幻读」。严格表述应该是：

- **快照读**（普通 `SELECT`）：靠 MVCC 一致性视图，看不到其他事务的新插入 → 无幻读。
- **当前读**（`SELECT ... FOR UPDATE`、`UPDATE`、`DELETE`）：靠 next-key lock 锁住间隙 → 也基本无幻读。
- **例外**：先快照读、再当前读的混合场景，可能出现「读到的行数变了」。

答题时写「InnoDB 在 RR 下通过 MVCC 与 next-key lock 基本消除了幻读，但标准定义中 RR 允许幻读」是最准确的。

### 现场九：MVCC 的 Read View 只创建一次，与 RC 的区别就在这

这是最高频的一道原理题。核心区别：

```text
RC（读已提交）：每次 SELECT 都新建一个 Read View
  → 所以能看到其他事务已提交的最新数据 → 不可重复读

RR（可重复读）：只在事务的第一次 SELECT 时创建 Read View，之后复用
  → 整个事务看到的是同一个快照 → 可重复读
```

Read View 的四个关键字段与可见性判断：

```text
m_ids          当前活跃（未提交）的事务 ID 列表
min_trx_id     m_ids 中的最小值
max_trx_id     下一个将分配的事务 ID
creator_trx_id 创建该 Read View 的事务 ID

判断某行版本（trx_id）是否可见：
  trx_id < min_trx_id      → 可见（事务已提交）
  trx_id >= max_trx_id     → 不可见（事务在快照之后才开始）
  min_trx_id <= trx_id < max_trx_id：
      在 m_ids 中            → 不可见（还活着）
      不在 m_ids 中          → 可见（已提交）
```

配合 undo log 的版本链（每行的 `DB_TRX_ID` + `DB_ROLL_PTR` 串起历史版本），就构成了「不阻塞读的一致性快照」。这套机制的代价是 undo log 会膨胀——长事务会阻止 purge，这是「为什么不能有长事务」的根本原因。

### 现场十：`UPDATE` 用了索引，反而更容易死锁

反直觉但真实：`UPDATE` 走索引时加的是**行锁 + 间隙锁**（next-key lock），锁的范围是「索引区间」；不走索引时是**全表扫描 + 锁所有行**（表级效果），反而「简单粗暴但不精细」。

死锁的经典场景：

```sql
-- 事务 A
BEGIN;
UPDATE t SET v = 1 WHERE id = 5;    -- 锁 id=5
UPDATE t SET v = 2 WHERE id = 9;    -- 等 id=9

-- 事务 B（同时）
BEGIN;
UPDATE t SET v = 3 WHERE id = 9;    -- 锁 id=9
UPDATE t SET v = 4 WHERE id = 5;    -- 等 id=5  ← 死锁
```

两个降低死锁概率的实践：

1. **按固定顺序加锁**（比如都按 id 升序更新）。
2. **缩短事务**（把非数据库操作移出事务，减少持锁时间）。

排查手段：

```sql
SHOW ENGINE INNODB STATUS;      -- 看 LATEST DETECTED DEADLOCK 段
SELECT * FROM performance_schema.data_locks;   -- 当前锁等待
SELECT * FROM sys.innodb_lock_waits;           -- 谁在等谁
```

### 现场十一：redo log 和 undo log 的作用记反了

这两个日志名字像，作用完全不同：

```text
redo log（重做日志）
  - 物理日志：记录「某页某偏移改成了什么」
  - 作用：崩溃恢复（crash-safe），保证已提交事务不丢
  - 循环写，空间固定（innodb_log_file_size）
  - 实现 WAL：先写日志再写数据页，把随机写变成顺序写

undo log（回滚日志）
  - 逻辑日志：记录「反向操作」（INSERT 记 DELETE，UPDATE 记旧值）
  - 作用：事务回滚 + MVCC 的版本链
  - 存放在 undo 表空间，由 purge 线程清理
```

一句话区分：**redo 保证「已提交的不丢」，undo 保证「未提交的可撤」**。

还有一条高频考点：**两阶段提交**。redo log 是 InnoDB 的，binlog 是 Server 层的，两者必须一致：

```text
1. 写 redo log，标记 prepare
2. 写 binlog
3. 写 redo log，标记 commit
崩溃恢复时：redo 是 prepare 且 binlog 完整 → 提交；否则回滚
```

这就是「为什么 redo log 要分 prepare/commit 两个阶段」——为了让两份日志达成一致。

### 现场十二：以为「事务里所有语句都回滚」，其实 DDL 会隐式提交

```sql
BEGIN;
INSERT INTO t VALUES (1);
ALTER TABLE t ADD COLUMN x INT;    -- DDL 会隐式提交前面的事务！
INSERT INTO t VALUES (2);
ROLLBACK;                          -- 只能回滚第 3 条，前面都已提交
```

MySQL 里 DDL（`CREATE`/`ALTER`/`DROP`/`TRUNCATE`）都会隐式提交当前事务。这是很多人「以为回滚了其实没回滚」的原因。

同类陷阱还有：

```sql
BEGIN;
SET autocommit = 1;      -- 隐式提交
LOCK TABLES ...;         -- 隐式提交
```

另一类更隐蔽的：**应用层的「事务没生效」**。比如 Spring 的 `@Transactional` 加在 private 方法上、或者在同一个类里自调用——代理没经过，注解形同虚设。这是从「SQL 层」跨到「框架层」的经典坑，排查时必须两边都看。

## 三视角解析
### 🧑‍💻 程序员视角
`EXPLAIN` 的 `type=ALL` 就是全表扫描，要结合 `rows` 与 `filtered` 判断代价。给 `status` 建索引还是全表扫，往往因为「区分度太低」——只有几种取值的列，优化器判断走索引不如全扫。联合索引的最左前缀被破坏（跳过第一列直接查第二列），索引用不上。在索引列上做运算（`WHERE YEAR(created_at) = 2026`）会让索引失效，应改成范围查询。

### 🎓 博士生视角
B+ 树的「矮胖」结构使「磁盘 IO 次数」稳定在 3~4 次，这是它优于二叉树与哈希的根本原因：二叉树的深度随数据量对数增长，哈希不支持范围查询与排序。聚簇索引（InnoDB）把数据行存在叶子节点，二级索引的叶子存主键，因此「二级索引查询」需要回表——覆盖索引可以避免这次回表。MVCC 用「版本链 + ReadView」实现「读不加锁」，其可见性规则由事务 ID 与快照决定，这是「可重复读」隔离级别的实现基础。

### 📚 考研者视角
数据库面试高频：
1. **索引结构**：B+ 树 vs B 树 vs 哈希，为什么 MySQL 用 B+ 树。
2. **索引失效**：函数运算、隐式类型转换、最左前缀、`LIKE '%x'`、`OR` 混用。
3. **事务隔离**：四个级别与脏读/不可重复读/幻读的对应，MVCC 与间隙锁的作用。
4. **锁**：共享锁/排他锁、行锁与表锁、死锁的排查（`SHOW ENGINE INNODB STATUS`）。

## 收尾：凯喵的索引与事务排查口诀

五句话应付大部分情况：

**先看计划再动手**——`EXPLAIN` 的 `type`/`rows`/`Extra` 三列先读一遍，别凭直觉加索引。

**左裸右值**——`WHERE` 等号左边的列必须是裸列；函数、运算、隐式转换都会让索引失效。

**最左前缀像电话簿**——查不了「名」也跳不过「姓」；范围条件会截断后续列。

**RC 每句一快照，RR 首句定终身**——Read View 的创建时机就是两个隔离级别的全部区别。

**redo 保已提交，undo 保可回滚**——再加一句「DDL 隐式提交」，事务相关的题基本不会错。

最后说一句方法上的话。索引和事务这两块，八股文能背出结论，但真正的能力在于**把现象对应到机制**：看到 `type: ALL` 能想到「区分度不足或回表太贵」；看到死锁能想到「next-key lock 的区间重叠」；看到「回滚没生效」能想到「隐式提交或代理失效」。

凯喵建议的练习方式是：**在自己的库上造这十二种现场**。建一张百万行的表，故意写 `WHERE DATE(col)=...` 看执行计划；故意开两个会话互相等锁看死锁日志；故意在事务里插一条 DDL 再回滚看数据还在不在。每种现象亲眼看一次，比读十遍结论都记得牢——因为这些机制的本质是「并发下的时序」，而时序只能通过观察建立直觉，无法通过阅读获得。
