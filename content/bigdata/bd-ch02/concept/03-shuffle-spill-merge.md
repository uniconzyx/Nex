# 一、Shuffle 的排序与溢写（spill）

（中立陈述）Map 端并不边算边发网络——它先把 kv 写入**内存环形缓冲区（io.sort.mb，默认 100MB）**。缓冲区按 `spill.percent`（默认 0.8）阈值触发**溢写（spill）**：先按 partition 排序、partition 内按 key 排序（快速排序），再把有序数据写到本地磁盘的一个 spill 文件。Map 结束前，这些 spill 文件会被**归并**成一个大文件供 Reduce 拉取。

### 🧑‍💻 程序员视角
- 调优第一杠杆：`mapreduce.task.io.sort.mb` 调大 → 更少 spill → 更少磁盘 IO；但 JVM 堆内存有限，调太大会 OOM。经验：给 map 堆的 70% 左右给排序缓冲区，其余留给框架。
- 真实踩坑：看到 map 阶段「combine 阶段」特别慢，往往是 spill 次数过多（缓冲区太小）；`grep 'spill' ` 看日志里 spill 次数，>10 次就该调大缓冲区或加 Combiner。
- 溢写是「先排序再落盘」：所以 Map 输出文件天然**按 (partition, key) 有序**，这保证了下游 Reduce 端能用归并而非哈希、且能边拉边合。
- 索引文件：`spill.out.index` 记录每个 partition 在 spill 文件中的偏移，Reduce 端据此**只拉自己那一段**，避免全量传输。

### 🎓 博士生视角
- 内存/磁盘权衡：环形缓冲区是对「写时不确定总大小、又想延迟落盘」的经典解——它用一段定长数组 + 读写指针，写入不阻塞、达到水位再刷盘，把随机写转化为顺序写。
- 外排序的正确性：每个 spill 是有序段（run）；多段有序 → 用**多路归并**合成一个全局有序文件，时间复杂度 `O(n log(n/m))`（m 为内存可容纳段数），这正是外部排序（external merge sort）的标准范式，也是 TeraSort 的底座。
- 排序的稳定性与必要性：必须「先按 partition 再按 key」两级排序，使归并时同 key 连续到达 Reducer，从而 Reducer 只需维护「当前 key」的状态机即可完成分组聚合，无需把所有 value 一次性读进内存。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Map 端 Shuffle 做了什么？spill 是什么？」标准答：Map 输出进环形缓冲区，达到阈值**溢写**到磁盘（先按 partition、再按 key 排序），Map 结束后**归并**所有 spill 成一个有序文件，并写索引供 Reduce 拉取。
- 易错口径：① spill 是「落盘」不是「网络传输」，真正跨网络在 Reduce 的 copy 阶段；② 排序发生在 spill 时（快排），归并发生在 map 结束（归并排序）——两者都是外部排序的一环；③ 缓冲区是「环形」而非简单数组，阈值默认 0.8。
- 关联考点：与「外部排序 / 多路归并」算法题结合；与「归并排序」对比考时间复杂度。

---

# 二、归并（merge）与 Reduce 端的 fetch

（中立陈述）Reduce 端通过 **copy/fetch 线程** 并行地从各个 MapTask 拉取属于自己的 partition 数据。数据先落「内存缓冲区」，溢满后也 spill 到本地磁盘；所有 map 数据到齐后，Reduce 端把**内存片段 + 磁盘 spill** 做一次**多路归并**，得到全局按 key 有序的流，再逐 key 喂给用户的 reduce 函数。

### 🧑‍💻 程序员视角
- 长尾根因：Reduce 任务要**等最慢的 Map 完成**才能开始 copy；copy 阶段常出现「99% 的 reduce 在等 1% 的 map」，所以「map 慢」会直接拖垮整体——这是为什么要先保证 map 均衡。
- 内存/磁盘平衡：`mapreduce.reduce.shuffle.input.buffer.percent` 控制 copy 阶段用多少堆内存缓存拉来的数据；设太小会频繁把拉取结果 spill 到磁盘再归并，多一轮 IO。
- 并行拉取：`mapreduce.reduce.shuffle.parallelcopies`（默认 5）决定同时拉几个 map 的输出；map 很多时调大能缩短 copy 阶段。
- JVM 复用：开 `jvm.reuse` 让多个 task 复用同一 JVM，省去频繁启停 JVM 的开销（对大量小 task 明显）。

### 🎓 博士生视角
- 两阶段归并：Map 端把「内存段」归并成有序 spill，再把多个 spill 归并成 final；Reduce 端把「网络拉来的内存段 + 本地 spill」再次归并。整条链是**分层多路归并**，每层把 `k` 个有序输入合成 1 个，归并扇入（fan-in）由内存决定，层数 ≈ `log_k(段数)`。
- 流式聚合的状态机：归并输出是「按 key 有序」的单流，Reducer 只需维护 `(current_key, accumulator)`：遇到新 key 就输出上一组结果并重置。这个**分组状态机**把「全量 value 列表」的内存压力降为「单 key 的增量累计」，是能在单机上处理超大数据集的关键。
- 容错语义：某个 map 输出拉取失败（节点宕机），Reduce 会向**其他存有该 block 副本的节点**重试拉取（HDFS 多副本的红利）；这再次体现「数据多副本」如何支撑计算层的粗粒度容错。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Reduce 端 Shuffle 包含哪几步？」标准答：**copy（fetch 线程并行拉取本分区数据）→ merge（内存与磁盘 spill 多路归并成有序流）→ 分组喂给 reduce 函数**。
- 易错口径：① Reduce 不是「等所有 map 完成后」才开始——copy 阶段与「最后一个 map 完成」几乎同步启动，但必须等齐；② Reduce 端也会 spill，不是只有 Map 端会；③ 归并是保序的多路归并，输出仍按 (key) 有序，所以 reduce 内无需再排序。
- 关联考点：与「归并排序」「外部排序的归并扇入」同族；与「为什么 reduce 数不能无限大」（每 reduce 都要独立 copy/merge 一轮开销）连考。
