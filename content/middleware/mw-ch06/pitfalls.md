# mw-ch06 · 陷阱清单：Kafka 生产消费最易错的十四件事

> 每一条都对应一个**线上真实会出事**的配置或写法。行首编号与门禁统计一致。

1. **`acks` 只在生产者设，忘了 `min.insync.replicas`** —— 只写 `acks=all` 而 `min.insync.replicas` 仍是默认 1 时，ISR 收缩到只剩 leader 后 `acks=all` **退化成 `acks=1`**，照样丢数据。正确做法：生产端 `acks=all` **必须**配 broker/Topic 端 `min.insync.replicas ≥ 2`（3 副本场景）。

2. **`enable.auto.commit=true` 却不处理业务失败** —— 自动提交在 `poll()` 时提交**上一批**的位移，与业务处理结果无关。处理到一半崩溃 → 这批消息**永久丢失**且无任何日志。正确做法：生产环境设 `enable.auto.commit=false`，处理成功后手动提交。

3. **`commitSync()` 写在业务处理之前** —— 这是**主动选择 at-most-once**。一旦处理抛异常，位移已经前进，消息再也回不来。正确顺序：**先处理、成功后再提交**（at-least-once），重复由业务幂等消化。

4. **以为 `enable.idempotence=true` 能防止消费者重复** —— 幂等生产者是**生产端**的去重（PID + 分区 + 序列号），与消费者的重复消费**毫无关系**。防重复消费只能靠业务幂等。

5. **以为 `acks=all` 就等于"写入所有副本"** —— 它等于「写入**当前 ISR 中的全部副本**」。ISR 会因副本落后而收缩，所以它**不是**「写入全部 `replication.factor` 个副本」。

6. **消费者数超过分区数还继续加机器** —— 并行度上限是 `min(消费者数, 分区数)`，多出来的消费者**永远空闲**（仍在组内、仍发心跳，但拿不到分区）。提吞吐要么加分区（破坏 key 映射，需谨慎），要么优化单条处理耗时。

7. **`max.poll.interval.ms` 当成网络超时** —— 它管的是**两次 `poll()` 之间的业务处理时长**（默认 5 分钟）。心跳由后台线程正常发送也救不了：一次 `poll()` 返回的批次处理超过 5 分钟，消费者照样被踢出组并触发 rebalance。

8. **`session.timeout.ms` 调得过小** —— 网络抖动（GC 停顿、跨机房抖动）就会导致心跳超时 → 被踢 → rebalance → **重复消费 + 消费停摆**。约束是 `heartbeat.interval.ms < session.timeout.ms / 3`。

9. **只用 key 保证有序，忽略 `max.in.flight.requests.per.connection`** —— 同分区内，若 `in.flight > 1` 且关闭幂等，**重试会导致乱序**（第 2 批重试成功可能晚于第 3 批到达）。正确组合：**同 key + `enable.idempotence=true`（会自动把 in.flight 限制到 5）+ `max.in.flight ≤ 5`**。

10. **把「消息 ID」当作有序 key** —— 每条消息 ID 都不同，`murmur2(key) % N` 会把它们散到不同分区，**完全失去有序性**。有序 key 必须是**业务上需要保序的维度**（订单号、用户 ID、设备 ID）。

11. **用 `hashCode()` 预计算分区号** —— Kafka 用的是自实现的 **murmur2**，与 `java.util.HashMap` 的扰动函数不同。用 `hashCode()` 手动指定的分区与 broker 端的分区器**不一致**，会破坏「同 key 同分区」。

12. **给无 key 的消息填一个随机 key** —— 看似"分布均匀"，实则破坏**粘性分区**的攒批效果（每条消息换分区 → batch 永远装不满），吞吐显著下降，且分布方差反而更大。无 key 时就让 key 为 `null`。

13. **从 Eager 策略直接切到 `CooperativeStickyAssignor`** —— 直接改 `partition.assignment.strategy` 会导致消费者之间协议不一致，陷入**反复 rebalance**。必须用 `upgrade.from` 走一次滚动升级。

14. **`auto.offset.reset=latest` 配 `enable.auto.commit=false` 的新组首次启动** —— 新消费者组（`__consumer_offsets` 无记录）会从 `latest` 开始，**历史消息全部跳过**。要么用 `earliest`，要么在启动前确认组内已有有效位移。
