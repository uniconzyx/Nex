# 四、消费者组与位点：有序、不重、可重放

## ① 消费者组与 rebalance

**核心不变量**：在同一个消费者组内，**一个分区同一时刻只能被一个消费者消费**。这条规则带来两个直接后果：

- 组内消费者的最大并行度 = 分区数；
- 「同一个 key 的消息按顺序被处理」在组内是成立的（因为该 key 只落在一个分区，而该分区只被一个消费者读）。

**Rebalance（再均衡）** 是「重新分配分区给组内消费者」的过程，触发条件有三类：

1. **成员变化**：消费者加入、退出、崩溃（心跳超时）；
2. **订阅变化**：消费者用正则订阅了新的 topic；
3. **分区变化**：topic 增加了分区。

rebalance 期间，分区会被**撤销（revoke）**再**分配（assign）**，这期间消费会短暂停摆（Eager 协议下是 stop-the-world）。所以「频繁 rebalance」是消费延迟尖刺与重复消费的常见根因。

三种协议：

| 协议 | 行为 | 代价 |
|---|---|---|
| **Eager**（Range/RoundRobin） | 所有消费者**放弃全部分区**，等协调者重新分配 | stop-the-world，影响面最大 |
| **Cooperative**（CooperativeSticky） | 只撤销**需要迁移**的分区，其余继续消费 | 可能需多轮才能收敛，但影响面小 |
| **静态成员**（`group.instance.id`） | 消费者重启后在 `session.timeout.ms` 内不被踢出 | 避免滚动重启引发的连锁 rebalance |

### 🧑‍💻 程序员视角

**rebalance 是消费端最容易被忽视的性能陷阱。** 一次 Eager rebalance 会让**所有**消费者停下，等协调者完成分配——如果分区很多（几千个），这个过程可能持续几十秒，期间消费完全停摆、位点可能重复提交或漏提交。

工程上的四条防线：

1. **避免 `max.poll.interval.ms` 超时**：这是**最常见的 rebalance 原因**。消费一批消息后若处理时间超过了 `max.poll.interval.ms`（默认 5 分钟），协调者会认为该消费者已死并踢出它 → 触发 rebalance。解决办法：缩小 `max.poll.records`（每批少取点）、或把处理逻辑异步化、或调大 `max.poll.interval.ms`。
2. **滚动重启用静态成员**：给每个消费者配 `group.instance.id`，重启时在 `session.timeout.ms` 内不触发 rebalance，避免「重启第一个就引发全组 rebalance」的雪崩。
3. **升级到 CooperativeSticky 协议**：减少 stop-the-world 的影响面（只有需要迁移的分区会短暂停）。
4. **`session.timeout.ms` 与心跳线程分离**：心跳由独立线程发送，不受业务处理阻塞（Kafka 0.10.1+ 已如此），所以 `session.timeout.ms` 可以设得较小（如 10s）以更快发现真故障，而不必担心被业务拖累。

**排查顺序**：看消费延迟尖刺时，先查协调者日志（`GroupCoordinator`）里的 rebalance 记录与原因（`MemberTimeout` / `RebalanceInProgress`），再查消费者的 `poll` 间隔。

### 🎓 博士生视角

消费者组的分配问题在形式上是一个**带约束的划分（partitioning）问题**：

> 把 P 个分区划分给 C 个消费者，每个分区恰好属于一个消费者（组内互斥），最小化「负载不均」。

这是一个 NP-hard 的均衡划分问题（等价于 multiway number partitioning），所以 Kafka 用的是**启发式**（Range / RoundRobin / Sticky）。

**Range 策略的倾斜**可以精确刻画：设 `P = q·C + r`（0 ≤ r < C），则前 `r` 个消费者分到 `q+1` 个分区，其余分到 `q` 个。当 `r` 接近 C 时，负载比达到 `(q+1)/q` —— 当 q=1、C 很大时（例如 P=100, C=60 → q=1, r=40），前 40 个消费者 2 个分区、后 20 个 1 个分区，**负载差 100%**。这就是「分区数取消费者数整数倍」这条经验的定量来源。

**Sticky 策略**的动机是**减少 rebalance 时的迁移量**：在保证均衡的前提下，尽量让分区留在原来的消费者上（用图着色/贪心近似求解），从而减少「撤销-重分配」带来的消费中断与重复。

**Cooperative 协议**则改变了「先撤销全部再分配」的两阶段语义，改为**增量式**：协调者计算出「需要迁移」的分区集合，只撤销这些，消费者重新加入后协调者再分配（可能需要多轮收敛）。它的正确性依赖「消费者保留未撤销分区的所有权」，这是一个**协议层面的不变量**。

### 📚 考研者视角

**面试标准问答**：

- **问**：怎么保证同一个消费者组内消息不被重复消费？**答**：同一个组的同一个分区只被一个消费者消费，**天然不会重复**；但 rebalance 时「消费者已处理但未提交位点」的那批消息会被新消费者重新读，因此**需要业务幂等**。跨消费者组则每个组独立消费一份（这是设计如此，不算重复）。
- **问**：rebalance 什么时候发生？**答**：① 组内成员数变化（加入/退出/心跳超时/`max.poll.interval.ms` 超时）；② 订阅的 topic 变化；③ 订阅 topic 的分区数变化。
- **问**：怎么避免频繁 rebalance？**答**：合理设置 `session.timeout.ms` / `heartbeat.interval.ms` / `max.poll.interval.ms`；控制 `max.poll.records` 让单批处理时间可控；滚动重启时使用**静态成员**（`group.instance.id`）；升级到 **CooperativeSticky** 协议。
- **易错**：把 `session.timeout.ms` 与 `max.poll.interval.ms` 混为一谈。前者管「心跳是否收到」（心跳由后台线程发），后者管「两次 `poll()` 的间隔」（由业务处理速度决定）。

## ② 分区分配策略：Range / RoundRobin / Sticky

`partition.assignment.strategy` 可选：

| 策略 | 分配方式 | 问题 |
|---|---|---|
| **Range**（默认） | 对每个 topic 的分区排序，按消费者数**均分区间** | 分区数不整除时**前几个消费者多分**，且订阅多个 topic 时倾斜叠加 |
| **RoundRobin** | 所有 topic 的分区**拉平**后逐个轮询分配 | 均衡性好，但 rebalance 时迁移量大（不保持黏性） |
| **Sticky** | 均衡 + 尽量**保持上次分配**，减少迁移 | 计算复杂，收敛稍慢 |
| **CooperativeSticky** | Sticky + 增量式 rebalance（不停止消费） | 需要多轮收敛；要求客户端版本较新 |

### 🧑‍💻 程序员视角

**选型建议**：绝大多数新项目直接用 **`CooperativeStickyAssignor`**——它同时拿到「黏性（少迁移）」与「增量（少停摆）」两个好处。

**什么时候必须避开 Range**：订阅了**多个** topic 且各 topic 分区数不一致时，Range 的倾斜会**按 topic 累加**。例如订阅 A（3 分区）与 B（3 分区）、2 个消费者：Range 给消费者 1 分 A0、A1 与 B0、B1，消费者 2 只拿到 A2、B2 → 负载比 2:1。

**排查思路**：用 `kafka-consumer-groups.sh --describe --group <g>` 查看每个消费者分到的分区，若明显不均（某消费者分区数是别人的两倍），先确认策略是否为 Range、分区数是否被消费者数整除。

### 🎓 博士生视角

四种策略可以放在同一个优化目标下比较：

```
minimize( 负载不均衡 + λ · 迁移量 )
```

- Range：只优化均衡（且是「按区间」的粗糙均衡），完全不考虑迁移量 → 倾斜 + 迁移大；
- RoundRobin：优化均衡（更细粒度），但也不考虑迁移量；
- Sticky：显式加入迁移量项（λ > 0），用近似算法求「均衡前提下的最小迁移」；
- CooperativeSticky：Sticky 的目标函数 + 增量协议（把「撤销」变成部分撤销，缩短不可用窗口）。

**Range 倾斜的精确表达**：对每个 topic 独立做 `P = q·C + r` 的切分，然后**按 topic 叠加**。因此总负载的不均衡度是各 topic 倾斜的**线性叠加**——订阅的 topic 越多、分区数越不规整，最坏情况越差。这解释了为什么「多 topic 订阅 + Range」是重灾组合。

### 📚 考研者视角

**面试标准问答**：

- **问**：Kafka 默认的分区分配策略是什么？**答**：**RangeAssignor**（按 topic 逐一分区间）。新版客户端推荐 **CooperativeStickyAssignor**。
- **问**：Range 策略有什么问题？**答**：当分区数不能被消费者数整除时，**靠前的消费者会多分到分区**；订阅多个 topic 时倾斜会叠加，导致负载不均（长尾消费者）。
- **问**：怎么让负载更均匀？**答**：换 **RoundRobin** 或 **Sticky/CooperativeSticky**；并让**分区数是消费者数的整数倍**。
- **易错**：以为分区分配一定均匀。**默认的 Range 在整除条件下才均匀。**

## ③ 位点提交与三种投递语义

**位点（offset）** 是消费者「读到哪里」的记录，存放在内部 topic **`__consumer_offsets`** 中（key = `(group, topic, partition)`）。

提交时机决定投递语义：

| 语义 | 做法 | 后果 |
|---|---|---|
| **at-most-once（至多一次）** | **先提交位点，再处理消息** | 处理失败则消息丢（已提交，不会重读） |
| **at-least-once（至少一次）** | **先处理消息，再提交位点** | 处理成功但提交失败 → 重读 → **重复** |
| **exactly-once（精确一次）** | 处理与提交在**同一事务**中（`sendOffsetsToTransaction`） | 需要事务支持，成本最高 |

**自动提交的陷阱**：`enable.auto.commit=true`（默认）时，Kafka 按 `auto.commit.interval.ms`（默认 5s）提交的是 **`position`（已 poll 到但可能还没处理完的位点）**。所以默认配置 ≈ **at-most-once**，处理过程中崩溃会丢消息。**几乎所有「消息莫名少了几条」的事故都源于此。**

### 🧑‍💻 程序员视角

**默认配置不安全，这是本章最需要带走的一条。**

生产上的标准做法：

```properties
enable.auto.commit=false
# 处理完一批后手动提交
consumer.commitSync()          // 同步提交：可靠但慢
// 或 consumer.commitAsync()   // 异步提交：快但可能失败
```

**「处理」的边界要自己想清楚**：如果处理是「写数据库」，那提交位点必须发生在**数据库事务提交之后**；否则「位点已提交但数据库回滚」→ 丢消息。反过来说，如果先写库再提交位点，中途崩溃会导致**重复写库**，所以写库必须幂等（唯一键 / upsert / 去重表）。

**一个进阶技巧**：把「消息 + 位点」放进同一个外部事务。Kafka 0.11+ 提供了 `sendOffsetsToTransaction`，让「写下游 Kafka topic」与「提交位点」原子化——这是 Kafka Streams 实现 exactly-once 的基础。但**如果下游是 MySQL**，Kafka 的事务管不到 MySQL，exactly-once 只能在应用层用幂等实现（这是常见误解：以为开了 Kafka 事务就万事大吉）。

**排查顺序**：遇到「消息重复」，先确认是不是 at-least-once 语义下的正常重复（rebalance 或提交失败引起），再检查业务是否幂等；遇到「消息丢失」，先查 `enable.auto.commit` 与提交时机。

### 🎓 博士生视角

三种语义的本质区别在于**「副作用的发生」与「位点推进」这两个事件的顺序约束**：

设 `E` = 业务副作用完成，`C` = 位点提交完成。

- **at-most-once**：`C` 先于 `E`。不变量是「已提交的位点一定不会重读」→ 崩溃时 `[c, position)` 丢失。
- **at-least-once**：`E` 先于 `C`。不变量是「未提交的位点一定会重读」→ 崩溃时 `[c, position)` 重复。
- **exactly-once**：要求 `E` 与 `C` **原子**（要么都成功要么都失败）。在单机数据库语境下这等价于「把位点写进同一个事务」；在分布式语境下需要 **分布式事务 / 幂等 + 去重**。

**一个重要的不可能性认识**：真正的 exactly-once 在分布式系统中无法仅靠消息中间件实现，只有当「副作用」也参与同一事务域时才可以。Kafka 能做到「Kafka 内部 exactly-once」（写 Kafka topic + 提交位点原子），但**跨系统（如 Kafka -> MySQL）就只能退化为 at-least-once + 消费端幂等**。这条边界是面试高频追问点，也是最容易答错的点。

### 📚 考研者视角

**面试标准问答**：

- **问**：Kafka 怎么保证消息不重复消费？**答**：**不能保证**。默认 `enable.auto.commit=true` 时是**at-most-once**（可能丢）；关闭自动提交、处理完再提交则是**at-least-once**（可能重复）。要做到不重，需要**消费端幂等**（唯一键 / 去重表 / upsert），或使用 Kafka 事务 + `sendOffsetsToTransaction`（仅限下游也是 Kafka）。
- **问**：`enable.auto.commit=true` 有什么问题？**答**：提交的是 `position` 而非「处理完成的位置」，且提交时机由时间驱动（`auto.commit.interval.ms`），因此**处理未完成就提交 → 崩溃丢消息**（at-most-once）。
- **问**：位点存在哪？**答**：内部 topic **`__consumer_offsets`**（默认 50 个分区，`cleanup.policy=compact`），key 为 `(group, topic, partition)`。
- **易错**：以为「关闭自动提交 + 手动提交」= 不重复。实际是 **at-least-once**，重复仍会发生（rebalance、提交失败），必须配幂等。
