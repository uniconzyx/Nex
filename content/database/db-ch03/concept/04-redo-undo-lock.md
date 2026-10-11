# 04 · redo/undo log 与锁（Next-Key Lock、死锁、长事务）

> 博士看"事务的持久化与并发控制原语"，程序员看"为什么提交后断电不丢、为什么偶尔死锁"。

## 1. redo log：崩溃恢复与 WAL

- InnoDB 改数据先改**内存 Buffer Pool**，并不每次都刷盘。若直接随机写数据页，I/O 极慢且断电即丢。于是引入 **redo log（物理逻辑日志，记录"页号+偏移+新值"）**：事务提交时**顺序写** redo log（顺序 I/O 远快于随机写），再异步把脏页刷回数据文件。
- 这叫 **WAL（Write-Ahead Logging，先写日志）**：只要 redo 落盘，即使脏页没刷、宕机，重启时也能**重放 redo** 恢复已提交事务 → 保证**持久性**。
- **两阶段提交（2PC）**：事务提交要同时保证 redo log 与 binlog 一致：① redo 写 `prepare`；② 写 binlog；③ redo 写 `commit`。崩溃恢复时，若 redo 处于 prepare 且 binlog 完整 → 提交；否则回滚。这是 MySQL 主从一致的基础。
- 持久化强度由 `innodb_flush_log_at_trx_commit` 控制：`1`（默认，每次提交刷盘，最安全）、`2`（刷到 OS 缓存）、`0`（每秒刷）。`0/2` 丢数据风险高。

## 2. double write buffer：防"页断裂"

InnoDB 页 16KB，但磁盘扇区常 512B/4KB，**一次写页可能只写入一半就断电** → 页损坏、redo 也无力（redo 基于"整页"重放）。double write buffer 先顺序写一份页副本，再写真正位置；崩溃时若真页损坏，用副本恢复。

## 3. undo log：回滚 + MVCC 的版本源

- 每次修改前，旧值写入 **undo log**（存在回滚段）。`ROLLBACK` 时按 undo 反向执行恢复；事务未提交时别人也看不见（MVCC 判不可见）。
- undo log 也是 concept 03 中 MVCC **版本链**的物理存储：旧版本行挂在 undo 上，快照读沿 `DB_ROLL_PTR` 回溯。
- **purge 线程**：当没有任何事务的 ReadView 还需要某旧版本时，才清理它。长事务持有旧 ReadView → 这些 undo 版本不能被 purge → **回滚段无限膨胀**。

## 4. 锁：行锁、间隙锁、Next-Key Lock（解决幻读）

InnoDB 锁加在**索引记录**上（没索引会锁全表！）。
- **记录锁（Record Lock）**：锁住某一行。
- **间隙锁（Gap Lock）**：锁住两条记录之间的"间隙"，防止别的事务**插入**到该范围 → 防幻读的关键。
- **Next-Key Lock = 记录锁 + 间隙锁**：RR 下 `SELECT ... FOR UPDATE WHERE id BETWEEN 10 AND 20` 不仅锁住命中的行，还锁住 (10,20) 这段间隙，别的事务插入 id=15 会被阻塞。这就是 RR 下"当前读无幻读"的实现。
- **意向锁（Intention Lock）**：表级，标识"某事务将要/正在锁表中的某些行"，让表锁与行锁能快速冲突检测。

## 5. 死锁与长事务

- **死锁**：两个事务互相持有对方想要的锁（T1 锁 A 等 B，T2 锁 B 等 A）。InnoDB 默认开启 **死锁检测**（`innodb_deadlock_detect=ON`），选择**回滚代价小**的事务（undo 量少）并抛 `1213` 错误；应用应捕获后重试。
- **长事务危害**：① 持有锁久 → 阻塞别人、易死锁；② ReadView 不释放 → undo 无法 purge → 膨胀、全库变慢；③ 大事务写 binlog/redo 集中 → 复制延迟。

## 6. 工程实践

- 事务**越短越好**：把无关 SELECT/网络调用移出事务；批量写**分批提交**（每 1000~5000 行一提交）。
- 更新/删除务必走**索引**，否则行锁升级为全表锁，瞬间拖累并发。
- 高并发扣库存：先 `SELECT ... FOR UPDATE` 锁行（当前读），校验余额后再 `UPDATE`，提交即释放。

## 7. 可运行代码

见 `examples/ex07-transaction-rollback.json`（undo 回滚）、`examples/ex11-redo-undo-vars.json`（redo/undo 相关系统变量）、`examples/ex09-current-read-for-update.json`（当前读加 Next-Key Lock 前奏）。死锁/间隙锁属并发行为，需两会话复现，建议结合 `SHOW ENGINE INNODB STATUS` 与 `performance_schema.data_locks` 观察。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 定位死锁：开启 `innodb_print_all_deadlocks` 把死锁日志打到 error log；降低死锁概率的手段是**统一加锁顺序**、缩短事务、批量按主键排序后操作。
- redo 决定「崩溃后能恢复到最后一次提交」，undo 决定「回滚」与「MVCC 旧版本」——理解它们能解释为什么 binlog 与 redo 需要两阶段提交来保证一致。
- 长事务会让 undo 版本链膨胀（俗称「undo 膨胀」），监控 `history_list_length` 是最实用的手段。

### 🎓 博士生视角
- **WAL（Write-Ahead Logging）** 是持久性的核心：先顺序写日志（快），再异步刷数据页（随机写），把随机 IO 摊平成顺序 IO；崩溃恢复靠 redo 前滚 + undo 回滚。
- **Next-Key Lock = 记录锁 + 间隙锁**，它锁住记录及其前面的间隙，因此能阻止别的事务在区间内插入——这才是 RR 下防住幻读的机制（而快照读本来就不产生幻读）。
- 死锁检测基于**等待图（wait-for graph）**的环检测，复杂度与事务数相关；也可用超时（`innodb_lock_wait_timeout`）作为兜底策略。

### 📚 考研者视角
- **数据库原理常考**：WAL 与检查点（checkpoint）恢复策略、**死锁的四个必要条件与预防/检测/解除**、两阶段提交协议（2PC）。
- 与 408 操作系统交叉：死锁的四个必要条件（互斥、占有并等待、不可剥夺、循环等待）是**同一套理论**，且 408 必考。
- 记忆锚点：**redo 前滚（保持久性）、undo 回滚（保原子性）**；**间隙锁的作用是防幻读**。
