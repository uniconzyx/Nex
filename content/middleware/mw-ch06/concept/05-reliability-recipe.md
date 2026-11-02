# 生产端可靠性实战：不丢、不重、有序

> 「`acks=all` 就等于不丢吗」「重复消费怎么防」「rebalance 为什么会把消费打断」——
> 这三个问题在生产事故里出现的频率最高。本节把 Kafka 生产端/消费端的**配置组合**
> 与**幂等实现**写成可以直接抄的配置与代码。

### 一、生产者配置：不丢的第一道闸

```yaml
# producer.properties —— 三件套缺一不可
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all                    # 等所有 ISR 副本写成功
enable.idempotence=true      # 开启幂等：重试不会产生重复记录
max.in.flight.requests.per.connection=5   # 幂等下最多允许 5 个在途请求
retries=2147483647          # 无限重试（由 delivery.timeout 控制总时长）
delivery.timeout.ms=120000  # 单次投递总超时
compression.type=zstd       # 批量压缩，磁盘与网络都省
linger.ms=10                 # 攒 10ms 换吞吐（延迟敏感场景调 0）
batch.size=65536
```

```text
可靠性三件套（broker 侧）：
  replication.factor = 3          # 三个副本
  min.insync.replicas = 2          # 至少两个 ISR 才算写成功
  unclean.leader.election.enable = false   # 落后副本不许当 leader
三者少一个，"不丢"就不成立。
```

### 二、幂等生产者：重试为什么不产生重复

```java
// 幂等由 broker 侧维护的 producerId + epoch 实现：同一事务内重试会被去重
Properties props = new Properties();
props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "broker1:9092");
props.put(ProducerConfig.ACKS_CONFIG, "all");
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, "5");
props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, "120000");

try (KafkaProducer<String, String> producer = new KafkaProducer<>(props)) {
    // key 决定分区：同 key 落同分区，才有"分区内有序"
    ProducerRecord<String, String> rec =
            new ProducerRecord<>("orders", order.getUserId(), mapper.writeValueAsString(order));
    producer.send(rec, (metadata, ex) -> {
        if (ex != null) {
            // 异步回调里做业务补偿，不要在这里吞异常
            log.error("send failed topic={} partition={}", rec.topic(), rec.partition(), ex);
            deadLetterQueue.save(rec.value(), ex);
        }
    });
    producer.flush();
}
```

### 三、消费端幂等：至少一次 + 去重表

```python
# 至少一次语义下，同一条消息会被投递多次；用业务唯一键 + 唯一索引去重
import sqlite3, json

conn = sqlite3.connect("app.db")
conn.execute("CREATE TABLE IF NOT EXISTS processed_orders (order_id TEXT PRIMARY KEY, done_at INTEGER)")
conn.commit()

def handle(msg):
    order = json.loads(msg.value)
    with conn:                      # 事务：去重判断与业务写入同一事务
        cur = conn.execute(
            "INSERT OR IGNORE INTO processed_orders(order_id, done_at) VALUES (?, strftime('%s','now'))",
            (order["id"],),
        )
        if cur.rowcount == 0:       # 已处理过，直接跳过（幂等成功）
            return
        apply_business_side_effect(order)   # 真正的副作用（发货/入账）

def on_message(consumer, msg):
    try:
        handle(msg)
        consumer.commit()           # 处理完再提交位移
    except Exception:
        log.exception("handle failed, will retry")
        raise                       # 不提交位移 → 重新投递，配合去重表
```

关键顺序：**先处理并落库，最后提交位移**。反过来（先提交后处理）会丢消息，
两头都做（先提交再处理 + 失败重试）会重复。

### 四、rebalance：消费被打断时在发生什么

```text
触发 rebalance 的四种情况：
1) 消费者加入/退出（扩缩容、滚动重启）
2) 分区数变化（给 topic 加分区）
3) 消费超时（max.poll.interval.ms 到了还没 poll）
4) 心跳丢失（session.timeout.ms 内没心跳）

Eager（默认 RangeAssignor）：
   撤销所有分区 → 重新分配 → 全部消费者重新加入
   → 期间该组所有分区都暂停消费
CooperativeSticky（推荐）：
   分批撤销/分配，未受影响的分区继续消费
   → 滚动升级要用 upgrade.from 过渡，不能直接改策略

配套参数：
  max.poll.interval.ms  要大于单批处理耗时（否则"活着但太慢"被踢出组）
  max.poll.records       一次拉多少条，调小可降低单次处理时长
  session.timeout.ms / heartbeat.interval.ms  心跳与超时
```

```python
# 消费者配置：把"活着但处理慢"这件事变成可观测的指标
consumer_config = {
    "bootstrap.servers": "broker1:9092",
    "group.id": "order-workers",
    "enable.auto.commit": False,          # 手动提交位移
    "auto.offset.reset": "earliest",       # 新组从最早开始（否则历史全跳过）
    "max.poll.records": 200,              # 单批别太大
    "max.poll.interval.ms": 300000,       # 5 分钟内必须 poll 一次
    "session.timeout.ms": 45000,
    "heartbeat.interval.ms": 15000,
    "partition.assignment.strategy": "org.apache.kafka.clients.consumer.CooperativeStickyAssignor",
}
```

### 五、上线前自检清单

```text
□ acks=all + min.insync.replicas=2 + replication.factor=3 都配了吗
□ unclean.leader.election 关闭了吗
□ 生产者 enable.idempotence=true 了吗（否则重试会写重复）
□ 消费端手动提交位移，且先处理后提交吗
□ 业务有唯一键 + 去重表吗（否则重复消费必然出事）
□ key 设计能保证需要的顺序粒度吗（同 key 才同分区）
□ max.poll.interval.ms 大于单批耗时 P99 吗
□ 监控：lag、producer error rate、rebalance 频次、DLQ 速率
```
