# 缓存设计实战手记：凯喵那个凌晨三点被打穿的首页

> 这一章讲缓存设计、穿透/击穿/雪崩、缓存与数据库一致性。概念都会背，但真到大促流量峰值时，坑全在「以为没问题」的地方。这篇手记用十二个现场把这条链路走一遍。

## 开场：缓存的本质是「用一致性换延迟」

缓存之所以快，是因为它跳过了慢路径（数据库、下游服务），代价是**数据可能不是最新的**。所以缓存设计的所有争论，最终都归结为一个问题：这个业务能容忍多长时间的不一致。

把这个问题想清楚，具体方案就自然出来了：能容忍 1 秒的用过期时间，不能容忍的要在写路径上做文章，介于两者之间的用「先更新库再删缓存 + 延迟双删」。下面十二个现场按这条主线展开。

### 现场一：缓存穿透——查一个不存在的数据，每次打到数据库

某个恶意用户用 `id=-1`、`id=999999999` 反复请求，缓存里永远没有（因为数据本身不存在），每次都落到数据库。数据库被打到 QPS 上限。

三种防护，按成本递增：

```python
# 方案一：缓存空值（最简单，适合 id 有限的场景）
def get_user(uid):
    key = f"user:{uid}"
    val = redis.get(key)
    if val is not None:
        return None if val == "__NULL__" else json.loads(val)
    row = db.query("SELECT * FROM user WHERE id=%s", uid)
    if row is None:
        redis.setex(key, 300, "__NULL__")   # 短 TTL，防止长期占用
        return None
    redis.setex(key, 3600, json.dumps(row))
    return row

# 方案二：布隆过滤器（适合 id 空间巨大、只关心「存在性」）
# 初始化时把所有合法 id 灌进布隆过滤器，查询前先过一遍
if not bloom.exists(f"user:{uid}"):
    return None          # 一定不存在，直接短路，不查库

# 方案三：参数校验 + 限流（治标但必做）
if not (0 < uid < MAX_UID) or rate_limit(uid):
    return None
```

空值缓存的坑是：如果攻击者随机生成大量不同的 id，空值缓存本身会把 Redis 内存打满。所以必须配**短 TTL + 单独的前缀 + 内存告警**，或者直接用布隆过滤器。

### 现场二：缓存击穿——热点 key 过期瞬间，大量请求同时回源

某个首页配置 key 的 TTL 到期，恰好 5000 QPS 同时发现缓存没了，一起回源查数据库——数据库瞬间被压死。

三种解法：

```python
# 方案一：互斥锁（最稳，代价是有一点等待）
def get_config(key):
    val = redis.get(key)
    if val is not None:
        return json.loads(val)
    lock = f"lock:{key}"
    if redis.set(lock, "1", nx=True, ex=10):        # 抢到锁的只有一个
        try:
            data = db.load_config(key)
            redis.setex(key, 300, json.dumps(data))
            return data
        finally:
            redis.delete(lock)
    else:
        # 没抢到锁：短暂等待后重试（或返回旧值）
        time.sleep(0.05)
        return get_config(key)

# 方案二：逻辑过期（不设 TTL，值里带过期时间，异步刷新）
def get_config_logical(key):
    raw = redis.get(key)
    if raw is None:
        return load_and_cache(key)          # 首次加载
    obj = json.loads(raw)                   # {"data":..., "expire_at":...}
    if obj["expire_at"] > time.time():
        return obj["data"]                  # 未过期，直接返回
    # 已逻辑过期：返回旧值 + 异步刷新（保证可用性优先）
    async_refresh(key)
    return obj["data"]
```

凯喵的选型：**强一致要求高的用互斥锁，可用性优先的用逻辑过期**。逻辑过期的优势是「永远不会因为缓存失效而阻塞请求」，代价是可能返回稍旧的数据。

### 现场三：缓存雪崩——大量 key 同一时刻过期

所有 key 的 TTL 都设成 3600 秒、又是在同一时刻批量写入的，于是每小时整点集体失效，数据库周期性被打出尖峰。

修法是给 TTL 加随机抖动：

```python
import random

def set_with_jitter(key, val, base_ttl=3600, jitter=300):
    ttl = base_ttl + random.randint(-jitter, jitter)
    redis.setex(key, max(60, ttl), val)      # 下限保护，别设成负数
```

更彻底的方案是**分级 TTL**：核心配置 10 分钟、普通数据 1 小时、冷数据 1 天，让失效点自然分散。

还有一种「雪崩」不是过期引起的：**Redis 集群整体故障**。这时所有请求直接打数据库，通常几秒内就打挂。必须有的兜底：

```python
def get_with_fallback(key):
    try:
        val = redis.get(key)
        if val is not None:
            return json.loads(val)
    except RedisError:
        metrics.incr("cache.unavailable")     # 关键：缓存故障必须单独告警
    # 降级：走本地缓存 → 限流 → 返回默认值，绝不无脑打库
    local = local_cache.get(key)
    if local is not None:
        return local
    if not rate_limiter.allow():
        return DEFAULT_VALUE                  # 明确降级，而不是拖垮数据库
    return db.query(key)
```

### 现场四：先更新数据库再删缓存，中间读到旧值

经典的一致性问题。时序：

```text
T1: 写请求更新数据库（值变成 B）
T2: 读请求查缓存，命中旧的 A，返回 A     ← 读到脏数据
T3: 写请求删除缓存
T4: 后续读请求回源，拿到 B，写回缓存     ← 之后才正常
```

这个窗口很小（通常毫秒级），但在「读多写少 + 读在写前后紧邻」的场景下会真实发生。

标准做法是「**先更新库、再删缓存**」，并配合：

```python
def update_user(uid, data):
    db.update("user", uid, data)        # 1. 先改库
    redis.delete(f"user:{uid}")         # 2. 再删缓存（不是更新缓存！）
    # 3. 延迟双删：等一小会儿再删一次，覆盖「读请求把旧值写回」的窗口
    schedule_after(500, lambda: redis.delete(f"user:{uid}"))
```

两个关键点：一是**删缓存而不是更新缓存**（更新缓存有并发覆盖问题，且写多读少时白费计算）；二是**延迟双删的时间要大于一次读请求的耗时**（通常 300-500ms），太短没覆盖到，太长影响一致性窗口。

### 现场五：为什么是「删缓存」而不是「更新缓存」

很多人直觉是「写库成功后顺便把新值写进缓存」，看起来更省一次回源。但它有两个严重问题：

```text
问题一：并发写覆盖
  T1 写库=A（慢）  T2 写库=B（快）
  T2 更新缓存=B    T1 更新缓存=A     ← 缓存里是旧值 A，且长期不纠正

问题二：无效计算
  写了 100 次但只读了 1 次的数据，更新缓存等于算了 99 次无用功
```

「删缓存」把「写入缓存」的时机推迟到下次读取，天然避免了写写并发覆盖，也避免了无效计算。**「Cache-Aside + 删除」是绝大多数场景的正确选择**，只有在「写极频繁、读极频繁、值计算极贵」时才考虑「写穿透（write-through）」。

### 现场六：缓存和数据库双写不一致，怎么兜底

即使做对了「先库后删」，仍有极小概率不一致（比如删缓存那一步失败、或主从延迟导致读到了旧库）。必须有兜底机制：

```python
# 兜底一：给缓存设一个较短的 TTL（比如 5 分钟）
# 哪怕逻辑上永不失效，也要有物理过期，保证最终一致

# 兜底二：异步对账
def reconcile(uid):
    db_val = db.query_user(uid)
    cache_val = redis.get(f"user:{uid}")
    if cache_val and json.loads(cache_val) != db_val:
        redis.delete(f"user:{uid}")      # 不一致就删掉，让下次读回源

# 兜底三：binlog 订阅（最可靠，适合强一致要求高的场景）
# 用 Canal / Debezium 订阅数据库变更，异步删缓存
```

凯喵的实践：**TTL 是必须的，对账是可选的，binlog 是给「绝对不能不一致」的场景准备的**。三层里至少要有第一层，因为任何主动失效机制都可能失败。

### 现场七：缓存 key 设计得太粗，改一个字段全表失效

把整个用户对象序列化成一个 key，改昵称时删掉整个 key，下次读又要回源查全字段。高并发下等于缓存完全失效。

更细的粒度设计：

```python
# 粗粒度（不推荐）：一个 key 存整个对象
# user:1000 -> {"id":1000,"name":"kaimao","avatar":"...","stats":{...}}
# 改 name 就要删整个 key

# 细粒度（推荐）：按「访问模式」拆
# user:1000:profile  -> {"name":"kaimao","avatar":"..."}     （读多写少）
# user:1000:stats    -> {"posts":123,"followers":45}          （可容忍延迟）
# user:1000:settings -> {...}                                 （写多读少）

# 或者用 hash，按字段更新
redis.hset("user:1000", "name", "kaimao")     # 只改一个字段
redis.hget("user:1000", "name")
```

拆分的依据是**读写比和更新频率**：读多写少的独立存、变化频繁的用 hash 按字段更新、能容忍延迟的单独设 TTL。

### 现场八：把大对象塞进缓存，网络先成瓶颈

一个商品详情缓存 200KB，QPS 5000，光出口带宽就是 `200KB × 5000 = 1GB/s`。Redis 本身没满，网卡先满了。

优化方向：

```text
1. 只缓存「渲染首屏真正需要的字段」，其余按需查
2. 压缩：大 JSON 用 msgpack/zstd 压缩，通常能到 1/3~1/10
3. 分片读取：列表只存 id，详情按需批量取（MGET / pipeline）
4. 用更紧凑的结构：hash 比 JSON 字符串省（省掉重复的 key 名）
```

凯喵的经验阈值：**单个 value 超过 10KB 就该审视，超过 100KB 基本是设计问题**。而且大 value 还有个隐性代价——删除/过期时会阻塞主线程（`DEL` 是同步的），需要改用 `UNLINK`（异步删除）。

### 现场九：`KEYS *` 和 `FLUSHALL` 在生产上执行

这两个命令都是 O(n) 且阻塞单线程，几百万 key 的库上执行一次就是几十秒不可用。

替代方案：

```bash
# 遍历：用 SCAN 游标，分批不阻塞
redis-cli --scan --pattern 'user:*' --count 1000 | head -100

# 删除前缀：用 SCAN + UNLINK 组合（绝不用 KEYS + DEL）
redis-cli --scan --pattern 'tmp:*' --count 500 | xargs -n 100 redis-cli unlink

# 清库：用 FLUSHALL ASYNC（4.0+）或直接重建实例
redis-cli flushall async
```

更进一步，可以在 `redis.conf` 里直接禁用危险命令：

```conf
rename-command KEYS ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_9f8a3b"   # 改名而非禁用，保留运维能力
```

### 现场十：缓存预热没做，发版后第一个请求全部回源

新版本上线后缓存是空的，瞬时流量全部打到数据库。如果 QPS 是 5000，数据库可能直接挂。

预热方案：

```python
def warmup():
    # 1. 找出热点 key（从访问日志或监控里取 top N）
    hot_keys = load_top_keys(n=10000)
    # 2. 批量回源并写入（控制并发，别把库打满）
    with ThreadPoolExecutor(max_workers=8) as pool:
        for batch in chunked(hot_keys, 200):
            pool.submit(load_and_cache_batch, batch)
            time.sleep(0.05)          # 主动限速，给数据库留余量
```

关键细节：**预热必须限速**。凯喵见过预热脚本把数据库打挂的事故——因为预热本身就是一次全量回源，和缓存雪崩的效果一样。

### 现场十一：把缓存当存储用，重启后数据全丢

有人把 session、购物车、甚至订单状态放在 Redis 里，且没配持久化、没做兜底。一次实例迁移，数据全没了。

判断标准很简单：**这份数据丢了，业务能不能自行恢复？**

```text
能恢复（可接受）：页面配置、排行榜快照、推荐结果 → 纯缓存，丢了回源
不能恢复（危险）：session、购物车、验证码、幂等键 → 必须有持久化或兜底存储
```

对第二类，至少要做到：`appendonly yes`（AOF）+ 定期 RDB + 主从 + 「Redis 不可用时降级到数据库或本地存储」。

凯喵的原则：**Redis 是加速层，不是真相来源**。任何「只存在 Redis 里的数据」都要问一句：如果它明天消失，会发生什么。

### 现场十二：没有缓存命中率监控，优化全凭感觉

「加了缓存」不等于「缓存有效」。必须监控的指标：

```bash
redis-cli info stats | grep -E 'keyspace_hits|keyspace_misses|evicted_keys|expired_keys'
# 命中率 = hits / (hits + misses)，低于 80% 要查原因

redis-cli info memory | grep -E 'used_memory_human|maxmemory_human|mem_fragmentation_ratio'
# used_memory 接近 maxmemory 时，淘汰会开始影响命中率

redis-cli info stats | grep rejected_connections
# 连接数打满的早期信号
```

四个典型诊断：

```text
命中率高但延迟高    → 大 key / 慢命令 / 网络
命中率低            → TTL 太短 / key 设计粒度太细 / 缓存被频繁淘汰
evicted_keys 增长快 → 内存不足，加内存或缩短 TTL
mem_fragmentation>1.5 → 内存碎片，考虑重启或 activedefrag
```

## 三视角解析
### 🧑‍💻 程序员视角
缓存穿透是「查一个数据库里也不存在的数据」，每次都穿过缓存打到 DB——解法是缓存空值（带短 TTL）或布隆过滤器前置。缓存击穿是「热点 key 过期瞬间大量请求同时回源」，解法是互斥锁重建或逻辑过期（不设 TTL，异步刷新）。缓存雪崩是「大量 key 同一时刻过期」，解法是 TTL 加随机抖动。更新策略上「先更库再删缓存」仍可能读到旧值（并发读在删除前把旧值写回缓存），「延迟双删」也只能降低概率，强一致必须加锁或走串行化。

### 🎓 博士生视角
缓存一致性的本质是「两个存储系统的写入顺序问题」：无论「先更库后删缓存」还是「先删缓存后更库」，在并发下都存在窗口。Cache-Aside 的经典分析表明，唯一能保证强一致的方案是「读时加锁 + 写时加锁」，代价是吞吐下降。工程上接受「最终一致」，用「删除而非更新缓存」+「延迟双删」+「binlog 订阅补偿」把不一致窗口压到毫秒级。布隆过滤器的误判率由位数组大小与哈希函数个数决定，公式为 `(1-e^(-kn/m))^k`。

### 📚 考研者视角
后端面试高频：
1. **三大问题**：穿透（不存在的数据）、击穿（热点 key 失效）、雪崩（大量同时失效），各自的成因与解法。
2. **更新策略**：Cache-Aside、Read/Write-Through、Write-Behind 的差异与适用场景。
3. **一致性**：为什么「删缓存」优于「更新缓存」、延迟双删的原理与局限。
4. **布隆过滤器**：原理、误判率、不支持删除（用计数布隆或布谷鸟过滤器解决）。

## 收尾：凯喵的缓存设计四问

设计任何缓存前，先回答四个问题：

**能容忍多久不一致**——决定 TTL 和更新策略（删缓存 / 延迟双删 / binlog）。

**失效时怎么办**——穿透有布隆、击穿有互斥、雪崩有抖动；Redis 整体挂了要有本地缓存 + 限流兜底。

**key 粒度对不对**——按读写比拆，别一个大对象装全部；单 value 超 10KB 就该审视。

**怎么知道它有效**——命中率、淘汰数、内存碎片、连接数，四个指标缺一不可。

最后说一句认知层面的话。缓存是分布式系统里最典型的「用复杂度换性能」的组件：它把一次慢查询变成一次快查询，同时引入了不一致、失效、雪崩、穿透这一整族问题。所以「加缓存」从来不是一个单点优化，而是一次**系统性的契约变更**——你必须同时定义「不一致的容忍度」「失效时的退路」「怎么观测它是否在工作」。

凯喵见过最稳的缓存系统，不是用了最花哨方案的，而是把「TTL 有抖动、失效有锁、故障有降级、指标有告警」这四件事都做到位的。反过来，只加了缓存却没定义退路的系统，平时看起来快，一到流量峰值就变成整个链路上最先崩的那一环——因为它把所有的压力都攒到了失效的那一刻。
