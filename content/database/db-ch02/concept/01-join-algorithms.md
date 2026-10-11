# 01 · JOIN 的执行算法：从"双重循环"到 Hash/Merge Join

> 博士视角看"关联"的算法本质，程序员视角看"InnoDB 到底怎么跑我的 JOIN"。

## 1. 理论根基：JOIN 是两个关系的「笛卡尔积 + 选择」

关系代数里，`R ⋈ S` 的严格定义是 `σ_cond(R × S)`：先对两表做笛卡尔积（行数 = |R|×|S|），再用连接条件做选择。**朴素实现是 O(|R|·|S|)**，对两张大表不可接受。所有 JOIN 算法都是在"避免物化完整笛卡尔积"这一目标下的工程折中。

设外表（驱动表）行数 M、内表（被驱动表）行数 N：
- **Nested Loop Join (NLJ)**：对外表每一行，拿连接键去内表逐行比对 → `O(M·N)`。
- **Block Nested Loop Join (BNL，MySQL 在无可用索引时的默认兜底)**：不逐行回表，而是把驱动表一批行（join buffer）一次性读入内存，再用这批键批量探测内表 → 把对内表的扫描次数从 M 降到 `⌈M/join_buffer_size⌉`，复杂度降到 `O(M·N / B)`。仍是 M×N 量级，只是大幅减少内表的**被扫描轮数**（I/O 次数），这是它相对朴素 NLJ 的核心改进。
- **Hash Join**：以等值连接（`a.x = b.y`）为前提。用较小表 build 一张内存哈希表（键=连接列，值=行或行指针），再扫描大表 probe，命中即拼行。平均 `O(M+N)`，对大表无索引的等值连接最优；缺点是**只能等值连接、不支持不等/范围连接、内存放不下时退化成分片落盘（MySQL 8.0.18+ 的 Hash Join 支持 on-disk 溢出）**。
- **Merge Join**：两表先按连接键排序（若连接列已有有序索引则可免排序），再用双指针归并，单次线性扫描 `O(M log M + N log N)`（含排序）。适合**连接列已有序**（如两表都按 PK 或同一索引列排序）的场景，且天然支持非等值/范围连接。

## 2. 实现机制：InnoDB/优化器怎么选

MySQL 优化器在 8.0 之前主要靠「索引嵌套循环」（Index Nested Loop Join，NLJ 的升级版：驱动表出一行，用连接键走内表索引，复杂度 `O(M·log N)`）。**8.0.18 起引入 Hash Join**，用于「两表都没有可用连接索引」的等值连接，替代了原来昂贵的 BNL。

关键认知（程序员视角）：
- **驱动表选择**：优化器通常把"估算行数少"的表当驱动表——因为被驱动表若能用上索引，则每轮只做 `log N` 次查找；驱动表越小，探测轮数越少。这就是"小表驱动大表"的由来（前提是内表连接列有索引）。
- **`EXPLAIN` 里的线索**：`join type` 为 `eq_ref`/`ref` 表示走了索引嵌套循环；`type: ALL` + `Extra: Using join buffer (Block Nested Loop)` 表示退化成 BNL；`Extra: Using join buffer (Hash Join)` 表示用了 Hash Join。

## 3. 工程实践与权衡

- 大表 JOIN **务必保证连接列有索引**（内表连接列加索引，把 NLJ 降为 `O(M·log N)`）。
- 连接列类型/字符集必须一致，否则触发隐式转换 → 索引失效 → 退化 BNL/全表。
- 只 `SELECT` 需要的列；BNL 的 join buffer 只存"用到的列"，少列能装更多行、减少轮数。

## 4. 边界与陷阱

- `LEFT JOIN` 时**驱动表被固定为左表**，优化器不能自由翻转驱动表顺序；若左表很大右表很小，可能被迫大表驱动 → 性能差。此时改写为 `RIGHT JOIN`（让小表在右）或 `INNER JOIN`（让优化器自由选）往往更优。
- 多表 JOIN（A⋈B⋈C）的驱动顺序由优化器基于每个中间结果的 `rows` 估算决定，统计信息过期会导致选错驱动表（`ANALYZE TABLE` 更新统计）。

## 5. 可运行代码

见 `examples/ex01-inner-join-dept.json`（INNER JOIN）、`examples/ex02-left-join-null.json`（NULL 语义）、`examples/ex03-block-nested-loop.json`（无索引退化的演示数据），以及 `examples/ex11-self-join.json`（员工-经理自连接）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- NLJ 的**驱动表选择**极其关键：小结果集做驱动、被驱动表的连接列**必须有索引**，否则退化为 O(N×M)。
- `EXPLAIN` 里出现 `Using join buffer (Block Nested Loop)` 通常意味着被驱动表缺索引或走了 BNL，是优化 JDBC 慢查询的第一信号。
- 强制连接顺序/算法是最后手段（`STRAIGHT_JOIN`），优先靠统计信息与索引让优化器自己选对。

### 🎓 博士生视角
- 三种算法的适用域由**是否有索引**与**内存预算**共同决定：
  - **Nested Loop**：有索引时近似 O(N log M)，无索引时最坏 O(N×M)；
  - **Hash Join**：等值连接、两侧都大且无索引，建表 O(N) + 探测 O(M)，需要能被 `join_buffer_size` 容纳；
  - **Merge Join**：两侧已按连接键有序时顺序扫描、无随机 IO（MySQL 无原生 Merge Join，PostgreSQL 有）。
- MySQL 8.0.18 之前**只有 BNL 没有真正的 Hash Join**，这是与 PostgreSQL 的重要实现差异，也是历史上 MySQL 大表连接慢的根因之一。
- 复杂度分析要点：连接算法的选择本质是在「随机 IO 次数」与「内存占用」之间做权衡。

### 📚 考研者视角
- 算法层面可考**嵌套循环、哈希、归并**三种连接的时间/空间复杂度对比（与 408 的排序、哈希表知识直接复用）。
- 若考数据库原理，常配套考「查询优化的启发式规则」（尽早选择、尽早投影、把小表放前面）。
- 记忆锚点：**NLJ 靠索引、Hash Join 靠内存、Merge Join 靠有序**。
