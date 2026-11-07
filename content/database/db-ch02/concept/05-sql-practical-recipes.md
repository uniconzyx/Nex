# 凯喵实战手记：SQL 连接与子查询——写对结果却跑死的那些现场

> 写 SQL 最容易的两件事：一是结果「看起来对」其实错，二是「能跑」但慢到数据库报警。凯喵在 JOIN 和子查询上栽的跟头，足够讲一节课。这 12 个现场，帮你把「语义对」和「跑得动」同时拿捏。

### 1. INNER JOIN 只留两表都匹配的行

凯喵第一次 join 用户和订单，发现「没下过单的用户全没了」：

```sql
SELECT u.name, o.amount
FROM users u
JOIN orders o ON u.id = o.user_id;   -- 只返回有订单的用户
```

INNER JOIN（默认 JOIN）会**丢弃任意一侧无匹配的行**。要保留「无订单用户」，必须用 LEFT JOIN。先想清楚业务要的是「交集」还是「左表全量」。

### 2. LEFT JOIN 之后 WHERE 过滤右表会退化成内连接

凯喵想查「所有用户及其已支付订单」，结果左表被悄悄砍掉：

```sql
SELECT u.name, o.amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.status = 'paid';   -- 右表没匹配的 o.status 为 NULL，被 WHERE 滤掉！
```

LEFT JOIN 的「保住无匹配行」只在 `ON` 阶段生效；`WHERE` 里再过滤右表字段，NULL 行直接被删，等于内连接。修法：过滤条件写进 `ON`，或显式 `OR o.status IS NULL`。

### 3. 笛卡尔积：忘了 ON 条件的灾难

凯喵漏写 join 条件，结果行数爆炸：

```sql
SELECT * FROM users, orders;          -- 没有 ON：N×M 行，灾难
SELECT * FROM users CROSS JOIN orders; -- 明确要笛卡尔积才这么写
```

多表 JOIN 必须每个连接都有 `ON`（或 `USING`）。意外笛卡尔积会让结果翻倍又翻倍，且极慢。需要笛卡尔积时用显式 `CROSS JOIN` 表明意图。

### 4. 自连接：同一张表当两张用

凯喵查「每个员工的经理姓名」，一张员工表搞定：

```sql
SELECT e.name, m.name AS manager
FROM emp e
LEFT JOIN emp m ON e.manager_id = m.id;
```

自连接用**表别名**把同一张表当成两张。常见于「上下级、前后序、相邻记录」类查询。注意层级深时要换成递归 CTE（`WITH RECURSIVE`）。

### 5. 子查询相关与不相关：性能天差地别

凯喵写的相关子查询慢到超时：

```sql
-- 相关子查询：外层每行都重跑一次内层
SELECT name FROM emp e
WHERE salary > (SELECT AVG(salary) FROM emp WHERE dept = e.dept);

-- 改写成 JOIN + 聚合，通常快得多
SELECT e.name
FROM emp e JOIN (SELECT dept, AVG(salary) a FROM emp GROUP BY dept) d
  ON e.dept = d.dept AND e.salary > d.a;
```

相关子查询对每行重算，量级放大 N 倍。能用 JOIN + 预聚合的，优先改写。判断是否「相关」看内层是否引用了外层列。

### 6. EXISTS vs IN：NULL 语义与空值处理

凯喵在「有订单的用户」上纠结用哪个：

```sql
SELECT name FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);
-- 比 IN (SELECT user_id ...) 在 user_id 有 NULL 时更安全，且常更快
```

`IN` 遇到子查询结果含 NULL 时语义会变（`NOT IN (NULL)` 永远未知）；`EXISTS` 只看「有没有行」，不受 NULL 干扰，且通常在找到第一条就短路。大表关联优先 `EXISTS`。

### 7. 集合运算：UNION 去重 vs UNION ALL

凯喵用 `UNION` 合并日志，慢了一倍还丢了重复：

```sql
SELECT col FROM t1
UNION ALL          -- 保留全部行，不去重，快
SELECT col FROM t2;
-- UNION 会去重（隐式 DISTINCT），若不需要去重请用 UNION ALL
```

`UNION` 自带去重排序，代价高；确定无重复或不需要去重时一律 `UNION ALL`。两个查询的列数、类型、顺序必须一致。

### 8. INTERSECT / EXCEPT：交集与差集

凯喵查「A 表有但 B 表没有的 ID」用了 NOT IN，被 NULL 坑：

```sql
-- 更稳的写法：EXCEPT（差集）
SELECT id FROM a
EXCEPT
SELECT id FROM b;
```

`EXCEPT` 直接表达「在 A 不在 B」，比 `NOT IN` 更不容易被 NULL 坑。注意各数据库支持度（MySQL 用 `LEFT JOIN ... WHERE b.id IS NULL` 替代）。

### 9. 反范式：用冗余换读性能

凯喵的订单列表每次都要 JOIN 用户表取昵称，QPS 上不去：

```sql
-- 反范式：订单表冗余 user_name，读时不再 JOIN
ALTER TABLE orders ADD COLUMN user_name VARCHAR(64);
-- 写时双写/通过触发器同步，读时单表查询
```

规范化减少冗余但增加 JOIN；反范式（冗余常读字段）牺牲写入一致性换读取速度。适合「读远多于写、且字段变更不频繁」的场景，配合同步机制保一致。

### 10. 用窗口函数做「每组 Top-N」

凯喵想取每个部门工资最高的两人，GROUP BY 做不到：

```sql
SELECT name, dept, salary FROM (
  SELECT name, dept, salary,
         ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) rn
  FROM emp
) t WHERE rn <= 2;
```

窗口函数（带 `OVER (PARTITION BY ... ORDER BY ...)`）**不缩减行数**，在原行上附加排名。Top-N、累计、同比环比都靠它，比「自连接算排名」简洁得多。

### 11. 聚合陷阱：SELECT 里出现非聚合非分组列

凯喵写出语义错误的聚合查询：

```sql
SELECT dept, name, MAX(salary)   -- name 既不是分组列也不是聚合，结果无意义
FROM emp GROUP BY dept;
```

`GROUP BY dept` 后，每行代表「一个部门」，但 `name` 是该部门多个名字之一，数据库只会「随便取一个」。要拿「最高薪者的名字」用窗口函数或子查询，别直接 SELECT 裸列。

### 12. 执行顺序：写的是 SELECT-FROM-WHERE，跑的是 FROM-WHERE-SELECT

凯喵总搞不清别名在哪能用：

```sql
-- 逻辑执行顺序：FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY
SELECT dept AS d, COUNT(*) c
FROM emp
WHERE salary > 1000        -- WHERE 在 SELECT 前，不能用 c 或 d 别名
GROUP BY d                  -- GROUP BY 多数库能用 SELECT 别名，但不完全通用
ORDER BY c DESC;            -- ORDER BY 在最后，能用别名
```

WHERE 在聚合前过滤（不能用聚合函数），HAVING 在聚合后过滤。理解执行顺序才能写出既对又快的 SQL，也才看得懂执行计划。

> 凯喵总结：SQL 的坑九成在「JOIN 语义」「相关子查询慢」「UNION 去重」「反范式一致性」「窗口 vs GROUP BY」「执行顺序」。把这 12 个现场刻进查询本，结果错和跑死都能少一半。

> 现场之外：写 SQL 先问自己三件事——「要的是哪种连接（语义对吗）」「有没有意外笛卡尔积」「能不能用 JOIN 替掉相关子查询」。上生产前 `EXPLAIN` 看一眼执行计划，比事后救火省心百倍。

> 一句话收尾：SQL 写对容易写快难，语义对和跑得动是两件事——前者靠逻辑，后者靠执行计划。

### 凯喵复盘：SQL 的两个灵魂问题

这 12 个现场都绕不开两个灵魂问题：**语义上「我要的是哪种集合运算」，性能上「引擎会怎么跑」**。LEFT JOIN 退化成内连接、UNION 偷偷去重、IN 遇 NULL 翻车，都是「集合语义理解错」；相关子查询慢、意外笛卡尔积、GROUP BY 后 SELECT 裸列，是「没站在执行顺序和代价的角度想」。写复杂 SQL 时，先在纸上画出「结果集语义」，再用 `EXPLAIN` 核对「执行路径」，两者对得上才敢上生产。把「语义」和「代价」当成写 SQL 的双腿，结果错和跑死都能少一半。落到写查询上，记住一句话：**先想清楚要的是哪种集合运算，再想引擎会怎么跑**。语义对靠逻辑，跑得动靠执行计划，两者缺一不可；上生产前 `EXPLAIN` 看一眼，比事后救火省心百倍。很多人 SQL 写错不是不会语法，而是从没在脑子里跑过一遍「结果集到底长什么样」。养成「先想象结果、再写语句、最后 EXPLAIN」的习惯，比背任何优化技巧都管用，也更少出生产事故。SQL 这门手艺，想清楚结果集比写得快重要得多——慢一点想，远比快一点写、再花一夜救火来得划算。慢想快写，远胜快写慢救。

## 三视角解析
### 🧑‍💻 程序员视角
`LEFT JOIN` 之后在 `WHERE` 里过滤右表字段，会把「左表全保留」的语义破坏成 `INNER JOIN`——右表为 NULL 的行被过滤掉了，条件必须写在 `ON` 里。忘了 `ON` 条件会产生笛卡尔积，两张十万行的表直接生成百亿行。自连接是「同一张表当两张用」，典型场景是「找每个员工的上级」与「找连续登录」。子查询能用 `JOIN` 改写的尽量改写，因为相关子查询可能对每行执行一次。

### 🎓 博士生视角
SQL 的执行语义是「先 FROM/JOIN 构造笛卡尔积 → 再 WHERE 过滤 → 再 GROUP BY → 再 HAVING → 再 SELECT → 最后 ORDER BY/LIMIT」，理解这个顺序才能解释「为什么 WHERE 里不能用聚合函数」「为什么别名在 WHERE 里不可见」。外连接的「保留侧」语义决定了过滤条件的放置位置：`ON` 参与连接匹配、`WHERE` 在连接结果上过滤。查询优化器的核心工作是把「逻辑计划」重写成「等价但更便宜的物理计划」。

### 📚 考研者视角
数据库面试高频：
1. **连接类型**：INNER/LEFT/RIGHT/FULL OUTER 的结果集差异，`ON` 与 `WHERE` 的区别。
2. **聚合**：`GROUP BY` 与 `HAVING` 的执行顺序、`COUNT(*)` 与 `COUNT(col)` 的差异。
3. **子查询**：相关子查询与非相关子查询、`EXISTS` 与 `IN` 的取舍。
4. **窗口函数**：`ROW_NUMBER`/`RANK`/`DENSE_RANK` 的差异、`PARTITION BY` 的用法。

```text
05-sql-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 1. INNER JOIN 只留两表都匹配的行  (sql)
    |
    v
  [02] 2. LEFT JOIN 之后 WHERE 过滤右表会退化成内连接  (sql)
    |
    v
  [03] 3. 笛卡尔积：忘了 ON 条件的灾难  (sql)
    |
    v
  [04] 4. 自连接：同一张表当两张用  (sql)
    |
    v
  [05] 5. 子查询相关与不相关：性能天差地别  (sql)
    |
    v
  [06] 6. EXISTS vs IN：NULL 语义与空值处理  (sql)
    |
    v
  [07] 7. 集合运算：UNION 去重 vs UNION ALL  (sql)
    |
    v
  [08] 8. INTERSECT / EXCEPT：交集与差集  (sql)
    |
    v
  [... 其余 5 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
