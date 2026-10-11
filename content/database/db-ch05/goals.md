# db-ch05 · 存储过程 / 触发器 / 自定义函数 · 学习目标

## 前置
- `db-ch01` SQL 基础（DDL/DML、`SELECT`、约束、NULL 语义）
- 建议先学过 `db-ch02` 多表连接与 `db-ch03` 索引与事务（本章多处引用「集合操作 vs 逐行处理」的代价对比）

## 本章定位
`db-ch01`~`db-ch04` 讲的都是「**把 SQL 发给数据库**」。
本章讲的是「**把过程化逻辑放进数据库**」——存储过程、自定义函数、触发器、游标与流程控制。
它们把「一次一集合（set-at-a-time）」的关系模型，扩展成了「一次一记录（record-at-a-time）」的过程化编程模型，
也正因为这个转向，带来了**可维护性、可移植性、可观测性、水平扩展**四个方向的系统性代价。

> ⚠️ 本机没有可用的 MySQL 服务（有客户端但无凭证）。
> 因此本章的 SQL 示例一律标 `_verified: false`，**只作语法与写法参考**，`expected_output` 只描述
> 语法结构要点与结果集表头形态，**不编造行数据**；
> 所有「真实实测」的证据来自用 **Python 的 sqlite3** 实跑的等价示例（sqlite 原生支持
> `CREATE TRIGGER` / `BEFORE` / `AFTER` / `NEW` / `OLD` / 事务，足以复现触发器的语义与陷阱）。

## 学习资源（GitHub star 最高）
- **Snailclimb/JavaGuide**（★159056）—— 含 MySQL 存储过程、触发器、权限与调优的系统讲解
  <https://github.com/Snailclimb/JavaGuide>
- **macrozheng/mall**（★84863）—— 真实业务库表设计范例与 SQL 实践（观察其**几乎不用存储过程**的工程取向）
  <https://github.com/macrozheng/mall>
- **doocs/advanced-java**（★79141）—— 含分库分表、读写分离与分布式事务，解释「为什么过程在分片下失灵」
  <https://github.com/doocs/advanced-java>

## 推荐书目
- 《MySQL 必知必会》第 23~25 章（存储过程 / 游标 / 触发器）——**本章主教材**，语法口径以它为准
- 《数据库系统概念》第 4 章（中级 SQL）与第 5 章（高级 SQL：触发器、递归查询）——SQL/PSM 的形式化基础
- 《高性能 MySQL》第 6 章（查询性能优化）——用它的代价模型解释「游标逐行为什么慢」

## 验收标准
1. 能写出存储过程与自定义函数的完整定义（含 `DELIMITER`），并说出二者在**调用方式、返回值、能否含事务、能否出现在 `WHERE`**四条上的差异。
2. 能准确说明 `IN` / `OUT` / `INOUT` 三种参数模式在过程体内的可见性与回传语义，并给出各自的典型用途。
3. 能解释 `DELIMITER` **是客户端指令而非服务器语法**，并说清不加它会出什么错。
4. 能画出行级触发器在 `BEFORE / AFTER × INSERT / UPDATE / DELETE` 六个组合下 `NEW` / `OLD` 的**可用性矩阵**。
5. 能用触发器写出一份可用的审计日志，并说出触发器做业务逻辑的至少四条工程风险。
6. 能写出带 `DECLARE CURSOR` + `CONTINUE HANDLER FOR NOT FOUND` + `LOOP` 的完整游标遍历，并说明 `DECLARE` 的**强制顺序**。
7. 能写出 `IF` / `CASE` / `WHILE` / `LOOP` / `REPEAT` 五种流程控制，并说出 `WHILE` 与 `REPEAT` 的判定时机差异。
8. 能给出「存储过程 vs 函数 vs 应用层」的职责边界决策表，并复述「为什么互联网公司普遍不用存储过程」的完整论证链。
9. 能说明存储过程内 `COMMIT` / `ROLLBACK` 与外层事务的冲突，以及 MySQL 中 DDL 隐式提交带来的原子性破坏。


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
