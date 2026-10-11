# 02 · DDL 与 DML（建表、改表与增删改）

SQL 分为 DDL（数据定义）与 DML（数据操作）两大类。

## DDL：定义结构

```sql
-- 建表
CREATE TABLE employee (
    emp_id  INT PRIMARY KEY,
    name    VARCHAR(20) NOT NULL,
    dept_id INT,
    salary  DECIMAL(10,2)
);

-- 改表：新增列
ALTER TABLE employee ADD COLUMN hire_date DATE;

-- 删表
DROP TABLE IF EXISTS employee;
```

## DML：操作数据

```sql
-- 插入（显式列名最稳妥）
INSERT INTO employee (emp_id, name, dept_id, salary)
VALUES (1, 'Alice', 10, 6000.00),
       (2, 'Bob',   20, 8000.00);

-- 更新（务必带 WHERE，否则全表更新）
UPDATE employee SET salary = 6500.00 WHERE emp_id = 1;

-- 删除（务必带 WHERE，否则全表删除）
DELETE FROM employee WHERE emp_id = 2;
```

> 避坑：`UPDATE` / `DELETE` 忘记 `WHERE` 会作用于全表，生产环境务必先 `SELECT` 确认影响行数，或开启安全更新模式（SQL_SAFE_UPDATES）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- DDL 会**隐式提交事务**且多数变更会锁表：大表加列/改类型要走 online DDL 或用 gh-ost/pt-osc 等工具，别在业务高峰直接 `ALTER`。
- 生产铁律：`UPDATE` / `DELETE` 必须带 `WHERE`，先在 `SELECT` 上验证条件再改（可用 `LIMIT` 兜底试跑）。
- 类型选择的实操判据：状态用小整数、枚举别用字符串、变长文本用 `VARCHAR`（`CHAR` 只适合定长如 MD5）。

### 🎓 博士生视角
- **金额必须用 `DECIMAL`**：二进制浮点无法精确表示 0.1（0.1 是二进制无限循环小数），`FLOAT/DOUBLE` 做累加会累积误差，而 `DECIMAL` 是十进制定点表示，语义上精确。这是「数值表示」问题而非数据库问题。
- DDL 的本质是**模式演化的原子性**：MySQL 8 的 instant DDL 只改数据字典（元数据），无须重建表；而早期的 copy 算法要重建整表并阻塞写入。
- 列式存储与行式存储的选择，也起源于「读取模式」（OLTP 点查 vs OLAP 扫描）这一访问模式差异。

### 📚 考研者视角
- 自命题常考 **DDL / DML 语句书写**：`CREATE TABLE`（含约束）、`ALTER TABLE`、`INSERT`（多值/子查询插入）、`UPDATE`、`DELETE`。
- 与之配套的常考点是**完整性约束的分类与实现**：实体完整性（主键非空唯一）、参照完整性（外键）、用户定义完整性（CHECK/默认值）。
- 记忆锚点：**精确数值用 `DECIMAL`、近似数值用 `FLOAT/DOUBLE`**；这条在选择题里几乎年年出现。
