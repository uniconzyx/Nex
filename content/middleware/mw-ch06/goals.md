# 学习目标 · Kafka 生产者与消费者机制（mw-ch06）

> 上一章（mw-ch05）解决了「消息存在哪里」——提交日志、分区、副本、ISR。
> 这一章解决「消息怎么进来、怎么出去」以及**一路上会丢在哪、会重在哪**。

## 一、本章要解决的问题

1. **生产者把消息发到哪个分区？** 有 key 和无 key 的分区策略为什么不一样？「同 key 同分区」靠什么保证？
2. **「发送成功」这四个字到底意味着什么？** `acks=0` / `acks=1` / `acks=all` 分别把哪些数据放到了风险里？
3. **为什么会重复消费？** 重复消费是 bug，还是某种交付语义下的**必然代价**？
4. **位移（offset）什么时候提交才不丢不重？** 自动提交为什么会「静默丢消息」？
5. **rebalance 为什么被称为 Stop-The-World？** 它由什么触发？增量式（Cooperative）改善了哪一部分？

## 二、学完你能做到

- 对一个具体的业务（订单、日志、埋点），**选对 acks 与 `min.insync.replicas` 的组合**，并说清最坏情况下会丢多少。
- 判断一段生产者代码**是否真的能保证顺序**（关键在 `max.in.flight.requests.per.connection` 与幂等开关）。
- 判断一段消费者代码属于 **at-most-once / at-least-once / exactly-once** 中的哪一种，并指出重复或丢失的**具体窗口**。
- 读懂 `__consumer_offsets` 里存的到底是什么，以及为什么它本身也是一个分区化的日志。
- 在面试中把「Kafka 如何保证不丢消息」回答成**三个环节 + 每条对策**的结构化答案，而不是背一句话。

## 三、知识清单

| 模块 | 关键概念 | 对应章节 |
|---|---|---|
| 生产者路径 | 分区器、粘性分区、RecordAccumulator、Sender 线程、攒批 | concept 01 |
| 生产者可靠性 | acks、retries、`delivery.timeout.ms`、`min.insync.replicas` | concept 02 |
| 精确一次 | 幂等生产者（PID + 序列号）、生产者事务、`read_committed` | concept 02 |
| 消费者组 | 组协调者、分区分配策略、rebalance 协议（Eager / Cooperative） | concept 03 |
| 位移与语义 | 自动/手动提交、同步/异步、`__consumer_offsets`、三种交付语义 | concept 04 |

## 四、学习路径建议

1. 先读 concept 01 建立「一条消息的完整旅程」这张地图，**不要在没搞清分区器之前谈可靠性**。
2. 再读 concept 02。`acks` 与 `min.insync.replicas` 必须**一起**理解，单独记住 `acks=all` 是不够的。
3. 然后读 concept 03、04。把 rebalance 与位移提交连起来看：**rebalance 期间正是重复消费的高发窗口**。
4. 最后跑 `examples/` 里的 12 个模拟：它们把「丢在哪、重在哪」变成**可数的数字**。

## 五、自检标准

- [ ] 能画出一条消息从 `send()` 到被消费者读到的完整链路，并标出每一段可能出问题的地方。
- [ ] 能说清 `acks=all` + `min.insync.replicas=1` 为什么**仍然可能丢**。
- [ ] 能解释幂等生产者为什么**只解决重复写入，不解决跨会话重复**（PID 会变）。
- [ ] 能写出「消费者多、分区少」和「分区多、消费者少」两种情况下**哪些消费者会空闲**。
- [ ] 能指出 `enable.auto.commit=true` 在生产环境中最典型的丢失场景。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | 全章 | 含 Redis 与消息队列的高频面试知识；本章先读与「① 分区器」「② 攒批与吞吐」相关的部分 |
| 2 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | 全章 | 高并发与分布式：缓存、消息队列、分库分表专题；本章先读与「① 分区器」「② 攒批与吞吐」相关的部分 |
| 3 | [redis/redis](https://github.com/redis/redis) | 77,127 | 全章 | Redis 官方源码仓库：数据结构与命令实现的权威来源；本章先读与「① 分区器」「② 攒批与吞吐」相关的部分 |
| 4 | [apache/kafka](https://github.com/apache/kafka) | 34,105 | 全章 | Apache Kafka 官方仓库：架构与协议实现；本章先读与「① 分区器」「② 攒批与吞吐」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Redis 入门到实战<br><sub>黑马程序员</sub> | [BV1cr4y1671t](https://www.bilibili.com/video/BV1cr4y1671t/) | 全章 | 主线课：数据结构与底层编码 → 持久化 → 主从/哨兵/集群 → 缓存三大问题与分布式锁；看完回 `ex01`（分区器对比）核对 |
| 2 | 尚硅谷 · Kafka 快速入门<br><sub>尚硅谷</sub> | [BV1a4411B7V9](https://www.bilibili.com/video/BV1a4411B7V9/) | 全章 | Topic/Partition/Replica 模型、生产者与消费者、位移提交；讲清「顺序性只在分区内成立」；看完回 `ex02`（linger.ms 与 batch.si）核对 |
| 3 | 尚硅谷 · Kafka 3.x 从入门到调优<br><sub>尚硅谷</sub> | [BV1vr4y1677k](https://www.bilibili.com/video/BV1vr4y1677k/) | 全章 | 比入门版多了调优与运维：ISR、HW/LEO、日志段与零拷贝、积压排查；看完回 `ex03`（acks=0/1/all 的「已确认却丢）核对 |
| 4 | 尚硅谷 · RabbitMQ 消息队列<br><sub>尚硅谷</sub> | [BV1cb4y1o7zz](https://www.bilibili.com/video/BV1cb4y1o7zz/) | 全章 | 交换机类型、确认机制与死信队列；做选型对比时用它补齐「非日志型 MQ」的视角；看完回 `ex04`（acks=all + min.insyn）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Redis 设计与实现》黄健宏 |
| 2 | 《Kafka 权威指南》Narkhede 等 |
| 3 | 《数据密集型应用系统设计》Kleppmann |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
