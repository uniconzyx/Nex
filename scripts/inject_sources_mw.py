# -*- coding: utf-8 -*-
"""middleware 学科来源锚点重写（批次 M1，8 章 32 条）。

依据：逐章 grep concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
每条格式：`§x.y 小节标题 · 读什么`（分隔符为前后各一空格的中间点）。

本批除了编号错位，还清了三条「跑题」条目：
  mw-ch04#3 原讲「过期与淘汰」，属 mw-ch02 的内容，本章讲缓存设计 → 换成缓存一致性
  mw-ch01#4 原拿 Kafka 集合实现凑数，与本章编码切换无关      → 换成 skiplist 结构
  mw-ch07#3 原拿 Redis 落盘对比，与「存储端不丢」隔一层        → 换成副本/ISR
"""
import json
import os
import re

MANIFEST = "content/middleware/_manifest.json"
CH_DIR = "content/middleware"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，须框定范围）。"""
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- mw-ch01 Redis 数据结构与底层编码 ----------------
    "mw-ch01": [
        "§1.2 String 对象的三种编码 · 读 `docs/database/redis/` 的底层数据结构篇："
        "`int`/`embstr`/`raw` 的分界点是 44 字节，embstr 与 redisObject 一次分配、raw 两次"
        "——这解释了「45 字节的 key 比 44 字节多一次内存分配」，也是 §4.2 类型/编码系统的最小样本",

        "§4.1 dict：渐进式 rehash（不阻塞的单线程友好设计） · 对照 `docs/high-concurrency/` 的 Redis 系列："
        "`ht[0]`/`ht[1]` 双表 + `rehashidx` 游标 + 每次操作搬一个桶，把 O(n) 的扩容摊到多次操作上；"
        "这也是 §3.2 ZSet 为什么要「skiplist + dict」双结构——dict 负责 O(1) 查分，skiplist 负责范围",

        "§1.1 SDS：Redis 的二进制安全字符串 · 读 `src/sds.c`："
        "`sdsnewlen` 按长度分 sdshdr5/8/16/32/64 五种头部、`len`/`alloc` 两个字段让取长度变成 O(1)、"
        "`sdscatlen` 按需预分配——三处细节合起来就是「二进制安全 + 免 strlen」的完整答案",

        "§3.2 ZSet：listpack 与 skiplist + dict 双结构 · 读 `src/t_zset.c` 的 `zaddGenericCommand`："
        "元素少且短时用 listpack 省内存，超过 `zset-max-listpack-entries` 就转 skiplist；"
        "这一条正好对应 §2.2 Hash 的编码切换阈值——两处共同构成「小对象紧凑、大对象随机访问」的取舍",
    ],
    # ---------------- mw-ch02 Redis 持久化与内存管理 ----------------
    "mw-ch02": [
        "§2.2 AOF 重写（rewrite）与混合持久化 · 读 `docs/database/redis/` 的持久化篇："
        "重写不是读旧 AOF，而是「按当前内存状态生成最小命令集」，因此重写后的文件与历史无关"
        "——这也解释了 §2.1 `appendfsync` 三策略与重写为什么是两件独立的事：一个管安全，一个管体积",

        "§3.2 内存淘汰、maxmemory 与碎片管理 · 对照 `docs/high-concurrency/` 的 Redis 内存篇："
        "`maxmemory-policy` 的八种策略里 `allkeys-lru` 与 `volatile-lru` 的差别是「要不要保护无 TTL 的键」；"
        "配合 §3.1 惰性删除 + 定期删除两条腿，才能解释「内存没满但淘汰频繁」这类现场",

        "§1.1 RDB 快照与 fork + 写时复制（COW） · 读 `src/rdb.c` 的 `rdbSaveBackground`："
        "`fork()` 之后子进程持有快照视图，父进程写入触发缺页复制"
        "——「fork 瞬间内存翻倍」不是估算，而是 COW 的必然代价，也是 §1.2 `save m n` 触发频率的调优依据",

        "§2.1 AOF 追加与 appendfsync 三策略 · 对照 `core/src/main/scala/kafka/log/Log.scala`："
        "Kafka 用「追加日志 + 段文件」实现持久化，与 AOF 的 append-only 同源，"
        "区别在于 Kafka 靠「保留策略」删除旧段而不是重写；比对两者「什么时候算写成功」，"
        "就明白 `everysec` 与 `always` 的取舍本质",
    ],
    # ---------------- mw-ch03 Redis 高可用 ----------------
    "mw-ch03": [
        "§2.1 主观下线 SDOWN 与客观下线 ODOWN（quorum 投票） · 读 `docs/database/redis/` 的高可用篇："
        "单个哨兵判 SDOWN 只是「我觉得」，凑够 quorum 才升 ODOWN，"
        "`majority` 与 `quorum` 是两个不同的数——配错就会「以为三个哨兵就安全」，"
        "这正是 §2.2 选主前必须先满足的门槛",

        "§3.3 脑裂（split-brain）与 min-replicas 防护 · 对照 `docs/high-concurrency/` 的 Redis 集群文章："
        "老主库网络分区后仍接受写入，恢复时这部分数据被覆盖，"
        "`min-replicas-to-write` 用「写成功必须至少 N 个从库确认」把风险压到配置层面；"
        "配合 §3.1 的 MOVED/ASK 重定向，能看清「分区期间客户端被导向哪边」",

        "§1.2 部分同步 repl_backlog、offset 与心跳 REPLCONF ACK · 读 `src/replication.c`："
        "`repl_backlog` 环形缓冲区 + `master_repl_offset` 让「断线重连只补差额」成为可能，"
        "缓冲区太小就只能退回 §1.1 的全量同步——这是「主从频繁全量」的第一排查点",

        "§2.2 Raft 式 leader 选举与故障转移的选主规则 · 对照 `core/src/main/scala/kafka/controller/` 的选举逻辑："
        "Kafka 用 Controller + ZK/KRaft 选 leader，Redis Sentinel 用 Raft 式投票，"
        "两者的共同前提都是「多数派还活着」；差别在 Kafka 的 ISR 限制候选范围，"
        "而 Sentinel 靠 `replica-priority` 打分",
    ],
    # ---------------- mw-ch04 缓存设计与三大经典问题 ----------------
    "mw-ch04": [
        "§1.1 布隆过滤器：用极少空间做「存在性」拦截 · 读 `docs/database/redis/` 的缓存专题："
        "穿透 / 击穿 / 雪崩三者的触发条件不同（不存在 / 热点失效 / 批量同时失效），"
        "解法也不同（布隆 + 空值缓存 / 互斥重建 / TTL 抖动）；"
        "混着答是面试扣分点——先按 §1.2 与 §2.1、§2.2 把三者的边界分清楚",

        "§3.1 Cache-Aside 的两种写顺序与并发脏数据 · 对照 `docs/high-concurrency/` 的缓存一致性文章："
        "并发下「读请求把旧值写回缓存」的窗口无法完全消除，"
        "延迟双删只能降低概率，强一致必须加锁或串行化；读完再回 §3.2 看 Write-Through 为什么把窗口挪到写侧",

        "§2.1 缓存击穿：一个热点 key 过期瞬间被海量并发打穿 · 读 `src/dict.c` 的 `lookupKey` 与 "
        "`dictAddRaw`：Redis 单命令原子但不提供「查不到就加锁重建」这种复合语义，"
        "所以互斥重建必须在客户端或 Lua 脚本里做——这正是 §2.2 雪崩要用「TTL 抖动」而非同一把锁的原因",

        "§3.2 三大更新策略：Write-Through / Write-Behind / 延迟双删 · 对照 `core/src/main/scala/kafka/log/Log.scala`："
        "Kafka 的页缓存在「写入即对读者可见」这一点上相当于 Write-Through，"
        "代价是写放大；把它和 §3.1 的 Cache-Aside 并排看，"
        "就是「一致性强度 ↔ 写延迟 ↔ 实现复杂度」的三角权衡",
    ],
    # ---------------- mw-ch05 Kafka 架构 ----------------
    "mw-ch05": [
        "§2.2 ISR 与 acks：把「不丢」写成可验证的条件 · 读 `docs/database/kafka/` 的副本篇："
        "`acks=all` 只是「等 ISR 全部确认」，还要配 `min.insync.replicas` 才有意义"
        "——只设前者，ISR 缩到一个副本时等于 `acks=1`；这正是 §2.3 LEO/HW/LSO 三个 offset 的判据落地",

        "§4.1 消费者组与 rebalance · 对照 `docs/high-concurrency/` 的消息队列文章："
        "rebalance 期间全组停止消费，`session.timeout.ms` 与 `max.poll.interval.ms` 配小了会「反复踢人」，"
        "这是「消费明明没挂却一直 rebalance」的根因；回答它要回 §4.2 看分配策略是否 Sticky",

        "§3.2 零拷贝与页缓存：为什么 Kafka 能跑到百万级 · 对照 `src/networking.c` 的 `writev`/`sendfile` 用法："
        "Redis 与 Kafka 都靠「不让数据经过用户态」省掉两次拷贝，"
        "区别在于 Kafka 还叠加了 §3.1 的段文件稀疏索引与批量发送",

        "§1.2 Topic / Partition / Offset：逻辑与物理的分离 · 读 `core/src/main/scala/kafka/log/Log.scala`："
        "每个分区就是一个 append-only 的段文件序列，消费位点只是「读到哪个 offset」，"
        "所以消息可以被多个消费者组各自重放——这是「日志」与「队列」的本质差别，"
        "也是 §1.3 分区数决定并行度的原因",
    ],
    # ---------------- mw-ch06 Kafka 生产者与消费者 ----------------
    "mw-ch06": [
        "§2.3 幂等生产者与事务 · 读 `docs/database/kafka/` 的生产者篇："
        "PID + 序列号让 broker 能识别「同一会话内的重试」，但它只管单分区单会话，"
        "跨会话仍会重复，所以业务幂等仍不可省；对照 §2.1 三档 acks 各自的丢失窗口，"
        "就明白幂等与不丢是两套正交的保障",

        "§4.1 位移提交的四种方式 · 对照 `docs/high-concurrency/` 的 Kafka 消费篇："
        "自动提交是「按时间」、手动提交是「按处理进度」，前者在 rebalance 时会重复消费一批"
        "——「至少一次」的重复量级就由这个选择决定；配合 §4.2 三种交付语义，"
        "就能把「重复多少」算成一个区间而不是一句形容词",

        "§2.2 min.insync.replicas：与 acks=all 的配合 · 对照 `src/db.c` 的 `setKey` 覆盖语义："
        "Redis 的写是「后写覆盖」，天然不产生重复，但也不保证「已确认的写还在」；"
        "Kafka 用 min.insync.replicas 把「至少几个副本写成功才回 ACK」显式化，"
        "是两种截然不同的「成功」定义",

        "§1.3 发送链路：从 send() 到 Broker · 读 `clients/src/main/java/org/apache/kafka/clients/producer/KafkaProducer.java` "
        "与 `internals/Sender.java`：消息先进 `RecordAccumulator` 按分区攒批，Sender 线程按 broker 聚合请求"
        "——「batch.size 与 linger.ms 决定吞吐」就发生在这两层，"
        "对应 §1.2 攒批与吞吐那一节的算式",
    ],
    # ---------------- mw-ch07 消息可靠性 ----------------
    "mw-ch07": [
        "§3.1 三种「顺序」必须先分清 · 读 `docs/database/kafka/` 的顺序篇："
        "分区内有序、分区之间无序、跨 topic 更无序，"
        "所谓「保证顺序」永远要附加「在哪个范围内」这个限定语；"
        "弄清这条再读 §3.2，才能判断顺序是在生产、传输、重试还是消费哪一环被打破",

        "§4.1 事务消息买到了什么、没买到什么 · 对照 `docs/high-concurrency/` 的分布式事务文章："
        "Kafka 事务只保证「多条消息原子写入 + 消费端读已提交」，它不保证「业务操作与发消息」的原子性，"
        "后者要靠本地消息表或 Outbox；这正是 §4.2 重试策略必须区分「可重试/不可重试」的原因",

        "§1.2 存储端：副本、ISR 与「少数派当选」 · 对照 `src/rdb.c` 与 `src/aof.c` 的落盘时机："
        "Redis 的 `appendfsync everysec` 最多丢 1 秒，Kafka 的 `acks=all` 不丢已确认消息"
        "——「不丢」的强度取决于「什么时候算成功」；两者都把答案写在配置里而不是实现里",

        "§2.1 重复从哪里来：四个不变的来源 · 读 `internals/Sender.java` 的重试分支："
        "网络超时后重发、但 broker 其实已写入，这是「生产者侧重复」的典型来源；"
        "`enable.idempotence=true` 用序列号把这类重复挡在 broker 侧，"
        "而 §2.2 的幂等三件套负责挡住剩下的三种",
    ],
    # ---------------- mw-ch08 消息队列选型 ----------------
    "mw-ch08": [
        "§1.1 三大价值：削峰填谷、系统解耦、异步化 · 读 `docs/database/kafka/` 的入门篇："
        "三者都成立的前提是「允许最终一致」，如果业务要求强一致，"
        "引入 MQ 只会把问题变成「分布式事务」；读完再回 §1.2 四类新增复杂度，"
        "就知道代价具体压在谁身上",

        "§2.1 五个维度的对比框架 · 对照 `docs/high-concurrency/` 的消息队列对比文章："
        "吞吐（Kafka/RocketMQ 高）、路由灵活度（RabbitMQ 强）、事务与延迟消息（RocketMQ 有）"
        "——先过硬约束再加权打分，不要一上来比 benchmark；"
        "这正是 §2.3 选型判据的顺序，也是 §2.2 路由能力单独成节的理由",

        "§1.3 边界：什么时候用 Redis Stream / DB 轮询 / 同步 RPC 反而更合适 · 对照 `src/t_stream.c`："
        "Stream 有消费组与 ACK，但没有分区与副本，「轻量队列」够用；"
        "一旦要「百万级积压 + 多副本」，就超出它的设计边界——那条边界正好对应 §3.2 的分区数上限",

        "§3.1 积压的数学：四个变量 · 读 `core/src/main/scala/kafka/log/Log.scala` 的分区模型："
        "单个分区只能被一个消费者消费，所以「加消费者」的上限就是分区数"
        "——积压时先扩分区再扩实例，顺序反了就白扩；"
        "把这条带进 §3.3 的容量规划，就能算出「多久清完」而不是只说「要扩容」",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    data = json.load(open(MANIFEST, encoding="utf-8"))

    done = 0
    changed = False
    for ch in data.get("chapters", []):
        cid = ch.get("id")
        if cid not in NOTES:
            continue
        new = NOTES[cid]
        res = ch.setdefault("resources", {})
        old = res.get("github_notes", [])
        if len(old) != len(new):
            print(f"!! {cid} 原 {len(old)} 条、新 {len(new)} 条，不匹配，跳过")
            continue
        if old != new:
            res["github_notes"] = new
            changed = True
        done += 1
        ok, msg = rewrite_goals_table(cid, new)
        print(f"{'OK ' if ok else '!! '}{cid}: notes {len(new)} 条｜{msg}")

    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"manifest 已写盘（{done} 章）")
    else:
        print(f"manifest 已是目标状态（{done} 章），未写盘")


if __name__ == "__main__":
    main()
