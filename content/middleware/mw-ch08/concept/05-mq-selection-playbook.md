# 选型与运维实战：把 MQ 选型落成可执行的清单

> 选型讨论最容易变成"背产品特性"。这一节反过来：先用一张表把**决策维度**固定，
> 再用两段代码把两种典型语义（**逐条 ack** 与 **按 offset 消费**）写出来，
> 最后给出容量、降级与排障的最小清单。

### 一、先看决策维度，再看产品

```text
┌──────────────┬────────────────────────┬────────────────────────┐
│ 维度          │ RabbitMQ               │ Kafka                  │
├──────────────┼────────────────────────┼────────────────────────┤
│ 投递语义      │ 逐条 ack/nack，可重投    │ 按 offset 提交，批量确认 │
│ 路由能力      │ 交换机/队列/主题灵活      │ 只能按分区消费，路由弱   │
│ 单条延迟      │ 毫秒级（低吞吐时更优）    │ 毫秒~十毫秒（批量更大） │
│ 峰值吞吐      │ 万级/秒（多实例可堆）     │ 百万级/秒              │
│ 顺序保证      │ 队列内 FIFO            │ 分区内有序（全局无序）   │
│ 回放/重算     │ 需自己留队列            │ 换 offset 重放，天然支持 │
│ 延迟队列      │ 插件原生支持            │ 需自己搭多级 topic       │
│ 运维成本      │ 管理台友好，参数少       │ 调优项多（JVM/ISR/分区） │
└──────────────┴────────────────────────┴────────────────────────┘
结论：**"一条消息要送达才算数" → RabbitMQ；"高吞吐日志流 + 回放" → Kafka。**
```

### 二、逐条 ack 的语义（RabbitMQ 风格）

```python
# 逐条确认：处理成功才 ack；失败 nack(requeue=True) 回到队列，失败次数超限进死信
import json, time
from collections import defaultdict

MAX_RETRY = 3
attempts = defaultdict(int)

def handle(channel, delivery):
    body = json.loads(delivery.body)
    try:
        do_business(body)                    # 真正的业务处理
    except Exception as e:
        attempts[delivery.message_id] += 1
        if attempts[delivery.message_id] >= MAX_RETRY:
            channel.basic_publish(
                exchange="", routing_key="dlq.order",   # 死信队列
                body=delivery.body,
                properties={"headers": {"error": str(e), "retry": attempts[delivery.message_id]}},
            )
            channel.basic_ack(delivery.delivery_tag)      # 已进死信，确认掉，别无限重投
        else:
            time.sleep(2 ** attempts[delivery.message_id])  # 退避，避免重试风暴
            channel.basic_nack(delivery.delivery_tag, requeue=True)
        return
    channel.basic_ack(delivery.delivery_tag)
```

注意最后那句 `basic_ack`：**进了死信也要 ack**，否则原队列的消息会一直重投，形成毒丸（poison pill）。

### 三、按 offset 消费的语义（Kafka 风格）

```python
# 手动提交位移：处理完这一批再提交 offset，保证"至少一次"
import json, time

def poll_loop(consumer, batch_size=500, poll_timeout_ms=1000):
    while True:
        records = consumer.poll(timeout_ms=poll_timeout_ms, max_records=batch_size)
        if not records:
            continue
        processed = []
        for tp, msgs in records.items():
            for m in msgs:
                try:
                    do_business(json.loads(m.value))
                    processed.append((tp, m.offset))
                except Exception:
                    log.error("fail at %s-%s, 交给死信 topic", tp, m.offset)
                    send_to_dlq(m)
                    processed.append((tp, m.offset))   # 失败也推进位，靠 DLQ 兜底
        # 只提交连续处理成功的那一段，避免跳过失败消息
        consumer.commit(offsets=processed)
```

若要"恰好一次"，改用 Kafka 事务（`transactional.id` + `send_offsets_to_transaction`），
把"写下游数据库"与"提交位移"放进同一个事务边界。

### 四、容量与降级清单（按顺序过）

```yaml
# 1) 容量：按峰值算，并留故障余量
capacity:
  peak_msgs_per_sec: 20000
  target_utilization: 0.65          # 稳态利用率不超过 0.65
  n_minus_1_capacity_check: true    # 挂掉一个分区/节点后仍能扛住峰值
  avg_msg_bytes: 1024
  retention: 7d

# 2) 降级顺序（先牺牲什么）
degradation:
  - step: reduce_consumer_concurrency   # 先降并发
  - step: pause_noncritical_consumers  # 再停非关键消费
  - step: switch_to_batch_processing    # 再转批处理
  - step: shed_load                     # 最后才丢弃/降级非关键流量

# 3) 告警阈值
alerts:
  consumer_lag_p95: 100000
  producer_error_rate: 0.01
  dlq_rate: 0.001
  rebalance_rate_per_hour: 3
```

```text
排障三问：
1) 消息去哪了？   → 看 DLQ 速率与失败原因分布（多半是反序列化/下游超时）
2) 消费慢在哪？   → 看单条处理耗时 P99（不是平均值）与 GC/连接池等待
3) 会不会重复？   → 看位移提交方式 + 下游是否幂等（没有幂等 = 迟早重复）
```
