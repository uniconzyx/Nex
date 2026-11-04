# db-ch03 · 索引与事务：B+树索引、ACID、隔离级别 · 学习目标

- 理解 InnoDB **B+树索引的物理结构**：页（16KB）、聚簇索引 vs 二级索引、非叶子节点只存键+指针、叶子节点存整行（聚簇）或主键（二级）；能从"树高 3~4 层"估算千万/亿级表的查询只需 3~4 次 I/O
- 掌握**回表与覆盖索引**：二级索引如何靠主键"书签"回表取整行；什么情况下索引能"覆盖"查询从而避免回表
- 深刻理解**最左前缀原则**与联合索引的列顺序设计；理解索引下推（ICP）如何把过滤下推到存储引擎
- 理解事务 **ACID** 的落地机制：redo log（持久性/WAL）、undo log（原子性/MVCC 版本链）、double write buffer（页断裂保护）
- 掌握四种隔离级别与脏读/不可重复读/幻读的关系；理解 **MVCC** 版本链（DB_TRX_ID/DB_ROLL_PTR/undo）与 ReadView、当前读 vs 快照读
- 理解 **Next-Key Lock**（记录锁 + 间隙锁）如何在 RR 下解决幻读；了解死锁成因、检测与长事务的危害
- 能用 `EXPLAIN`/`SHOW INDEX` 判断一条查询是否走索引、是否覆盖、是否回表，并能据此设计索引
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §1.1 理论根基：为什么是 B+树，不是哈希/红黑树/B树 | 读 `docs/database/mysql/mysql-index.md`：B+ 树把数据全放叶子、非叶子只存键，因此一个 16KB 页能装更多键、树更矮——磁盘 IO 次数稳定在 3~4 次，这是它胜过二叉树与哈希的根本原因；对照 §1.2 的页结构，就能算出三层树能存多少行 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §2.1 回表（Bookmark Lookup）：二级索引的隐含成本 | 看 `document/sql/mall.sql` 里每张表的 `PRIMARY KEY (id)` 与业务唯一键：InnoDB 的二级索引叶子存主键，所以「按业务键查」要回表一次；这解释了 §2.2 覆盖索引为什么能把这次回表省掉——代价是索引里多存几列 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §3.3 MVCC：多版本并发控制（核心） | 对照 `docs/high-concurrency/mysql-lock.md`：快照读靠 undo 版本链 + ReadView，当前读（`SELECT ... FOR UPDATE`）才加锁——「可重复读下仍会幻读」的现场就出在这两者的边界上；配合 §3.4 当前读 vs 快照读，就能解释同一个事务里两次查询结果为何不一致 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | §1.2 InnoDB 的页与两类索引 | 主线课：SQL 语法 → 约束与多表 → 索引与事务 → 优化，每段都有可直接跑的脚本；看完回 `ex01`（建二级索引并用 EXPLAIN 验证走索）核对 |
| 2 | 尚硅谷 · MySQL 数据库高级<br><sub>尚硅谷</sub> | [BV1KW411u7vy](https://www.bilibili.com/video/BV1KW411u7vy/) | §1.2 InnoDB 的页与两类索引 | 专攻优化：B+ 树索引结构、执行计划、锁与隔离级别的实验演示；看完回 `ex02`（覆盖索引）核对 |
| 3 | 一个动画搞懂 MySQL 索引原理<br><sub>轩辕的编程宇宙</sub> | [BV1pJ4m1j7Pm](https://www.bilibili.com/video/BV1pJ4m1j7Pm/) | §1.2 InnoDB 的页与两类索引 | 6 分钟动画：聚簇索引与二级索引的回表过程，看完再读概念篇会顺很多；看完回 `ex03`（回表）核对 |
| 4 | 尚硅谷 · MySQL 基础+高级篇<br><sub>黎曼的猜想</sub> | [BV12b411K7Zu](https://www.bilibili.com/video/BV12b411K7Zu/) | §1.2 InnoDB 的页与两类索引 | 基础篇讲 SQL 与建表规范，高级篇讲索引、explain、慢查询与优化器；看完回 `ex04`（最左前缀失效）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《MySQL 技术内幕：InnoDB 存储引擎（第 2 版）》姜承尧 |
| 2 | 《高性能 MySQL（第 4 版）》 |
| 3 | 《数据库系统概念（第 7 版）》Silberschatz |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
