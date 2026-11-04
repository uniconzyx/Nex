# -*- coding: utf-8 -*-
"""bigdata 学科来源笔记（6 章 24 条）。

病因与 data / fundamentals 早期章节同构：6 章共用同一套 4 仓库
（zoomcamp / spark / BigData-Notes / hadoop）+ 同一套
「§x.y 讲「某话题」时读某路径」模板，编号全部虚构
（如 bd-ch01 只有 4 个小节、却写到 §3.1；bd-ch06 写到 §4.3）。

本批按 concept 真实 `##` 标题逐节重写，并顺带纠正两条仓库错配：
  · bd-ch03#2 原写 `sql/catalyst/...` 却归在 hadoop 仓库行 → 改指 spark 的 optimizer
  · bd-ch05#4 原写 `hive/` 却归在 hadoop 仓库行 → 改指 spark 的 HiveExternalCatalog
"""
import json
import os
import re

MANIFEST = "content/bigdata/_manifest.json"
CH_DIR = "content/bigdata"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

# 仓库序：DataTalksClub/data-engineering-zoomcamp · apache/spark ·
#         heibaiying/BigData-Notes · apache/hadoop
NOTES: dict[str, list[str]] = {
    # ---------------- bd-ch01 Hadoop 生态与 HDFS 架构 ----------------
    "bd-ch01": [
        "§1.2 二、从单机到分布式的动机：容量、吞吐、容错 · 读 "
        "`week5-batch/` 的批处理作业："
        "同一份数据在单机 pandas 与集群 Spark 上的耗时对比，"
        "就是「容量」与「吞吐」这两个动机的实测证据；"
        "而「容错」那一条要回到本章 §3.1「fsimage / edits 与 checkpoint」——"
        "单机靠文件不损坏，集群必须假设节点随时会坏，这才有了 edits 日志",

        "§2.1 二、DataNode 与块存储（真正搬砖的劳工） · 读 "
        "`core/src/main/scala/org/apache/spark/rdd/` 里对 `HadoopRDD` 的实现："
        "Spark 把 HDFS 的 split 直接当分区，不搬数据只搬计算——"
        "这正是本节「DataNode 只负责按块存取、计算要挪过去」的结构性理由；"
        "读完再回看本章 §4.1「读取、短路读与小文件问题」，"
        "短路读绕开的正是这一层的 RPC",

        "§3.1 二、fsimage / edits 与 checkpoint（安全模式） · 读 "
        "`hadoop-hdfs-project/hadoop-hdfs/src/main/java/org/apache/hadoop/hdfs/server/namenode/` "
        "下的 `FSDirectory` 与 `INodeFile`："
        "目录树与块列表就是这两个类，"
        "内存占用随「文件数」而非「数据量」增长——"
        "这就是本章 §4.1 里「小文件问题」的物理根源："
        "一个 1KB 文件也要占一份 INode 和一条块列表",

        "§4.1 二、读取、短路读与小文件问题 · 读根目录的 `HDFS.md`："
        "它用一张流程图画出「客户端 → DN1 → DN2 → DN3 → ack 回传」的写入 pipeline，"
        "并给出「哪个环节挂掉会触发重试」的对照；"
        "本节讲的读路径与它是镜像关系："
        "写是 pipeline、读是就近选择，"
        "两者共用同一套「副本 + 校验和」的容错底座",
    ],

    # ---------------- bd-ch02 MapReduce 原理与 YARN 调度 ----------------
    "bd-ch02": [
        "§1.2 二、WordCount 端到端走读 · 读 "
        "`hadoop-mapreduce-project/hadoop-mapreduce-client/` 下的 `MapTask`/`ReduceTask`："
        "`MapTask.runNewMapper` 里就是 map → partition → sort → spill 的实际顺序，"
        "与本节的数据流图一一对应；"
        "看完再回看本章 §3.1「归并（merge）与 Reduce 端的 fetch」——"
        "spill 落盘、merge 合并、fetch 拉取是三个不同的磁盘动作，"
        "调优点完全不一样",

        "§2.1 二、Partitioner：决定 Reduce 数与数据分布 · 读 "
        "`week5-batch/` 的作业调优笔记："
        "「分区数设太大 → 大量小文件」「设太小 → 单分区 OOM」这两条经验，"
        "在本章 §3.1 有对应的计算式——"
        "分区数 = Reduce 任务数 = 输出文件数，"
        "所以「文件数」这个结果是被 Partitioner 这一行代码决定的",

        "§3.1 二、归并（merge）与 Reduce 端的 fetch · 读 "
        "`MapReduce.md`："
        "它用 WordCount 演示「加 Combiner 前后 shuffle 数据量差多少」，"
        "并强调「求平均不能直接 Combiner、必须先传到 (sum, count)」这条限制；"
        "这正是本章 §2.1 里 Combiner 语义边界的来由——"
        "Combiner 要求运算可结合，而平均值不满足",

        "§4.1 二、FIFO / Capacity / Fair 三种调度器 · 读 "
        "`resource-managers/yarn/src/main/scala/org/apache/spark/deploy/yarn/`："
        "`ApplicationMaster` 申请 Container、`ExecutorAllocationManager` 动态伸缩，"
        "落地的是「RM 管资源、AM 管作业」这条分工；"
        "本节三种调度器的差别就落在「Container 怎么分给不同队列」上，"
        "而 Spark 侧只能看到 AM 最终拿到的那些 Container",
    ],

    # ---------------- bd-ch03 Hive：数据仓库与 HQL ----------------
    "bd-ch03": [
        "§1.2 二、表的生命周期与 LOCATION / EXTERNAL 工程约定 · 读 "
        "`Hive.md`："
        "删内部表连数据一起删、删外部表只删元数据，"
        "文档里配了 `LOCATION` 的对照实验，比背定义好记；"
        "本章 §1.1「可运行代码」那一节可以直接跑一遍这个对照——"
        "工程上默认建外部表，正是因为「元数据可重建、数据不可重建」",

        "§2.2 可运行代码：用 EXPLAIN 验证裁剪是否生效 · 读 "
        "`sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/optimizer/`："
        "`PushPredicateThroughJoin`、`ColumnPruning` 这些规则就是「谓词下推、列裁剪」"
        "在 Spark 侧的等价物，Hive 的 `EXPLAIN` 输出里对应的也是同一批优化；"
        "本节讲的是「怎么验证裁剪生效」，而本节所依赖的判据就在这份规则表里——"
        "看懂了规则名，`EXPLAIN` 里的 `PartitionFilters` 才有意义",

        "§3.1 二、执行引擎与 JOIN 策略选择（MapJoin vs CommonJoin） · 读 "
        "`sql/core/src/main/scala/org/apache/spark/sql/execution/joins/`："
        "`BroadcastHashJoinExec` 与 `SortMergeJoinExec` 是 MapJoin / CommonJoin 的同一组选择，"
        "判据都是「一侧能否装进内存」；"
        "本章 §2.1「分桶表（Bucket）」也是为了这条判据服务的——"
        "分桶让 join 键落在同一桶内，才能省掉整轮 shuffle",

        "§4.1 二、ORC/Parquet 列式存储与谓词下推 · 读 "
        "`week4-analytics/` 的查询对比："
        "同一份数据存 CSV 与 Parquet，扫描列数少时后者快一个数量级——"
        "这就是本节「列裁剪 + 谓词下推」两条收益的实测；"
        "再对照本章 §2.2 的 `EXPLAIN` 验证法，"
        "就能把「快了十倍」拆成「少读了多少列、少扫了多少分区」两个可核对的数",
    ],

    # ---------------- bd-ch04 Spark 核心：RDD 与惰性求值 ----------------
    "bd-ch04": [
        "§1.1 二、不可变性与血缘（lineage）容错 · 读 "
        "`core/src/main/scala/org/apache/spark/rdd/RDD.scala`："
        "`getPartitions`/`compute`/`getDependencies` 三个抽象方法"
        "就是「分区列表 + 计算函数 + 依赖」的代码化，其余两个是优化信息；"
        "本节讲的 lineage 容错，本质上就是「只要 `getDependencies` 还在，"
        "丢了的 `compute` 可以重跑」；"
        "对照本章 §4.1 的副本容错看：HDFS 靠多存几份、Spark 靠重算，"
        "前者贵在存储、后者贵在计算",

        "§2.1 二、Transformation 与 Action 的判别 · 读 "
        "`week5-batch/` 的 Spark 作业："
        "`df.filter(...)` 之后不打 `show()`/`count()` 就什么都不执行，"
        "脚本里加不加 action 直接决定「有没有真的跑」；"
        "本节要练的判别方法在源码里就是「是否返回 RDD/DataFrame」——"
        "返回新 RDD 的是 transformation，返回非 RDD（数、列表、None）的是 action",

        "§3.1 二、Stage 划分与 Task 数量计算 · 读 `Spark.md`："
        "它画出「窄依赖可流水线、宽依赖要 shuffle」的依赖图，"
        "并给出「Stage 数 = 宽依赖数 + 1」的算式；"
        "本章 §1.1「RDD 五大特性」里的 `getDependencies` 是这个算式唯一的输入——"
        "所以「怎么少一个 Stage」等价于「怎么消掉一次宽依赖」",

        "§4.1 二、算子选择与数据倾斜（工程调优三板斧） · 读 "
        "`hadoop-hdfs-project/` 的副本机制做对照："
        "HDFS 用「多存几份」换容错，Spark 用「血缘重算」换容错，"
        "这决定了 Spark 不能随意 `checkpoint`——一旦截断血缘，"
        "重算就退化成重读，这正是本节调优三板斧里「该不该 cache」的判据；"
        "再看本章 §5.2「收尾：Spark 调优就是守住那三条前提」，"
        "三条前提全部指向「别让一次宽依赖白白多跑一遍」",
    ],

    # ---------------- bd-ch05 Spark SQL、DataFrame 与 Catalyst ----------------
    "bd-ch05": [
        "§1.1 二、Dataset 的类型安全与编码器（Encoder） · 读 `Spark.md` 的 Spark SQL 篇："
        "DataFrame 携带 schema、能进优化器，RDD 是黑盒函数——"
        "「结构化信息就是优化空间」这句话的来源就在这里；"
        "本节讲的 Encoder 是同一件事再往前一步："
        "Dataset 比 DataFrame 多的是「编译期类型 + 二进制编码」，"
        "所以它既保留类型检查、又不付对象序列化的代价",

        "§2.1 二、谓词下推、列裁剪、常量折叠与 JOIN 重排 · 读 "
        "`sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/` 的目录结构："
        "`analyzer/`（解析）→ `optimizer/`（逻辑优化）→ `planner/`（物理计划）→ `codegen`（生成字节码），"
        "目录本身就是四阶段的证据；"
        "本节列的四条规则全部住在 `optimizer/` 里——"
        "看 `EXPLAIN` 输出时，`Analyzed` 之前不该出现下推，`Optimized` 之后必须出现",

        "§3.1 二、全阶段代码生成（Whole-Stage Codegen） · 读 "
        "`sql/core/src/main/scala/org/apache/spark/sql/execution/` 下的 "
        "`WholeStageCodegenExec`："
        "它把一串算子熔成一个 `doExecute` 方法，"
        "省掉每个算子之间「吐出 Row → 再读回 Row」的虚调用；"
        "本节讲「为什么要 codegen」，这条在 `EXPLAIN` 里表现为 `*(n)` 前缀——"
        "带星号的是已熔断的 stage，没有星号的就是被拆开了",

        "§4.2 三、执行计划读法与 Hive Metastore 集成 · 读 "
        "`sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/catalog/` 下的 "
        "`HiveExternalCatalog`："
        "库/表/分区/列都存进 MySQL，Spark SQL 通过它读写同一份元数据——"
        "这就是「湖仓共用 Metastore」的由来；"
        "本节「执行计划读法」里看到的 `Location`、`PartitionFilters` 都来自这张表，"
        "所以元数据一旦不同步，计划里就会出现「表存在但扫 0 行」这类怪现象",
    ],

    # ---------------- bd-ch06 离线数仓实战：分层建模与调度 ----------------
    "bd-ch06": [
        "§1.1 二、分层落地规范：命名、调用约束与自动化体检 · 读 "
        "`week4-analytics/` 的数仓作业："
        "从原始 JSON 到宽表再聚合到指标表，每一层的输入输出都是独立的表——"
        "「层与层的调用关系」就是本节要讲的规范落地；"
        "规范里最容易破的两条是「下游不许跨层读 ODS」与「同层不许互相依赖」，"
        "这两条一旦破了，血缘图就从树变成环，"
        "本章 §4.1「元数据与数据血缘」也就无从生成",

        "§2.1 二、星型模型 vs 雪花模型：JOIN 次数与存储的定量取舍 · 读 "
        "`BigData-Notes` 里的数仓篇："
        "「先声明粒度再选维度」这条顺序反了，后面所有指标口径都会漂移，"
        "文档给了「订单事实表」的完整推演；"
        "本节讲的定量取舍就落在这个推演上："
        "雪花把维度再拆一级省了重复存储，代价是每查一层多一次 JOIN，"
        "所以「星型优先」不是审美，是 JOIN 次数换存储的算术",

        "§3.1 二、指标口径治理：原子指标 / 派生指标与口径一致性 · 读 "
        "`week4-analytics/` 里的聚合脚本："
        "`count`/`nunique` 混用会把「订单数」算成「商品数」，"
        "指标定义必须先写清再写代码；"
        "本节把这件事拆成「原子指标 + 修饰词 = 派生指标」两层，"
        "就是为了让口径只在原子层定义一次——"
        "派生层任何不一致，都能顺着定义追到同一个原子指标",

        "§4.1 二、数据倾斜调优、元数据与数据血缘 · 读 "
        "`sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/` 的写入路径："
        "`repartition` 与 `coalesce` 在写出前决定文件数，"
        "分区数乘作业批次就是「每天新增多少小文件」；"
        "而在 YARN 侧，`hadoop-yarn-project/` 的 `CapacityScheduler` 决定"
        "「哪个队列先跑」——基线任务必须放在高优先级队列，"
        "否则会被离线回刷任务挤掉（这就是本节讲的 SLA 风险）",
    ],
}


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        raw = fb.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8"))
    changed = 0
    for ch in data.get("chapters", []):
        cid = ch.get("id") or ch.get("chapter_id")
        notes = NOTES.get(cid)
        if not notes:
            continue
        res = ch.get("resources") or {}
        cur = res.get("github_notes") or []
        if len(cur) != len(notes):
            print(f"!! {cid}: 原 {len(cur)} 条 / 新 {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        ch["resources"] = res
        ok, msg = rewrite_goals_table(cid, notes)
        print(f"{'ok' if ok else '!!'} {cid}: manifest 已改，goals {msg}")
        changed += 1

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if nl == "\r\n":
        out = out.replace("\n", "\r\n")
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(f"\n完成 {changed} 章")


if __name__ == "__main__":
    main()
