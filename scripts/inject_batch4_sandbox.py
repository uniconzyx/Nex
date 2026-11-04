# -*- coding: utf-8 -*-
"""批次四：给 bigdata / data / java / agent 8 章补 sandbox。

与 inject_batch3_sandbox.py 同一套路（详见那个文件的头部说明）：
把 sandbox 模块写进 content/_handmade/labs.json 的 chapters，
再由 gen_interactive.py 并入 interactive.json 与前端数据。

为什么是这 8 章
---------------
sandbox 的硬门槛是「参数能调、判据能算」。以下章节的核心知识本身就是
一条能写出闭式表达式的数量关系，做成沙盒才不是假游戏：

  bigdata/bd-ch02   MapReduce：Combiner 压缩率 → Shuffle 数据量 / 单 reduce 负载
  bigdata/bd-ch04   Spark：分区数 → Task 数；groupByKey 相对 reduceByKey 的 shuffle 放大
  data/data-ch01    ndarray 内存 = 元素数 × dtype 字节；视图 vs 拷贝
  data/data-ch02    广播不复制（stride 置 0），物化成数组后内存爆炸
  java/java-ch07    线程池：CPU 密集 N+1 / IO 密集 N×(1+W/C)
  java/java-ch08    JVM：NewRatio 决定新生代大小 → Minor GC 次数；对象大小对齐 8B
  agent/agent-ch05  RAG：chunk 数 × top-k × 块大小 → 上下文 tokens 预算
  agent/agent-ch07  LoRA：rank → 可训练参数量；显存账本（权重/适配器/激活）

刻意没做的：agent-ch01/04/12/13/14/16（岗位、需求、商业化、简历全是定性）、
fs-ch07（项目实战）、java-ch01（基础语法）、py-ch05（文件 IO 读写）。
硬把它们做成旋钮游戏，玩家拧到全绿也学不到东西。

三条通用纪律（与批次三一致）
---------------------------
1. checks 不能只写「目标态」，必须补取值下限。否则穷举求解读会退化成
   「所有旋钮拉到最小值」，等于没玩。
2. `if(c,a,b)` 在两套求值器里都是**急切求值**（两分支都先算），除法要么
   保证除数恒非零，要么别放进 if 分支里。
3. fmt 只支持 int / fix2 / pct。

写盘必须 indent=1 + newline="\\n"，与仓库现有风格逐字节一致。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# bigdata/bd-ch02 · MapReduce：Combiner 决定了 Shuffle 要搬多少数据
# ----------------------------------------------------------------------------
# 教学点：Map 输出的 kv 对必须经 Shuffle 跨网络搬到 reducer。Combiner 是
# 「本地 reduce」，把同一个 map 内相同 key 先合并，从而在搬运前就砍掉大部分
# 数据——压缩率直接决定 Shuffle 总字节数与单 reduce 负载。
# 公式：
#   mapOut  = 输入条数 ÷ 每条记录产出 kv 数（简化：1 条记录 → kvPerRec 个 kv）
#   afterComb = mapOut × (1 − combRatio)      ← combRatio 为 0 表示没用 Combiner
#   shuffleMB = afterComb × 每 kv 字节 ÷ 1e6
#   perReduceMB = shuffleMB ÷ reduce 数        ← 太少 reduce 会单点 OOM
# 可玩性：默认 100 万条 × 8 kv/条、没用 Combiner → 800 万 kv，按 100B/kv 约 800MB，
# 分给 2 个 reduce 每个 400MB，直接超 256MB 的单 reduce 安全线。
# 玩家要么开 Combiner（压缩 90%），要么加 reduce 数，或者两者都做。
# ============================================================================
bd_ch02 = {
    "kind": "sandbox",
    "title": "Shuffle 到底要搬多少数据",
    "brief": (
        "Map 输出的每个 kv 都要跨网络搬到 reducer——这是 MapReduce 最贵的一步。"
        "Combiner 是本地预聚合，能在搬运前把相同 key 先合并，压缩率直接决定 Shuffle 总量；"
        "reduce 数决定这些数据分摊到几个 reducer，太少会单点 OOM。"
        "拖输入规模、Combiner 压缩率与 reduce 数，把 Shuffle 压进预算。"
    ),
    "params": [
        # 输入记录数（万条为单位，避免数值过大）
        {"key": "inputWan", "label": "输入记录数", "min": 10, "max": 1000, "step": 10, "value": 100, "unit": "万条"},
        # 每条记录 map 后产出的 kv 对数
        {"key": "kvPerRec", "label": "每条记录产出 kv", "min": 1, "max": 20, "step": 1, "value": 8},
        # Combiner 压缩率：0 = 不用 Combiner；0.9 = 相同 key 合并掉九成
        {"key": "combRatio", "label": "Combiner 压缩率", "min": 0.0, "max": 0.95, "step": 0.05, "value": 0.0},
        # reduce 任务数（= 分区数）
        {"key": "numReduce", "label": "reduce 任务数", "min": 1, "max": 40, "step": 1, "value": 2},
    ],
    "metrics": [
        # map 阶段原始输出 kv 数（万条 × 万 = 万？不，是 万条 → 万 kv）
        # inputWan 单位是「万条记录」，乘 kvPerRec 得到「万 kv」
        {"key": "mapOutWan", "label": "map 输出 kv（万）", "expr": "inputWan * kvPerRec", "unit": "万", "fmt": "int"},
        # Combiner 之后还剩多少（万 kv）。combRatio=0 时原样不动
        {"key": "afterCombWan", "label": "Combiner 后 kv（万）", "expr": "inputWan * kvPerRec * (1 - combRatio)", "unit": "万", "fmt": "int"},
        # Shuffle 总字节：万 kv × 1e4 × 100B ÷ 1e6 = 万 × 1
        # 即 shuffleMB = afterCombWan × 1.0（每万 kv 约 1MB，按 100 字节/kv 估算）
        {"key": "shuffleMB", "label": "Shuffle 总量", "expr": "inputWan * kvPerRec * (1 - combRatio)", "unit": "MB", "fmt": "int"},
        # 单个 reducer 要处理多少
        {"key": "perReduceMB", "label": "单 reduce 负载", "expr": "inputWan * kvPerRec * (1 - combRatio) / numReduce", "unit": "MB", "fmt": "int"},
        # 有没有触发 Combiner（用于判据）
        {"key": "hasComb", "label": "是否启用 Combiner", "expr": "if(combRatio > 0, 1, 0)", "fmt": "int"},
    ],
    "checks": [
        # 单 reduce 负载不能超 256MB（≈ 堆内可排序的舒适区，超了要落盘多次）
        {"expr": "perReduceMB <= 256", "label": "单 reduce 负载 ≤256MB（超了会反复溢写）"},
        # Shuffle 总量控制住，否则网络成瓶颈
        {"expr": "shuffleMB <= 500", "label": "Shuffle 总量 ≤500MB"},
        # 下限：没用 Combiner 就等于放弃了 MapReduce 最重要的优化，不给过
        {"expr": "hasComb == 1", "label": "必须启用 Combiner（省下的就是省下的网络带宽）"},
        # 下限：reduce 数太少会单点，太多会产生大量小文件；要求至少 4 个
        {"expr": "numReduce >= 4", "label": "reduce ≥4（太少单点、太多小文件）"},
        # 既定事实：输入规模与每条记录的 kv 产出由业务数据决定，不是你能调的。
        # 用 == 而非 >=：一旦允许「调大」，玩家会把数据量拉满来让 combRatio 显得有效，
        # 那等于换了一道题。锁死这两个值，唯一变量就只剩 Combiner 与 reduce 数。
        {"expr": "inputWan == 100", "label": "输入固定 100 万条（数据规模是既定事实）"},
        {"expr": "kvPerRec == 8", "label": "每条记录固定 8 个 kv（产出来自业务逻辑）"},
    ],
    "insight": (
        "Shuffle 是 MapReduce 的胜负手：Map 输出的每个 kv 都要跨网络搬运。"
        "Combiner 是「本地 reduce」，在搬运前先合并相同 key——WordCount 里加不加它，"
        "Shuffle 量能差一个数量级（但求平均这类不可交换的聚合不能加）。"
        "reduce 数就是分区数：太少单点 OOM，太多会产生大量小文件拖垮 NameNode。"
    ),
}


# ============================================================================
# bigdata/bd-ch04 · Spark：分区数直接等于 Task 数
# ----------------------------------------------------------------------------
# 教学点（两条本章最常考的数量关系）：
#   1. Task 数 = 分区数。并行度不是靠线程池，是靠分区数。
#   2. reduceByKey 有 map 端预聚合，groupByKey 没有 → 同样数据 groupByKey 的
#      Shuffle 量是 reduceByKey 的「每 key 平均条目数」倍。
# 公式：
#   taskCount  = numPartitions
#   moveMB     = 数据量 × 每 key 平均条目数 ÷ 预聚合因子
#                reduceByKey 预聚合后 ≈ 按 key 去重，groupByKey 全量搬
#   stageTime  = 每 task 处理量 ÷ 单核速率（简化为线性）→ 看能否进窗口
# 可玩性：默认 2 分区（Spark 的默认值，正是踩坑点）、groupByKey、数据 1000MB，
# 单 task 背 500MB 且 shuffle 放大 20 倍 → 必挂。玩家要加分区 + 换 reduceByKey。
# ============================================================================
bd_ch04 = {
    "kind": "sandbox",
    "title": "并行度不是线程数，是分区数",
    "brief": (
        "Spark 里 Task 数 = 分区数，加 Executor 不会让任务变多。"
        "而 reduceByKey 有 map 端预聚合、groupByKey 没有，同样的数据后者 Shuffle 量会放大「每 key 平均条目数」倍。"
        "拖分区数、聚合算子与数据规模，让单个 Task 不爆、Shuffle 不炸。"
    ),
    "params": [
        # 分区数：默认 2，Spark 读文件时的默认值，也是本章最经典的坑
        {"key": "numPart", "label": "分区数", "min": 2, "max": 400, "step": 2, "value": 2},
        # 数据规模
        {"key": "dataMB", "label": "数据规模", "min": 100, "max": 20000, "step": 100, "value": 1000, "unit": "MB"},
        # 每个 key 平均有多少条目（决定 groupByKey 的放大倍数）
        {"key": "itemsPerKey", "label": "每 key 平均条目数", "min": 1, "max": 50, "step": 1, "value": 20},
        # 算子选择：0 = groupByKey（无预聚合），1 = reduceByKey（有预聚合）
        {"key": "useReduceByKey", "label": "聚合算子", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["groupByKey", "reduceByKey"]},
    ],
    "metrics": [
        # Task 数 = 分区数（这是本章第一等式）
        {"key": "taskCount", "label": "Task 数", "expr": "numPart", "unit": "个", "fmt": "int"},
        # 单 Task 处理的数据量：数据量 ÷ 分区数
        {"key": "perTaskMB", "label": "单 Task 数据量", "expr": "dataMB / numPart", "unit": "MB", "fmt": "int"},
        # Shuffle 量：
        #   groupByKey  → dataMB × itemsPerKey（全量按 key 搬）
        #   reduceByKey → dataMB（map 端先聚合到每 key 一条）
        {"key": "shuffleMB", "label": "Shuffle 量",
         "expr": "if(useReduceByKey == 1, dataMB, dataMB * itemsPerKey)", "unit": "MB", "fmt": "int"},
        # 是否用了预聚合算子
        {"key": "hasPreAgg", "label": "是否 map 端预聚合", "expr": "useReduceByKey", "fmt": "int"},
    ],
    "checks": [
        # 单 Task 不超过 128MB（Spark 单 task 的舒适区间，超了容易 spill）
        {"expr": "perTaskMB <= 128", "label": "单 Task ≤128MB（超了容易 spill 落盘）"},
        # Shuffle 量控制住
        {"expr": "shuffleMB <= 2000", "label": "Shuffle 量 ≤2GB"},
        # 下限：分区数至少 2×核数量级才有并行度（这里用 ≥16 近似 8 核 ×2）
        {"expr": "numPart >= 16", "label": "分区数 ≥16（并行度要压满可用核）"},
        # 必须用 reduceByKey 而不是 groupByKey
        {"expr": "hasPreAgg == 1", "label": "用 reduceByKey 而非 groupByKey（map 端预聚合省掉绝大部分 Shuffle）"},
        # 既定事实：数据规模和 key 分布是数据本身的属性，不由你决定。
        # 用 == 锁死——允许调大只会让玩家把数据拉满、把 itemsPerKey 拉高，
        # 从而让 reduceByKey 的优势「看起来」更大，实际换了一道题。
        {"expr": "dataMB == 1000", "label": "数据固定 1GB（规模是既定事实）"},
        {"expr": "itemsPerKey == 20", "label": "每 key 固定 20 条（key 分布由数据决定）"},
    ],
    "insight": (
        "Task 数 = 分区数，这是 Spark 并行度的唯一来源；加 Executor 只是加「同时能跑几个 Task」的槽位。"
        "reduceByKey 在 map 端先按 key 聚合，搬出去的是「每 key 一条」；groupByKey 把每个 key 的全部条目原样搬——"
        "每 key 20 条就是 20 倍 Shuffle。所以能预聚合就别 groupByKey；join 时小表优先广播成窄依赖。"
    ),
}


# ============================================================================
# data/data-ch01 · NumPy：ndarray 的内存账与视图/拷贝
# ----------------------------------------------------------------------------
# 教学点：
#   ndarray 内存 = 元素数 × itemsize（dtype 字节数）。
#   dtype 一升级（int8→int64）就是 8 倍内存，跟数据「一样多」但占的空间完全不同。
#   切片 / reshape 是视图（base 指向原数组，零拷贝）；花式索引 / astype 一定拷贝。
# 公式：
#   elems   = rows × cols
#   memMB   = elems × itemsize ÷ 1e6
#   copyMB  = if(isView, 0, memMB)     ← 视图不占额外内存
# 可玩性：默认 4000×4000 int64 = 1600 万元素 × 8B = 128MB，再选「拷贝」→ 翻倍到 256MB，
# 超了 200MB 的预算。玩家要降 dtype 或改视图，或缩规模。
# ============================================================================
data_ch01 = {
    "kind": "sandbox",
    "title": "dtype 一升位，内存就翻倍",
    "brief": (
        "ndarray 的内存 = 元素数 × dtype 字节数。"
        "int8→int64 是 8 倍，float32→float64 是 2 倍——数据一样多，占的空间完全不同。"
        "而切片/reshape 是视图（零拷贝），花式索引/astype 一定拷贝。"
        "拖规模、dtype 位宽与操作类型，把内存压进预算。"
    ),
    "params": [
        {"key": "rows", "label": "行数", "min": 100, "max": 10000, "step": 100, "value": 4000},
        {"key": "cols", "label": "列数", "min": 100, "max": 10000, "step": 100, "value": 4000},
        # itemsize 直接作为可调参数：1=int8, 2=int16/float16, 4=int32/float32, 8=int64/float64
        {"key": "itemsize", "label": "单元素字节数", "min": 1, "max": 8, "step": 1, "value": 8, "unit": "B"},
        # 操作类型：0 = 视图（切片/reshape），1 = 拷贝（花式索引/astype）
        {"key": "isCopy", "label": "操作类型", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["视图（零拷贝）", "拷贝（新缓冲）"]},
        # 内存预算
        # 内存预算：min 必须能被 200 整除，否则 200 不在网格上 → `budgetMB == 200`
        # 这条锁定判据永远命中不了（grid 生成的是 16,32,…,192,208，跳过 200）
        {"key": "budgetMB", "label": "内存预算", "min": 200, "max": 1024, "step": 8, "value": 200, "unit": "MB"},
    ],
    "metrics": [
        # 元素数
        {"key": "elems", "label": "元素个数", "expr": "rows * cols", "unit": "个", "fmt": "int"},
        # 原数组占用（MB）：元素数 × itemsize ÷ 1e6
        {"key": "baseMB", "label": "原数组内存", "expr": "rows * cols * itemsize / 1000000", "unit": "MB", "fmt": "fix2"},
        # 额外占用：视图为 0，拷贝为再开一份同样大小
        {"key": "extraMB", "label": "额外占用", "expr": "if(isCopy == 1, rows * cols * itemsize / 1000000, 0)", "unit": "MB", "fmt": "fix2"},
        # 峰值内存 = 原 + 额外
        {"key": "peakMB", "label": "峰值内存",
         "expr": "rows * cols * itemsize / 1000000 + if(isCopy == 1, rows * cols * itemsize / 1000000, 0)",
         "unit": "MB", "fmt": "fix2"},
        # 单元素字节数带来的倍数（相对 int8）
        {"key": "bytesRatio", "label": "相对 int8 的倍数", "expr": "itemsize", "unit": "倍", "fmt": "int"},
    ],
    "checks": [
        # 峰值不能超预算
        {"expr": "peakMB <= budgetMB", "label": "峰值内存不超预算"},
        # 下限：位宽不能无脑降到 1 字节，int8 存不下常见整数范围，float16 存不下精度
        {"expr": "itemsize >= 4", "label": "单元素 ≥4 字节（int8/float16 精度不够）"},
        # 必须选视图——这是本章的核心技能点
        {"expr": "isCopy == 0", "label": "用视图而非拷贝（切片/reshape 零拷贝）"},
        # 既定条件用 == 锁死：预算放大等于「买台新机器」，数据缩小等于「换个小数据集」，
        # 两者都绕开了本章真正要练的东西——选对 dtype、选视图而非拷贝。
        {"expr": "budgetMB == 200", "label": "预算固定 200MB（机器内存既定）"},
        {"expr": "rows == 4000 && cols == 4000", "label": "矩阵固定 4000×4000（数据集既定）"},
    ],
    "insight": (
        "ndarray 内存 = 元素数 × itemsize。dtype 一升位就是成倍增长：int8→int64 是 8 倍。"
        "切片、reshape、transpose 都是视图（base 指向原数组，stride 改一下就行），零拷贝；"
        "花式索引、astype、ravel（非连续时）一定拷贝。"
        "所以「转置后再 ravel」会偷偷拷贝一份——这不是 bug，是内存布局不连续。"
    ),
}


# ============================================================================
# data/data-ch02 · NumPy 广播：不复制数据，但物化就爆炸
# ----------------------------------------------------------------------------
# 教学点：广播的语义是「把该维 stride 置 0」，所以零内存、零拷贝。
# 但一旦 np.array(broadcast) 或做需要真实缓冲的操作，就会按广播后 shape 物化。
# 公式：
#   outElems = 各维最大值之积（广播后 shape）
#   outMB    = outElems × itemsize ÷ 1e6
#   onTheFly → 实际额外内存 0
#   materialize → 额外 = outMB
# 可玩性：默认 1000×1000 加 1000×1，广播后 100 万元素，物化就要 8MB；
# 把「第 3 维」加进来（比如 1000×1000×100）广播后 1 亿元素 = 800MB，直接爆。
# ============================================================================
data_ch02 = {
    "kind": "sandbox",
    "title": "广播零拷贝，物化就爆炸",
    "brief": (
        "广播不复制数据——它只是把该维的 stride 置 0，所以零内存。"
        "但一旦 np.array(broadcast) 物化，就会按广播后的完整 shape 分配缓冲。"
        "拖三个维度与是否物化，看什么时候内存会炸。"
    ),
    "params": [
        {"key": "d1", "label": "维度 1", "min": 10, "max": 2000, "step": 10, "value": 1000},
        {"key": "d2", "label": "维度 2", "min": 10, "max": 2000, "step": 10, "value": 1000},
        {"key": "d3", "label": "维度 3", "min": 1, "max": 200, "step": 1, "value": 100},
        {"key": "itemsize", "label": "单元素字节数", "min": 1, "max": 8, "step": 1, "value": 8, "unit": "B"},
        # 0 = 惰性广播（on-the-fly，stride 置 0），1 = 物化成真实数组
        {"key": "materialize", "label": "是否物化", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["惰性广播（stride=0）", "np.array() 物化"]},
    ],
    "metrics": [
        # 广播后完整 shape 的元素数
        {"key": "outElems", "label": "广播后元素数", "expr": "d1 * d2 * d3", "unit": "个", "fmt": "int"},
        # 惰性广播的额外内存恒为 0
        {"key": "lazyMB", "label": "惰性广播额外内存", "expr": "0", "unit": "MB", "fmt": "int"},
        # 物化后要分配的缓冲
        {"key": "matMB", "label": "物化后内存", "expr": "d1 * d2 * d3 * itemsize / 1000000", "unit": "MB", "fmt": "fix2"},
        # 实际额外内存：看选哪种
        {"key": "actualMB", "label": "实际额外内存",
         "expr": "if(materialize == 1, d1 * d2 * d3 * itemsize / 1000000, 0)", "unit": "MB", "fmt": "fix2"},
        # 放大倍数：广播后元素数 ÷ 原始一个向量的元素数（用 d1 近似基准）
        {"key": "amplify", "label": "相对单向量放大", "expr": "d1 * d2 * d3 / d1", "unit": "倍", "fmt": "int"},
    ],
    "checks": [
        # 实际额外内存压进 64MB
        {"expr": "actualMB <= 64", "label": "额外内存 ≤64MB"},
        # 必须保持惰性——这是本章核心认知
        {"expr": "materialize == 0", "label": "保持惰性广播（不要 np.array 物化）"},
        # 下限：三个维度都得有规模，否则广播没有意义
        {"expr": "d1 >= 500 && d2 >= 500 && d3 >= 10", "label": "三个维度都要有规模（d1/d2≥500、d3≥10）"},
        # 下限：dtype 位宽是数据本身的属性（float64 特征就是 8 字节），
        # 靠把 itemsize 调到 1 来省内存，等于把精度问题藏起来。
        {"expr": "itemsize >= 4", "label": "单元素 ≥4 字节（float32 起步，别靠降精度省内存）"},
    ],
    "insight": (
        "广播的语义是「把该维 stride 置 0」，所以零内存、零拷贝——"
        "这就是为什么 (1000,1000) + (1000,1) 不报内存错。"
        "但只要你把它物化（np.array(broadcast)、concatenate、写进需要真实缓冲的算子），"
        "就会按广播后的完整 shape 分配：1000×1000×100 × 8B = 800MB。"
        "所以「广播很方便」和「广播后别手贱物化」要一起记。"
    ),
}


# ============================================================================
# java/java-ch07 · 线程池：线程数不是越多越好
# ----------------------------------------------------------------------------
# 教学点（本章最常考的两个公式）：
#   CPU 密集：N_cpu + 1（多 1 个应对偶发缺页中断）
#   IO  密集：N_cpu × (1 + W/C)，W 为等待时间、C 为计算时间
# 以及「线程数配好之后，还要看队列容量能不能吸收突发」。
# 公式：
#   ideal   = if(ioBound, cores * (1 + waitMs / calcMs), cores + 1)
#   queueCap= 峰值QPS × 可接受排队秒数（Little 定律：L = λW）
# 可玩性：默认 8 核、IO 密集 W=90ms C=10ms → 理想 80 线程，但玩家只配了 8，
# 队列又只给 100，QPS 500 时直接拒绝。
# ============================================================================
java_ch07 = {
    "kind": "sandbox",
    "title": "线程池大小不是拍脑袋",
    "brief": (
        "CPU 密集取 N_cpu+1；IO 密集取 N_cpu×(1+W/C)——等 90ms 算 10ms 就是 10 倍。"
        "线程数配好之后还要看队列：按 Little 定律，队列容量 ≈ 峰值QPS × 可接受排队秒数。"
        "拖核数、任务类型与队列容量，让请求不被拒绝。"
    ),
    "params": [
        # 可用核数（容器里 availableProcessors 与实际 quota 不一致是经典坑）
        {"key": "cores", "label": "可用核数", "min": 2, "max": 64, "step": 2, "value": 8},
        # 任务类型：0 = CPU 密集，1 = IO 密集
        {"key": "ioBound", "label": "任务类型", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["CPU 密集", "IO 密集"]},
        # IO 等待时间（仅 IO 密集时参与计算）
        {"key": "waitMs", "label": "IO 等待时间", "min": 0, "max": 200, "step": 10, "value": 90, "unit": "ms"},
        # 计算时间
        {"key": "calcMs", "label": "计算时间", "min": 1, "max": 50, "step": 1, "value": 10, "unit": "ms"},
        # 实际配置的核心线程数
        {"key": "poolSize", "label": "实际线程数", "min": 1, "max": 200, "step": 1, "value": 8},
        # 队列容量
        {"key": "queueCap", "label": "队列容量", "min": 10, "max": 10000, "step": 10, "value": 100},
        # 峰值 QPS
        {"key": "qps", "label": "峰值 QPS", "min": 10, "max": 5000, "step": 10, "value": 500},
    ],
    "metrics": [
        # 计算/等待比：W/C
        {"key": "wcRatio", "label": "等待/计算比", "expr": "waitMs / calcMs", "unit": "倍", "fmt": "fix2"},
        # 理论线程数
        #   IO 密集：cores × (1 + W/C)
        #   CPU 密集：cores + 1
        {"key": "idealThreads", "label": "理论线程数",
         "expr": "if(ioBound == 1, cores * (1 + waitMs / calcMs), cores + 1)", "unit": "个", "fmt": "int"},
        # 线程利用率：实际配置 ÷ 理论值
        {"key": "utilRatio", "label": "相对理论值", "expr": "poolSize / if(ioBound == 1, cores * (1 + waitMs / calcMs), cores + 1)", "unit": "倍", "fmt": "fix2"},
        # 需求队列容量（Little 定律：L = λ × W，简化取 1 秒窗口）
        {"key": "needQueue", "label": "需要的队列容量", "expr": "qps", "unit": "个", "fmt": "int"},
        # 是否会拒绝：线程满 + 队列满 → 触发拒绝策略
        {"key": "reject", "label": "是否会拒绝请求", "expr": "if(queueCap < qps && poolSize < qps, 1, 0)", "fmt": "int"},
    ],
    "checks": [
        # 不能拒绝请求
        {"expr": "reject == 0", "label": "不触发拒绝策略（线程+队列能吸收峰值 QPS）"},
        # 线程数要接近理论值（至少 80%，太少会白白浪费等待时间）
        {"expr": "utilRatio >= 0.8", "label": "线程数达理论值 80% 以上（IO 密集别按核数配）"},
        # 上限：线程数不能超过理论值 2 倍，否则上下文切换开销爆炸
        {"expr": "utilRatio <= 2", "label": "线程数不超理论值 2 倍（超了上下文切换反噬）"},
        # 队列不能无界（无界队列会掩盖问题，最终 OOM）
        {"expr": "queueCap <= 5000", "label": "队列有界且 ≤5000（无界队列掩盖背压）"},
        # 既定事实：核数是机器规格、QPS 是业务流量、W/C 是任务本身的耗时结构。
        # 全部用 == 锁死——只要允许调，玩家就会靠加核、降流量、拉长等待时间「换一道题」，
        # 而不是学「IO 密集该按 N×(1+W/C) 配线程数」这件事。
        {"expr": "cores == 8", "label": "核数固定 8（机器规格既定）"},
        {"expr": "qps == 500", "label": "峰值 QPS 固定 500（流量由业务决定）"},
        {"expr": "waitMs == 90", "label": "IO 等待固定 90ms（真实 DB/RPC 往返量级）"},
    ],
    "insight": (
        "CPU 密集取 N_cpu+1；IO 密集取 N_cpu×(1+W/C)——等 90ms 算 10ms 就是 10 倍，"
        "8 核要 80 个线程而不是 8 个。但线程数只是第一层："
        "队列容量按 Little 定律 L=λW 估，太小会拒绝、无界会掩盖背压直到 OOM。"
        "容器里还要注意 availableProcessors 读的是宿主核数而非 CPU quota——这是云原生经典故障源。"
    ),
}


# ============================================================================
# java/java-ch08 · JVM：堆怎么切，GC 就怎么跑
# ----------------------------------------------------------------------------
# 教学点：
#   NewRatio=2 → 老年代:新生代 = 2:1，即新生代占堆的 1/3。
#   新生代越大，Minor GC 间隔越长但单次越久；越小则 GC 频繁。
#   SurvivorRatio=8 → Eden:单个Survivor = 8:1，即 Eden 占新生代的 8/10。
#   对象大小按 8 字节对齐：new int[10] = 8(头) + 4(长度) + 40 = 52 → 对齐 56B。
# 公式：
#   youngMB  = heapMB / (1 + newRatio)
#   edenMB   = youngMB × survivorRatio / (survivorRatio + 2)
#   gcCount  = 分配总量 ÷ eden 大小（Eden 满即触发 Minor GC）
# 可玩性：默认堆 4G、NewRatio=2 → 新生代 1.33G、Eden 1.07G；
# 分配 50G 就触 47 次 Minor GC —— 目标是把次数压下来又不让单次停顿过长。
# ============================================================================
java_ch08 = {
    "kind": "sandbox",
    "title": "堆怎么切，GC 就怎么跑",
    "brief": (
        "NewRatio=2 表示老年代:新生代=2:1，新生代只占堆的 1/3。"
        "SurvivorRatio=8 表示 Eden:单个Survivor=8:1。"
        "Eden 满就触发 Minor GC——分配量除以 Eden 大小就是 GC 次数。"
        "拖堆大小与代比例，既压 GC 次数又不让单次停顿超预算。"
    ),
    "params": [
        # 堆大小：默认 2G —— 小堆 + 大分配量正是「GC 打到 CPU 满」的常见事故
        {"key": "heapGB", "label": "堆大小", "min": 1, "max": 32, "step": 1, "value": 2, "unit": "GB"},
        # NewRatio：老年代 ÷ 新生代
        {"key": "newRatio", "label": "NewRatio（老:新）", "min": 1, "max": 8, "step": 1, "value": 2},
        # SurvivorRatio：Eden ÷ 单个 Survivor
        {"key": "survRatio", "label": "SurvivorRatio", "min": 2, "max": 16, "step": 2, "value": 8},
        # 总分配量（GB）：默认 300G，配合 2G 堆 → GC 次数爆表
        {"key": "allocGB", "label": "总分配量", "min": 10, "max": 500, "step": 10, "value": 300, "unit": "GB"},
    ],
    "metrics": [
        # 新生代大小 = 堆 ÷ (1 + NewRatio)
        {"key": "youngMB", "label": "新生代大小", "expr": "heapGB * 1024 / (1 + newRatio)", "unit": "MB", "fmt": "int"},
        # 老年代大小 = 堆 − 新生代
        {"key": "oldMB", "label": "老年代大小", "expr": "heapGB * 1024 * newRatio / (1 + newRatio)", "unit": "MB", "fmt": "int"},
        # Eden 大小 = 新生代 × SurvivorRatio / (SurvivorRatio + 2)
        # （新生代 = Eden + 2 个 Survivor，Eden : S1 : S2 = survRatio : 1 : 1）
        {"key": "edenMB", "label": "Eden 大小",
         "expr": "heapGB * 1024 / (1 + newRatio) * survRatio / (survRatio + 2)", "unit": "MB", "fmt": "int"},
        # Minor GC 次数 ≈ 分配总量 ÷ Eden 大小（Eden 满触发一次）
        {"key": "gcCount", "label": "Minor GC 次数",
         "expr": "allocGB * 1024 / (heapGB * 1024 / (1 + newRatio) * survRatio / (survRatio + 2))",
         "unit": "次", "fmt": "int"},
        # 单次 Minor GC 停顿估算：Eden 越大扫得越久（按 1GB≈8ms 粗略线性）
        {"key": "pauseMs", "label": "单次停顿估算",
         "expr": "heapGB * 1024 / (1 + newRatio) * survRatio / (survRatio + 2) / 1024 * 8",
         "unit": "ms", "fmt": "fix2"},
    ],
    "checks": [
        # GC 次数压到 60 次以内
        {"expr": "gcCount <= 60", "label": "Minor GC 次数 ≤60"},
        # 单次停顿不超过 50ms（交互式应用的常见 SLA）
        {"expr": "pauseMs <= 50", "label": "单次停顿 ≤50ms"},
        # 下限：老年代不能太小，否则对象晋升后立刻触发 Full GC
        {"expr": "oldMB >= 1024", "label": "老年代 ≥1GB（太小会频繁 Full GC）"},
        # 下限：Eden 不能太小，否则 GC 频繁到失去意义
        {"expr": "edenMB >= 256", "label": "Eden ≥256MB（太小 GC 过密）"},
        # 既定事实：分配总量是业务吞吐的产物、SurvivorRatio=8 是 JVM 经验默认值。
        # 用 == 锁死，避免玩家靠「减分配量 / 调 SurvivorRatio」把 GC 次数做小。
        {"expr": "allocGB == 300", "label": "分配量固定 300GB（业务吞吐既定）"},
        {"expr": "survRatio == 8", "label": "SurvivorRatio 固定 8（默认 Eden:S1:S2=8:1:1）"},
    ],
    "insight": (
        "NewRatio=2 表示老:新=2:1，新生代只占堆的 1/3；SurvivorRatio=8 表示 Eden 占新生代的 8/10。"
        "Eden 满即触发 Minor GC，所以「分配量 ÷ Eden 大小 = GC 次数」——"
        "想少 GC 就加大 Eden，但 Eden 越大单次扫描越久，停顿跟着涨。"
        "这就是为什么 G1/ZGC 要拆 Region 做增量回收：在「次数」和「单次停顿」之间找第三条路。"
    ),
}


# ============================================================================
# agent/agent-ch05 · RAG：chunk 与 top-k 决定上下文预算
# ----------------------------------------------------------------------------
# 教学点：RAG 的上下文 tokens = top-k × 每块 tokens（× 重叠带来的放大）。
#   切块太小 → 召回碎片，单块缺上下文；切块太大 → 一两块就吃满窗口。
#   重叠窗口提升召回但成倍放大 token 消耗。
# 公式：
#   perChunkTok = chunkSize × (1 + overlap)          ← 重叠让有效块变长
#   ctxTok      = topK × perChunkTok + 固定开销
#   chunkCount  = 文档 tokens ÷ (chunkSize × (1 − overlap))  ← 重叠让块数变多
# 可玩性：默认块 512、重叠 20%、top-5 → 每块 614 tok，5 块 3070 tok，
# 加上系统提示 1000 就到 4070，超了 4096 窗口。玩家要调块大小或降 top-k。
# ============================================================================
agent_ch05 = {
    "kind": "sandbox",
    "title": "RAG 的上下文预算怎么花",
    "brief": (
        "上下文 tokens = top-k × 每块 tokens + 系统提示。"
        "切块太小召回碎片、太大一两块就吃满窗口；"
        "重叠窗口能提升召回，但会让块数和每块长度同时放大。"
        "拖块大小、重叠率与 top-k，把整条链压进模型窗口。"
    ),
    "params": [
        # 块大小（tokens）
        {"key": "chunkSize", "label": "切块大小", "min": 128, "max": 2048, "step": 128, "value": 512, "unit": "tok"},
        # 重叠率（0~50%）
        {"key": "overlap", "label": "重叠率", "min": 0.0, "max": 0.5, "step": 0.05, "value": 0.2},
        # 召回条数
        {"key": "topK", "label": "召回条数 top-k", "min": 1, "max": 20, "step": 1, "value": 5},
        # 文档总规模（千 tokens）
        {"key": "docKTok", "label": "文档规模", "min": 10, "max": 500, "step": 10, "value": 100, "unit": "千 tok"},
        # 系统提示 + 问题 + 固定开销
        {"key": "sysTok", "label": "系统提示开销", "min": 200, "max": 2000, "step": 100, "value": 1000, "unit": "tok"},
        # 模型上下文窗口
        {"key": "windowK", "label": "上下文窗口", "min": 4, "max": 128, "step": 4, "value": 4, "unit": "K tok"},
    ],
    "metrics": [
        # 每块有效 tokens（块大小 × (1 + 重叠率)）
        {"key": "perChunkTok", "label": "每块 tokens", "expr": "chunkSize * (1 + overlap)", "unit": "tok", "fmt": "int"},
        # 上下文总占用 = top-k × 每块 + 固定开销
        {"key": "ctxTok", "label": "上下文占用", "expr": "topK * chunkSize * (1 + overlap) + sysTok", "unit": "tok", "fmt": "int"},
        # 窗口占用率
        {"key": "fillRatio", "label": "窗口占用率",
         "expr": "(topK * chunkSize * (1 + overlap) + sysTok) / (windowK * 1024)", "unit": "倍", "fmt": "fix2"},
        # 索引块数 = 文档 tokens ÷ 净步进（chunkSize × (1 − overlap)）
        {"key": "chunkCount", "label": "索引块数",
         "expr": "docKTok * 1000 / (chunkSize * (1 - overlap + if(overlap == 1, 0.01, 0)))", "unit": "块", "fmt": "int"},
        # 是否溢出窗口
        {"key": "overflow", "label": "是否溢出窗口",
         "expr": "if(topK * chunkSize * (1 + overlap) + sysTok > windowK * 1024, 1, 0)", "fmt": "int"},
    ],
    "checks": [
        # 不能溢出窗口
        {"expr": "overflow == 0", "label": "上下文不溢出模型窗口"},
        # 留出生成空间：占用率不超过 70%
        {"expr": "fillRatio <= 0.7", "label": "窗口占用 ≤70%（留 30% 给生成与多轮）"},
        # 下限：块不能太小，否则召回碎片化、单块缺上下文
        {"expr": "chunkSize >= 256", "label": "块 ≥256 tok（再小召回碎片化）"},
        # 下限：top-k 太少召回不足，答案质量上不去
        {"expr": "topK >= 3", "label": "top-k ≥3（召回太少答案容易漏）"},
        # 重叠窗口是本章重点，不许调成 0——那等于放弃了「答案跨切点」的防护；
        # 文档规模与系统提示、窗口都是既定条件，用 == 锁死（扩窗口 / 缩文档都是换题）。
        {"expr": "overlap >= 0.1", "label": "重叠 ≥10%（不然答案跨切点就召回不到）"},
        {"expr": "docKTok == 100", "label": "文档固定 10 万 tok（知识库规模既定）"},
        {"expr": "sysTok == 1000", "label": "系统提示固定 1000 tok（已写好的模板）"},
        {"expr": "windowK == 4", "label": "窗口固定 4K（模型能力既定，别换更大上下文的模型）"},
    ],
    "insight": (
        "RAG 的上下文预算 = top-k × 每块 tokens + 系统提示 + 生成预留。"
        "块切太小，召回的是碎片、单块缺上下文；切太大，一两块就吃满窗口。"
        "重叠窗口能救回「答案刚好跨在切点」的情况，代价是块数和每块长度同时放大——"
        "20% 重叠意味着有效块长 +20%、索引块数 +25%。所以调参数时先算账再动手。"
    ),
}


# ============================================================================
# agent/agent-ch07 · LoRA：rank 涨的是参数量，不是表达力
# ----------------------------------------------------------------------------
# 教学点：
#   单层 LoRA 参数量 = r × (d_in + d_out)；rank 翻倍参数量就翻倍。
#   缩放 = α/r，所以只翻 rank 不调 α 等于把有效学习率打了对折。
#   显存账本里最先爆的通常不是权重而是激活。
# 公式：
#   paramsPerLayer = r × (d + d) = 2 × r × d     （以 d_in = d_out = d 近似）
#   totalParams    = paramsPerLayer × layers × 挂载层数
#   adapterMB      = totalParams × 2B（fp16）
#   actMB          = batch × seq × hidden × layers × 2B（简化，未开梯度检查点）
# 可玩性：默认 r=16、32 层、d=4096、挂 q/k/v/o 四层 → 每层 2×16×4096=131072，
# 乘 32 层 × 4 = 1677 万参数，fp16 约 32MB，还好；但激活 8×2048×4096×32×2 ≈ 4.3GB，
# 加上 7B 权重 13.5GB，24GB 卡直接爆——正是本章「先开梯度检查点」的动机。
# ============================================================================
agent_ch07 = {
    "kind": "sandbox",
    "title": "LoRA 显存账本：先爆的不是权重",
    "brief": (
        "LoRA 参数量 = rank × (d_in+d_out) × 层数 × 挂载层数，rank 翻倍参数就翻倍。"
        "但显存账本里最大的一项往往是激活，不是权重。"
        "拖 rank、批大小、序列长度与挂载层数，把总占用压进显卡。"
    ),
    "params": [
        # rank
        {"key": "rank", "label": "rank", "min": 4, "max": 128, "step": 4, "value": 16},
        # 基座维度 d（d_model）
        {"key": "dModel", "label": "隐藏维度 d", "min": 1024, "max": 8192, "step": 512, "value": 4096},
        # 层数
        {"key": "layers", "label": "层数", "min": 12, "max": 80, "step": 4, "value": 32},
        # 挂载的线性层数（q,k,v,o = 4；加 MLP 三个 = 7）
        {"key": "mountLayers", "label": "每层挂载数", "min": 1, "max": 7, "step": 1, "value": 4},
        # batch size：默认 32，配合 4096 序列会让激活爆掉——这是本章最真实的
        # 「上来就 OOM」场景，逼玩家先开梯度检查点、再降 seq/batch
        {"key": "batch", "label": "批大小", "min": 1, "max": 32, "step": 1, "value": 32},
        # 序列长度
        {"key": "seqLen", "label": "序列长度", "min": 256, "max": 4096, "step": 256, "value": 4096, "unit": "tok"},
        # 基座权重大小（GB）
        {"key": "baseGB", "label": "基座权重", "min": 1, "max": 70, "step": 1, "value": 13, "unit": "GB"},
        # 显卡显存
        {"key": "gpuGB", "label": "显卡显存", "min": 8, "max": 80, "step": 8, "value": 24, "unit": "GB"},
        # 梯度检查点：0=关，1=开（激活显存约降到 1/8）
        {"key": "gradCkpt", "label": "梯度检查点", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["关", "开"]},
    ],
    "metrics": [
        # 每层每挂载点的 LoRA 参数 = r × (d_in + d_out) = 2 × r × d
        {"key": "paramsPerLayer", "label": "每层挂载参数量", "expr": "2 * rank * dModel", "unit": "个", "fmt": "int"},
        # 总 LoRA 参数
        {"key": "totalParams", "label": "LoRA 总参数", "expr": "2 * rank * dModel * layers * mountLayers", "unit": "个", "fmt": "int"},
        # 适配器显存（fp16 = 2 字节）
        {"key": "adapterMB", "label": "适配器显存", "expr": "2 * rank * dModel * layers * mountLayers * 2 / 1000000", "unit": "MB", "fmt": "fix2"},
        # 激活显存（粗算）：batch × seq × d × layers × 2B ÷ 1e9，开梯度检查点降到 1/8
        {"key": "actMB", "label": "激活显存",
         "expr": "batch * seqLen * dModel * layers * 2 / 1000000 * if(gradCkpt == 1, 0.125, 1)",
         "unit": "MB", "fmt": "int"},
        # 总占用 = 权重 + 适配器 + 激活（GB）
        {"key": "totalGB", "label": "显存总占用",
         "expr": "baseGB + (2 * rank * dModel * layers * mountLayers * 2 / 1000000 + batch * seqLen * dModel * layers * 2 / 1000000 * if(gradCkpt == 1, 0.125, 1)) / 1024",
         "unit": "GB", "fmt": "fix2"},
        # 是否放得下
        {"key": "fits", "label": "是否放得下",
         "expr": "if(baseGB + (2 * rank * dModel * layers * mountLayers * 2 / 1000000 + batch * seqLen * dModel * layers * 2 / 1000000 * if(gradCkpt == 1, 0.125, 1)) / 1024 <= gpuGB, 1, 0)",
         "fmt": "int"},
        # 缩放系数 α/r（取 α = 2r 时的常数 2，这里演示「只翻 rank 不调 α 的后果」）
        {"key": "scaleRatio", "label": "缩放 α/r（α=32）", "expr": "32 / rank", "unit": "倍", "fmt": "fix2"},
    ],
    "checks": [
        # 必须放得下
        {"expr": "fits == 1", "label": "显存放得下"},
        # 适配器参数量别太大（<1% 基座才有意义）
        {"expr": "adapterMB <= 512", "label": "适配器 ≤512MB（LoRA 的意义是只训一小部分）"},
        # 下限：rank 不能太小，太小表达力不足（本章建议 r=8~16 起步）
        {"expr": "rank >= 8", "label": "rank ≥8（再小往往学不会）"},
        # 下限：批大小不能降到 1，单样本训练梯度噪声过大
        {"expr": "batch >= 2", "label": "批 ≥2（单样本梯度噪声大）"},
        # 下限：序列长度要覆盖真实任务
        {"expr": "seqLen >= 512", "label": "序列 ≥512 tok（再短覆盖不了典型任务）"},
        # 既定事实：基座模型规模（7B≈13GB fp16）、显卡（24GB 单卡）、
        # 挂载层数（q/k/v/o 四件套）、模型维度与层数都不该为了过关被改。
        # 全部 == 锁死——只要允许換大卡/换小模型，就变成「买硬件」而不是「算账」。
        # 锁死后唯一出路是「开梯度检查点 + 降 seq/batch/rank」，
        # 正是本章那句「先开梯度检查点 → 降 seq → 最后降 rank」。
        {"expr": "baseGB == 13", "label": "基座固定 7B/13GB（fp16 的固有体积）"},
        {"expr": "gpuGB == 24", "label": "显卡固定 24GB（既定硬件预算）"},
        {"expr": "mountLayers == 4", "label": "每层固定挂 q/k/v/o 四件套"},
        {"expr": "dModel == 4096", "label": "隐藏维度固定 4096（模型结构既定）"},
        {"expr": "layers == 32", "label": "层数固定 32（模型结构既定）"},
        # 本章明确的操作顺序：救 OOM 第一步就是开梯度检查点（激活降到约 1/8），
        # 它几乎不损表达力、代价只是重算。所以把它做成硬性要求，
        # 让玩家在「拧大 batch/seq 时」先习惯开它，而不是一上来就砍 rank。
        {"expr": "gradCkpt == 1", "label": "必须开梯度检查点（救 OOM 的第一步，几乎不损精度）"},
    ],
    "insight": (
        "LoRA 参数量 = rank × (d_in+d_out) × 层数 × 挂载层数，rank 翻倍参数量就翻倍，"
        "但表达力提升通常远小于 4 倍——所以默认 r=16 挂 q/k/v/o 跑基线。"
        "显存账本里最大的一项往往是激活而不是权重：7B 权重 13.5GB 是固定的，"
        "激活随手就是几 GB 且随 batch×seq 线性涨。所以救 OOM 的顺序是"
        "「先开梯度检查点 → 降 seq/batch → 最后才降 rank」。"
        "另外 α 要和 rank 一起调：LoRA 输出乘 α/r，只翻 rank 不调 α 等于把有效学习率减半。"
    ),
}


# ---------------------------------------------------------------------------
# 落盘
# ---------------------------------------------------------------------------
MODULES = {
    "bigdata/bd-ch02": bd_ch02,
    "bigdata/bd-ch04": bd_ch04,
    "data/data-ch01": data_ch01,
    "data/data-ch02": data_ch02,
    "java/java-ch07": java_ch07,
    "java/java-ch08": java_ch08,
    "agent/agent-ch05": agent_ch05,
    "agent/agent-ch07": agent_ch07,
}


def main() -> int:
    """读取 labs.json → 写入 8 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    for key, mod in MODULES.items():
        # 幂等：同一章节重复运行结果一致，不会叠加两份
        chapters[key] = [mod]
        print(f"added {key:<18} ({len(mod['params'])} params / {len(mod['checks'])} checks)")

    # indent=1 + newline="\n"：与仓库现有风格逐字节一致（indent=2 或 CRLF 会整份假 diff）
    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
