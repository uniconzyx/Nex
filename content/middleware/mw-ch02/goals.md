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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | 含 Redis 与消息队列的高频面试知识 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 高并发与分布式：缓存、消息队列、分库分表专题 |
| [redis/redis](https://github.com/redis/redis) | 76640 | Redis 官方源码仓库：数据结构与命令实现的权威来源 |
| [apache/kafka](https://github.com/apache/kafka) | 33917 | Apache Kafka 官方仓库：架构与协议实现 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Redis 6 入门到精通 | [视频](https://www.bilibili.com/video/BV1Rv41177Af/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Kafka 教程 | [视频](https://www.bilibili.com/video/BV1a4411B7V9/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · RabbitMQ 新版教程 | [视频](https://www.bilibili.com/video/BV1sw4m1U7Qe/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Nginx 由浅入深 | [视频](https://www.bilibili.com/video/BV1zJ411w7SV/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · ZooKeeper 教程 | [视频](https://www.bilibili.com/video/BV1to4y1C7gw/) | 本学科配套视频，建议结合本章示例与习题观看 |
