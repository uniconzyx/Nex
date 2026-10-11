# 资源限制与 OOM、配置外置、K8s 演进与故障排查

> 本节目标：收尾四个「上生产才会遇到」的问题——容器为什么会被杀、配置该放哪、
> 本地 compose 怎么演进到 K8s、出事了按什么顺序查。
> 每个主题按 🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者 三视角解析。

---

## 一、资源限制与 OOM：`mem_limit`/`cpus` 与退出码 137

compose 用 `mem_limit`（或新版 `deploy.resources.limits.memory`）与 `cpus` 限制容器用量，
底层仍是 cgroup（见 tool-ch05）：`memory.max` 是**硬上限**，
超出即触发内核 OOM killer，容器表现为**退出码 137**（`128 + SIGKILL 9`）。

examples/ex05 实测的判据：峰值 > 可用额度 → OOMKilled（137）；
峰值等于上限不触发；显式配置 swap 后可用额度 = `mem_limit + swap`。
另有一类**高频但不是 OOM 的问题**：应用没感知 cgroup——JVM 按**宿主内存**的 1/4 算最大堆
（16GiB 宿主 → 4GiB 堆），而容器只有 512MiB，于是**启动即被杀**。

### 🧑‍💻 程序员视角

- **排查 OOM 的固定顺序**：
  ① `docker inspect` 看 `State.OOMKilled` 字段；
  ② `docker stats` 看实际用量曲线；
  ③ 宿主 `dmesg | grep -i oom-kill` 看内核记录；
  ④ 若 `OOMKilled=false` 却退出 137，多半是外部 `kill -9` 或宿主自身 OOM。
- **应用必须感知 cgroup**：JVM 用 `UseContainerSupport` + `MaxRAMPercentage`（JDK 10+ 默认开启）；
  Node 用 `--max-old-space-size`；Go 用 `GOMEMLIMIT`。**不要只设 `mem_limit` 就完事**。
- **limit 与 request 要分开想（K8s 口径）**：`request` 是调度依据（保证能拿到），
  `limit` 是硬上限（超了就被杀）。CPU 超限是**节流**（变慢，不退出），
  内存超限是**杀死**（直接 137）——这是两者最关键的区别。
- **留余量**：堆 + 元空间 + 线程栈 + 直接内存 + page cache 都要算进去，
  通常 `limit` 要比「堆上限」大 25%~50%；否则会遇到「堆没满但容器被杀」。
- **压测而非拍脑袋**：上限值应来自压测得到的峰值 × 安全系数，
  而不是「先给 512MiB 试试」。上线后要盯着 P99 内存用量做回归。

### 🎓 博士生视角

- **为什么内存超限必须是「杀」而不是「拒绝分配」**：
  `malloc` 在 Linux 上默认走 **overcommit**——分配虚拟内存几乎总是成功，
  真正的物理页在**首次访问触发缺页**时才分配。因此内核在内存耗尽时
  **无法**通过「让某次分配失败」来止损（那次分配早就成功了），
  只能选择一个进程杀掉来回收页。这就是 OOM killer 存在的**第一性理由**。
- **OOM killer 的选择机制**：内核为每个进程算一个
  `oom_score`（主要正比于**已用内存占可用内存的比例**，`oom_score_adj` 可人工干预），
  挑最高分的杀。容器里 PID 1 通常是最大的那个，所以表现为「整个容器没了」而不是
  「某个线程没了」。
- **cgroup v2 的改进**：v2 引入 `memory.low`（尽力保证）、`memory.high`（温和限流 + 回收）、
  `memory.max`（硬上限并被 OOM killer 兜底）三档，
  并暴露 `memory.events` 里的 `oom_kill` 计数——把「曾经被杀过」变成**可观测事件**，
  而不必去翻 `dmesg`。
- **CPU 与内存的本质差别**：CPU 是**可压缩资源**（compressible）——
  拿不到就等一等，进程还在；内存是**不可压缩资源**（incompressible）——
  已经占用的页不能凭空收回（匿名页只能换出或杀进程）。
  这是「CPU 节流、内存杀死」这一不对称行为的总根源。

### 📚 考研者视角

> 非 408 学科，按「笔试/面试考点」口径写；与 408 的联系点非常直接。

- **考点归属**：**408 操作系统的内存管理**——
  虚拟内存、请求分页、页面置换、**抖动（thrashing）**、以及
  **分配 vs 首次访问**的差别。容器 OOM 就是这些考点的工程映射。
- **标准问法与答案**：
  - 「容器退出码 137 是什么意思？」——**`128 + 9`，即被 SIGKILL 杀死，
    最常见的原因是 OOMKilled（内存超过 cgroup 上限）**。
  - 「为什么设了 `mem_limit` 应用还是被杀？」——**应用没感知 cgroup，
    按宿主内存算堆/缓存**，上限远大于容器可用额度。
  - 「CPU 超限会怎样？」——**被 CFS 节流（变慢），不会退出**；
    这与内存超限被杀形成对比。
- **易混对比**：
  `request`（调度保证）vs `limit`（硬上限）；
  CPU 节流 vs 内存 OOM；
  `OOMKilled=true`（cgroup 触发）vs 退出 137 但 `OOMKilled=false`（外部 kill）。
- **与「抖动」的联系**：若把 `mem_limit` 设得过小、应用频繁触及上限并大量换页，
  就复现了 408 里 **thrashing**（刚换出的页马上又要换入，
  系统时间全花在页面置换上）——这也是「不要过度压缩内存上限」的理论依据。

---

## 二、配置外置（12-Factor）与密钥管理

12-Factor App 给出云原生应用的一组约定，与容器化直接相关的几条：

- **I 基准代码**：一份代码库，多份部署；
- **II 依赖**：显式声明依赖清单（`requirements.txt` / `package.json`），不依赖宿主预装；
- **III 配置**：**配置存于环境变量 / 配置服务**，绝不硬编码进代码或镜像；
- **VI 进程**：应用是**无状态**进程，session 与上传不能落在容器本地；
- **VII 端口绑定**：端口由外部注入，应用不假设自己监听哪个固定端口；
- **XI 日志**：日志当作**事件流**写 stdout，由平台采集。

examples/ex09 实测：把 `DB_HOST` 写进 `ENV`、把密码写进 `ARG`、
`COPY .env` 进镜像、日志写文件、session 落本地、端口硬编码——
六条全踩的组合规率为 0.0%；全部外置的正例为 100.0%。

### 🧑‍💻 程序员视角

- **「配置」的判定标准**：**随部署环境变化的值**就是配置
  （数据库地址、端口、超时、特性开关、外部域名）。
  不随环境变化的（如 `LANG`、`PYTHONUNBUFFERED`）留在镜像里没问题。
- **密钥的三个层次**：
  ① 开发期用 `.env`（**必须进 `.gitignore`**，只提交 `.env.example`）；
  ② 运行时用 compose `secrets` / K8s `Secret` / 环境变量注入；
  ③ 生产用 Vault / 云厂商 KMS，**支持轮换**。
- **绝不进镜像**：`ENV`/`ARG`/`COPY` 的内容会**永久留在镜像层**，
  任何人 `docker pull` 后 `docker history` 都能看到；`RUN rm` 只是 whiteout，删不掉。
- **无状态是水平扩展的前提**：session 写本地文件的服务一扩容就丢登录态；
  要么外置到 Redis，要么用 JWT。**上传文件必须挂卷或走对象存储**。
- **一次构建多处部署**：同一个镜像在 dev/staging/prod 只靠**环境变量**区分，
  这样 prod 跑的就是 staging 验证过的那一份二进制——这是容器化最大的收益之一。

### 🎓 博士生视角

- **为什么要「一次构建多处部署」**：构建是一个**高维度、难复现**的过程
  （编译器版本、依赖树快照、时间、随机种子）。若每个环境各构建一次，
  `staging` 与 `prod` 跑的就是**两个不同的制品**，staging 的验证结论对 prod 无效。
  把配置外置，使制品成为**环境无关的函数** `artifact(config) → 行为`，
  才能让「验证过的东西被部署」这一推断成立。
- **配置的本质是「晚绑定」**：编译期常量是**早绑定**，环境变量是**运行期绑定**。
  12-Factor III 主张把绑定时机尽量推迟，**缩小需要重新构建的维度**，
  这与软件工程里「依赖注入 / 控制反转」是同一思想在系统边界上的应用。
- **为什么 Secret 与 ConfigMap 要分开**：二者的**安全属性**不同——
  ConfigMap 只需完整性，Secret 还需**机密性与访问控制**（etcd 静态加密、
  RBAC 单独授权、禁止打进日志）。把密钥塞进 ConfigMap 等于放弃了
  这一整套控制面，是一次**抽象层次的错误**。
- **轮换能力是被设计出来的**：只要密钥进了镜像层，轮换就必须**重建 + 全量重新部署**；
  运行时注入的密钥可以做到**改一次、滚动生效**。
  这决定了泄漏事件的响应时间从「小时级」变成「分钟级」。

### 📚 考研者视角

> 非 408 学科，按「笔试/面试考点」口径写；与 408 的联系点已标注。

- **标准问法与答案**：
  - 「什么是 12-Factor 的『配置外置』？」——**配置存于环境变量/配置服务，
    不硬编码进代码或镜像；同一份制品靠不同配置部署到多个环境**。
  - 「密钥能写进 Dockerfile 的 `ENV` 吗？」——**不能**。
    内容会永久留在镜像层，`docker history` 可见，且轮换需要重建镜像。
  - 「为什么要『一次构建多处部署』？」——**保证 prod 跑的就是 staging 验证过的制品**。
- **易混对比**：
  `.env`（开发期、不进 git）vs `environment`（compose 内联）vs
  `secrets`（文件挂载、不进环境变量）vs 外部密钥服务（可轮换、可审计）；
  ConfigMap（非敏感）vs Secret（敏感、需加密与 RBAC）。
- **与 408 的联系**：「无状态进程 + 外置状态」对应
  **操作系统里进程与资源分离**的思想；「一次构建多处部署」对应
  **计组中指令与数据分离、地址重定位**（同一段代码可被加载到不同地址运行）。
- **记忆口诀**：**「配置进环境、密钥进 Secret、日志进 stdout、状态进外部存储」**。

---

## 三、从 compose 到 K8s：概念映射与演进路径

compose 解决的是**单机多容器**，K8s 解决的是**多机编排**。
概念上有清晰的一一对应（examples/ex11 实测生成 19 个对象）：

| compose | Kubernetes | 说明 |
|---|---|---|
| `service`（无状态） | `Deployment` + `Service` | 由控制器保证副本数 |
| `service`（有状态 + 命名卷） | `StatefulSet` + `Service(headless)` + `PVC` | 稳定网络标识与存储 |
| `depends_on` | **无直接等价物** | K8s 不保证启动顺序，靠 `initContainer`/readiness 门控 |
| `healthcheck` | `livenessProbe` + `readinessProbe` + `startupProbe` | 语义被拆细了 |
| `restart: always` | `restartPolicy: Always`（由控制器重建 Pod） | 是**重建**不是原地重启 |
| 命名卷 | `PersistentVolumeClaim` | 与 Pod 生命周期解耦 |
| bind mount | `hostPath`（不推荐）/ ConfigMap 挂载 | 破坏可移植性 |
| `environment`（非敏感） | `ConfigMap` | |
| `environment`（敏感） | `Secret` | |
| `ports` | `Service(NodePort/LoadBalancer)` + `Ingress` | |
| `mem_limit` / `cpus` | `resources.limits` / `resources.requests` | |

演进路径建议：**先让应用满足 12-Factor → 用 compose 跑通单机 →
把 compose 翻译成 K8s 清单（可用 `kompose` 起个草稿，但**必须人工重写**）→
补齐探针与资源限制 → 接 CI/CD 与监控**。

### 🧑‍💻 程序员视角

- **不要直接 `kompose convert` 就上线**：自动转换出来的清单缺少
  `readinessProbe`、`resources.requests`、滚动更新策略与 PDB，
  而且会把 `depends_on` 悄悄丢掉。**转换结果只能当草稿**。
- **K8s 没有 `depends_on`，这是最大的认知落差**：K8s 假设
  **所有依赖都可能随时不可用**，因此要求应用自己能重试。
  必须补 `initContainer`（等 db 端口）或 `readinessProbe` 门控。
- **Pod 是调度单位、不是容器**：一个 Pod 里可以有多个容器，
  共享网络与 UTS namespace（所以它们之间**可以**用 localhost 通信），
  这对应 compose 里「紧密耦合的一组进程」（如应用 + sidecar 日志采集）。
- **Deployment 管的是「期望副本数」**：删除一个 Pod 会自动补一个，
  所以**不要手动 `kubectl run` 跑生产负载**，一切走控制器。
- **先补可观测性再迁移**：没有探针、没有资源限制、没有日志采集就迁 K8s，
  只会把「单机故障」升级成「分布式故障」。

### 🎓 博士生视角

- **根本差别是「控制循环」**：compose 是**一次性命令式执行**
  （`up` 时按拓扑序创建，之后基本不管）；
  K8s 是**声明式 + 持续调和（reconciliation loop）**——
  控制器不断比较「期望状态」与「实际状态」并驱动后者趋近前者。
  这使系统具备**自愈**能力（节点宕机后自动在其他节点重建），
  代价是引入了**最终一致性**：状态变更不是瞬时的。
- **为什么 K8s 不提供 `depends_on`**：在分布式环境下，依赖的可用性是
  **动态属性**而非启动期的一次性条件。提供「启动顺序」会给人一种
  「依赖已就绪」的错误保证。K8s 的做法是把就绪性建模成
  **持续观测的端点**（readiness），由 Service 动态地把未就绪的 Pod 摘掉——
  这是把静态的顺序约束换成了动态的反馈控制。
- **调度问题**：K8s 的调度是**多维装箱问题**（CPU/内存/GPU/亲和性/污点容忍），
  属于 NP-Hard，实践中用**过滤 + 打分**的两阶段启发式；
  `requests` 是调度器的输入，`limits` 是运行时的 cgroup 边界——
  二者分工明确，这也是 compose 里单一 `mem_limit` 所缺失的层次。
- **不可变基础设施的终局**：Pod 被视为**可随时被替换的牲畜**而不是宠物，
  因此一切本地状态都是反模式；这与 12-Factor 的「无状态进程」是同一原则的
  强制度量——K8s 用「随时可能重建 Pod」把这条原则变成了**硬约束**。

### 📚 考研者视角

> 非 408 学科，按「笔试/面试考点」口径写；与 408 的联系点已标注。

- **标准问法与答案**：
  - 「compose 的 service 对应 K8s 的什么？」——**无状态 → Deployment + Service；
    有状态带卷 → StatefulSet + headless Service + PVC**。
  - 「K8s 里有 `depends_on` 吗？」——**没有**。K8s 不保证启动顺序，
    靠 `initContainer` 或 readiness 门控，应用本身也要能重试。
  - 「Pod 和容器是什么关系？」——**Pod 是调度的最小单位，可含多个容器，
    它们共享网络与 UTS namespace（可用 localhost 互通）**。
- **易混对比**：
  `livenessProbe`（失败重启）vs `readinessProbe`（失败摘流量）vs `startupProbe`（慢启动保护）；
  `requests`（调度依据）vs `limits`（运行时硬上限）；
  Deployment（无状态）vs StatefulSet（有状态、稳定标识）vs DaemonSet（每节点一个）。
- **与 408 的联系**：控制器的调和循环对应
  **操作系统里「进程状态机 + 调度器」**的思想；多维装箱调度对应
  **操作系统内存分配（首次适应/最佳适应）**与**计组中 Cache 替换策略**的同类启发式问题。
- **记忆口径**：**「compose 管单机、K8s 管集群；compose 是命令式、K8s 是声明式调和」**。

---

## 四、常见故障排查：症状 → 根因 → 处置

把高频故障整理成可判定的规则（examples/ex13 实测规则库判定）：

| 症状 | 根因 | 处置 |
|---|---|---|
| `port is already allocated` / `address already in use` | 宿主端口被别的容器或进程占用 | `ss -lntp` 查占用者；改宿主侧端口 |
| `permission denied`（写卷时） | bind mount 的宿主目录属主与容器 uid 不一致 | `chown` 到镜像 `USER` 的 uid；或改用命名卷 |
| `connection refused` | 端口没发布 / 服务没监听 / 不在同一网络 | 先容器内自证端口；核对 `ports`；加入同一 network |
| `no such host` / `name resolution failure` | 用了 `localhost` 或默认 bridge（无内嵌 DNS） | 容器间一律用服务名；显式声明自定义网络 |
| 时间差 8 小时 | 容器是 UTC，未设 `TZ` | `ENV TZ=Asia/Shanghai`；挂 `/etc/localtime`；装 tzdata |
| 中文乱码 / `UnicodeEncodeError` | 容器 locale 是 POSIX/C，默认 ASCII | `ENV LANG=C.UTF-8 LC_ALL=C.UTF-8`；代码显式 `encoding='utf-8'` |

### 🧑‍💻 程序员视角

- **固定排查顺序**：容器是否活着 → 退出码（137/143/139）→
  `docker logs` → 进容器自证（`curl localhost:<port>`）→ 再查宿主端口与网络。
  **先自证再怀疑别人**，能省掉一半时间。
- **`docker compose config` 是排查配置问题的第一利器**：
  它输出插值、合并后的最终配置，变量取了哪个值、端口映射成什么样一目了然。
- **「能 ping 通但连不上」** 与 **「连不上且 ping 不通」** 是两类问题：
  前者是端口/应用问题，后者是网络/DNS 问题。
- **时区与编码属于「本地能跑线上不行」的重灾区**：
  本地开发机的 `TZ` 与 `LANG` 常常是设好的，容器里是空的。
  这两个必须显式写进镜像或 compose。
- **留证据**：故障现场先 `docker inspect` / `docker logs --tail 500` 存下来再重启，
  重启之后状态机就清空了。

### 🎓 博士生视角

- **排查的本质是「二分定位」**：沿着请求路径
  `客户端 → 宿主端口 → DNAT → 容器网络 → 容器内进程 → 应用逻辑 → 依赖服务`
  从外到内逐段验证，每一段用一个**可证伪的判据**（端口通不通、DNS 解不解得开、
  应用端口自证成不成功）。这本质上是**故障树分析（FTA）**的思想：
  用最少的观测把故障空间对半切分。
- **为什么「容器里访问 localhost」必然失败**：`localhost` 解析到
  `127.0.0.1`，而 loopback 设备属于**各自的 net namespace**（见 concept/01）。
  这类 bug 的共性在于：**名字的含义依赖于所处的命名空间**
  ——同样的 `localhost` 在宿主和容器里指向不同的实体。
- **编码问题的根源是「默认值不一致」**：POSIX locale 下 C 库按 ASCII 处理，
  Python3 的 `open()` 默认编码来自 `locale.getpreferredencoding()`。
  这类问题的通解是**在边界处显式指定编码**，而不是依赖环境默认值——
  与「显式优于隐式」的一般工程原则一致。
- **时区问题的本质是「UTC 是唯一无歧义的存储格式」**：
  正确的做法是**内部一律 UTC、只在展示层转本地时区**，
  而不是把 `TZ` 到处塞；日志用 ISO-8601 带时区偏移，才能跨机对齐。

### 📚 考研者视角

> 非 408 学科，按「笔试/面试考点」口径写；与 408 的联系点已标注。

- **标准问法与答案**：
  - 「端口被占用怎么排查？」——**`ss -lntp`（或 `netstat`）查占用者，
    改宿主侧端口映射；注意是宿主端口在前**。
  - 「容器写卷报 Permission denied 怎么解决？」——**bind mount 的属主与容器 uid 不一致；
    `chown` 到镜像 `USER` 的 uid，或改用命名卷让 docker 初始化属主**。
  - 「容器间 `no such host` 是什么原因？」——**用了 `localhost` 或默认 bridge 网络；
    应改用服务名，并把服务放进同一个自定义网络**。
- **易混对比**：
  `connection refused`（端口没人监听）vs `no route to host`（网络/防火墙）vs
  `no such host`（DNS 解析失败）——**三者分别对应传输层、网络层、应用层（DNS）**，
  是分层定位的典型练习。
- **与 408 的联系**：这套症状—层次的对应正是
  **计算机网络分层模型（408 网络必考）**的实际运用：
  DNS 属应用层、TCP 连接属传输层、路由可达属网络层、ARP/网桥属链路层。
- **记忆口诀**：**「先活着、再看码、再看日志、自证端口、最后查网络」**。

---

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | OOM 看 137 + `OOMKilled` 字段，应用要感知 cgroup；配置进环境、密钥进 Secret；迁 K8s 必须补探针与资源限制 |
| 博士生 | 内存不可压缩故超限即杀、CPU 可压缩故只节流；外置配置把制品变成环境无关函数；声明式调和取代一次性编排 |
| 考研者 | 退出码 137、CPU 节流 vs 内存 OOM、12-Factor 配置外置、compose↔K8s 映射是标准问答口径；分层定位对应网络分层考点 |
