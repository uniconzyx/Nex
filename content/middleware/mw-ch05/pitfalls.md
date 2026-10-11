# mw-ch05 · 陷阱清单：Kafka 最容易错的十五件事

1. **把 Kafka 当传统队列，以为「消费即删除」** —— Kafka 的消息**与消费进度无关**，只按 `retention.ms`/`retention.bytes` 或 `compact` 清理。所以同一个 topic 可以被多个消费者组**各自完整消费**（这就是可重放能力）。**正确认识**：Kafka 是「可重放的分布式日志」，不是「取出即销毁的队列」。

2. **以为分区数可以随便增减** —— 分区**只能增加，不能减少**（减少会导致数据丢失与位点错乱，Kafka 不直接支持）。更关键的是：增加分区会改变 `hash(key) % N` 的落点，**破坏跨分区的顺序连续性**。**正确做法**：上线前按 `max(目标吞吐/单分区吞吐, 消费者数, broker 数)` 规划到位并留余量。

3. **认为「分区越多吞吐越高」** —— 分区数增加会带来：每分区独立的 `.log/.index/.timeindex` 文件句柄、ISR 维护心跳、rebalance 与故障恢复时间上升。**正确认识**：存在边际收益递减的最优点；分区数超过消费者数就是纯浪费（多余消费者空闲）。

4. **只配 `acks=all` 就以为不丢消息** —— 若 ISR 收缩到只剩 Leader，`acks=all` 等价于 `acks=1`。**必须同时配** `min.insync.replicas=2`（ISR 不足时**拒绝写入**）+ `replication.factor=3`，才是真正的不丢条件。

5. **把「有序」理解成全局有序** —— Kafka **只保证单分区内有序**。全局有序只能用一个分区（牺牲全部并行度）。**正确表述**：先明确「顺序的边界是分区」，再用分区键把需要保序的实体（如同一订单 id）路由到同一分区，并注意 `max.in.flight.requests.per.connection > 1` 时需开启幂等才能避免重试乱序。

6. **消费者数超过分区数，以为能提速** —— 组内同一分区只能被一个消费者消费，因此**有效并行度 = min(消费者数, 分区数)**。多出来的消费者**完全空闲**。**正确做法**：先把分区数提上去（或按分区数规划消费者实例数），再谈扩容。

7. **用默认的自动提交位点，却期望「处理完才算消费成功」** —— `enable.auto.commit=true` 提交的是 `position`（poll 到的位置）而非处理完成的位置，**默认配置等价于 at-most-once**，处理中崩溃即丢消息。**正确做法**：`enable.auto.commit=false`，**处理完成后手动提交**。

8. **以为「先处理再提交」就不会重复** —— 先处理再提交是 **at-least-once**，rebalance 或提交失败都会导致重复消费。**正确做法**：消费端必须**幂等**（唯一键、去重表、upsert），或在上游保证「同 key 同分区」后用状态去重。

9. **以为跨系统也能做 exactly-once** —— Kafka 事务（`sendOffsetsToTransaction`）只能让「写 Kafka + 提交位点」原子化。**下游是 MySQL/Redis 时 Kafka 的事务管不到**，只能退化为 at-least-once + 应用层幂等。**正确认识**：exactly-once 只在同一事务域内成立。

10. **开启 `unclean.leader.election.enable=true` 却不理解代价** —— 该选项允许**非 ISR 副本**（含落后很多的副本）当选 Leader，以「可用性优先」换「数据可能回滚丢失」。**正确做法**：默认保持 `false`；只有在「可接受丢数据、不可接受不可用」的场景才开启。

11. **把 `retention.ms` 当成「消息精确存活时长」** —— Kafka 的删除粒度是 **segment**：只有当**段内所有消息都超期**时整段才删。若段没写满（`log.segment.bytes` 默认 1GB），消息可能比 `retention.ms` 活得更久。**正确做法**：按「写入速率 × 保留时长」估算合适的段大小，并同时配置 `retention.bytes` 兜底防磁盘写满。

12. **用 `compact` 策略做消息去重** —— 压实是**异步、有延迟**的，中间状态仍可能读到多条同 key 记录。**正确做法**：去重必须放在消费端（幂等），`compact` 只适合「每 key 保留最新值」的状态快照语义（如 `__consumer_offsets`）。

13. **把 `session.timeout.ms` 与 `max.poll.interval.ms` 混为一谈** ——前者管「心跳是否收到」（后台线程发），后者管「两次 `poll()` 的间隔」（由业务处理速度决定）。**`max.poll.interval.ms` 超时是 rebalance 最常见的根因**。**正确做法**：缩小 `max.poll.records` 或异步化处理逻辑，让单批处理时间远小于该阈值。

14. **滚动重启引发全组 rebalance 雪崩** —— 每重启一个消费者都会触发一次 Eager rebalance，重启 10 个就 rebalance 10 次，期间消费反复停摆。**正确做法**：给消费者配 **`group.instance.id`（静态成员）**，或升级到 **CooperativeSticky** 增量协议。

15. **`replication.factor=1` 却以为有容错** —— 单副本时任何一台 broker 重启/磁盘故障都会导致该分区不可用（无副本可选举）。**正确做法**：生产环境至少 `replication.factor=3`，并置于不同机架（`broker.rack`）。
