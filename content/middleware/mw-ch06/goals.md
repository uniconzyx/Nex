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
