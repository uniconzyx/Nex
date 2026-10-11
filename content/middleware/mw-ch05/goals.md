# 学习目标 · Kafka 架构：Topic、Partition 与 Replica（mw-ch05）

## 一、本章要解决的问题

消息队列不是「把消息从 A 搬到 B」这么简单。当一条订单状态变更需要同时被风控、推荐、数仓、通知四个系统消费，且要求**不丢、不重、按分区有序、能重放历史**时，你要面对的是一整套分布式日志的设计取舍。本章把 Kafka 的模型拆到「为什么这么设计」的层面。

## 二、学完你能做到

1. **说清 Kafka 与传统 MQ 的模型差异**：为什么 Kafka 的 broker 不知道「谁读到哪」，以及这个设计如何换来高吞吐与可重放。
2. **准确使用分区**：分区是并行度的单位、是有序性的边界；能根据吞吐与延迟需求算出合理的分区数，并说清「分区数只能增不能减」的代价。
3. **讲透副本与 ISR**：`acks=0/1/all` 各自的耐久性语义，`min.insync.replicas` 为什么必须一起配；`LEO` / `HW` / `LSO` 三个 offset 的推进关系，以及为什么消费者只能读到 HW 之前。
4. **解释高吞吐的来源**：顺序写 + 页缓存 + 稀疏索引 + 零拷贝（`sendfile`），并能量化对比传统 `read + write` 的拷贝次数。
5. **设计消费者组**：rebalance 的触发与三种协议（Eager / Cooperative / 静态成员），四种分区分配策略的差异与倾斜问题，以及位点提交与三种投递语义的对应关系。

## 三、知识清单

| 主题 | 关键点 |
|---|---|
| 提交日志模型 | append-only、offset、消费者自己维护位点 |
| Topic / Partition | 逻辑主题 vs 物理分区目录；offset 单调递增 |
| 并行度 | 分区数 = 消费并行度上限；分区键决定有序范围 |
| 副本与 ISR | 副本因子、Leader/Follower、ISR 收缩与扩张 |
| acks 语义 | acks=0/1/all 与 min.insync.replicas 的组合 |
| Offset 三元组 | LEO（写入位置）、HW（可读上界）、LSO（事务上界） |
| 存储 | segment / .index / .timeindex、稀疏索引、日志保留与压实 |
| 零拷贝 | sendfile、页缓存、4 次拷贝 vs 2 次 |
| 消费者组 | rebalance 协议、四种分配策略、位点提交与投递语义 |

## 四、学习路径建议

1. 先读 `01-commit-log-and-partition.md`，建立「分布式日志」的第一性认识；
2. 再读 `02-replica-isr-and-leader-election.md`，把「不丢」这件事量化到 acks + ISR；
3. 然后读 `03-storage-log-segment-and-zerocopy.md`，理解吞吐为什么能到百万级；
4. 最后读 `04-consumer-group-and-offset.md`，落到消费端的位点与投递语义；
5. 做完 `exercises.json` 的 8 道题与 `project.json` 的分区规划项目，用 `examples/` 的 12 个可运行模拟把每个结论验证一遍。

## 五、自检标准

- 能不用看笔记画出「生产者 -> Leader -> ISR 同步 -> HW 推进 -> 消费者读取」的时序；
- 被问到「acks=all 会不会丢消息」，能立刻反问 `min.insync.replicas` 配了多少；
- 被问到「怎么保证顺序」，能回答「先明确顺序的边界是分区，再谈分区键」。


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
