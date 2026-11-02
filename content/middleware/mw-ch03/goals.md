# 学习目标 · Redis 高可用：主从、哨兵与 Cluster（mw-ch03）

> 学科：`middleware` · 分组：M1 Redis 原理
> 配套资源：《Redis 设计与实现》第 3 章。本章聚焦「高可用三件套」——主从复制、哨兵、Cluster，并用 Python 从零模拟核心机制、打印真实结果。

完成本章后，读者应能：

1. **讲清主从复制的全量同步与部分同步**：理解 `PSYNC` 的状态机（FULLRESYNC vs CONTINUE）、主节点 `fork + RDB` 全量传输、从节点清空载入再补增量；理解 `repl_backlog` 环形缓冲如何支撑部分同步、`offset` 作为复制逻辑时钟、`REPLCONF ACK` 心跳如何上报进度与计算 `lag`。
2. **掌握哨兵的故障发现与转移**：区分 SDOWN（单哨兵主观下线）与 ODOWN（quorum 投票后的客观下线）；理解类 Raft 的 leader 选举（epoch + 多数派 >N/2）；背记故障转移选主规则 `replica-priority 最小 → offset 最大 → runid 字典序最小`。
3. **理解 Redis Cluster 的分片与路由**：16384 槽位、`CRC16(key) & 16383` 键槽计算；MOVED（归属已变、刷新映射）与 ASK（迁移中、临时不刷新）的区别；hash tag 解决跨槽多 key 限制。
4. **理解槽迁移与集群总线**：`CLUSTER SETSLOT` + `MIGRATE` 在线重分片、迁移期 ASK 引导；集群总线 gossip（PING/PONG）做拓扑传播与故障共识；Cluster 内置主从 failover 无需 Sentinel。
5. **认识脑裂与 CAP 取舍**：理解网络分区导致的双主数据分叉；用 `min-replicas-to-write` + `min-replicas-max-lag` 在分区时牺牲可用性换一致性（CP 倾向）。
6. **从零模拟并实测**：用 Python 实现主从 PSYNC/backlog、哨兵 SDOWN/ODOWN/选主、Cluster 槽位/CRC16/MOVED/ASK/迁移/gossip、脑裂 min-replicas 防护，并能打印真实运行结果（见 examples/）。
7. **掌握笔试/面试高频口径**：全量 vs 部分同步、quorum 与多数派的区别、选主规则、MOVED vs ASK、gossip、脑裂防护与 CAP，能给出标准答法与易错点。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §2.1 | 讲「哨兵的主观/客观下线」时读 `docs/database/redis/` 的高可用篇：单个哨兵判 SDOWN 只是「我觉得」，凑够 quorum 才升 ODOWN，`majority` 与 `quorum` 是两个不同的数——配错就会「以为三个哨兵就安全」 |
| 2 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §3.2 | 讲「脑裂与 min-replicas-to-write」时对照 `docs/high-concurrency/` 的 Redis 集群文章：老主库网络分区后仍接受写入，恢复时这部分数据被覆盖，`min-replicas-to-write` 用「写成功必须至少 N 个从库确认」把风险压到配置层面 |
| 3 | [redis/redis](https://github.com/redis/redis) | 77,127 | §1.1 | 讲「全量同步 PSYNC」时读 `src/replication.c`：`repl_backlog` 环形缓冲区 + `master_repl_offset` 让「断线重连只补差额」成为可能，缓冲区太小就只能退回全量同步——这是「主从频繁全量」的第一排查点 |
| 4 | [apache/kafka](https://github.com/apache/kafka) | 34,105 | §2.2 | 讲「选主与多数派」时对照 `core/src/main/scala/kafka/controller/` 的选举逻辑：Kafka 用 Controller + ZK/KRaft 选 leader，Redis Sentinel 用 Raft 式投票，两者的共同前提都是「多数派还活着」 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Redis 入门到实战<br><sub>黑马程序员</sub> | [BV1cr4y1671t](https://www.bilibili.com/video/BV1cr4y1671t/) | §3.2 ② 槽迁移 | 主线课：数据结构与底层编码 → 持久化 → 主从/哨兵/集群 → 缓存三大问题与分布式锁；看完回 `ex01_fullsync_psync`（主从全量同步 PSYNC（fork RD）核对 |
| 2 | 尚硅谷 · Kafka 3.x 从入门到调优<br><sub>尚硅谷</sub> | [BV1vr4y1677k](https://www.bilibili.com/video/BV1vr4y1677k/) | 全章 | 比入门版多了调优与运维：ISR、HW/LEO、日志段与零拷贝、积压排查；看完回 `ex02_partial_repl_backlog`（部分同步）核对 |
| 3 | 尚硅谷 · RabbitMQ 消息队列<br><sub>尚硅谷</sub> | [BV1cb4y1o7zz](https://www.bilibili.com/video/BV1cb4y1o7zz/) | 全章 | 交换机类型、确认机制与死信队列；做选型对比时用它补齐「非日志型 MQ」的视角；看完回 `ex03_replconf_ack_offset`（REPLCONF ACK 心跳上报 of）核对 |
| 4 | 尚硅谷 · Kafka 快速入门<br><sub>尚硅谷</sub> | [BV1a4411B7V9](https://www.bilibili.com/video/BV1a4411B7V9/) | 全章 | Topic/Partition/Replica 模型、生产者与消费者、位移提交；讲清「顺序性只在分区内成立」；看完回 `ex04_sdown`（哨兵主观下线 SDOWN）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Redis 设计与实现》黄健宏 |
| 2 | 《Kafka 权威指南》Narkhede 等 |
| 3 | 《数据密集型应用系统设计》Kleppmann |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
