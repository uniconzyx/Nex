# bd-ch02 · MapReduce 与 YARN 调优实战：凯喵的踩坑手册

> §1–§4 讲原理，这一节把「跑得慢/跑错」的常见原因和治法列成清单。大数据作业调优，80% 的功夫在 Shuffle 和调度。

### Combiner：本地先 reducer 省带宽

Combiner 在 map 端本地先做一轮聚合，把 `(word,1)` 合并成 `(word,n)` 再发往 reduce，网络传输量可能降一个数量级。注意 Combiner 必须满足交换律结合律，否则结果错。

```java
job.setCombinerClass(WordCountReducer.class);  // 复用 reducer 逻辑做本地预聚合
```

### Partitioner 决定数据去哪

默认 `HashPartitioner` 按 key 哈希分桶。若 key 分布不均（如按用户 id，少数大 V 数据极多），会出现数据倾斜——个别 reduce 拖死全作业。凯喵的做法：对热点 key 做加盐/二次聚合打散。

### Shuffle 的磁盘溢出与合并

Map 输出先写环形缓冲，满了 spill 到磁盘，最后 merge。spill 次数过多 = 磁盘 IO 爆炸。调大 `mapreduce.task.io.sort.mb`、合理设 `spill.percent` 能减少 spill 与 merge 轮次。

### YARN 的 RM / AM / NM 三角色

ResourceManager 全局调度、NodeManager 管单节点资源、ApplicationMaster 是**每作业一个**、负责任务级调度与容错。RM 挂（未配 HA）全集群瘫痪；AM 挂 RM 会重启它。生产 RM 必须上 HA（ZKFC + ZK）。

### Capacity vs Fair 调度差异

Capacity 的 `capacity` 是**保底占比**，`maximum-capacity` 才是弹性上限；不设上限的队列借不到别人空闲资源。Fair 里不设 `weight` 才平分，设了权重按权重分，且靠 preemption 超时抢资源——不是「切过去就自动公平」。

### 小文件问题的根源

HDFS 块大、元数据贵，海量小文件让 NameNode 内存爆、map 数爆炸（一个小文件一个 split 一个 map）。凯喵用 HAR、CombineFileInputFormat、或上游合并来治本。

### 数据倾斜：热点 key 怎么治

症状：99% reduce 早结束，剩一两个卡 99%。治法：抽样找热点 key、对热点加随机前缀打散（两阶段聚合）、或单独处理大 key。倾斜不解决，加机器也没用。

### Speculative 执行救慢任务

同一任务因机器慢/磁盘忙明显落后时，YARN 启一个**推测副本**抢跑，先完成者胜。能掩盖偶发慢节点，但会使资源翻倍——对严重倾斜的作业可能火上浇油，必要时关掉。

### 计数器与调优观测

MapReduce 内置计数器（记录数、spill 次数、GC 时间）是调优的仪表盘。凯喵每次调优先看计数器：spill 多 → 调排序内存；GC 高 → 调堆；shuffle 慢 → 看网络与分区。

### 作业级与集群级角色分清

ApplicationMaster 是**每作业一个、随作业生死**；RM 才是全局唯一。别把「AM 挂了集群挂」和「RM 挂了集群挂」混为一谈——前者只丢当前作业，后者要 HA 才扛得住。

### 用 Combiner 减少网络传输

把 reducer 逻辑同时注册为 combiner，map 端先本地聚合，网络只传压缩后的结果。

```java
job.setCombinerClass(WordCountReducer.class);
```

### 自定义 Partitioner 打散热点 key

默认哈希分区遇到少数超大 key 会倾斜，给热点 key 加随机前缀做二次聚合。

```java
int p = (key.hashCode() & Integer.MAX_VALUE) % numReduce;
```

### 调大排序内存减少 spill

map 输出在内存里排序，内存太小会频繁 spill 到磁盘再 merge。按数据量调 `io.sort.mb`。

```xml
<property>
  <name>mapreduce.task.io.sort.mb</name>
  <value>512</value>
</property>
```

## 三视角解析
### 🧑‍💻 程序员视角
Combiner 是「本地 reduce」，能大幅减少 shuffle 数据量，但它只能用于「满足结合律与交换律」的聚合（求和可以，求平均不行——除非传 (sum, count)）。Partitioner 决定数据去哪个 Reduce，默认哈希可能导致倾斜，自定义分区要保证「热点 key 被打散」。Shuffle 的溢写（spill）次数由缓冲区大小与溢写阈值决定，调大缓冲区能减少磁盘 IO。YARN 的 RM/AM/NM 三角色里，AM 是「每个作业的管家」，它挂了作业就失败。

### 🎓 博士生视角
MapReduce 的性能瓶颈几乎总在 shuffle：`map 输出 → 分区 → 排序 → 溢写 → 归并 → reduce 拉取`，每一段都涉及磁盘与网络。优化的本质是「减少数据搬运」：Combiner 在 map 端预聚合、Partitioner 均衡分区、压缩中间结果。YARN 把「资源管理」与「作业调度」分离，RM 只管资源、AM 管作业生命周期，这一设计使多种计算框架（MR/Spark/Flink）能共享同一集群。

### 📚 考研者视角
大数据面试高频：
1. **MapReduce 流程**：split → map → shuffle（分区/排序/溢写/归并）→ reduce。
2. **Combiner 的前提**：结合律与交换律，为什么求平均不能直接用。
3. **数据倾斜**：表现（少数 Reduce 慢）、解法（加盐、自定义分区、MapJoin）。
4. **YARN 架构**：RM/AM/NM/Container 的职责与交互流程。

```text
05-mapreduce-tuning-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] Combiner：本地先 reducer 省带宽  (java)
    |
    v
  [02] Partitioner 决定数据去哪  (-)
    |
    v
  [03] Shuffle 的磁盘溢出与合并  (-)
    |
    v
  [04] YARN 的 RM / AM / NM 三角色  (-)
    |
    v
  [05] Capacity vs Fair 调度差异  (-)
    |
    v
  [06] 小文件问题的根源  (-)
    |
    v
  [07] 数据倾斜：热点 key 怎么治  (-)
    |
    v
  [08] Speculative 执行救慢任务  (-)
    |
    v
  [... 其余 5 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
