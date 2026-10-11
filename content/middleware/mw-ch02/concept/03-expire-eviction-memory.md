# 三、过期删除、内存淘汰与碎片管理

本文件覆盖两个核心主题：**① 过期键删除（惰性 + 定期采样）** 与 **② 内存淘汰（近似 LRU/LFU、maxmemory、碎片率、编码转换）**。

---

## ① 过期键删除：惰性删除 + 定期删除

（中立陈述）给 key 设置 TTL 后，Redis 不会在到期瞬间自动删除，而是用两种策略配合：①**惰性删除（lazy expiration）**——访问 key 时检查是否过期，过期则删除并返回空；②**定期删除（active expire）**——`serverCron` 每秒约 10 次，每次随机抽取若干带 TTL 的 key，删除其中过期的，并自适应调整抽样力度。二者结合：惰性保证“不浪费 CPU 在无人访问的 key 上”，定期保证“过期 key 最终会被回收、不无限占内存”。见 `examples/ex08_expire_lazy.json`、`ex09_expire_active.json`。

### 🧑‍💻 程序员视角
- **惰性删除的隐患**：大量 key 同时过期却长期无人访问，会一直占内存直到被定期任务或访问触发；业务上避免“同一时刻批量过期”（如缓存集中设相同 TTL），应给 TTL 加随机抖动（如 `TTL + random(0,300)`）。
- **定期删除是抽样的**：不是全量扫描，所以极端情况下过期 key 可能有短暂残留（内存未立即释放），这是设计权衡而非 bug；可通过 `hz` 调高频率（但更费 CPU）。
- **踩坑**：`DEL`/`EXPIRE` 自身是写命令，会被 AOF/RDB 记录；而惰性/定期删除过期 key **不生成 del 命令**，从节点靠主节点的 del 同步删除。主从不一致排查时常源于此。

### 🎓 博士生视角
- **惰性删除的复杂度**：访问路径上多一次 `now - expire_time` 比较（O(1)），过期则顺带删除；把“删除成本”均摊到访问时刻，避免集中删除造成的延迟尖刺。
- **定期删除的自适应**：每次随机抽取 `ACTIVE_EXPIRE_CYCLE_LOOKUPS_PER_LOOP`（默认 20）个 key，若过期比例超过 25% 则继续本轮抽样，直到低于阈值或超时（默认 25ms），从而“过期越多、清理越积极”，又受时间上限约束不影响主线程。
- **“为什么要抽样而非全扫”**：全量扫描过期字典在 key 数巨大时不可接受；抽样把删除成本控制在固定预算内，是“概率性彻底清理”的工程近似，符合 Redis 单线程低延迟优先原则。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Redis 怎么删除过期 key？」答：惰性删除（访问时删除）+ 定期删除（周期性随机采样删除）结合；单靠任一都会有问题（全惰性=内存泄漏，全定期=CPU 尖刺）。
- **易错口径**：过期删除**不会**主动生成 del 命令，主从靠主节点传播 del 同步；另外“过期即立刻删除”是错误理解，是“被动/周期”而非“定时触发”。
- **关联考点**：可联系操作系统/数据库的“惰性回收 + 后台整理”思想，以及缓存 TTL 打散的工程实践。

---

## ② 内存淘汰、maxmemory 与碎片管理

（中立陈述）当 `used_memory` 达到 `maxmemory` 且再写入时，Redis 按 `maxmemory-policy` 选 key 淘汰。八种策略分三类：`noeviction`（默认，写满报错）、`*lru`（近似 LRU，allkeys/volatile）、`*lfu`（近似 LFU，allkeys/volatile）、`*random`、`volatile-ttl`。Redis 的 LRU/LFU 是**近似算法**：不维护全局链表，而是**随机采样 N 个（默认 5，maxmemory-samples）候选，从中挑最久未用/最低频的淘汰**，以极小采样代价近似全局最优。内存碎片率 `mem_fragmentation_ratio = used_memory_rss / used_memory`，>1.5 表示碎片严重，<1 表示内存被 OS 换页（swap）。见 `examples/ex10_lru_approx.json`、`ex11_lfu_approx.json`、`ex12_mem_fragmentation.json`、`ex13_encoding_conversion.json`、`ex14_eviction_policies.json`。

### 🧑‍💻 程序员视角
- **缓存场景选 `allkeys-lru`/`allkeys-lfu`**：纯缓存（数据可重建）用 allkeys-*，写满即按热度淘汰；若数据须持久（如当数据库用）则用 `noeviction` 或 `volatile-*`，避免误删重要 key。
- **采样数 `maxmemory-samples`**：调到 10 会更接近真实 LRU、命中率更高，但更费 CPU；默认 5 是平衡点。
- **big key 是内存杀手**：大 Hash/大 ZSet 删除/淘汰时会阻塞主线程（耗时与元素数成正比），用 `UNLINK`（异步惰性删除）替代 `DEL`；日常用 `redis-cli --bigkeys` 排查。
- **碎片治理**：碎片率高可开启 `activedefrag`（主动碎片整理），或低峰期重启重建；内存被 swap（`ratio<1`）必须立即排查，否则延迟暴涨。

### 🎓 博士生视角
- **近似 LRU 的动机**：严格 LRU 需为每个 key 维护全局访问时序链表，每次访问 O(1) 改链表、淘汰 O(1) 取表尾，但链表操作在单线程高并发下仍是可观开销且占用额外指针内存；近似 LRU 用「每个 key 一个 24-bit LRU 时钟 + 随机采样 N 取最小」以极低成本逼近效果（Redis 官方测试命中率与严格 LRU 仅差约 1%~2%）。
- **LFU 的计数器与衰减**：`lfu-log-factor` 控制计数增长的对数速率（访问越多增长越慢，防溢出），`lfu-decay-time` 控制空闲 key 的计数随时间衰减；这样既能识别长期热点，又能在热度消退后及时淘汰，优于 LRU 对“历史老但不再访问”key 的偏见。
- **碎片率公式的硬件语义**：`used_memory` 是 Redis 分配器（jemalloc）记账的“逻辑已用”，`used_memory_rss` 是 OS 视角的“物理常驻”；二者比值反映分配器碎片与外部碎片；`ratio<1` 说明 `rss<逻辑内存`——必然是有部分内存被换到 swap，属危险信号。
- **编码转换与内存**：小整数/短串/小集合用 int/embstr/listpack/intset 紧凑编码省内存，超阈值升级为 raw/hashtable/skiplist（参考 mw-ch01）；写入触发的编码升级会临时增加内存与 CPU。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Redis 的八种淘汰策略？」必列：noeviction、allkeys-lru、volatile-lru、allkeys-lfu、volatile-lfu、allkeys-random、volatile-random、volatile-ttl；并说明 allkeys-* 对所有 key、volatile-* 仅对带 TTL 的 key 生效。
- **标准问法**：「为什么 Redis 用近似 LRU 而非严格 LRU？」答：严格 LRU 需全局链表，维护开销大；近似 LRU 随机采样 N 个候选取最久未用，成本低、命中率接近，符合单线程低延迟目标。
- **易错口径**：`mem_fragmentation_ratio<1` 不是“碎片好”，而是“内存被 swap 换出”，性能会骤降；`>1` 才表示有碎片（正常略大于 1）。LRU/LFU 是“近似”而非“精确全局”。
