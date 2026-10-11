# db-ch01 · 关系模型与 SQL 基础（DDL/DML/SELECT/JOIN/聚合/分组）· 学习目标

- 理解关系模型核心概念：表（关系）、行（元组）、列（属性）、主键、外键与关系完整性
- 掌握 DDL：用 `CREATE TABLE` / `ALTER TABLE` / `DROP TABLE` 创建、修改、删除表与列
- 掌握 DML：用 `INSERT` / `UPDATE` / `DELETE` 完成数据的增、改、删
- 掌握 `SELECT` 基础：投影列、`WHERE` 过滤、`ORDER BY` 排序、`LIMIT` 限制行数
- 理解并正确使用 `INNER JOIN` / `LEFT JOIN` / `RIGHT JOIN` 完成多表关联查询
- 掌握聚合函数（`COUNT`/`SUM`/`AVG`/`MAX`/`MIN`）与 `GROUP BY` 分组、`HAVING` 分组后过滤
- 理解 `DISTINCT` 去重与子查询（标量子查询、IN 子查询）的基本用法


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
