# 二、哨兵（Sentinel）：故障发现与故障转移

本文件覆盖两个核心主题：**① 主观下线 SDOWN 与客观下线 ODOWN（quorum 投票）** 与 **② Raft 式 leader 选举与故障转移的选主规则（优先级 → offset → runid）**。

---

## ① 主观下线 SDOWN 与客观下线 ODOWN（quorum 投票）

（中立陈述）每个哨兵独立地以 `down-after-milliseconds` 为阈值：若在该时间内没收到主节点的有效心跳（PING 未回 PONG/LOADING/MASTERDOWN），该哨兵**单方面**认定主节点「主观下线（SDOWN）」。单个哨兵的 SDOWN 不足以触发故障转移——它向其他哨兵发送 `is-master-down-by-addr` 询问，当**确认下线的票数 ≥ quorum** 时，哨兵把主节点标记为「客观下线（ODOWN）」，ODOWN 才是真正启动故障转移的门槛。见 `examples/ex04_sdown.json`、`ex05_odown_quorum.json`。

### 🧑‍💻 程序员视角
- **quorum 不是「多数派」**：quorum 只是「确认 SDOWN 的哨兵数门槛」，通常设成小于哨兵总数（如 3 哨兵配 quorum=2）；它和后续 leader 选举所需的「多数派」是两个不同概念，别混淆。
- **`down-after-milliseconds` 调小 vs 调大**：调小能更快发现故障但易因网络抖动误判（抖动 → 误 ODOWN → 不必要的故障转移）；调大则发现慢。一般设 5s~30s，配合网络质量权衡。
- **脑裂防护要靠 quorum + 真实隔离**：仅靠哨兵投票无法彻底避免脑裂（见第三文件），SDOWN/ODOWN 只是「逻辑判定」，真正防止双主要靠 `min-replicas` 或外部 fencing。
- **哨兵也要奇数 + ≥3 节点**：哨兵本身做分布式判定，少于 3 个无法在节点故障后仍可靠形成 quorum，且网络分区时易脑裂。

### 🎓 博士生视角
- **SDOWN 是「本地观测」、ODOWN 是「群体共识」**：SDOWN 依据单哨兵的连续心跳缺失（通常默认连续失败即判，Redis 内部还有 `SENTINEL` 的 PING 重试与 `master-link-down` 状态），是主观、易错的；ODOWN 通过 `is-master-down-by-addr` 的 gossip 式询问聚合多哨兵意见，把「我看不见」升级为「大家都看不见」，降低误判。
- **quorum 的数学语义**：设哨兵集合 S、总数 N，ODOWN 成立条件是「含自身在内的 ≥ quorum 个哨兵报告 SDOWN」；注意 quorum 不要求 > N/2，因此 ODOWN 判定与 leader 选举的多数派门槛解耦设计，避免「N/2 失败就完全卡死」。
- **为什么先 SDOWN 再 ODOWN**：若每个哨兵直接对全局广播「主挂了」会放大抖动误判；两阶段让「本地失效探测」与「全局决策」分离，ODOWN 的多哨兵确认天然实现了「少数服从多数」的容错。

### 📚 考研者视角（笔面考点）
- **标准定义**：SDOWN = 单个哨兵在 `down-after-milliseconds` 内未收到主节点有效回复而**单方面**判定下线；ODOWN = 达到 quorum 个哨兵都认定 SDOWN 后，哨兵集群**共识**判定主节点真正下线，才触发故障转移。
- **经典辨析**：quorum 是「确认下线的哨兵数」，不是 Raft 的「多数派」；ODOWN 需要 quorum 同意而非 N/2+1 同意——这是高频扣分点。
- **易错口径**：SDOWN 不会自动变 ODOWN，必须由哨兵间 `is-master-down-by-addr` 投票累计到 quorum；并且「哨兵判定 ODOWN」与「实际选谁当新主/谁来执行故障转移」是两件事（后者靠 Raft 选 leader）。

---

## ② Raft 式 leader 选举与故障转移的选主规则

（中立陈述）主节点进入 ODOWN 后，哨兵集群需要从多个哨兵中选出一个「leader 哨兵」来实际执行故障转移（避免多个哨兵同时执行造成混乱）。选举采用类似 Raft 的「先到先得 + 任期（epoch）+ 多数派」机制：每个哨兵在发现自己可参与时递增 `leader_epoch` 并投票给自己，同时向其他哨兵拉票（`is-master-down-by-addr` 带 `leader` 标记）；先获得**多数派**（>N/2）投票的哨兵成为 leader。leader 选定新主时遵循规则：**slave-priority（replica-priority）最高优先 → 复制 offset 最大（数据最新）→ runid 字典序最小**。见 `examples/ex06_sentinel_raft_leader.json`、`ex07_failover_select_replica.json`。

### 🧑‍💻 程序员视角
- **`replica-priority` 的实战用法**：给「硬件差/想当备胎」的从节点设大 priority（如 100），给「强机器」设 0 或最小，让故障转移天然优先切到好机器；priority 相同的从节点才比 offset。
- **offset 最大 = 数据最新**：选主时优先选复制进度最靠前的从节点，最小化数据丢失；这也提示我们平时要让从节点尽量「跟得上」主节点（监控 lag）。
- **故障转移窗口要心里有数**：从 ODOWN 到真正切主完成，包含 leader 选举 + 选主 + 让其余从节点 `REPLICAOF` 新主 + 通知客户端，通常数秒到十几秒；这期间主节点不可写，应用要有重试/降级。
- **客户端必须接 Sentinel**：业务代码别直连写死的主节点 IP，要用 Sentinel 客户端（JedisSentinelPool 等）订阅 `+switch-master` 事件自动感知新主，否则故障转移后写请求打到旧主会失败。

### 🎓 博士生视角
- **为什么哨兵选举像 Raft 而非 Paxos**：哨兵只需在「要执行故障转移」这件事上达成一个 leader 共识，且强调「谁的 epoch 新、谁先拉到多数票谁当选」的单向收敛，避免活锁；用 `leader_epoch` 作为逻辑任期，旧任期选票作废，保证同一任期最多一个 leader。
- **多数派的必要性**：leader 必须拿到 >N/2 票，确保「不可能同时出现两个 leader 各自执行故障转移」（因为两个 leader 需要的总票数超过 N，而总票只有 N）。这与 SDOWN/ODOWN 的 quorum 解耦，是「执行权」而非「判定权」。
- **选主规则的函数式表达**：`best = argmin over replicas of (-priority, -offset, runid)`；priority 越小越优先，offset 越大越优先，runid 越小越优先——这是确定性的、可复现的总排序，避免两个哨兵选出不同新主。

### 📚 考研者视角（笔面考点）
- **标准问法**：「哨兵怎么选 leader？故障转移怎么选新主？」答：leader 选举用类 Raft 机制（epoch + 先到先得 + 多数派 >N/2 票当选）；选新主规则为 `replica-priority` 最小 → 复制 offset 最大 → runid 字典序最小。
- **必背结论**：ODOWN 只决定「要故障转移」，leader 选举决定「谁来做」，选主规则决定「选哪个从节点」；三者是不同步骤。
- **易错口径**：leader 选举的「多数派」是 >N/2，而 ODOWN 的 quorum 是独立配置、不要求多数派——两者常被混为一谈；选主优先级 priority 是「数值小优先」，offset 是「数值大优先」。
