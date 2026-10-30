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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,300 | 全章 | 含 Redis 与消息队列的高频面试知识；本章先读与「① 从「队列」到「分布式提…」「② Topic / Par…」相关的部分 |
| 2 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,162 | 全章 | 高并发与分布式：缓存、消息队列、分库分表专题；本章先读与「① 从「队列」到「分布式提…」「② Topic / Par…」相关的部分 |
| 3 | [redis/redis](https://github.com/redis/redis) | 76,964 | 全章 | Redis 官方源码仓库：数据结构与命令实现的权威来源；本章先读与「① 从「队列」到「分布式提…」「② Topic / Par…」相关的部分 |
| 4 | [apache/kafka](https://github.com/apache/kafka) | 34,141 | 全章 | Apache Kafka 官方仓库：架构与协议实现；本章先读与「① 从「队列」到「分布式提…」「② Topic / Par…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Redis 入门到实战<br><sub>黑马程序员</sub> | [BV1cr4y1671t](https://www.bilibili.com/video/BV1cr4y1671t/) | §3.2 ② 零拷贝与页缓存 | 主线课：数据结构与底层编码 → 持久化 → 主从/哨兵/集群 → 缓存三大问题与分布式锁；看完回 `ex01`（分区器）核对 |
| 2 | 尚硅谷 · Kafka 快速入门<br><sub>尚硅谷</sub> | [BV1a4411B7V9](https://www.bilibili.com/video/BV1a4411B7V9/) | §3.2 ② 零拷贝与页缓存 | Topic/Partition/Replica 模型、生产者与消费者、位移提交；讲清「顺序性只在分区内成立」；看完回 `ex02`（acks=0/1/all 的耐久性边界与）核对 |
| 3 | 尚硅谷 · Kafka 3.x 从入门到调优<br><sub>尚硅谷</sub> | [BV1vr4y1677k](https://www.bilibili.com/video/BV1vr4y1677k/) | §3.2 ② 零拷贝与页缓存 | 比入门版多了调优与运维：ISR、HW/LEO、日志段与零拷贝、积压排查；看完回 `ex03`（LEO / HW / LSO 三个 of）核对 |
| 4 | 尚硅谷 · RabbitMQ 消息队列<br><sub>尚硅谷</sub> | [BV1cb4y1o7zz](https://www.bilibili.com/video/BV1cb4y1o7zz/) | 全章 | 交换机类型、确认机制与死信队列；做选型对比时用它补齐「非日志型 MQ」的视角；看完回 `ex04`（幂等生产者）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Redis 设计与实现》黄健宏 |
| 2 | 《Kafka 权威指南》Narkhede 等 |
| 3 | 《数据密集型应用系统设计》Kleppmann |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
