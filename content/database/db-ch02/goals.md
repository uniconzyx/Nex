# db-ch02 · 表连接与子查询：JOIN、子查询、集合操作 · 学习目标

- 理解 JOIN 的**执行算法本质**：Nested Loop Join / Block Nested Loop Join / Hash Join / Merge Join 各自的时间复杂度、内存特征与适用场景，能解释"InnoDB 为什么常选小表做驱动表"
- 掌握 INNER / LEFT / RIGHT / CROSS / SELF JOIN 的语义差异，尤其是 LEFT JOIN 右表无匹配时补 `NULL` 的坑，以及过滤条件放在 `ON` 还是 `WHERE` 的结果差异
- 理解子查询的分类（标量子查询、列/行/表子查询、相关 vs 非相关、派生表），以及 MySQL 对子查询的优化（物化、semi-join、anti-join、`IN` vs `EXISTS` 的优化器转换）
- 能用 `UNION` / `UNION ALL` / `INTERSECT` / `EXCEPT` 表达集合运算，理解去重与排序（`filesort`）的代价，并能把"集合操作"等价改写为 `JOIN`
- 从数据库理论视角理解**范式（1NF/2NF/3NF/BCNF）与函数依赖**，并在工程上权衡"反范式（冗余/汇总表）"以牺牲写入代价换取 JOIN 性能
- 具备把"多步业务查询"拆成 JOIN + 子查询 + 集合操作组合，并用 `EXPLAIN` 判断其执行方式（驱动表、是否用临时表/文件排序）的能力


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
