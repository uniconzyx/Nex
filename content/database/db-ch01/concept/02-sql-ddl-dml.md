# 02 · DDL 与 DML（建表、改表与增删改）

SQL 分为 DDL（数据定义）与 DML（数据操作）两大类。

这个划分不只是"管结构"和"管数据"的方便说法，它对应**事务语义**的根本差异：DDL 在多数数据库里会**隐式提交**当前事务，DML 才可以回滚。搞混这一点，是"我明明在事务里，为什么 ALTER 把前面的操作提交了"这类事故的根源。

## 一、SQL 的五大类

| 类别 | 全称 | 语句 | 是否可回滚 |
|---|---|---|---|
| DDL | Data Definition | `CREATE` / `ALTER` / `DROP` / `TRUNCATE` | MySQL 中隐式提交，不可回滚（PG 可） |
| DML | Data Manipulation | `INSERT` / `UPDATE` / `DELETE` | 可（在事务内） |
| DQL | Data Query | `SELECT` | 只读 |
| DCL | Data Control | `GRANT` / `REVOKE` | — |
| TCL | Transaction Control | `BEGIN` / `COMMIT` / `ROLLBACK` | — |

`TRUNCATE` 归 DDL 是个常见误解点：它按页释放数据、不写逐行 undo，因此不能回滚、会重置自增、不触发行级触发器。

## 二、DDL：定义结构

```sql
-- 建表
CREATE TABLE employee (
    emp_id  INT PRIMARY KEY AUTO_INCREMENT,
    name    VARCHAR(20) NOT NULL,
    dept_id INT,
    salary  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    hired   DATE,
    status  TINYINT NOT NULL DEFAULT 1,
    CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
);

-- 改表：加列（8.0 instant DDL，秒级完成）
ALTER TABLE employee ADD COLUMN hire_date DATE;

-- 改表：加索引、加唯一约束
ALTER TABLE employee ADD UNIQUE KEY uk_name (name);
ALTER TABLE employee ADD INDEX idx_dept (dept_id);

-- 删表
DROP TABLE IF EXISTS employee;
```

### 约束的六种形态

- `PRIMARY KEY`：非空 + 唯一，一张表一个（可复合）。
- `UNIQUE`：唯一但允许多个 `NULL`（`NULL` 不等于 `NULL`）。
- `NOT NULL`：禁止空值。
- `DEFAULT`：缺省值。
- `CHECK`：行级条件（MySQL 8.0.16 起才真正生效，此前只是语法解析）。
- `FOREIGN KEY`：引用完整性，可配 `ON DELETE CASCADE` / `ON UPDATE SET NULL`。

### `ALTER TABLE` 的代价：三种算法

- **COPY**：建新表 → 逐行拷数据 → 改名。全程锁写，大表上可能是小时级。
- **INPLACE**：原地重建（如加二级索引），允许并发 DML 但需额外磁盘。
- **INSTANT**：只改数据字典（8.0.12 起支持加列到末尾、8.0.29 起支持任意位置），毫秒级。

生产上给大表加列/改类型必须走 `ALGORITHM=INPLACE/INSTANT` 或外部工具（gh-ost、pt-online-schema-change），别在业务高峰直接 `ALTER`。

## 三、DML：增删改

```sql
-- 插入（显式列名最稳妥：加列后旧语句不会错位）
INSERT INTO employee (emp_id, name, dept_id, salary)
VALUES (1, 'Alice', 10, 6000.00),
       (2, 'Bob',   20, 8000.00);

-- 从查询结果插入
INSERT INTO employee_archive (emp_id, name)
SELECT emp_id, name FROM employee WHERE status = 0;

-- 更新（务必带 WHERE）
UPDATE employee SET salary = 6500.00 WHERE emp_id = 1;

-- 删除（务必带 WHERE）
DELETE FROM employee WHERE emp_id = 2;
```

### UPSERT：`ON DUPLICATE KEY UPDATE`

```sql
INSERT INTO employee (emp_id, name, salary) VALUES (1, 'Alice', 7000.00)
ON DUPLICATE KEY UPDATE salary = VALUES(salary);
```

命中主键/唯一键冲突时转为更新。注意它依赖唯一约束的存在，且**自增主键会被消耗**（冲突也会推进 `AUTO_INCREMENT`）。MySQL 8.0.20 起推荐用别名语法 `AS new` 代替已废弃的 `VALUES()`。

### 批量操作与事务边界

```sql
START TRANSACTION;
UPDATE account SET balance = balance - 100 WHERE id = 1;
UPDATE account SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

转账这类操作必须在同一事务里，否则中间失败会造成资金不平。注意**先减后加与先加后减的死锁概率不同**：固定顺序（按 id 升序）加锁能显著降低死锁。

## 四、数据类型的选择：四个关键判断

### 金额用 `DECIMAL` 而不是 `FLOAT/DOUBLE`

二进制浮点无法精确表示 0.1（0.1 是二进制无限循环小数），累加会产生误差；`DECIMAL(10,2)` 是十进制定点表示，语义精确。这是"数值表示"问题，不是数据库问题。

### `VARCHAR` 与 `CHAR`

- `VARCHAR(n)`：变长，适合姓名、地址、标题。存储实际长度 + 1~2 字节长度前缀。
- `CHAR(n)`：定长，适合长度恒定的值（MD5、国家代码、定长编码），尾部空格会被填充。

### `DATETIME` 与 `TIMESTAMP`

- `DATETIME`：8 字节，范围 1000~9999 年，**不做时区转换**（存的是什么就是什么）。
- `TIMESTAMP`：4 字节，范围 1970~2038 年，**按会话时区转换**，且支持自动更新（`ON UPDATE CURRENT_TIMESTAMP`）。

跨时区系统用 `TIMESTAMP` + UTC 会话时区，或统一用 `DATETIME` 存 UTC（应用层转换）。混用会出"同一个事件在两个服务里差 8 小时"的事故。

### 状态/枚举用 `TINYINT` 而不是字符串

`status TINYINT` 占 1 字节、可索引、比较快；`status VARCHAR(20)` 占 20 字节且容易拼错。枚举值在应用层用常量或枚举类映射。

## 五、`UPDATE` / `DELETE` 的安全流程

1. **先 `SELECT` 同条件**，确认行数与内容符合预期。
2. 加 `LIMIT` 试跑（`UPDATE ... WHERE ... LIMIT 10`）。
3. 生产环境开启 `SQL_SAFE_UPDATES`（禁止无 `WHERE` 或无 `LIMIT` 的更新）。
4. 大表分批处理（按主键范围切批），避免长事务与主从延迟。
5. `DELETE` 之后 `TRUNCATE` 不能反悔，重要数据先 `CREATE TABLE ... AS SELECT` 备份。

```text
危险语句的检查清单

  UPDATE / DELETE
    ├─ 有 WHERE 吗？          无 → 全表操作，事故
    ├─ WHERE 用到索引吗？      否 → 锁全表扫描的行
    ├─ 影响行数是多少？        超大 → 拆批
    └─ 在事务里吗？            是 → 注意长事务与 undo 膨胀
```

## 六、边界与陷阱

- **`UPDATE`/`DELETE` 忘 `WHERE`**：全表操作，最常见也最致命。
- **DDL 隐式提交**：`START TRANSACTION; INSERT ...; ALTER TABLE ...; ROLLBACK;` 中 `ROLLBACK` 无效，`INSERT` 已提交。
- **`TRUNCATE` 不可回滚**：且会重置 `AUTO_INCREMENT`。
- **`INSERT` 不写列名**：表加列后列数不匹配，或值错位。
- **`ALTER TABLE` 锁表**：大表用 COPY 算法会长时间阻塞写入。
- **`VARCHAR(255)` 一统天下**：`VARCHAR` 长度影响索引长度限制（InnoDB 单列索引 767/3072 字节），乱设会撞上限。
- **唯一约束允许多个 `NULL`**：想"必填且唯一"必须 `NOT NULL` + `UNIQUE` 一起加。

## 七、可运行示例：建表、UPSERT 与安全更新

```sql
CREATE TABLE account (
    id      INT PRIMARY KEY,
    owner   VARCHAR(20) NOT NULL,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status  TINYINT NOT NULL DEFAULT 1,
    UNIQUE KEY uk_owner (owner)
);

INSERT INTO account (id, owner, balance) VALUES (1,'Alice',1000.00), (2,'Bob',500.00);

-- UPSERT：冲突则更新
INSERT INTO account (id, owner, balance) VALUES (1,'Alice',1200.00) AS new
ON DUPLICATE KEY UPDATE balance = new.balance;

-- 转账：两条语句必须在同一事务
START TRANSACTION;
UPDATE account SET balance = balance - 200.00 WHERE id = 1;
UPDATE account SET balance = balance + 200.00 WHERE id = 2;
COMMIT;

SELECT * FROM account ORDER BY id;
```

`DECIMAL(10,2)` 保证 `balance` 的加减精确到分；`AS new` 别名语法是 MySQL 8.0.20+ 的推荐写法（旧的 `VALUES(col)` 已废弃）。

## 三视角解析

### 🧑‍💻 程序员视角
- DDL 会**隐式提交事务**且多数变更会锁表：大表加列/改类型要走 online DDL 或用 gh-ost/pt-osc 等工具，别在业务高峰直接 `ALTER`。
- 生产铁律：`UPDATE` / `DELETE` 必须带 `WHERE`，先在 `SELECT` 上验证条件再改（可用 `LIMIT` 兜底试跑）。
- 类型选择的实操判据：状态用小整数、枚举别用字符串、变长文本用 `VARCHAR`（`CHAR` 只适合定长如 MD5）。
- 建表时一次性想清楚约束（非空、唯一、默认值），事后补 `NOT NULL` 要扫全表且可能失败（已有 `NULL` 数据）。

### 🎓 博士生视角
- **金额必须用 `DECIMAL`**：二进制浮点无法精确表示 0.1（0.1 是二进制无限循环小数），`FLOAT/DOUBLE` 做累加会累积误差，而 `DECIMAL` 是十进制定点表示，语义上精确。这是「数值表示」问题而非数据库问题。
- DDL 的本质是**模式演化的原子性**：MySQL 8 的 instant DDL 只改数据字典（元数据），无须重建表；而早期的 copy 算法要重建整表并阻塞写入。
- 列式存储与行式存储的选择，也起源于「读取模式」（OLTP 点查 vs OLAP 扫描）这一访问模式差异。
- `TRUNCATE` 之所以快，是因为它按**区/页**释放而非逐行删并写 undo；代价是不可回滚、不触发触发器、重置自增。这是"用语义换性能"的典型取舍。
- `ON DUPLICATE KEY UPDATE` 的语义依赖唯一索引冲突检测，因此**没有唯一约束时它退化为普通 INSERT**；`REPLACE INTO` 则是"删除 + 插入"，会重置未指定的列并触发 `DELETE` 级联，比 UPSERT 危险得多。

### 📚 考研者视角
- 自命题常考 **DDL / DML 语句书写**：`CREATE TABLE`（含约束）、`ALTER TABLE`、`INSERT`（多值/子查询插入）、`UPDATE`、`DELETE`。
- 与之配套的常考点是**完整性约束的分类与实现**：实体完整性（主键非空唯一）、参照完整性（外键）、用户定义完整性（CHECK/默认值）。
- 常考辨析：`DELETE`（DML，可回滚，逐行，可带 `WHERE`）vs `TRUNCATE`（DDL，不可回滚，重置自增）vs `DROP`（删表结构与数据）。
- 记忆锚点：**精确数值用 `DECIMAL`、近似数值用 `FLOAT/DOUBLE`**；这条在选择题里几乎年年出现。
