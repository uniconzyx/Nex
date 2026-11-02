# Redis 高可用实战手记：凯喵经历的一次主从切换灾难

> 这一章讲主从复制、哨兵、Cluster。概念都听过，但真到线上切换时，坑全在细节里：复制延迟、脑裂、哨兵选主失败、Cluster 的 slot 迁移卡住。这篇手记用十二个现场把「高可用三件套」的边界摸清。

## 开场：高可用不等于「不出故障」

很多人以为上了哨兵就「不会挂」。实际的高可用只保证一件事：**故障发生时，服务能在可接受的时间内自动恢复**。它不保证不丢数据、不保证不短暂不可用、更不保证不出错。

理解这一点之后，三个问题就变得关键：恢复需要多久（RTO）、会丢多少数据（RPO）、恢复过程中会不会出现双主（脑裂）。下面十二个现场按这三个问题组织。

### 现场一：主从复制的全量同步把主库打挂

第一次建立主从时，从库发 `PSYNC`，主库发现无法增量，就执行 `BGSAVE` 生成 RDB 全量传给从库。如果主库内存 20G、磁盘慢，`BGSAVE` 的 fork 会拷贝页表、写盘会占 IO，主库延迟瞬间飙升，甚至触发「fork 失败」。

关键参数与对策：

```text
repl-backlog-size     复制积压缓冲区大小（默认 1MB，生产建议 64MB~256MB）
repl-diskless-sync    yes 时不落盘，直接通过网络传 RDB（省磁盘 IO）
repl-diskless-sync-delay  延迟几秒再开始，让多个从库一起等，避免重复 fork
client-output-buffer-limit replica  从库缓冲区上限，超了会断开从库
```

凯喵的实践约定是：**新从库接入必须在低峰期，且一次只加一个**。同时主库要有 `maxmemory` 余量，保证 `BGSAVE` 期间 fork 的 copy-on-write 不会把内存撑爆。

### 现场二：复制延迟被忽略，读到旧数据

主从复制的传播是异步的：主库写入 → 写进 backlog → 异步发给从库。所以从库可能存在几百毫秒到几秒的延迟。

在「写后立刻读」的场景下，这会直接暴露为业务 bug：用户改了昵称，刷新页面还是旧的。

三种处理方式：

```python
# 方案一：关键读走主库（最简单）
def get_user(uid, need_fresh=False):
    conn = master if need_fresh else replica_pool.get()
    return conn.hgetall(f"user:{uid}")

# 方案二：用 WAIT 命令同步等待（Redis 3.0+）
master.set("k", "v")
replicas_acked = master.execute_command("WAIT", 1, 100)   # 等 1 个从库，超时 100ms
# 返回实际确认的从库数，小于期望就说明没等到

# 方案三：会话粘性 + 版本号校验
# 写操作返回新版本号，读时带上版本号，从库落后就重试或降级读主
```

凯喵的经验：**方案二最容易被忽略但最实用**——`WAIT` 只在需要的少数写路径上加，代价可控。但要注意 `WAIT` 只保证「数据已到达从库的内存」，不保证已落盘。

### 现场三：哨兵数量配成偶数，投票僵持

哨兵判定主库客观下线（`SDOWN` → `ODOWN`）需要**多数派**同意：`quorum` 个哨兵认为下线，且得到 `majority = N/2 + 1` 个哨兵授权才能执行故障转移。

3 个哨兵：需要 2 票，能容忍 1 个挂。4 个哨兵：需要 3 票（多数派 3），能容忍 1 个挂——**容错能力与 3 个相同，却多花一台机器**。所以哨兵数量必须是奇数，最少 3 个。

另一个高频错误是把哨兵和 Redis 部署在同一台机器上：

```text
错误：3 台机器，每台一个 Redis + 一个 Sentinel
→ 机器挂一台，同时丢一个 Redis 和一个 Sentinel，可能直接凑不够多数派

正确：3 台 Redis + 3 台（或 5 个分布在更多机器上的）Sentinel
```

### 现场四：脑裂——老主库没死，新主库已选出

网络分区时最危险的情况：哨兵连不上主库，判定其下线并选出新主；但老主库其实活着，客户端还在往它写。分区恢复后，老主库被降级为从库，**它上面那批写入被清空**。

这是 Redis 异步复制的固有问题，不能完全消除，只能降低损失：

```conf
# 主库侧：至少要有 N 个从库连接才允许写（降低孤立主库继续接受写的概率）
min-replicas-to-write 1
min-replicas-max-lag 10

# 哨兵侧：切换前多确认几轮，避免短暂抖动误判
sentinel down-after-milliseconds mymaster 30000
```

`min-replicas-to-write` 的含义是：如果健康从库少于 1 个、或延迟超过 10 秒，主库**拒绝写**。这会把「静默丢数据」变成「明确报错」，对业务更友好——因为报错能被监控发现，静默丢数据不能。

凯喵的结论：**宁可短暂不可写，也不要接受一个已经和数据流断开的主库继续接写**。

### 现场五：哨兵切换后客户端还连着老地址

哨兵做完故障转移，主库地址变了，但客户端连接池里还是旧地址，于是一直报 `READONLY You can't write against a read only replica`。

修法是客户端必须支持哨兵发现：

```python
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [("10.0.0.1", 26379), ("10.0.0.2", 26379), ("10.0.0.3", 26379)],
    socket_timeout=0.5,
)
master = sentinel.master_for("mymaster", socket_timeout=0.5, password="***")
replica = sentinel.slave_for("mymaster", socket_timeout=0.5, password="***")
# master_for 每次取连接前会向哨兵确认当前主库地址，切换后自动跟随
```

关键是**不要自己解析哨兵返回的地址后缓存起来**——那等于把动态发现退化成静态配置。如果确实要缓存，必须订阅哨兵的 `+switch-master` 事件来失效缓存。

### 现场六：只读从库被写入，因为客户端连错了

`READONLY` 报错的反面是：明明想连从库读，结果连到了主库，所有读压力压到主库上，主库 CPU 打满。

判断当前连的是谁：

```bash
redis-cli -h 10.0.0.5 -p 6379 info replication | head -5
# role:master  -> 这是主库
# role:slave + master_host:... -> 这是从库
```

还有一个隐蔽情况：**故障转移后原从库升主，配置里写的"从库地址"变成了主库**。此时所有标了「读从库」的流量都打到新主上。所以「按地址区分读写」是脆弱的，正确做法是按 `role` 区分（哨兵客户端的 `master_for`/`slave_for` 就是按角色而非地址）。

### 现场七：Cluster 的 slot 数量记错，key 落错节点

Redis Cluster 有 16384 个 slot，`slot = CRC16(key) % 16384`，每个节点负责一段。

两个高频错误：

```bash
# 错误一：以为 16384 是每个节点的 slot 数
# 实际是总数，3 主节点大致各分 ~5461 个

# 错误二：用 hash tag 想控制同节点，但写法不对
SET {user1000}.name "kaimao"     # OK：{} 内的内容参与哈希 -> 同节点
SET user{1000}.name "kaimao"     # 错：只有 {} 内的 1000 参与哈希，
                                 # 但 user 在前，实际 key 的哈希仍按 {1000}
```

hash tag 的规则是：**key 里第一对 `{}` 之间的内容**参与哈希计算。所以 `{user1000}.name` 和 `{user1000}.age` 一定同 slot，可以放心用 `MGET` 或事务。但要注意别让所有 key 都用同一个 tag——那会把整个集群退化成单节点。

### 现场八：Cluster 的跨 slot 操作直接报错

```bash
MGET {a}1 {b}1
# (error) CROSSSLOT Keys in request don't hash to the same slot
```

这是设计使然：Cluster 不做跨节点的多 key 聚合。三条出路：

```python
# 方案一：用 hash tag 让相关 key 同 slot（最优）
key_a = f"{{order:{oid}}}:items"
key_b = f"{{order:{oid}}}:total"      # 与上面同 slot，可 MGET

# 方案二：客户端侧拆分，逐个节点请求再合并
results = {k: client.get(k) for k in keys}    # 简单但 N 次 RTT

# 方案三：用一个 hash 存相关字段，天然同 slot
client.hset(f"order:{oid}", mapping={"items": ..., "total": ...})
```

凯喵的选型建议：**能用 hash 结构的别拆成多个 string key**，因为 hash 天然落在同一 slot，省掉所有跨 slot 问题。

### 现场九：Cluster 扩容时 slot 迁移把服务拖慢

加节点需要把一部分 slot 从老节点迁到新节点。迁移过程中 `MIGRATE` 会逐 key 搬运，如果 key 很多且大，会长时间占用 CPU 和网络。

正确的迁移节奏：

```bash
# 1. 先加空节点，让它加入集群（此时不持有 slot）
redis-cli --cluster add-node 10.0.0.9:6379 10.0.0.1:6379

# 2. 分批迁移 slot，每批少量，观察延迟
redis-cli --cluster reshard 10.0.0.1:6379 \
  --cluster-from <src-id> --cluster-to <dst-id> \
  --cluster-slots 500 --cluster-yes     # 一次只迁 500 个

# 3. 迁移期间监控
redis-cli --cluster check 10.0.0.1:6379
```

迁移中的 slot 处于 `MIGRATING`/`IMPORTING` 状态，客户端如果访问到「key 已迁走」的情况会收到 `ASK` 重定向，正常客户端会自动跟随。但如果客户端不支持 `ASK`（只支持 `MOVED`），迁移期间会报错——这是选客户端时容易被忽略的兼容性问题。

### 现场十：以为 Cluster 有强一致，实际会丢写

Cluster 的每个主节点也是异步复制到从库的。主节点挂掉、从库升主时，**没来得及同步的写就丢了**。

更麻烦的是 Cluster 的选主规则：从库需要获得**多数主节点**的投票才能升主。如果两个主节点同时挂、又正好分布在不同的少数派里，可能短时间没有可用主。

缓解手段：

```conf
# 主节点至少要有 1 个健康从库才接受写（同单机的 min-replicas 思路）
min-replicas-to-write 1
min-replicas-max-lag 10

# 关键写用 WAIT 等复制确认
WAIT 1 100
```

凯喵的结论：**Redis 的任何高可用方案都不提供强一致**。需要强一致的场景（比如扣库存的最终判断）必须回到数据库或引入额外的一致性协议，不能指望 Redis 复制。

### 现场十一：故障演练没做过，真出事时不知道谁在做什么

最贵的一条教训。上线前团队只做了「正常启动」测试，没做过「kill 主库」「断网分区」「同时挂两个节点」的演练。

结果真出事时，三个人同时在看日志、谁也不知道哨兵日志在哪、切换花了十二分钟（设计目标是 30 秒）。

故障演练的最小清单：

```text
1. kill -9 主库进程        → 验证哨兵切换耗时与客户端跟随
2. 断开主库网络（iptables）  → 验证脑裂防护是否生效（min-replicas）
3. 挂掉一个哨兵              → 验证剩余哨兵仍能形成多数派
4. 从库延迟 30 秒再切换      → 验证业务能接受多少数据丢失
5. Cluster 迁移中 kill 节点  → 验证 slot 状态能自愈
```

每一项都要记录：检测时间、判定时间、切换时间、客户端恢复时间。这四个数字合起来才是真实的 RTO。

### 现场十二：监控只盯「进程活着」，不看复制状态

「Redis 还在跑」不等于「服务可用」。必须监控的指标：

```bash
redis-cli info replication
# master_link_status:up        ← 从库与主库的连接状态（down 就是断链）
# master_last_io_seconds_ago   ← 距离上次收到主库数据多久（>10s 要告警）
# slave_repl_offset 与 master_repl_offset 的差值 ← 复制延迟（字节数）

redis-cli info stats | grep rejected_connections    # 连接被拒
redis-cli info memory | grep used_memory_human
```

凯喵的告警阈值建议：

```text
master_link_status == down                 → P1 立即
master_last_io_seconds_ago > 30            → P2
repl_offset 差值 > 10MB 且持续 1 分钟       → P2
哨兵 s_down / o_down 计数 > 0               → P1
Cluster cluster_state != ok                → P1
```

关键认知：**高可用方案的可靠性，取决于你能不能看见它正在失效**。看不见的降级，比直接崩溃更危险，因为它会让所有人在「系统正常」的错觉里继续运行。

## 收尾：凯喵的高可用三问

每次设计或复盘 Redis 高可用，先回答三个问题：

**恢复要多久（RTO）**——哨兵切换通常 10-30 秒，Cluster 类似；客户端是否自动跟随决定了业务实际感受。

**会丢多少（RPO）**——异步复制下，丢的是「主库已写、从库未收」的那部分，通常是几百毫秒到几秒的写入量；`min-replicas-to-write` 能把静默丢失变成显式失败。

**会不会双主**——依赖多数派投票 + `min-replicas` 限制写；分区恢复后必须确认老主已被降级且数据已重建。

最后说一句观念上的话。Redis 高可用的所有机制，本质上都在**异步复制的物理约束**下做权衡：想要低延迟就得接受可能丢数据，想要不丢数据就得上同步复制（性能暴跌）。没有免费的一致性。

所以真正的工程能力不体现在「配了哨兵」，而体现在**清楚地知道这套方案在什么情况下会失效、失效时业务会看到什么、以及怎么在五分钟内确认现状**。凯喵见过最稳的团队，不是用了最复杂方案的，而是把「演练过、有监控、有预案」这三件事做到位的——因为故障从来不会按文档发生，它只会按你没演练过的那个方向发生。
