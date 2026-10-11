# 学习目标 · 缓存设计与三大经典问题（mw-ch04）

> 学科：`middleware` · 分组：M2 缓存工程
> 配套资源：《Redis 深度历险》缓存篇。本章聚焦「缓存设计」与「穿透 / 击穿 / 雪崩」三大经典问题，
> 以及缓存与数据库一致性、更新策略；并用 Python 从零模拟核心机制、打印**确定性量化结果**。

完成本章后，读者应能：

1. **讲清缓存穿透与布隆过滤器**：理解「查询不存在的数据把压力打到 DB」的穿透场景；掌握布隆过滤器的 bit 数组 + 多哈希原理、假阳性（误判）的不可消除性与定量误判率公式 `(1 - e^{-kn/m})^k`；会用空值缓存作为兜底。
2. **掌握缓存击穿的防护**：区分「单 key 热点过期」的击穿与「批量过期」的雪崩；用互斥锁 / 单飞（singleflight）让并发回源只发生一次，或用逻辑过期（异步重建）避免阻塞；能用 Python 实测「200 并发真实回源 1 次」。
3. **理解缓存雪崩与 TTL 打散**：理解统一 TTL 导致同一时刻大量 key 集体失效、DB 被打垮的雪崩；会用过期时间随机化（TTL + 随机抖动）把瞬时失效峰值摊平；了解多级缓存与熔断降级的兜底作用，并能量化「随机化前后同一时刻失效 key 数」的对比。
4. **掌握缓存与数据库一致性（Cache-Aside）**：背记「先更新库、再删缓存」优于「先删缓存、再更新库」；能用确定性时序模拟证明两种顺序在并发读写下产生脏数据的概率差异；理解延迟双删为什么能补救读线程回填的旧值。
5. **区分三大更新策略**：Write-Through（同步双写）、Write-Behind（先写缓存、异步批量刷盘、写合并）、Cache-Aside（读时回填、写时删/更新），清楚各自的强一致 / 最终一致取舍与适用场景。
6. **从零模拟并实测**：用 Python 实现布隆过滤器与误判率、单飞重建回源计数、雪崩 TTL 对比、Cache-Aside 两种顺序的脏数据时序、双删延迟、Write-Through/Write-Behind，并能打印真实运行统计（见 examples/）。
7. **掌握笔试 / 面试高频口径**：穿透（布隆 / 空值）、击穿（单飞 / 逻辑过期）、雪崩（TTL 打散 / 多级 / 熔断）、一致性（先更新库再删缓存 + 延迟双删）、更新策略对比，能给出标准答法与易错点。


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
