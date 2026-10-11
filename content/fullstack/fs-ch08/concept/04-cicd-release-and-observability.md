# fs-ch08 · 四、CI/CD 流水线、发布策略与可观测性

## 一、CI/CD 流水线设计（GitHub Actions）

GitHub Actions 的 workflow 是三层结构：**workflow**（一个 YAML 文件）→ **job**（默认并行，用 `needs:` 串行）→ **step**（顺序执行）。`runs-on` 指定 runner，`on` 声明触发条件，`secrets` 注入敏感值，`strategy.matrix` 展开参数组合，`actions/cache` 复用依赖缓存。

一个标准的四段流水线：

```yaml
name: ci
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm ci
      - run: npm run build
  test:
    runs-on: ubuntu-latest
    needs: [build]
    steps:
      - run: npm test
  image:
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: docker/build-push-action@v6
  deploy:
    runs-on: ubuntu-latest
    needs: [image]
    steps:
      - run: kubectl apply -f k8s/
```

本章 ex05 的静态校验器（自带极简 YAML 子集解析器）对合法与非法两份 workflow 给出判定：

```
=== workflow(good) ===
jobs=4  topo_order=build,test,image,deploy  issues=0  valid=True
=== workflow(bad) ===
jobs=3  topo_order=deploy  issues=4  valid=False
  - cycle:build->test->build
  - missing_runs_on:test
  - missing_trigger
  - unknown_needs:deploy>buidl
```

本章 ex06 进一步把 DAG 当成调度问题求解：

```
jobs=6  topo_order=lint,build,e2e,test,image,deploy  dag_acyclic=True
  lint    start=0  finish=2
  build   start=2  finish=7
  test    start=7  finish=11
  e2e     start=7  finish=13
  image   start=11 finish=14
  deploy  start=14 finish=15
makespan_min=15
critical_path=lint->build->test->image->deploy
max_parallelism=2
sum_job_minutes=21   serial_would_take=21   speedup_pct=28.6
```

串行要 21 分钟，按 DAG 调度只需 15 分钟（关键路径长度），最大并行度只有 2——**并行化的收益上限由关键路径决定，而不是由「能并行多少」决定**。

### 🧑‍💻 程序员视角
- 设计原则落地：① **快速失败**——把最便宜、最可能失败的检查放最前（lint/类型检查 → 单元测试 → 构建 → 制镜像 → 部署）；② **needs 串成 DAG**，绝不把部署与测试并行；③ 镜像只在主干分支且测试通过后推送；④ 依赖与构建产物用 cache 复用（命中率决定流水线墙钟的主要常数项）；⑤ 密钥走 `secrets`，不要回显到日志（用 `::add-mask::` 遮蔽派生值）。
- 矩阵的用法与代价：`strategy.matrix` 把 `{os, node-version}` 展开成 N 个并行 job，覆盖率上去了但配额消耗与失败重试成本也上去；应只矩阵化「真的有平台/版本差异」的维度。
- 事故画像：`needs: [buidl]` 拼错一个字母，GitHub Actions 会直接报「依赖的 job 不存在」而整个 workflow 失败；另一种更隐蔽的错是把两个 job 都用 `needs` 指成环，导致 workflow 永久排队。这类错误完全可以在提交前用静态校验（ex05）挡住，不必等到 CI 里爆炸。
- 可见性：把关键判据（走了几条测试、镜像大小、部署耗时）作为 job summary 输出，让「流水线是否健康」可被一眼看出，而不是靠翻日志。

### 🎓 博士生视角
- 流水线调度就是**有向无环图的最小完工时间（makespan）问题**：给定每个 job 的工时与依赖约束，`start(n) = max{ finish(d) : d ∈ deps(n) }`，`makespan = max finish(n)`。这条递推与 AOE 网求最早发生时间 `ve` 完全同构。
- 关键路径是 makespan 的下界，也是**不能被并行度改善的部分**：增加 runner 只能压缩非关键路径上的等待（提高并发宽度），无法越过关键路径。ex06 的 `speedup_pct=28.6` 就是「21 → 15」这条链的量化。
- 更一般的资源受限调度（job 有限、runner 有限、要最小化 makespan）是 NP-hard 的，实践中用列表调度（list scheduling）这类启发式：按关键路径长度或工时降序依次分配给最早空闲的 runner。理解这一点能解释「为什么加机器有时候不见效」——瓶颈在关键路径。
- 「快速失败」有信息论依据：在流水线里，任务是串行依赖的，前置任务的失败会**作废其后所有工作**；因此把「低成本 + 高失败概率」的检查前置，能最小化期望浪费的资源。这不是风格偏好，而是期望代价的一阶优化。

### 📚 考研者视角
- **408 数据结构考点（强连接）**：**AOV 网与拓扑排序**、**AOE 网与关键路径**。标准口径：正推求事件最早发生时间 `ve(j) = max{ ve(i) + w(i,j) }`，逆推求最晚发生时间 `vl(i) = min{ vl(j) - w(i,j) }`；活动的 `e(a) = ve(i)`、`l(a) = vl(j) - w(i,j)`，`e(a) = l(a)` 即为**关键活动**，关键活动连成关键路径，其长度即最短工期。
- **常考题型**：给定 AOE 网求关键路径与最短完成时间；判断某活动能否缩短工期（只有关键活动能）。本章 ex06 输出的 `start/finish` 就是 `ve/vf` 的等价形式，`critical_path_len=15=makespan_min` 即为该结论。
- **易混点**：关键路径可能不唯一；缩短**非关键活动**不会缩短工期（其时间余量 > 0）；缩短关键活动也不一定缩短总工期——当它变成非关键活动后就不再是瓶颈。
- **面试考点**：CI 与 CD 的区别；流水线为什么要「先 lint 后 test」；如何设计一条可信的发布流水线。

## 二、环境与发布策略：蓝绿、金丝雀、滚动与回滚

发布策略的本质是「在切换流量时，如何控制风险与恢复速度」：

| 策略 | 形态 | 停机 | 回滚速度 | 主要风险 |
|---|---|---|---|---|
| **重建** recreate | 停旧起新 | 有 | 快 | 明确的服务中断 |
| **滚动** rolling | 逐批替换 | 无 | 中（要滚回去） | 新旧版本长期共存；批间容量下降 |
| **蓝绿** blue-green | 两套完整环境切流量 | 无 | 极快（切回） | 资源翻倍；数据库变更难同步 |
| **金丝雀** canary | 按权重逐步放量 | 无 | 快（停放量） | 观察窗口与指标选择；分桶稳定性 |

本章 ex10 用确定性分桶（`crc32(user) % 100`）模拟两种策略在 2000 个用户上的流量分配：

```
=== canary ===
  step  weight  new_version_users  share_pct  err_permille  action
  0     5       107                5.35       0             continue
  1     25      510                25.50      10            continue
  2     50      1007               50.35      15            continue
  3     100     2000               100.00     -             no_data
=== blue_green ===
  0     0       0                  0.00       0             continue
  1     100     2000               100.00     10            continue
canary_is_progressive=True
blue_green_is_atomic=True
bucketing_is_stable=True
canary_aborts_on_error=True
```

当新版本错误率越过阈值（`133 permille > 30`）时，金丝雀在第 1 步 `abort_rollback`。本章 ex09 则给出**回滚判定**的判据设计：

```
=== single_spike_then_ok ===   window0 breach(150) → window1 ok(8) → window2 ok(7)   rollback=False
=== sustained_degradation ===  window0 breach(80)  → window1 breach(114)            rollback=True at_window=1
=== insufficient_data ===      requests=40 / 30 均 < 200 → skip_insufficient_data   rollback=False
```

关键读数：**单点尖峰不触发回滚，持续劣化在连续 2 个窗口越界后触发，样本不足则不下结论**。

### 🧑‍💻 程序员视角
- 金丝雀必须用**稳定哈希分桶**而不是随机分配：否则同一用户在不同请求间来回切版本，遇到问题时无法复现，会话/缓存也会错乱。ex10 的 `routed(5) ⊆ routed(25) ⊆ routed(50)` 是权重单调递增时新版本用户集合的**嵌套性**，这正是稳定分桶带来的性质。
- 回滚判据要防两类错误：**假阳性**（单点尖峰就回滚 → 发布-回滚抖动，团队不敢发版）与**假阴性**（连续劣化没人管 → 事故扩大）。ex09 用「最小样本量 + 连续 N 窗口越界」同时压制两者。
- 数据库变更决定回滚可行性：任何**破坏性** schema 变更都必须在两步之间保持双版本兼容（expand/contract：先加字段并双写 → 数据迁移 → 再切读 → 最后删旧字段）。否则「应用能回滚、数据库回不去」，回滚就是空话。
- 事故画像：金丝雀用 5% 流量跑 3 分钟就放到 100%，结果问题在 20 分钟后（长尾延迟、缓存冷启动、连接池耗尽）才出现，此时已全量。修复是让观察窗口覆盖业务周期，并选择与业务相关的指标（下单成功率、支付成功率），而不只是 HTTP 5xx。

### 🎓 博士生视角
- 稳定分桶的形式化：定义 `bucket(u) = H(u) mod 100`，金丝雀命中集合 `S(w) = {u : bucket(u) < w}`。由 `w1 < w2 ⟹ S(w1) ⊆ S(w2)` 得到嵌套性，于是「放量」是**单调加入**用户，已在金丝雀里的用户不会被踢回旧版本。随机分配则不具此性质，会破坏会话一致性与指标可比性。
- 回滚判定是一个**序贯决策**问题：每个窗口观测到的是比例的样本估计 $\\hat p = x/n$，其标准误为 $\\sqrt{\\hat p(1-\\hat p)/n}$。样本量越小，$\\hat p$ 的方差越大，「尖峰」越可能只是噪声——这正是 ex09 的 `min_requests=200` 要表达的约束：**在样本不足时不做决策**。
- 连续 N 窗口的规则等价于引入了**确认延迟**：把单次观测的假阳性率降低到近似 $p^N$，代价是最长检测延迟 ≈ N × 窗口长度。这是「灵敏 vs 稳健」的经典取舍，与探针的 `failureThreshold` 是同一类设计。
- 蓝绿与金丝雀的差别是**状态空间**：蓝绿只有两个状态（全部旧 / 全部新），切换是原子的，因此回滚也是原子的；金丝雀有连续的权重维度，回滚是「停止放量并回退权重」，中间态需要处理「两个版本同时持有会话与数据」的双写兼容问题。

### 📚 考研者视角
- **408 考点**：AOE 网关键路径（发布批次与并行替换的调度同构）；进程/线程并发与资源分配（滚动发布中的容量约束）；操作系统中的**负载与调度**指标。
- **概率统计口径**：总体比例的估计 $\\hat p = x/n$、标准误 $\\sqrt{\\hat p(1-\\hat p)/n}$、置信区间随 $n^{-1/2}$ 收窄；这解释了「为什么样本不足时不能下结论」（ex09 的 skip 分支）与「为什么小流量金丝雀需要更长的观察窗」。
- **易混点**：灰度（面向**用户/入口**的部分可见，常按地区或用户群体）与金丝雀（面向**流量比例**的逐步放量）常被混用；蓝绿强调的是「两套完整环境 + 原子切换」，不是「两个颜色」。答题时按机制定义而不是按名字解释。
- **面试考点**：蓝绿与金丝雀的区别与各自代价；回滚为什么比发布更重要；数据库迁移如何做到可回滚。

## 三、监控、告警与日志聚合

可观测性由三根支柱构成：**metrics**（可聚合、适合告警）、**logs**（信息密度高、适合定位）、**traces**（跨服务因果、适合延迟归因）。健康检查在编排层表现为探针：

| 探针 | 失败后果 | 该探什么 |
|---|---|---|
| **liveness** | 重启容器 | 自身进程是否卡死（死锁、假死） |
| **readiness** | 摘掉流量 | 是否具备服务能力（依赖是否可用、预热是否完成） |
| **startup** | 继续等待（不执行 liveness） | 慢启动服务是否已完成初始化 |

探针判定是一个**滞回状态机**：连续失败 `failureThreshold` 次判不健康，连续成功 `successThreshold` 次判恢复。本章 ex08 用整数时钟实测：

```
=== trip_then_recover probes=0000111 failureThreshold=3 successThreshold=2 ===
  t=0 probe=0 consec_fail=1 state=healthy
  t=1 probe=0 consec_fail=2 state=healthy
  t=2 probe=0 consec_fail=3 state=unhealthy      ← 第 3 次失败才切换
  t=5 probe=1 consec_fail=0 consec_ok=2 state=healthy
  events=t2:became_unhealthy,t5:became_healthy
=== flap_never_trips probes=101010 failureThreshold=3 successThreshold=2 ===
  final_state=healthy                             ← 抖动永不触发
trip_at_failure_threshold=True
single_success_not_enough=True
```

### 🧑‍💻 程序员视角
- liveness 与 readiness 混用会引发雪崩：若把 liveness 探成「依赖数据库可用」的一次查询，数据库抖动 30 秒会让**所有**实例的 liveness 同时失败并集体重启，重启期间无法服务，抖动被放大成故障。正确做法：liveness 只探自身（如进程内定时器心跳），readiness 才探依赖。
- 慢启动服务用 `startupProbe`，而不是把 liveness 的 `initialDelaySeconds` 调得很大——后者会让「运行期真卡死」也被延迟发现。
- 告警设计三条：① 报**症状**（用户可感知的 SLO 违反）而不是**原因**（CPU 高不一定影响用户）；② 用多窗口多燃烧率（burn rate）平衡灵敏与噪音；③ 每条告警必须配 runbook，否则会被静音，静音等于没有告警。
- 黄金四信号：延迟（latency）、流量（traffic）、错误（errors）、饱和度（saturation）。容量规划看饱和度（连接池使用率、队列深度、磁盘水位），而不是等失败率上升。

### 🎓 博士生视角
- 滞回（hysteresis）的必要性：若用单一阈值（失败即不健康、成功即健康），噪声会让状态在两种状态间高频震荡，触发大量无意义的重启与流量摘挂。用不对称阈值（失败 N 次 / 成功 M 次）把状态机变成 **Schmitt 触发器**结构，代价是引入检测延迟。ex08 的 `flap_never_trips=True` 就是滞回的直接效果。
- 状态机视角下，探针的输出是「观测序列 → 状态序列」的确定性映射，其最长检测延迟可解析求出（≈ `failureThreshold × periodSeconds`）。把这段延迟与 SLO 的误差预算对齐，是「探针参数要不要调小」的正确决策依据，而不是凭感觉。
- 监控系统的成本由**时间序列基数**（cardinality）主导：把用户 id、请求 id 这类高基数字段放进标签，会让存储与查询成本随标签组合数爆炸。因此需要显式设计聚合维度，把「定位」交给 logs/traces 承担。
- 告警质量的度量是对称错误率：漏报（假阴性）导致事故扩大，误报（假阳性）导致告警疲劳进而人为忽略。工程上通过「多窗口燃烧率」把两者同时压住——短窗口快速发现、长窗口过滤瞬时抖动。

### 📚 考研者视角
- **监控本身不在 408 考纲内**，但相关考纲概念：**进程状态与状态转换**（就绪/运行/阻塞/终止的状态机，与探针状态机同构）、**进程调度与负载指标**、**死锁检测与恢复**（liveness 探针检测的正是「无法推进」这一死锁特征）。
- **口径**：`failureThreshold` 与 `successThreshold` 是**两个不同方向的阈值**，一个管降级、一个管恢复；把两者当同一个数会导致「退出不健康」与「进入不健康」的延迟不对称，进而出现「恢复了但流量迟迟不回来」。
- **易混点**：健康检查（health check，判断进程/服务是否可用）与就绪检查（readiness，判断是否该接收流量）语义不同；把两者混为一谈是面试高频失分点。再叠加「启动检查」共三种，职责各不相同。
- **面试考点**：liveness 与 readiness 的区别；探针参数怎么配；如何避免告警风暴；可观测性三支柱的分工。
