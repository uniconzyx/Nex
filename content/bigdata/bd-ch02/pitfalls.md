# MapReduce 与 YARN 易错点（高频踩坑与笔试面试易混口径）

1. **把 Reducer 的输入当成单值 `(k, v)`** —— 错。Reducer 收到的输入是 `(key, Iterable<value>)`，即**同一 key 的所有 value 组成的迭代器**，形如 `(word, [1,1,1])`。若直接当单个 value 处理，聚合结果必然错误。正确写法：在 reduce 里遍历 `values` 累加/汇总；在 SQL 里理解成「GROUP BY key 后对该组多行做聚合」。

2. **认为 Combiner 一定能用、或把它当 Reducer 的替代** —— 错。Combiner 只在 Map 端本地做**可结合/可交换**的聚合，运行次数不确定（可能 0 次），且**跨 map 的最终合并仍由 Reducer 完成**。求均值、求中位数、去重计数这类不可逆/非结合的运算，直接当 Combiner 会算错（如 `avg(avg,avg)≠avg`）。正确写法：可结合的 sum/count/min/max 才配 Combiner；求均值应传 `(sum,count)` 由 Reducer 相除；绝不能把有副作用（发消息、全局计数）的逻辑放进 Combiner。

3. **默认哈希分区会自动均衡、不会倾斜** —— 错。默认 `hash(key) % R` 是「与 key 值无关」的散列，对**幂律分布**（少数热 key 占绝大多数）完全无效：一个 `vip_user` 可能被和别的 key 哈希到同一分区，造成该 reduce 数据量爆炸、长尾卡在 99%。正确写法：识别热 key（看 counters 里某 reduce 输入远大于均值）；手写 Partitioner 把热 key 单独路由，或用「加盐（salting）：热 key 加随机后缀打散到多 reduce，再二次聚合」。

4. **reduce 数随便设，越大越快** —— 错。`mapreduce.job.reduces` 既决定并行度也决定**输出文件数**。`R` 过大 → 上百个近乎空的小文件（浪费 NN 元数据、拖慢后续读、Hive 小文件问题）；`R` 过小 → 单 reduce 处理过多、易 OOM、慢。正确写法：按 `输入量 / 256MB~1GB` 估；且 reduce 数一旦定下，因为默认哈希是取模而非一致性哈希，**改 R 会让几乎所有 key 重新分区（全量 shuffle）**，所以上线前就要估准。

5. **Shuffle 是「Map 之后才发生」、只有 Map 端会落盘** —— 错。Shuffle 从 Map 写环形缓冲区就开始（排序+spill 到本地磁盘），Reduce 端也有 copy→merge→**可能 spill 再归并**。它是横跨 Map 输出与 Reduce 输入、且两端都涉及磁盘 IO 的过程，是作业性能的「胜负手」。正确写法：调优优先看 Shuffle：`io.sort.mb` 调大减少 spill、给 Combiner、调 `reduce.shuffle.parallelcopies`/缓冲区比例；看到 map 慢或 reduce 长尾先查 spill 次数与数据倾斜。

6. **Partitioner 返回的分区号可能越界或为负** —— 错。自定义 `getPartition` 若用 `key.hashCode() % R`，Java 的 `%` 对负哈希值会得到负数，或结果超出 `[0, R)`，直接抛 `IOException` 让 task 失败。正确写法：写成 `(key.hashCode() & Integer.MAX_VALUE) % R` 或 `(h % R + R) % R`，保证落在合法区间；并牢记「相同 key 必须永远进同一分区」这一正确性不变量。

7. **AM 是常驻全局服务、和 RM 一样只有一个** —— 错。ApplicationMaster 是**每作业一个、随作业生死**，负责任务级调度与容错；RM 才是全局唯一。AM 挂了 RM 会重启用新容器拉起（作业不丢），但 RM 挂了（未配 HA）则全集群无法提交/调度新作业。正确写法：区分「作业级角色 AM」与「集群级角色 RM」；生产环境 RM 必须上 HA（ZKFC + ZK），否则单点。

8. **Capacity 调度器的 `capacity` 是「上限」、Fair 调度器默认就完全公平** —— 错。`capacity` 是队列的**保底（min-guarantee）占比**，`maximum-capacity` 才是弹性上限；不设 `maximum-capacity=100%` 队列借不到别人空闲资源。Fair 里若不设 `weight`，各队列才平分；设了权重则按权重分，且「公平」指 max-min 公平而非绝对平分，还要靠 preemption _timeout 才抢资源。正确写法：用 Capacity 时想清楚保底 vs 借用边界；用 Fair 时显式配权重与抢占超时，别以为「切换就自动公平」。
