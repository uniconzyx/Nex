# 01 · 存储过程与自定义函数：定义、DELIMITER 与参数模式

## 一、存储过程与自定义函数：定义、调用与差异

**存储过程（stored procedure）** 是**在数据库服务器内命名保存、由客户端显式调用**的一组 SQL/过程化语句；
**自定义函数（stored function）** 同样保存在服务器内，但它出现在**表达式**里、并**必须返回一个标量值**。

MySQL 中两者的最小完整定义（注意 `DELIMITER` 的用法在第二节解释）：

```sql
DELIMITER $$
CREATE PROCEDURE p_add_employee(
    IN  p_name   VARCHAR(20),
    IN  p_salary DECIMAL(10,2),
    OUT p_new_id BIGINT
)
BEGIN
    INSERT INTO employee(name, salary) VALUES (p_name, p_salary);
    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

CALL p_add_employee('Tom', 8000.00, @uid);
SELECT @uid;
```

```sql
DELIMITER $$
CREATE FUNCTION f_tax(p_salary DECIMAL(10,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
NO SQL
BEGIN
    RETURN p_salary * 0.10;
END$$
DELIMITER ;

SELECT f_tax(8000.00);          -- 出现在表达式位置
```

四条核心差异（面试与笔试的标准对比口径）：

| 维度 | 存储过程 `PROCEDURE` | 自定义函数 `FUNCTION` |
|---|---|---|
| 调用方式 | `CALL p(...)` 独立语句 | 嵌在表达式里 `f(x)`、`WHERE f(col)=1` |
| 返回值 | 0 个或多个（`OUT` / `INOUT` / 直接 `SELECT` 结果集） | **恰好 1 个标量值**（`RETURNS` 声明类型） |
| 事务控制 | **可以**含 `COMMIT` / `ROLLBACK` | **不可以**含事务控制语句 |
| 能否返回结果集 | 可以（过程体内直接 `SELECT`） | 不可以 |

函数还有一条过程没有的要求：必须声明**确定性**，即 `DETERMINISTIC` 或 `NOT DETERMINISTIC`，
以及数据访问类别 `CONTAINS SQL` / `NO SQL` / `READS SQL DATA` / `MODIFIES SQL DATA`。
声明不实会直接影响**基于 statement 的 binlog 主从复制**的正确性。

### 🧑‍💻 程序员视角
- 工程上先问一句「这段逻辑要不要出现在 `WHERE` 里」：要在 `WHERE` 里被逐行调用 → 只能是函数；
  只是「一次调用做完一件事」→ 存储过程。这是第一刀切分。
- 函数进 `WHERE` 有隐患：MySQL 5.7 会在**外层查询的每一行**都调用一次函数（无法缓存），
  10 万行的扫描就是 10 万次函数调用 + 10 万次服务器内部解析，比直接写 SQL 慢几个数量级。
  `WHERE f(col) = 1` 还同时废掉了 `col` 上的索引。
- 运维现实：程序体现在 `information_schema.ROUTINES` 与 `SHOW CREATE PROCEDURE` 里，
  但它**不在代码仓库里**；因此必须把 `CREATE PROCEDURE` 脚本纳入版本管理与发布流水线，
  否则「谁在什么时候改了过程体」根本查不到——这是最常见的生产事故来源。

### 🎓 博士生视角
- 存储过程属于 SQL 标准的**持久存储模块（SQL/PSM，ISO/IEC 9075-4）**。各厂商方言不同：
  Oracle 是 PL/SQL、SQL Server 是 T-SQL、MySQL 是接近于 SQL/PSM 的自有语法，可移植性天生为零。
- 执行模型有两种：**解释执行**（每次调用解析过程体）与**预编译/字节码**（首次调用编译成内部指令后缓存）。
  MySQL 属于后者，因此首次 `CALL` 有编译开销、后续调用低。
- 收益的第一性来源是**消灭网络往返（RTT）**：客户端—服务器架构诞生时（Sybase / Oracle 7 时代）
  网络带宽与延迟是主要瓶颈，把 100 条 SQL 压成 1 次 `CALL` 能显著减少往返。
  这个前提在今天的同机房（< 0.5 ms RTT）内网下已经**大幅弱化**，这正是存储过程式微的技术根因。
- 函数与过程的差异不是「实现细节」，而是**语言文法位置决定的**：函数出现在表达式的语法槽位里，
  所以语言必须保证它可以被求值任意次（幂等/确定性要求）、无副作用（不得提交事务）；
  过程出现在语句槽位里，因此自由得多。

### 📚 考研者视角
- 数据库不在 408 统考四门（数据结构/组成原理/操作系统/计算机网络）之内，故本视角按
  **考研复试笔试 + 数据库课程期末考 + 校招面试** 口径整理。
- **标准定义（背）**：存储过程是「为实现特定功能而预先编译并存储在数据库服务器中的一组 SQL 语句集合，
  通过过程名和参数调用」。函数是「有返回值的过程化 SQL 单元，可出现在表达式中」。
- **常考对比题**：存储过程与函数的三点区别 → ① 函数必须有且仅有一个返回值，过程可无；
  ② 过程可用 `OUT/INOUT` 带出多个值，函数不行；③ 函数通常用于计算、过程通常用于业务动作。
- **易混点**：`CALL` 是**语句**而非表达式，所以 `SELECT p(...)` 报错；
  反过来函数可以 `SELECT f(...)`。这条经常被写成选择题。
- **口径提醒**：教材（《数据库系统概论》王珊版）把存储过程与触发器统称为 SQL 的**过程化扩展**，
  其动机是「弥补 SQL 非过程化的不足」，答卷时最好点出这个动机。

## 二、参数模式 IN / OUT / INOUT 与 DELIMITER 的作用

**参数模式**决定形参在过程体内如何被初始化、修改是否回传：

| 模式 | 进入过程时的初值 | 过程内可读 | 过程内可写 | 修改是否回传调用者 | 典型用途 |
|---|---|---|---|---|---|
| `IN`（默认） | 调用者传入的值 | 是 | 是（仅本地副本） | **否** | 输入条件 |
| `OUT` | **被重置为 `NULL`** | 是（但为 NULL） | 是 | **是** | 带回计算结果 |
| `INOUT` | 调用者传入的值 | 是 | 是 | **是** | 累加器、状态回传 |

```sql
DELIMITER $$
CREATE PROCEDURE p_discount(
    IN    p_amount  DECIMAL(10,2),   -- 只读副本
    IN    p_rate    DECIMAL(5,4),    -- 只读副本
    OUT   p_final   DECIMAL(10,2),   -- 进入即 NULL, 由过程写回
    INOUT p_counter INT              -- 保留初值, 可读可写
)
BEGIN
    SET p_final = p_amount * (1 - p_rate);
    SET p_counter = p_counter + 1;
END$$
DELIMITER ;
```

**`DELIMITER` 是客户端指令**（`mysql` 命令行、Navicat、JDBC 的部分工具等的解析约定），
**不会发给服务器**。原因：复合语句 `BEGIN ... END` 内部本身含 `;`，
而客户端默认以 `;` 作为「语句结束、可以发送了」的信号，
于是会在 `SET @a = x + 1;` 处就把半截语句发出去，服务器自然报 1064 语法错误。

```sql
DELIMITER $$                    -- 仅客户端行为: 把结束符从 ; 改为 $$
CREATE PROCEDURE p_inc(IN x INT)
BEGIN
    SET @a = x + 1;             -- 这个分号现在只是过程体内部的分号
    INSERT INTO t(v) VALUES (@a);
END$$                           -- 客户端在这里才认为语句结束
DELIMITER ;                     -- 恢复默认, 否则后续每条语句都要用 $$ 结尾
```

### 🧑‍💻 程序员视角
- `OUT` 参数最反直觉的地方：**它不是「不传值」，而是「进去以后被清空」**。
  调试时看到 `OUT` 形参在过程开头是 `NULL` 是正常的；而在调用端必须用一个用户变量接住：
  `CALL p_discount(100.00, 0.15, @f, @c); SELECT @f, @c;`。
- 忘写 `DELIMITER` 的报错长这样：`ERROR 1064 (42000)`，且指向 `BEGIN` 附近 ——
  看到这个组合（错误位置在 `BEGIN` 或第一个内部分号处）第一反应就是结束符没改。
- `DELIMITER ;` 一定要在过程定义之后**恢复**，否则同一个会话里后面所有语句都得用 `$$` 收尾，
  排错时非常容易被自己坑。
- 工程惯例：把「参数模式」当接口契约写进文档 —— 哪些参数是 `OUT`/`INOUT` 直接决定调用方要不要准备用户变量。

### 🎓 博士生视角
- 三种模式本质上是**值语义 vs 引用语义 + 初始化策略**的三种组合：
  `IN` = 值传递（过程内的赋值只作用于栈上的形参副本）；
  `OUT` = 新分配一块存储、初始化为 `NULL`、返回时拷回；
  `INOUT` = 拷入 + 拷回。
  这与 C++ 的「传值 / 出参指针 / 引用参数」是同一组语义在不同语言表面的映射。
- MySQL 里 `OUT`/`INOUT` 的实际载体是**用户变量（`@var`）或过程/函数本地变量**，
  不能是字面量；这是编译器对「可写实参」的语法约束（lvalue 要求）——与 C++ 引用参数不能绑定临时量同理。
- `DELIMITER` 的存在暴露了一个深刻事实：**SQL 语句的边界不由语法决定，而由客户端约定**。
  服务器端的语法分析器其实能识别 `BEGIN...END` 块（`CREATE PROCEDURE` 内部是完整语法树）；
  需要 `DELIMITER` 的只有「逐条切分再发送」的**文本协议客户端**。
  换成走二进制协议、整段发送的驱动（如 JDBC 的 `allowMultiQueries`），问题表现就不同——
  这解释了为什么「同一条 `CREATE PROCEDURE`，命令行报错、JDBC 却可能通过」。

### 📚 考研者视角
- **考点口径**：`IN` 是默认模式；`OUT` 进入时为 `NULL`；`INOUT` 兼具两者。
  常考判断题：「`OUT` 参数可以先读调用者传入的值」→ **错**（已被置 NULL）。
- **易混点**：局部变量（`DECLARE`，仅在过程/函数内有效）与用户变量（`@var`，会话级、跨语句有效）
  是两种东西。`CALL` 的 `OUT/INOUT` 实参**必须是用户变量或局部变量**，写常量会报错。
- 笔试常问「为什么定义存储过程要先写 `DELIMITER`」：答「客户端默认以分号作为语句结束符，
  过程体内含分号会导致客户端提前截断发送」，并强调「`DELIMITER` 是客户端指令、不提交服务器」。
- 相关的标准概念是「SQL 语句分隔符（statement terminator）」，
  在嵌入式 SQL 里对应 `EXEC SQL ... END-EXEC` 的定界方式 —— 都是「如何界定一条语句」的问题。
