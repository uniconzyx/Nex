# 一、内部表（MANAGED）vs 外部表（EXTERNAL）

（中立陈述）Hive 的表在 Metastore 中记录**元数据**（库/表名、列类型、SerDe、存储位置 `LOCATION`）；数据本身落在 HDFS。表的「托管关系」由建表时是否带 `EXTERNAL` 决定：**内部表**由 Hive 全托管——`DROP` 时元数据与 HDFS 数据**一起删除**；**外部表**仅由 Hive 记录元数据——`DROP` 时**只删元数据、保留 HDFS 数据**。二者查数据、写 SQL 的方式完全一致，区别只在 `DROP`/表重建时的数据去留。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 内部表 vs 外部表：DROP 时元数据/数据的去留

```python
# 模拟 Hive Metastore + HDFS，演示内部表 / 外部表 DROP 的差异
metastore = {}   # table_name -> dict(type, location)
hdfs = {}        # location -> set of file names

def create_table(name, table_type, location, files):
    metastore[name] = {"type": table_type, "location": location}
    hdfs[location] = set(files)
    print(f"CREATE {table_type} TABLE {name} LOCATION '{location}'")
    for f in files:
        print(f"   -> HDFS 写入数据文件: {location}/{f}")

def drop_table(name):
    t = metastore.pop(name)
    loc = t["location"]
    if t["type"] == "INTERNAL":
        removed = hdfs.pop(loc, set())
        print(f"DROP TABLE {name} (内部表): 删除元数据 + 删除数据文件 {sorted(removed)}")
    else:
        kept = hdfs.get(loc, set())
        print(f"DROP TABLE {name} (外部表): 仅删除元数据，保留数据文件 {sorted(kept)} (需手动 hdfs dfs -rm)")

create_table("emp_internal", "INTERNAL", "/warehouse/emp", ["part-00000", "part-00001"])
create_table("emp_external", "EXTERNAL", "/raw/emp", ["part-00000", "part-00001"])
print("\n--- DROP 之前 ---")
print("metastore 表:", list(metastore.keys()))
print("HDFS 占用:", {k: sorted(v) for k, v in hdfs.items()})

drop_table("emp_internal")
drop_table("emp_external")

print("\n--- DROP 之后 ---")
print("metastore 表:", list(metastore.keys()))
print("HDFS 占用:", {k: sorted(v) for k, v in hdfs.items()})
print("\n结论: 内部表 DROP 连数据一起删(危险, 需谨慎); 外部表 DROP 只删元数据(数据安全, 常用于对接外部系统)")
```

实际输出：

```text
CREATE INTERNAL TABLE emp_internal LOCATION '/warehouse/emp'
   -> HDFS 写入数据文件: /warehouse/emp/part-00000
   -> HDFS 写入数据文件: /warehouse/emp/part-00001
CREATE EXTERNAL TABLE emp_external LOCATION '/raw/emp'
   -> HDFS 写入数据文件: /raw/emp/part-00000
   -> HDFS 写入数据文件: /raw/emp/part-00001

--- DROP 之前 ---
metastore 表: ['emp_internal', 'emp_external']
HDFS 占用: {'/warehouse/emp': ['part-00000', 'part-00001'], '/raw/emp': ['part-00000', 'part-00001']}
DROP TABLE emp_internal (内部表): 删除元数据 + 删除数据文件 ['part-00000', 'part-00001']
DROP TABLE emp_external (外部表): 仅删除元数据，保留数据文件 ['part-00000', 'part-00001'] (需手动 hdfs dfs -rm)

--- DROP 之后 ---
metastore 表: []
HDFS 占用: {'/raw/emp': ['part-00000', 'part-00001']}

结论: 内部表 DROP 连数据一起删(危险, 需谨慎); 外部表 DROP 只删元数据(数据安全, 常用于对接外部系统)
```

> 出处：`examples/ex01.json`。改一处再看输出变没变，比读三遍解释有用。

### 分区表的分区裁剪（partition pruning）

```python
# 模拟分区表的分区裁剪 (partition pruning)
partitions = {
    "2024-01-01": [("a", 1), ("b", 2)],
    "2024-01-02": [("c", 3), ("d", 4), ("e", 5)],
    "2024-01-03": [("f", 6)],
}

def scan_all():
    rows = []
    scanned = list(partitions.keys())
    for p in scanned:
        rows += partitions[p]
    return scanned, rows

def scan_pruned(target_dt):
    if target_dt in partitions:
        return [target_dt], partitions[target_dt]
    return [], []

print("分区表 emp_dt 共有分区:", list(partitions.keys()))
# 未裁剪: 全表扫描
sc, rows = scan_all()
print(f"查询 SELECT * FROM emp_dt (无分区过滤): 扫描 {len(sc)} 个分区 = {sc}, 读出 {len(rows)} 行")
# 裁剪: 按 dt 过滤
sc2, rows2 = scan_pruned("2024-01-02")
print(f"查询 ... WHERE dt='2024-01-02': 仅扫描 {len(sc2)} 个分区 = {sc2}, 读出 {len(rows2)} 行")
print("分区裁剪收益: 少扫描", len(sc) - len(sc2), "个分区, I/O 按分区目录直接跳过, 不读无关数据")
```

实际输出：

```text
分区表 emp_dt 共有分区: ['2024-01-01', '2024-01-02', '2024-01-03']
查询 SELECT * FROM emp_dt (无分区过滤): 扫描 3 个分区 = ['2024-01-01', '2024-01-02', '2024-01-03'], 读出 6 行
查询 ... WHERE dt='2024-01-02': 仅扫描 1 个分区 = ['2024-01-02'], 读出 3 行
分区裁剪收益: 少扫描 2 个分区, I/O 按分区目录直接跳过, 不读无关数据
```

> 出处：`examples/ex02.json`。改一处再看输出变没变，比读三遍解释有用。

### 🧑‍💻 程序员视角
- 工程铁律：只要数据**不是 Hive 独占生成**的（Flume/Kafka 落盘、Spark 写出的中间结果、别的引擎也要读），一律建 `EXTERNAL`。否则一次误 `DROP` 就把上游数据删光、且不可恢复（除非开 Trash/快照）。
- 反向：纯 Hive 内部加工链路的临时/中间表用内部表，删表即清数据，省得留一堆孤儿目录占 NN 元数据。
- 排障：表查不到数据但 `DESCRIBE` 还在，多半是外部表 `LOCATION` 指向的目录被别的作业挪走；内部表则不用担心这点（Hive 自己管路径）。

### 🎓 博士生视角
- 抽象边界：Hive 把「**命名空间（元数据）**」与「**物理存储（HDFS 文件）**」解耦。内部表是「强拥有」语义（生命周期绑定），外部表是「弱引用」语义（生命周期独立）——这是引用计数式资源管理与外部资源管理的经典分野。
- 正确性不变量：`DROP` 内部表必须保证「元数据删除」与「数据删除」要么都成功、要么都可见（Hive 先删元数据再删数据，失败则可能留孤儿数据；实践中靠 Trash 兜底）。外部表的 `DROP` 则是纯元数据操作，恒等幂等。
- 与存储层关系：外部表的存在，使 Hive 能作为「**只读/共享查询层**」挂在既有数据湖之上，而不必复制数据——这是 Lakehouse 架构（Hive Metastore 作为统一 Catalog）的底层前提。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「内部表和外部表的区别？DROP 时分别会怎样？」标准答：内部表 Hive 托管数据，`DROP` 删元数据+数据；外部表只删元数据、保留数据，常用于对接外部系统。
- 易错口径：二者**查询/写入语法完全一样**，区别只在生命周期；很多人误以为外部表「不能写入」或「性能更差」——错，写性能无差别。
- 关联考点：与「Hive Metastore 的作用（统一元数据/Catalog）」连考；与外部表支撑「数据共享 / 多引擎共用同一份数据」的架构意义结合。

---

# 二、表的生命周期与 LOCATION / EXTERNAL 工程约定

（中立陈述）建表语句中 `LOCATION` 指定数据在 HDFS 的绝对路径；不指定时内部表落在 `hive.metastore.warehouse.dir`（默认 `/user/hive/warehouse`）。`EXTERNAL` 关键字让表与数据解绑。表还可以用 `TBLPROPERTIES` 记录 owner、注释、是否可被查询等元信息。表的生命周期管理本质是「**元数据操作**」与「**数据操作**」的配对纪律。

### 🧑‍💻 程序员视角
- 落库规范：生产数仓里 ODS（贴源层）几乎全是外部表指向原始落盘目录；DWD/DWS/ADS 内部加工层才用内部表。重建表时外部表 `CREATE EXTERNAL ... LOCATION` 即可重新挂上旧数据，零拷贝。
- 误删预案：开 HDFS Trash（`fs.trash.interval`）让内部表 `DROP` 的数据先进回收站可救；外部表则天然不怕 `DROP`。
- 命名与权限：外部表 `LOCATION` 常跨团队目录，注意 HDFS 权限（ranger/sentry）别让 Hive 进程无读权限导致查询空结果。

### 🎓 博士生视角
- 生命周期一致性：表与其数据的「引用关系」是一种轻量级的**资源元数据协议**。理想实现应保证「没有元数据指向的数据」最终被 GC（Hive 不自动做，需 `msck repair` / 人工清理），以及「有元数据但数据丢失」能被快速检测（`DESCRIBE` 正常但查询报错）。
- 演进：Iceberg/Hudi 等表格式把「数据文件清单」也纳入**事务性元数据**（snapshot），外部表概念被弱化——任何引擎都能安全读写同一份数据且互不破坏，这是从「Hive 弱引用」到「表格式强事务」的范式升级。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「什么时候该用外部表？」标准答：数据共享、对接外部系统、防止误删数据时；反之 Hive 独占的中间结果用内部表。
- 易错口径：误以为 `LOCATION` 只对外表有意义——其实内部表也能指定 `LOCATION`；区别不在有没有 `LOCATION`，而在 `EXTERNAL` 关键字。
- 关联考点：与「Hive Metastore 作为统一 Catalog 支撑多计算引擎（Spark/Presto/Flink）」结合考，这是现代数据湖架构的高频题。
