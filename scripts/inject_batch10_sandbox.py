# -*- coding: utf-8 -*-
"""批次十：middleware 六章 + bigdata 四章 + data 四章 sandbox。

与前几批同一套路：写进 content/_handmade/labs.json 的 chapters，
再由 gen_interactive.py 并入各章 interactive.json 与前端数据。

为什么是这十四章
-------------
中间件、大数据、数据分析三块的知识点，书上大多是「结论 + 配置项」，
但每一个结论背后都有一笔能算的账：

  mw-ch01  Redis 小 hash 用 listpack 592 字节/个，hashtable 2624——差 4.4 倍
  mw-ch02  appendfsync always 每次写都 fsync，吞吐被压到 1000 QPS
  mw-ch04  缓存穿透：10% 未命中 × 50% 恶意 key，DB 直接接 5000+ QPS
  mw-ch06  Kafka 每条消息一次往返 vs 攒 64KB：吞吐差 64 倍
  mw-ch07  先 ack 后处理 → 处理失败的消息直接消失；重试 → 重复消费
  mw-ch08  消费者数超过分区数纯属浪费，积压追平时间 = 积压 / (消费 - 生产)
  bd-ch01  一亿个 1MB 小文件：NameNode 28GB 堆 + 一亿个 map task
  bd-ch03  不分区扫 2TB，按天分区只扫 5.5GB
  bd-ch05  sort-merge join shuffle 1TB，broadcast join shuffle 0
  bd-ch06  60 个报表各扫 30% 原始数据，一天烧 1080 元；分层后 78 元
  data-ch03 object 列 68 字节/行 vs category 8 字节；iterrows 3μs/行
  data-ch04  merge 前不聚合，一对多把 200 万行放大成 1000 万行
  data-ch05  10000 页串行 50 分钟；并发上限由「限速 × 单请求耗时」决定
  data-ch06  1000 组 × 5 折 × 30 秒 = 41.7 小时，8 核并行 5.2 小时

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限（小规模怎么配都对，没教学意义）。
2. 不锁「正确答案」，让预算判据自己淘汰错方案。
3. 默认值 = 真实事故配置（默认参数 / 教材写法 / 新手写法）。
4. `if(c,a,b)` 急切求值 → 分支内除法保证除数非零常量。
5. fmt 只认 int / fix2 / pct；不支持科学计数法。
6. 判据阈值留 5% 以上余量；被引用的指标必须定义在前面。

写盘必须 indent=1 + newline="\\n"；且只替换本章 sandbox、保留 debug 等其它模块。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# middleware/mw-ch01 · 一百万个缓存 key，多花 2GB
# ----------------------------------------------------------------------------
# 教学点：Redis 7 的 hash 在字段数 ≤128 且值 ≤64B 时用 listpack（一块连续内存，
# 每字段约 28 字节）；一旦超阈值或显式配置 hash-max-listpack-entries=0，
# 就转成 hashtable（每个字段两个 dictEntry + 两条 SDS，约 128 字节）——4 倍。
# ============================================================================
mw_ch01 = {
    "kind": "sandbox",
    "title": "一百万个缓存 key，多花 2GB",
    "brief": (
        "同样存「100 万个 hash、每个 20 个字段」，Redis 可能只吃 565MB，"
        "也可能吃到 2.5GB——差别只在底层编码。"
        "小 hash 用 listpack（一块连续内存，每字段约 28 字节），"
        "超过阈值就转 hashtable（每字段两个 dictEntry + 两条 SDS，约 128 字节）。"
        "把 key 数量与编码拖到真实值，看这 4.4 倍是怎么来的。"
    ),
    "params": [
        # key 数量（万）
        {"key": "keysW", "label": "hash key 数量（万）", "min": 10, "max": 500, "step": 10, "value": 100},
        # 每个 hash 的字段数
        {"key": "fields", "label": "每个 hash 字段数", "min": 4, "max": 200, "step": 4, "value": 20},
        # 编码配置
        {"key": "encoding", "label": "hash 编码", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["hashtable（禁用 listpack）", "listpack（默认自动）"]},
    ],
    "metrics": [
        {"key": "keys", "label": "hash key 总数", "expr": "keysW * 10000", "unit": "个", "fmt": "int"},
        # listpack 每 key：每字段 28 字节 + 头部 32
        {"key": "lpBytes", "label": "listpack 每 key", "expr": "fields * 28 + 32", "unit": "字节", "fmt": "int"},
        # hashtable 每 key：每字段 128 字节 + dict 头 64
        {"key": "htBytes", "label": "hashtable 每 key", "expr": "fields * 128 + 64", "unit": "字节", "fmt": "int"},
        # 实际生效的编码：listpack 只在字段数 ≤128 时生效（阈值）
        {"key": "effLP", "label": "实际是否 listpack", "expr": "if(encoding == 1, if(fields <= 128, 1, 0), 0)", "unit": "是/否", "fmt": "int"},
        # 每 key 实际占用
        {"key": "perKey", "label": "每 key 实际占用", "expr": "if(encoding == 1, if(fields <= 128, fields * 28 + 32, fields * 128 + 64), fields * 128 + 64)", "unit": "字节", "fmt": "int"},
        # 总内存
        {"key": "totalMB", "label": "总内存占用", "expr": "keysW * 10000 * if(encoding == 1, if(fields <= 128, fields * 28 + 32, fields * 128 + 64), fields * 128 + 64) / 1048576", "unit": "MB", "fmt": "int"},
        # 相对 listpack 的膨胀
        {"key": "blowup", "label": "相对 listpack 膨胀", "expr": "if(encoding == 1, if(fields <= 128, 1, 5), 4)", "unit": "×", "fmt": "int"},
        # 单 key 读写是否需要两次寻址（hashtable 要跳到 dictEntry 再跳 SDS）
        {"key": "ptrChases", "label": "单 key 平均指针跳转", "expr": "if(encoding == 1, if(fields <= 128, 1, 4), 4)", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        # 下限：十万个 key 起，几百个 key 的编码差异无感
        {"expr": "keys >= 100000", "label": "hash key ≥10 万个（真实的会话/购物车/画像场景）"},
        # 前提：真实的小对象有十几个字段（避免把 fields 拖到最小值就通关）
        {"expr": "fields >= 12", "label": "每个 hash ≥12 个字段（用户画像/会话的真实形态）"},
        # 上限：内存必须装得进实例
        {"expr": "totalMB <= 700", "label": "总内存 ≤700MB"},
        # 上限：必须真的走 listpack 编码
        {"expr": "effLP == 1", "label": "实际编码为 listpack（小 hash 用紧凑编码）"},
        # 上限：单 key 指针跳转
        {"expr": "ptrChases <= 1", "label": "单 key 指针跳转 ≤1 次（连续内存）"},
    ],
    "insight": (
        "Redis 的「一种数据结构」在底层有多种编码，选哪种由**规模阈值**自动决定："
        "hash 在字段数 ≤128 且单值 ≤64 字节时用 **listpack**（Redis 7 之前叫 ziplist）——"
        "所有字段塞进一块连续内存，每字段约 28 字节（前驱长度 + 编码 + 内容），"
        "读一个 key 只需一次内存寻址，CPU 缓存友好。"
        "超过阈值转 **hashtable**：每个字段要有 key 和 value 两个 `dictEntry`，"
        "每个 entry 又是两条 SDS 字符串（还有各自的头部与预分配），"
        "实测约 128 字节/字段——**4 倍以上**，而且每读一个字段要跳 2~4 次指针。"
        "这不是配置洁癖：100 万个 20 字段的 hash，listpack 565MB、hashtable 2.5GB，"
        "直接决定你能不能塞进 4GB 的实例、会不会触发淘汰。"
        "三条实操："
        "① **小对象尽量用 hash**（`HSET user:1 name x age 18`），比给每个字段建一个 "
        "string key 省得多（一个 string key 光是 key 本身 + robj + SDS 就要 100 字节）；"
        "② **别随手关掉阈值**：`hash-max-listpack-entries 0` 是性能调优的反模式，"
        "除非你确认字段数会稳定超过几百；"
        "③ **阈值是可调的**：字段数稳定在 200 时把 `hash-max-listpack-entries` 提到 256，"
        "仍是 O(n) 查找但 n=200 的线性扫描比指针跳转快——**在阈值内，"
        "线性扫描胜过哈希查找**，这是小对象压缩编码的核心取舍。"
    ),
}


# ============================================================================
# middleware/mw-ch02 · 每次写都 fsync，吞吐掉到 1/50
# ----------------------------------------------------------------------------
# 教学点：appendfsync always 每条命令一次 fsync（约 1ms），单实例写吞吐
# 被钉死在 1000 QPS；everysec 由后台线程每秒 fsync 一次，吞吐不受限，
# 代价是最多丢 1 秒；只开 RDB 则丢最后一次快照之后的全部（默认 5 分钟）。
# 另外 RDB fork 时的 COW 会让内存短暂翻倍（写多的实例更明显）。
# ============================================================================
mw_ch02 = {
    "kind": "sandbox",
    "title": "每次写都 fsync，吞吐掉到 1/50",
    "brief": (
        "`appendfsync always` 保证一条不丢：每条写命令都要等一次 `fsync` 落盘，"
        "机械盘 1ms 一次，单实例写吞吐被钉死在 1000 QPS。"
        "`everysec` 让后台线程每秒刷一次，吞吐跑满，代价是最多丢 1 秒数据。"
        "只开 RDB 则可能丢 5 分钟。把写入速率与持久化方式拖到真实值，"
        "看「不丢数据」这件事的价格。"
    ),
    "params": [
        # 每秒写命令数（千）
        {"key": "writesK", "label": "每秒写命令（千）", "min": 1, "max": 200, "step": 1, "value": 50},
        # 实例内存（GB）
        {"key": "memGB", "label": "实例内存", "min": 1, "max": 64, "step": 1, "value": 16},
        # 持久化方式
        {"key": "mode", "label": "持久化方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["AOF appendfsync always", "AOF appendfsync everysec", "仅 RDB 快照"]},
    ],
    "metrics": [
        # 需要的写吞吐
        {"key": "needQps", "label": "需要的写 QPS", "expr": "writesK * 1000", "unit": "QPS", "fmt": "int"},
        # 每秒 fsync 次数
        {"key": "fsyncPerSec", "label": "每秒 fsync 次数", "expr": "if(mode == 0, writesK * 1000, if(mode == 1, 1, 0))", "unit": "次", "fmt": "int"},
        # 单实例写吞吐上限
        {"key": "qpsCap", "label": "写吞吐上限", "expr": "if(mode == 0, 1000, if(mode == 1, 150000, 200000))", "unit": "QPS", "fmt": "int"},
        # 实际能服务的写 QPS
        {"key": "servedQps", "label": "实际服务 QPS", "expr": "min(writesK * 1000, if(mode == 0, 1000, if(mode == 1, 150000, 200000)))", "unit": "QPS", "fmt": "int"},
        # 被挡掉的请求比例
        {"key": "overflowPct", "label": "请求被挡比例", "expr": "(writesK * 1000 - min(writesK * 1000, if(mode == 0, 1000, if(mode == 1, 150000, 200000)))) * 100 / (writesK * 1000)", "unit": "%", "fmt": "int"},
        # 故障时最多丢多少数据
        {"key": "rtoS", "label": "崩溃最多丢数据", "expr": "if(mode == 0, 0, if(mode == 1, 1, 300))", "unit": "秒", "fmt": "int"},
        # RDB fork 时 COW 复制的内存（按 50% 页被改写）
        {"key": "cowMB", "label": "fork 时 COW 复制", "expr": "if(mode == 2, memGB * 1024 * 50 / 100, 0)", "unit": "MB", "fmt": "int"},
        # fork 期间峰值内存
        {"key": "peakGB", "label": "fork 期间峰值内存", "expr": "memGB + if(mode == 2, memGB * 50 / 100, 0)", "unit": "GB", "fmt": "int"},
    ],
    "checks": [
        # 下限：每秒两万写起，低频写入怎么配都行
        {"expr": "writesK >= 20", "label": "写吞吐 ≥2 万 QPS（真实的高写入场景）"},
        # 上限：崩溃最多丢 1 秒
        {"expr": "rtoS <= 1", "label": "崩溃最多丢 1 秒数据（RPO ≤1s）"},
        # 上限：请求不能被挡
        {"expr": "overflowPct <= 5", "label": "被挡请求 ≤5%（吞吐要跟得上）"},
        # 上限：fork 期间峰值内存别超过 1.6 倍
        {"expr": "peakGB <= memGB * 1.6", "label": "fork 峰值内存 ≤1.6 倍（不能把机器撑爆）"},
    ],
    "insight": (
        "Redis 持久化的三种组合，本质是 **RPO（最多丢多少）与吞吐的交换**："
        "**always**：每条写命令同步 `fsync`，RPO=0，但一次 `fsync` 约 1ms（机械盘）"
        "→ 单实例写吞吐上限 **1000 QPS**，是 everysec 的 1/150。"
        "**everysec**：命令先写 AOF 缓冲区就返回，后台线程每秒 `fsync` 一次，"
        "RPO≤1 秒，吞吐几乎不受影响——**生产环境的默认选择**。"
        "**仅 RDB**：每 5 分钟（默认 `save 900 1 / 300 10 / 60 10000`）一次快照，"
        "RPO 可能是几分钟，重启恢复也慢（要重放整个数据集）。"
        "两个必须知道的细节："
        "① **fork 的 COW 代价**：RDB 快照和 AOF 重写都要 `fork` 子进程，"
        "fork 本身是 O(页表) 很快，但子进程写、父进程也写时触发 **copy-on-write**，"
        "被改写的页要复制一份——写入速率越高，COW 复制越多，峰值内存可能接近 2 倍。"
        "所以「`maxmemory` 要按 `实例内存 / 2` 规划」不是玄学；"
        "② **AOF 重写不能省**：AOF 是追加日志，`INCR` 一百万次就是一百万条命令，"
        "重写会生成「当前状态的最小命令集」（`SET counter 1000000` 一条），"
        "把文件从 GB 压回 MB。"
        "一句话选型：**要 RPO=0 就得接受 1000 QPS 的单实例上限**（或者上 Redis 集群分片），"
        "否则 everysec 是性价比最高的选择。"
    ),
}


# ============================================================================
# middleware/mw-ch04 · 缓存穿透：DB 替缓存挨打
# ----------------------------------------------------------------------------
# 教学点：缓存命中率 90% 看着不错，但每秒 10 万请求的 10% 就是 1 万 QPS 打到 DB；
# 若其中一半是「查不存在的 key」（恶意扫描/爬虫/参数错误），DB 还要为这些
# 必然为空的查询付出完整代价。空值缓存 + 布隆过滤器把这类请求挡在缓存层。
# ============================================================================
mw_ch04 = {
    "kind": "sandbox",
    "title": "缓存穿透：DB 替缓存挨打",
    "brief": (
        "命中率 90% 听起来很好，但每秒 10 万请求里仍有 1 万打到数据库；"
        "如果其中一半是「查一个根本不存在的 id」（爬虫、恶意扫描、前端传错参数），"
        "数据库就是在为必然为空的查询反复做全表/索引查找。"
        "布隆过滤器 + 空值缓存能把这类请求挡在缓存层。"
        "把请求量、命中率、恶意占比与防护手段拖到真实值，看 DB 承压多少。"
    ),
    "params": [
        # 每秒请求（千）
        {"key": "reqK", "label": "每秒请求（千）", "min": 1, "max": 200, "step": 1, "value": 100},
        # 缓存命中率
        {"key": "hitPct", "label": "缓存命中率", "min": 50, "max": 99, "step": 1, "value": 90},
        # 未命中里「DB 也没有」的比例
        {"key": "notExistPct", "label": "未命中中不存在的 key 占比", "min": 0, "max": 100, "step": 5, "value": 50},
        # 防护
        {"key": "guard", "label": "穿透防护", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["无防护", "布隆过滤器 + 空值缓存"]},
    ],
    "metrics": [
        {"key": "reqQps", "label": "总请求 QPS", "expr": "reqK * 1000", "unit": "QPS", "fmt": "int"},
        # 未命中量
        {"key": "missQps", "label": "缓存未命中 QPS", "expr": "reqK * 1000 * (100 - hitPct) / 100", "unit": "QPS", "fmt": "int"},
        # 其中「DB 也没有」的穿透请求
        {"key": "penetrateQps", "label": "穿透请求 QPS", "expr": "reqK * 1000 * (100 - hitPct) / 100 * notExistPct / 100", "unit": "QPS", "fmt": "int"},
        # 打到 DB 的 QPS：无防护全打；有防护只留 10%（布隆挡 98% + 空值缓存兜底）
        {"key": "dbQps", "label": "打到 DB 的 QPS", "expr": "if(guard == 1, reqK * 1000 * (100 - hitPct) / 100 * 10 / 100, reqK * 1000 * (100 - hitPct) / 100)", "unit": "QPS", "fmt": "int"},
        # DB 单机安全承载
        {"key": "dbCap", "label": "DB 单机安全承载", "expr": "5000", "unit": "QPS", "fmt": "int"},
        # 超载倍数
        {"key": "overload", "label": "DB 超载倍数", "expr": "if(guard == 1, reqK * 1000 * (100 - hitPct) / 100 * 10 / 100 / 5000, reqK * 1000 * (100 - hitPct) / 100 / 5000)", "unit": "×", "fmt": "fix2"},
        # DB CPU（线性外推到 100%）
        {"key": "dbCpuPct", "label": "DB CPU 估算", "expr": "if(guard == 1, min(100, reqK * 1000 * (100 - hitPct) / 100 * 10 / 100 * 100 / 5000), min(100, reqK * 1000 * (100 - hitPct) / 100 * 100 / 5000))", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：五万 QPS 起，小流量怎么都扛得住
        {"expr": "reqK >= 50", "label": "总请求 ≥5 万 QPS（真实的热点接口）"},
        # 前提：确实存在穿透（恶意/不存在的 key）
        {"expr": "notExistPct >= 20", "label": "未命中中 ≥20% 是根本不存在的 key（穿透场景）"},
        # 上限：DB 不能超载
        {"expr": "overload <= 1", "label": "DB 负载 ≤1 倍安全水位"},
        # 上限：DB CPU
        {"expr": "dbCpuPct <= 80", "label": "DB CPU ≤80%"},
    ],
    "insight": (
        "缓存三大问题是**三种不同的失效模式**，别混："
        "**穿透**——查的数据根本不存在，缓存永远不命中，请求全打到 DB"
        "（恶意扫描、参数错误、爬虫遍历 id）；"
        "**击穿**——某个热点 key 过期瞬间，成百上千并发同时回源"
        "（正解是互斥锁/单飞 + 逻辑过期）；"
        "**雪崩**——大批 key 同一时刻过期，或缓存集群整体挂了"
        "（正解是过期时间加随机抖动 + 多级缓存 + 熔断降级）。"
        "穿透的两道防线："
        "① **布隆过滤器**（`BF.ADD` / RedisBloom）：把「存在的 id」预先灌进去，"
        "查询前先问「可能存在吗」——**说不存在就一定不存在**，直接返回空；"
        "误判率可控（1% 误判率约 9.6 bit/元素），代价是**不支持删除**"
        "（要用 counting bloom 或定期重建）；"
        "② **空值缓存**：DB 查不到也写一个短 TTL（30~60 秒）的空值，"
        "挡住短时间内的重复穿透；TTL 不能长，否则数据补录后仍然返回空。"
        "本例的账：10 万 QPS × 10% 未命中 = 1 万打到 DB；"
        "加防护后剩 1000（布隆挡掉 98% 的不存在 key + 空值缓存兜住残余），"
        "**从 2 倍超载回到 20% 水位**。"
        "最后一条工程纪律：**布隆过滤器只能挡「不存在」，挡不住「存在但热点」**——"
        "后者要靠本地缓存 + 逻辑过期 + 限流，不要指望一个组件解决三个问题。"
    ),
}


# ============================================================================
# middleware/mw-ch06 · 一条一发 vs 攒够 64KB：吞吐差 64 倍
# ----------------------------------------------------------------------------
# 教学点：Kafka 生产者的吞吐由「每批消息数 × 在途请求数 / 单次往返延迟」决定。
# batch.size 1KB（约 4 条）时每条消息都要等一次往返；攒到 64KB（256 条）
# 一次网络往返搬 256 条，吞吐提升两个数量级。acks=all 让往返变慢（要等 ISR 复制）。
# ============================================================================
mw_ch06 = {
    "kind": "sandbox",
    "title": "一条一发 vs 攒够 64KB：吞吐差 64 倍",
    "brief": (
        "`producer.send(record)` 逐条发送时，每条消息都要等一次网络往返；"
        "`batch.size` 攒到 64KB（约 256 条）再一次发出去，同样一次往返搬 256 条。"
        "吞吐公式是「每批条数 × 在途请求数 ÷ 往返延迟」，"
        "所以批量大小是吞吐的第一杠杆，`acks=all` 则把往返拉长（要等 ISR 全部确认）。"
        "把消息速率、批量大小与 acks 拖到真实值，看能不能追上生产速率。"
    ),
    "params": [
        # 消息速率（千条/秒）
        {"key": "msgsK", "label": "消息速率（千条/秒）", "min": 1, "max": 200, "step": 1, "value": 100},
        # 批量大小（KB）
        {"key": "batchKB", "label": "batch.size", "min": 1, "max": 64, "step": 1, "value": 1},
        # acks
        {"key": "acks", "label": "acks", "min": 0, "max": 2, "step": 1, "value": 1,
         "labels": ["acks=0（不等确认）", "acks=1（等 leader）", "acks=all（等 ISR）"]},
    ],
    "metrics": [
        # 每条消息按 256 字节算
        {"key": "msgsPerBatch", "label": "每批消息数", "expr": "batchKB * 1024 / 256", "unit": "条", "fmt": "int"},
        # 单次往返延迟
        {"key": "rttMs", "label": "单次往返延迟", "expr": "if(acks == 0, 2, if(acks == 1, 5, 15))", "unit": "ms", "fmt": "int"},
        # 生产者在途请求数（max.in.flight.requests.per.connection 默认 5）
        {"key": "inflight", "label": "在途请求数", "expr": "5", "unit": "个", "fmt": "int"},
        # 吞吐上限 = 每批条数 × 在途 ÷ 往返
        {"key": "throughput", "label": "吞吐上限", "expr": "batchKB * 1024 / 256 * 5 * 1000 / if(acks == 0, 2, if(acks == 1, 5, 15))", "unit": "条/秒", "fmt": "int"},
        # 需要的吞吐
        {"key": "need", "label": "需要吞吐", "expr": "msgsK * 1000", "unit": "条/秒", "fmt": "int"},
        # 每秒 send 调用次数
        {"key": "sendCalls", "label": "每秒 send 调用", "expr": "msgsK * 1000 * 256 / (batchKB * 1024)", "unit": "次", "fmt": "int"},
        # 消费积压速率
        {"key": "lagPerSec", "label": "每秒堆积消息", "expr": "msgsK * 1000 - batchKB * 1024 / 256 * 5 * 1000 / if(acks == 0, 2, if(acks == 1, 5, 15))", "unit": "条", "fmt": "int"},
    ],
    "checks": [
        # 下限：五万条/秒起，低频消息怎么发都行
        {"expr": "msgsK >= 50", "label": "消息速率 ≥5 万条/秒（日志/埋点这类真实流量）"},
        # 上限：吞吐必须追上生产速率
        {"expr": "throughput >= msgsK * 1000", "label": "吞吐 ≥生产速率（不能堆积）"},
        # 上限：每秒 send 调用
        {"expr": "sendCalls <= 2000", "label": "每秒 send 调用 ≤2000 次（别一条一发）"},
        # 上限：积压速率
        {"expr": "lagPerSec <= 0", "label": "积压速率 ≤0（不产生堆积）"},
    ],
    "insight": (
        "Kafka 生产者的吞吐公式可以写成："
        "**`吞吐 = 每批条数 × 在途请求数 ÷ 单次往返延迟`**。"
        "每批条数由 `batch.size`（默认 16KB）和 `linger.ms`（默认 0）共同决定——"
        "`linger.ms=0` 意味着「有就发」，批量永远攒不满；"
        "把它调到 5~20ms，用 5~20ms 的延迟换几十倍吞吐，是日志/埋点场景的标配。"
        "本例：1KB 批量 ≈ 4 条/批，5 个在途、5ms 往返 = **4000 条/秒**；"
        "64KB 批量 ≈ 256 条/批 = **25.6 万条/秒**——**64 倍**。"
        "`acks` 的影响是第二个维度："
        "`acks=0`（发了就算，不等确认）往返 2ms，但**丢了不知道**；"
        "`acks=1`（等 leader 写入）5ms，leader 挂了可能丢；"
        "`acks=all`（等 ISR 全部确认）15ms，最强保证但往返慢 3 倍——"
        "所以「可靠性」和「吞吐」在这里是直接相乘的关系。"
        "三个配套参数："
        "① **`compression.type=lz4/zstd`**：日志类文本压缩比 5~10 倍，"
        "把网络与磁盘成本直接降一个数量级（CPU 换带宽，几乎总是划算）；"
        "② **`max.in.flight.requests.per.connection`**：默认 5，配合 `acks=all` 时"
        "要开 `enable.idempotence=true`（否则重试会乱序）；"
        "③ **分区数 ≥ 消费者数**：否则加了消费者也吃不满（见 mw-ch08）。"
        "反过来，批量不是越大越好：`batch.size` 太大时内存占用涨（每分区一个缓冲），"
        "且 `linger.ms` 会真的增加端到端延迟——**实时性要求高的场景（风控、支付）"
        "宁可小批量**。"
    ),
}


# ============================================================================
# middleware/mw-ch07 · 先 ack 后处理，失败的消息就没了
# ----------------------------------------------------------------------------
# 教学点：自动 ack（收到就提交位点）时，处理失败的消息不会重投——直接丢。
# 手动 ack（处理成功再提交）保证「至少一次」，但失败重试会带来重复消费，
# 必须配合幂等（业务唯一键去重表 / 状态机）才能做到「恰好一次」的效果。
# ============================================================================
mw_ch07 = {
    "kind": "sandbox",
    "title": "先 ack 后处理，失败的消息就没了",
    "brief": (
        "「收到消息就 ack，再去处理业务」看着顺畅，但处理失败时位点已经提交，"
        "消息不会重投——**直接消失**。改成「处理成功再 ack」能保证至少一次，"
        "代价是失败重试会让同一条消息被消费多次，必须有幂等去重兜底。"
        "把消息速率、失败率、ack 时机与去重手段拖到真实值，"
        "看「不丢」和「不重」这两件事怎么同时成立。"
    ),
    "params": [
        # 消息速率（千条/秒）
        {"key": "msgsK", "label": "消息速率（千条/秒）", "min": 1, "max": 100, "step": 1, "value": 20},
        # 处理失败率
        {"key": "failPct", "label": "处理失败率", "min": 1, "max": 20, "step": 1, "value": 5},
        # ack 时机
        {"key": "ackMode", "label": "ack 时机", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["先 ack 再处理（自动提交）", "先处理再 ack（手动提交）"]},
        # 幂等去重
        {"key": "dedup", "label": "幂等去重", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["无（直接写库）", "业务唯一键去重"]},
    ],
    "metrics": [
        {"key": "msgs", "label": "消息速率", "expr": "msgsK * 1000", "unit": "条/秒", "fmt": "int"},
        # 失败消息数
        {"key": "failQps", "label": "处理失败条数", "expr": "msgsK * 1000 * failPct / 100", "unit": "条/秒", "fmt": "int"},
        # 丢失：自动 ack 时失败即丢（位点已提交，不会重投）
        {"key": "lostQps", "label": "丢失消息", "expr": "if(ackMode == 0, msgsK * 1000 * failPct / 100, 0)", "unit": "条/秒", "fmt": "int"},
        # 重复：手动 ack 时失败会重投，无幂等就重复消费
        {"key": "dupQps", "label": "重复消费", "expr": "if(ackMode == 0, 0, if(dedup == 1, 0, msgsK * 1000 * failPct / 100))", "unit": "条/秒", "fmt": "int"},
        # 重试次数
        {"key": "retryQps", "label": "重试次数", "expr": "if(ackMode == 0, 0, msgsK * 1000 * failPct / 100)", "unit": "次/秒", "fmt": "int"},
        # 有效处理（去重后的净效果）
        {"key": "effectivePct", "label": "有效处理率", "expr": "100 - if(ackMode == 0, failPct, if(dedup == 1, 0, failPct))", "unit": "%", "fmt": "int"},
        # 丢失比例
        {"key": "lostPct", "label": "丢失比例", "expr": "if(ackMode == 0, failPct, 0)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：每秒一万条起，低频消息的可靠性问题不明显
        {"expr": "msgs >= 10000", "label": "消息 ≥1 万条/秒（真实的订单/支付流水）"},
        # 前提：确实有失败（网络抖动/下游超时/脏数据）
        {"expr": "failPct >= 1", "label": "处理失败率 ≥1%（真实链路必然有失败）"},
        # 上限：一条都不能丢
        {"expr": "lostQps <= 0", "label": "丢失消息 = 0（至少一次投递）"},
        # 上限：重复消费控制在千分之一
        {"expr": "dupQps <= msgs * 0.001", "label": "重复消费 ≤千分之一（幂等要生效）"},
        # 上限：有效处理率
        {"expr": "effectivePct >= 99", "label": "有效处理率 ≥99%"},
    ],
    "insight": (
        "消息可靠性有三条独立的账，必须分开记："
        "**不丢**——位点什么时候提交？「收到就 ack」等于「还没处理就先记账」，"
        "处理失败时位点已前移，消息不会重投，**直接丢**。"
        "正解是**处理成功后再 ack**（手动提交/Kafka 的 `enable.auto.commit=false`），"
        "失败就不提交，重平衡或重投后还能再来一次——这就是「至少一次」。"
        "**不重**——至少一次的代价是**必然重复**：重复的条件是「处理成功但 ack 失败」，"
        "这个窗口永远存在（网络、进程崩溃、rebalance）。"
        "所以消费端**必须幂等**：业务唯一键 + 去重表、状态机（只允许 A→B 一次）、"
        "或数据库唯一约束 + `ON DUPLICATE KEY UPDATE`。"
        "**有序**——单分区内有序，但重试会打乱顺序（3 失败重投，4 已经处理完了）。"
        "要严格有序只能：① 失败就阻塞该分区（牺牲可用性）；"
        "② 用业务键做分区键，让同一实体落同一分区；③ 幂等 + 版本号丢弃旧消息。"
        "本例的账：2 万条/秒、5% 失败——自动 ack 丢 1000 条/秒（一天 8600 万条），"
        "手动 ack 不丢但重复 1000 条/秒，加去重表后两者都归零。"
        "一个常被忽略的坑：**去重表的 TTL**。消息可能延迟几小时才重投，"
        "去重键至少要保留「最大重投窗口」，否则过期后重复又进来了。"
    ),
}


# ============================================================================
# middleware/mw-ch08 · 消费者加到 20 个，吞吐一点没涨
# ----------------------------------------------------------------------------
# 教学点：分区是消费并行度的硬上限——同一分区同时只能被一个消费者消费。
# 消费者数 > 分区数时，多出来的消费者完全空闲；而要提升吞吐，
# 必须同时加分区和消费者。积压追平时间 = 积压量 /（消费速率 − 生产速率）。
# ============================================================================
mw_ch08 = {
    "kind": "sandbox",
    "title": "消费者加到 20 个，吞吐一点没涨",
    "brief": (
        "消费者从 8 个加到 20 个，吞吐纹丝不动——因为只有 8 个分区，"
        "同一分区同时只能被一个消费者消费，多出来的 12 个完全空闲。"
        "要加吞吐必须**同时加分区**（分区是并行的硬上限）。"
        "把生产速率、单消费者能力、分区数与消费者数拖到真实值，"
        "看积压能不能追平、有多少消费者在白拿钱。"
    ),
    "params": [
        # 生产速率（千条/秒）
        {"key": "produceK", "label": "生产速率（千条/秒）", "min": 1, "max": 200, "step": 1, "value": 100},
        # 单消费者能力（千条/秒）
        {"key": "perConsumerK", "label": "单消费者消费能力（千条/秒）", "min": 1, "max": 50, "step": 1, "value": 10},
        # 分区数
        {"key": "partitions", "label": "分区数", "min": 1, "max": 64, "step": 1, "value": 8},
        # 消费者数
        {"key": "consumers", "label": "消费者数", "min": 1, "max": 64, "step": 1, "value": 8},
    ],
    "metrics": [
        # 有效消费者 = min(消费者, 分区)
        {"key": "effective", "label": "有效消费者数", "expr": "min(consumers, partitions)", "unit": "个", "fmt": "int"},
        # 空闲消费者
        {"key": "idle", "label": "空闲消费者数", "expr": "consumers - min(consumers, partitions)", "unit": "个", "fmt": "int"},
        # 消费速率
        {"key": "consumeK", "label": "消费速率", "expr": "min(consumers, partitions) * perConsumerK", "unit": "千条/秒", "fmt": "int"},
        # 积压速率（正数=堆积）
        {"key": "backlogK", "label": "积压速率", "expr": "produceK - min(consumers, partitions) * perConsumerK", "unit": "千条/秒", "fmt": "int"},
        # 每小时堆积量（万条）
        {"key": "lagPerHourW", "label": "每小时堆积（万条）", "expr": "(produceK - min(consumers, partitions) * perConsumerK) * 3600 / 10", "unit": "万条", "fmt": "int"},
        # 消费利用率
        {"key": "utilPct", "label": "消费者利用率", "expr": "min(consumers, partitions) * 100 / consumers", "unit": "%", "fmt": "int"},
        # 每月浪费的消费者实例费（每个 300 元）
        {"key": "wasteYuan", "label": "每月为空闲消费者付费", "expr": "(consumers - min(consumers, partitions)) * 300", "unit": "元", "fmt": "int"},
    ],
    "checks": [
        # 下限：五万条/秒起，低流量不需要并行
        {"expr": "produceK >= 50", "label": "生产速率 ≥5 万条/秒（真实的高吞吐 topic）"},
        # 上限：不许有消费者空转
        {"expr": "idle <= 0", "label": "空闲消费者 = 0（消费者数不超过分区数）"},
        # 上限：必须能追平生产
        {"expr": "backlogK <= 0", "label": "积压速率 ≤0（消费追得上生产）"},
        # 上限：消费者利用率
        {"expr": "utilPct >= 90", "label": "消费者利用率 ≥90%"},
        # 上限：不许为空转实例付费
        {"expr": "wasteYuan <= 0", "label": "空转实例开销 = 0 元/月"},
    ],
    "insight": (
        "Kafka 的消费并行度有一条硬约束：**同一分区在同一消费组内同时只能被一个消费者消费**。"
        "所以 `有效消费者数 = min(消费者数, 分区数)`，多出来的消费者**一个消息都分不到**，"
        "只是白拿实例费（本例 20 消费者 / 8 分区 = 12 个空转，每月 3600 元）。"
        "两条推论，都是工程上最常踩的："
        "① **要提吞吐，先加分区**。分区数决定并行上限，消费者数决定实际用了几路。"
        "顺序反了就是「加机器不加吞吐」；"
        "② **分区不是越多越好**：分区多了元数据与副本开销涨（每个分区在 broker 上"
        "都有目录、索引、 follower 拉取线程），且 **Kafka 不支持减少分区**"
        "（只能新建 topic 迁移），所以初始分区数要按「未来 1~2 年峰值吞吐 ÷ 单分区能力」估。"
        "积压的账要单独算：**`追平时间 = 积压量 ÷ (消费速率 − 生产速率)`**。"
        "消费速率等于生产速率时追平时间是无穷大——这就是「积压了但看起来消费者都在跑」"
        "的真相：不是不消费，是**刚好抵平**，永远清不掉。"
        "扩容的正确姿势（在线无停机）："
        "① 先给 topic 加分区（`kafka-topics.sh --alter --partitions N`）——"
        "**注意：加分区会破坏 key 的分区映射，同一 key 的新旧消息可能落到不同分区，"
        "依赖分区内有序的业务要谨慎**；"
        "② 再把消费者实例加到与分区数相等；"
        "③ 积压期间临时扩消费者是无效的（受分区数限制），"
        "要更快只能「起一个临时消费者组把消息转到更多分区的新 topic」。"
    ),
}


# ============================================================================
# bigdata/bd-ch01 · 一亿个小文件，NameNode 先崩
# ----------------------------------------------------------------------------
# 教学点：HDFS 每个文件/目录/块在 NameNode 里约 150 字节元数据，且全部常驻堆。
# 一亿个 1MB 小文件 = 14GB 元数据（堆里再放大一倍），同时每个文件一个
# map task（启动开销 20ms），一亿个任务光启动就 23 天。
# ============================================================================
bd_ch01 = {
    "kind": "sandbox",
    "title": "一亿个小文件，NameNode 先崩",
    "brief": (
        "HDFS 每个文件在 NameNode 里约 150 字节元数据，而且**全量常驻堆内存**。"
        "一亿个 1MB 的小文件 = 14GB 元数据（堆里再放大一倍），"
        "外加一亿个 map task（每个启动 20ms）——光调度就要 23 天。"
        "把小文件数量、平均大小与是否合并拖到真实值，"
        "看「小文件问题」到底崩在哪一层。"
    ),
    "params": [
        # 文件数（百万）
        {"key": "filesM", "label": "文件数（百万）", "min": 1, "max": 500, "step": 1, "value": 100},
        # 平均文件大小（MB）
        {"key": "avgMB", "label": "平均文件大小", "min": 1, "max": 128, "step": 1, "value": 1},
        # 是否合并
        {"key": "merge", "label": "小文件处理", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["保持原样", "合并到 128MB 块"]},
    ],
    "metrics": [
        # 总数据量（GB）
        {"key": "totalGB", "label": "总数据量", "expr": "filesM * 1000000 * avgMB / 1024", "unit": "GB", "fmt": "int"},
        # 合并后文件数 = 总量 / 128MB
        {"key": "mergedFiles", "label": "合并后文件数", "expr": "filesM * 1000000 * avgMB / 128", "unit": "个", "fmt": "int"},
        # 实际文件数
        {"key": "fileCount", "label": "实际文件数", "expr": "if(merge == 1, filesM * 1000000 * avgMB / 128, filesM * 1000000)", "unit": "个", "fmt": "int"},
        # NameNode 元数据（每文件 150 字节，含目录项与块信息）
        {"key": "nnMB", "label": "NameNode 元数据", "expr": "if(merge == 1, filesM * 1000000 * avgMB / 128, filesM * 1000000) * 150 / 1048576", "unit": "MB", "fmt": "int"},
        # 堆占用（元数据对象放大 2 倍）
        {"key": "nnHeapGB", "label": "NameNode 堆占用", "expr": "if(merge == 1, filesM * 1000000 * avgMB / 128, filesM * 1000000) * 150 / 1048576 / 1024 * 2", "unit": "GB", "fmt": "int"},
        # map task 数（一个文件至少一个）
        {"key": "mapTasks", "label": "map task 数", "expr": "if(merge == 1, filesM * 1000000 * avgMB / 128, filesM * 1000000)", "unit": "个", "fmt": "int"},
        # 任务启动开销（每个 20ms）
        {"key": "taskStartH", "label": "任务启动总耗时", "expr": "if(merge == 1, filesM * 1000000 * avgMB / 128, filesM * 1000000) * 20 / 1000 / 3600", "unit": "小时", "fmt": "int"},
    ],
    "checks": [
        # 下限：一千万个文件起，小文件问题才显形
        {"expr": "filesM * 1000000 >= 10000000", "label": "文件数 ≥1000 万（典型的小文件事故规模）"},
        # 上限：NameNode 堆压到 20GB 内
        {"expr": "nnHeapGB <= 20", "label": "NameNode 堆 ≤20GB（留出 GC 余量）"},
        # 上限：任务数受控
        {"expr": "mapTasks <= 1000000", "label": "map task ≤100 万个"},
        # 上限：任务启动耗时可接受
        {"expr": "taskStartH <= 6", "label": "任务启动总耗时 ≤6 小时"},
    ],
    "insight": (
        "HDFS 的设计假设是**大文件、顺序读、一次写多次读**，"
        "而「每个文件一个块」的小文件恰恰把三件事全违背了："
        "**① NameNode 内存**：每个文件、目录、块在 NN 里都是独立对象（INode + 块列表），"
        "合计约 150 字节且**全部常驻堆**（JVM 对象还要放大 2 倍左右）。"
        "一亿文件 ≈ 14GB 原始 + 28GB 堆——单 NN 直接顶到上限"
        "（NN 的堆一般给 32GB 以内，因为 Full GC 停顿与堆大小成正比）。"
        "**② 计算层任务爆炸**：MapReduce/Spark 默认「一个文件至少一个 task」，"
        "一亿个 1MB 文件就是一亿个 task，每个启动 20ms（JVM 复用也要线程/调度开销），"
        "光启动 23 天——数据本身只有 100TB。"
        "**③ 随机 IO**：1MB 文件读一次就要一次 seek，吞吐远低于 128MB 顺序读。"
        "三种正解："
        "① **入湖前合并**（Flume 的 `hdfs.rollSize`/`rollCount`、"
        "`FileCompactor`、Spark 的 `repartition` 后 `coalesce` 再写）；"
        "② **HAR 归档**（Hadoop Archives 把小文件打成 .har，NN 只记一个文件，"
        "但读性能一般，属于「能用但别长期用」）；"
        "③ **换存储格式**：直接写 ORC/Parquet（一个文件装几百万行），"
        "或者上 Hudi/Iceberg/Delta（它们用「文件组 + 元数据日志」管理小文件，"
        "并支持自动 compaction）。"
        "一句话判据：**单文件小于块大小（128MB）就是小文件**，"
        "小文件占比超过 10% 就该上合并任务了。"
    ),
}


# ============================================================================
# bigdata/bd-ch03 · 不分区扫 2TB，分区只扫 5.5GB
# ----------------------------------------------------------------------------
# 教学点：Hive 分区就是目录，`WHERE dt='2026-11-05'` 只扫对应目录（分区裁剪）。
# 全表 2TB 扫一遍约 68 分钟；按天分区后查一天只扫 5.5GB，11 秒。
# 但分区粒度太细会产生大量小文件，反过来拖慢任务。
# ============================================================================
bd_ch03 = {
    "kind": "sandbox",
    "title": "不分区扫 2TB，分区只扫 5.5GB",
    "brief": (
        "同一张 2TB 的表，查一天的数据：不分区要全表扫 2TB（约 68 分钟），"
        "按天分区只扫 `dt=2026-11-05` 那个目录的 5.5GB（11 秒）。"
        "分区裁剪是 Hive 最便宜的优化，代价是分区太细会产生一堆小文件。"
        "把表大小、查询天数与分区方式拖到真实值，看扫多少数据、起多少任务。"
    ),
    "params": [
        # 表大小（GB）
        {"key": "tableGB", "label": "表大小", "min": 100, "max": 10000, "step": 100, "value": 2000},
        # 查询天数
        {"key": "days", "label": "查询覆盖天数", "min": 1, "max": 365, "step": 1, "value": 1},
        # 分区
        {"key": "partition", "label": "分区方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["不分区（单目录）", "按天分区"]},
    ],
    "metrics": [
        # 需要扫描的数据量
        {"key": "scanGB", "label": "扫描数据量", "expr": "if(partition == 1, tableGB * days / 365, tableGB)", "unit": "GB", "fmt": "int"},
        # 扫描耗时（500MB/s）
        {"key": "scanS", "label": "扫描耗时", "expr": "if(partition == 1, tableGB * days / 365, tableGB) * 1024 / 500", "unit": "秒", "fmt": "int"},
        # 文件数：分区后每天 200 个文件
        {"key": "files", "label": "输入文件数", "expr": "if(partition == 1, days * 200, 200)", "unit": "个", "fmt": "int"},
        # 任务启动开销
        {"key": "taskStartS", "label": "任务启动开销", "expr": "if(partition == 1, days * 200, 200) * 20 / 1000", "unit": "秒", "fmt": "int"},
        # 总耗时
        {"key": "totalS", "label": "查询总耗时", "expr": "if(partition == 1, tableGB * days / 365, tableGB) * 1024 / 500 + if(partition == 1, days * 200, 200) * 20 / 1000", "unit": "秒", "fmt": "int"},
        # 扫描量占比
        {"key": "scanPct", "label": "扫了表的百分之多少", "expr": "if(partition == 1, days * 100 / 365, 100)", "unit": "%", "fmt": "int"},
        # 分区数
        {"key": "partitions", "label": "分区数", "expr": "if(partition == 1, 365, 1)", "unit": "个", "fmt": "int"},
    ],
    "checks": [
        # 下限：1TB 起，小表全扫也无所谓
        {"expr": "tableGB >= 1000", "label": "表 ≥1TB（真实的事实表规模）"},
        # 前提：只查近一周的数据
        {"expr": "days <= 7", "label": "查询只覆盖 ≤7 天"},
        # 上限：扫描量
        {"expr": "scanGB <= 50", "label": "扫描 ≤50GB"},
        # 上限：查询耗时
        {"expr": "totalS <= 200", "label": "查询 ≤200 秒"},
        # 下限：扫描量占比说明真的裁剪了
        {"expr": "scanPct <= 3", "label": "只扫全表的 ≤3%（分区裁剪生效）"},
    ],
    "insight": (
        "Hive 的「分区」不是数据库意义上的逻辑分区，而是**目录**："
        "`/warehouse/orders/dt=2026-11-05/`。所以 `WHERE dt='2026-11-05'` 时，"
        "执行引擎**连这个目录都不进**其他的——这就是分区裁剪，"
        "它省的是**磁盘 IO**（本例 2TB → 5.5GB，364 倍），也是 Hive 最便宜的优化。"
        "三条必须记住的规则："
        "① **分区字段必须出现在 WHERE 里**，且不要套函数（`WHERE substr(dt,1,7)='2026-11'` "
        "会让裁剪失效，要改成 `WHERE dt BETWEEN '2026-11-01' AND '2026-11-30'`）；"
        "② **分区粒度要匹配查询模式**：按天分区适合「查最近 N 天」，"
        "按小时分区会让分区数 ×24，小文件问题随之放大；"
        "③ **分区不是索引**：分区内还是全扫，所以分区内要用 **ORC/Parquet + 列裁剪**，"
        "再叠 **谓词下推**（`WHERE` 条件下推到存储层跳过 row group）与 **分桶**（`CLUSTERED BY`，"
        "让 join 走 Map-side merge）。"
        "反面的坑：「为了查询灵活，按 20 个维度都分区」——"
        "分区目录数 = 维度基数的笛卡尔积，几十万个空目录，"
        "`SHOW PARTITIONS` 都要跑几分钟，NameNode 也会被拖死。"
        "正确的做法是**只按时间分区（基数小、单调增长），其余维度靠分桶或数据布局**。"
    ),
}


# ============================================================================
# bigdata/bd-ch05 · 一次 join 白搬 1TB
# ----------------------------------------------------------------------------
# 教学点：sort-merge join 要把两张表都按 join key 重分区（shuffle），
# 事实表 1TB 全量落盘溢写；broadcast join 把维表广播到每个 executor，
# shuffle 为 0——但维表超过 8GB 广播会 OOM。
# ============================================================================
bd_ch05 = {
    "kind": "sandbox",
    "title": "一次 join 白搬 1TB",
    "brief": (
        "事实表 1TB join 一张 500MB 的维表，默认走 sort-merge join——"
        "两张表都要按 join key 重分区，1TB 数据全量落盘再拉起来，"
        "光是 shuffle 就要一个多小时。维表只有 500MB，"
        "广播到每个 executor 就能变成 map 端 join，shuffle 归零。"
        "把事实表、维表大小与 join 策略拖到真实值，看这 1TB 是怎么白搬的。"
    ),
    "params": [
        # 事实表（GB）
        {"key": "factGB", "label": "事实表大小", "min": 10, "max": 5000, "step": 10, "value": 1000},
        # 维表（MB）
        {"key": "dimMB", "label": "维表大小", "min": 16, "max": 16384, "step": 16, "value": 512},
        # join 策略
        {"key": "mode", "label": "join 策略", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["sort-merge join（双表 shuffle）", "broadcast join（广播维表）"]},
        # 集群核数
        {"key": "cores", "label": "集群核数", "min": 10, "max": 500, "step": 10, "value": 100},
    ],
    "metrics": [
        # shuffle 数据量：sort-merge 两表都搬；broadcast 为 0
        {"key": "shuffleGB", "label": "shuffle 数据量", "expr": "if(mode == 0, factGB + dimMB / 1024, 0)", "unit": "GB", "fmt": "int"},
        # 溢写磁盘量（60% 需要落盘）
        {"key": "spillGB", "label": "磁盘溢写量", "expr": "if(mode == 0, (factGB + dimMB / 1024) * 60 / 100, 0)", "unit": "GB", "fmt": "int"},
        # 扫描事实表（5GB/s 列存并行）
        {"key": "scanS", "label": "扫描事实表", "expr": "factGB / 5", "unit": "秒", "fmt": "int"},
        # 总耗时：shuffle 200MB/s，broadcast 还要把维表发给每个 executor
        {"key": "totalS", "label": "作业总耗时", "expr": "if(mode == 0, (factGB + dimMB / 1024) * 1024 / 200 + factGB / 5, factGB / 5 + dimMB * cores / 4 / 1000)", "unit": "秒", "fmt": "int"},
        # stage 数
        {"key": "stages", "label": "stage 数", "expr": "if(mode == 0, 3, 2)", "unit": "个", "fmt": "int"},
        # 广播阈值（Spark 默认上限 8GB）
        {"key": "bcastLimitMB", "label": "广播上限", "expr": "8192", "unit": "MB", "fmt": "int"},
        # 是否会 OOM
        {"key": "bcastOOM", "label": "广播是否 OOM", "expr": "if(mode == 1, if(dimMB > 8192, 1, 0), 0)", "unit": "是/否", "fmt": "int"},
        # 相对最优策略的减速
        {"key": "slowdown", "label": "相对广播 join 减速", "expr": "if(mode == 0, ((factGB + dimMB / 1024) * 1024 / 200 + factGB / 5) / (factGB / 5 + dimMB * cores / 4 / 1000), 1)", "unit": "×", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：500GB 起，小表 join 怎么都无所谓
        {"expr": "factGB >= 500", "label": "事实表 ≥500GB（真实的大表 join）"},
        # 上限：shuffle 量
        {"expr": "shuffleGB <= 100", "label": "shuffle ≤100GB（别把大表整体搬一遍）"},
        # 上限：作业耗时
        {"expr": "totalS <= 260", "label": "作业 ≤260 秒"},
        # 上限：不能 OOM
        {"expr": "bcastOOM == 0", "label": "广播不 OOM（维表在广播上限内）"},
        # 上限：不允许多余 stage
        {"expr": "stages <= 2", "label": "stage ≤2（无 shuffle 边界）"},
    ],
    "insight": (
        "Spark join 的物理计划只有两条主路："
        "**sort-merge join**——两张表都按 join key 做 hash 重分区（shuffle），"
        "每个分区内排序再归并。代价是**两张大表都要过网络与磁盘**："
        "1TB 事实表 shuffle 就是 1TB 落盘 + 1TB 拉取，按 200MB/s 算要 85 分钟；"
        "**broadcast join**——把小表收成一个哈希表，**广播到每个 executor**，"
        "大表只需本地扫描（map 端 join），shuffle 为 0。本例耗时从 5322 秒降到 212 秒。"
        "广播的边界是**内存**：`spark.sql.autoBroadcastJoinThreshold` 默认 10MB，"
        "实际可调到 8GB 左右（再大每个 executor 都放不下，直接 OOM）。"
        "所以判据是「维表是否装得进 executor 内存」，不是「维表小不小」。"
        "三条配套优化："
        "① **统计信息**（`ANALYZE TABLE ... COMPUTE STATISTICS`）——"
        "Catalyst 靠它判断表大小，没有统计信息时可能选错策略（该广播的不广播，"
        "不该广播的硬广播）；"
        "② **AQE**（`spark.sql.adaptive.enabled=true`）：运行时发现某个分区特别大，"
        "自动拆分成更多分区（skew join 处理），把 1TB 里那个 300GB 的热点分区打散；"
        "③ **分桶 join**（`CLUSTERED BY ... INTO n BUCKETS` + 同桶数）："
        "两表已经按同样规则分桶时，**连 shuffle 都不需要**，直接按桶对齐做 merge。"
        "一句话记住：**能广播就广播，不能广播就分桶，都不行才 shuffle**。"
    ),
}


# ============================================================================
# bigdata/bd-ch06 · 60 个报表各扫一遍原始数据
# ----------------------------------------------------------------------------
# 教学点：不分层时每个报表直接查 ODS，扫 30% 原始数据 × 60 个报表 = 36TB/天；
# 分层后 ODS→DWD 只扫一次全量，60 个报表各扫 10GB 的 DWD 汇总表，
# 一天 2.6TB，成本从 1080 元降到 78 元。
# ============================================================================
bd_ch06 = {
    "kind": "sandbox",
    "title": "60 个报表各扫一遍原始数据",
    "brief": (
        "不建分层，每个报表都直接查 ODS 明细，各扫 30% 原始数据——"
        "60 个报表 × 2TB × 30% = 每天 36TB，光扫描费就 1080 元。"
        "分层之后 ODS→DWD 只扫一次全量，报表改查 10GB 的 DWS 汇总表，"
        "一天 2.6TB、78 元。把报表数、原始数据量与是否分层拖到真实值，"
        "看「建模」这件事的 ROI。"
    ),
    "params": [
        # 报表数
        {"key": "reports", "label": "报表/看板数量", "min": 1, "max": 200, "step": 1, "value": 60},
        # 原始数据量（GB）
        {"key": "odsGB", "label": "ODS 原始数据量", "min": 100, "max": 10000, "step": 100, "value": 2000},
        # 分层
        {"key": "layers", "label": "数仓分层", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["直连 ODS 明细", "ODS→DWD→DWS 分层"]},
    ],
    "metrics": [
        # 每天扫描量：不分层 = 每个报表各扫 30% 原始数据；分层 = ODS 扫一次 + 报表扫 DWS
        {"key": "dailyScanGB", "label": "每天扫描量", "expr": "if(layers == 1, odsGB + reports * 10, reports * odsGB * 30 / 100)", "unit": "GB", "fmt": "int"},
        # 换算 TB
        {"key": "dailyScanTB", "label": "每天扫描量（TB）", "expr": "dailyScanGB / 1024", "unit": "TB", "fmt": "int"},
        # 每天成本（每 TB 30 元）
        {"key": "dailyCost", "label": "每天扫描成本", "expr": "dailyScanGB / 1024 * 30", "unit": "元", "fmt": "int"},
        # 每天总机时（集群 5TB/小时）
        {"key": "runtimeH", "label": "每天总机时", "expr": "dailyScanGB / 1024 / 5", "unit": "小时", "fmt": "fix2"},
        # 复用倍数：一张 DWD 被多少报表复用
        {"key": "reuse", "label": "DWD 被复用次数", "expr": "if(layers == 1, reports, 0)", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        # 下限：30 个报表起，两三个报表不需要建模
        {"expr": "reports >= 30", "label": "报表数 ≥30（真实的数据团队规模）"},
        # 前提：数据量够大
        {"expr": "odsGB >= 1000", "label": "ODS ≥1TB（建模才有意义）"},
        # 上限：每天成本（不分层在最小规模下也要 290 元，过不了）
        {"expr": "dailyCost <= 150", "label": "每天扫描成本 ≤150 元"},
        # 上限：单次调度耗时要赶在下次调度前跑完
        {"expr": "runtimeH <= 8", "label": "每天总机时 ≤8 小时（调度窗口跑得完）"},
    ],
    "insight": (
        "数仓分层的本质不是「规范」，而是**把 N 次重复计算收敛成 1 次**："
        "不分层时每个报表都要自己从 ODS 明细里洗一遍（过滤、去重、维表关联），"
        "60 个报表就是 60 次同样的扫描——**36TB/天，其中 35TB 是重复劳动**。"
        "分层后的账：ODS→DWD 一天只跑一次（扫全量 2TB），"
        "DWD→DWS 按主题聚合成 100 个宽表（每个 10GB），"
        "报表直接查 DWS（60 × 10GB = 600GB）——**总量 2.6TB，省 93%**。"
        "四层的职责要分清，否则会退化成「分了很多层但每层都全量」："
        "**ODS**：贴源，只做抽取与格式统一，不洗数据（保留回溯能力）；"
        "**DWD**：明细，做清洗、去重、维度退化、统一口径（一行一个业务事件）；"
        "**DWS**：汇总，按主题 + 粒度预聚合（一行一个实体一天）；"
        "**ADS**：应用层，直接对着报表/接口的形态（可以宽表、可以冗余）。"
        "两条判据看分层做得好不好："
        "① **DWD 被复用次数**——一个 DWD 表只被一个报表用，等于没分层；"
        "② **单次调度能否在窗口内跑完**——分层后每个任务都变短，"
        "整条链路才能在 24 次调度里排得开（这也是「调度叠起来」的根因："
        "单个任务太长，前一天的还没跑完，第二天的又开始了）。"
        "最后一点：**分层不是越深越好**。每加一层就多一次落盘与调度依赖，"
        "中小团队 ODS→DWD→ADS 三层足够；层数多到 5 层时，"
        "排查「这个指标为什么不对」要跨 5 张表追血缘，运维成本反超收益。"
    ),
}


# ============================================================================
# data/data-ch03 · object 列 68 字节，category 只要 8 字节
# ----------------------------------------------------------------------------
# 教学点：pandas 的 object 列存的是 Python 字符串对象的指针（8 字节），
# 每个字符串还有 49 字节的 PyUnicode 头 + 内容，实测约 68 字节/行；
# category 存「整数码 + 字典」，8 字节/行。另外 iterrows 每行创建一个 Series
# （约 3μs），向量化操作是 20ns 级。
# ============================================================================
data_ch03 = {
    "kind": "sandbox",
    "title": "object 列 68 字节，category 只要 8 字节",
    "brief": (
        "一个 500 万行的订单表，城市列用 `object`（Python 字符串）要占 340MB，"
        "换成 `category`（整数码 + 字典）只要 38MB——因为 object 列存的只是指针，"
        "真正的字符串对象还各自带 49 字节的头。"
        "再加上 `iterrows` 逐行循环（每行造一个 Series，约 3 微秒），"
        "同样的清洗逻辑能从 15 秒变成 0.1 秒。"
        "把行数、列类型与遍历方式拖到真实值，看这两笔账。"
    ),
    "params": [
        # 行数（百万）
        {"key": "rowsM", "label": "数据行数（百万）", "min": 1, "max": 50, "step": 1, "value": 5},
        # 字符串列类型
        {"key": "dtype", "label": "字符串列类型", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["object（Python 字符串）", "category（字典编码）"]},
        # 遍历方式
        {"key": "loop", "label": "处理方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["iterrows 逐行", "向量化 / .str 访问器"]},
    ],
    "metrics": [
        {"key": "rows", "label": "数据行数", "expr": "rowsM * 1000000", "unit": "行", "fmt": "int"},
        # 每行该列占用：object 68 字节（8 指针 + 49 头 + 内容），category 8 字节（int32 码）
        {"key": "perRow", "label": "每行该列占用", "expr": "if(dtype == 0, 68, 8)", "unit": "字节", "fmt": "int"},
        # 该列内存
        {"key": "memMB", "label": "该列内存", "expr": "rowsM * 1000000 * if(dtype == 0, 68, 8) / 1048576", "unit": "MB", "fmt": "int"},
        # 每行处理耗时：iterrows 3μs（造 Series），向量化 20ns
        {"key": "nsPerRow", "label": "每行处理耗时", "expr": "if(loop == 0, 3000, 20)", "unit": "ns", "fmt": "int"},
        # 总处理耗时
        {"key": "totalS", "label": "处理耗时", "expr": "rowsM * 1000000 * if(loop == 0, 3000, 20) / 1000000000", "unit": "秒", "fmt": "fix2"},
        # 内存膨胀倍数
        {"key": "blowup", "label": "相对 category 膨胀", "expr": "if(dtype == 0, 9, 1)", "unit": "×", "fmt": "int"},
        # 是否吃满内存（按 8GB 可用算）
        {"key": "memPct", "label": "占 8GB 内存比例", "expr": "rowsM * 1000000 * if(dtype == 0, 68, 8) / 1048576 * 100 / 8192", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万行起，小表怎么存都无所谓
        {"expr": "rows >= 1000000", "label": "行数 ≥100 万（真实的分析表）"},
        # 上限：每行该列占用（object 68 字节过不了，必须换 category）
        {"expr": "perRow <= 20", "label": "每行该列 ≤20 字节（对象列要压到 8 字节）"},
        # 上限：该列内存
        {"expr": "memMB <= 100", "label": "字符串列 ≤100MB"},
        # 上限：处理耗时
        {"expr": "totalS <= 2", "label": "处理耗时 ≤2 秒"},
        # 上限：内存占比
        {"expr": "memPct <= 2", "label": "该列 ≤8GB 内存的 2%"},
    ],
    "insight": (
        "pandas 的 `object` 列是个**指针数组**：每行 8 字节指向一个 Python 字符串对象，"
        "而每个 `str` 对象自己还有约 49 字节的 `PyUnicodeObject` 头（引用计数、长度、hash、"
        "字符宽度标记）。所以「存一个 4 字的城市名」实际吃 68 字节。"
        "`category` 换成**字典编码**：内部维护一个唯一值数组，列里只存 int32 的码"
        "（8 字节/行，4 字节码 + 对齐），1000 个唯一值只占几 KB 的字典。"
        "本例 500 万行从 340MB 降到 38MB——而且 `groupby` 时**按码分组比按字符串哈希快得多**。"
        "什么时候该用：**唯一值比例 < 50%** 的列（城市、状态、品类、设备型号）都该转；"
        "唯一值接近行数（订单号、用户 id）时 category 反而更慢更占内存。"
        "第二笔账是遍历：`iterrows` 每行都会新建一个 `Series` 对象（约 3μs），"
        "1000 万行就是 30 秒；向量化写法（`.str.contains`、`np.where`、`df.loc` 掩码）"
        "在 C 层循环，每行 20ns，**快 150 倍**。"
        "四条实操："
        "① **先看 `df.info(memory_usage='deep')`**——`memory_usage` 默认不统计 object 里的字符串，"
        "会严重低估；"
        "② 读 CSV 时用 `dtype={'city':'category'}` 直接在读入阶段省内存；"
        "③ 别用 `iterrows`/`apply(axis=1)` 做能向量化的运算；"
        "④ 数值列用 `int32`/`float32`（`pd.to_numeric(..., downcast=...)`），"
        "大表下 8 字节→4 字节就是一半内存。"
    ),
}


# ============================================================================
# data/data-ch04 · merge 前不聚合，200 万行变 1000 万行
# ----------------------------------------------------------------------------
# 教学点：多个 `apply`/自定义函数无所谓，真正会爆的是 **一对多 merge**——
# 左表 200 万行按用户 id join 右表（每用户 5 条记录），结果直接放大到 1000 万行，
# 内存 200MB→1.9GB。正解是先把右表聚合到唯一键再 join。
# ============================================================================
data_ch04 = {
    "kind": "sandbox",
    "title": "merge 前不聚合，200 万行变 1000 万行",
    "brief": (
        "左表 200 万个订单，按 `user_id` join 右表（每个用户平均 5 条行为记录），"
        "结果直接放大成 1000 万行，内存从 380MB 涨到 1.9GB。"
        "这不是索引问题是**语义问题**：一对多 join 本来就会复制行。"
        "正解是先把右表聚合到「每个 user_id 一行」再 join。"
        "把行数、匹配倍数与处理方式拖到真实值，看行数是怎么被放大的。"
    ),
    "params": [
        # 左表行数（万）
        {"key": "leftM", "label": "左表行数（万）", "min": 10, "max": 1000, "step": 10, "value": 200},
        # 右表平均匹配数
        {"key": "fanout", "label": "右表每键平均匹配行数", "min": 1, "max": 20, "step": 1, "value": 5},
        # 处理方式
        {"key": "mode", "label": "join 前处理", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["直接 merge（一对多）", "右表先聚合到唯一键"]},
    ],
    "metrics": [
        {"key": "leftRows", "label": "左表行数", "expr": "leftM * 10000", "unit": "行", "fmt": "int"},
        # 结果行数：一对多会把左表行数乘以匹配数
        {"key": "resultRows", "label": "结果行数", "expr": "leftM * 10000 * if(mode == 0, fanout, 1)", "unit": "行", "fmt": "int"},
        # 放大倍数
        {"key": "blowup", "label": "行数放大", "expr": "if(mode == 0, fanout, 1)", "unit": "×", "fmt": "int"},
        # 结果内存（每行 200 字节）
        {"key": "memMB", "label": "结果内存", "expr": "leftM * 10000 * if(mode == 0, fanout, 1) * 200 / 1048576", "unit": "MB", "fmt": "int"},
        # 处理耗时（每行 0.5μs）
        {"key": "timeS", "label": "join+聚合耗时", "expr": "leftM * 10000 * if(mode == 0, fanout, 1) * 0.5 / 1000000", "unit": "秒", "fmt": "fix2"},
        # 聚合阶段的额外开销
        {"key": "aggCostS", "label": "预先聚合开销", "expr": "if(mode == 1, leftM * 10000 * fanout * 0.2 / 1000000, 0)", "unit": "秒", "fmt": "fix2"},
        # 下游还要处理多少行
        {"key": "downstreamRows", "label": "下游要处理行数", "expr": "leftM * 10000 * if(mode == 0, fanout, 1)", "unit": "行", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万行起，小表 explode 也无所谓
        {"expr": "leftRows >= 1000000", "label": "左表 ≥100 万行（真实的事实表）"},
        # 前提：右表确实是一对多
        {"expr": "fanout >= 2", "label": "右表每键 ≥2 行（一对多场景）"},
        # 上限：结果不许放大
        {"expr": "resultRows <= leftRows", "label": "结果行数不超过左表（先聚合到唯一键）"},
        # 上限：结果内存
        {"expr": "memMB <= 500", "label": "结果 ≤500MB"},
        # 上限：耗时
        {"expr": "timeS <= 2", "label": "join+聚合 ≤2 秒"},
    ],
    "insight": (
        "`merge` 的行数不是「左表行数」，而是 **`Σ(每个键在右表的匹配数)`**——"
        "一对一 join 不放大，一对多 join 按匹配数放大，多对多会**乘起来**放大"
        "（1000 行 × 1000 行共享一个键 = 100 万行）。"
        "本例 200 万 × 5 = 1000 万行，内存从 380MB 到 1.9GB，"
        "而且**下游的每一行都要重新算一遍**（聚合、排序、导出全部变慢）。"
        "三种正解，按推荐顺序："
        "① **先聚合再 join**：右表 `groupby('user_id').agg(orders=('id','count'), amount=('amt','sum'))` "
        "变成「一 user 一行」再 merge——本例多花 0.2 秒聚合，省掉 800 万行；"
        "② **用 `merge(..., validate='m:1')` 让 pandas 帮你查基数**："
        "声明右表是「多对一」的唯一侧，基数不符直接抛 `MergeError`，"
        "把「悄悄放大」变成「当场失败」——**这是最该养成的习惯**；"
        "③ 只想「带一个标量过来」时用 `map`（`df['city'] = df.user_id.map(city_map)`），"
        "不产生中间表，也不会放大。"
        "另外两个常见爆点："
        "**`groupby.apply` 返回 DataFrame** 会触发 `FutureWarning` 并重建索引（慢 10 倍），"
        "能用内置 `agg` 就别用 `apply`；"
        "**时间序列 `resample` 后的 `asfreq`/`ffill`** 在高频数据上会把稀疏表填成稠密表，"
        "内存按「时间跨度 × 频率」增长，而不是按原始行数。"
    ),
}


# ============================================================================
# data/data-ch05 · 一万页串行爬，五十分钟
# ----------------------------------------------------------------------------
# 教学点：10000 页 × 300ms 串行 = 50 分钟；并发能压到理论值，但并发上限由
# 「站点限速 × 单请求耗时」决定（Little 定律）——限速 50 QPS、单请求 300ms，
# 在途请求最多 15 个，开 32 并发只会在服务端排队甚至被封。
# ============================================================================
data_ch05 = {
    "kind": "sandbox",
    "title": "一万页串行爬，五十分钟",
    "brief": (
        "10000 个页面、每页 300ms，串行抓要 50 分钟。"
        "并发能把它压下来，但**并发数不是越大越好**：站点限速 50 QPS、"
        "单请求 300ms 时，同时在途的请求最多 15 个（Little 定律），"
        "开 32 并发只会让请求在服务端排队、甚至触发封禁。"
        "把页数、并发、响应耗时与限速拖到真实值，找那个「不超限又能跑完」的并发数。"
    ),
    "params": [
        # 页面数
        {"key": "pages", "label": "页面数", "min": 100, "max": 100000, "step": 100, "value": 10000},
        # 并发数
        {"key": "conc", "label": "并发数", "min": 1, "max": 64, "step": 1, "value": 1},
        # 单页响应耗时（ms）
        {"key": "rttMs", "label": "单页响应耗时", "min": 50, "max": 2000, "step": 50, "value": 300},
        # 站点限速（QPS）
        {"key": "limitQps", "label": "站点限速（QPS）", "min": 1, "max": 200, "step": 1, "value": 50},
    ],
    "metrics": [
        # 串行耗时
        {"key": "serialS", "label": "串行耗时", "expr": "pages * rttMs / 1000", "unit": "秒", "fmt": "int"},
        # 并发理论耗时（不考虑限速）
        {"key": "idealS", "label": "并发理论耗时", "expr": "pages * rttMs / 1000 / conc", "unit": "秒", "fmt": "int"},
        # 限速下限：至少需要 pages / limitQps 秒
        {"key": "limitS", "label": "限速决定的下限", "expr": "pages / limitQps", "unit": "秒", "fmt": "int"},
        # 实际耗时 = 两者取大
        {"key": "actualS", "label": "实际耗时", "expr": "max(pages * rttMs / 1000 / conc, pages / limitQps)", "unit": "秒", "fmt": "int"},
        # 实际 QPS
        {"key": "actualQps", "label": "实际 QPS", "expr": "pages / max(pages * rttMs / 1000 / conc, pages / limitQps)", "unit": "QPS", "fmt": "fix2"},
        # 不超限的最大并发（Little 定律：在途 = QPS × 耗时）
        {"key": "maxConc", "label": "不超限的最大并发", "expr": "limitQps * rttMs / 1000", "unit": "个", "fmt": "int"},
        # 并发是否浪费
        {"key": "wasted", "label": "超出限速的并发数", "expr": "max(0, conc - limitQps * rttMs / 1000)", "unit": "个", "fmt": "int"},
    ],
    "checks": [
        # 下限：5000 页起，抓几十页串行也无所谓
        {"expr": "pages >= 5000", "label": "页面数 ≥5000"},
        # 上限：总耗时
        {"expr": "actualS <= 600", "label": "总耗时 ≤600 秒（10 分钟）"},
        # 前提：真实站点响应在 200ms 以上（别把 rtt 拖到 50ms 蒙过去）
        {"expr": "rttMs >= 200", "label": "单页响应 ≥200ms（真实站点的响应时间）"},
        # 前提：站点限速不会很高（一般 10~60 QPS）
        {"expr": "limitQps <= 60", "label": "站点限速 ≤60 QPS"},
        # 上限：并发不超过「限速 × 耗时」算出的在途上限
        {"expr": "conc <= limitQps * rttMs / 1000", "label": "并发 ≤限速允许的在途数（Little 定律）"},
        # 上限：实际 QPS 不超限
        {"expr": "actualQps <= limitQps", "label": "实际 QPS ≤站点限速"},
        # 下限：真的并发了
        {"expr": "conc >= 4", "label": "并发 ≥4（串行跑不完）"},
    ],
    "insight": (
        "采集的耗时模型只有两行：**串行 `N × RTT`**，**并发 `max(N × RTT / C, N / QPS_limit)`**。"
        "第二项是很多人忽略的：**限速是硬约束，并发再大也跑不过它**。"
        "本例 10000 页 × 300ms = 50 分钟串行；并发 15 时理论 200 秒，"
        "但限速 50 QPS 决定了至少 200 秒——两个下限刚好重合。"
        "**「不超限的最大并发」= 限速 × 单请求耗时**（Little 定律的采集版）："
        "50 QPS × 0.3s = 15 个在途。开 16 个时第 16 个请求只会在服务端排队，"
        "开 32 个时服务端看到的是「瞬时 100 QPS 的突发」，轻则 429，重则封 IP。"
        "三条工程纪律："
        "① **用令牌桶/信号量做客户端限速**（`aiohttp` 的 `Semaphore` + "
        "`asyncio.sleep` 补速率），别指望「并发数 = 限速」这种巧合；"
        "② **一定要有退避重试**（指数退避 + 抖动），429/503 时退到 1 QPS 等一分钟，"
        "比硬刚被封 IP 划算得多；"
        "③ **先看 `robots.txt` 与《数据安全法》《个人信息保护法》的边界**："
        "公开数据也要遵守站点条款与抓取频率，绕过反爬、抓个人信息、"
        "抓完转卖都可能直接违法——**合规成本远高于技术成本**。"
        "顺带一句性能细节：串行的 300ms 里大部分是**等待 IO**（不是 CPU），"
        "所以异步（`aiohttp`/`httpx.AsyncClient`）比多线程更省资源；"
        "CPU 密集的解析（HTML→结构化）反而该放进线程池，别堵住事件循环。"
    ),
}


# ============================================================================
# data/data-ch06 · 网格搜索 5000 次训练，跑两周
# ----------------------------------------------------------------------------
# 教学点：网格搜索的代价是**组合数 × CV 折数 × 单次训练时间**，三个因子相乘。
# 1000 组参数 × 5 折 × 30 秒 = 41.7 小时；8 核并行降到 5.2 小时。
# 正确做法是先随机搜索/贝叶斯搜索缩小范围，再在小网格上精调。
# ============================================================================
data_ch06 = {
    "kind": "sandbox",
    "title": "网格搜索 5000 次训练，跑两周",
    "brief": (
        "网格搜索的代价是三个因子**相乘**：组合数 × CV 折数 × 单次训练时间。"
        "1000 组参数 × 5 折 × 30 秒 = 41.7 小时，一周的算力就这么没了；"
        "开 8 核并行降到 5.2 小时，但更有效的做法是先随机搜索把范围缩小。"
        "把组合数、折数、单次训练时间与并行度拖到真实值，"
        "看「调参」这笔算力账。"
    ),
    "params": [
        # 参数组合数
        {"key": "combos", "label": "参数组合数", "min": 4, "max": 5000, "step": 4, "value": 1000},
        # CV 折数
        {"key": "folds", "label": "交叉验证折数", "min": 3, "max": 10, "step": 1, "value": 5},
        # 单次训练耗时（秒）
        {"key": "oneTrainS", "label": "单次训练耗时（秒）", "min": 1, "max": 300, "step": 1, "value": 30},
        # 并行度
        {"key": "parallel", "label": "并行核数", "min": 1, "max": 64, "step": 1, "value": 1},
    ],
    "metrics": [
        # 总训练次数
        {"key": "fitCount", "label": "总训练次数", "expr": "combos * folds", "unit": "次", "fmt": "int"},
        # 串行耗时（小时）
        {"key": "serialH", "label": "串行耗时", "expr": "combos * folds * oneTrainS / 3600", "unit": "小时", "fmt": "fix2"},
        # 并行后的墙钟时间（小时）
        {"key": "wallH", "label": "并行后墙钟时间", "expr": "combos * folds * oneTrainS / 3600 / parallel", "unit": "小时", "fmt": "fix2"},
        # 随机搜索 60 组的耗时（对比）
        {"key": "randomH", "label": "随机搜索 60 组耗时", "expr": "60 * folds * oneTrainS / 3600 / parallel", "unit": "小时", "fmt": "fix2"},
        # 训练次数相对随机搜索的倍数
        {"key": "gridVsRandom", "label": "网格/随机 次数比", "expr": "combos / 60", "unit": "×", "fmt": "int"},
        # 改随机搜索能省下的墙钟时间
        {"key": "savedH", "label": "改随机搜索可省", "expr": "combos * folds * oneTrainS / 3600 / parallel - 60 * folds * oneTrainS / 3600 / parallel", "unit": "小时", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：200 组起，小网格怎么搜都行
        {"expr": "combos >= 200", "label": "参数组合 ≥200 组（真实的调参规模）"},
        # 前提：单次训练不能太便宜（否则调参不是瓶颈）
        {"expr": "oneTrainS >= 10", "label": "单次训练 ≥10 秒（中等模型）"},
        # 上限：墙钟时间
        {"expr": "wallH <= 8", "label": "调参墙钟时间 ≤8 小时（一夜能跑完）"},
        # 下限：并行度（要真的用上多核）
        {"expr": "parallel >= 4", "label": "并行 ≥4 核"},
    ],
    "insight": (
        "调参的算力账是**三个因子相乘**：`组合数 × 折数 × 单次训练时间`。"
        "很多人只盯「组合数」，但折数从 5 加到 10 就是翻倍，"
        "单次训练从 30 秒涨到 5 分钟就是 10 倍——**乘积才是账单**。"
        "本例 1000 × 5 × 30 秒 = 41.7 小时，8 核并行 5.2 小时。"
        "降低这笔账的四个杠杆，按性价比排序："
        "① **先随机搜索/贝叶斯搜索**（`RandomizedSearchCV` + `HalvingRandomSearchCV`）："
        "60 组随机样本通常能找到网格 1000 组里 90% 的好区域，"
        "**成本降到 1/16**，再在那个小区域做精调；"
        "② **早停 / 逐次减半**（successive halving）：先在小数据/少轮次上跑所有组合，"
        "淘汰差的，只对好的跑全量——`HalvingGridSearchCV` 就是干这个的；"
        "③ **并行**：`n_jobs=-1` 几乎是免费的加速，但要注意 "
        "**每个 fold 内的模型自己也可能开多线程**（BLAS/OpenMP），"
        "会互相抢核，实测 `n_jobs=8` 配 `OMP_NUM_THREADS=1` 通常比 `n_jobs=-1` 更快；"
        "④ **缩小验证成本**：5 折已经够用，10 折的收益远小于 2 倍成本；"
        "大数据集上用 `train_test_split` + 单次验证先粗筛，最后才上 CV。"
        "还有一条容易被忽略的：**别在测试集上调参**。"
        "CV 是在训练集内部做模型选择，最终只在**留出的测试集**上评估一次——"
        "同一份数据既调参又评估，指标会系统性偏高（数据泄漏的一种）。"
    ),
}


MODULES = {
    "middleware/mw-ch01": mw_ch01,
    "middleware/mw-ch02": mw_ch02,
    "middleware/mw-ch04": mw_ch04,
    "middleware/mw-ch06": mw_ch06,
    "middleware/mw-ch07": mw_ch07,
    "middleware/mw-ch08": mw_ch08,
    "bigdata/bd-ch01": bd_ch01,
    "bigdata/bd-ch03": bd_ch03,
    "bigdata/bd-ch05": bd_ch05,
    "bigdata/bd-ch06": bd_ch06,
    "data/data-ch03": data_ch03,
    "data/data-ch04": data_ch04,
    "data/data-ch05": data_ch05,
    "data/data-ch06": data_ch06,
}


def main() -> int:
    """读取 labs.json → 写入 14 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<22} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
