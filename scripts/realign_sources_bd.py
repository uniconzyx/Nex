# -*- coding: utf-8 -*-
"""bigdata 24 条笔记按「路径归属仓库」整列重排。

行序固定为 zoomcamp / spark / BigData-Notes / hadoop，
每条笔记里引用的路径必须落在该行自己的仓库中。
"""
import json
import os
import re

MANIFEST = "content/bigdata/_manifest.json"
CH_DIR = "content/bigdata"
RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

NOTES: dict[str, list[tuple[str, str]]] = {
"bd-ch01": [
 ("zoomcamp", "§1.2 二、从单机到分布式的动机：容量、吞吐、容错 · 读 `week5-batch/` 的批处理作业："
  "同一份数据在单机 pandas 与集群 Spark 上的耗时对比，"
  "就是「容量」与「吞吐」这两个动机的实测证据；"
  "而「容错」那一条要回到本章 §3.1「fsimage / edits 与 checkpoint」——"
  "单机只需担心文件损坏，集群必须假设节点随时会掉，这才逼出了 edits 日志"),
 ("spark", "§2.1 二、DataNode 与块存储（真正搬砖的劳工） · 读 "
  "`core/src/main/scala/org/apache/spark/rdd/` 里对 `HadoopRDD` 的实现："
  "Spark 把 HDFS 的 split 直接当分区，不搬数据只搬计算——"
  "这正是本节「DataNode 只负责按块存取、计算要挪过去」的结构性理由；"
  "读完再回看本章 §4.1「读取、短路读与小文件问题」，短路读绕开的正是这一层 RPC"),
 ("notes", "§3.1 二、fsimage / edits 与 checkpoint（安全模式） · 读根目录的 `HDFS.md`："
  "它把 NameNode 的内存结构、edits 追加、SecondaryNameNode 做 checkpoint 的时序画成一条时间线，"
  "并点明「edits 太长 → 重启要回放很久」这个痛点；"
  "这正是本节要讲的「为什么要 checkpoint」——"
  "它不是备份，而是「把 edits 折叠回 fsimage」的压缩动作"),
 ("hadoop", "§4.1 二、读取、短路读与小文件问题 · 读 "
  "`hadoop-hdfs-project/hadoop-hdfs/src/main/java/org/apache/hadoop/hdfs/server/namenode/` "
  "下的 `FSDirectory` 与 `INodeFile`："
  "目录树与块列表就是这两个类，内存占用随「文件数」而非「数据量」增长——"
  "这就是本节「小文件问题」的物理根源：一个 1KB 文件也要占一份 INode 加一条块列表"),
],
"bd-ch02": [
 ("zoomcamp", "§4.1 二、FIFO / Capacity / Fair 三种调度器 · 读 `week5-batch/` 的作业提交脚本："
  "同一份 Spark 作业换不同队列提交，排队时间差别很大——"
  "这就是三种调度器的差别落到「实际墙钟时间」上的样子；"
  "本节讲的是队列怎么分资源，而作业日志里从 `submitted` 到 `accepted by scheduler` "
  "之间的空窗，就是排队本身"),
 ("spark", "§3.1 二、归并（merge）与 Reduce 端的 fetch · 读 "
  "`core/src/main/scala/org/apache/spark/shuffle/` 的 `sort` 与 `hash` 两套实现："
  "Spark 要自己做 shuffle，是因为 MR 的 merge-fetch 模型对迭代式计算不友好；"
  "对照本章 §2.1「Partitioner：决定 Reduce 数与数据分布」，"
  "Spark 的 `HashPartitioner`/`RangePartitioner` 与 MR 的 Partitioner 是同一个契约——"
  "「同键必同分区」，差别只在 spill 与 merge 的策略"),
 ("notes", "§1.2 二、WordCount 端到端走读 · 读 `MapReduce.md`："
  "它用 WordCount 把 map → partition → sort → spill → merge → reduce 六个动作逐步展开，"
  "并演示「加 Combiner 前后 shuffle 数据量差多少」；"
  "本节要走通的就是这六步，"
  "而「求平均不能直接 Combiner、必须先传 (sum, count)」这条限制"
  "正是本章 §3.1 归并阶段最容易踩的坑"),
 ("hadoop", "§2.1 二、Partitioner：决定 Reduce 数与数据分布 · 读 "
  "`hadoop-mapreduce-project/hadoop-mapreduce-client/` 下的 `MapTask`/`ReduceTask`："
  "`MapTask.runNewMapper` 里就是 map → partition → sort → spill 的实际顺序，"
  "`partition` 那一步调用的正是 `Partitioner.getPartition`；"
  "所以「分区数设太大 → 大量小文件、太小 → 单分区 OOM」这两条经验，"
  "在源码里就是一行 `numReduceTasks` 的取值"),
],
"bd-ch03": [
 ("zoomcamp", "§4.1 二、ORC/Parquet 列式存储与谓词下推 · 读 `week4-analytics/` 的查询对比："
  "同一份数据存 CSV 与 Parquet，扫描列数少时后者快一个数量级——"
  "这就是本节「列裁剪 + 谓词下推」两条收益的实测；"
  "再配合本章 §2.2 的 `EXPLAIN` 验证法，"
  "能把「快了十倍」拆成「少读了多少列、少扫了多少分区」两个可对数"),
 ("spark", "§2.2 可运行代码：用 EXPLAIN 验证裁剪是否生效 · 读 "
  "`sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/optimizer/`："
  "`PushPredicateThroughJoin`、`ColumnPruning` 这些规则就是「谓词下推、列裁剪」"
  "在 Spark 侧的实现，Hive 的 `EXPLAIN` 里对应的也是同一批优化；"
  "先认清规则名，`EXPLAIN` 输出里的 `PartitionFilters` 才读得懂"),
 ("notes", "§1.2 二、表的生命周期与 LOCATION / EXTERNAL 工程约定 · 读 `Hive.md`："
  "删内部表连数据一起删、删外部表只删元数据，"
  "文档里配了 `LOCATION` 的对照实验，比背定义好记；"
  "本章 §1.1「可运行代码」那一节可以直接跑一遍这个对照——"
  "工程上默认建外部表，正因为「元数据可重建、数据不可重建」"),
 ("hadoop", "§3.1 二、执行引擎与 JOIN 策略选择（MapJoin vs CommonJoin） · 读 "
  "`hadoop-mapreduce-project/` 的作业提交入口："
  "Hive 把 HQL 编译成 MR/Tez 作业后，最终仍由 Hadoop 执行——"
  "这就是本节「Hive 只是编译器，执行归 Hadoop」的分工；"
  "MapJoin 的本质是「小表塞进 DistributedCache、大表在 map 阶段直接本地补全」，"
  "所以它省掉的正是 MR 那一次 shuffle"),
],
"bd-ch04": [
 ("zoomcamp", "§2.1 二、Transformation 与 Action 的判别 · 读 `week5-batch/` 的 Spark 作业："
  "`df.filter(...)` 之后不打 `show()`/`count()` 就什么都不执行，"
  "脚本里加不加 action 直接决定「有没有真的跑」；"
  "本节要练的判别方法在源码里就是「是否返回 RDD/DataFrame」——"
  "返回新 RDD 的是 transformation，返回数/列表/None 的是 action"),
 ("spark", "§1.1 二、不可变性与血缘（lineage）容错 · 读 "
  "`core/src/main/scala/org/apache/spark/rdd/RDD.scala`："
  "`getPartitions`/`compute`/`getDependencies` 三个抽象方法"
  "就是「分区列表 + 计算函数 + 依赖」的代码化，其余两个是优化信息；"
  "本节讲的 lineage 容错，本质就是「只要 `getDependencies` 还在，"
  "丢掉的 `compute` 就能重跑」"),
 ("notes", "§3.1 二、Stage 划分与 Task 数量计算 · 读 `Spark.md`："
  "它画出「窄依赖可流水线、宽依赖要 shuffle」的依赖图，"
  "并给出「Stage 数 = 宽依赖数 + 1」的算式；"
  "本章 §1.1 里的 `getDependencies` 是这个算式唯一的输入——"
  "所以「怎么少一个 Stage」等价于「怎么消掉一次宽依赖」"),
 ("hadoop", "§4.1 二、算子选择与数据倾斜（工程调优三板斧） · 读 "
  "`hadoop-hdfs-project/` 的副本机制做对照："
  "HDFS 用「多存几份」换容错，Spark 用「血缘重算」换容错，"
  "所以 Spark 不能随意 `checkpoint`——一旦截断血缘，重算就退化成重读；"
  "这正是本节「该不该 cache」的判据，"
  "也对应本章 §5.2「收尾：Spark 调优就是守住那三条前提」"),
],
"bd-ch05": [
 ("zoomcamp", "§4.1 二、宽依赖 / 窄依赖与 Shuffle 边界 · 读 `week5-batch/` 的 Spark SQL 作业日志："
  "`spark.sql.adaptive.enabled=true` 后，`SortMergeJoin` 会在运行时统计出来后"
  "被改写成 `BroadcastHashJoin`，日志里能看到 `Plan changed`；"
  "所以「Shuffle 边界在哪」不只看语法，还要看这一层运行时改写——"
  "本节讲边界，AQE 讲的是边界可以在跑起来之后重新画"),
 ("spark", "§2.1 二、谓词下推、列裁剪、常量折叠与 JOIN 重排 · 读 "
  "`sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/` 的目录结构："
  "`analyzer/`（解析）→ `optimizer/`（逻辑优化）→ `planner/`（物理计划）→ `codegen`（生成字节码），"
  "目录本身就是四阶段的证据；"
  "本节列的四条规则全部住在 `optimizer/` 里，"
  "所以 `EXPLAIN` 里 `Analyzed` 之前不该出现下推、`Optimized` 之后必须出现"),
 ("notes", "§1.1 二、Dataset 的类型安全与编码器（Encoder） · 读 `Spark.md` 的 Spark SQL 篇："
  "DataFrame 携带 schema、能进优化器，RDD 是黑盒函数——"
  "「结构化信息就是优化空间」这句话的来源就在这里；"
  "本节 Encoder 是同一件事再往前一步：Dataset 多的是「编译期类型 + 二进制编码」，"
  "既保留类型检查、又不付对象序列化的代价"),
 ("hadoop", "§4.2 三、执行计划读法与 Hive Metastore 集成 · 读 `hive/` 的元数据表设计："
  "库/表/分区/列都存 MySQL，Spark SQL 通过 `HiveExternalCatalog` 读写同一份元数据——"
  "这就是「湖仓共用 Metastore」的由来；"
  "本节读计划时看到的 `Location`、`PartitionFilters` 都来自这张表，"
  "所以元数据一旦不同步，就会出现「表存在但扫 0 行」这类怪现象"),
],
"bd-ch06": [
 ("zoomcamp", "§1.1 二、分层落地规范：命名、调用约束与自动化体检 · 读 `week4-analytics/` 的数仓作业："
  "从原始 JSON 到宽表再聚合到指标表，每一层的输入输出都是独立的表——"
  "「层与层的调用关系」就是本节规范的落地样本；"
  "规范里最容易破的两条是「下游不许跨层读 ODS」与「同层不许互相依赖」，"
  "一旦破了，血缘图就从树变成环"),
 ("spark", "§4.1 二、数据倾斜调优、元数据与数据血缘 · 读 "
  "`sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/` 的写入路径："
  "`repartition` 与 `coalesce` 在写出前决定文件数，"
  "分区数乘作业批次就是「每天新增多少小文件」；"
  "血缘由这些写入路径的输入表反推出来，"
  "所以小文件治理与血缘治理在同一个位置动手"),
 ("notes", "§2.1 二、星型模型 vs 雪花模型：JOIN 次数与存储的定量取舍 · 读 "
  "`BigData-Notes` 里的数仓篇："
  "「先声明粒度再选维度」这条顺序反了，后面所有指标口径都会漂移，"
  "文档给了「订单事实表」的完整推演；"
  "本节讲的定量取舍就落在这个推演上："
  "雪花省了重复存储，代价是每查一层多一次 JOIN——「星型优先」不是审美而是算术"),
 ("hadoop", "§3.1 二、指标口径治理：原子指标 / 派生指标与口径一致性 · 读 "
  "`hadoop-yarn-project/` 的队列与容量调度："
  "`CapacityScheduler` 决定「哪个队列先跑」，"
  "指标口径的「日/时切换」要靠定时任务按时产出，任务抢不到资源就会断档；"
  "所以本节把口径分「原子 + 派生」两层，"
  "同时也是为了让调度只需盯住原子层那张表"),
],
}


def split_note(note: str) -> tuple[str, str]:
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals(cid: str, ordered: list[tuple[str, str]]) -> None:
    path = os.path.join(CH_DIR, cid, "goals.md")
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    assert len(row_idx) == len(ordered), (cid, len(row_idx))
    for i, (_, note) in zip(row_idx, ordered):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        raw = fb.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8"))
    for ch in data["chapters"]:
        cid = ch["id"]
        ordered = NOTES[cid]
        repos = ch["resources"]["github"]
        want = ["data-engineering-zoomcamp", "spark", "BigData-Notes", "hadoop"]
        got = [r.split("/")[-1] for r in repos]
        assert got == want, (cid, got)
        ch["resources"]["github_notes"] = [n for _, n in ordered]
        rewrite_goals(cid, ordered)
        print(f"ok {cid} {' | '.join(got)}")
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if nl == "\r\n":
        out = out.replace("\n", "\r\n")
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("\n完成 6 章 24 条整列重排")


if __name__ == "__main__":
    main()
