# 本章避坑指南

1. **UPDATE/DELETE 忘写 WHERE** —— `UPDATE employee SET salary=0;` 会清空整张表薪资。正确写法：先 `SELECT` 确认影响集，再补 `WHERE emp_id=...`；生产建议开启 `SQL_SAFE_UPDATES`。

2. **SELECT 非聚合列未进 GROUP BY** —— `SELECT dept_id, name FROM employee GROUP BY dept_id;` 中 `name` 既不在 `GROUP BY` 也非聚合函数，在标准 `ONLY_FULL_GROUP_BY` 模式下直接报错（MySQL 5.7+ 默认开启）。正确写法：把 `name` 加入 `GROUP BY`，或对 `name` 使用 `MAX()`/`GROUP_CONCAT()` 等聚合。

3. **用 WHERE 过滤聚合结果** —— `... WHERE AVG(salary)>7000 GROUP BY dept_id` 非法，聚合值不能在 `WHERE` 中过滤。正确写法：改用 `HAVING AVG(salary) > 7000`。

4. **混淆 INNER JOIN 与 LEFT JOIN 的 NULL 语义** —— `LEFT JOIN` 右表无匹配时列值为 `NULL`，若再用 `WHERE right.col = 'x'` 过滤会把 `NULL` 行一并剔掉，等价于 `INNER JOIN`。正确写法：把右表过滤条件放进 `ON`（如 `ON e.dept_id=d.dept_id AND d.location='Beijing'`），或显式 `WHERE right.col IS NULL` 查找「无匹配」。

5. **字符串比较用单引号、列名别用关键字** —— MySQL 字符串字面量用单引号 `'Alice'`；双引号在 ANSI 模式下会被当作标识符。列名若用了 `order`/`group` 等保留字需用反引号 `` `order` `` 包裹，否则报语法错。

6. **LIMIT 不分页时会拿到不稳定顺序** —— 未加 `ORDER BY` 的 `LIMIT 3` 返回的是「存储引擎任意 3 行」，多次执行顺序可能不同。正确写法：始终配合确定性的 `ORDER BY` 主键/唯一列。
