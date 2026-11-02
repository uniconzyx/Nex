# §5 bd-ch01 实战手记：凯喵带你把 HDFS 用「挂」

> 前四节把生态、架构、副本、读写讲透了。这一节凯喵把 HDFS 运维里最容易「集群半夜告警」的 12 个现场摆出来——副本丢了、NN 卡重启、小文件压垮元数据、短路读没配。每个都是值班电话换来的教训。

### 现场一：副本因子设成 1 省空间，丢块一起丢

凯喵为了「省存储」把 `dfs.replication=1`，结果一个 DataNode 硬盘坏掉，直接丢了一整批块，作业全红。默认 3 副本是「同机架 2 + 跨机架 1」，能扛整机架断电。生产保持 ≥3；冷数据改用 Erasure Coding（RS-6-3 把 3x 开销降到约 1.5x）。

```xml
<!-- hdfs-site.xml -->
<property>
  <name>dfs.replication</name>
  <value>3</value>   <!-- ✅ 生产至少 3 -->
</property>
<!-- 冷数据改用 EC，省空间且仍可恢复 -->
<property>
  <name>dfs.namenode.ec.policies.enabled</name>
  <value>RS-6-3-1024k</value>
</property>
```

### 现场二：单 NameNode 不做 checkpoint，重启小时级

凯喵的公司只部署一个 NameNode，又没 SecondaryNameNode，跑了几个月 `edits` 文件涨到几百 GB。重启时要回放全部 editlog，启动时间从小秒级变成小时级，业务停摆半天。解法：QJM + ZKFC 做 HA（Standby 自动 checkpoint），或至少部署 SecondaryNameNode 并监控 Last checkpoint 时间。

```bash
# 手动触发 checkpoint（仅 SecondaryNameNode 场景）
hdfs dfsadmin -saveNamespace
# 看上次 checkpoint 时间，超时即告警
hdfs dfsadmin -report | grep -i "Last"
```

### 现场三：把 SecondaryNameNode 当「热备」是最大误解

凯喵新人以为 SecondaryNameNode 挂了 NameNode 能自动接管——大错。SNN 只做 **fsimage + edits 定期合并**，减轻 NN 内存压力，**不接管服务、不保存最新 edits**。真正的热备是 HA 里的 Standby NameNode（共享 editlog，秒级切换）。别把 SNN 当容灾。

```text
NameNode        : 接收读写，写 edits，内存维护元数据
SecondaryNameNode: 周期性 pull edits + fsimage 合并回传（不是备份！）
Standby NN(HA)  : 实时读共享 edits，随时可切主（这才是热备）
```

### 现场四：小文件海量，NameNode 内存被元数据撑爆

凯喵的爬虫每小时落几百万个几 KB 的小文件，三个月后 NameNode 内存 OOM、集群不可用。HDFS 为**每个文件/目录/块**在 NN 内存存约 150 字节元数据，小文件多了元数据开销远超数据本身。治理：HAR 归档、HBase/对象存储存小文件、写时合并（ORC + 大 block）。

```bash
# 用 HAR 把海量小文件归档成一个大文件
hadoop archive -archiveName logs.har -p /data/logs /data/archive
```

### 现场五：机架感知没配，跨机架副本失效

凯喵的集群所有 DataNode 被误认为同一机架，3 副本全落在一个机柜。结果那个机柜交换机一挂，整批块不可用。副本放置策略依赖**机架感知**（`net.topology.script` 返回每节点的机架路径），否则「同机架 2 + 跨机架 1」退化成「同机柜 3」，容错归零。

```xml
<property>
  <name>net.topology.script.file.name</name>
  <value>/etc/hadoop/rack-awareness.sh</value>  <!-- 返回 /rack1 之类 -->
</property>
```

### 现场六：写入流水线中对端慢，整条 pipeline 卡住

凯喵的大文件写入时，一个 DataNode 磁盘 IO 慢，整条 pipeline 吞吐被它拖垮。HDFS 写入是**流水线复制**（client→DN1→DN2→DN3），任一环节慢都拉低整体。监控各 DN 的 `BytesWritten` 速率，慢节点及时下线（`dfs.datanode.failed.volumes.tolerated`）。

```bash
# 查看各 DN 写入速率，定位慢节点
hdfs dfsadmin -report
```

### 现场七：安全模式下写数据全部失败

凯喵重启 NN 后程序狂报「NameNode is in safe mode」。安全模式是 NN 启动时的保护态：先等足够比例的块上报（默认 `dfs.namenode.safemode.threshold-pct=0.999`），确认块齐全才退出。期间**只读不写**。等它自动退出；确认数据齐全可手动 `leave`。切勿贸然强制离开。

```bash
hdfs dfsadmin -safemode get      # 查状态
hdfs dfsadmin -safemode wait     # 脚本里等它退出
# hdfs dfsadmin -safemode leave  # 仅确认数据齐全后手动退出
```

### 现场八：短路读（short-circuit）没开，本地读也走网络

凯喵的 NodeLocal 任务读本地块却要走 TCP 回路，延迟高。HDFS 支持**短路读**：client 与 DN 同机时直接读本地文件、绕过网络栈。需配置 `dfs.client.read.shortcircuit=true` 且 unix socket 路径可写。同机计算（Spark on YARN）收益明显。

```xml
<property>
  <name>dfs.client.read.shortcircuit</name>
  <value>true</value>
</property>
<property>
  <name>dfs.domain.socket.path</name>
  <value>/var/run/hadoop/dn.socket</value>
</property>
```

### 现场九：块大小设太小，Map 数爆炸

凯喵把 `dfs.blocksize` 设成 32MB（甚至默认被改），1TB 数据产生几万个块，NN 元数据压力大、Map 任务数爆炸。Hadoop 3 默认 128MB（甚至 256MB），大文件场景块越大、元数据越少、吞吐越高。按文件大小调。

```xml
<property>
  <name>dfs.blocksize</name>
  <value>134217728</value>  <!-- 128 MB，大文件友好 -->
</property>
```

### 现场十：心跳/块报告超时，误判 DN 死亡触发大量复制

凯喵的 DN 因 GC 停顿太久，NN 在 `dfs.namenode.heartbeat.recheck-interval` 内没收到心跳，把它标记为 dead，立刻在别的 DN 补副本，网络被打满。调大超时与 `heartbeat.interval`，并给 DN 足够堆内存避免长 GC 停顿。

```xml
<property>
  <name>dfs.namenode.heartbeat.recheck-interval</name>
  <value>300000</value>  <!-- 5 分钟再判定死亡，避免 GC 抖动误杀 -->
</property>
```

### 现场十一：回收站默认关，rm -r 直接没

凯喵手滑 `hdfs dfs -rm -r /data/tmp`，文件瞬间消失不可恢复。HDFS 回收站默认**关闭**，需开 `fs.trash.interval>0`，删除的文件先进 `/user/.../.Trash`，到期才真删。重要目录操作前先确认回收站开着。

```xml
<property>
  <name>fs.trash.interval</name>
  <value>1440</value>  <!-- 1 天保留，误删可救 -->
</property>
```

### 现场十二：fsimage 从不备份，NN 元数据损坏即全损

凯喵的 NN 元数据目录只在一块盘上，磁盘坏道导致 fsimage 损坏，集群起不来。NN 的元数据是「命根子」，必须：① 配 HA 共享存储（QJM/ZK）；② 定期把 fsimage 备份到异地；③ `dfs.namenode.name.dir` 配多目录（多盘）冗余。

```xml
<property>
  <name>dfs.namenode.name.dir</name>
  <value>/data/nn,/data2/nn</value>  <!-- 多盘冗余，坏一块不丢 -->
</property>
```

> 凯喵总结：HDFS 的事故几乎都集中在「单点」「元数据」「副本」「小文件」——NN 不 HA、副本设 1、小文件炸内存、机架感知没配。把这 12 个现场刻进值班手册，半夜少接三通告警电话。

## 三视角解析
### 🧑‍💻 程序员视角
副本因子设成 1 省空间，结果一台机器坏就丢块——HDFS 的容错完全建立在副本上，省副本等于放弃可靠性。单 NameNode 不做 checkpoint，`edits` 无限增长，重启时回放要几小时。把 SecondaryNameNode 当成「备用 NameNode」是经典误解：它只做 checkpoint 合并，不提供故障切换，HA 要靠 Standby NameNode + ZKFC。小文件海量会把 NameNode 内存撑爆——每个文件约 150~300 字节元数据，一亿小文件就是几十 GB。

### 🎓 博士生视角
HDFS 的设计假设是「大文件、顺序读、高吞吐、容忍高延迟」，因此它牺牲了随机写与低延迟。NameNode 把所有元数据放内存，使「文件数」成为硬上限，这也是 Federation（多 NameNode 分片命名空间）与 Ozone（对象存储）出现的动因。副本放置策略（同机架 1 + 跨机架 2）在「可靠性」与「跨机架带宽成本」之间取平衡，理解这一点才能解释「为什么不是所有副本都放不同机架」。

### 📚 考研者视角
大数据面试高频：
1. **HDFS 架构**：NameNode/DataNode 职责、块大小（128MB）、副本机制。
2. **读写流程**：写入的 pipeline、读取的短路读、`fsimage` 与 `edits`。
3. **HA**：ZKFC + Standby、脑裂防护（fencing）。
4. **小文件问题**：成因（NameNode 内存）与治理（HAR、合并、对象存储）。
