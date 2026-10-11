# 一、YARN 三角色与容器分配状态机

（中立陈述）YARN（Yet Another Resource Negotiator）把「资源调度」从计算框架中抽离成独立层。三类角色：**ResourceManager（RM，全局资源管理，含调度器）**、**NodeManager（NM，单节点代理，管容器生命周期）**、**ApplicationMaster（AM，每作业一个，向 RM 申请容器、在 NM 上启停任务、盯进度）**。作业提交后，RM 先为 AM 分配一个容器，AM 再循环向 RM 申请更多容器来跑 Task。

### 🧑‍💻 程序员视角
- 排障入口：`yarn application -list`、`yarn logs -applicationId <id>` 是日常；作业卡住先看 AM 日志（AM 容器通常叫 `container_eXX_000001`），再下钻到具体 task 容器。
- 资源参数：`yarn.nodemanager.resource.memory-mb / .vcores` 限定单 NM 能卖出多少；任务侧 `-Dmapreduce.map.memory.mb=2048` 要**落在 NM 资源粒度内**，超了会被 RM 拒单或 NM 因超内存被 kill（OOM Killer 直接杀容器，表现为任务「无故失败重试」）。
- 高可用：RM 必须配 HA（Active/Standby + ZooKeeper），否则 RM 单点挂了全集群没法提交新作业；生产环境 ZK 是最常见依赖。
- 容器 vs JVM：一个容器 = 一组资源（mem+core）的隔离单元，里面跑一个 JVM/进程；`yarn.nodemanager.container-executor` 决定用 default（同用户）还是 Linux 容器（cgroup 隔离，更安全）。

### 🎓 博士生视角
- 解耦价值：YARN 把「**调度（scheduling）**」与「**应用执行（application semantics）**」彻底分离——RM 只管「把资源给谁」，AM 管「拿到资源干什么」。于是 MapReduce、Spark、Flink 共用同一套资源层，对比 Mesos 的两级调度与 Kubernetes 的 pod 调度，是「中心化调度」范式的代表。
- 状态机正确性：RM 内 Application 有状态机 `NEW → NEW_SAVING → SUBMITTED → ACCEPTED → RUNNING → FINISHED/FAILED/KILLED`；Container 有 `NEW → LOCALIZING → LOCALIZED → RUNNING → COMPLETED`；状态转移由事件驱动（如 `CONTAINER_ALLOCATED`、`CONTAINER_LAUNCHED`），任意非法转移都会被 RM 拒绝——这是用「显式状态机」约束分布式并发错误的经典做法。
- 资源模型：YARN 的资源是**离散的 Container 槽位（mem, vcore）**，而非连续配额；AM 以「心跳 RPC」周期性向 RM 汇报进度并领新资源，这种「拉模型（pull/heartbeat）」比「推模型」更利于 RM 的水平扩展与失败恢复。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「YARN 的三大组件是什么？各自职责？」标准答：**RM（全局资源调度与仲裁）、NM（单节点容器管理/资源上报）、AM（每作业一个，申请资源、启停 task、容错）**。
- 易错口径：① AM 不是常驻全局服务，而是**每作业一个、随作业结束而销毁**；② 真正的「调度决策」在 RM 内的调度器，不在 AM；③ NM 不跑业务逻辑，只管容器生命周期与健康上报。
- 作业提交流程（常考顺序题）：Client 提交 → RM 收下并 `NEW_SAVING` → 分配 AM 容器（`ACCEPTED`）→ NM 启动 AM → AM 向 RM 申请 task 容器 → NM 启动 task → 完成 `FINISHED`。
- 关联考点：与「HDFS 的 NN/DN 角色划分」类比（中心元数据 vs 分布式数据），理解「管控面 / 数据面分离」这一贯穿大数据的设计哲学。

---

# 二、FIFO / Capacity / Fair 三种调度器

（中立陈述）RM 内置三种调度器：**FIFO**（单队列，先到先得，大作业独占集群）、**Capacity**（多队列、每队列保底容量、队列内 FIFO，适合多租户保 SLA）、**Fair**（多队列、动态把空闲资源整合给「最饿」的作业，追求公平共享，适合交互+批处理混跑）。三者是「吞吐量 vs 公平性 vs 隔离性」的不同取舍。

### 🧑‍💻 程序员视角
- 选型经验：纯离线批处理、一个团队 → FIFO 最简单；多部门共用集群、要保关键队列资源 → **Capacity**（给「生产队列」保底 60%、「实验队列」40%）；交互式 SQL + 批处理混跑、希望空闲时互相借资源 → **Fair**。
- Capacity 配置坑：队列「最大容量」设成 100% 才能借别人空闲资源，否则只能用自己的保底；`yarn.scheduler.capacity.root.<q>.capacity` 是「保底占比」，`maximum-capacity` 是「弹性上限」。
- Fair 配置坑：不设 `weight` 则所有队列平分；`fairSharePreemptionTimeout` 控制「等不到公平份额多久就抢占」，抢占（preemption）虽好但会杀容器，对长任务不友好，需谨慎开。
- 别混用：调度器是 RM 全局唯一配置，不能「这个队列 FIFO、那个 Fair」——要么全 Capacity 要么全 Fair（Capacity 的层级队列可模拟部分公平）。

### 🎓 博士生视角
- 调度目标的形式化：FIFO 优化**平均周转时间**下的吞吐；Capacity 优化**最坏情况隔离**（min-guarantee，类 CPU 的 CFS 带宽控制）；Fair 优化**最大化 min{各作业获得/需求}** 的max-min fairness（与网络带宽分配、VM 调度同源）。
- 抢占的代价：Fair 的 preemption 把「借出去」的资源收回给欠配额方，本质是「撤销已分配容器」——这破坏了容器的「运行不中断」假设，需要 AM 能优雅处理任务被杀（checkpoint/重算），是公平与效率的再权衡。
- 与理论关系：max-min fairness 是经典的「无嫉妒（envy-free）」资源分配解；Capacity 的层级队列则对应「层级加权公平队列（Hierarchical WFQ）」，二者都能在「用户级」与「作业级」间灵活组合。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「YARN 有哪几种调度器？区别？」标准答：**FIFO（单队列先到先得）、Capacity（多队列保底容量、队列内 FIFO、多租户隔离）、Fair（动态公平共享、空闲资源被最饿作业用、可抢占）**。
- 易错口径：① 默认调度器是 Capacity（Hadoop 2/3 起），不是 FIFO；② FIFO 没有队列隔离，一个大作业会「饿死」后面的小作业；③ Capacity 的 `capacity` 是**保底**百分比，不是上限，`maximum-capacity` 才是上限。
- 高频追问：「小作业被大作业堵住怎么办？」答：换 Fair/Capacity 让小作业能分到资源，而非 FIFO；「怎么保证某队列资源不被别人抢光？」答：Capacity 配 `capacity` 保底 + `maximum-capacity` 限制借用。
- 关联考点：与「操作系统调度（CFS/公平调度）」「网络公平队列」横向对比，体现「公平分配」是跨层通用命题。
