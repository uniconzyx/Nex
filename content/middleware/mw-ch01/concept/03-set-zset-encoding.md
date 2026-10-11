# 三、Set 与 ZSet 的底层编码

本文件覆盖两个核心主题：**① Set 的 intset 与 hashtable** 与 **② ZSet 的 listpack 与 skiplist+dict**。

---

## ① Set：intset（整数集合）与 hashtable

（中立陈述）Set 当**所有元素都是整数且元素个数 ≤ `set-max-intset-entries`（默认 512）**时编码为 `intset`（一块连续、按值升序排列的整数数组，按 `encoding` 字段统一用 16/32/64 位存储）；任一条件不满足即转成 `hashtable`（value 为 NULL 的字典）。intset 在插入更大范围整数时会**升级（upgrade）**编码位宽。

### 🧑‍💻 程序员视角
- **纯整数小集合极省内存**：粉丝 ID 集合、标签 ID 集合用 Set，只要全是 int 且 ≤512，内存远小于 hashtable；但一旦混入一个字符串元素（如 `"vip"`），整个集合立刻转 hashtable，内存与延迟突变——这是「脏数据触发编码升级」的典型事故。
- **SADD 混合类型要小心**：`SADD tag 1 2 "x"` 会让前面两个 int 也被挪进 hashtable。
- **踩坑**：`SMEMBERS` 大集合是 `O(N)` 且阻塞，分页用 `SSCAN`。

### 🎓 博士生视角
- **内存布局**：`intset` 头含 `encoding`(16/32/64)、`length`、以及紧随其后的元素数组；元素**升序**排列以支持二分查找 `O(log n)`。
- **升级过程**：插入一个超出当前 `encoding` 范围的数时，先整体按新位宽（如 int16→int32）重排内存，再把新元素放到正确位置；升级**单向、不回退**，因为回退要判断所有元素是否都够小，代价高且易抖动。
- **为什么连续数组**：比 hashtable 省掉指针与桶开销，缓存命中率高；512 这个上限是「紧凑性 vs 查找/插入拷贝成本」的经验折中。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Set 的两种编码及转换条件？」答 intset（全整型且 ≤512）↔ hashtable，条件为**「且」**。
- **易错口径**：intset 里元素**升序存储**是为了 `O(log n)` 查找；升级是**整体重编码**不是逐元素扩展，考试常考「插入 65535 到 int16 集合会发生什么」——答升级为 int32 并重排。
- **连问**：「intset 会降级吗？」答不会，升级单向。

---

## ② ZSet：listpack 与 skiplist + dict 双结构

（中立陈述）ZSet 在**元素数 ≤ `zset-max-listpack-entries`（默认 128）且每个 member 字节 ≤ `zset-max-listpack-value`（默认 64）**时用 `listpack`（member 与 score 成对紧凑存放）；否则用 `skiplist`（跳表）+ `dict` 双结构：跳表按 score 排序支持范围查询，字典按 member 查 score（`O(1)`），两者共享 member/score 对象避免重复存储。

### 🧑‍💻 程序员视角
- **ZADD 别超阈值**：排行榜小集合用 listpack 很省，但元素稍多就转跳表+字典，内存翻几倍；上线要看 `OBJECT ENCODING` 确认热榜仍在 listpack。
- **范围查询用跳表**：`ZRANGEBYSCORE`/`ZREVRANK` 是跳表的强项（`O(log n + m)`）；但 `ZSCORE` 走字典 `O(1)`，不要为了拿分再用 `ZRANK` 反查。
- **踩坑**：score 用浮点，相等 score 按 member 字典序排，别假设同分顺序；`ZINCRBY` 大跳变要留意精度。

### 🎓 博士生视角
- **跳表层数概率**：每个节点以 `p=1/4` 概率晋升到更高层，期望层数约 `1/(1-p)=1.33`，最大层数 `ZSKIPLIST_MAXLEVEL=32`；整体查找复杂度 `O(log n)`，与平衡树同阶但实现更简单、范围遍历更自然。
- **双结构一致性**：`dict` 与 `skiplist` 指向同一份 `robj`，`ZADD` 同时更新两者；删 member 时两结构都要改，保证 `ZSCORE` 与 `ZRANK` 永远一致。
- **listpack 布局**：member、score 交替紧凑存放；超阈值转结构后，listpack 的「省内存」让位给「高效范围/单点查询」。

### 📚 考研者视角（笔面考点）
- **标准问法**：「ZSet 为什么用跳表而不是红黑树？」答：跳表范围查询/遍历更自然、`O(log n)`、实现简单、且可灵活调整 `p` 与层高；Redis 另配 dict 做 `O(1)` 单点查分。
- **易错口径**：别只答「跳表简单」——要点出**跳表+字典双结构**分工（跳表管排序/范围，字典管 member→score），以及 listpack 小数据紧凑编码。
- **连问**：「跳表层数怎么定？」答每层 `1/4` 概率晋升，最大 32 层，期望层数约 1.33。
