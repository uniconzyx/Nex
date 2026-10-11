# 常见陷阱：Docker Compose 与部署实践

> 每条都是「命令能跑通、但结果或可靠性是错的」类型。按「现象 → 根因 → 正确做法」组织。
> 对应 examples 的实测评据已在括号中标注。

1. **用短语法 `depends_on` 以为能保证依赖就绪** —— 现象：`compose up` 成功，但 api 日志第一行就是 connection refused，前端 500。根因：短语法等价于 `condition: service_started`，只等容器**进程被创建**，不等应用**能接受连接**；数据库此时还在 initdb 与跑迁移。正确做法：被依赖方配 `healthcheck`，依赖方写 `depends_on: {db: {condition: service_healthy}}`；同时应用侧仍要有连接重试与退避。（ex02 实测：started 有 3 处抢跑，healthy 为 0 处）

2. **写了 `condition: service_healthy` 却忘了给被依赖方配 `healthcheck`** —— 现象：compose 报 dependency failed to start，或者干脆永远卡住。根因：没有 healthcheck 的服务**永远不会**进入 healthy 状态，条件无法满足。正确做法：健康检查要成对配置——db 有、api 依赖 db；api 自己也必须有，才能供 web 依赖。

3. **依赖图里出现环** —— 现象：编排器无法确定启动顺序，或报 cycle detected。根因：A 依赖 B、B 又依赖 A，说明服务职责切错了。正确做法：抽第三个服务、或改成消息队列异步解耦；**绝不能靠 `restart: always` 掩盖**——那只会变成两个服务互相等待的崩溃循环。（ex01 实测：三节点环与自环均无法排出拓扑序）

4. **健康检查不设 `start_period` 导致慢启动服务被反复杀** —— 现象：服务每次启动到一半就被重启，永远起不来。根因：migrations/大表预热期间探测必然失败，达到 `retries` 就被判 unhealthy，进而触发重启，形成「起一半被杀」的死循环。正确做法：设 `start_period`（如 30s~60s）覆盖初始化窗口；经验值 `interval=10s timeout=3s retries=3 start_period=30s`。（ex03 实测：start_period 内的失败不计入重试）

5. **以为健康检查失败一次就 unhealthy** —— 现象：偶发抖动被误判为故障，触发不必要的重启与告警。根因：状态机要求**连续**失败 `retries` 次，中间任何一次成功都会把计数清零。正确做法：理解这是抗噪设计，需要灵敏度就调小 `retries`/`interval`，不要误以为机制失效。（ex03 实测：抖动序列 8 次探测从未 unhealthy）

6. **在容器里用 `localhost` 访问同一 compose 的其他服务** —— 现象：`connection refused` 或 `no such host`，而宿主上明明能连。根因：每个容器有独立 net namespace，`localhost` 是**各自的** loopback。正确做法：容器间一律用**服务名**作为 DNS 名（`db:5432`），并把服务放进同一个自定义网络。

7. **用默认 bridge 网络而不是自定义网络** —— 现象：容器间用服务名解析失败（`no such host`）。根因：Docker 的**内嵌 DNS**（容器内的 127.0.0.11）只存在于**自定义**网络；默认 `docker0` 网桥没有它，`--link` 也已废弃。正确做法：显式声明 network 并把服务都加进去；compose 默认创建的 `<project>_default` 就够用。

8. **以为 `expose` 会把端口发布到宿主** —— 现象：写了 `expose: 8080`，宿主 curl 连不上。根因：`expose` 只写进元数据，**不做任何映射**；`ports` 才在 iptables nat 表里加 DNAT。正确做法：需要宿主访问就写 `ports`，并记住**宿主端口在前**（`8081:8080`）。中间件（db/redis）出于安全应**不发布**。（ex10 实测：只写容器端口不构成冲突）

9. **多个服务发布同一个宿主端口** —— 现象：`Bind for 0.0.0.0:80 failed: port is already allocated`。根因：宿主端口是全局资源，一个端口只能被一个容器映射。正确做法：改宿主侧端口；同一端口绑**不同宿主 IP**（`127.0.0.1:9000:9000` 与 `0.0.0.0:9000:9000`）不算冲突。（ex10 实测冲突检测正反两组）

10. **bind mount 遇到 Permission denied** —— 现象：镜像里写了 `USER 10001`（安全基线），宿主目录属主却是 root，一写就报权限错误。根因：**bind mount 完全沿用宿主的 uid/gid**，docker 不会帮你 chown（那会破坏宿主上可能被共享的文件）。正确做法：`chown` 到镜像 `USER` 的 uid，或改用**命名卷**（docker 首次挂载时会按镜像内目录属性初始化属主）。

11. **以为命名卷会把镜像里的更新同步进去** —— 现象：升级镜像后改了默认配置文件，容器内看到的还是旧内容。根因：docker 只在**卷为空时**才把镜像目录内容拷贝进去；卷里一旦有内容就以卷为准。正确做法：升级涉及配置变更时，显式迁移卷内数据，或用 ConfigMap/配置挂载替代卷内配置。

12. **`compose down -v` 把生产数据一起删了** —— 现象：一次「重启服务」之后数据库空了。根因：`down` 默认**保留**命名卷，`-v` 会**连卷一起删**。正确做法：生产环境禁用 `-v`，除非明确要重置；定期用临时容器打包命名卷做备份并**演练恢复**。（没演练过的备份等于没有备份）

13. **以为 `.env` 里的值会覆盖 shell 里的同名变量** —— 现象：`.env` 写着 `TAG=1.4.2`，实际部署成了 1.5.0。根因：插值来源里 **shell（宿主 OS 环境）优先于 `.env`**。正确做法：CI 里不要导出同名变量，或用 `--env-file` 固定来源；用 `docker compose config` 复核最终值。（ex07 实测五级优先级）

14. **以为 `.env` 会直接给容器注入变量** —— 现象：`.env` 里配了一堆值，容器里 `env` 却看不到。根因：`.env` 与 shell 都只是**插值来源**，作用于「解析 YAML 时」；必须配合 `environment` 或 `env_file` 才会真正进入容器。正确做法：要注入就写 `environment`（或 `env_file: [.env]`）。

15. **镜像标签不写强制校验，缺变量时悄悄部署成 latest** —— 现象：CI 忘了传 `TAG`，镜像标签变成空的，等价于 `app:latest`，部署了一个完全不确定的版本。根因：普通 `${TAG}` 未定义时展开成空串，不报错。正确做法：一律写 `image: app:${TAG:?必须指定 TAG}`，缺变量时 compose **直接失败**。（ex08 实测 `${VAR:?err}` 正反用例）

16. **把密钥写进 `environment` / `ARG` / `COPY .env`** —— 现象：密钥泄漏到镜像仓库，轮换要重建全部镜像。根因：这些内容会**永久留在镜像层**，`docker history` 可见，`RUN rm` 只是 whiteout 删不掉。正确做法：运行时注入（compose `secrets` / K8s `Secret` / Vault）；构建期用 BuildKit `--secret`。（ex09 实测 12-Factor 合规率）

17. **生产部署用 `latest` 标签** —— 现象：出事后回滚，重新拉 `app:latest` 拿到的**还是新版本**。根因：`latest` 是**浮动指针**，构建不可复现、回滚不可靠。正确做法：打不可变的语义化标签 + git sha，部署清单**固定到 digest**；`latest` 只留给本地开发。（ex12 实测：latest 不可回滚，digest 可）

18. **日志不配轮转，磁盘被 `json-file` 撑爆** —— 现象：宿主的 `/var/lib/docker` 涨到 100%，所有容器一起挂。根因：默认 `json-file` 把日志写到**宿主**且随时间线性增长。正确做法：显式配 `max-size` / `max-file`（单容器上限 = 两者相乘），或改用 `local` 驱动（自带轮转 + 压缩）；救急时 `truncate` 而不是 `rm`（文件被进程持有，`rm` 不释放空间）。（ex06 实测：配轮转恒定 240MiB，不配 53 小时撑爆 50GiB）

19. **设了 `mem_limit` 却不管应用是否感知 cgroup** —— 现象：容器一启动就被杀，退出码 137。根因：JVM/Node 默认按**宿主内存**算堆与 GC 阈值（16GiB 宿主 → 4GiB 堆），远超容器上限。正确做法：开启容器感知（JVM `UseContainerSupport` + `MaxRAMPercentage`、Node `--max-old-space-size`、Go `GOMEMLIMIT`），并给堆之外的元空间/线程栈/直接内存留 25%~50% 余量。（ex05 实测）

20. **把 CPU 超限与内存超限混为一谈** —— 现象：以为「资源超了都会退出」，结果 CPU 打满时服务只是变慢却没重启，排查方向跑偏。根因：**CPU 是可压缩资源**（超限被 CFS 节流，进程还在），**内存是不可压缩资源**（超限直接 OOM-kill，退出码 137）。正确做法：看到 137 先查内存（`docker inspect` 的 `OOMKilled` 字段 + `dmesg`），看到变慢再查 CPU 节流。

21. **用 `restart: always` 当作高可用手段** —— 现象：服务崩溃后不停重启，日志刷屏，根因被掩盖。根因：restart 只负责「拉起来」，不负责「修好」；持续崩溃还会被 `start-limit-hit` 熔断。正确做法：restart 只作兜底，根因靠健康检查 + 指标告警 + 日志定位。（ex04 实测：退避序列 1/2/4 后被熔断）

22. **忽略了镜像里的时区与 locale 默认值** —— 现象：订单时间与本地差 8 小时；写中文日志报 `UnicodeEncodeError`。根因：容器默认 UTC 且 locale 是 POSIX/C，Python 的 `open()` 默认编码按 locale 取，因此是 ASCII。正确做法：`ENV TZ=Asia/Shanghai` + `ENV LANG=C.UTF-8 LC_ALL=C.UTF-8`；更根本的是**内部一律存 UTC、只在展示层转换**，IO 边界显式写 `encoding='utf-8'`。（ex13 实测规则库判定）

23. **`kompose convert` 之后直接上线** —— 现象：迁移到 K8s 后服务起不来或流量打到没就绪的实例。根因：自动转换会**悄悄丢掉 `depends_on`**，且缺少 `readinessProbe`、`resources.requests`、滚动更新策略。正确做法：转换结果只当草稿，人工补齐探针、资源限制与就绪门控；K8s **没有 `depends_on` 的等价物**，顺序要靠 `initContainer` 或 readiness。（ex11 实测概念映射）

24. **把 `docker compose up` 当成幂等的部署动作** —— 现象：以为重复执行只会「补齐差异」，结果配置漂移、旧容器残留。根因：compose 的 `up` 会按当前文件重建**有差异**的服务，但不会清理文件里已删除的服务；多个人在不同机器上各跑一次，状态无从审计。正确做法：生产用 **GitOps**——部署清单进 git，由流水线按清单部署，回滚就是一次 `git revert`。
