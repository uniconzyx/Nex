# -*- coding: utf-8 -*-
"""来源颗粒度 · middleware 8 章。

四个仓库的角色分工：
  redis/redis         —— 直接读 C 源码，用来「验证机制到底怎么实现」
  apache/kafka        —— 读 Java/Scala 源码，看「语义落在哪个类」
  Snailclimb/JavaGuide —— 校准面试口径
  doocs/advanced-java  —— 看「这个点会被追问到多深」
"""
import sys

from _route_granularity import apply

GUI = 'Snailclimb/JavaGuide'
ADV = 'doocs/advanced-java'
REDIS = 'redis/redis'
KAFKA = 'apache/kafka'

DATA = {
    'mw-ch01': {
        REDIS: ('§1.1', '讲「为什么不用 C 字符串」时读 `src/sds.c`：`sdsnewlen` 按长度分 sdshdr5/8/16/32/64 五种头部、`len`/`alloc` 两个字段让取长度变成 O(1)、`sdscatlen` 按需预分配——三处细节合起来就是「二进制安全 + 免 strlen」的完整答案'),
        KAFKA: ('§3.2', '讲「编码转换的触发条件」时对照 `clients/src/main/java/org/apache/kafka/common/utils/` 下的集合实现：Kafka 用自定义 `Bytes`/`ByteBuffer` 包装避免装箱，与 Redis「小对象用紧凑编码」是同一种「按规模选表示」的思路'),
        GUI: ('§1.3', '讲「string 的三种编码」时读 `docs/database/redis/` 的底层数据结构篇：`int`/`embstr`/`raw` 的分界点是 44 字节，embstr 与 redisObject 一次分配、raw 两次——这解释了「45 字节的 key 比 44 字节多一次内存分配」'),
        ADV: ('§4.1', '讲「渐进式 rehash」时对照 `docs/high-concurrency/` 的 Redis 系列：`ht[0]`/`ht[1]` 双表 + `rehashidx` 游标 + 每次操作搬一个桶，把 O(n) 的扩容摊到多次操作上，这是「不阻塞单线程」的关键设计'),
    },
    'mw-ch02': {
        REDIS: ('§1.1', '讲「RDB 与 fork + COW」时读 `src/rdb.c` 的 `rdbSaveBackground`：`fork()` 之后子进程持有快照视图，父进程写入触发缺页复制——「fork 瞬间内存翻倍」不是估算，而是 COW 的必然代价'),
        KAFKA: ('§2.2', '讲「AOF 与预写日志」时对照 `core/src/main/scala/kafka/log/Log.scala`：Kafka 用「追加日志 + 段文件」实现持久化，与 AOF 的 append-only 同源，区别在于 Kafka 靠「保留策略」删除旧段而不是重写'),
        GUI: ('§2.2', '讲「AOF 重写」时读 `docs/database/redis/` 的持久化篇：重写不是读旧 AOF，而是「按当前内存状态生成最小命令集」，因此重写后的文件与历史无关——这也解释了混合持久化为什么能兼顾恢复速度与安全性'),
        ADV: ('§3.1', '讲「过期键删除与淘汰」时对照 `docs/high-concurrency/` 的 Redis 内存篇：惰性删除 + 定期删除两条腿走路，`maxmemory-policy` 的八种策略里 `allkeys-lru` 与 `volatile-lru` 的差别是「要不要保护无 TTL 的键」'),
    },
    'mw-ch03': {
        REDIS: ('§1.1', '讲「全量同步 PSYNC」时读 `src/replication.c`：`repl_backlog` 环形缓冲区 + `master_repl_offset` 让「断线重连只补差额」成为可能，缓冲区太小就只能退回全量同步——这是「主从频繁全量」的第一排查点'),
        KAFKA: ('§2.2', '讲「选主与多数派」时对照 `core/src/main/scala/kafka/controller/` 的选举逻辑：Kafka 用 Controller + ZK/KRaft 选 leader，Redis Sentinel 用 Raft 式投票，两者的共同前提都是「多数派还活着」'),
        GUI: ('§2.1', '讲「哨兵的主观/客观下线」时读 `docs/database/redis/` 的高可用篇：单个哨兵判 SDOWN 只是「我觉得」，凑够 quorum 才升 ODOWN，`majority` 与 `quorum` 是两个不同的数——配错就会「以为三个哨兵就安全」'),
        ADV: ('§3.2', '讲「脑裂与 min-replicas-to-write」时对照 `docs/high-concurrency/` 的 Redis 集群文章：老主库网络分区后仍接受写入，恢复时这部分数据被覆盖，`min-replicas-to-write` 用「写成功必须至少 N 个从库确认」把风险压到配置层面'),
    },
    'mw-ch04': {
        REDIS: ('§3.1', '讲「过期与淘汰的边界」时读 `src/expire.c` 与 `src/evict.c`：过期键是「到点删除」，淘汰是「内存满了赶人」，两套逻辑独立；`volatile-*` 策略只对设了 TTL 的键生效，全都没 TTL 时它会退化成「不淘汰、直接报错」'),
        KAFKA: ('§2.1', '讲「缓存穿透的兜底」时对照 `core/src/main/scala/kafka/log/Log.scala` 的「读不存在返回空」：存储层对「查不到」与「出错」必须区分，否则缓存层会把「暂时查不到」也缓存成空值，把一次抖动放大成一片空白'),
        GUI: ('§1.1', '讲「缓存穿透/击穿/雪崩」时读 `docs/database/redis/` 的缓存专题：三者的触发条件不同（不存在 / 热点失效 / 批量同时失效），解法也不同（空值缓存+布隆 / 互斥重建 / TTL 抖动），混着答是面试扣分点'),
        ADV: ('§4.2', '讲「先更库再删缓存」时对照 `docs/high-concurrency/` 的缓存一致性文章：并发下「读请求把旧值写回缓存」的窗口无法完全消除，延迟双删只能降低概率，强一致必须加锁或串行化'),
    },
    'mw-ch05': {
        KAFKA: ('§1.2', '讲「从队列到分布式提交日志」时读 `core/src/main/scala/kafka/log/Log.scala`：每个分区就是一个 append-only 的段文件序列，消费位点只是「读到哪个 offset」，所以消息可以被多个消费者组各自重放——这是「日志」与「队列」的本质差别'),
        REDIS: ('§3.2', '讲「零拷贝」时对照 `src/networking.c` 的 `writev`/`sendfile` 用法：Redis 与 Kafka 都靠「不让数据经过用户态」省掉两次拷贝，区别在于 Kafka 还叠加了页缓存与批量发送'),
        GUI: ('§2.2', '讲「ISR 与 acks」时读 `docs/database/kafka/` 的副本篇：`acks=all` 只是「等 ISR 全部确认」，还要配 `min.insync.replicas` 才有意义——只设前者，ISR 缩到一个副本时等于 `acks=1`'),
        ADV: ('§4.1', '讲「消费者组与 rebalance」时对照 `docs/high-concurrency/` 的消息队列文章：rebalance 期间全组停止消费，`session.timeout.ms` 与 `max.poll.interval.ms` 配小了会「反复踢人」，这是「消费明明没挂却一直 rebalance」的根因'),
    },
    'mw-ch06': {
        KAFKA: ('§1.3', '讲「从 send() 到 Broker」时读 `clients/src/main/java/org/apache/kafka/clients/producer/KafkaProducer.java` 与 `internals/Sender.java`：消息先进 `RecordAccumulator` 按分区攒批，Sender 线程按 broker 聚合请求——「batch.size 与 linger.ms 决定吞吐」就发生在这两层'),
        REDIS: ('§2.3', '讲「幂等与去重」时对照 `src/db.c` 的 `setKey` 覆盖语义：Redis 的写是「后写覆盖」，天然不产生重复，而消息队列必须自己实现「重复消息只生效一次」——这就是为什么消费端幂等不能指望中间件'),
        GUI: ('§2.2', '讲「幂等生产者」时读 `docs/database/kafka/` 的生产者篇：PID + 序列号让 broker 能识别「同一会话内的重试」，但它只管单分区单会话，跨会话仍会重复，所以业务幂等仍不可省'),
        ADV: ('§4.1', '讲「位移提交的四种方式」时对照 `docs/high-concurrency/` 的 Kafka 消费篇：自动提交是「按时间」、手动提交是「按处理进度」，前者在 rebalance 时会重复消费一批——「至少一次」的重复量级就由这个选择决定'),
    },
    'mw-ch07': {
        KAFKA: ('§2.1', '讲「重复从哪里来」时读 `internals/Sender.java` 的重试分支：网络超时后重发、但 broker 其实已写入，这是「生产者侧重复」的典型来源；`enable.idempotence=true` 用序列号把这类重复挡在 broker 侧'),
        REDIS: ('§1.2', '讲「存储端不丢」时对照 `src/rdb.c` 与 `src/aof.c` 的落盘时机：Redis 的 `appendfsync everysec` 最多丢 1 秒，Kafka 的 `acks=all` 不丢已确认消息——「不丢」的强度取决于「什么时候算成功」'),
        GUI: ('§3.1', '讲「三种顺序」时读 `docs/database/kafka/` 的顺序篇：分区内有序、分区之间无序、跨 topic 更无序，所谓「保证顺序」永远要附加「在哪个范围内」这个限定语'),
        ADV: ('§4.2', '讲「事务消息」时对照 `docs/high-concurrency/` 的分布式事务文章：Kafka 事务只保证「多条消息原子写入 + 消费端读已提交」，它不保证「业务操作与发消息」的原子性，后者要靠本地消息表或 Outbox'),
    },
    'mw-ch08': {
        KAFKA: ('§3.1', '讲「积压的数学」时读 `core/src/main/scala/kafka/log/Log.scala` 的分区模型：单个分区只能被一个消费者消费，所以「加消费者」的上限就是分区数——积压时先扩分区再扩实例，顺序反了就白扩'),
        REDIS: ('§1.3', '讲「什么时候用 Redis Stream 而不是 MQ」时对照 `src/t_stream.c`：Stream 有消费组与 ACK，但没有分区与副本，「轻量队列」够用；一旦要「百万级积压 + 多副本」，就超出它的设计边界'),
        GUI: ('§1.1', '讲「MQ 的三大价值」时读 `docs/database/kafka/` 的入门篇：削峰、解耦、异步——三者都成立的前提是「允许最终一致」，如果业务要求强一致，引入 MQ 只会把问题变成「分布式事务」'),
        ADV: ('§2.2', '讲「选型矩阵」时对照 `docs/high-concurrency/` 的消息队列对比文章：吞吐（Kafka/RocketMQ 高）、路由灵活度（RabbitMQ 强）、事务与延迟消息（RocketMQ 有）——先过硬约束再加权打分，不要一上来比 benchmark'),
    },
}

if __name__ == '__main__':
    sys.exit(apply('middleware', DATA))
