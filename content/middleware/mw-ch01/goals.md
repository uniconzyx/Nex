# 学习目标 · Redis 数据结构与底层编码（mw-ch01）

> 学科：`middleware` · 分组：M1 Redis 原理
> 配套资源：《Redis 设计与实现》第 1-2 章、《Redis 深度历险》。本章聚焦「Redis 对象类型 ↔ 底层编码」的映射关系与从零模拟。

完成本章后，读者应能：

1. **说清五种顶层对象类型与底层编码的映射**：String / List / Hash / Set / ZSet 各自在何种条件下选用 int、embstr、raw、listpack（ziplist）、quicklist、hashtable、intset、skiplist+dict 等编码，并记住关键阈值（如 `hash-max-listpack-entries`、`zset-max-listpack-value`、`set-max-intset-entries`）。
2. **对比 SDS 与 C 字符串**：理解长度前缀、`O(1)` 长度获取、二进制安全、惰性删除与空间预分配（`alloc`/`len`/`free`）带来的写入放大优化与内存换时间权衡。
3. **理解字典的渐进式 rehash**：为什么 Redis 不在一次命令里把整张表搬完，而是分散到每次增删改查与定时任务中，避免长尾延迟。
4. **从零实现一个迷你 Redis 内核**：用 Python 模拟 SDS、dict 渐进 rehash、listpack 编码阈值、intset 升级、skiplist 跳表、quicklist 与 bitmap 的字节布局，并能打印真实结构状态。
5. **掌握笔试/面试高频口径**：Object Encoding 判定、ziplist 连锁更新、intset 编码升级、跳表层数概率、String 44 字节 embstr 分界等，能给出标准答法与易错点。


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
