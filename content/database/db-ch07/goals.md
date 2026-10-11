# db-ch07 · 备份恢复与权限安全 · 学习目标

## 前置
- `db-ch01` 关系模型与 SQL 基础（表/行/列/主键/外键、DDL、DML、SELECT）

## 本章定位
前六章解决「数据怎么存、怎么查、怎么设计」；本章回答另外两个**运维与安全**问题：

1. **数据丢了/错了怎么办** —— 备份有哪几条路线、恢复怎么验收、误删之后怎么把库拉回到「错误发生前一秒」（PITR）；
2. **数据被谁拿到、被谁改掉怎么办** —— 账号与权限模型、SQL 注入的成因与防线、敏感数据脱敏加密、审计与安全清单。

一条贯穿全章的判据：**「备份成功」不等于「能恢复」**。备份只是把数据搬了一份，
恢复才是把数据变回可用状态；只有被**验证过**的备份才算备份。

## 三条主线
1. **备份线**：逻辑备份（mysqldump）vs 物理备份（冷备/热备、XtraBackup）→
   全量 + 增量 + 校验 → 备份链与恢复演练；
2. **恢复线**：binlog 三种格式 → 位点/时间戳 → 时间点恢复（PITR）→ 目标点裁剪与核对；
3. **安全线**：用户@主机与 GRANT/REVOKE → 最小权限与角色 → SQL 注入（预编译/白名单/权限兜底）
   → 脱敏、列级加密、TDE、审计日志 → 安全清单。

## 学习资源（GitHub star 最高）
- **Snailclimb/JavaGuide**（★159056）—— 含 MySQL 索引、事务、锁与调优的系统讲解
  <https://github.com/Snailclimb/JavaGuide>
- **macrozheng/mall**（★84863）—— 真实业务库表设计范例与 SQL 实践
  <https://github.com/macrozheng/mall>
- **doocs/advanced-java**（★79141）—— 含分库分表、读写分离与分布式事务
  <https://github.com/doocs/advanced-java>

## 推荐书目
- 《高性能 MySQL》第 10 章（备份与恢复）—— **本章主教材**，备份类型与工具的工程取舍
- 《数据库系统概念》第 16 章（授权）—— 权限模型与视图授权的标准定义
- 《MySQL 必知必会》第 21-25 章 —— 账号管理与 DDL/DML 语法基础

## 本章示例的实测口径
> 本机无 MySQL 实例与凭证。因此本章示例分两类：
> ① **可实跑示例**（`examples/ex01` ~ `ex12`）：全部是 Python 3 + 内置 `sqlite3` / `hashlib` / `hmac`，
>    真建库、真备份、真恢复、真执行注入对比，`expected_output` 全部来自真实运行；
> ② **命令形态示例**（`examples/ex13`、`ex14`）：mysqldump 与 binlog 的 MySQL 语句，
>    标 `"_verified": false`，只写语法结构与流程要点，**不编造执行结果**。
>
> 备份恢复类的判据一律用**确定性量**：表名集合、行数、内容校验和（sha256），
> 不使用耗时或文件大小（与引擎实现相关，不可复现）。

## 验收标准
1. 能说清**逻辑备份**与**物理备份**的原理差异，并给出「选哪一个」的决策条件。
2. 能区分冷备 / 温备 / 热备，并说明 `--single-transaction` 为何只对 InnoDB 有效。
3. 能写出 `mysqldump` 的**全量 / 单表 / 仅结构 / 仅数据**四种命令形态。
4. 能解释 **RPO 与 RTO** 的定义，并由 RPO/RTO 反推全量、增量的备份频率。
5. 能说明备份**校验和与恢复演练**为什么是备份闭环的必需环节，并写出验收判据。
6. 能对比 binlog 的 **STATEMENT / ROW / MIXED** 三种格式，指出各自的确定性与体积代价。
7. 能默写 **PITR 流程**：恢复全量 → 取位点/时间戳 → 截取日志重放到目标点 → 核对 → 放流量。
8. 能说清「增量备份」与「binlog 即增量」两种实现路线的关系与差异。
9. 能解释 **用户@主机** 的匹配规则，以及库级/表级/列级授权的粒度差异。
10. 能写出 `GRANT` / `REVOKE` 的语句，并说明为何「回收权限」要覆盖所有粒度（幽灵权限）。
11. 能说清 **SQL 注入**的成因，并写出预编译、白名单、最小权限三道防线的分工。
12. 能实现并解释**脱敏**（掩码/假名化）、**加盐哈希**与**审计日志触发器**，指出各自的适用边界。


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

## 软前置（可选，不阻断学习）
- 本章仅依赖本学科 `db-ch01`。若已具备任意一种语言的字符串/哈希库使用经验
  （Python 标准库 `sqlite3` + `hashlib` 即可），可直接阅读 `examples/` 中的实现。
