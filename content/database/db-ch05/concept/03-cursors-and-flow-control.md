# 03 · 游标与流程控制：一次一记录的过程化补偿

## 一、游标：DECLARE / OPEN / FETCH / CLOSE 与 CONTINUE HANDLER

关系模型的原则是**一次一集合（set-at-a-time）**——你描述「要什么」，不描述「怎么一行行取」。
**游标（cursor）** 是对这条原则的**过程化补偿**：它给结果集装上一个「可逐行推进的句柄」，
让你能用宿主语言（这里是 SQL/PSM）的方式处理每一行。

MySQL 服务器端游标的四个动作与**强制声明顺序**：

```sql
DELIMITER $$
CREATE PROCEDURE p_raise_all(IN p_pct DECIMAL(5,2))
BEGIN
    -- ① 变量声明
    DECLARE v_id   BIGINT;
    DECLARE v_sal  DECIMAL(10,2);
    DECLARE v_done INT DEFAULT 0;                       -- 结束标志
    -- ② 游标声明（必须在变量与 handler 之前/之后的固定位置）
    DECLARE cur_emp CURSOR FOR
        SELECT id, salary FROM employee WHERE status = 1;
    -- ③ 异常/结束条件处理器
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    OPEN cur_emp;                                       -- 打开
    read_loop: LOOP
        FETCH cur_emp INTO v_id, v_sal;                 -- 取一行
        IF v_done = 1 THEN LEAVE read_loop; END IF;     -- 取空了就退出
        UPDATE employee
           SET salary = v_sal * (1 + p_pct / 100)
         WHERE id = v_id;
    END LOOP;
    CLOSE cur_emp;                                      -- 关闭
END$$
DELIMITER ;
```

**`DECLARE` 的顺序是硬性规定**，必须严格按下面的次序，写反直接报错：

```
① 局部变量   DECLARE var ... ;
② 条件       DECLARE cond CONDITION FOR ... ;
③ 游标       DECLARE cur CURSOR FOR ... ;
④ 处理器     DECLARE {CONTINUE|EXIT|UNDO} HANDLER FOR ... ;
```

**`CONTINUE HANDLER FOR NOT FOUND`** 是游标循环的「终止信号产生器」：
当 `FETCH` 取不到行时，SQLSTATE 变成 `02000`（`NOT FOUND`），handler 被激活并把 `v_done` 置 1。
若是 `CONTINUE`，过程继续往下走（所以必须自己 `LEAVE`）；
若是 `EXIT`，则**直接退出当前 `BEGIN...END` 块**（所以 `EXIT` 型 handler 不需要 `v_done` 标志）。

MySQL 服务器端游标的三个限制要记住：**只读（不能 `UPDATE ... WHERE CURRENT OF`）、只向前（不可回滚）、不可滚动**。

### 🧑‍💻 程序员视角
- **第一原则：能用集合操作就别用游标**。上面那个游标逐行循环，等价于一条语句：
  `UPDATE employee SET salary = salary * (1 + p_pct/100) WHERE status = 1;`
  后者是 1 次 SQL 解析 + 1 次执行计划 + 集合级写入，前者是 N 次 `FETCH` + N 次 `UPDATE` 解析。
- 游标真正适用的场景只有三类：① 每行要调用**外部系统/HTTP/消息队列**（无法写成 SQL）；
  ② 逻辑分支极其复杂、用集合表达式写不清楚；③ 需要**分块提交**避免超长事务。
- 分块提交的写法：每处理 1000 行 `COMMIT` 一次，把长事务拆成多个短事务。
  代价是**丧失了跨块的回滚能力**——中途失败只能靠幂等重跑，必须先想清楚幂等键。
- 没有 handler 的游标循环会**死循环**：`FETCH` 取空后不会自动退出，`v_sal` 保持上一次的值，
  于是 `UPDATE` 一直重复执行。这是「数据库 CPU 100% 但 SQL 看不出在干什么」的经典原因。

### 🎓 博士生视角
- 游标是**「一次一集合」与「一次一记录」两种范式的接口**。关系代数里，查询结果是一个集合，
  没有顺序、没有「下一行」的概念；游标强行给它加上顺序与位置，因此它是**违背关系模型纯粹性的补丁**。
  这也解释了为什么游标只能读、不能回滚——一旦允许随机访问，就必须物化整个结果集，代价从 O(1) 内存变 O(N)。
- 实现上，服务器端游标有两种策略：**物化（materialized）** 与 **流式/流水线（pipelined）**。
  MySQL 对服务器端游标倾向于物化到临时表，所以「游标省内存」是个常见误解——
  大结果集 + 游标很可能直接把临时表刷到磁盘。
- 复杂度对比（N 行）：集合操作 = **1 次解析 + 1 次优化 + N 次元组处理**；
  游标 = **N 次 `FETCH` + N 次子语句解析/优化 + N 次元组处理**。
  差距不在元组处理，而在**解析与优化的 N 倍重复**与 N 次客户端/服务器内部交互。
- handler 的 `CONTINUE`/`EXIT` 与编程语言的 `catch` / `catch + return` 是同构的：
  两者都是「异常点 → 恢复点」的映射，只是 SQL/PSM 把控制流写成了声明式前缀。

### 📚 考研者视角
- 数据库不在 408 统考范围，本视角按**课程期末考 + 复试笔试 + 面试**口径整理。
- **游标四步骤必背**：`DECLARE`（声明）→ `OPEN`（打开）→ `FETCH`（提取，循环）→ `CLOSE`（关闭）。
  标准 SQL 里还有 `FETCH` 的定位方式（`NEXT`/`PRIOR`/`FIRST`/`LAST`/`ABSOLUTE`/`RELATIVE`）。
- **常考对比**：**显式游标**（用户 `DECLARE`，可控）vs **隐式游标**（DBMS 为单行 `SELECT`、`INSERT`/`UPDATE`/`DELETE` 自动建立，如 Oracle 的 `SQL%ROWCOUNT`）。
- **易混点**：`EXIT HANDLER`（异常时退出块）与 `CONTINUE HANDLER`（异常时继续执行）必须分清——
  这是存储过程笔试题的高频陷阱，题干常问「下面哪个 handler 不需要额外的结束标志变量」→ `EXIT`。
- **为什么游标慢（标准答法）**：它把「一次一集合」降级为「一次一记录」，
  使数据库无法整体优化与批量写入，导致解析次数、锁持有次数、往返次数都变成 O(N)。

## 二、流程控制：IF / CASE / WHILE / LOOP / REPEAT

存储程序里的流程控制是 SQL/PSM 的过程化骨架，五件套如下：

```sql
-- ① IF / ELSEIF / ELSE
IF v_score >= 90 THEN SET v_grade = 'A';
ELSEIF v_score >= 60 THEN SET v_grade = 'B';
ELSE SET v_grade = 'F'; END IF;

-- ② CASE（两种形态）
CASE v_code                                  -- 简单 CASE：与一个表达式比较
    WHEN 1 THEN SET v_name = 'NEW';
    WHEN 2 THEN SET v_name = 'PAID';
    ELSE SET v_name = 'UNKNOWN';
END CASE;
CASE                                         -- 搜索 CASE：每个 WHEN 是独立条件
    WHEN v_qty = 0 THEN SET v_state = 'EMPTY';
    WHEN v_qty < 10 THEN SET v_state = 'LOW';
    ELSE SET v_state = 'OK';
END CASE;

-- ③ WHILE：先判断，后执行（可能 0 次）
WHILE v_i <= 10 DO
    SET v_sum = v_sum + v_i; SET v_i = v_i + 1;
END WHILE;

-- ④ REPEAT ... UNTIL：先执行，后判断（至少 1 次）
REPEAT
    SET v_i = v_i + 1;
UNTIL v_i > 10 END REPEAT;

-- ⑤ LOOP + 标签 + LEAVE / ITERATE
calc: LOOP
    SET v_i = v_i + 1;
    IF v_i = 5 THEN ITERATE calc; END IF;    -- 相当于 continue
    IF v_i > 10 THEN LEAVE calc; END IF;     -- 相当于 break
    SET v_sum = v_sum + v_i;
END LOOP calc;
```

**`WHILE` 与 `REPEAT` 的唯一本质差异是判定时机**：`WHILE` 是**前测**（条件为假则循环体一次都不执行），
`REPEAT ... UNTIL` 是**后测**（至少执行一次）。`UNTIL` 后的条件为**真时停止**——与直觉的「直到条件成立」一致，但容易与 `WHILE` 写反。

### 🧑‍💻 程序员视角
- 批处理里 `REPEAT ... UNTIL` 与 `WHILE` 的选择是**语义问题不是风格问题**：
  要「至少处理一次」的场景（如「先取一批再判断是否取完」）用 `REPEAT`，
  「条件不满足就完全不动」的场景用 `WHILE`。写反会产生「空表也执行一次」的诡异副作用。
- `LEAVE` / `ITERATE` 必须带**标签**，且标签要写在 `LOOP`/`WHILE`/`REPEAT` 前面。
  没有标签只能用 `LEAVE` 退出最内层；需要跳出多层嵌套时必须用标签。
- 流程控制越多，越应该反问「这段逻辑该不该在数据库里」：
  一个 200 行的 `CASE` + `LOOP` 过程，等价的应用层代码可以被单元测试、被静态分析、被链路追踪——
  而这些能力在存储过程里全部缺失。
- 调试技巧：MySQL 没有存储过程断点调试器，唯一可行的手段是**临时表打点**（把中间变量写入临时表再查）。

### 🎓 博士生视角
- SQL/PSM 的流程控制是**图灵完备**的：`WHILE` + 变量赋值 + 递归调用即可模拟任意计算。
  这意味着存储过程不再是「查询语言」，而是「跑在 DBMS 进程里的通用程序」——
  能力扩张的代价是**丧失了关系语言的可优化性**（优化器无法重写过程化的循环）。
- `WHILE` / `REPEAT` / `LOOP` 三者的形式语义可统一为「带守卫的定点迭代」：
  `WHILE` = 前测定点，`REPEAT` = 后测定点，`LOOP` + `LEAVE` = 无守卫 + 显式跳出。
  与 C 的 `while` / `do-while` / `for(;;)`+`break` 一一对应，这是语言设计上的收敛。
- `LOOP` 末尾的分号归属（`END REPEAT;` vs `END LOOP calc;`）问题，本质是**语句终结符在复合结构中的消歧**；
  这与 `DELIMITER` 要解决的问题是同一个根源：SQL 用分号做终结符，而嵌套结构引入了「内部分号」。
- 复杂度视角：`LOOP` 内嵌 `LOOP` 的嵌套深度 d、每层 N 次迭代 → O(N^d) 次过程化语句解析。
  优化器对这种结构**完全无能为力**，这是「过程化 SQL 难以调优」的形式化原因。

### 📚 考研者视角
- **考点清单（面试/复试）**：`IF`（前测分支）、`CASE`（等值/条件两形态）、
  `WHILE`（前测循环）、`REPEAT`（后测循环）、`LOOP`（无限循环 + `LEAVE` 跳出）、
  `ITERATE`（跳过本次循环）、`LEAVE`（跳出标签块）。
- **最高频陷阱题**：「`WHILE` 和 `REPEAT` 的区别？」标准答：
  `WHILE` 先判断条件后执行循环体，**可能一次都不执行**；`REPEAT` 先执行后判断，**至少执行一次**。
- **易混点**：`ITERATE`（跳过本次、继续下一次）对应 `continue`；`LEAVE`（跳出整个循环/块）对应 `break`。
  二者都**必须带标签**，且标签必须已声明。
- **口径提醒**：`CASE` 在 SQL 里有**两种含义**——查询表达式里的 `CASE WHEN`（可出现在 `SELECT` 列表）
  与存储程序里的 `CASE` **语句**（带 `END CASE`）。笔试常考「`CASE` 是表达式还是语句」→ 两者都有，看语法位置。
