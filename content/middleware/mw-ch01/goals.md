# 学习目标 · Redis 数据结构与底层编码（mw-ch01）

> 学科：`middleware` · 分组：M1 Redis 原理
> 配套资源：《Redis 设计与实现》第 1-2 章、《Redis 深度历险》。本章聚焦「Redis 对象类型 ↔ 底层编码」的映射关系与从零模拟。

完成本章后，读者应能：

1. **说清五种顶层对象类型与底层编码的映射**：String / List / Hash / Set / ZSet 各自在何种条件下选用 int、embstr、raw、listpack（ziplist）、quicklist、hashtable、intset、skiplist+dict 等编码，并记住关键阈值（如 `hash-max-listpack-entries`、`zset-max-listpack-value`、`set-max-intset-entries`）。
2. **对比 SDS 与 C 字符串**：理解长度前缀、`O(1)` 长度获取、二进制安全、惰性删除与空间预分配（`alloc`/`len`/`free`）带来的写入放大优化与内存换时间权衡。
3. **理解字典的渐进式 rehash**：为什么 Redis 不在一次命令里把整张表搬完，而是分散到每次增删改查与定时任务中，避免长尾延迟。
4. **从零实现一个迷你 Redis 内核**：用 Python 模拟 SDS、dict 渐进 rehash、listpack 编码阈值、intset 升级、skiplist 跳表、quicklist 与 bitmap 的字节布局，并能打印真实结构状态。
5. **掌握笔试/面试高频口径**：Object Encoding 判定、ziplist 连锁更新、intset 编码升级、跳表层数概率、String 44 字节 embstr 分界等，能给出标准答法与易错点。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §1.2 String 对象的三种编码 | 读 `docs/database/redis/` 的底层数据结构篇：`int`/`embstr`/`raw` 的分界点是 44 字节，embstr 与 redisObject 一次分配、raw 两次——这解释了「45 字节的 key 比 44 字节多一次内存分配」，也是 §4.2 类型/编码系统的最小样本 |
| 2 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §4.1 dict：渐进式 rehash（不阻塞的单线程友好设计） | 对照 `docs/high-concurrency/` 的 Redis 系列：`ht[0]`/`ht[1]` 双表 + `rehashidx` 游标 + 每次操作搬一个桶，把 O(n) 的扩容摊到多次操作上；这也是 §3.2 ZSet 为什么要「skiplist + dict」双结构——dict 负责 O(1) 查分，skiplist 负责范围 |
| 3 | [redis/redis](https://github.com/redis/redis) | 77,127 | §1.1 SDS：Redis 的二进制安全字符串 | 读 `src/sds.c`：`sdsnewlen` 按长度分 sdshdr5/8/16/32/64 五种头部、`len`/`alloc` 两个字段让取长度变成 O(1)、`sdscatlen` 按需预分配——三处细节合起来就是「二进制安全 + 免 strlen」的完整答案 |
| 4 | [apache/kafka](https://github.com/apache/kafka) | 34,105 | §3.2 ZSet：listpack 与 skiplist + dict 双结构 | 读 `src/t_zset.c` 的 `zaddGenericCommand`：元素少且短时用 listpack 省内存，超过 `zset-max-listpack-entries` 就转 skiplist；这一条正好对应 §2.2 Hash 的编码切换阈值——两处共同构成「小对象紧凑、大对象随机访问」的取舍 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Redis 入门到实战<br><sub>黑马程序员</sub> | [BV1cr4y1671t](https://www.bilibili.com/video/BV1cr4y1671t/) | §1.1 ① SDS | 主线课：数据结构与底层编码 → 持久化 → 主从/哨兵/集群 → 缓存三大问题与分布式锁；看完回 `ex01_sds_dynamic_string`（SDS 动态字符串）核对 |
| 2 | 尚硅谷 · Kafka 3.x 从入门到调优<br><sub>尚硅谷</sub> | [BV1vr4y1677k](https://www.bilibili.com/video/BV1vr4y1677k/) | 全章 | 比入门版多了调优与运维：ISR、HW/LEO、日志段与零拷贝、积压排查；看完回 `ex02_dict_incremental_rehash`（dict 渐进式 rehash）核对 |
| 3 | 尚硅谷 · RabbitMQ 消息队列<br><sub>尚硅谷</sub> | [BV1cb4y1o7zz](https://www.bilibili.com/video/BV1cb4y1o7zz/) | 全章 | 交换机类型、确认机制与死信队列；做选型对比时用它补齐「非日志型 MQ」的视角；看完回 `ex03_string_object_encoding`（String 对象编码判定）核对 |
| 4 | 尚硅谷 · Kafka 快速入门<br><sub>尚硅谷</sub> | [BV1a4411B7V9](https://www.bilibili.com/video/BV1a4411B7V9/) | 全章 | Topic/Partition/Replica 模型、生产者与消费者、位移提交；讲清「顺序性只在分区内成立」；看完回 `ex04_hash_encoding`（Hash 编码切换）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Redis 设计与实现》黄健宏 |
| 2 | 《Kafka 权威指南》Narkhede 等 |
| 3 | 《数据密集型应用系统设计》Kleppmann |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
