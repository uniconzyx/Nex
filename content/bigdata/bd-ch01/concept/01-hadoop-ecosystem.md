# Hadoop 生态全景与组件分工

（中立陈述）Hadoop 自 2006 年从 Google 的 GFS 与 MapReduce 论文开源实现演化而来，如今是一个以 **HDFS（分布式存储）+ YARN（资源调度）+ 计算引擎（MapReduce/Spark/Flink）** 为核心的生态。HDFS 解决「数据放得下、丢不了、读得快」，YARN 解决「一堆机器上的计算任务如何公平且高利用率地跑」，上层计算引擎解决「如何用这套基础设施做批处理 / 流处理 / SQL 分析」。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### NameNode 元数据：INode 与块映射

```python
BLOCK = 128 * 1024 * 1024
class INode:
    def __init__(self, path):
        self.path = path
        self.blocks = []
        self.replicas = {}
dns = ["dn1", "dn2", "dn3"]
def create(path, size, rep=3):
    n = INode(path)
    nb = (size + BLOCK - 1) // BLOCK
    for i in range(nb):
        blk = "blk_" + path.replace("/", "_") + "_" + str(i)
        n.blocks.append(blk)
        n.replicas[blk] = dns[:rep]
    return n
f = create("/user/logs/access.log", 300 * 1024 * 1024)
print("file:", f.path)
print("size_mb:", 300)
print("block_size_mb:", BLOCK // (1024 * 1024))
print("num_blocks:", len(f.blocks))
print("block_0:", f.blocks[0], "replicas:", f.replicas[f.blocks[0]])
print("last_block_size_mb:", 300 - 2 * 128)
```

实际输出：

```text
file: /user/logs/access.log
size_mb: 300
block_size_mb: 128
num_blocks: 3
block_0: blk__user_logs_access.log_0 replicas: ['dn1', 'dn2', 'dn3']
last_block_size_mb: 44
```

> 出处：`examples/ex01.json`。改一处再看输出变没变，比读三遍解释有用。

### DataNode 块存储与校验和防静默损坏

```python
import hashlib
class DataNode:
    def __init__(self, name):
        self.name = name
        self.store = {}
    def put_block(self, blk, data):
        cs = hashlib.md5(data).hexdigest()
        self.store[blk] = (data, cs)
    def read_block(self, blk):
        data, cs = self.store[blk]
        if hashlib.md5(data).hexdigest() != cs:
            return None, "CORRUPT"
        return data, "OK"
dn = DataNode("dn1")
dn.put_block("blk_A", b"hello-hdfs")
data, status = dn.read_block("blk_A")
print("datanode:", dn.name)
print("stored_blocks:", list(dn.store.keys()))
print("read_status:", status)
print("read_data:", data.decode())
dn.store["blk_A"] = (b"hello-hdfs", "deadbeef")
_, bad = dn.read_block("blk_A")
print("after_tamper_status:", bad)
```

实际输出：

```text
datanode: dn1
stored_blocks: ['blk_A']
read_status: OK
read_data: hello-hdfs
after_tamper_status: CORRUPT
```

> 出处：`examples/ex02.json`。改一处再看输出变没变，比读三遍解释有用。

### 🧑‍💻 程序员视角
- 工程选型：公司落地大数据平台时，HDFS 通常只做「冷/温数据底座」，热数据走对象存储（S3/OSS）或 KV；不要为了「听起来先进」把 HDFS 当通用 NAS 用——它没有随机写、没有 POSIX 语义。
- 运维坑：HDFS 的「单 NameNode 瓶颈」在 2.x 之后由 **HA（QJM + ZKFC）** 解决，生产环境务必上 HA；否则 NameNode 一挂全集群不可用，且 fsimage 恢复慢。
- 版本惯例：Hadoop 3.x 默认块大小升到 128MB（早期 64MB），并引入纠删码（Erasure Coding）替代 3 副本以省存储；升级前用 `hdfs upgrade` 走滚动升级而非直接替换。

### 🎓 博士生视角
- 第一性原理：分布式存储的本质矛盾是「**一致性、可用性、分区容忍（CAP）三者不可兼得**」。HDFS 选择 **CP 倾向**——写入要求副本达标才返回成功（强一致写），牺牲一部分写可用性换取数据不丢；读则就近、弱一致窗口极小。
- 设计动机：GFS 论文的核心洞察是「**组件故障是常态而非异常**」，因此系统必须把「故障检测 + 自动恢复」做成一等公民，而不是事后补丁。HDFS 的块复制、心跳、安全模式都源于此。
- 与相邻理论关系：HDFS 的追加写 + 多副本，本质是 **primary-backup 复制（chain replication 的简化版）**；其元数据单点又催生了之后的 HBase（region 分片）来绕开单 NameNode 命名空间上限。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Hadoop 三大核心组件是什么？分别解决什么问题？」标准答：**HDFS（分布式存储）、YARN（资源管理与调度）、MapReduce/计算引擎（分布式计算）**。
- 易错口径：把「Hadoop = HDFS」或把 YARN 说成「只属于 MapReduce」都是错的——YARN 是独立资源层，Spark/Flink 都跑在它上面。
- 关联考点：CAP 定理在「分布式存储」类题里高频出现，要能结合 HDFS 说清它选了 CP；GFS 三论文（GFS / MapReduce / BigTable）是分布式系统经典出处，常被当作拓展考点。

---

## 二、从单机到分布式的动机：容量、吞吐、容错

（中立陈述）单机文件系统（ext4/xfs）受限于单盘容量、单机能挂载的盘数、以及单条总线的 IO 带宽；更致命的是「单机故障 = 数据不可用甚至丢失」。分布式文件系统把文件**分块（block）**后打散到成百上千台廉价机器，用「**分而治之 + 冗余**」同时解决三件事：横向扩容容量、并行提升聚合吞吐、用副本容忍节点故障。

### 🧑‍💻 程序员视角
- 踩坑：把 1 个 10GB 文件塞进单盘，磁盘满就真满了；HDFS 把文件切成 128MB 块分布到多机，单盘满只影响该机上的块，且副本机制让「坏盘」对用户透明。
- 调优：小文件（几 KB）直接上 HDFS 是灾难——每个文件在 NameNode 占约 150B~300B 元数据，100 万小文件就是几百 MB 内存且寻址慢；工程上用 **HAR、HBase、或合并成大文件（SequenceFile/ORC）** 治理。
- 吞吐误区：单流读 HDFS 未必比本地盘快（有网络开销），快的是**多客户端/多块并行**的聚合带宽。

### 🎓 博士生视角
- 容量与吞吐的数学：设单盘容量 C、单盘带宽 B、节点数 N、网络带宽 β，则聚合容量 ∝ N·C，聚合吞吐 ∝ min(N·B, 网络汇聚带宽)；当 N 足够大，**存储与计算解耦**才能各自独立扩展（这就是为什么存算分离架构兴起）。
- 容错的形式化：块副本数 r，单节点年故障率 p，则数据丢失概率约 `C(N,r)·p^r`（近似），取 r=3、p=0.01 时丢数据概率低到可接受量级——这是「3 副本」的工程最优解而非玄学。
- 寻址成本：大块（128MB）让「元数据量 = 总数据量 / 块大小」，把 NameNode 内存压力从 O(字节) 降到 O(块数)，是空间换管理成本的经典权衡。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「HDFS 为什么要把大文件切块、为什么默认 128MB？」标准答：切块便于**并行读写与负载均衡**；块大是为了**减少寻址开销与 NameNode 元数据量**，但过大则并行度下降、故障恢复慢，128MB 是经验平衡点。
- 易错口径：块大小不是「越大越好」，也不是文件系统簇大小的概念混淆；HDFS 块是**逻辑分块**，与磁盘物理扇区无关。
- 计算口径：给文件大小 F 与块大小 B，块数 = `ceil(F / B)`（最后一块可小于 B）；这是高频手算题。
