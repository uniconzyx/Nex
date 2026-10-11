# 02 · 触发器：ECA 模型、BEFORE/AFTER 时序与 NEW/OLD 行镜像

## 一、触发器的 ECA 模型与 BEFORE / AFTER 时序

触发器（trigger）是**由数据修改事件自动激活**的一段过程化代码，用户**不能显式调用**它。
教科书把它形式化为 **ECA 模型**：

```
E (Event)     : INSERT / UPDATE / DELETE  (可加 OF col 限定列)
C (Condition) : WHEN 子句 (可选)
A (Action)    : BEGIN ... END 内的过程化语句
```

MySQL 的触发器有两个硬约束：**只支持行级触发（隐式 `FOR EACH ROW`）**，且**一个事件同一时序只能有一个触发器**（5.7 起放宽为可多个同类触发器，按创建顺序执行）。

```sql
DELIMITER $$
CREATE TRIGGER trg_emp_bu
BEFORE UPDATE ON employee
FOR EACH ROW
BEGIN
    IF NEW.salary < 0 THEN
        SET NEW.salary = 0;          -- BEFORE 才能改 NEW
    END IF;
END$$
DELIMITER ;
```

执行时序（`DML 语句 → BEFORE 触发器 → 约束检查与写盘 → AFTER 触发器`）：

```
   UPDATE employee SET salary = 9000 WHERE id = 2;
        |
        v
   [BEFORE UPDATE 触发器]  <- 能读写 NEW 和 OLD; 能改写 NEW.salary
        |
        v
   [约束检查: NOT NULL / UNIQUE / 外键 / CHECK]
        |
        v
   [实际写入数据页 + 维护所有二级索引]
        |
        v
   [AFTER UPDATE 触发器]   <- 只能读 NEW/OLD; 改写 NEW 无效
```

`BEFORE` 与 `AFTER` 的选择原则：**要「改变即将写入的行」用 `BEFORE`，要「记录/联动已发生的事实」用 `AFTER`**。

### 🧑‍💻 程序员视角
- 生产建议：**默认用 `AFTER`**。`BEFORE` 改写 `NEW` 会让最终落库的值与 SQL 语句字面不一致，
  排查数据问题时极易误判（「我明明写的 9000，为什么库里是 8000」）。
- MySQL 触发器有一条硬限制必须记住：**触发器内部不能对本表执行 `INSERT/UPDATE/DELETE`**，
  会报 `ERROR 1442 (HY000): Can't update table 'employee' because it is already being used by this statement`。
  想在触发器里「修正本行」只能走 `BEFORE ... SET NEW.col = ...`。
- 主从复制风险：如果 binlog 是 `STATEMENT` 格式，触发器在从库会被**再次执行**，
  若触发器里含 `NOW()`、`RAND()`、`UUID()` 等非确定性调用，主从数据立刻分叉。
  结论：用触发器就必须配 `binlog_format = ROW`。
- 排查体验极差：`INSERT` 报错却指向触发器里的某行，`SHOW TRIGGERS` 才看得到。
  常规做法是把触发器**登记在案**（谁建的、干什么、什么条件删除），避免变成「幽灵逻辑」。

### 🎓 博士生视角
- ECA 模型源自**主动数据库（active database）**研究，触发器是它的数据库实现形态。
  它把「约束的检查」从应用层下沉到了 DBMS，代价是引入了**隐式控制流**——
  破坏了「SQL 语句的语义 = 语句本身」这一可组合性（compositionality）性质。
- `BEFORE` 的本质是**对元组写入前的拦截点**，因此它拥有对行镜像的写权限；
  `AFTER` 是**写盘后的通知点**，行镜像已成为历史，只读是自然结果。
  这套「hook 点 + 行镜像」的设计与 ORM 的 `beforeSave` / `afterSave` 回调、编译器 pass 的插桩点同源。
- 行级触发器的复杂度要单独算：一条影响 N 行的语句 → 触发器被执行 **N 次**。
  因此 `UPDATE big_table SET ...` 这类批量语句的实际代价是 `O(N × 触发器体代价)`，
  与大表上的「一次全表更新」组合会产生灾难性的放大——这就是「导入数据时先 `DROP TRIGGER`」的经验来源。
- 触发器执行在**与触发它的 DML 语句相同的事务**上下文中，因此具备原子性：
  DML 回滚时触发器写入也一并回滚。但它**不能**用来保证「跨库/跨实例」的一致性——
  事务边界仍然是单个 DBMS 实例。

### 📚 考研者视角
- **必背定义**：触发器是「用户定义在关系表上的一类由事件驱动的特殊过程，
  一旦定义便存储在数据库中，任何对表的增删改操作都会自动激活相应的触发器」。
- **ECA 三要素**（Event-Condition-Action）是标准考点，一定要能展开成「事件 / 条件 / 动作」并各举一例。
- **常考对比**：触发器 vs 存储过程 → ① 触发器**自动触发**、不能被 `CALL`；过程**必须显式调用**；
  ② 触发器绑定在表上、随表删除而失效；过程是独立对象；
  ③ 触发器没有参数，过程有参数模式。
- **优缺点标准答案**：优点 = 集中实现复杂约束、自动执行不依赖应用、保护数据完整性；
  缺点 = 逻辑隐蔽难调试、行级触发开销随行数放大、移植性差、可能造成级联/递归。
- **易混点**：`ASSERTION`（断言）是标准 SQL 的完整约束，MySQL **不支持**；
  触发器是它的「过程化替代品」。这条常在数据库原理的选择题里出现。

## 二、NEW / OLD 行镜像的可用性矩阵与审计日志落地

`NEW` 与 `OLD` 是触发器里两个**行镜像**（row image）伪记录，分别代表「修改后的行」和「修改前的行」。
它们的可用性由事件决定，且是**硬性矩阵**，写错就是编译期错误：

| 事件 | `OLD` | `NEW` | 备注 |
|---|---|---|---|
| `INSERT` | **不可用** | 可用 | 只有「新行」，没有「旧行」 |
| `UPDATE` | 可用 | 可用 | 二者都有，才能算出「变化量」 |
| `DELETE` | 可用 | **不可用** | 只有「旧行」 |

审计日志是最经典的触发器落地场景：**任何对工资的改动都必须留痕，且应用层无法绕过**。

```sql
CREATE TABLE salary_audit (
    audit_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    emp_id     BIGINT,
    old_salary DECIMAL(10,2),
    new_salary DECIMAL(10,2),
    op         VARCHAR(8),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

DELIMITER $$
CREATE TRIGGER trg_salary_au
AFTER UPDATE ON employee
FOR EACH ROW
BEGIN
    IF NEW.salary <> OLD.salary THEN          -- 只在真正变化时留痕
        INSERT INTO salary_audit(emp_id, old_salary, new_salary, op)
        VALUES (OLD.id, OLD.salary, NEW.salary, 'UPDATE');
    END IF;
END$$
DELIMITER ;
```

注意三个工程细节：① 审计表**不设外键**（否则删除员工时审计记录会被连带约束）；
② 只在 `<>` 时才写（避免无效留痕把审计表撑爆）；
③ 审计写入必须在**同一事务**内，才能保证「业务写了、审计没写」这种不一致不出现。

### 🧑‍💻 程序员视角
- 审计表设计惯例：**不建外键、不建触发器、只追加不更新**（append-only），
  并对应用账号**只授 `INSERT`/`SELECT` 权限**，防止应用反过来篡改审计。
- 排查经验：审计表突然暴涨，先看是不是有人写了「无条件留痕」的 `AFTER UPDATE`——
  批量 `UPDATE t SET status=0` 会按行数写等量审计行。
- 另一种常见诉求是「审计只需要知道谁改的」：MySQL 触发器里可用 `CURRENT_USER()` 拿到**登录账号**，
  但注意它拿不到业务用户（谁在 App 里点的按钮），所以真正的 who 通常还是要在业务表上加 `updated_by` 列。
- 慎用触发器做业务联动（如「下单后自动扣库存」）：级联逻辑一旦写进触发器，
  应用层的可观测性（链路追踪、埋点、幂等控制）全部失效，出问题只能靠数据库日志。

### 🎓 博士生视角
- `NEW`/`OLD` 只是**语法上的伪记录**，语义上是「行版本的投影」。形式化地，对一行 `r`：
  `OLD = r_after_where_but_before_set`，`NEW = r_after_set`。这解释了为什么
  `UPDATE` 的 `BEFORE` 阶段 `NEW` 反映的是**已应用 `SET` 但尚未落盘**的值。
- 矩阵的完备性来自**事件与行版本数量的对应**：`INSERT` 引入 1 个新版本（无旧版本），
  `DELETE` 移除 1 个旧版本（无新版本），`UPDATE` 是一次「旧版本 → 新版本」的替换。
  三者恰好是行版本集合上的三个基本操作。
- 审计的一致性论证：由于触发器与 DML 共享事务，审计行与业务行的提交/回滚是原子的；
  这使审计表满足**「不可分离性」（no lost audit）**：不存在「业务成功而审计缺失」的中间状态。
  代价是审计写入被拉进了业务事务的**临界路径**，会延长持锁时间。
- 与数据库理论的关系：触发器实现的是**事件-条件-动作规则**，属于「主动规则系统」；
  SQL:1999 起标准明确了触发器语义，但各实现的**触发时序、级联行为、递归策略**从未统一——
  这正是「有触发器的系统难移植」的理论根据。

### 📚 考研者视角
- **矩阵必背**：`INSERT` 只有 `NEW`、`DELETE` 只有 `OLD`、`UPDATE` 两者都有。
  这是最高频的触发器选择题，几乎每次都考。
- **常考问法**：「在 `DELETE` 触发器中想引用 `NEW.列名`，会怎样？」→ 语法/编译错误（`NEW` 在该事件下无定义）。
- **`BEFORE` 与 `AFTER` 的考点**：只有 `BEFORE` 型触发器**可以修改 `NEW` 行镜像**（常用于数据校验与规范化）；
  `AFTER` 型不能。答「用触发器实现字段默认值修正」应选 `BEFORE`。
- **口径提醒**：教材称触发器为「**由事件驱动的特殊过程**」，并强调它**没有参数**、**不能被显式调用**。
- **易混点**：触发器的 `FOR EACH ROW`（行级，每行执行一次）与 `FOR EACH STATEMENT`（语句级，整条语句一次）
  是标准 SQL 的两种粒度；**MySQL 只有行级**，这是它的方言限制，答题时要区分「标准」与「MySQL 实现」。
