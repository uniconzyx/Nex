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

这条顺序解释了三件常被当成"规定"来背的事：为什么 `WHERE` 里不能用 `SELECT` 起的别名（`SELECT` 还没执行）；为什么聚合函数不能写在 `WHERE` 里（还没分组）；为什么 `ORDER BY` **可以**用别名（它在 `SELECT` 之后）。

## 一、两个顺序，别搞混

```text
书写顺序                    逻辑执行顺序
SELECT                       FROM / JOIN
  ↓                            ↓
FROM                         WHERE
  ↓                            ↓
WHERE                        GROUP BY
  ↓                            ↓
GROUP BY                     HAVING
  ↓                            ↓
HAVING                       SELECT（计算表达式、起别名）
  ↓                            ↓
ORDER BY                     ORDER BY（可用别名）
  ↓                            ↓
LIMIT                        LIMIT
```

注意"逻辑顺序"不等于"物理执行顺序"：优化器会在保持语义等价的前提下重排（选择下推、谓词合并）。但**语义判定**永远按逻辑顺序解释。

## 二、JOIN 全景

| 类型 | 语义 | 结果 |
|---|---|---|
| `INNER JOIN` | 两表都匹配 | 只保留匹配行 |
| `LEFT JOIN` | 保留左表全部 | 右表无匹配补 `NULL` |
| `RIGHT JOIN` | 保留右表全部 | 左表无匹配补 `NULL` |
| `FULL OUTER JOIN` | 两边都保留 | MySQL 不支持，用 `UNION` 模拟 |
| `CROSS JOIN` | 笛卡尔积 | m×n 行 |
| 自连接（self join） | 表与自己连接 | 用于层级/比较同表行 |

```sql
-- INNER JOIN：只要匹配上的
SELECT e.name, d.dept_name
FROM employee e
INNER JOIN department d ON e.dept_id = d.dept_id;

-- LEFT JOIN：保留所有员工，没部门的 dept_name 为 NULL
SELECT e.name, d.dept_name
FROM employee e
LEFT JOIN department d ON e.dept_id = d.dept_id;

-- 自连接：查每个员工与其经理
SELECT e.name AS emp, m.name AS manager
FROM employee e
LEFT JOIN employee m ON e.manager_id = m.emp_id;
```

### `ON` 与 `WHERE` 的区别（LEFT JOIN 的关键）

```sql
-- 语义 A：先把右表过滤到 location='Beijing'，再左连接（保留所有员工）
SELECT e.name, d.dept_name
FROM employee e
LEFT JOIN department d ON e.dept_id = d.dept_id AND d.location = 'Beijing';

-- 语义 B：左连接后再过滤，未匹配的行被 NULL 判假 → 退化成 INNER JOIN
SELECT e.name, d.dept_name
FROM employee e
LEFT JOIN department d ON e.dept_id = d.dept_id
WHERE d.location = 'Beijing';
```

这是"数据莫名变少"的第一嫌疑点。规则：**想保留左表全部行，就把右表的过滤条件放 `ON`**。

### 关于 `FULL OUTER JOIN`

MySQL 没有这个语法，用两条 `LEFT JOIN` + `RIGHT JOIN` 做 `UNION`：

```sql
SELECT e.name, d.dept_name FROM employee e LEFT JOIN department d ON e.dept_id = d.dept_id
UNION
SELECT e.name, d.dept_name FROM employee e RIGHT JOIN department d ON e.dept_id = d.dept_id;
```

## 三、聚合与分组

```sql
SELECT dept_id,
       COUNT(*)             AS headcount,
       ROUND(AVG(salary),2) AS avg_salary,
       MAX(salary)          AS top_salary
FROM employee
GROUP BY dept_id
HAVING AVG(salary) > 7000
ORDER BY avg_salary DESC;
```

### 五个聚合函数与 `NULL` 的关系

- `COUNT(*)` 数**行**，包含含 `NULL` 的行。
- `COUNT(col)` 数该列**非 `NULL`** 的行。
- `SUM` / `AVG` / `MAX` / `MIN` 都**忽略 `NULL`**。

这带来两个反直觉结果：

```sql
-- 若 10 行里有 4 行 salary 为 NULL
SELECT COUNT(*), COUNT(salary), AVG(salary) FROM employee;
-- COUNT(*) = 10，COUNT(salary) = 6，AVG 是 6 个值的平均（不是 10 个）
```

`AVG` 的分母是"非空个数"，想按全部行平均要写 `SUM(salary)/COUNT(*)`。

### `ONLY_FULL_GROUP_BY`：为什么必须列出非聚合列

`SELECT dept_id, name FROM employee GROUP BY dept_id` 在标准 SQL 下非法：每个 `dept_id` 组里有多个 `name`，引擎无法决定返回哪一个。MySQL 5.7 起默认开启 `ONLY_FULL_GROUP_BY`，直接报错——这比"随机返回一个"安全得多。

想让每组取一个代表值，用聚合函数显式表达意图：

```sql
SELECT dept_id, MAX(name) AS any_name, COUNT(*) FROM employee GROUP BY dept_id;
```

### `GROUP BY` 与 `ORDER BY` 的 `NULL` 位置

分组时所有 `NULL` 归为**同一组**（`NULL` 与 `NULL` 被视为相等——这是 `GROUP BY`/`DISTINCT` 的特例，与 `=` 比较不同）。排序时 `NULL` 在 MySQL 里视为最小，`ASC` 时排最前；显式控制用 `ORDER BY col IS NULL, col`。

## 四、子查询的三种形态

```sql
-- 标量子查询：返回单值
SELECT name, salary FROM employee
WHERE salary > (SELECT AVG(salary) FROM employee);

-- 行/列子查询 + IN
SELECT name FROM employee WHERE dept_id IN (SELECT dept_id FROM department WHERE location='Beijing');

-- 相关子查询（EXISTS）：对外层每一行执行一次
SELECT d.dept_name FROM department d
WHERE EXISTS (SELECT 1 FROM employee e WHERE e.dept_id = d.dept_id);
```

**`IN` 与 `EXISTS` 的取舍**：子查询结果小、外层大 → 用 `IN`；外层小、子查询大 → 用 `EXISTS`（可提前短路）。更关键的是 **`NOT IN` 遇 `NULL` 会返回空集，`NOT EXISTS` 不会**——这条比性能更值得记住。

## 五、窗口函数：分组的"不折叠"版本

`GROUP BY` 会把多行折叠成一行；只想"在每行旁边显示分组统计"时用窗口函数：

```sql
SELECT name, dept_id, salary,
       AVG(salary) OVER (PARTITION BY dept_id) AS dept_avg,
       RANK()       OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rk
FROM employee;
```

`OVER` 定义窗口（分区 + 排序），行数不减少。这是 MySQL 8.0 引入的能力，替代了大量自连接与临时表写法。

## 六、边界与陷阱

- **`WHERE` 过滤行、`HAVING` 过滤组**：聚合条件必须放 `HAVING`。
- **`COUNT(*)` 与 `COUNT(col)` 口径不同**：统计人数时若列可为 `NULL`，结果会少。
- **`LEFT JOIN` 的右表条件放 `WHERE`**：退化成 `INNER JOIN`。
- **`SELECT *` 与 `GROUP BY` 混用**：非聚合列未列出，`ONLY_FULL_GROUP_BY` 报错。
- **`LIMIT` 无 `ORDER BY`**：返回顺序不确定，翻页结果会漂移。
- **`NULL` 参与 `NOT IN`**：整条查询返回空。
- **`DISTINCT` 当"去重一切"用**：它作用于整行组合，不是单列；且 `DISTINCT` + `ORDER BY` 可能触发临时表。
- **在 `WHERE` 里对列做函数运算**：`WHERE DATE(created_at) = '2026-01-01'` 会让索引失效，改用范围查询 `created_at >= '2026-01-01' AND created_at < '2026-01-02'`。

## 七、可运行示例：JOIN 语义与聚合口径

```sql
-- 两种 JOIN 的差异
SELECT e.name, d.dept_name
FROM employee e INNER JOIN department d ON e.dept_id = d.dept_id
ORDER BY e.name;

SELECT e.name, d.dept_name
FROM employee e LEFT JOIN department d ON e.dept_id = d.dept_id
ORDER BY e.name;

-- ON 上过滤 vs WHERE 上过滤（LEFT JOIN 语义变化）
SELECT 'on_filter' AS tag, e.name, d.dept_name
FROM employee e LEFT JOIN department d
     ON e.dept_id = d.dept_id AND d.location = 'Beijing'
UNION ALL
SELECT 'where_filter', e.name, d.dept_name
FROM employee e LEFT JOIN department d ON e.dept_id = d.dept_id
WHERE d.location = 'Beijing';

-- 聚合口径：COUNT(*) 与 COUNT(col) 的差异
SELECT dept_id,
       COUNT(*)      AS rows_all,
       COUNT(dept_id) AS rows_nonnull,
       ROUND(AVG(salary), 2) AS avg_salary
FROM employee
GROUP BY dept_id
ORDER BY dept_id;
```

第三段用 `UNION ALL` 把两种过滤方式并排输出，能直接看到 `where_filter` 那组少了"没有部门/部门不在北京"的员工——这就是"LEFT JOIN 退化"的观测方式。

## 八、小结：查询的三层心智模型

写复杂 SQL 时，脑子里保留三层结构，比一条条子句往下顺要可靠得多。

**第一层是「行从哪来」。** FROM 与 JOIN 决定了行的来源与基数。这一层必须回答两个问题：
一行代表什么（粒度），以及 JOIN 之后行数会不会放大（扇出）。
绝大多数「结果数字偏大」的 bug 都发生在这一层——一对多 JOIN 后直接 SUM，明细被重复累加了多次，
而 SQL 本身不报任何错。

**第二层是「哪些行留下」。** WHERE 在聚合之前生效，HAVING 在聚合之后生效。
把本该写在 WHERE 的条件塞进 HAVING，除了慢，更严重的是让「过滤」与「聚合」的语义纠缠在一起：
后来读这段代码的人无法只从 WHERE 判断结果集的范围，必须把整个 GROUP BY 读完。

**第三层是「怎么折叠」。** GROUP BY 把多行压成一行，窗口函数在保留明细的同时附加聚合值。
选择标准非常清晰——**最终结果还需不需要明细**。需要就用窗口函数，不需要就用 GROUP BY。
如果发现自己「先 GROUP BY 再 JOIN 回明细表」，那通常说明第一层的粒度没想清楚，
而不是需要更多子查询。

执行顺序 `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT` 之所以值得背下来，
是因为它精确描述了这三层的先后关系：能写进 WHERE 的条件永远比写进 HAVING 更早生效，
也就能更早把参与运算的数据量降下来。这条规则同时解释了「为什么 SELECT 里的别名不能用在 WHERE」——
WHERE 执行时 SELECT 还没轮到。

## 三视角解析

### 🧑‍💻 程序员视角
- `WHERE` 过滤**行**、`HAVING` 过滤**组**——先分组后筛选的语义区别必须在写 SQL 时就分清楚。
- `COUNT(*)` 数行（含 NULL 行），`COUNT(col)` 只数该列非 NULL 的行——两个函数经常被混用导致统计口径错误。
- `LEFT JOIN` 的过滤条件放 `ON` 还是 `WHERE` 会改变语义：放 `WHERE` 会把左表未匹配行过滤掉，**LEFT JOIN 退化成 INNER JOIN**——这是排查「数据莫名变少」的第一嫌疑点。
- 需要"每行带分组统计"时用窗口函数，别再用自连接或子查询硬凑；MySQL 8.0+ 才有，注意目标环境版本。

### 🎓 博士生视角
- SQL 有**两个顺序**：书写顺序（SELECT…FROM…WHERE…）与**逻辑执行顺序**（FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT）。理解后者才能解释「为什么 WHERE 里不能用 SELECT 的别名」「为什么聚合函数不能出现在 WHERE 中」。
- SQL 默认是**多重集（bag）语义**而非集合语义——这正是 `UNION` 需要显式去重、而关系代数默认去重的原因。
- 聚合可以看作分组键上的**函数式归约**（fold），`GROUP BY` 是按 key 的 partition-then-reduce，与 MapReduce 的 shuffle 阶段同构。
- 连接算法的物理实现有三种：**嵌套循环**（小表驱动）、**哈希连接**（等值连接，内存建哈希表）、**排序合并连接**（适合已有序或需排序）。`EXPLAIN` 里的 `Using join buffer`、`Using temporary` 就是这些策略的直接痕迹。
- 三值逻辑让 `GROUP BY` 与 `=` 的行为不一致：`NULL = NULL` 是 UNKNOWN，但 `GROUP BY`/`DISTINCT` 把 `NULL` 视为同一组。这是标准刻意的规定，因为"分组"是按值等价类划分，而非按比较谓词。

### 📚 考研者视角
- **自命题必考大题**：写出满足给定需求的 SQL 查询（多表连接 + 分组 + `HAVING` + 排序 + 嵌套），并常要求**与关系代数表达式互译**。
- 常见陷阱题：`NULL` 参与比较与聚合的结果；`COUNT(*)` 与 `COUNT(列)` 的差异。
- 常考辨析：`INNER JOIN` / `LEFT JOIN` / 自然连接 / 等值连接的写法与差异；`WHERE` 与 `HAVING` 的作用阶段。
- 记忆锚点：**逻辑执行顺序 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY**；**WHERE 管行、HAVING 管组**；**聚合函数忽略 NULL**。
