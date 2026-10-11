# Hive 数据仓库与 HQL 易错点（高频踩坑与笔试面试易混口径）

1. **把内部表当外部表用，DROP 把数据一起删了** —— 错。内部表（MANAGED）`DROP TABLE` 会**同时删除元数据与 HDFS 数据**；外部表（EXTERNAL）只删元数据、保留数据。正确写法：对接外部系统（Flume/Kafka 落盘、其他引擎共用）的表一律建 `EXTERNAL`；需要 Hive 全托管的临时/中间表才用内部表。误删内部表数据不可恢复（除非有快照/回收站）。

2. **把分区字段当普通列，导致全表扫描、分区裁剪失效** —— 错。分区列是**目录层级**（`/dt=2024-01-02/`），不是行内字段；只有 `WHERE dt='...'` 这类**等值/范围过滤分区列**才能触发 partition pruning，直接跳过无关目录。正确写法：查询务必带上分区过滤条件；避免在分区列上做函数变换（如 `substr(dt,1,7)='2024-01'`）否则裁剪失效；分区粒度别过细（否则小文件爆炸）。

3. **分桶数随便设、或把分桶当分区用** —— 错。分桶按 `hash(bucket_col) % N` 决定文件（`/000000_0 ...`），用于 JOIN 避免 shuffle、采样、`SORTED BY`；分区是目录级裁剪。二者正交：分区管「扫哪些目录」，分桶管「目录内如何切文件」。正确写法：分桶数取 2 的幂、与 Reduce 数对齐；只有**两表按同一列、同一桶数分桶**的 JOIN 才能走分桶 MapJoin；建表必须 `CLUSTERED BY(col) INTO N BUCKETS` + 写入时 `set hive.enforce.bucketing=true`。

4. **认为 MapJoin 永远最优、小表一定能广播** —— 错。MapJoin 仅当小表能放进各 Map 任务内存（`hive.auto.convert.join` 默认阈值约 25MB，由 `hive.mapjoin.smalltable.filesize` 控制）才安全；小表过大广播会 OOM、或退化为 CommonJoin。正确写法：确认小表真实大小再开 MapJoin；维度表膨胀后改用分桶 JOIN 或 SMB Join；用 `/*+ MAPJOIN(dim) */` 仅当自动转换不生效时强制。

5. **动态分区不设 nonstrict，整张表被误写/作业失败** —— 错。动态分区让分区值来自 `SELECT` 末尾列，可能瞬间生成海量分区；默认 `hive.exec.dynamic.partition.mode=strict` 要求至少一个静态分区，防误把全表重写到任意分区。正确写法：确需全动态时显式设 `nonstrict` 并限制 `hive.exec.max.dynamic.partitions`，否则一个脏数据值就能造出几万个分区拖垮 NN。

6. **数据倾斜靠「加大 Reduce 数」解决** —— 错。倾斜是「某一/少数 key 数据量碾压其余」，加 Reduce 数只改变取模基数、把热 key 仍压到同一个 Reduce（长尾卡 99%）。正确写法：先用 counters/监控定位热 key；小表侧用 MapJoin 消 shuffle；大表自身热 key 用**加盐（salting）+ 两阶段聚合**或自定义 Partitioner 单独路由；空值导致的倾斜先 `nvl` 打散或单独处理。

7. **以为列式存储「自动」就快，不写谓词下推/列裁剪** —— 错。ORC/Parquet 的收益来自**列裁剪**（只物化 `SELECT` 的列）与**谓词下推**（过滤下推到 Scan 层，尽量少读、尽早过滤）。若 `SELECT *` 或过滤列不在存储统计里，列存优势大打折扣。正确写法：只 `SELECT` 需要的列；把过滤条件写在能下推的列上（分区列、排序列、有 min/max 统计的列）；避免对列做函数包裹破坏下推。

8. **窗口函数和 GROUP BY 混为一谈** —— 错。`GROUP BY` **缩减行数**（每组聚成一行）；窗口函数（含 `OVER (PARTITION BY ... ORDER BY ...)`）**不缩减行数**，在原行上附加聚合/排名结果。正确写法：要「每组 Top-N」用 `ROW_NUMBER() ... WHERE rn<=N`；要「每组聚合后拼回明细」用窗口聚合而非 GROUP BY；注意窗口函数通常在 Reduce 端计算，数据量大时同样会倾斜。
