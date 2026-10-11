# 二、可靠性开关：acks、重试、幂等与事务

> 「Kafka 会不会丢消息」这个问题问得太粗。正确问法是：
> **在 acks 取什么值、`min.insync.replicas` 取什么值、重试开不开、幂等开不开的组合下，最坏会丢多少？**

## ① acks：三档语义与各自的丢失窗口

| `acks` | 含义 | 什么时候算"成功" | 最坏丢失场景 |
|---|---|---|---|
| `0` | **不等任何确认** | `send()` 入队即算 | broker 宕机 / 网络断，**整批静默消失** |
| `1` | 只要 **leader** 写入即算 | leader 落盘 | leader 在副本同步前宕机 → 数据丢 |
| `all`（= `-1`） | 要求 **ISR 中所有副本**都写入 | 全部 ISR 落盘 | ISR 里只剩 leader 一个时，仍可能丢 |

⚠️ **关键误解**：`acks=all` 不等于「写入所有副本」。它等于「写入**当前 ISR 中的全部副本**」。
如果 ISR 因为副本落后而收缩到只剩 leader，`acks=all` 就**退化成了 `acks=1`**。
这就是 `min.insync.replicas` 必须存在的理由。

### 🧑‍💻 程序员视角

**工程决策**：
- 日志 / 埋点 / 可重放数据 → `acks=1`（甚至 `0`），把吞吐放在第一位；
- 交易 / 支付 / 不可丢的业务事件 → `acks=all` + `min.insync.replicas=2`（3 副本）或 `=2`（5 副本中容忍 2 个故障）；
- **绝不要** `acks=all` + `min.insync.replicas=1` —— 这个组合看起来"安全"，实则**和 `acks=1` 一样会丢**，只是多付了延迟。

**排查顺序**：消费者发现"消息少了"，按此顺序：
1. 查生产者指标 `record-error-rate` / `record-retry-rate`（是否在重试耗尽的路上）；
2. 查 Topic 的 `min.insync.replicas` 与当时的 ISR 大小（是否已退化成 1）；
3. 查 `unclean.leader.election.enable`（若为 true，落后副本可当选 → **直接丢已提交数据**）；
4. 最后才查消费者侧（是不是被 `auto.offset.reset` 跳过了）。

### 🎓 博士生视角

**第一性原理**：这是一次 **quorum 语义的选择**。设副本数 `R`、ISR 大小 `I`、`min.insync.replicas = m`。
`acks=all` 实际要求的是「写入 `I` 个副本」，而写入的前提是 `I ≥ m`。
因此系统能容忍的**同时故障副本数**是 `R - m`（当 `m = R` 时，容错为 0 —— 这就是 `min.insync.replicas=1` 的情形被放大的原因）。

**形式化**：设每个副本在单位时间内故障概率为 `p`、修复率 `μ`，则「提交后仍丢失」需要
（a）`m` 个确认副本全部故障，且（b）`unclean.leader.election=true` 允许一个**未包含该消息的副本**当选 leader。
条件 (b) 是**可用性对一致性的让渡**：Kafka 在这里选择了 CAP 中的 **AP 倾向**（可调），
所以 `unclean.leader.election.enable=true` 的语义是「用可能丢数据换取更快恢复可用」。

**与 Raft 的对照**：Raft 要求「过半确认」（`m > R/2`）才能提交，这保证任何两个 quorum 必有交集 ——
因此 Raft 中 `m` 的下界是硬性的（`R/2 + 1`）。Kafka 的 `min.insync.replicas` **没有强制过半**，
它是**可配置的（默认 1）**，这意味着 Kafka 把「一致性强度」交给了使用者，
代价是**配错就静默丢数据**。这是理解 Kafka 可靠性的钥匙。

### 📚 考研者视角

**标准问法**：「Kafka 如何保证消息不丢？」

**标准口径（三个环节，逐条给对策）**：

| 环节 | 丢失原因 | 对策 |
|---|---|---|
| **生产端** | `acks=0/1`；重试失败未处理；回调未检查 | `acks=all` + `retries=Integer.MAX_VALUE` + `enable.idempotence=true` + **处理回调异常** |
| **存储端** | ISR 收缩后 `acks=all` 退化；`unclean.leader.election=true` | `min.insync.replicas ≥ 2` + `unclean.leader.election.enable=false` + `replication.factor ≥ 3` |
| **消费端** | 位移**先提交后处理**；`enable.auto.commit=true` | **先处理业务、成功后手动提交位移**（至少一次语义） |

**高频易错点**：
- 「`acks=all` 就不会丢」→ 错，见上（ISR 收缩 + unclean 选举）；
- 「`replication.factor=3` 就不会丢」→ 错，还得看 `min.insync.replicas` 与 unclean 开关；
- 「消费端不会丢」→ 错，**自动提交 + 处理失败** 是最经典的丢消息路径。

**记忆锚点**：**「生产看 acks，存储看 ISR 与 min.insync，消费看提交时机」**。


## ② min.insync.replicas：与 acks=all 的配合

`acks=all` 决定「等谁确认」，`min.insync.replicas` 决定「ISR 至少要几个才允许写入」。两者是**正交**的。

设 `replication.factor=3`、`min.insync.replicas=2`：

| 当时 ISR | 生产者行为 |
|---|---|
| 3 个副本都在 | 写入 3 个后返回成功 |
| 2 个副本在 | 写入 2 个后返回成功（**仍满足 `≥2`**） |
| 只剩 leader | **拒绝写入**，抛 `NotEnoughReplicasException` |

**「拒绝写入」是特性不是 bug**：这是 Kafka 的 **C 优先**选择 —— 宁可不可写，也不接受一个可能立刻丢失的写入。
所以 `min.insync.replicas` 是**可用性与一致性的旋钮**。

### 🧑‍💻 程序员视角

**踩坑**：把 `min.insync.replicas` 设为与 `replication.factor` 相等的值（如 3 副本设 3），
意味着**任何一个副本挂掉，整个 Topic 立刻不可写**。生产环境的常见取值是 `replication.factor=3` + `min.insync.replicas=2`。

**另一个坑**：`min.insync.replicas` 可以设在 **Topic 级**也可以设在 **broker 级**，Topic 级优先。
如果只改了 broker 级默认值，**已存在的 Topic 不会继承**，容易造成"文档说改了、实际没生效"。

### 🎓 博士生视角

**第一性原理**：`min.insync.replicas` 定义了写入的**可用性下界**。设 `R=3, m=2`：
- 容错 `R - m = 1` 个副本故障时**仍可写**；
- 故障数达到 `R - m + 1 = 2` 时**拒绝写入**。

所以 `m` 的取值把系统放在「可用-一致」曲线上的不同点：

| `m` | 可容忍故障 | 一致性强度 | 可用性 |
|---|---|---|---|
| 1 | 2 | 弱（等同 `acks=1`） | 高 |
| 2 | 1 | 较强 | 中 |
| 3 | 0 | 最强（写入即全副本） | 低 |

对比 Raft：`R=3` 时 Raft 的 quorum 是 2，与 `m=2` 的 Kafka 语义接近 —— **但 Raft 强制这个值，Kafka 允许你设成 1**。
这个「允许设 1」的设计自由度，正是大量线上事故的来源。

### 📚 考研者视角

**标准问法**：「`acks=all` 和 `min.insync.replicas` 是什么关系？」

**标准口径**：**两个维度，互相独立**。`acks=all` 是**生产者的等待策略**（等 ISR 全部确认），
`min.insync.replicas` 是 **broker 的写入准入条件**（ISR 少于它就拒写）。
只有两者配合（如 `acks=all` + `min.insync.replicas=2`）才构成有效的持久性保证。

**一句话总结（面试可直接用）**：
> `acks=all` 决定「等谁」，`min.insync.replicas` 决定「够不够格写」。少了后者的 `acks=all` 是纸糊的。

## ③ 幂等生产者与事务

**幂等生产者（`enable.idempotence=true`，Kafka 1.0+）**：
- 生产者首次启动时从 broker 申请一个 **PID（Producer ID）**；
- 每条消息带一个 **(PID, 分区, 序列号)** 三元组，broker 端对每个 `(PID, 分区)` 维护已接收的最大序列号；
- 序列号 ≤ 已记录的 → **判为重复，丢弃**（这解决了重试导致的重复写入）。

**它解决什么**：**生产者重试**引起的同分区重复。**它不解决什么**：
- **跨会话重复**：生产者重启后 PID 会**变**（除非用事务 ID 固定），旧 PID 的去重信息不再适用；
- **应用层重复**：`send()` 成功但业务失败后你**又发了一遍**——那不是 Kafka 能管的。

**生产者事务（`transactional.id`）**：把多条消息的写入 + 位移提交绑成一个**原子单元**，配合消费者 `isolation.level=read_committed`，
实现「流处理场景的 exactly-once」。代价是：需要 `transactional.id`、事务超时管理、以及**只能保证 Kafka 内部的原子性**
（若下游是数据库，仍需要两阶段或幂等表）。

### 🧑‍💻 程序员视角

**工程决策顺序**：
1. 先开 `enable.idempotence=true` —— 它几乎没有性能代价（只多几个字段），而且会自动把 `acks` 提到 `all`、`retries` 提高、`max.in.flight` 限制在 5；
2. 再考虑是否需要事务。事务的成本在**延迟**（commit 需要额外的协调往返）和**运维复杂度**（事务超时、`transactional.id` 唯一性），**不是吞吐**；
3. 若下游是数据库，**优先在业务侧做幂等（唯一键 / 去重表）**，而不是把所有希望寄托在 Kafka 事务上。

**排查顺序**：遇到"明明开了幂等还是重复"，先确认重复是**跨分区**还是**跨会话**：
- 跨分区 → 分区器和 key 的问题（幂等只在分区内生效）；
- 跨会话 → 生产者重启，PID 变了（需要事务 ID 或业务侧幂等）。

### 🎓 博士生视角

**第一性原理**：幂等生产者实现的是一个**去重集合（dedup set）**，其状态是「每个 `(PID, 分区)` 已见过的最大序列号」。
这是一个**有界状态**（每个分区只需存一个整数），因此可以在 broker 内存中长期维护 —— 这正是它代价极低的原因。

**但它为什么有界却不完备**：因为 PID 的生命周期绑在生产者会话上。设会话重启后 PID 从 `P₁` 变成 `P₂`，
则 `seq(P₁) = 100` 与 `seq(P₂) = 1` 在 broker 看来是**两个不同的去重域**，重放的消息不会被识别为重复。
要跨会话去重，必须引入一个**比会话更长久的标识** —— 这正是 `transactional.id` 的作用：
它把 PID 的申请锚定在一个**稳定的名字**上，从而让跨会话的去重状态得以接续。

**这实际上是「至少一次 + 去重 = 精确一次」这条经典等式的具体实现**：
Kafka 不做「消息只发一次」（网络不可能保证），而是**允许重复 + 提供去重元数据**。

### 📚 考研者视角

**标准问法**：「Kafka 的幂等生产者能保证不重复吗？」

**标准口径**：**只能保证单分区、单会话内不重复**。

必须点出三个边界：
1. **单分区**：幂等状态是 `(PID, 分区)` 粒度的，跨分区不生效；
2. **单会话**：生产者重启后 PID 变化，跨会话不生效（需 `transactional.id`）；
3. **仅管 Kafka 侧**：它管不了「业务处理完但你又重发一次」。

**加分口径**：提到 `enable.idempotence=true` 会**自动把 `acks` 提升为 `all`**、`retries` 提升、
并把 `max.in.flight` 限制在 5（因为要保证顺序），这是它与「手写去重」的关键区别。

**记忆锚点**：**幂等 = 「PID + 分区 + 序列号」在三元组内的去重**。


## 小结

| 开关 | 解决 | 不解决 |
|---|---|---|
| `acks=all` | 等 ISR 全部确认 | ISR 只有 1 个时仍会丢 |
| `min.insync.replicas=2` | 阻止 ISR 收缩后继续写入 | 不提升写入速度 |
| `enable.idempotence` | 重试导致的同分区重复 | 跨会话 / 跨分区重复 |
| 事务 + `read_committed` | Kafka 内的原子写 | 跨系统的原子性 |
