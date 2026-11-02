# 凯喵实战手记 · Redis 底层结构：为什么你的 key 会突然变胖

> 凯喵说：很多人用 Redis 只看命令，不看编码。等到某天发现内存爆了、某条命令突然卡住、迁移后数据体积翻倍，才回头问「它到底把数据存成什么样」。这一章我们把 Redis 的底层数据结构一个个拉到现场，让你从「会用」走到「知道它怎么存」。

### 现场 1：为什么 Redis 不用 C 字符串

C 字符串以零字节结尾，求长度要遍历，还不安全。Redis 自己实现了 SDS（简单动态字符串），头部记录长度与已分配容量，取长度是常数时间，且二进制安全，能存图片、序列化数据。凯喵提醒：你存进去的每个字符串，底层其实都套着一个 SDS 头，所以「小字符串」并不是零成本，这也是 Redis 单 key 内存开销偏高的根源之一。

```c
struct sdshdr8 {
    uint8_t len;      // 已用长度
    uint8_t alloc;    // 已分配容量（不含头和终止符）
    unsigned char flags;
    char buf[];       // 柔性数组，实际内容
};
```

### 现场 2：SDS 头部按长度自适应

短字符串用 sdshdr5（只存 flags 和内容），中等用 sdshdr8，再长用 16/32/64 位头。头部越小越省内存，但能表达的长度上限越低。凯喵带人排查「为什么一万个短 key 占了这么多内存」时，第一件事就是算：每个 key 的 SDS 头加 redisObject 头加字典项，固定开销可能超过二十字节，key 越小越吃亏。

### 现场 3：字符串的三种编码：int、embstr、raw

Redis 会看内容挑最省的编码。能解析成 64 位整数的用 int，直接把数值存在指针位里，没有额外分配；短字符串用 embstr，头和内容一次分配、内存连续；长字符串用 raw，头和内容分开分配。凯喵强调：这三种编码不是你选的，是 Redis 按长度与内容自动切的，理解它才能解释内存曲线的突变。

```bash
SET n 12345
OBJECT ENCODING n      # int
SET s "hello"
OBJECT ENCODING s      # embstr
SET l "a very long string exceeding forty four bytes......"
OBJECT ENCODING l      # raw
```

### 现场 4：44 字节是 embstr 与 raw 的分界线

embstr 只用于长度不超过 44 的字符串，超过就变 raw。这个数字不是随便定的，而是缓存行与对象头算出来的经验值。凯喵的实战经验：如果你有一批「刚好卡在四五十字节」的 key，稍微缩短命名或换哈希前缀，就能把它们从 raw 拉回 embstr，内存能省下可观的一截。

### 现场 5：append 让 embstr 悄悄变 raw

embstr 设计成只读，一旦你对它 `APPEND`，Redis 必须先转成 raw 再改，编码当场变化且不可逆。凯喵见过有人拿 embstr 当计数器反复 append，结果编码一直停在 raw，内存比预期高。要累加数值用 `INCR`，要拼接就接受 raw 的成本，别指望它还能缩回去。

```bash
SET k "abc"
OBJECT ENCODING k      # embstr
APPEND k "def"
OBJECT ENCODING k      # raw（不可逆）
```

### 现场 6：list 的演进：ziplist 到 quicklist

老版本小 list 用 ziplist（一整块连续内存），大 list 用双向链表。后来统一成 quicklist：一个双向链表，每个节点是一块 listpack，兼顾内存连续与插入效率。凯喵提醒：quicklist 的节点大小由 `list-max-listpack-size` 控制，调太小节点多、指针开销大，调太大单节点操作慢，是个权衡。

### 现场 7：hash 在 listpack 与 hashtable 之间切换

小 hash 用 listpack 紧凑存，字段数或单值长度超过阈值就转 hashtable。阈值由 `hash-max-listpack-entries`（默认 128）和 `hash-max-listpack-value`（默认 64）控制。凯喵的现场经验：很多人把用户属性塞进一个 hash，字段一多就跨过阈值，编码变成 hashtable，内存当场翻倍，而他们完全没意识到是「字段数量」触发的。

```bash
HSET user name kai age 3
OBJECT ENCODING user   # listpack
# 字段数超过 128 后
OBJECT ENCODING user   # hashtable
```

### 现场 8：set 的三态：intset、listpack、hashtable

set 里全是整数且数量少时用 intset（有序整数数组，省内存）；元素是短字符串且数量少时用 listpack；否则用 hashtable。凯喵提醒：intset 只能存整数，一旦你往里加一个字符串，整个 set 会转成 hashtable，而且不可逆。设计时要想清楚这个集合未来会不会混入非整数。

### 现场 9：zset 的 listpack 与 skiplist

小 zset 用 listpack 按分数有序存，元素数或值长度超阈值就转 skiplist 加字典。阈值是 `zset-max-listpack-entries`（默认 128）和 `zset-max-listpack-value`（默认 64）。凯喵：排行榜类业务最容易踩这个，成员一多就转 skiplist，内存和操作复杂度都上一个台阶，提前按规模规划好分片比事后优化省事。

### 现场 10：渐进式 rehash 让扩容不卡顿

字典扩容不是一次性搬完，而是保留新旧两张表，每次操作顺手搬一点，直到搬完。这就是渐进式 rehash。凯喵提醒：rehash 期间内存会短暂翻倍，如果你的实例内存已经贴着上限，一次大量写入可能直接触发淘汰甚至 OOM，扩容前留足余量是运维的基本功。

```bash
# rehash 期间新旧表并存，内存短时上升
INFO memory | grep used_memory
```

### 现场 11：用 OBJECT ENCODING 现场排查

怀疑内存异常时，先对可疑 key 跑 `OBJECT ENCODING`，再看 `MEMORY USAGE`。这两个命令能立刻告诉你它用的是哪种编码、实际占多少字节。凯喵的排查顺序：先定位大 key，再看编码是否「本该紧凑却变成了哈希表」，最后才谈优化。凭猜测调参数，往往越调越乱。

```bash
OBJECT ENCODING bigkey
MEMORY USAGE bigkey SAMPLES 0
```

### 现场 12：大 key 是内存与阻塞的双重炸弹

单个 key 存了几十万个元素，不只是占内存，`DEL` 它时还会阻塞主线程。凯喵的规矩：大 key 用 `UNLINK` 异步删，设计阶段就按业务维度拆分，别让一个 key 无限膨胀。所谓「大」没有绝对标准，但超过几 MB 就该警惕，超过几十 MB 基本要在架构上拆。

### 现场 13：阈值参数的副作用不可逆

把 `hash-max-listpack-entries` 调大能让更多 hash 留在紧凑编码，省内存，但单次操作要遍历整块内存，可能变慢；而且编码一旦转成 hashtable 就不会自动转回 listpack，改配置也救不回已经变胖的 key。凯喵：调阈值前先评估读写比例与元素规模，改完用 `OBJECT ENCODING` 验证，别只看文档默认值。

### 现场 14：按访问模式选结构，而不是按直觉

同样是「存一堆东西」，用 list、hash、set、zset 的内存与操作成本差别很大。凯喵的选型口诀：要按序取用 list，要按字段查 hash，要去重 set，要按分数排 zset。选错结构，后面所有的优化都是在给错误的地基打补丁。先想清楚你主要的访问模式，再决定底层结构，这比任何参数调优都重要。

> 凯喵总结：Redis 的内存问题九成来自「不知道它把数据存成什么编码」。理解 SDS 头开销、embstr 的 44 字节线、各结构的紧凑编码与切换阈值，你就能在内存曲线突变时一眼看出原因，而不是盲目调参。

> 一句话收尾：Redis 的「快」是设计出来的，「胖」也是设计出来的——看懂它的底层结构，你才真正拥有对它内存的掌控权。

### 凯喵叮嘱：先观测，再判断，最后才优化

最后叮嘱一句：排查内存问题前，先别急着加机器或调淘汰策略，先跑一遍 `OBJECT ENCODING` 和 `MEMORY USAGE`，把每个大 key 的编码与真实占用列出来。大多数所谓内存暴涨，其实就是某几个 key 悄悄换了编码、或者某个集合无限膨胀。看清现状再动手，比任何优化技巧都有效。这也是凯喵带团队时反复强调的顺序：先观测，再判断，最后才优化。跳过观测直接调参，往往越调越乱，还把真正的原因掩盖掉。养成先量后调的习惯，你对 Redis 内存的掌控会稳得多。

## 三视角解析
### 🧑‍💻 程序员视角
Redis 不用 C 字符串而用 SDS：C 字符串取长度要 `strlen` 是 O(n)，且二进制不安全（遇 `\0` 截断）。SDS 头部记录 `len` 与 `alloc`，取长度 O(1)、可存二进制、扩容有预分配策略。字符串有三种编码：短整数用 `int`、≤44 字节用 `embstr`（与 `redisObject` 一次分配）、更长的用 `raw`。这就是为什么「存 45 字节的 key」比「存 44 字节」多一次内存分配——批量 key 设计时值得卡在这个边界内。

### 🎓 博士生视角
Redis 的对象模型是「`redisObject` + 编码」：同一逻辑类型（string/list/hash/set/zset）按数据规模与内容切换底层编码（如 hash 在小规模时用 `listpack`，超阈值转 `hashtable`）。这种「自适应编码」把「小对象的空间效率」与「大对象的时间效率」统一起来，代价是转换不可逆（一旦转成 hashtable 就不会退回）。理解编码边界（如 `hash-max-listpack-entries`）是排查「内存突然翻倍」的关键。

### 📚 考研者视角
后端面试高频：
1. **五大数据类型与底层编码**：string（int/embstr/raw）、list（listpack/quicklist）、hash（listpack/hashtable）、set（intset/listpack/hashtable）、zset（listpack/skiplist）。
2. **SDS 的优势**：O(1) 取长度、二进制安全、预分配减少重分配。
3. **过期与淘汰**：惰性删除 + 定期删除，八种淘汰策略（`allkeys-lru`、`volatile-lfu` 等）。
4. **持久化**：RDB 快照与 AOF 日志的取舍，混合持久化。
