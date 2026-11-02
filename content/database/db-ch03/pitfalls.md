# 本章避坑指南

1. **`SELECT *` + 二级索引必然回表，大结果集时优化器会放弃索引** —— 查询只需要少数列时却写 `SELECT *`，二级索引无法覆盖，每行都要回表；命中行数多时回表成本超过全表扫描，优化器反而选 `ALL`。正确写法：只查需要的列，或建**覆盖索引**（`Extra: Using index`）避免回表。

2. **违反最左前缀：跳列 / 前导通配 / 对列套函数，索引直接失效** —— 联合索引 `(a,b,c)`，写 `WHERE b=2`、`WHERE name LIKE '%明'`、`WHERE YEAR(created_at)=2023` 都让索引用不上（退化为全表扫）。正确写法：等值列放最左、范围列放中、用 `created_at BETWEEN ... AND ...` 替代函数包裹、前缀匹配才用 `LIKE '明%'`。

3. **隐式类型转换导致索引失效** —— `phone` 是 `VARCHAR`，却写 `WHERE phone=13800138000`（数字），MySQL 会对 `phone` 做隐式 `CAST`，等价于对列套函数 → 索引失效、全表扫。正确写法：`WHERE phone='13800138000'`（字符串加引号），并保证连接/比较两边类型一致。

4. **误以为 RR 完全无幻读：当前读仍可能看到"新插入行"** —— RR 下普通 `SELECT` 走快照读，看不到别的事务插入（似乎无幻读）；但 `SELECT ... FOR UPDATE` / `UPDATE` 是**当前读**，会看到已提交的新行。解决幻读靠 **Next-Key Lock**（锁住间隙阻止插入）；不要误以为 RR 下 `FOR UPDATE` 范围查询不会"多出版本"。

5. **长事务：持有 ReadView 不释放，undo 版本无法 purge** —— 一个开着不提交的事务会让 `MVCC` 版本链无限堆积，回滚段膨胀、所有快照读变慢，还长期占锁易死锁。正确写法：事务尽量短、`autocommit=1` 默认开启；批量任务分批提交。

6. **UPDATE/DELETE 没走索引 → 行锁升级为全表锁** —— InnoDB 锁加在索引记录上，若 `WHERE` 条件列无索引，会锁住全表（或退化为逐行锁全表），瞬间卡死并发。正确写法：务必在 `WHERE` 列上建索引再改。

7. **`FOR UPDATE` 范围查询会锁间隙，别在事务里长时间持有** —— `SELECT ... FOR UPDATE WHERE id BETWEEN 10 AND 20` 加 Next-Key Lock，锁住 (10,20) 间隙，别的事务插入该区间会阻塞甚至死锁。正确写法：锁粒度尽量小、锁完立即处理并尽快提交。

8. **在索引列上套函数或隐式类型转换 → 索引失效**
   `WHERE DATE(created_at) = '2026-10-31'`、`WHERE varchar_col = 123`（字符串列与数字比较会隐式转换）都会让 B+ 树无法按序定位，退化成全表扫。`EXPLAIN` 里表现为 `type=ALL` 或 `key=NULL`。
   ✅ 改写成范围：`created_at >= '2026-10-31' AND created_at < '2026-11-01'`；类型严格对齐，把 `123` 写成 `'123'`。

9. **在 RR 隔离级别下以为完全没有幻读**
   InnoDB 的 RR 用 MVCC 解决了**快照读**的幻读，但**当前读**（`SELECT ... FOR UPDATE` / `UPDATE` / `DELETE`）走的是 Next-Key Lock，加锁读仍可能看到新插入的行，或彼此因间隙锁阻塞。
   ✅ 分清快照读与当前读；需要严格串行语义时用 `SERIALIZABLE` 或应用层锁，不要靠「RR 就安全」的直觉。

8. **`EXPLAIN` 看到 `type=ALL` 就直接加索引** —— 小表（几千行）全表扫往往比走索引更快，优化器已经算过成本。正确做法：先看 `rows` 与 `filtered`，再评估「加索引后回表的代价」，区分度低（如 `status` 只有三四种值）的列单建索引基本无效。
9. **在索引列上用函数或隐式转换** —— `WHERE DATE(created_at)='2026-11-01'`、`WHERE varchar_col=123` 都会让索引失效。正确写法：改成范围查询 `created_at >= '2026-11-01' AND created_at < '2026-11-02'`，并保证比较两边类型一致。
10. **联合索引列顺序按「查询写法」而非「区分度」排** —— 把低区分度的 `status` 放在最左，导致后续高区分度列用不上。正确做法：等值条件里区分度最高的列放最左；范围条件列放在最后（因为范围会截断后续列）。
11. **以为 `SELECT *` 和列出字段性能一样** —— `SELECT *` 会让原本可用的覆盖索引退化成回表，尤其在分页与联表场景差异巨大。正确做法：只取需要的列，让 `Extra` 出现 `Using index`；深分页先用覆盖索引取主键再回表。
12. **给同一列建多个前缀重叠的索引** —— 已有 `(a,b)` 又建 `(a)`，后者完全冗余，只增加写入成本与优化器负担。正确做法：定期用 `sys.schema_redundant_indexes` / `schema_unused_indexes` 清理；注意 `(a)` 与 `(b,a)` 不冗余（最左列不同）。
13. **以为 InnoDB 的 RR 「完全没有幻读」** —— MVCC 只解决快照读的幻读；当前读（`FOR UPDATE`/`UPDATE`/`DELETE`）走 next-key lock，混合场景下仍可能观察到行数变化。正确表述：InnoDB RR 通过 MVCC + next-key lock 基本消除幻读，但标准定义中 RR 允许幻读，严格串行需 `SERIALIZABLE` 或应用层锁。
14. **把 redo log 和 undo log 的作用记反** —— redo 是物理日志、保证「已提交的不丢」（崩溃恢复）；undo 是逻辑日志、保证「未提交的可撤」（回滚 + MVCC 版本链）。顺带记住两阶段提交：redo prepare → 写 binlog → redo commit，崩溃时据 binlog 是否完整决定提交或回滚。
15. **在事务里执行 DDL 还指望能回滚** —— `ALTER`/`CREATE`/`DROP`/`TRUNCATE` 会隐式提交当前事务，`ROLLBACK` 只能撤掉 DDL 之后的语句。同类陷阱还有 `SET autocommit`、`LOCK TABLES`；框架层的对应坑是 `@Transactional` 加在 private 方法或同类自调用上导致代理失效。
