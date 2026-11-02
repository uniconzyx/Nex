# 本章避坑指南

1. **LEFT JOIN 把右表过滤条件写进 WHERE 反而变 INNER JOIN** —— `SELECT ... FROM A LEFT JOIN B ON A.id=B.aid WHERE B.status='ok'`：右表无匹配的行 `B.status` 为 `NULL`，被 `WHERE` 剔掉，等价 INNER JOIN。正确写法：把右表过滤放进 `ON`（`ON A.id=B.aid AND B.status='ok'`），或显式 `WHERE B.aid IS NULL` 找"无匹配"。

2. **NOT IN 子查询含 NULL 返回空集** —— `WHERE id NOT IN (SELECT mid FROM t WHERE mid IS NOT NULL 的补集...)` 一旦子查询出现任意 `NULL`，整个表达式结果为 `UNKNOWN`，整条查询返回 0 行。正确写法：用 `NOT EXISTS (SELECT 1 FROM t WHERE t.mid = a.id)` 或 `LEFT JOIN t ON ... WHERE t.mid IS NULL`，二者对 NULL 安全。

3. **相关子查询写在 SELECT 列表引发 N+1** —— `SELECT name, (SELECT COUNT(*) FROM orders o WHERE o.cid=c.id) FROM customer c` 会对每个客户执行一次子查询，客户多时极慢。正确写法：改写成 `LEFT JOIN + GROUP BY` 一次聚合出计数。

4. **盲目用 UNION 而非 UNION ALL 触发隐式排序去重** —— 两结果集确定不重叠时，`UNION` 仍会做一次 `filesort` 去重，白白浪费。正确写法：确认无重叠时用 `UNION ALL`；需要去重才用 `UNION`。

5. **派生表（FROM 子查询）没加限制导致物化巨型临时表** —— `FROM (SELECT * FROM huge WHERE ...) t` 若子查询带 `GROUP BY`/`DISTINCT`/`LIMIT` 无法被合并，会物化成磁盘临时表。正确写法：只 `SELECT` 必要列、尽量把过滤/聚合下推到派生表内，或改写成 JOIN/视图让优化器合并。

6. **多表 JOIN 连接列类型/字符集不一致导致索引失效退化 BNL** —— `a.uid(VARCHAR)` JOIN `b.user_id(INT)` 或两边字符集（utf8 vs utf8mb4）不同，会触发隐式转换，内表索引用不上，退化成 Block Nested Loop 全表扫描。正确写法：统一连接列的类型与字符集、加索引。

7. **IN 列表过长被优化器放弃** —— `col IN (上千个常量)` 超过 `range_optimizer_max_mem_size` 会退化为全表扫描。正确写法：把列表落成临时表再 `JOIN`，或改用 `EXISTS` 子查询。

8. **`NOT IN` 的子查询里出现 NULL，结果集直接变空**
   `WHERE id NOT IN (SELECT fk FROM t2)` 只要子查询返回**一个 NULL**，整体就恒为空——三值逻辑下 `id <> NULL` 是 UNKNOWN，永远不满足 TRUE。这类 bug 表现为「数据明明存在却查不出来」。
   ✅ 改用 `NOT EXISTS`（对 NULL 安全）；或子查询里加 `WHERE fk IS NOT NULL`。

9. **`LEFT JOIN` 之后在 `WHERE` 里过滤右表字段，悄悄退化成内连接**
   `LEFT JOIN t2 ON ... WHERE t2.status = 'ok'`：右表没匹配上的行 `t2.status` 为 NULL，被 `WHERE` 滤掉，左连接保住「无匹配行」的意义完全消失。
   ✅ 过滤条件写进 `ON`（`ON ... AND t2.status='ok'`），或显式允许空值 `OR t2.status IS NULL`。
10. **忘写 JOIN 的 ON 条件 → 意外笛卡尔积** —— 多表 JOIN 漏掉 `ON` 会产出 N×M 行，结果翻倍又翻倍且极慢。修法：每个连接都显式写 `ON`/`USING`；确实需要笛卡尔积时用 `CROSS JOIN` 表明意图，避免误写。
11. **`NOT IN (子查询)` 遇 NULL 永远为假** —— 子查询结果含 NULL 时，`x NOT IN (..., NULL)` 整体判定为 unknown，行被静默丢掉。修法：改用 `NOT EXISTS`，或对子查询加 `WHERE col IS NOT NULL`；需要差集优先 `EXCEPT`。
12. **用 `UNION` 当 `UNION ALL`** —— `UNION` 隐式去重排序，代价高；确定无重复或不需要去重时应用 `UNION ALL`。修法：能确认无重复就一律 `UNION ALL`，大数据量下常快一倍。
13. **GROUP BY 后 SELECT 裸列（非分组非聚合）** —— `SELECT dept, name, MAX(salary) ... GROUP BY dept`，`name` 是该部门多个名字之一，数据库任取一个，结果无意义。修法：要「最高薪者姓名」用窗口函数或子查询，别直接 SELECT 非分组列。
14. **相关子查询对每行重算，量级放大 N 倍** —— 内层引用外层列的相关子查询，外层每行都重跑一次内层。修法：能用 JOIN + 预聚合（派生表）改写的优先改写；判断是否「相关」看内层是否引用了外层列。
15. **把窗口函数当 GROUP BY 用** —— 窗口函数（带 `OVER`）**不缩减行数**，在原行上附加聚合结果；`GROUP BY` 才把每组聚成一行。修法：要「每组 Top-N / 每组累计」用窗口函数 + `WHERE rn<=N`；要「每组一行汇总」才用 GROUP BY。
