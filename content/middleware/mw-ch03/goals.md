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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | 含 Redis 与消息队列的高频面试知识 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 高并发与分布式：缓存、消息队列、分库分表专题 |
| [redis/redis](https://github.com/redis/redis) | 76640 | Redis 官方源码仓库：数据结构与命令实现的权威来源 |
| [apache/kafka](https://github.com/apache/kafka) | 33917 | Apache Kafka 官方仓库：架构与协议实现 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Redis 6 入门到精通 | [视频](https://www.bilibili.com/video/BV1Rv41177Af/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Kafka 教程 | [视频](https://www.bilibili.com/video/BV1a4411B7V9/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · RabbitMQ 新版教程 | [视频](https://www.bilibili.com/video/BV1sw4m1U7Qe/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Nginx 由浅入深 | [视频](https://www.bilibili.com/video/BV1zJ411w7SV/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · ZooKeeper 教程 | [视频](https://www.bilibili.com/video/BV1to4y1C7gw/) | 本学科配套视频，建议结合本章示例与习题观看 |
