# db-ch06 · 范式与数据库建模 · 学习目标

## 前置
- `db-ch01` 关系模型与 SQL 基础（表/行/列/主键/外键、DDL、JOIN、聚合）

## 本章定位
`db-ch01` 教你「怎么把数据存进去、查出来」；本章回答**更靠前的问题：表该怎么设计**。
一个设计失败的 Schema，后面无论加多少索引、怎么改写 SQL 都救不回来 ——
范式理论就是把「该不该拆表」从拍脑袋变成**可判定的算法**。

本章的三条主线：
1. **理论线**：函数依赖 → 属性闭包 → 候选键 → 范式判定 → 模式分解；
2. **工程线**：ER 建模 → 三种联系的落表方式 → 主外键设计 → 反范式权衡；
3. **验证线**：以上全部用 Python 实跑（闭包/候选键/范式判定/表格法/最小覆盖），
   并用内置 `sqlite3` 真建表、真 JOIN，验证「拆表后信息不丢」。

> 本章示例全部为可实跑的 **Python 3 + sqlite3**（标准库，无需第三方依赖），
> 每个 `expected_output` 都来自真实执行，回放脚本可复现。

## 学习资源（GitHub star 最高）
- **Snailclimb/JavaGuide**（★159056）—— 含 MySQL 索引、事务、锁与调优的系统讲解
  <https://github.com/Snailclimb/JavaGuide>
- **macrozheng/mall**（★84863）—— 真实业务库表设计范例与 SQL 实践
  <https://github.com/macrozheng/mall>
- **doocs/advanced-java**（★79141）—— 含分库分表、读写分离与分布式事务
  <https://github.com/doocs/advanced-java>

## 推荐书目
- 《数据库系统概论》第 5-6 章（函数依赖、范式、模式分解）——**本章主教材**，符号体系最标准
- 《数据库系统概念》第 7-8 章（数据库设计 / 规范化 / 范式分解算法）
- 《高性能 MySQL》附录（Schema 设计）—— 工程侧的反范式取舍

## 验收标准
1. 能写出函数依赖的形式化定义，并区分**完全依赖 / 部分依赖 / 传递依赖**。
2. 能默写 Armstrong 三条公理（自反、增广、传递）及三条推论（合并、分解、伪传递）。
3. 能手算任意属性集的**属性闭包 X+**，并据此判断 X 是否超键。
4. 能枚举出关系模式的**全部候选键**，并正确标出主属性集合。
5. 能对给定 R 与 F 判定 **1NF / 2NF / 3NF / BCNF**，并能举出「满足 3NF 但不满足 BCNF」的实例。
6. 能用**表格法（Chase）**判定分解的无损连接性，并会用二元分解的快速判据。
7. 能判定一个分解是否**保持依赖**，并说明它为何与无损连接相互独立。
8. 能计算函数依赖集的**最小覆盖**（右部单一、去冗余 FD、去左部冗余属性）。
9. 能把一个非 3NF 模式用**合成法**拆成 3NF，并验证无损连接与保持依赖。
10. 能把 ER 图（实体、属性、1:1 / 1:N / M:N 联系）正确映射成关系模式，含中间表与约束。
11. 能说清**超键 / 候选键 / 主键 / 外键**四者的集合关系与工程实现方式。
12. 能用**操作计数判据**评估反范式收益，说出「何时故意冗余」的边界条件。


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
- 本章仅依赖本学科 `db-ch01`。若已具备任意一种编程语言的集合/字典操作基础
  （Python 的 `set` 即可），可直接阅读 `examples/` 中的算法实现。
