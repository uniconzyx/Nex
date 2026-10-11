# fs-ch08 · 三、Docker Compose 编排与 12-Factor 配置

## 一、Docker Compose：服务依赖、网络、卷与健康检查

`compose.yaml` 用一份声明描述多容器应用：`services`（各容器）、`networks`（自定义网络，服务名即 DNS 名）、`volumes`（具名卷，生命周期独立于容器）、`env_file`/`environment`（配置注入）。

```yaml
services:
  db:
    image: postgres:16.4
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes: [pgdata:/var/lib/postgresql/data]
  api:
    build: .
    depends_on:
      db:
        condition: service_healthy      # 关键：等 db 真的就绪，而不是「已启动」
    ports: ["3000:3000"]
volumes:
  pgdata:
```

`depends_on` 的语义有两档：短语法（列表）只保证**启动顺序**；长语法带 `condition` 才提供**就绪门**（`service_started` / `service_healthy` / `service_completed_successfully`）。本章 ex07 用拓扑排序求解分层启动顺序，并检出循环依赖：

```
=== compose(good) services=5 ===
wave0=cache,db
wave1=api,worker
wave2=gateway
total_waves=3
start_order=cache,db,api,worker,gateway
=== compose(cyclic) services=3 ===
error=circular_dependency:a,b,c
```

### 🧑‍💻 程序员视角
- **只用 `depends_on` 而不写 healthcheck 是最常见的坑**：api 会在 db 还在初始化（postgres 首次启动要建库、加载脚本）时就开始连接，连接失败即退出；重启后 db 已就绪于是「自愈」，故障偶发难复现。正确做法是给 db 配 `healthcheck` 并把 condition 设为 `service_healthy`。
- 最坏等待时间要算：`interval × retries + timeout`，再对照 api 自身的启动超时；否则会把「等依赖」误判成「服务挂了」。
- 卷的取舍：**具名卷**用于数据库等需要持久化的数据（由 Docker 管理，性能好、可迁移）；**bind mount** 用于开发时挂源码（改动即时生效）与配置注入，但会把宿主的 uid/gid 权限语义带进容器，出现「容器内写不了」的问题。
- 定位说明：Compose 面向**单机**（开发、CI、小规模部署）；多机编排、跨节点调度、滚动更新与自愈属于 K8s 一类编排器的职责。不要在 Compose 上硬造生产级编排。

### 🎓 博士生视角
- 启动顺序问题的形式化：`depends_on` 定义了一个有向图，要求输出其**拓扑序**；当且仅当图中无环时拓扑序存在。因此「循环依赖」不是配置瑕疵而是**无解**——Compose 必须报错而不能死等。ex07 的 `circular_dependency:a,b,c` 正是这个判定。
- 分层的意义是**可并行性的显式化**：同一 wave 内的服务可以并发启动（ex07 的 `wave0=cache,db`），层数即最短启动批次 = 最长依赖链长度。这与 CI 流水线的 makespan 分析（ex06）是同一套图论工具。
- 健康探针把「就绪」从**时间假设**改成了**状态观测**：`service_healthy` 的语义是「探针连续成功」，本质是一个状态机收敛过程；因此它是最终一致而非即时的，最坏检测延迟约等于 `interval × retries`。
- 卷的生命周期与容器解耦，这一点在语义上把「数据」与「计算」分离：容器可任意替换/重建，数据留在卷里。这也是「不可变基础设施」得以成立的前提之一——销毁重建不丢数据。

### 📚 考研者视角
- **408 数据结构考点（本章最直接的连接点）**：**有向无环图（DAG）、AOV 网、拓扑排序**（Kahn 入度法与 DFS 逆后序法）、**环检测**；以及 **AOE 网与关键路径**（`ve`/`vl`、`e(i)=l(i)` 的关键活动判定）。ex07 的启动顺序与 ex06 的流水线调度就是这两类题的现实形态。
- **常考口径**：Kahn 算法「每次取入度为 0 的顶点并删除其出边」，能生成的顶点数少于顶点总数 ⇒ 存在环（ex07 与 ex05 的环检测都基于这条判据）。
- **易混点**：拓扑序**不唯一**（除非图退化为链）；因此实现里必须显式定义打破平局的规则（本章示例统一取字典序最小者）才能得到确定性输出——这也是「同一份配置两次启动顺序不同」的根本原因。
- **面试考点**：Compose 与 K8s 的区别、`depends_on` 能否保证依赖就绪（不能，需要 healthcheck）。

## 二、12-Factor 与配置外置

The Twelve-Factor App 的核心主张之一：**配置是「会因部署环境而不同的东西」，必须与代码分离，外置到环境变量**。十二因子包括：代码库（一份代码库多份部署）、依赖（显式声明并隔离）、配置（存环境变量）、后端服务（当作可替换资源）、构建发布运行（严格分离）、进程（无状态，共享无关）、端口绑定（自包含服务）、并发（通过进程模型水平扩展）、易处理（快速启动与优雅终止）、开发生产等价、日志（当作事件流）、管理进程（一次性任务）。

配置的外置强度分三档：

| 档位 | 形态 | 评价 |
|---|---|---|
| 硬编码 | 写死在源码 | **违规**；换环境要改代码、密钥随 Git 历史永久泄露 |
| 外部文件 | `config/*.json`、`.env` | 可接受；但若文件随 artifact 走，仍是「同一份构建产物不能跨环境」 |
| 环境变量 | `process.env.X` | 推荐；同一 artifact 跨 dev/staging/prod |

本章 ex11 的审计器对 8 个配置项打分：

```
DATABASE_URL         source=env       ok
LOG_LEVEL            source=file      ok_externalized_but_prefer_env
PORT                 source=hardcoded VIOLATION_HARDCODED_CONFIG           src/server.js:12
STRIPE_SECRET_KEY    source=hardcoded VIOLATION_CRITICAL_HARDCODED_SECRET  src/pay.js:7
DB_PASSWORD          source=hardcoded VIOLATION_CRITICAL_HARDCODED_SECRET  src/db.js:4
=== summary ===
compliant=5 violations=3 critical=2
compliance_pct=62.5
```

### 🧑‍💻 程序员视角
- 落地惯例：`.env` 只用于本地开发且**必须进 .gitignore**；生产用平台能力注入（K8s Secret/ConfigMap、云 Secret Manager、CI 的 `secrets`）；启动时做 **fail-fast 校验**（缺必需环境变量直接退出并打印变量名，绝不用默认值静默降级到错误配置）。
- 事故画像：把 `PORT` 硬编码成 3000，在平台要求容器监听 `$PORT` 的环境里直接健康检查失败；把 `NODE_ENV` 硬编码进 Dockerfile，导致 staging 也跑生产配置。
- 密钥泄露的正确止血顺序：① 立即**轮换**密钥（泄露已成事实，删代码不会让已泄露的值失效）；② 再清理仓库历史与缓存（`git filter-repo` + 强制推送 + 让所有克隆者重新拉取）；③ 最后加自动扫描（secret scanning / pre-commit hook）防复发。
- 与「构建/发布/运行」三阶段对齐：构建产出**不可变 artifact**（镜像按 digest 引用），发布只改配置与引用，运行才注入具体值。ex11 的三档评价本质就是问「这份配置属于哪个阶段」。

### 🎓 博士生视角
- 形式化：把应用看成一个函数 `f(artifact, config, env) -> behavior`。12-Factor 要求 artifact 固定、行为差异全部由 config 承担，从而获得**可复现性**（同一 artifact 在任意环境行为可推演）与**可回滚性**（回滚只需换回上一个 artifact 引用）。硬编码相当于把 config 编译进了 artifact，破坏了这两个性质。
- 为什么偏好环境变量而非配置文件：环境变量由**创建进程的父进程**在 `execve` 时注入，与语言、框架无关，作用域天然是「这个进程及其子进程」，且随进程消亡而消失；配置文件则需要「找到路径」「解析格式」「决定优先级」三步，每步都可能不一致。
- 环境变量的代价同样来自这个机制：它是**扁平的无类型字符串**，没有层级、没有类型、没有枚举约束，也没有加密。因此工程上必须补一层 schema 校验（缺项/类型/范围）把「字符串」还原成「有类型的配置」，并把机密与普通配置分开处置（机密需要审计、轮换与短时有效期）。
- 「后端服务当作可替换资源」这一条把数据库、缓存、消息队列都抽象成「通过配置指向的附件」，于是本地可以用容器、生产可以用托管服务，应用代码不变。这是**依赖倒置**在部署层面的体现。

### 📚 考研者视角
- **12-Factor 不在 408 考纲内**，但相关考纲概念：**进程的地址空间布局**（栈、环境块与参数区）、`exec` 系列系统调用如何传递 `argv` 与 `envp`、进程创建与替换（`fork` + `exec`）。环境变量能跨 `fork/exec` 传给子进程，正是它能做配置载体的操作系统层原因。
- **面试/笔试考点**：① 12-Factor 是哪 12 条（至少要能报出配置、日志、构建发布运行、进程、并发等）；② 配置为什么放环境变量而不是配置文件（回答要点：同一 artifact 跨环境、与语言无关、作用域随进程）；③ 密钥泄露怎么处理（回答要点：先轮换再清历史）。
- **易混点**：`NODE_ENV`/`PORT` 这类**部署环境相关**的配置必须外置；而应用内不变的业务常量（如状态枚举）不算配置，硬编码它们是合理的。把「所有常量都外置」当成 12-Factor 是过度解读。
- **口径**：日志作为「事件流」意味着应用只写 stdout/stderr、不负责路由与归档；路由和归档是运行环境（journald、日志采集器、聚合后端）的职责。这条与本章第一节的 journalctl 直接呼应。
