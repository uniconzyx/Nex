# db-ch02 · 表连接与子查询：JOIN、子查询、集合操作 · 学习目标

- 理解 JOIN 的**执行算法本质**：Nested Loop Join / Block Nested Loop Join / Hash Join / Merge Join 各自的时间复杂度、内存特征与适用场景，能解释"InnoDB 为什么常选小表做驱动表"
- 掌握 INNER / LEFT / RIGHT / CROSS / SELF JOIN 的语义差异，尤其是 LEFT JOIN 右表无匹配时补 `NULL` 的坑，以及过滤条件放在 `ON` 还是 `WHERE` 的结果差异
- 理解子查询的分类（标量子查询、列/行/表子查询、相关 vs 非相关、派生表），以及 MySQL 对子查询的优化（物化、semi-join、anti-join、`IN` vs `EXISTS` 的优化器转换）
- 能用 `UNION` / `UNION ALL` / `INTERSECT` / `EXCEPT` 表达集合运算，理解去重与排序（`filesort`）的代价，并能把"集合操作"等价改写为 `JOIN`
- 从数据库理论视角理解**范式（1NF/2NF/3NF/BCNF）与函数依赖**，并在工程上权衡"反范式（冗余/汇总表）"以牺牲写入代价换取 JOIN 性能
- 具备把"多步业务查询"拆成 JOIN + 子查询 + 集合操作组合，并用 `EXPLAIN` 判断其执行方式（驱动表、是否用临时表/文件排序）的能力
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §4.1 | 讲「子查询的三种形态」时读 `docs/database/mysql/` 的 SQL 优化篇：标量子查询、`IN`、`EXISTS` 在执行计划里的差异是「是否被改写成半连接」，这决定了相关子查询会不会被逐行执行 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §3.1 | 讲「JOIN 与聚合」时看 `mall-mbg` 生成的 Example/Criteria 类：它把「动态 WHERE + ORDER BY」拼成 SQL，能直观看到「条件组合爆炸」是怎么发生的，也能理解为什么复杂查询要手写 XML |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §2.2 | 讲「IN vs EXISTS」时对照 `docs/high-concurrency/` 的 MySQL 优化文章：小表驱动大表、`EXISTS` 在外层小的时候更快，这条结论来自「谁做驱动表」而非语法本身 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | §2.2 MySQL 如何"拆掉"子… | 主线课：SQL 语法 → 约束与多表 → 索引与事务 → 优化，每段都有可直接跑的脚本；看完回 `ex01`（INNER JOIN 关联员工与部门（仅）核对 |
| 2 | 尚硅谷 · MySQL 基础+高级篇<br><sub>黎曼的猜想</sub> | [BV12b411K7Zu](https://www.bilibili.com/video/BV12b411K7Zu/) | §2.2 MySQL 如何"拆掉"子… | 基础篇讲 SQL 与建表规范，高级篇讲索引、explain、慢查询与优化器；看完回 `ex02`（LEFT JOIN 保留左表全部行）核对 |
| 3 | 尚硅谷 · MySQL 数据库高级<br><sub>尚硅谷</sub> | [BV1KW411u7vy](https://www.bilibili.com/video/BV1KW411u7vy/) | §1.2 InnoDB/优化器怎么选 | 专攻优化：B+ 树索引结构、执行计划、锁与隔离级别的实验演示；看完回 `ex03`（RIGHT JOIN 保留右表全部行（含）核对 |
| 4 | 一个动画搞懂 MySQL 索引原理<br><sub>轩辕的编程宇宙</sub> | [BV1pJ4m1j7Pm](https://www.bilibili.com/video/BV1pJ4m1j7Pm/) | 全章 | 6 分钟动画：聚簇索引与二级索引的回表过程，看完再读概念篇会顺很多；看完回 `ex04`（CROSS JOIN 笛卡尔积（无连接条）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《MySQL 技术内幕：InnoDB 存储引擎（第 2 版）》姜承尧 |
| 2 | 《高性能 MySQL（第 4 版）》 |
| 3 | 《数据库系统概念（第 7 版）》Silberschatz |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
