# Docker Compose 与部署实践 — 学习目标

## 一、本章定位

本章是「工程工具」学科第六章，也是 Docker 这条线的收尾章。tool-ch05 解决了
**「单个容器怎么造、怎么跑」**，本章解决下一个问题：**十几个服务怎么一起跑起来、
怎么可靠地交付到生产、出事了怎么定位**。

Compose 是把「一组容器的声明式期望状态」写进 YAML 的工具；但真正决定线上稳定性的，
是那些看起来最不起眼的字段：`depends_on` 的 `condition`、`healthcheck` 的
`start_period`、`restart` 的退避、日志驱动的轮转上限、内存上限与 OOM 的关系。
本章把这些字段全部还原成**可判定的规则**，并用 13 个离线可跑的 Python 示例实测其判据。

- **先修**：`tool-ch05`（Docker 基础：镜像、容器与 Dockerfile）。本章默认你已理解
  镜像分层、容器可写层、数据卷与端口映射。
- **衔接**：本章最后一节给出 compose → Kubernetes 的概念映射，是把本地编排迁移到
  生产编排的桥；再往后属于云原生/运维方向（本学科不展开）。
- **面试权重**：★★★★★ —— `depends_on` 为什么不够用、健康检查与就绪门控、
  OOMKilled 的排查、12-Factor 配置外置、`latest` 标签的陷阱、compose 与 K8s 的
  概念对应，是后端/SRE/云原生方向的必考组合。

## 二、学习目标

学完本章，你应当能够：

1. **写对 compose 的服务定义并排出启动顺序**：把 `services` 归一成依赖图，会用
   Kahn 算法做**拓扑排序**并给出可并行的启动批次；能**检测循环依赖**（examples/ex01 实测
   三节点环与自环）。
2. **说清 `depends_on` 的局限并给出正确写法**：短语法等价于
   `condition: service_started`，**只等容器启动、不等应用就绪**；要保证就绪必须写
   `condition: service_healthy`，且被依赖方必须配 `healthcheck`
   （examples/ex02 实测：started 有 3 处抢跑，healthy 为 0 处）。
3. **掌握健康检查状态机**：`test`/`interval`/`timeout`/`retries`/`start_period`
   五个字段各自的作用；**连续失败达到 `retries` 才转 unhealthy**，抖动不会触发；
   `start_period` 内的失败不计入重试（examples/ex03 实测时间序列）。
4. **区分网络里的「暴露」与「发布」**：`expose` 只是文档性声明，`ports` 才是把端口
   发布到宿主；同一自定义 bridge 网络内**服务名即 DNS**，容器间互访用服务名而不是
   `localhost`。
5. **选对数据卷形式**：命名卷（docker 管理生命周期、会自动初始化属主）vs
   绑定挂载（宿主目录直通、需自己对齐 uid/gid）；知道备份与迁移的做法。
6. **求解环境变量的最终值**：按 Docker 官方的**五级优先级**
   （CLI `-e` > 插值（shell 优先于 `.env`）> `environment` > `env_file` > 镜像 `ENV`）
   推算任意组合下的结果；会用 `${VAR:-default}` / `${VAR:?err}` 让缺变量**构建期即失败**
   （examples/ex07、ex08 实测多组用例）。
7. **配置 restart 与日志驱动**：`no`/`always`/`unless-stopped`/`on-failure` 的语义差别，
   `on-failure` 的**指数退避**与 `start-limit-hit` 熔断；`json-file` 不配
   `max-size`/`max-file` 会撑爆磁盘（examples/ex04、ex06 实测）。
8. **解释资源限制与 OOM**：`mem_limit`/`cpus` 的语义，容器 OOMKilled 的成因、
   退出码 137 的来历，以及「应用没感知 cgroup」这一高频事故；会给出排查顺序。
9. **把配置外置并管好密钥**：用 12-Factor 的口径判断哪些配置不该进镜像；密钥走
   运行时注入或密钥挂载，绝不进镜像层（examples/ex09 实测合规率）。
10. **打通 CI 与镜像仓库**：build → 打标签 → 推送 → 部署的流水线；`latest` 的浮动陷阱，
    语义化标签与 **digest 固定**的区别（examples/ex12 实测：latest 不可回滚，digest 可）。
11. **给出 compose → K8s 的演进路径**：Deployment/Service/StatefulSet/PVC/
    ConfigMap/Secret/Probe 与 compose 各字段的对应关系（examples/ex11 实测生成 19 个对象）。
12. **按症状定位常见故障**：端口占用、卷权限、网络不通、DNS 解析失败、时区与编码，
    形成稳定的排查顺序（examples/ex13 实测规则库判定）。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写出环境变量五级优先级与四种 restart 策略 | 习题 choice |
| 理解 | 给一段 compose 推断启动批次、是否可编排、有无端口冲突 | 习题 output |
| 应用 | 用 Python 实现依赖图拓扑排序、健康检查状态机、OOM 判定器 | examples 实跑 13 个 |
| 分析 | 能定位「compose up 成功但接口 500」的根因（依赖抢跑） | pitfalls 第 1/2 条 |
| 评价 | 能论证「为什么生产不能用 latest 标签」 | interview 第 5 题 |

## 四、常见认知误区（先破后立）

1. **「`depends_on` 保证了依赖就绪」** —— 错。它只保证**启动顺序**，
   `service_started` 表示「容器进程起来了」，不代表数据库能接受连接。
2. **「健康检查失败一次容器就被标记为 unhealthy」** —— 错。要**连续**失败
   `retries` 次；单次抖动会被下一次成功清零。
3. **「`.env` 里的值会覆盖 shell 里的同名变量」** —— 错。插值来源里
   **shell（宿主环境）优先**；而且 `.env` 与 shell 都只是插值来源，
   必须配合 `environment`/`env_file` 才会真正进入容器。
4. **「日志写在容器里，容器删了日志也没了，不会占磁盘」** —— 错。
   `json-file` 的日志存在宿主的 `/var/lib/docker/containers/<id>/`，
   容器删了才释放；容器活着不配轮转就会**一直涨到撑爆磁盘**。
5. **「设了 `mem_limit` 应用就会自动适配」** —— 错。cgroup 是内核强制的，
   但 JVM/Node 默认按**宿主内存**算堆/GC 阈值，于是启动即 OOMKilled（137）。
6. **「用 `latest` 方便，回滚时重新拉一次就行」** —— 错。`latest` 是**浮动指针**，
   回滚拉到的可能是新版本，等于没回滚。要用 digest 或不可变语义化标签。

## 五、学习路径建议

1. 读 concept/01（服务定义、依赖顺序与网络），跑 examples/ex01、ex02、ex10。
2. 读 concept/02（数据卷、环境变量、健康检查），跑 examples/ex07、ex08、ex03。
3. 读 concept/03（restart、日志、镜像仓库与 CI），跑 examples/ex04、ex06、ex12。
4. 读 concept/04（资源限制/OOM、配置与密钥、K8s 演进、故障排查），
   跑 examples/ex05、ex09、ex11、ex13。
5. 做 exercises.json 的 8 道题，自测 interview.json，再用 project.json 交付一个
   compose 静态分析器 `compose-lite`。

## 六、与 GitHub 顶级资源的对接

- bregman-arie/devops-exercises（84k★）—— DevOps 练习题集，含 Docker/K8s/CI 专项练习
- trimstray/the-book-of-secret-knowledge（248k★）—— 运维与工程工具知识合集
- jlevy/the-art-of-command-line（162k★）—— 命令行体系化进阶
- ohmyzsh/ohmyzsh（190k★）—— Shell 生产力框架
- 推荐读物：《Docker 技术入门与实战》编排篇、Docker 官方 Compose 文档
  （Compose file reference / Environment variables precedence）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 254,934 | §4.4 常见故障排查：症状 → 根因 → 处置 | 看 `topics/containers/running_containers.md`：题目按「容器起不来 / 起来了但连不通 / 起来了但立刻退出」分场景排查；这套分层正是本章排障表的骨架，先分清「没起来」还是「起来了但连不通」，比盲查日志快得多 |
| 2 | [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,274 | §2.2 环境变量：五级优先级与变量插值 | 读 `lib/` 里对 `PATH` 的处理：容器里同样靠环境变量注入配置，理解 Shell 的变量作用域能避免「变量在容器里读不到」；关键要分清 compose 文件里的 `${VAR}`（编排时插值）与容器内的运行时变量——这是两级不同的作用点 |
| 3 | [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162,646 | §1.2 网络：自定义 bridge、服务名即 DNS、暴露 vs 发布 | 读 `topics/containers/containerized_web_server.md`与 `flask_container_ci2`：前者验证服务名解析，后者展示多容器间的网络打通；配合本章 `expose` 与 `ports` 的区别，就能解释「同网段服务名能通、宿主机 curl 不通」 |
| 4 | [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 86,127 | §2.1 数据卷：命名卷 vs 绑定挂载，持久化与备份 | 读 `topics/containers/containerized_db_persistent_storage.md`：题目要求让数据库数据在容器重建后仍存在，答案对比命名卷与绑定挂载两种写法；这直接验证本章那条——容器的可写层随实例消亡，只有卷是「越过容器生命周期」的存储 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Docker 实战（入门到大神）<br><sub>尚硅谷</sub> | [BV1gr4y1U7CY](https://www.bilibili.com/video/BV1gr4y1U7CY/) | 全章 | 主线：镜像分层 → 容器生命周期 → Dockerfile 与多阶段构建 → 数据卷与网络 → Compose；看完回 `ex01`（Compose 服务解析器）核对 |
| 2 | 黑马程序员 · Git 全套教程<br><sub>黑马程序员</sub> | [BV1MU4y1Y7h5](https://www.bilibili.com/video/BV1MU4y1Y7h5/) | 全章 | 对象模型 → 分支本质 → merge/rebase → 冲突与 reflog 救援；配真实协作场景演示；看完回 `ex02`（depends_on 的局限）核对 |
| 3 | 黑马测试 · Linux 课程（2 天）<br><sub>黑马测试</sub> | [BV1vk4y1r7cW](https://www.bilibili.com/video/BV1vk4y1r7cW/) | §2.2 环境变量 | 环境配置与 vim、进程与权限、常见运维操作；装环境卡住时看它；看完回 `ex03`（健康检查状态机）核对 |
| 4 | GeekHour · 一小时 Git 教程<br><sub>GeekHour</sub> | [BV1HM411377j](https://www.bilibili.com/video/BV1HM411377j/) | 全章 | 一小时建立全局图：三区、HEAD、常用命令的对应关系，适合先看这个再进细节；看完回 `ex04`（restart 策略退避模拟）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《鸟哥的 Linux 私房菜（第 4 版）》 |
| 2 | 《Pro Git（第 2 版）》Chacon & Straub |
| 3 | 《Docker 技术入门与实战（第 3 版）》杨保华 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
