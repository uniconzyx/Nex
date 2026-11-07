# §4 mw-ch02 实战手记：凯喵带你把 Redis 用「崩」

> 前三节把 RDB fork-COW、AOF appendfsync、过期与淘汰讲透了。这一节凯喵把 Redis 最容易「内存爆 / 阻塞 / 丢数据」的 12 个现场搬出来——每个都是半夜告警的元凶。

### 现场一：忽略 RDB fork 的 COW 放大，被 OOM kill

凯喵在主库跑 `bgsave`，期间大量写入触发 copy-on-write 复制页，RSS 接近翻倍，撞上容器内存上限被 OOM kill，恢复又要重放 AOF。解法：单实例内存控在物理内存一半内；关 THP（`transparent_hugepage=never`）；快照错峰；用副本执行持久化，主库只保 `everysec`。

```bash
# 关掉透明大页，减小 fork 时 COW 页大小
echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

### 现场二：AOF 用 always 把吞吐打到地板

凯喵为「绝不丢数据」把 `appendfsync always`，每条写都 fsync，QPS 从 10 万掉到几千。`always` 每条刷盘，`everysec` 每秒一批，折中且最多丢 1 秒。绝大多数场景用 `everysec`。

```conf
# redis.conf
appendonly yes
appendfsync everysec   # ✅ 每秒 fsync，最多丢 1s，吞吐可接受
# appendfsync always  # ❌ 每条刷盘，性能灾难
```

### 现场三：bigkey 一把删，主线程卡死

凯喵 `DEL` 一个 500 万字段的 hash，主线程阻塞好几秒，所有请求超时。大 key 的删除/遍历要分批：`UNLINK`（异步惰性删）或 `HSCAN` 分批清，别一把梭。

```bash
# ✅ 异步删除，不阻塞主线程
UNLINK big_hash
# 遍历大 key 分批处理
HSCAN big_hash 0 COUNT 1000
```

### 现场四：热点 key 打爆单线程，CPU 100%

凯喵某个 key 被疯狂访问，Redis 单线程处理不过来，整体变慢。热点 key 要：本地缓存挡一层、key 加随机后缀分片、或读多写少场景上从节点分担读。

```java
// 热点 key 加随机后缀拆成多个，分散单线程压力
String k = "hot:" + (threadId % 10);
```

### 现场五：内存淘汰策略配错，该清的没清

凯喵设了 `maxmemory` 却用默认 `noeviction`，内存满了写请求直接报错而不是淘汰。按业务选策略：缓存用 `allkeys-lru`，保留 TTL 语义用 `volatile-lru`。

```conf
maxmemory 4gb
maxmemory-policy allkeys-lru   # ✅ 内存满按 LRU 淘汰
# noeviction                   # ❌ 满了直接拒绝写入
```

### 现场六：过期键没及时删，内存悄悄涨

凯喵以为设了 TTL 就万事大吉，结果大量 key 集中过期时 Redis 才被动清理，内存短时涨、访问时卡。主动过期有定时+惰性两种，集中过期会阻塞；用**随机过期时间打散**（TTL + 随机抖动）。

```bash
# ❌ 几百万 key 同一秒过期，集中清理阻塞
EXPIRE k 3600
# ✅ 加随机抖动打散
EXPIRE k 3600 + rand(0, 600)
```

### 现场七：把 Redis 当持久数据库，重启数据没了

凯喵把订单状态只放 Redis 不设持久化，主节点故障切换后数据全丢。Redis 是缓存/存储但**默认 RDB 是周期快照**，可能丢间隔内数据。重要数据双写数据库，或开 AOF+副本。

```conf
# 重要数据至少开 AOF，并配副本
appendonly yes
# 另加从节点，主挂从接
replicaof <masterip> <masterport>
```

### 现场八：keys * 在生产环境一键卡死

凯喵为查 key 在线上跑 `KEYS *`，几百万 key 一次性遍历，主线程卡几十秒。生产一律用 `SCAN` 游标迭代，分批返回，不阻塞。

```bash
# ✅ 分批游标，安全
SCAN 0 MATCH "order:*" COUNT 1000
# ❌ KEYS * 全量遍历，生产禁用
```

### 现场九：Pipeline 没用，网络往返把延迟堆高

凯喵循环发 1000 条命令，每条等回包，延迟 ×1000。多条命令打包用 **Pipeline** 一次网络往返，吞吐翻几十倍；需要原子性用 `MULTI/EXEC` 事务。

```java
// ✅ Pipeline 合并往返
Pipeline p = jedis.pipelined();
for (String k : keys) p.get(k);
p.sync();
```

### 现场十：Hash 的 field 过多变成 bigkey

凯喵把「全站用户在线状态」塞进一个 hash 的几百万 field，单 key 巨大，迁移/删除都卡。超大集合要**按业务分片**成多个 key（如 `online:{shard}`），控制单 key 规模。

```bash
# ❌ 一个 hash 装百万 field
HSET online_all user1 1
# ✅ 按分片拆
HSET online:0 user1 1   # 按 hash(uid)%N 分片
```

### 现场十一：Lua 脚本太长，阻塞且无法迁移

凯喵写了个百行 Lua 脚本做复杂事务，执行期间主线程全卡，集群迁移也因脚本无法跨 slot 失败。Lua 脚本要**短平快**、只操作同 slot 的 key，复杂逻辑放到客户端。

```lua
-- ✅ 短脚本，同 slot
redis.call("SET", KEYS[1], ARGV[1])
redis.call("EXPIRE", KEYS[1], ARGV[2])
```

### 现场十二：maxmemory 不设，机器内存被打满

凯喵的 Redis 没配 `maxmemory`，缓存越涨越多直到 OS 杀进程。Redis 不背「内存上限」的责任，必须显式设 `maxmemory` + 淘汰策略，否则迟早 OOM。

```conf
maxmemory 8gb
maxmemory-policy volatile-ttl   # 优先淘汰快过期的
```

> 凯喵总结：Redis 的坑九成在「内存」「阻塞」「丢数据」。记住 bigkey 异步删、everysec 够用、SCAN 替 KEYS、maxmemory 必配。把这 12 个现场刻进运维手册，半夜少接告警。

### 现场之外：凯喵的 Redis 三道防线
线上用 Redis，凯喵给自己立了三道防线。第一道是容量线：任何单实例内存都不许超过物理内存一半，fork 时的 COW 放大和 AOF 重写都要预留空间，绝不赌它不触发。第二道是慢操作线：禁止 KEYS、禁止一把 DEL 大 key、禁止超长 Lua，凡是可能阻塞主线程的操作一律改异步或分批。第三道是持久化线：缓存能丢的才纯内存，订单状态这类重要数据必须双写数据库或开 AOF 加副本。三道防线守住，Redis 基本不会成为半夜把你叫醒的那个组件。

### 现场拾遗：监控与容量才是最后的保险
最后凯喵强调，光靠编码规范还不够，Redis 必须配监控。内存使用率、命中率、fork 耗时、慢查询日志这几个指标要进告警面板，容量到七成就要扩容或清理。很多事故不是代码写错，而是没人发现内存曲线悄悄爬到上限。把容量和延迟当成一等公民来盯，比背一百条避坑清单都管用。

### 一句话收尾
凯喵最后提醒：Redis 再快也只是内存里的键值库，它解决的是「快」而不是「可靠」。任何你承受不起丢失的数据，都不该只活在 Redis 里。把它的角色摆正——缓存加速可以，做唯一真相源不行——这才是所有避坑清单背后真正要懂的那一句话。

## 三视角解析
### 🧑‍💻 程序员视角
RDB 的 `fork` 在写时复制下会放大内存：主库写入频繁时，被修改的页要复制一份，峰值内存可能是两倍——在内存吃紧的机器上做 `bgsave` 直接把实例打挂。AOF 用 `always` 每条命令都 `fsync`，吞吐掉到几百 QPS，生产一般用 `everysec`。`DEL` 一个几百万字段的 bigkey 会阻塞主线程几秒，必须用 `UNLINK`（异步回收）或 `SCAN` 分批删。热点 key 打爆单线程更是常见：Redis 单线程处理命令，一个 key 的 QPS 上限就是整个实例的上限。

### 🎓 博士生视角
Redis 的单线程指的是「命令执行单线程」，网络 IO 在 6.0 后可以多线程。这一设计把「并发安全」问题消掉，代价是「任何慢命令都会阻塞所有人」——所以 `KEYS *`、大 `DEL`、复杂 `ZRANGE` 都是生产禁忌。持久化的两难是「性能 vs 数据安全」：RDB 快但可能丢分钟级数据，AOF 全但慢、文件大。混合持久化（AOF 重写时前半段用 RDB 格式）试图兼顾，但仍需按业务 RPO 选择。

### 📚 考研者视角
后端面试高频：
1. **持久化对比**：RDB（快照、体积小、恢复快、可能丢数据）vs AOF（日志、更安全、体积大、恢复慢）。
2. **单线程为什么快**：纯内存、IO 多路复用、避免锁与上下文切换。
3. **bigkey 与 hotkey**：识别方法（`--bigkeys`、`--hotkeys`）、治理手段（拆分、异步删除、本地缓存）。
4. **内存淘汰**：`maxmemory-policy` 的八种策略与 LRU/LFU 的实现差异（近似算法 + 采样）。

```text
04-redis-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：忽略 RDB fork 的 COW 放大，被 OOM kill  (bash)
    |
    v
  [02] 现场二：AOF 用 always 把吞吐打到地板  (conf)
    |
    v
  [03] 现场三：bigkey 一把删，主线程卡死  (bash)
    |
    v
  [04] 现场四：热点 key 打爆单线程，CPU 100%  (java)
    |
    v
  [05] 现场五：内存淘汰策略配错，该清的没清  (conf)
    |
    v
  [06] 现场六：过期键没及时删，内存悄悄涨  (bash)
    |
    v
  [07] 现场七：把 Redis 当持久数据库，重启数据没了  (conf)
    |
    v
  [08] 现场八：keys * 在生产环境一键卡死  (bash)
    |
    v
  [... 其余 7 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
