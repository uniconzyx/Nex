# 二、副本、ISR 与「不丢」的精确条件

## ① 副本因子与 Leader / Follower

一个分区可以有 `replication.factor` 个副本，其中：

- **Leader**：唯一对外提供读写服务的副本。生产者的写请求、消费者的读请求都只走 Leader。
- **Follower**：只做一件事——**主动向 Leader 拉取（fetch）数据**，保持与 Leader 的同步。

注意这个方向：**Follower 主动拉，而不是 Leader 推**。这是 Kafka 复制设计的关键选择，好处是：

1. Follower 可以自主控制拉取速率，不会被打挂（天然的背压）；
2. 允许**批量拉取**与**追赶**（follow 落后时自然加速）；
3. Leader 无需维护每个 Follower 的推送状态，逻辑更简单。

副本分布的约束：同一个分区的多个副本必须分布在**不同的 broker** 上（若配置了机架信息则尽量分布在不同机架），否则「副本」毫无容错意义。

### 🧑‍💻 程序员视角

工程上最需要警觉的是「**副本因子写成了 1**」。很多人测试环境图省事设 `replication.factor=1`，上线忘了改，于是任何一台 broker 重启都会导致该分区不可用（没有可选举的副本，只能等它回来）。

另一个常见误区是认为「副本越多越安全」。副本带来的成本是实打实的：

- **写入放大**：`acks=all` 时，Leader 要等所有 ISR 副本都写入才算成功 → 写延迟由**最慢的 ISR 副本**决定（长尾效应）；
- **网络与磁盘成本**：每增加一个副本，就多一份跨 broker 的网络传输与磁盘写入；
- **恢复时间**：broker 重启后要追赶的日志量随副本数增长。

所以生产环境常见配置是 **`replication.factor=3` + `min.insync.replicas=2`**：能容忍 1 个副本挂掉而仍可写，同时写延迟可控。这是「三副本 + 多数派」在可用性与成本之间的经典折中。

**排查顺序**：遇到「写入超时」，先看 `UnderReplicatedPartitions`（ISR 小于副本因子）与 `IsrShrinksPerSec`——如果有副本反复进出 ISR，说明某台 broker 的磁盘或网络跟不上，Leader 在等一个永远追不上的 Follower。

### 🎓 博士生视角

Kafka 的复制模型是**基于拉取的异步主从复制**，配合**动态的同步副本集合（ISR）**。这与 Raft/Paxos 这类**基于多数派日志共识**的协议有本质区别，务必不要混为一谈：

| 维度 | Kafka ISR 模型 | Raft / Paxos |
|---|---|---|
| 提交条件 | 所有 **ISR** 副本写入（集合并发动态变化） | **多数派**（majority）持久化 |
| 成员集合 | 动态（落后超 `replica.lag.time.max.ms` 即被踢出） | 固定成员集，多数派是静态定义 |
| 一致性保证 | 弱于 Raft（依赖 HW 且存在历史边界问题） | 强一致（线性一致） |
| 可用性 | 副本数减 1 仍可写（3 副本） | 同理，需多数派存活 |

ISR 的动态性是把双刃剑：**它保证了「只要还有 1 个副本同步，就可以继续写」**，但代价是「同步副本」的判定标准是**时间**（`replica.lag.time.max.ms`，默认 30s）而非「是否已持久化某一具体 offset」。这带来一个著名的历史问题：**HW 回退与日志截断（log truncation）**。当 Leader 切换时，新 Leader 的日志可能与旧 Leader 不一致，Follower 必须截断自己「多出来的」部分以求一致——而这段被截断的数据可能已经被消费者读过了（因为它曾在旧 Leader 上低于 HW）。这就是 Kafka 后来引入 **Leader Epoch** 的原因：用 `(epoch, offset)` 对来标记日志，避免仅靠 HW 判定一致性。

### 📚 考研者视角

**面试标准问答**：

- **问**：Kafka 的副本机制和 Raft 一样吗？**答**：不一样。Kafka 是**基于 ISR 的异步复制**（拉模式），提交条件是「ISR 全部写入」；Raft 是**多数派共识**，提交条件是「多数派持久化」。Kafka 的一致性弱于 Raft。
- **问**：副本因子 3 能容忍几个 broker 挂？**答**：**容忍 1 个**。若同时挂 2 个，ISR 只剩 1 个，此时若 `min.insync.replicas=2` 则**无法写入**（宁可不可写也不丢数据）；若没配 `min.insync.replicas`，则可能只剩一个副本，一旦它也挂则丢数据。
- **问**：ISR 是什么意思？**答**：**In-Sync Replicas**，与 Leader 保持同步的副本集合（含 Leader 自己）。判定标准是「副本的 LEO 落后 Leader 不超过 `replica.lag.time.max.ms`」。
- **易错**：以为 ISR 是「所有活着的副本」。**错**——一个活着但严重落后的副本会被踢出 ISR。

## ② ISR 与 acks：把「不丢」写成可验证的条件

`acks` 是**生产端**的参数，决定「什么时候算写入成功」：

| acks | 语义 | 耐久性 | 延迟 |
|---|---|---|---|
| `0` | 发出去就认为成功，不等任何响应 | **可能丢失**（broker 挂了都不知道） | 最低 |
| `1` | Leader 写入本地日志即返回 | Leader 挂 → 可能丢失（Follower 还没同步） | 中 |
| `all`（= `-1`） | 所有 **ISR** 副本都写入才返回 | 取决于 ISR 大小 | 最高 |

**关键陷阱**：`acks=all` 单独配置**并不保证不丢**。极端情况下 ISR 可能只剩 Leader 自己（其他副本都落后被踢出去了），此时 `acks=all` 等价于 `acks=1`。

所以真正的「不丢」条件是三个参数的 **联合约束**：

```
acks = all
min.insync.replicas = 2      # ISR 至少 2 个才允许写
replication.factor = 3       # 保证有 3 份物理拷贝
```

此时若 ISR 收缩到 1 个，broker 会**拒绝写入**（抛 `NotEnoughReplicasException`）。这是把「一致性优先于可用性」写进配置的做法 —— **宁可写入失败，也不写一份随时会丢的数据**。

### 🧑‍💻 程序员视角

**运维口诀**：`acks=all` 管生产端，`min.insync.replicas` 管 broker 端，两个都配才安全。

再补一个容易忽略的点：**`retries` 与幂等**。开重试是必要的（网络抖动、Leader 切换都会导致可重试的失败），但重试会带来两个问题：

1. **重复写入**：请求发出去了但响应丢了，重试就写了两条 → 靠 `enable.idempotence=true`（PID + sequence number 去重）解决；
2. **乱序**：`max.in.flight.requests.per.connection > 1` 时，重试的请求可能后于后续请求到达 → 幂等开启后 Kafka 会限制并发为 5 并保证顺序，或干脆设为 1。

所以生产端的安全组合是：**`acks=all` + `enable.idempotence=true` + `retries=MAX` + 限制 `max.in.flight`**。多数客户端在 `acks=all` + 幂等开启时已自动帮你调优。

**排查思路**：报「消息写不进去」时，先看异常类型——`NotEnoughReplicas` / `NotEnoughReplicasAfterAppend` 说明 ISR 不足（去查哪台 broker 掉队了）；`TimeoutException` 说明等待超时（看是不是有 Follower 一直追不上，拖累了 `acks=all` 的响应）。

### 🎓 博士生视角

把「不丢」形式化，需要区分**两种丢失**：

1. **已确认丢失**（acknowledged loss）：生产者收到了成功响应，但消息后来丢了。这是最严重的一类，**必须杜绝**。
2. **未确认丢失**（unacknowledged loss）：生产者没收到成功响应（超时/报错），消息可能没写进去。这可以通过重试 + 幂等收敛。

`acks=all + min.insync.replicas=2 + rf=3` 想表达的命题是：

> 若生产者收到成功响应，则消息至少存在于 **2 个** broker 的磁盘上。

为什么是「至少 2」而不是「至少 1」？因为若只有 1 份，那台 broker 的磁盘损坏即永久丢失。2 份意味着「容忍同时损坏 1 份」。在分布式存储里，**「先落盘再确认」+「多副本」** 是达成持久性的标准组合，`min.insync.replicas` 就是把「多副本」这个条件**从概率性保证升级为确定性约束**：只要 ISR ≥ 2，成功响应就意味着 2 份落盘；ISR < 2 时直接拒绝，不让「假成功」发生。

对照 CAP：这个配置选择了 **CP**（拒绝写入以保证一致性）。若改成 `acks=1` 或 `min.insync.replicas=1`，就偏向 AP（可用性优先，接受极端情况下的数据丢失）。

### 📚 考研者视角

**面试标准问答**：

- **问**：`acks=all` 就一定不丢消息吗？**答**：**不一定**。若 ISR 收缩到只剩 Leader，`acks=all` 等价于 `acks=1`。必须同时设置 **`min.insync.replicas >= 2`**，此时 ISR 不足会拒绝写入。
- **问**：`acks=0/1/all` 分别适用什么场景？**答**：`0` 用于日志采集等可容忍丢失的高吞吐场景；`1` 用于一般业务但接受极端丢数据；`all` 用于金融/订单等不允许丢的场景。
- **问**：怎么保证消息不丢？**答**：三层——**生产端** `acks=all` + `retries` + 幂等；**broker 端** `min.insync.replicas>=2` + `replication.factor>=3` + `unclean.leader.election.enable=false`；**消费端** 处理完成后手动提交位点。
- **易错**：只答「acks=all」。面试官问「为什么」时答不上 `min.insync.replicas`，基本会被判定为只背了结论。

## ③ LEO / HW / LSO：三个 offset 撑起一致性

| 名称 | 全称 | 含义 |
|---|---|---|
| **LEO** | Log End Offset | 该副本**下一条**待写入的位置（即已有 N 条消息则 LEO = N） |
| **HW** | High Watermark | ISR 中**最小的 LEO**；消费者**只能读到 HW 之前**的消息 |
| **LSO** | Last Stable Offset | 事务场景下，**未提交事务的第一个 offset**；消费者（`read_committed`）只能读到 LSO 之前 |

它们的推进关系：

```
HW = min(LEO of all replicas in ISR)
消费者可见范围 = [0, HW)          （普通场景）
消费者可见范围 = [0, LSO)          （read_committed 事务场景，LSO <= HW）
```

**为什么消费者只能读到 HW？** 因为 HW 之前的消息**在所有 ISR 副本上都已存在**——即使此刻 Leader 挂了，新 Leader（从 ISR 中选出）也一定有这些数据，消费者读到的东西不会「消失」（即不会发生数据的回滚/截断）。HW 之后、LEO 之前的消息只存在于部分副本上，一旦发生 Leader 切换可能被截断，**此时读出去就会造成「已消费数据凭空消失」**。所以 Kafka 用 HW 做「安全可读」的水位线。

### 🧑‍💻 程序员视角

**HW 的直接工程后果：消费者看到的延迟 ≈ `HW 落后 LEO 的距离`。** 副本同步有网络往返时间，所以 Kafka 的端到端延迟天然包含「等 ISR 确认」这一段。这解释了两个现象：

- `acks=all` 时生产者延迟明显高于 `acks=1`（要等所有 ISR 落盘 + HW 推进相关往返）；
- 消费者「明明写入成功了，却暂时读不到」——多半是 HW 还没推进（某个 Follower 拉取慢）。

**调优方向**：

- 降低延迟 → 减小 `replica.lag.time.max.ms`（更快踢出掉队副本）或减少副本数；也可以调 `replica.fetch.wait.max.ms`。
- 提高吞吐 → 增大 `replica.fetch.min.bytes` / `replica.fetch.max.bytes`（批量拉取）。
- 注意 `replica.fetch.max.bytes` 与 `message.max.bytes` 的关系：若单条消息大于 Follower 一次能拉的上限，Follower 会陷入「永远拉不到这条消息」的死循环 → 必须让 `replica.fetch.max.bytes >= message.max.bytes`。

**排查思路**：遇到「消息写入成功但消费者长时间读不到」，去查 `kafka-log-dirs` 看各副本的 LEO 差值，或看 JMX 的 `ReplicaFetcherManager` 指标，定位是哪台 broker 拖住了 HW。

### 🎓 博士生视角

这三个 offset 共同构成一个**一致性水位（consistency watermark）**机制，是分布式复制日志里非常经典的设计。

把它抽象出来看：在一个主从复制的日志系统中，Leader 的 LEO 是「**已写入**」的位置，而系统对外的「**已提交（committed）**」位置必须取所有副本的**最小值**——因为只有这样才能保证「任何一台副本接任 Leader 后，都不会丢掉这些已提交的数据」。所以：

> 已提交位置 = min{ LEO_i : i ∈ ISR } = HW

这本质上与 Raft 的 **commitIndex = median(matchIndex)** 是同一个思想，区别只在于：

- Raft 取**多数派的中位数**（因为成员集固定、多数派交集性质保证正确性）；
- Kafka 取 **ISR 的最小值**（因为 ISR 是动态收缩的，收缩本身就是「剔除不可靠副本」的动作，所以剩余成员的最小值即可保证安全）。

**Leader Epoch 的引入**正是为了修补「仅靠 HW 无法区分日志是否属于同一任 Leader」的问题：新 Leader 在接任时写入一个 epoch 递增的 leader-epoch checkpoint，Follower 用 `(epoch, startOffset)` 来判定该截断到哪，而不是简单地把自己的日志截到 HW。这消除了「HW 回退」导致的日志不一致窗口。

### 📚 考研者视角

**面试标准问答**：

- **问**：HW 是什么？为什么消费者只能读到 HW？**答**：HW = ISR 中最小 LEO，代表「所有 ISR 副本都已拥有的位置」。只读到 HW 是为了保证**已消费的数据不会因 Leader 切换被截断**（即不会发生「消费过的数据凭空消失」）。
- **问**：LEO 和 HW 的关系？**答**：LEO 是「写入到哪」，HW 是「安全可读到哪」，恒有 `HW ≤ LEO`；Leader 与 Follower 同步推进，HW 由 ISR 中最慢的副本决定。
- **问**：LSO 是什么？**答**：`Last Stable Offset`，事务场景下 **未提交事务的第一个 offset**。消费者设 `isolation.level=read_committed` 时只读到 LSO 之前，从而不会读到未提交事务的消息。
- **易错**：把 HW 说成「Leader 写入的最高 offset」。**错**——Leader 写入的位置是 LEO；HW 是**所有 ISR 副本**都已达到的位置。
