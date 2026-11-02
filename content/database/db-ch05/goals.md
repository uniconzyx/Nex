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
## 推荐书目

- 《MySQL 必知必会》第 23~25 章（存储过程 / 游标 / 触发器）——**本章主教材**，语法口径以它为准
- 《数据库系统概念》第 4 章（中级 SQL）与第 5 章（高级 SQL：触发器、递归查询）——SQL/PSM 的形式化基础
- 《高性能 MySQL》第 6 章（查询性能优化）——用它的代价模型解释「游标逐行为什么慢」

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §1.1 | 讲「存储过程与函数的差异」时读 `docs/database/mysql/` 的过程化编程章节：函数必须 RETURN 一个值、过程靠 OUT 参数，二者的调用位置（表达式 vs CALL）决定了它们不能互换 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §4.1 | 讲「存储过程与应用的边界」时看 `mall` 的 Service 层：业务规则全在 Java 里、SQL 只出现在 mapper XML 中，这是「存储过程不适合互联网团队」的直接证据——版本管理、单测、灰度发布都做不了 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §1.3 | 讲「触发器与审计」时对照 `docs/high-concurrency/` 的数据库设计文章：触发器把逻辑藏进数据库，排查时「看不见调用方」，审计场景更推荐 binlog 订阅（Canal）而非触发器 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | §4.2 动态 SQL 拼接与注入；… | 主线课：SQL 语法 → 约束与多表 → 索引与事务 → 优化，每段都有可直接跑的脚本；看完回 `ex01`（用 Python 值语义模拟存储过程参数）核对 |
| 2 | 尚硅谷 · MySQL 基础+高级篇<br><sub>黎曼的猜想</sub> | [BV12b411K7Zu](https://www.bilibili.com/video/BV12b411K7Zu/) | §4.2 动态 SQL 拼接与注入；… | 基础篇讲 SQL 与建表规范，高级篇讲索引、explain、慢查询与优化器；看完回 `ex02`（DELIMITER 的必要性）核对 |
| 3 | 尚硅谷 · MySQL 数据库高级<br><sub>尚硅谷</sub> | [BV1KW411u7vy](https://www.bilibili.com/video/BV1KW411u7vy/) | §4.2 动态 SQL 拼接与注入；… | 专攻优化：B+ 树索引结构、执行计划、锁与隔离级别的实验演示；看完回 `ex03`（游标逐行处理 vs 集合操作）核对 |
| 4 | 一个动画搞懂 MySQL 索引原理<br><sub>轩辕的编程宇宙</sub> | [BV1pJ4m1j7Pm](https://www.bilibili.com/video/BV1pJ4m1j7Pm/) | 全章 | 6 分钟动画：聚簇索引与二级索引的回表过程，看完再读概念篇会顺很多；看完回 `ex04`（触发器 BEFORE/AFTER 时序与）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《MySQL 技术内幕：InnoDB 存储引擎（第 2 版）》姜承尧 |
| 2 | 《高性能 MySQL（第 4 版）》 |
| 3 | 《数据库系统概念（第 7 版）》Silberschatz |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。

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