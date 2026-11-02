# 学习目标 · Redis 持久化与内存管理（mw-ch02）

> 学科：`middleware` · 分组：M1 Redis 原理
> 配套资源：《Redis 设计与实现》第 4-5 章。本章聚焦「持久化（RDB/AOF）」与「内存管理（过期/淘汰/碎片/编码）」两大主题，并用 Python 从零模拟核心机制、打印真实结果。

完成本章后，读者应能：

1. **讲清 RDB 的 fork + 写时复制（COW）**：理解 BGSAVE/BGREWRITEAOF 为什么要 fork 子进程、COW 如何让子进程拿到一致性快照而父进程写入不被看见、fork 的代价为何是 O(页表) 而非 O(数据量)，以及 `save m n` 多条件触发规则。
2. **对比 AOF 三种 appendfsync 策略**：always / everysec / no 在「耐久性 vs 吞吐」上的取舍；理解 AOF 重写（rewrite）如何抵消冗余命令缩小体积；混合持久化（RDB 头 + AOF 增量尾）如何兼顾快速加载与低丢失。
3. **掌握过期键删除两大策略**：惰性删除（访问时才删，省 CPU）与定期删除（每秒多次、每次随机采样少量 key，平衡回收），以及二者如何配合避免大量 key 同时过期拖垮 CPU。
4. **理解内存淘汰与 maxmemory**：八种 `maxmemory-policy` 的语义与选型；Redis 用「随机采样近似 LRU/LFU」而非全局严格算法的原因；`mem_fragmentation_ratio` 的含义与异常处置；big key 与内存编码转换（int/embstr/raw）对内存的影响。
5. **从零模拟并实测**：用 Python 实现 RDB fork-COW、save 规则、AOF 三策略、AOF 重写/混合、惰性+定期过期、近似 LRU/LFU、碎片率计算，并能打印真实运行结果（见 examples/）。
6. **掌握笔试/面试高频口径**：RDB vs AOF 选型、COW 机制、AOF 重写与混合持久化、过期删除、近似 LRU 的随机采样思想、碎片率异常等，能给出标准答法与易错点。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §2.2 | 讲「AOF 重写」时读 `docs/database/redis/` 的持久化篇：重写不是读旧 AOF，而是「按当前内存状态生成最小命令集」，因此重写后的文件与历史无关——这也解释了混合持久化为什么能兼顾恢复速度与安全性 |
| 2 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §3.1 | 讲「过期键删除与淘汰」时对照 `docs/high-concurrency/` 的 Redis 内存篇：惰性删除 + 定期删除两条腿走路，`maxmemory-policy` 的八种策略里 `allkeys-lru` 与 `volatile-lru` 的差别是「要不要保护无 TTL 的键」 |
| 3 | [redis/redis](https://github.com/redis/redis) | 77,127 | §1.1 | 讲「RDB 与 fork + COW」时读 `src/rdb.c` 的 `rdbSaveBackground`：`fork()` 之后子进程持有快照视图，父进程写入触发缺页复制——「fork 瞬间内存翻倍」不是估算，而是 COW 的必然代价 |
| 4 | [apache/kafka](https://github.com/apache/kafka) | 34,105 | §2.2 | 讲「AOF 与预写日志」时对照 `core/src/main/scala/kafka/log/Log.scala`：Kafka 用「追加日志 + 段文件」实现持久化，与 AOF 的 append-only 同源，区别在于 Kafka 靠「保留策略」删除旧段而不是重写 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Redis 入门到实战<br><sub>黑马程序员</sub> | [BV1cr4y1671t](https://www.bilibili.com/video/BV1cr4y1671t/) | 全章 | 主线课：数据结构与底层编码 → 持久化 → 主从/哨兵/集群 → 缓存三大问题与分布式锁；看完回 `ex01_rdb_fork_cow`（RDB 快照）核对 |
| 2 | 尚硅谷 · Kafka 3.x 从入门到调优<br><sub>尚硅谷</sub> | [BV1vr4y1677k](https://www.bilibili.com/video/BV1vr4y1677k/) | 全章 | 比入门版多了调优与运维：ISR、HW/LEO、日志段与零拷贝、积压排查；看完回 `ex02_rdb_save_m_n`（RDB 触发条件）核对 |
| 3 | 尚硅谷 · RabbitMQ 消息队列<br><sub>尚硅谷</sub> | [BV1cb4y1o7zz](https://www.bilibili.com/video/BV1cb4y1o7zz/) | 全章 | 交换机类型、确认机制与死信队列；做选型对比时用它补齐「非日志型 MQ」的视角；看完回 `ex03_aof_always`（AOF 追加）核对 |
| 4 | 尚硅谷 · Kafka 快速入门<br><sub>尚硅谷</sub> | [BV1a4411B7V9](https://www.bilibili.com/video/BV1a4411B7V9/) | 全章 | Topic/Partition/Replica 模型、生产者与消费者、位移提交；讲清「顺序性只在分区内成立」；看完回 `ex04_aof_everysec`（AOF 追加）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Redis 设计与实现》黄健宏 |
| 2 | 《Kafka 权威指南》Narkhede 等 |
| 3 | 《数据密集型应用系统设计》Kleppmann |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
