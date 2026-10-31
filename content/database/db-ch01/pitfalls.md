# 本章避坑指南

1. **UPDATE/DELETE 忘写 WHERE** —— `UPDATE employee SET salary=0;` 会清空整张表薪资。正确写法：先 `SELECT` 确认影响集，再补 `WHERE emp_id=...`；生产建议开启 `SQL_SAFE_UPDATES`。
2. **SELECT 非聚合列未进 GROUP BY** —— `SELECT dept_id, name FROM employee GROUP BY dept_id;` 中 `name` 既不在 `GROUP BY` 也非聚合函数，在标准 `ONLY_FULL_GROUP_BY` 模式下直接报错（MySQL 5.7+ 默认开启）。正确写法：把 `name` 加入 `GROUP BY`，或对 `name` 使用 `MAX()`/`GROUP_CONCAT()` 等聚合。
3. **用 WHERE 过滤聚合结果** —— `... WHERE AVG(salary)>7000 GROUP BY dept_id` 非法，聚合值不能在 `WHERE` 中过滤。正确写法：改用 `HAVING AVG(salary) > 7000`。
4. **混淆 INNER JOIN 与 LEFT JOIN 的 NULL 语义** —— `LEFT JOIN` 右表无匹配时列值为 `NULL`，若再用 `WHERE right.col = 'x'` 过滤会把 `NULL` 行一并剔掉，等价于 `INNER JOIN`。正确写法：把右表过滤条件放进 `ON`（如 `ON e.dept_id=d.dept_id AND d.location='Beijing'`），或显式 `WHERE right.col IS NULL` 查找「无匹配」。
5. **字符串比较用单引号、列名别用关键字** —— MySQL 字符串字面量用单引号 `'Alice'`；双引号在 ANSI 模式下会被当作标识符。列名若用了 `order`/`group` 等保留字需用反引号 `` `order` `` 包裹，否则报语法错。
6. **LIMIT 不分页时会拿到不稳定顺序** —— 未加 `ORDER BY` 的 `LIMIT 3` 返回的是「存储引擎任意 3 行」，多次执行顺序可能不同。正确写法：始终配合确定性的 `ORDER BY` 主键/唯一列。
7. **`NOT IN` 遇到 `NULL` 返回空集** —— `x NOT IN (…, NULL)` 恒为 UNKNOWN，`WHERE` 丢弃 UNKNOWN，于是整条查询返回空。用 `NOT EXISTS` 替代，或确保子查询结果非空（`WHERE col IS NOT NULL`）。
8. **`COUNT(col)` 与 `COUNT(*)` 口径混用** —— 列可为 `NULL` 时前者会少数；统计"人数"却用了 `COUNT(email)`，结果偏小。按业务语义选，别按习惯选。
9. **`AVG` 的分母是"非空个数"** —— 有 `NULL` 的行不参与平均。若要按全部行平均，写 `SUM(col)/COUNT(*)` 并在业务上决定 `NULL` 是否按 0 计。
10. **金额字段用 `FLOAT/DOUBLE`** —— 二进制浮点无法精确表示 0.1，累加后出现 `6000.000000000001` 这类值。金额一律 `DECIMAL(10,2)`。
11. **`TRUNCATE` 当 `DELETE` 用** —— `TRUNCATE` 是 DDL：不可回滚、重置自增、不触发行触发器、按页释放。想能回滚就用 `DELETE`（或先备份）。
12. **在事务里执行 DDL 然后 ROLLBACK** —— MySQL 的 DDL 隐式提交，`ROLLBACK` 只会撤销 DDL 之后的 DML，之前的操作已经落盘。PG 没这个问题，别把两边的经验混用。
13. **`WHERE DATE(created_at) = '2026-01-01'`** —— 对列做函数运算会让索引失效，退化为全表扫描。改成范围查询：`created_at >= '2026-01-01' AND created_at < '2026-01-02'`。
14. **`INSERT` 不写列名** —— 表加列后列数不匹配导致报错，或值错位写入错误字段（更糟，且难发现）。永远显式列名。
15. **大表直接 `ALTER TABLE`** —— 走 COPY 算法会锁写数分钟到数小时。用 `ALGORITHM=INPLACE/INSTANT` 或 gh-ost / pt-online-schema-change，并在低峰执行。
16. **外键与唯一约束允许多个 `NULL`** —— `UNIQUE` 列可以有任意多个 `NULL`（`NULL` 不等于 `NULL`）。要"必填且唯一"必须 `NOT NULL` + `UNIQUE` 同时加。
