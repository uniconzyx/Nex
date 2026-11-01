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

<!-- injected-code -->

```yaml
services:
  api:
    build: .
    depends_on:
      db:
        condition: service_healthy     # 等就绪，不只是等启动
    environment:
      DB_HOST: db                      # 服务名即 DNS 名，同网络内直接解析
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
```

`depends_on` 的默认 condition 是 `service_started`——只保证「容器起来了」，
而 Postgres 从容器起来到能接受连接还有几秒。不显式写 `service_healthy`，
应用就会稳定地在启动时撞一次「连接被拒绝」，然后靠重试掩盖掉这个设计缺陷。

## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### Compose 服务解析器：依赖图构建、拓扑排序与循环依赖检测（正反两组）

```python
from collections import defaultdict


def parse_services(raw):
    """把 compose 的 services 段归一成内部模型。

    depends_on 有两种写法：短语法（列表）与长语法（映射，键是服务名，
    值是 condition）。归一后统一成列表，保留 condition 供 ex02 使用。
    """
    services = {}
    conditions = {}
    for name, spec in raw.items():
        deps = spec.get("depends_on") or []
        cond = {}
        if isinstance(deps, dict):
            for d, cfg in deps.items():
                cond[d] = (cfg or {}).get("condition", "service_started")
            deps = list(deps.keys())
        else:
            for d in deps:
                cond[d] = "service_started"
        services[name] = {
            "image": spec.get("image", ""),
            "depends_on": list(deps),
            "ports": list(spec.get("ports") or []),
        }
        conditions[name] = cond
    return services, conditions


def topo_sort(services):
    """Kahn 算法：返回 (拓扑序, 启动批次, 环内服务, 悬空依赖)。"""
    indeg = {n: 0 for n in services}
    adj = defaultdict(list)
    missing = []
    for n, s in services.items():
        for d in s["depends_on"]:
            if d not in services:
                missing.append((n, d))
                continue
            adj[d].append(n)
            indeg[n] += 1
    ready = sorted(n for n in services if indeg[n] == 0)
    order, batches = [], []
    while ready:
        batches.append(list(ready))
        nxt = []
        for n in ready:
            order.append(n)
            for m in sorted(adj[n]):
                indeg[m] -= 1
                if indeg[m] == 0:
                    nxt.append(m)
        ready = sorted(nxt)
    cycle = sorted(n for n in services if indeg[n] > 0)
    return order, batches, cycle, missing


def show(title, raw):
    print("=== %s ===" % title)
    svc, cond = parse_services(raw)
    print("服务数 = %d" % len(svc))
    for n, s in svc.items():
        c = ",".join("%s:%s" % (d, cond[n][d]) for d in s["depends_on"]) or "-"
        print("  %-6s image=%-30s depends_on=%-18s condition=%s" % (n, s["image"], str(s["depends_on"]), c))
    order, batches, cycle, missing = topo_sort(svc)
    print("拓扑序: %s" % (" -> ".join(order) if order else "(空)"))
    for i, b in enumerate(batches, 1):
        print("  启动批次 %d: %s" % (i, b))
    print("批次总数 = %d（同批次内可并行启动）" % len(batches))
    print("存在循环依赖: %s" % bool(cycle))
    if cycle:
        print("  环内服务: %s" % cycle)
    print("悬空依赖(依赖了未定义的服务): %s" % (missing if missing else "无"))
    print("可编排(无环且无悬空): %s" % (not cycle and not missing))
    print()


CASE_A = {
    "web":   {"image": "nginx:1.27-alpine", "depends_on": ["api", "redis"], "ports": ["80:80"]},
    "api":   {"image": "registry.internal/app:1.4.2", "ports": ["8080:8080"],
              "depends_on": {"db": {"condition": "service_healthy"},
                             "redis": {"condition": "service_started"}}},
    "redis": {"image": "redis:7.4-alpine"},
    "db":    {"image": "postgres:17.2-alpine", "ports": ["5432"]},
}

CASE_B = {
    "web":   {"image": "nginx:1.27-alpine", "depends_on": ["api"]},
    "api":   {"image": "registry.internal/app:1.4.2", "depends_on": ["cache"]},
    "cache": {"image": "redis:7.4-alpine", "depends_on": ["web"]},
}

CASE_C = {
    "worker": {"image": "registry.internal/app:1.4.2", "depends_on": ["worker"]},
    "api":    {"image": "registry.internal/app:1.4.2", "depends_on": ["worker"]},
}

print("### Compose 依赖图分析：拓扑排序 + 环检测 ###")
print()
show("用例A（正例）：无环 DAG，可以排出启动顺序", CASE_A)
show("用例B（反例）：三节点环 web -> api -> cache -> web", CASE_B)
show("用例C（反例）：自环 worker -> worker", CASE_C)
print("小结：Compose 要求依赖图是无环有向图（DAG）；")
print("      存在环时编排器无法给出启动顺序，必须在设计阶段拆掉环。")
```

实际输出：

```text
### Compose 依赖图分析：拓扑排序 + 环检测 ###

=== 用例A（正例）：无环 DAG，可以排出启动顺序 ===
服务数 = 4
  web    image=nginx:1.27-alpine              depends_on=['api', 'redis']   condition=api:service_started,redis:service_started
  api    image=registry.internal/app:1.4.2    depends_on=['db', 'redis']    condition=db:service_healthy,redis:service_started
  redis  image=redis:7.4-alpine               depends_on=[]                 condition=-
  db     image=postgres:17.2-alpine           depends_on=[]                 condition=-
拓扑序: db -> redis -> api -> web
  启动批次 1: ['db', 'redis']
  启动批次 2: ['api']
  启动批次 3: ['web']
批次总数 = 3（同批次内可并行启动）
存在循环依赖: False
悬空依赖(依赖了未定义的服务): 无
可编排(无环且无悬空): True

=== 用例B（反例）：三节点环 web -> api -> cache -> web ===
服务数 = 3
  web    image=nginx:1.27-alpine              depends_on=['api']            condition=api:service_started
  api    image=registry.internal/app:1.4.2    depends_on=['cache']
…（后续输出略，完整结果见判题台）
```

> 出处：`examples/ex01-compose-parser-topo-cycle.json`。改一处再看输出变没变，比读三遍解释有用。

### depends_on 的局限：service_started 只等启动不等就绪（正反两组实测）

```python
ORDER = ["db", "redis", "api", "web"]

SERVICES = {
    "db":    {"depends_on": [],        "ready_after": 12, "note": "初始化数据目录 + 跑迁移"},
    "redis": {"depends_on": [],        "ready_after": 2},
    "api":   {"depends_on": ["db", "redis"], "ready_after": 3},
    "web":   {"depends_on": ["api"],   "ready_after": 1},
}


def plan(condition):
    """按 condition 计算各服务的启动时刻与真正可用时刻（整数逻辑时钟）。"""
    start, ready = {}, {}
    for n in ORDER:
        deps = SERVICES[n]["depends_on"]
        if not deps:
            start[n] = 0
        else:
            t = 0
            for d in deps:
                wait = 0 if condition == "service_started" else SERVICES[d]["ready_after"]
                t = max(t, start[d] + wait)
            start[n] = t + 1          # 创建容器本身占 1 个 tick
        ready[n] = start[n] + SERVICES[n]["ready_after"]
    return start, ready


def unready_pairs(start, ready):
    """上游开始运行的时刻若早于依赖真正就绪的时刻，即为「抢跑」。"""
    bad = []
    for n in ORDER:
        for d in SERVICES[n]["depends_on"]:
            if start[n] < ready[d]:
                bad.append((n, d, start[n], ready[d]))
    return bad


def report(title, condition):
    print("=== %s ===" % title)
    start, ready = plan(condition)
    for n in ORDER:
        print("  %-6s start=%-3d ready=%-3d" % (n, start[n], ready[n]))
    bad = unready_pairs(start, ready)
    print("  抢跑的上游: %s" % (["%s<-%s(%d<%d)" % b for b in bad] if bad else "无"))
    print("  存在「依赖已 started 但未 ready 就启动」的上游: %s" % bool(bad))
    print("  抢跑数量 = %d" % len(bad))
    print("  全部服务真正可用的逻辑时刻 = %d" % max(ready.values()))
    print("  判定：启动完成即业务可用 = %s" % (not bad))
    print()
    return bool(bad)


print("### depends_on 的两种 condition 对比 ###")
print()
b1 = report("反例 A：短语法 depends_on（等价 condition: service_started）", "service_started")
b2 = report("正例 B：长语法 condition: service_healthy", "service_healthy")

print("=== 结论判据 ===")
print("service_started 会抢跑: %s（预期 True）" % b1)
print("service_healthy 会抢跑: %s（预期 False）" % b2)
print("只有 service_healthy 能保证依赖就绪: %s" % (b1 and not b2))
print("代价：service_healthy 把整体可用时刻从 12 推迟到 18，慢但正确")
```

实际输出：

```text
### depends_on 的两种 condition 对比 ###

=== 反例 A：短语法 depends_on（等价 condition: service_started） ===
  db     start=0   ready=12 
  redis  start=0   ready=2  
  api    start=1   ready=4  
  web    start=2   ready=3  
  抢跑的上游: ['api<-db(1<12)', 'api<-redis(1<2)', 'web<-api(2<4)']
  存在「依赖已 started 但未 ready 就启动」的上游: True
  抢跑数量 = 3
  全部服务真正可用的逻辑时刻 = 12
  判定：启动完成即业务可用 = False

=== 正例 B：长语法 condition: service_healthy ===
  db     start=0   ready=12 
  redis  start=0   ready=2  
  api    start=13  ready=16 
  web    start=17  ready=18 
  抢跑的上游: 无
  存在「依赖已 started 但未 ready 就启动」的上游: False
  抢跑数量 = 0
  全部服务真正可用的逻辑时刻 = 18
  判定：启动完成即业务可用 = True

=== 结论判据 ===
service_started 会抢跑: True（预期 True）
service_healthy 会抢跑: False（预期 False）
只有 service_healthy 能保证依赖就绪: True
代价：service_healthy 把整体可用时刻从 12 推迟到 18，慢但正确
```

> 出处：`examples/ex02-depends-on-started-vs-healthy.json`。改一处再看输出变没变，比读三遍解释有用。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | `depends_on` 只排顺序，就绪靠 `service_healthy` + 应用侧重试；容器间一律用服务名 |
| 博士生 | 依赖图是 AOV 网，可编排 ⟺ 无环；started 是事件、healthy 是谓词，中间隔着不可界定的 `T_init` |
| 考研者 | 对应 408 拓扑排序/关键路径与 NAT、DNS 考点；「EXPOSE 不映射、localhost 不可达」是标准口径 |
