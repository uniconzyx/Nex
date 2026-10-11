# db-ch05 · 陷阱清单：存储过程 / 触发器 / 游标最容易错的十四件事

1. **忘记 `DELIMITER`，过程体被分号切碎** —— 客户端默认以 `;` 判定「语句结束、可以发送」，`BEGIN ... END` 内部的 `;` 会让它提前发送半截语句，报 `ERROR 1064` 且错误位置指向 `BEGIN` 或内部分号。正确做法：`DELIMITER $$` 定义、`END$$` 收尾、最后 `DELIMITER ;` 恢复。

2. **以为 `DELIMITER` 是服务器语法** —— 它是**客户端指令**（命令行/Navicat 的解析约定），**不会发给服务器**。因此「同一段 `CREATE PROCEDURE` 在命令行报错、在 JDBC 里却可能通过」并不矛盾。

3. **以为 `OUT` 参数能读到调用者传入的值** —— `OUT` 形参在**过程入口被重置为 `NULL`**，只负责「带出」结果，读取它拿不到任何输入。要「既读又写」必须用 `INOUT`。

4. **把 `OUT`/`INOUT` 的实参写成常量** —— `CALL p(1, 2, 3)` 中第 3 个若是 `OUT` 参数会直接报错：可写实参必须是**用户变量（`@v`）或局部变量**。正确写法：`CALL p(1, 2, @out); SELECT @out;`。

5. **`DECLARE` 顺序写反** —— 存储程序内必须严格按「局部变量 → 条件 → 游标 → 处理器」的顺序声明，顺序错误直接语法报错。这条几乎没有例外。

6. **游标循环没有 `CONTINUE HANDLER FOR NOT FOUND`** —— 没有终止信号，`FETCH` 取空后不会退出，`LOOP` 无限执行、反复 `UPDATE` 同一行，典型症状是「数据库 CPU 打满、`SHOW PROCESSLIST` 看到同一条 `UPDATE`」。

7. **混淆 `CONTINUE` 与 `EXIT` 型 handler** —— `CONTINUE HANDLER` 触发后**继续执行**（所以必须自己写 `IF done = 1 THEN LEAVE ...` 退出）；`EXIT HANDLER` 触发后**退出当前 `BEGIN...END` 块**（不需要 `done` 标志）。二者混用会造成「循环提前退出」或「死循环」两种相反的 bug。

8. **用 `INSERT`/`DELETE` 触发器的 `NEW`/`OLD` 写错对象** —— `INSERT` 只有 `NEW`、`DELETE` 只有 `OLD`、`UPDATE` 两者都有。`DELETE` 触发器里引用 `NEW.col` 会直接报无定义。

9. **在 MySQL 触发器里对本表做增删改** —— 会报 `ERROR 1442: Can't update table ... because it is already being used by this statement`（MySQL 的限制）。想修正本行只能用 `BEFORE ... SET NEW.col = ...`。

10. **用触发器做业务联动，遭遇批量语句放大** —— 行级触发器对「一条影响 N 行的语句」执行 **N 次**。`UPDATE big_table SET status = 0` 加上触发器可能变成 N 次触发器逻辑 + N 次审计写入；因此批量导入/大表更新前应先 `DROP TRIGGER`、事后再建。

11. **触发器里写非确定性函数（`NOW()`/`RAND()`/`UUID()`）却没把 binlog 设成 ROW** —— 基于 `STATEMENT` 的复制会在从库**再次执行**触发器，导致主从数据分叉。用触发器必须配 `binlog_format = ROW`。

12. **在存储过程/函数/触发器内部写 `COMMIT`/`ROLLBACK`** —— 这会**结束调用者的事务**，使「外层回滚」只能回滚到过程提交之后，原子性被破坏。事务边界必须由应用层统一控制。

13. **在事务里混用 DDL 与 DML 并期望原子性** —— MySQL 的 `CREATE/ALTER/DROP TABLE` 会**隐式提交**当前事务，事务被强制切断，无法整体回滚（PostgreSQL 的 DDL 是事务性的，两库行为不同）。

14. **以为「存储过程能防 SQL 注入」** —— 过程本身不防注入；过程内若用 `CONCAT` 拼接用户输入再 `PREPARE ... FROM @sql`，一样会被注入。正确做法是值用 `?` 占位符 + `EXECUTE ... USING`，标识符（表名/列名/排序方向）走**枚举白名单**。
