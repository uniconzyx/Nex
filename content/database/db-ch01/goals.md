# db-ch01 · 关系模型与 SQL 基础（DDL/DML/SELECT/JOIN/聚合/分组）· 学习目标

- 理解关系模型核心概念：表（关系）、行（元组）、列（属性）、主键、外键与关系完整性
- 掌握 DDL：用 `CREATE TABLE` / `ALTER TABLE` / `DROP TABLE` 创建、修改、删除表与列
- 掌握 DML：用 `INSERT` / `UPDATE` / `DELETE` 完成数据的增、改、删
- 掌握 `SELECT` 基础：投影列、`WHERE` 过滤、`ORDER BY` 排序、`LIMIT` 限制行数
- 理解并正确使用 `INNER JOIN` / `LEFT JOIN` / `RIGHT JOIN` 完成多表关联查询
- 掌握聚合函数（`COUNT`/`SUM`/`AVG`/`MAX`/`MIN`）与 `GROUP BY` 分组、`HAVING` 分组后过滤
- 理解 `DISTINCT` 去重与子查询（标量子查询、IN 子查询）的基本用法
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | 全章 | 含 MySQL 索引、事务、锁与调优的系统讲解；本章先读与「核心要素」「DDL」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | 全章 | 真实业务库表设计范例与 SQL 实践；本章先读与「核心要素」「DDL」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | 全章 | 含分库分表、读写分离与分布式事务；本章先读与「核心要素」「DDL」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | 全章 | 主线课：SQL 语法 → 约束与多表 → 索引与事务 → 优化，每段都有可直接跑的脚本；看完回 `ex01`（DDL 建表与 DML 插入部门表）核对 |
| 2 | 尚硅谷 · MySQL 基础+高级篇<br><sub>黎曼的猜想</sub> | [BV12b411K7Zu](https://www.bilibili.com/video/BV12b411K7Zu/) | 全章 | 基础篇讲 SQL 与建表规范，高级篇讲索引、explain、慢查询与优化器；看完回 `ex02`（SELECT 投影与排序查询部门）核对 |
| 3 | 尚硅谷 · MySQL 数据库高级<br><sub>尚硅谷</sub> | [BV1KW411u7vy](https://www.bilibili.com/video/BV1KW411u7vy/) | 全章 | 专攻优化：B+ 树索引结构、执行计划、锁与隔离级别的实验演示；看完回 `ex03`（WHERE 过滤与 ORDER BY 排）核对 |
| 4 | 一个动画搞懂 MySQL 索引原理<br><sub>轩辕的编程宇宙</sub> | [BV1pJ4m1j7Pm](https://www.bilibili.com/video/BV1pJ4m1j7Pm/) | 全章 | 6 分钟动画：聚簇索引与二级索引的回表过程，看完再读概念篇会顺很多；看完回 `ex04`（ORDER BY DESC 配合 LIM）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《MySQL 技术内幕：InnoDB 存储引擎（第 2 版）》姜承尧 |
| 2 | 《高性能 MySQL（第 4 版）》 |
| 3 | 《数据库系统概念（第 7 版）》Silberschatz |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
