# 本章避坑指南

1. **LEFT JOIN 把右表过滤条件写进 WHERE 反而变 INNER JOIN** —— `SELECT ... FROM A LEFT JOIN B ON A.id=B.aid WHERE B.status='ok'`：右表无匹配的行 `B.status` 为 `NULL`，被 `WHERE` 剔掉，等价 INNER JOIN。正确写法：把右表过滤放进 `ON`（`ON A.id=B.aid AND B.status='ok'`），或显式 `WHERE B.aid IS NULL` 找"无匹配"。

2. **NOT IN 子查询含 NULL 返回空集** —— `WHERE id NOT IN (SELECT mid FROM t WHERE mid IS NOT NULL 的补集...)` 一旦子查询出现任意 `NULL`，整个表达式结果为 `UNKNOWN`，整条查询返回 0 行。正确写法：用 `NOT EXISTS (SELECT 1 FROM t WHERE t.mid = a.id)` 或 `LEFT JOIN t ON ... WHERE t.mid IS NULL`，二者对 NULL 安全。

3. **相关子查询写在 SELECT 列表引发 N+1** —— `SELECT name, (SELECT COUNT(*) FROM orders o WHERE o.cid=c.id) FROM customer c` 会对每个客户执行一次子查询，客户多时极慢。正确写法：改写成 `LEFT JOIN + GROUP BY` 一次聚合出计数。

4. **盲目用 UNION 而非 UNION ALL 触发隐式排序去重** —— 两结果集确定不重叠时，`UNION` 仍会做一次 `filesort` 去重，白白浪费。正确写法：确认无重叠时用 `UNION ALL`；需要去重才用 `UNION`。

5. **派生表（FROM 子查询）没加限制导致物化巨型临时表** —— `FROM (SELECT * FROM huge WHERE ...) t` 若子查询带 `GROUP BY`/`DISTINCT`/`LIMIT` 无法被合并，会物化成磁盘临时表。正确写法：只 `SELECT` 必要列、尽量把过滤/聚合下推到派生表内，或改写成 JOIN/视图让优化器合并。

6. **多表 JOIN 连接列类型/字符集不一致导致索引失效退化 BNL** —— `a.uid(VARCHAR)` JOIN `b.user_id(INT)` 或两边字符集（utf8 vs utf8mb4）不同，会触发隐式转换，内表索引用不上，退化成 Block Nested Loop 全表扫描。正确写法：统一连接列的类型与字符集、加索引。

7. **IN 列表过长被优化器放弃** —— `col IN (上千个常量)` 超过 `range_optimizer_max_mem_size` 会退化为全表扫描。正确写法：把列表落成临时表再 `JOIN`，或改用 `EXISTS` 子查询。
