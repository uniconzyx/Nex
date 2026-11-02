# §5 bd-ch03 实战手记：凯喵带你把 Hive 用「慢」

> 前四节把表、分区、编译、倾斜讲透了。这一节凯喵把数仓里 HQL 最容易「跑一夜还不出数」的 12 个现场摆出来——Join 倾斜、小文件、谓词下推失效、动态分区炸裂。每个都是真金白银买的教训。

### 现场一：大表 Join 小表，不写 MapJoin 就 shuffle 到死

凯喵的报表任务把 10 亿行的订单表 JOIN 一个 100 行的维度表，默认走了 CommonJoin，全量 shuffle 跑 40 分钟。解法：小表（默认 ≤ 25MB，`hive.auto.convert.join=true`）会被**广播到每个 Map 任务**，在 map 端直接 join，零 shuffle。手动可写 `/*+ MAPJOIN(dim) */`。

```sql
-- ✅ 小表广播，map 端完成 join，无 shuffle
SELECT /*+ MAPJOIN(d) */ o.id, d.name
FROM orders o JOIN dim_shop d ON o.shop_id = d.id;
```

### 现场二：数据倾斜靠加 Reduce 数，热 key 仍在同一个桶

凯喵第一反应是「加大 `mapred.reduce.tasks`」，结果 99% 的任务几秒跑完，1 个卡了半小时。倾斜是「少数 key 数据量碾压」，加 Reduce 只改变取模基数，热 key 仍压到同一 Reduce（长尾）。先定位热 key，再盐。

```sql
-- 定位倾斜 key
SELECT shop_id, COUNT(*) c FROM orders GROUP BY shop_id ORDER BY c DESC LIMIT 10;
-- 热 key（如 NULL 或某爆款）单独处理
```

### 现场三：加盐（salting）+ 两阶段聚合消倾斜

凯喵的 GROUP BY 被一个 NULL key 拖垮，于是给 NULL 打随机前缀分散到多个 Reduce，聚合两次（先带盐聚合，再去盐汇总）。空值导致的倾斜先 `nvl` 打散或单独处理，避免全压在一个 Reduce。

```sql
-- 第一阶段：给热 key 加随机盐，分散到多个 reduce
SELECT concat(nvl(shop_id,'rand'), '_', floor(rand()*10)) AS k, sum(amount) s
FROM orders GROUP BY concat(nvl(shop_id,'rand'), '_', floor(rand()*10));
-- 第二阶段：去盐再聚合
```

### 现场四：SELECT * 让列式存储优势归零

凯喵的 ORC 表查 `SELECT *` 比预期慢好几倍。ORC/Parquet 的收益来自**列裁剪**（只物化 SELECT 的列）和**谓词下推**（过滤下推到 Scan 层）。`SELECT *` 把全部列都读出来，列存等于白上。只 SELECT 需要的列。

```sql
-- ❌ 读全部列，列存优势归零
SELECT * FROM user_behavior;
-- ✅ 只取需要的列 + 能下推的过滤列
SELECT user_id, event_type FROM user_behavior
WHERE dt = '2026-11-01' AND event_type = 'pay';
```

### 现场五：动态分区不设 nonstrict，全表被重写到任意分区

凯喵把分区值来自 SELECT 末尾列的动态分区任务一跑，瞬间生成几万个分区，NameNode 被打垮。默认 `strict` 要求至少一个静态分区防误写；确需全动态必须显式 `nonstrict` 并限制 `max.dynamic.partitions`，否则一个脏值就能造出海量分区。

```sql
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;   -- 风险操作，需显式开
SET hive.exec.max.dynamic.partitions = 1000;        -- 兜底上限
INSERT OVERWRITE TABLE logs PARTITION (dt)
SELECT col1, col2, dt FROM staging;
```

### 现场六：窗口函数不是 GROUP BY，行数不变

凯喵新人写「每组 Top-N」用 GROUP BY，结果每组只剩一行，丢了明细。窗口函数（含 `OVER (PARTITION BY ... ORDER BY ...)`）**不缩减行数**，在原行上附加聚合/排名。要每组 Top-N 用 `ROW_NUMBER() ... WHERE rn <= N`。

```sql
-- ✅ 每组 Top-N，明细保留
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY shop_id ORDER BY amount DESC) rn
  FROM orders
) t WHERE rn <= 3;
```

### 现场七：分区裁剪看 dt 用对，否则全分区扫描

凯喵的查询 `WHERE dt = '2026-11-01'` 秒回，改成 `WHERE substr(dt,1,7)='2026-11'` 就扫全表。因为对分区列做函数包裹，优化器无法做**分区裁剪**，只能逐个分区打开看。分区列要原样比较，别套函数。

```sql
-- ✅ 分区裁剪生效，只扫一个分区
SELECT COUNT(*) FROM logs WHERE dt = '2026-11-01';
-- ❌ 分区列被函数包裹，裁剪失效，全扫
SELECT COUNT(*) FROM logs WHERE substr(dt,1,10) = '2026-11-01';
```

### 现场八：小文件过多，Map 数爆炸还拖垮 NN

凯喵的表每天 INSERT 几十次，攒出几万个小文件，读的时候起几万个 Map，NameNode 元数据爆炸。治理：① 合并小文件 `hive.merge.smallfiles.avgsize`；② 用 ORC + 合理桶数；③ 写时控制 Reduce 数 / 用 `DISTRIBUTE BY` 控制输出文件数。

```sql
SET hive.merge.mapfiles = true;
SET hive.merge.smallfiles.avgsize = 128000000;  -- 小于 128M 触发合并
```

### 现场九：分桶表 JOIN 才能用 SMB Join 提速

凯喵想让两个大表 JOIN 快一点，发现分桶后 JOIN 明显加速。原理：两表按相同 key 分相同数量的桶，Hive 可做 **Sort-Merge-Bucket Join**，每个桶内部已排序，避免一个大表全 shuffle。前提是两边桶数成倍数且按 join key 分桶。

```sql
CREATE TABLE a (...) CLUSTERED BY (user_id) INTO 32 BUCKETS;
CREATE TABLE b (...) CLUSTERED BY (user_id) INTO 32 BUCKETS;
-- 同 key 同桶数 -> SMB Join 生效
```

### 现场十：外部表 DROP 不删数据，误删保护靠它

凯喵的同事 `DROP TABLE` 把对接 Kafka 落盘的表删了，数据也没了。区别：MANAGED（内部表）DROP 时**元数据和数据一起删**；EXTERNAL（外部表）DROP 只删元数据、**数据留在 HDFS**。对接外部系统、防误删的数据请用外部表。

```sql
CREATE EXTERNAL TABLE raw_logs (...) LOCATION '/data/logs/';  -- ❌ 删表不删数据
DROP TABLE raw_logs;  -- 元数据没了，HDFS 文件还在
```

### 现场十一：LATERAL VIEW explode 行列转换先想基数

凯喵用 `explode` 把数组炸开做标签统计，结果一行变几千行，下游聚合爆内存。`explode` 是**行展开**（一行数组 → 多行），会放大数据量。炸之前先过滤、先 `size` 评估基数，超大数组考虑先 `LIMIT` 采样。

```sql
SELECT tag, COUNT(*) FROM user_tags
LATERAL VIEW explode(tags) t AS tag
GROUP BY tag;
```

### 现场十二：HQL 转 MR 的 GROUP BY 有 Combiner，但 DISTINCT 没有

凯喵写 `COUNT(DISTINCT user_id)` 比 `COUNT(user_id)` 慢很多。因为普通 GROUP BY 在 Map 端有 Combiner 预聚合，而 **DISTINCT 难以在 map 端去重**（跨行），常需一次额外 shuffle。超大基数去重可用 `COUNT(DISTINCT)` 近似（HyperLogLog）或先子查询去重再 COUNT。

```sql
-- ❌ 大基数精确去重，单独 shuffle
SELECT COUNT(DISTINCT user_id) FROM pv;
-- ✅ 先去重再计数，减少上层数据量
SELECT COUNT(*) FROM (SELECT DISTINCT user_id FROM pv) t;
```

> 凯喵总结：Hive 慢的锅 90% 不在 SQL 写法难看，而在「Join 没广播」「倾斜没加盐」「列存被 SELECT * 废掉」「分区被函数包裹」。把这 12 个现场过一遍，报表从一夜变几分钟。

## 三视角解析
### 🧑‍💻 程序员视角
大表 Join 小表不写 MapJoin，会走 CommonJoin 触发全量 shuffle——小表几 MB 却要搬几十 GB 的大表，慢十倍。数据倾斜靠「加 Reduce 数」是无效的：热 key 还是落在一个 Reduce 上，必须加盐（给热 key 加随机后缀）做两阶段聚合。`SELECT *` 让列式存储的优势归零：ORC/Parquet 只读需要的列，`*` 会把所有列都读出来。分区裁剪失效（如对分区字段用函数）也会导致全表扫描。

### 🎓 博士生视角
Hive 的本质是「把 SQL 编译成 MapReduce/Tez/Spark 作业」，因此 SQL 的写法直接决定物理计划。列式存储（ORC/Parquet）的优势来自「按列读取 + 谓词下推 + 更高的压缩率」，这要求查询只触及必要列。Hive 的元数据存在 Metastore（通常是 MySQL），它使「表结构」与「数据文件」解耦，这是 Lakehouse 架构的雏形。

### 📚 考研者视角
大数据面试高频：
1. **内部表与外部表**：删除时的行为差异（外部表只删元数据）。
2. **分区与分桶**：目录级裁剪 vs 文件级哈希，各自适用场景。
3. **Join 策略**：MapJoin（小表广播）、CommonJoin（shuffle）、SMB Join（排序合并）。
4. **数据倾斜**：加盐两阶段聚合、热点 key 单独处理。
