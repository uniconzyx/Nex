# 二、List 与 Hash 的底层编码

本文件覆盖两个核心主题：**① List 的 quicklist / listpack** 与 **② Hash 的 listpack 与 hashtable 编码**。

---

## ① List：从 ziplist+linkedlist 到 quicklist

（中立陈述）Redis 3.2 前 List 在元素少时用 `ziplist`、多时用 `linkedlist`；3.2 起统一为 `quicklist`——一个由**多个 listpack（Redis 7 起 ziplist 被 listpack 取代）节点**组成的双向链表，单个节点有大小上限（默认 `list-max-listpack-size = -2` 即 8KB），兼顾少量数据的紧凑与大量数据的分段。

### 🧑‍💻 程序员视角
- **不要用 List 当大消息队列无限堆积**：虽然 quicklist 分段，但单节点 8KB、整体无上限，消费者 lag 时内存会涨；大列表操作（`LRANGE 0 -1`）仍是 `O(N)` 且可能阻塞，分页取更安全。
- **ziplist→listpack 迁移**：Redis 7 把 `ziplist` 全面换成 `listpack`，根因是 ziplist 的「前一个条目长度」字段会导致**连锁更新（cascade update）**，listpack 改成从后向前记录本条目长度，消除该问题。
- **踩坑**：`LPUSH`/`RPUSH` 混用做栈/队列没问题，但 `LINSERT`/`LSET` 在中间写会触发节点分裂，性能劣于头尾操作。

### 🎓 博士生视角
- **内存布局**：每个 quicklist node 持有一个 listpack，listpack 是自描述紧凑串（每条目前部含本条目长度，从尾向首解析）；quicklist 头/尾各一个 `quicklistNode*`，并维护 `count`（总元素数）以支持 `LLEN` 的 `O(1)`。
- **fill 因子**：`list-max-listpack-size` 用负数表示「节点最大字节数上限档位」（-1=4KB…-5=64KB），正数表示「单节点最多 N 个 entry」，是空间局部性与指针开销的折中。
- **压缩中间节点**：`list-compress-depth` 可把中间节点用 LZF 压缩，只保留头尾若干节点不压缩，是「冷数据压缩、热数据直访」的典型分层。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Redis 的 List 底层是什么？为什么这么设计？」答 quicklist（listpack 双向链表），兼顾 ziplist 的紧凑与 linkedlist 的插入效率，避免大 ziplist 更新慢。
- **易错口径**：面试常问「ziplist 有什么缺陷」——答**连锁更新**（前驱长度字段 5B↔1B 进位导致后续整段重编码），listpack 通过「记录自身长度、从后向前遍历」修复；不要答成「不支持二进制」。
- **阈值题**：被问 `list-max-listpack-size` 含义时，区分正负两类语义，别混为一谈。

---

## ② Hash：listpack 与 hashtable 的编码切换

（中立陈述）Hash 对象在**字段数 ≤ `hash-max-listpack-entries`（默认 128）且每个 value 字节数 ≤ `hash-max-listpack-value`（默认 64）**时编码为 `listpack`；超出任一条件则转为 `hashtable`（真正的链式哈希表）。转换是单向的。

### 🧑‍💻 程序员视角
- **小 Hash 当对象用很香**：存用户画像（几十个字段、每字段短）用 Hash 而非 JSON 字符串，可单独读写字段；但要警惕某个 value 偶尔超 64 字节会把整个 Hash 变成 hashtable，内存与读放大骤增——这是「阈值突变」陷阱。
- **看编码**：上线前用 `OBJECT ENCODING` 抽查热点 Hash，确认仍在 listpack；否则调大 `hash-max-listpack-value` 需权衡「单节点过大拖慢 listpack 遍历」。
- **踩坑**：把 Hash 当「无限字段表」塞上万字段，会一路 hashtable 且易成 big key，`HGETALL` 阻塞。

### 🎓 博士生视角
- **listpack 布局**：field/value 成对连续存放，无额外指针，内存密度高；`HLEN`/`HGET` 需线性扫描（小数据可忽略），`O(N)`。
- **转 hashtable**：底层用 `dict`，`HGET` 变 `O(1)` 平均，但每个 entry 有 dictEntry 指针 + 哈希桶开销，内存膨胀数倍。
- **为什么单向转换**：避免「来回抖动」——若允许降级，写大 value 再删回会反复转码，引入不稳定延迟；单向保证可预测。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Hash 的两种编码及转换条件？」答 listpack（field≤128 且 value≤64B）↔ hashtable，超阈值单向转。
- **易错口径**：两个阈值是**「且」**关系，不是「或」；常有人记成「任一超就转」，要强调必须**同时满足**两条件才保留 listpack。
- **连问**：「为什么不对 listpack 做查找索引？」答小数据线性扫描成本可忽略，加索引反而破坏紧凑性——体现空间/时间取舍。
