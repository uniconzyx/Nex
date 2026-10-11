# db-ch04 · 查询优化与执行计划（EXPLAIN）· 学习目标

## 前置
- `db-ch02` SQL 基础（多表连接、子查询、聚合）
- `db-ch03` 索引与事务（B+ 树、最左前缀、覆盖索引、回表）——**本章是它的动手版**

## 本章定位
`db-ch03` 讲了「索引是什么」，本章解决「**索引到底有没有被用上、代价多少、怎么改**」。
一个后端工程师 80% 的数据库性能问题都能归结为一句话：
**「这条 SQL 的执行计划和你以为的不一样」**。学完本章，你应该能对着 `EXPLAIN` 的输出
逐列说出「它在干什么、为什么慢、下一步改什么」。

> ⚠️ 本机没有可用的 MySQL 服务（有客户端但无凭证）。
> 因此本章示例以 **Python 从零建模**为主：自己实现 B+ 树高度与 I/O 计数、最左前缀断裂判定、
> 选择性估算、回表代价模型、深分页代价曲线、filesort 判定。
> 少量纯 SQL 示例标 `_verified: false`，**只作语法与写法参考**，不可当作已实测结果。

## 学习资源（GitHub star 最高）
- **Snailclimb/JavaGuide**（★159056）—— 含 MySQL 索引、事务、锁与调优的系统讲解
  <https://github.com/Snailclimb/JavaGuide>
- **macrozheng/mall**（★84863）—— 真实业务库表设计范例与 SQL 实践
  <https://github.com/macrozheng/mall>
- **doocs/advanced-java**（★79141）—— 含分库分表、读写分离与分布式事务
  <https://github.com/doocs/advanced-java>

## 推荐书目
- 《高性能 MySQL》第 6 章（查询性能优化）——**本章主教材**，EXPLAIN 逐列讲解最权威
- 《数据库系统概念》第 13 章（查询处理）——代价模型与连接算法的形式化基础
- 《MySQL 是怎样运行的》——InnoDB 存储引擎与优化器内部机制

## 验收标准
1. 能逐列解释 `EXPLAIN` 的输出，并说出 `type` 的优劣阶梯与每一档的含义。
2. 能识别 `Extra` 中的关键信号：`Using index` / `Using index condition` / `Using filesort` / `Using temporary`。
3. 能列出至少 7 种索引失效场景，并指出每种对应的改写方式。
4. 能针对联合索引 `(a,b,c)` 判断任意 `WHERE` 组合实际能用到的前缀长度。
5. 能计算二级索引回表 vs 覆盖索引的代价差（I/O 次数口径），并据此判断是否值得加覆盖索引。
6. 能写出深分页的两种优化写法（延迟关联、游标法），并说明各自的适用前提。
7. 能判断 `ORDER BY` / `GROUP BY` 是否会产生 `filesort` 与 `temporary`。
8. 能说清「小表驱动大表」的原理，以及被驱动表关联列为什么必须建索引。


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
