# 03 · SELECT 查询、JOIN 关联与聚合分组

## SELECT 基本结构

```sql
SELECT name, salary
FROM employee
WHERE salary > 5000
ORDER BY salary DESC
LIMIT 3;
```

执行逻辑顺序（理解它才能写好查询）：`FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`。

## JOIN：多表关联

- `INNER JOIN`：只保留两表都匹配的行。
- `LEFT JOIN`：保留左表全部行，右表无匹配时补 `NULL`。

```sql
-- 查每个员工的姓名及其部门名（内连接）
SELECT e.name, d.dept_name
FROM employee e
INNER JOIN department d ON e.dept_id = d.dept_id;
```

## 聚合与分组

```sql
-- 每个部门的人数与平均薪资
SELECT dept_id,
       COUNT(*)            AS headcount,
       ROUND(AVG(salary),2) AS avg_salary
FROM employee
GROUP BY dept_id
HAVING AVG(salary) > 7000;   -- 分组后再过滤用 HAVING
```

> 要点：`WHERE` 在分组前过滤单行，`HAVING` 在分组后过滤组；出现在 `SELECT` 中非聚合列必须出现在 `GROUP BY` 中（或本身被聚合）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `WHERE` 过滤**行**、`HAVING` 过滤**组**——先分组后筛选的语义区别必须在写 SQL 时就分清楚。
- `COUNT(*)` 数行（含 NULL 行），`COUNT(col)` 只数该列非 NULL 的行——两个函数经常被混用导致统计口径错误。
- `LEFT JOIN` 的过滤条件放 `ON` 还是 `WHERE` 会改变语义：放 `WHERE` 会把左表未匹配行过滤掉，**LEFT JOIN 退化成 INNER JOIN**——这是排查「数据莫名变少」的第一嫌疑点。

### 🎓 博士生视角
- SQL 有**两个顺序**：书写顺序（SELECT…FROM…WHERE…）与**逻辑执行顺序**（FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT）。理解后者才能解释「为什么 WHERE 里不能用 SELECT 的别名」「为什么聚合函数不能出现在 WHERE 中」。
- SQL 默认是**多重集（bag）语义**而非集合语义——这正是 `UNION` 需要显式去重、而关系代数默认去重的原因。
- 聚合可以看作分组键上的**函数式归约**（fold），`GROUP BY` 是按 key 的 partition-then-reduce，与 MapReduce 的 shuffle 阶段同构。

### 📚 考研者视角
- **自命题必考大题**：写出满足给定需求的 SQL 查询（多表连接 + 分组 + `HAVING` + 排序 + 嵌套），并常要求**与关系代数表达式互译**。
- 常见陷阱题：`NULL` 参与比较与聚合的结果；`COUNT(*)` 与 `COUNT(列)` 的差异。
- 记忆锚点：**逻辑执行顺序 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY**；**WHERE 管行、HAVING 管组**。
