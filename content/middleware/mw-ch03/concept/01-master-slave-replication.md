# 一、主从复制：全量同步与部分同步

本文件覆盖两个核心主题：**① 全量同步 PSYNC（主节点 fork RDB + 从节点载入）** 与 **② 部分同步 repl_backlog、复制偏移量 offset 与心跳 REPLCONF ACK**。

---

## ① 全量同步 PSYNC：首次或无法续传时的 RDB 传输

（中立陈述）从节点启动或断线过久后，向主节点发送 `PSYNC ? -1`（首次）或 `PSYNC <replid> <offset>`（带历史）。主节点若支持部分同步且 backlog 仍保留对应偏移，则回 `CONTINUE` 走增量；否则回 `FULLRESYNC <replid> <offset>`，fork 子进程生成 RDB 全量快照并通过 socket 发给从节点，从节点清空本地后载入 RDB，再补发缓冲区里的增量写命令。见 `examples/ex01_fullsync_psync.json`。

### 🧑‍💻 程序员视角
- **线上首次同步很重**：全量同步要 fork + 传 RDB + 从节点载入，数据量大时主节点 fork 阻塞（`latest_fork_usec`）、网络传输、从节点载入都会显著消耗资源；生产上从节点尽量错峰接入，别一股脑全重启。
- **`replicaof` 的坑**：执行 `REPLICAOF` 切换主节点时从节点会先清空旧数据再全量同步，期间读请求可能返回空/旧值，切换窗口要配合熔断。
- **diskless 复制**：大内存实例磁盘慢时可用 `repl-diskless-sync yes`，主节点不落盘直接网络流式发给从节点，减少磁盘 IO；但并发多个从节点会排队。
- **主从延迟要监控**：`info replication` 里的 `master_repl_offset` 与 `slave_repl_offset` 差值即延迟字节，做读写分离时读从节点的陈旧数据要能容忍这个延迟。

### 🎓 博士生视角
- **PSYNC 的状态机**：从节点保存 `master_replid` 与自己的 `offset`；重连时主节点比对「自己的 replid」与「从节点上报的 replid」——不匹配（换主）或 offset 已滑出 backlog 窗口，则退化全量；匹配且 offset 在 `repl_backlog` 区间内则部分同步。
- **为什么用 fork + RDB 而不是在线拷贝**：与 BGSAVE 同理，fork 后子进程获得一致性内存视图（COW），主节点继续服务写命令；这些新写进入「复制缓冲区」（client output buffer 与 repl_backlog），全量传完后再补发，保证不丢增量。
- **backlog 是环形缓冲**：`repl_backlog` 固定大小（`repl-backlog-size`，默认 1MB）、环形复用；它同时服务「部分同步」与「复制管道断点续传」，offset 是全局单调递增的逻辑时钟。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Redis 主从复制的全量同步流程？」答：从发 `PSYNC` → 主 `FULLRESYNC` + fork 生成 RDB → 传输 RDB → 从清空载入 → 主补发增量写命令 → 完成同步。
- **关键字段**：`replid`（复制 ID，标识主节点身份）、`offset`（复制偏移量，全局逻辑时钟）、`repl_backlog`（环形复制积压缓冲）。
- **易错口径**：全量同步不是「主节点把内存直接拷给从节点」，而是 fork + 生成 RDB + 网络传输 + 从节点载入，且期间新写会补发；「从节点清空旧数据」发生在载入 RDB 之前，是切换主时的风险点。

---

## ② 部分同步 repl_backlog、offset 与心跳 REPLCONF ACK

（中立陈述）主从建立连接后进入命令传播阶段：主节点每执行一条写命令，就把命令与新的 `offset` 追加进 `repl_backlog` 并发送给从节点；从节点执行后推进自己的 `offset`，并周期性发 `REPLCONF ACK <offset>` 心跳告知主节点自己的进度（默认每秒）。主节点据此判断从节点是否落后、是否在「min-replicas」保护范围内。当从节点短暂断线重连，只要断线期间产生的写仍在 `repl_backlog` 窗口内，就能 `PSYNC` 部分同步，只补缺失区间。见 `examples/ex02_partial_repl_backlog.json`、`ex03_replconf_ack_offset.json`。

### 🧑‍💻 程序员视角
- **断线重连别怕**：配置合理的 `repl-backlog-size`（如 64MB~1GB，视写入速率与可容忍断线时长而定）能让几秒~几分钟的从节点抖动走「部分同步」，避免每次重连都来一次全量同步把主节点拖垮。
- **`REPLCONF ACK` 的真实用途**：它不只是心跳——主节点用从节点上报的 offset 计算 `lag`（`info replication` 的 `lag` 字段），也是 `min-replicas-to-write` / `min-replicas-max-lag` 判断是否允许写入的依据。
- **lag 突增的告警**：`lag` 持续 >1（秒）说明从节点网络/负载异常，读写分离读到的数据陈旧度在变大，应把该从节点摘出读池。
- **backlog 太小会退化全量**：高写入 + 长断线时，backlog 被环形覆盖，offset 滑出窗口，重连只能全量——这是「从节点重启后主节点 CPU/IO 飙升」的常见根因。

### 🎓 博士生视角
- **offset 作为逻辑时钟的严谨性**：主从各自维护 `master_repl_offset` / `slave_repl_offset`，二者之差即「未确认复制数据量」；`REPLCONF ACK` 把从节点进度回传，使主节点能构造「已复制到 N 个从节点」的安全性判断。
- **backlog 的环形覆盖模型**：设 backlog 大小为 B、总写入累积量为 W、从节点落后量为 D，则部分同步可行的充要条件是 `D <= B` 且从节点断线前最后的 offset 仍在 backlog 存活区间；一旦 `W - last_ack_offset > B` 即被覆盖，必须全量。
- **ACK 与 TCP 心跳的区别**：`REPLCONF ACK` 是应用层、携带精确 offset 的语义心跳，与 TCP keepalive 解耦——即便 TCP 连接未断，offset 长期不前进也能被识别为「逻辑卡死」。

### 📚 考研者视角（笔面考点）
- **标准问法**：「什么是部分同步？repl_backlog 起什么作用？」答：从节点短暂断线重连时，若断线期间写命令仍在主节点 `repl_backlog` 环形缓冲中（offset 未滑出窗口），主节点回 `CONTINUE` 并只补发缺失区间，无需全量；backlog 大小决定了可容忍的断线时长/写入量。
- **常考辨析**：`offset` 是全局单调递增的逻辑复制进度，不是字节绝对地址；`REPLCONF ACK` 周期（1s）上报 offset，用于计算 `lag` 与 min-replicas 保护。
- **易错口径**：部分同步「不是」默认永远可用——backlog 是固定大小环形缓冲，写入过快或断线过久导致 offset 被覆盖，就会退化成全量同步；backlog 调大能延长可容忍窗口。
