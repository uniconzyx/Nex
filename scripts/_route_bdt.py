# -*- coding: utf-8 -*-
"""来源颗粒度 · bigdata 6 章 + data 6 章 + tooling 6 章。"""
import sys

from _route_granularity import apply

# ---------------- bigdata ----------------
ZOOM = 'DataTalksClub/data-engineering-zoomcamp'
SPARK = 'apache/spark'
NOTES = 'heibaiying/BigData-Notes'
HADOOP = 'apache/hadoop'

BIGDATA = {
    'bd-ch01': {
        HADOOP: ('§1.2', '讲「NameNode 元数据常驻内存」时读 `hadoop-hdfs-project/hadoop-hdfs/src/main/java/org/apache/hadoop/hdfs/server/namenode/` 下的 `FSDirectory` 与 `INodeFile`：目录树与块列表就是这两个类，内存占用随「文件数」而非「数据量」增长——小文件问题的物理根源在这'),
        NOTES: ('§2.1', '讲「写入 pipeline」时读根目录的 `HDFS.md`：它用一张流程图画出「客户端 → DN1 → DN2 → DN3 → ack 回传」，配本章的 pipeline 章节对照看，能把「哪个环节挂掉会重试」串起来'),
        ZOOM: ('§1.3', '讲「从单机到分布式的动机」时看 `week5-batch/` 的批处理作业脚本：同一份数据在单机 pandas 与集群 Spark 上的耗时对比，是「容量与吞吐」这两个动机的实测证据'),
        SPARK: ('§3.1', '讲「HDFS 与计算引擎的分层」时读 `core/src/main/scala/org/apache/spark/rdd/` 里对 `HadoopRDD` 的实现：Spark 把 HDFS 的 split 直接当分区，不搬数据只搬计算——这就是「计算向数据靠拢」'),
    },
    'bd-ch02': {
        HADOOP: ('§1.1', '讲「MapReduce 三阶段」时读 `hadoop-mapreduce-project/hadoop-mapreduce-client/` 下的 `MapTask`/`ReduceTask`：`MapTask` 的 `runNewMapper` 里就是 map → partition → sort → spill 的实际顺序，与本章数据流图一一对应'),
        NOTES: ('§2.2', '讲「Combiner 的语义边界」时读 `MapReduce.md`：它用 WordCount 演示「加 Combiner 前后 shuffle 数据量差多少」，并强调「求平均必须传 (sum, count)」这条限制'),
        SPARK: ('§3.1', '讲「YARN 的资源模型」时读 `resource-managers/yarn/src/main/scala/org/apache/spark/deploy/yarn/`：`ApplicationMaster` 申请 Container、`ExecutorAllocationManager` 动态伸缩，都是「RM 管资源、AM 管作业」的落地'),
        ZOOM: ('§2.1', '讲「Shuffle 的磁盘溢出」时看 `week5-batch/` 的作业调优笔记：「分区数设太大 → 大量小文件」「设太小 → 单分区 OOM」这两条经验在本章有对应的计算式'),
    },
    'bd-ch03': {
        HADOOP: ('§1.3', '讲「Hive 与 Hadoop 的关系」时读 `hive/` 模块（在 `apache/hive` 而非 hadoop 仓库）的执行计划接口：Hive 只负责把 HQL 编译成 MR/Tez 作业，真正的执行仍由 Hadoop 完成'),
        NOTES: ('§2.1', '讲「内部表 vs 外部表」时读 `Hive.md`：删内部表连数据一起删、删外部表只删元数据，这条差异在文档里配了 `LOCATION` 的对照实验，比背定义好记'),
        ZOOM: ('§3.2', '讲「列式存储的收益」时看 `week4-analytics/` 的查询对比：同一份数据存 CSV 与 Parquet，扫描列数少时后者快一个数量级——谓词下推与列裁剪的实测'),
        SPARK: ('§4.1', '讲「HQL 到物理计划的映射」时读 `sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/optimizer/`：`PushPredicateThroughJoin`、`ColumnPruning` 这些规则就是「谓词下推、列裁剪」在 Spark 侧的等价物'),
    },
    'bd-ch04': {
        SPARK: ('§1.1', '讲「RDD 的五大特性」时读 `core/src/main/scala/org/apache/spark/rdd/RDD.scala`：`getPartitions`/`compute`/`getDependencies` 三个抽象方法就是「分区列表 + 计算函数 + 依赖」的代码化，其余两个是优化信息'),
        ZOOM: ('§2.3', '讲「惰性求值」时看 `week5-batch/` 的 Spark 作业：`df.filter(...)` 之后不打 `show()`/`count()` 就什么都不执行，脚本里加不加 action 决定「有没有真的跑」'),
        NOTES: ('§3.1', '讲「宽窄依赖与 Stage」时读 `Spark.md`：它画了「窄依赖可流水线、宽依赖要 shuffle」的依赖图，并给出「Stage 数 = 宽依赖数 + 1」的算式'),
        HADOOP: ('§4.2', '讲「血缘容错 vs 副本容错」时对照 `hadoop-hdfs-project/` 的副本机制：HDFS 靠「多存几份」，Spark 靠「重算丢失分区」——前者贵在存储、后者贵在计算，这是两种容错哲学'),
    },
    'bd-ch05': {
        SPARK: ('§2.1', '讲「Catalyst 四阶段」时读 `sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/`：`analyzer/`（解析）→ `optimizer/`（逻辑优化）→ `planner/`（物理计划）→ `codegen`（生成字节码），目录结构本身就是四阶段的证据'),
        ZOOM: ('§3.1', '讲「AQE 纠正误判」时看 `week5-batch/` 的 Spark SQL 作业日志：`spark.sql.adaptive.enabled=true` 后，`SortMergeJoin` 会被运行时统计改成 `BroadcastHashJoin`，日志里能看到 `Plan changed`'),
        NOTES: ('§1.3', '讲「DataFrame 与 RDD 的差别」时读 `Spark.md` 的 Spark SQL 篇：DataFrame 携带 schema、能进优化器，RDD 是黑盒函数——「结构化信息就是优化空间」这句话的来源'),
        HADOOP: ('§4.1', '讲「Metastore 的作用」时对照 `hive/` 的元数据表设计：库/表/分区/列都存 MySQL，Spark SQL 通过 `HiveExternalCatalog` 读写同一份元数据——这就是「湖仓共用 Metastore」的由来'),
    },
    'bd-ch06': {
        ZOOM: ('§1.2', '讲「ODS/DWD/DWS/ADS 四层」时看 `week4-analytics/` 的数仓作业：从原始 JSON 到宽表再聚合到指标表，每一层的输入输出都是独立的表，层与层的调用关系就是分层规范的落地'),
        NOTES: ('§2.2', '讲「维度建模与粒度」时读 `BigData-Notes` 里的数仓篇：「先声明粒度再选维度」这条顺序错了，后面所有指标口径都会漂移——文档给了「订单事实表」的完整推演'),
        HADOOP: ('§3.1', '讲「调度与 SLA」时对照 `hadoop-yarn-project/` 的队列与容量调度：YARN 的 `CapacityScheduler` 决定「哪个队列先跑」，数仓的基线任务要放在高优先级队列，否则被离线任务挤掉'),
        SPARK: ('§4.3', '讲「小文件合并」时读 `sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/` 的写入路径：`repartition` 与 `coalesce` 在写出前决定文件数，分区数乘作业批次就是「每天新增多少小文件」'),
    },
}

# ---------------- data ----------------
SK = 'scikit-learn/scikit-learn'
PDSH = 'jakevdp/PythonDataScienceHandbook'
PANDAS = 'pandas-dev/pandas'
DSB = 'microsoft/Data-Science-For-Beginners'

DATA = {
    'data-ch01': {
        PDSH: ('§1.1', '讲「ndarray 是数据 + 形状 + 步长」时读 `notebooks/02.02-The-Basics-Of-NumPy-Arrays.ipynb`：它用 `flags`、`strides`、`nbytes` 三个属性把「一块内存 + 元信息」直接打出来，比画图更直观'),
        PANDAS: ('§2.3', '讲「连续内存与缓存」时读 `pandas/core/internals/` 下的 Block 管理：pandas 按 dtype 把同类型列聚成 Block，就是为了「连续访问 + 向量化」，与 ndarray 的 C 顺序是同一个动机'),
        SK: ('§3.1', '讲「向量化与 BLAS」时读 `sklearn/utils/extmath.py`：所有矩阵运算最后都落到 `numpy.dot`（底层 BLAS），所以「特征矩阵按行存」不是风格问题，而是让 BLAS 能走连续内存'),
        DSB: ('§2.1', '讲「数据准备的第一步」时看 `2-Working-With-Data/`：先把数据读成 ndarray/DataFrame 再谈建模，形状与 dtype 没对齐时后面全是错'),
    },
    'data-ch02': {
        PDSH: ('§2.1', '讲「广播从尾轴对齐」时读 `notebooks/02.05-Computation-on-arrays-broadcasting.ipynb`：它用 `(3,1)` 与 `(1,4)` 相加得到 `(3,4)` 的例子，把「缺的维补 1、1 可以拉伸」讲成一张图'),
        SK: ('§3.2', '讲「向量化不是银弹」时读 `sklearn/utils/` 里的分块处理：大数据集要先 `train_test_split` 或分块，否则一次性构造的距离矩阵会直接 OOM——这正是广播隐式物化的风险'),
        PANDAS: ('§1.2', '讲「einsum 与矩阵乘」时读 `pandas/core/array_algos/`：底层把「按轴求和」翻译成 `einsum`/`dot`，走的是同一套 BLAS 路径，所以「向量化写法性能接近」不是巧合'),
        DSB: ('§4.1', '讲「随机可复现」时看课程里的建模脚本：所有 `train_test_split` 都带 `random_state`，否则「同一份代码两次结果不同」无法排查'),
    },
    'data-ch03': {
        PANDAS: ('§1.1', '讲「DataFrame 的列式存储」时读 `pandas/core/frame.py` 与 `internals/managers.py`：DataFrame 不是「行列表」，而是「按 dtype 分块的二维结构」，这解释了「混类型列会让操作变慢」'),
        PDSH: ('§2.2', '讲「索引与切片」时读 `notebooks/03.02-Data-Indexing-and-Selection.ipynb`：`loc` 闭区间、`iloc` 左闭右开——两种切片的边界规则不同，混用就是「取出来的行数不对」'),
        SK: ('§3.1', '讲「缺失值处理」时读 `sklearn/impute/`：`SimpleImputer` 的 `strategy` 与 pandas 的 `fillna` 是两套语义（前者在管道内、后者在数据上），混用时要注意「训练/推理口径一致」'),
        DSB: ('§4.2', '讲「数据清洗的顺序」时看 `2-Working-With-Data/`：先处理类型与缺失、再做衍生特征，顺序反了会得到「用脏数据算出来的特征」'),
    },
    'data-ch04': {
        PANDAS: ('§1.2', '讲「groupby 的实现」时读 `pandas/core/groupby/`：先按键做哈希分组、再对每组应用聚合，`as_index=False` 与 `reset_index()` 的差别就出在「分组键是否进索引」'),
        PDSH: ('§2.3', '讲「merge 的四种连接」时读 `notebooks/03.07-Merge-and-Join.ipynb`：inner/left/right/outer 的行数变化配了对照表，`indicator=True` 用来查「哪边没匹配上」'),
        SK: ('§3.3', '讲「时间序列的特征工程」时读 `sklearn/preprocessing/`：`rolling` 的窗口统计必须用「过去的数据」，否则就是未来信息泄漏——sklearn 的 pipeline 能强制这个边界'),
        DSB: ('§4.3', '讲「聚合后的口径」时看课程里的分组分析：`count`/`nunique` 混用会把「订单数」算成「商品数」，指标定义要先写清再写代码'),
    },
    'data-ch05': {
        PDSH: ('§1.1', '讲「数据来源与格式」时读 `notebooks/03.03-Hierarchy-Indexing.ipynb`：层级索引能把「多来源数据」压进一个 DataFrame，比手工拼列更不容易错位'),
        DSB: ('§2.2', '讲「采集的合规边界」时看 `1-Introduction/` 里的数据伦理一课：只采公开且允许抓取的数据、遵守 robots.txt 与频率限制——这条在本章有明确约束'),
        PANDAS: ('§3.1', '讲「解析后落表」时读 `pandas/io/json/`：`json_normalize` 把嵌套 JSON 拍平成表，是「采集 → 结构化」最常用的一步'),
        SK: ('§4.1', '讲「采集数据的质量校验」时读 `sklearn/utils/validation.py` 的 `check_array`：形状、dtype、NaN 的检查顺序，可以直接照搬成采集后的自检清单'),
    },
    'data-ch06': {
        SK: ('§1.1', '讲「建模流程」时读 `sklearn/pipeline.py`：`Pipeline` 把「预处理 + 模型」串成一步，`fit` 只在训练集上调用——这是防泄漏的结构性保证，不是纪律问题'),
        PDSH: ('§2.2', '讲「特征与目标的关系」时读 `notebooks/05.xx` 系列（机器学习篇）：先用散点图看关系再选模型，比盲试模型更快排除方向性错误'),
        PANDAS: ('§3.2', '讲「结果汇总」时读 `pandas/core/reshape/`：`pivot_table` 把「模型 × 指标」摊成矩阵，是写实验报告最省事的结构'),
        DSB: ('§4.1', '讲「从问题到方案」时看 `4-Data-Science-Lifecycle/`：先定义「成功标准」再选指标，否则模型分数再高也可能答错了问题'),
    },
}

# ---------------- tooling ----------------
SECRET = 'trimstray/the-book-of-secret-knowledge'
ZSH = 'ohmyzsh/ohmyzsh'
AOCL = 'jlevy/the-art-of-command-line'
DEVOPS = 'bregman-arie/devops-exercises'

TOOLING = {
    'tool-ch01': {
        AOCL: ('§1.2', '讲「文件与目录操作」时读 `README.md` 的「文件及数据处理」一节：`find`/`xargs`/`grep` 的组合用法给了可直接抄的一行命令，比 man 手册好上手'),
        DEVOPS: ('§2.1', '讲「权限位」时看 `topics/linux/` 的权限练习：`chmod 755` 与 `chmod u+x` 的等价关系、`umask` 如何影响新建文件，题后有答案可自测'),
        SECRET: ('§3.1', '讲「排障入口」时看分类里的「Sysadmin」一节：`df`/`du`/`lsof`/`ss` 这几个命令的定位分工，正好对应本章「先看哪一层」的顺序'),
        ZSH: ('§4.1', '讲「Shell 环境」时读 `lib/` 下的主题与补全脚本：`PATH`、别名、补全函数的加载顺序，决定了「为什么我的命令找不到」'),
    },
    'tool-ch02': {
        AOCL: ('§2.2', '讲「进程管理」时读 `README.md` 的「进程管理」一节：`ps`/`top`/`kill` 的组合，以及「先找 PID 再发信号」的顺序，避免 `kill -9` 乱杀'),
        DEVOPS: ('§3.1', '讲「管道与重定向」时看 `topics/linux/` 的练习题：`|`、`>`、`2>`、`tee` 的差别在题里被拆成若干小问，答错会立刻暴露理解漏洞'),
        ZSH: ('§1.2', '讲「Shell 脚本的健壮性」时读 `oh-my-zsh.sh` 开头的选项设置：`setopt` 系列让脚本遇错即停、未定义变量报错——这是「脚本别默默跑错」的开关'),
        SECRET: ('§4.2', '讲「一行命令解决一件事」时看「Shell one-liners」分类：把常见运维动作压成单行，是「管道思维」的最好训练材料'),
    },
    'tool-ch03': {
        AOCL: ('§1.1', '讲「Git 的日常操作」时读 `README.md` 的「版本控制」一节：`add`/`commit`/`log`/`diff` 的最小闭环，配 `git log --oneline --graph` 看历史形状'),
        DEVOPS: ('§2.1', '讲「对象模型」时看 `topics/git/` 的练习：`git cat-file -p` 查看 blob/tree/commit 的内容，能把「三个对象」从概念变成可见的文本'),
        SECRET: ('§3.2', '讲「分支与合并」时看「Git」分类里的速查：`rebase` 与 `merge` 的取舍、`reflog` 救回误删分支，都是高频操作'),
        ZSH: ('§4.1', '讲「别名与效率」时读 `plugins/git/git.plugin.zsh`：几十个别名把长命令压成两三个字母，理解它们等于理解「日常 Git 的主力命令是哪些」'),
    },
    'tool-ch04': {
        AOCL: ('§2.2', '讲「冲突解决」时读「版本控制」一节的合并说明：先 `git status` 看冲突文件、再逐个 `<<<<<<<` 标记处理，最后 `add` 结束合并——顺序错了会卡在中间态'),
        DEVOPS: ('§3.1', '讲「分支策略」时看 `topics/git/` 的分支练习：feature/release/hotfix 三类分支的合并方向，题里给了「什么情况下该从哪个分支切」的判断'),
        SECRET: ('§4.3', '讲「仓库卫生」时看「Git」分类里的清理命令：`git gc`、`git prune`、删除已合并分支，避免仓库越用越臃肿'),
        ZSH: ('§1.3', '讲「提交前的自检」时读 `plugins/git/` 里的 `gst`/`gd`/`gl` 别名：把「看状态 → 看差异 → 看历史」压成三个动作，形成固定节奏'),
    },
    'tool-ch05': {
        DEVOPS: ('§1.1', '讲「镜像分层」时看 `topics/docker/` 的练习题：每条 `RUN` 生成一层、层是只读的，所以「合并 RUN」能减小体积——题里有前后对比'),
        AOCL: ('§2.1', '讲「容器里的调试」时读「系统调试」一节：容器内没有 `ps`/`curl` 时用 `docker exec` 进容器、或用 `nsenter` 进命名空间，是排障的两条路'),
        SECRET: ('§3.2', '讲「namespace 与 cgroup」时看「Containers」分类：`unshare`/`nsenter`/`cgcreate` 这些底层命令能手工复现容器的隔离，验证「容器不是虚拟机」'),
        ZSH: ('§4.2', '讲「开发环境一致性」时读 `lib/` 与 `plugins/` 的组织：把配置放进镜像而不是「每人本机装一遍」，是「环境即代码」的最小实践'),
    },
    'tool-ch06': {
        DEVOPS: ('§1.3', '讲「Compose 的编排模型」时看 `topics/docker/` 的多容器练习：`depends_on` 只管启动顺序不管就绪，所以健康检查要单独配——这是「服务起来了但连不上」的常见原因'),
        SECRET: ('§2.3', '讲「部署的排障顺序」时看「Sysadmin」分类：先看端口是否监听（`ss -lntp`）、再看进程是否活着、最后看日志，三步定位比盲查快'),
        AOCL: ('§3.1', '讲「网络与端口」时读「网络」一节：`curl -v`、`ss`、`tcpdump` 的分工——分别回答「应用层通不通」「端口开没开」「包到没到」'),
        ZSH: ('§4.1', '讲「环境变量与配置注入」时读 `lib/` 里对 `PATH` 的处理：容器里同样靠环境变量注入配置，理解 Shell 的变量作用域能避免「变量在容器里读不到」'),
    },
}

if __name__ == '__main__':
    apply('bigdata', BIGDATA)
    apply('data', DATA)
    apply('tooling', TOOLING)
    sys.exit(0)
