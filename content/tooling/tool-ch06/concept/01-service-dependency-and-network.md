# 服务定义、依赖顺序与网络

> 本节目标：把 compose 的 `services` 段还原成一张**有向图**，并说清「启动顺序」与「真正可用」之间的鸿沟。
> 每个主题按 🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者 三视角解析。

---

## 一、服务定义与依赖顺序：`depends_on` 只保证启动顺序，不保证就绪

compose 文件的 `services` 段是一组**声明式期望状态**：每个服务给出镜像、端口、卷、环境变量、
依赖。编排器在 `up` 时把「谁依赖谁」抽成一张有向图，再决定启动顺序。

`depends_on` 有两种写法：

- **短语法**（列表）：`depends_on: [db, redis]`，等价于每条依赖都是 `condition: service_started`；
- **长语法**（映射）：
  `depends_on: { db: { condition: service_healthy } }`，可指定三种条件之一
  ——`service_started`（容器已启动）、`service_healthy`（健康检查通过）、
  `service_completed_successfully`（依赖是一次性任务且成功退出）。

形式化地看：服务集合 `S`、依赖边 `E ⊆ S×S` 构成有向图 `G=(S,E)`。
**可编排 ⟺ G 是无环有向图（DAG）**；用 Kahn 算法按入度分层，
同一层的服务互不依赖、可并行启动，层数就是启动过程的关键路径长度。
examples/ex01 实测：4 服务的 DAG 排出 3 个批次（`[db, redis] → [api] → [web]`）；
而三节点环 `web → api → cache → web` 与自环 `worker → worker` 都排不出拓扑序。

### 🧑‍💻 程序员视角

- **典型事故**：`docker compose up` 一切正常，但首页 500，api 日志第一行就是
  `connection refused to db`。根因是短语法 `depends_on` 只等到 db **容器进程存在**，
  而此时 db 还在 initdb、跑迁移，根本不接受连接。
- **正确写法是三段式**，缺一段都不行：
  ① db 自己要有 `healthcheck`（PostgreSQL 用 `pg_isready`）；
  ② api 写 `depends_on: {db: {condition: service_healthy}}`；
  ③ api 自己也要有 `healthcheck`，供 web 依赖。
- **编排层之外还要有应用侧重试**：`service_healthy` 只保证**启动那一刻**就绪，
  运行期 db 重启、网络抖动仍会发生；客户端必须有连接重试 + 指数退避 + 抖动。
- **循环依赖不要靠 `restart: always` 掩盖**：A 依赖 B、B 又依赖 A，通常说明
  两个服务的职责切错了——要么抽出第三个服务，要么改成消息队列异步解耦。
- **排查顺序**：先看启动批次是否符合预期 → 再看各服务 healthcheck 状态 →
  再看应用日志里「首次连接失败」的时间戳是否早于依赖的 ready 时刻。

### 🎓 博士生视角

- **为什么「启动」推不出「可用」**：`service_started` 是一个**进程创建事件**
  （PID 1 已经 exec），而「就绪」是一个**应用状态谓词**（监听 socket 已 bind 且能响应业务探测）。
  两者之间隔着一个**不可静态界定的初始化过程** `T_init`：
  它与数据量、迁移条数、冷缓存预热有关，可能 0.2 秒也可能 5 分钟。
  因此编排器无法用「顺序」表达「等待条件」，只能把就绪性提升为**可观测谓词**（healthcheck）。
- **拓扑排序的语义**：Kahn 算法按入度为 0 分层，本质是求 AOV 网的一个拓扑序列；
  序列不唯一（同层内顺序任意），但**层数**（关键路径长度）是唯一的，
  也就是「最快也要多少批才能全部起来」的理论下界。
- **复杂度**：建图 O(|S|+|E|)，Kahn O(|S|+|E|)；环检测不需要额外算法——
  拓扑排序结束后**入度仍 > 0 的节点**就是全部环上（或环可达）的节点。
- **设计动机**：Compose 选择「声明期望状态 + 编排器求序」而不是让用户写启动脚本，
  是**声明式 vs 命令式**的经典取舍：声明式可静态分析、可幂等重放、可 diff；
  代价是**表达不了时序逻辑**（「等到某条件再继续」），只能靠 healthcheck 这个外挂谓词补上。
  Kubernetes 干脆不提供 `depends_on` 的等价物，把这件事完全交给 readiness 门控。

### 📚 考研者视角

> Docker/Compose 不在 408 考纲内，但它**直接落在 408 数据结构**的一个标准考点上，
> 笔试与面试常拿它做工程实例。以下按「笔试/面试考点」口径写。

- **考点归属**：**有向无环图与拓扑排序（AOV 网）**、**关键路径**。
  把服务看成顶点、依赖看成有向边，compose 的依赖分析就是这个模型的直接映射。
- **标准问法与答案**：
  - 「`depends_on` 能保证数据库就绪吗？」——**不能**。它只保证**启动顺序**；
    要保证就绪必须写 `condition: service_healthy`，且被依赖方必须自己配 `healthcheck`。
  - 「compose 里出现循环依赖会怎样？」——**无法确定启动顺序，编排器无法编排**，
    必须在设计阶段拆掉环（抽服务 / 改异步）。
- **易混对比**：
  `depends_on`（启动顺序）≠ `healthcheck`（就绪谓词）；
  `depends_on` ≠ `links`（网络别名机制，已废弃）；
  `restart: always` 是**事后重启**，不能替代**事前等待**。
- **若考 AOV 网计算题**：拓扑序列可以不唯一，但拓扑排序的**层数**是确定的；
  判断是否有环的两种标准方法——DFS 的回边检测、或 Kahn 排序后剩余节点非空。

---

## 二、网络：自定义 bridge、服务名即 DNS、暴露 vs 发布

compose 为每个 project 默认创建一个 `<project>_default` 的**自定义 bridge 网络**，
并把该 project 下的所有服务都接进去。在这个网络里：

- **服务名就是 DNS 名**：api 访问 db 写 `db:5432` 即可，无需知道 IP；
  `scale` 出多副本时，DNS 会返回多个 A 记录（round-robin）。
- **`expose` 只是元数据**：它写进镜像/容器元信息，表达「我监听这个端口」，
  **不做任何映射**；宿主访问不到。
- **`ports` 才是真正的发布**：`宿主端口:容器端口`，在宿主 iptables 的 nat 表里
  加一条 DNAT 规则。注意**宿主端口在前**。
- 解析由 Docker 的**内嵌 DNS**（容器内的 `127.0.0.11:53`）完成；
  默认的 `docker0` bridge 没有这个 resolver，这也是必须用自定义网络的原因。

examples/ex10 实测：同一宿主端口被两个服务同时发布会被判为冲突；
只写容器端口（`ports: ["5432"]`）不构成冲突；同一端口绑不同宿主 IP 也不冲突。

### 🧑‍💻 程序员视角

- **最常见的新手错误**：在 api 里写 `localhost:5432` 去连同 compose 里的 db。
  容器里的 `localhost` 是**它自己的** loopback，永远连不到 db。一律写服务名。
- **最小暴露面原则**：db / redis 这类中间件**不要**发布到宿主（只写 `expose` 或不写），
  只有入口网关需要 `ports`。这既减少攻击面，也避免宿主端口冲突。
- **端口冲突的报错识别**：
  `Bind for 0.0.0.0:80 failed: port is already allocated` ——改宿主侧端口（`8081:8080`），
  或用 `ss -lntp` 找出是谁占了。
- **`container_name` 慎用**：它也能被 DNS 解析，但写死后就无法 `scale` 多副本了
  （名字冲突）；让 compose 自动生成名字。
- **跨 project 互通**：两个 compose project 默认在不同网络里，需要显式声明
  同一个 `external: true` 的网络并把两边都接进去。

### 🎓 博士生视角

- **底层机制**：自定义 bridge = Linux bridge 设备 + 一组 **veth pair**
  （一端放进容器 netns 成为 eth0，另一端挂到 bridge）+ iptables nat 表的
  DNAT/SNAT 规则。`ports` 的本质就是**加一条 DNAT**；`expose` 不加任何规则，
  这也是「写了 EXPOSE 却连不上」的根因。
- **内嵌 DNS 是自定义 bridge 与默认 bridge 的分水岭**：Docker 在容器里把
  `/etc/resolv.conf` 指向 `127.0.0.11`，由守护进程的嵌入式 resolver 按
  **容器名 / 服务名 / 网络别名**应答，并支持同一服务多副本的多 A 记录。
  默认 `docker0` 网桥没有它，历史上只能靠 `--link` 写 `/etc/hosts`（已废弃）。
- **命名空间视角**：每个容器有独立的 net namespace，因此 `127.0.0.1` 是**各自的**
  loopback、端口空间也完全独立——两个容器可以同时监听 8080 而不冲突，
  冲突只发生在**把它们都发布到宿主同一个端口**时。
- **演进**：跨主机场景用 **overlay 网络**，把二层帧用 VXLAN 封装进 UDP 跨机打通。
  这是 Swarm 与 K8s CNI 插件（Flannel/Calico）的共同思想；
  理解 bridge + veth + DNAT，是理解所有 CNI 的前置。

### 📚 考研者视角

- **考点归属**：**计算机网络的局域网与网络层**（408 网络考点：网桥/交换机、
  NAT、DNS、私有地址与端口）。容器网络是这些考点的现成实例，面试常拿它举例。
- **标准问法与答案**：
  - 「容器之间怎么互相访问？」——**用服务名（DNS 解析）**，
    前提是它们在同一个自定义网络中；不能用 `localhost`。
  - 「Dockerfile 里写了 `EXPOSE 8080`，宿主为什么访问不到？」——
    **EXPOSE 只是文档性元数据**，真正发布要 `ports`（`-p`）。
- **易混对比**：
  `expose`（元数据，不映射）vs `ports`（DNAT，真正发布）；
  `bridge`（NAT + 端口映射，默认）vs `host`（共享宿主 netns，无隔离、性能最好）
  vs `none`（只有 loopback）；
  **宿主端口在前、容器端口在后**（`8080:80` 是宿主 8080 → 容器 80）。
- **若考 NAT**：发布端口 = DNAT（改目的地址），容器访问外网 = SNAT/MASQUERADE
  （改源地址）。两者都在 nat 表，方向相反。

---

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | `depends_on` 只排顺序，就绪靠 `service_healthy` + 应用侧重试；容器间一律用服务名 |
| 博士生 | 依赖图是 AOV 网，可编排 ⟺ 无环；started 是事件、healthy 是谓词，中间隔着不可界定的 `T_init` |
| 考研者 | 对应 408 拓扑排序/关键路径与 NAT、DNS 考点；「EXPOSE 不映射、localhost 不可达」是标准口径 |
