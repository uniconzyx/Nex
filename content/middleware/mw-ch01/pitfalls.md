# 易错点 · Redis 数据结构与底层编码

> 行首编号条目（门禁按行首 `1.`/`- ` 统计）。每条：`N. **陷阱标题** —— 说明 + 正确写法`。

1. **把 SDS 的二进制安全归功于 `\0` 结尾** —— 许多人以为「因为以 `\0` 结尾所以能存任意字节」，恰恰相反：`\0` 只是为兼容 C 库函数的副产物，**二进制安全真正来自 `len` 字段**（按字节数而非扫描 `\0` 解析）。正确写法：回答「SDS 优点」时把「二进制安全」的解释锚定在 `len` 字段上，并说明保留 `\0` 仅为复用 `strlen` 类 C 函数。

2. **记错 Hash/ZSet/Set 编码切换的「且/或」关系** —— 实际条件是**同时满足**「元素数 ≤ 阈值」**且**「单值字节 ≤ 阈值」才保留紧凑编码（listpack/intset），任一不满足就转 hashtable/skiplist。正确写法：被问阈值时一律按「且」表述；排查「热 Hash 突然变 hashtable」优先查是否有某个 value 超过 `hash-max-listpack-value=64` 字节。

3. **以为 embstr 是可原地修改的紧凑串** —— `embstr` 是**一次性分配、只读**结构，任何 `APPEND`/`INCR` 都会先转成 `RAW` 再改，没有「原地扩容」。正确写法：高频写短串直接用 `SET` 覆盖或接受 embstr→raw 的转换；解释 44 字节分界时说明它来自 64B jemalloc 块减去 robj(16)+sdshdr8(3)+\0(1)。

4. **渐进式 rehash 期间仍向 ht[0] 写数据** —— 迁移进行中（`rehashidx != -1`）**新增 key 只写 ht[1]**，查找需查两张表，ht[0] 只减不增直至搬空。正确写法：描述 rehash 时明确「新增走 ht[1]、查找查两张表、搬完才互换」，避免写成「边搬边写旧表」。

5. **intset 升级后还能降级** —— intset 的 `encoding` 位宽升级（int16→int32→int64）是**单向、不回退**的，即使之后删掉大整数也不会缩回窄位宽。正确写法：答「intset 会升级但不会降级」，并说明升级是整块内存按新位宽重排，不是逐元素扩展。

6. **用 ziplist 的「前驱长度字段」理解连锁更新** —— 旧 ziplist 用「前一 entry 长度」字段，长度从 1B 跨到 5B 会触发后续整段重编码（连锁更新）；Redis 7 换 listpack 改为「记录自身长度、从后向前遍历」以消除该问题。正确写法：被问「ziplist 缺陷」时答连锁更新，并补充 listpack 的修复思路，别把 ziplist 与 listpack 混为一谈。

7. **线上用 `KEYS *` 扫 key**
   Redis 是单线程处理命令，`KEYS` 是 O(N) 全表遍历且**阻塞**：百万级 key 会让实例卡住数百毫秒到数秒，所有客户端一起超时，触发重试风暴。
   ✅ 用 `SCAN` 游标分批（每批 100~1000）；线上用 `rename-command` 直接屏蔽 `KEYS` / `FLUSHALL` / `FLUSHDB`。

8. **用 `ZRANGEBYSCORE` 取出来再逐条 `ZREM` 删**
   大集合下这是 N 次网络往返 + N 次单元素删除，延迟与网络放大几十倍，且中间态对并发读者可见。
   ✅ 用 `ZREMRANGEBYSCORE` / `ZREMRANGEBYRANK` 一条命令批量删；跨结构迁移用 `ZUNIONSTORE`（`WEIGHTS 0`）落到新 key 再 `DEL` 旧的。

9. **没算编码阈值，内存突然翻倍且不可逆**
   `hash-max-listpack-entries`（默认 128）、`list-max-listpack-size`、`set-max-intset-entries` 等阈值一超，紧凑编码（listpack/intset）立刻转成 hashtable/quicklist，单 key 内存可跳一个量级；**删元素也不会转回去**。
   ✅ 设计时就限制单 key 的元素个数与 value 长度；超大 hash 按业务维度拆成多个 key（分桶）；调整阈值前先用 `OBJECT ENCODING` 确认现状。
10. **把大 hash 当「万能存储」不分桶** —— 一个 hash 塞几十万字段，编码早转 hashtable，单 key 内存巨大，`HDEL`/`HGETALL` 还会阻塞主线程。正确写法：按业务维度拆成多个 key，大 key 用 `HSCAN` 分批处理，删除用 `UNLINK`。
11. **线上跑 `KEYS *` / `FLUSHALL`** —— `KEYS` 会遍历全库阻塞主线程，`FLUSHALL` 直接清空数据。正确写法：用 `SCAN` 游标迭代代替 `KEYS`；清库只在确认的测试环境做。
12. **阻塞队列 `BLPOP` 忘了设超时** —— 不设超时会永久阻塞，客户端连接泄漏。正确写法：`BLPOP key 5` 显式给秒级超时，循环里处理超时继续等。
13. **以为 set 存字符串还走 intset** —— intset 只能存整数，一旦混入一个字符串，整个 set 转 hashtable 且不可逆。正确写法：全整数集合才用 intset 预期，混类型场景直接按 hashtable 估算内存。
14. **zset 用 `ZRANGE 0 -1` 拉全量** —— 成员几十万时一次性取回，网络与内存双爆。正确写法：分页 `ZRANGE start stop`，或按分数 `ZRANGEBYSCORE` 限定范围，配合 `LIMIT`。
15. **把序列化大对象整块塞进单个 String** —— JSON/Protobuf 动辄几 MB，读一次整块加载，改一个字段要全量重写。正确写法：拆成 hash 字段或按业务拆 key，只读写需要的部分。
