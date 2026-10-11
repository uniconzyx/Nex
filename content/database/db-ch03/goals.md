# db-ch03 · 索引与事务：B+树索引、ACID、隔离级别 · 学习目标

- 理解 InnoDB **B+树索引的物理结构**：页（16KB）、聚簇索引 vs 二级索引、非叶子节点只存键+指针、叶子节点存整行（聚簇）或主键（二级）；能从"树高 3~4 层"估算千万/亿级表的查询只需 3~4 次 I/O
- 掌握**回表与覆盖索引**：二级索引如何靠主键"书签"回表取整行；什么情况下索引能"覆盖"查询从而避免回表
- 深刻理解**最左前缀原则**与联合索引的列顺序设计；理解索引下推（ICP）如何把过滤下推到存储引擎
- 理解事务 **ACID** 的落地机制：redo log（持久性/WAL）、undo log（原子性/MVCC 版本链）、double write buffer（页断裂保护）
- 掌握四种隔离级别与脏读/不可重复读/幻读的关系；理解 **MVCC** 版本链（DB_TRX_ID/DB_ROLL_PTR/undo）与 ReadView、当前读 vs 快照读
- 理解 **Next-Key Lock**（记录锁 + 间隙锁）如何在 RR 下解决幻读；了解死锁成因、检测与长事务的危害
- 能用 `EXPLAIN`/`SHOW INDEX` 判断一条查询是否走索引、是否覆盖、是否回表，并能据此设计索引


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | 含 MySQL 索引、事务、锁与调优的系统讲解 |
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | 真实业务库表设计范例与 SQL 实践 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 含分库分表、读写分离与分布式事务 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · MySQL 基础+高级篇 | [视频](https://www.bilibili.com/video/BV12b411K7Zu/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 黑马程序员 · MySQL 实战教程 | [视频](https://www.bilibili.com/video/BV1vi4y137PN/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · MySQL 高级教程（索引/锁/调优） | [视频](https://www.bilibili.com/video/BV1KW411u7vy/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Redis 6 入门到精通 | [视频](https://www.bilibili.com/video/BV1Rv41177Af/) | 本学科配套视频，建议结合本章示例与习题观看 |
