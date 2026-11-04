# -*- coding: utf-8 -*-
"""把「批次三」的 sandbox 模块写进 content/_handmade/labs.json 的 chapters。

背景
----
CppMind 的实验台数据管线是三层：

    作者源  content/_handmade/labs.json
      │      （手工精修的 sandbox / debug 模块，章节键 → 模块列表）
      ▼
    gen_interactive.py   ← 把自动抽取的 seq/match/boss/fill 与手工模块合并
      ▼
    产物    content/<学科>/<章>/interactive.json
            frontend/src/data/labs/<学科>.ts
            viz/interactive/src/data/index.ts

关键点：`gen_interactive.py` 每次运行都会**整份重写** interactive.json，只保留
它自己能生成的模块 + labs.json 里的手工模块。所以 sandbox 想活过重跑，就必须
落在 labs.json 里，不能直接手改 interactive.json（改了下次生成就没了）。

为什么单拿这三个章
------------------
tooling / middleware 整体偏「配置项、协议状态机」等定性内容，硬凑 sandbox 会
造出没有客观判据的假游戏。但这三章有真实可算的数值关系，值得做：

  tool-ch06  Docker 资源配额：副本数 × 单实例配额 vs 主机预算（含 headroom）
  mw-ch03    Redis 哨兵：quorum / 多数派 / min-replicas 的门槛关系
  mw-ch05    Kafka 积压：净速率 = 消费总速 − 生产速，再看清场是否进 SLA

设计约束（由 scripts/audit_handmade_labs.py 守门）
------------------------------------------------
1. 每章必须有解：存在某组参数让全部 checks 为真。
2. 默认参数**不能**开局通关，否则一进来就绿、没有可玩性。
3. 公式在两个求值器里必须都能算：
   - Python `audit_handmade_labs.ev`（守门 / 求解读）
   - TS    `frontend/src/components/lab/expr.ts` 的 evalExpr（运行时渲染）
   两边语法一致：数字 / 标识符 / 四则 / 幂 / 比较 / 逻辑 / 三元 / `if(c,a,b)`。
4. **除法要自己防零**：`if()` 在两个求值器里都是**急切求值**（两个分支都先算
   完再选），所以 `if(netRate > 0, backlog0 / netRate, -1)` 在 netRate==0 时
   仍然会抛 ZeroDivisionError。写法要保证除数恒非零，见 mw-ch05 的注释。

幂等性
------
脚本用章节键直接赋值，重复运行结果一致；不触动 labs.json 里其它条目。
写盘强制 indent=1 + newline="\\n"——与仓库现有风格一致（indent=2 或 CRLF
都会让整份文件产生几千行假 diff）。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# tool-ch06 · Docker Compose 部署：容器资源配额
# ----------------------------------------------------------------------------
# 教学点：配额要看「总账」而不是单实例。svcCount × cpuPerSvc 才是集群真实需求；
# 且必须预留 headroom（默认 10%）给突发流量与系统进程，否则调度能成功、
# 运行时照样 OOMKill / 被 CPU throttle。
# 可玩性：默认 8 副本 × 1 核 = 8 核，正好顶满 8 核预算 → 第一条判据过、
# 第二条内存 8192MB 也顶满 → 但第三条“预留 ≥10%”让预算缩到 7.2 核 / 7372MB，
# 于是默认必然爆掉，玩家必须降副本或降配额。
# ============================================================================
tool_ch06 = {
    "kind": "sandbox",
    "title": "容器配额算总账：副本一多就爆",
    "brief": (
        "单实例看着小，副本数一上去 CPU/内存总需求就超主机预算。"
        "配额必须留 headroom 给突发与系统开销，否则调度成功也会运行时 OOMKill / CPU 被 throttle。"
        "拖副本数、单实例配额与主机预算，把总需求压进预算内。"
    ),
    # params：全部是连续 range（3 个离散概念都能用连续数表达，不必做分段按钮）
    "params": [
        # 副本数：1~10。默认 8，是“看起来合理、其实快顶满”的陷阱值
        {"key": "svcCount", "label": "服务副本数", "min": 1, "max": 10, "step": 1, "value": 8},
        # 单实例 CPU 上限（docker run --cpus）。默认 1.0 核
        {"key": "cpuPerSvc", "label": "单实例 CPU 上限", "min": 0.1, "max": 2.0, "step": 0.1, "value": 1.0, "unit": "核"},
        # 单实例内存上限（--memory）。默认 1024MB
        {"key": "memPerSvc", "label": "单实例内存上限", "min": 128, "max": 2048, "step": 128, "value": 1024, "unit": "MB"},
        # 主机 CPU 总核数。默认 8 核
        {"key": "hostCPU", "label": "主机 CPU 预算", "min": 4, "max": 16, "step": 4, "value": 8, "unit": "核"},
        # 主机内存总量。默认 8GB
        {"key": "hostMem", "label": "主机内存预算", "min": 4096, "max": 16384, "step": 4096, "value": 8192, "unit": "MB"},
        # 预留缓冲比例：0~30%，默认 10%。这是本章最容易忽略的一项
        {"key": "reserveFrac", "label": "预留缓冲比例", "min": 0.0, "max": 0.3, "step": 0.05, "value": 0.1},
    ],
    # metrics 按顺序求值，后面的公式可以引用前面的 key
    "metrics": [
        # 总需求 = 单实例 × 副本数（线性，这正是“配额要看总账”的来源）
        {"key": "needCPU", "label": "CPU 总需求", "expr": "cpuPerSvc * svcCount", "unit": "核", "fmt": "fix2"},
        {"key": "needMem", "label": "内存总需求", "expr": "memPerSvc * svcCount", "unit": "MB", "fmt": "int"},
        # 可用预算 = 总额 × (1 − 预留比例)。留 10% 时 8 核只剩 7.2 核可用
        {"key": "budgetCPU", "label": "CPU 可用预算", "expr": "hostCPU * (1 - reserveFrac)", "unit": "核", "fmt": "fix2"},
        {"key": "budgetMem", "label": "内存可用预算", "expr": "hostMem * (1 - reserveFrac)", "unit": "MB", "fmt": "int"},
    ],
    # checks：全部为真才算通关（求值结果 == 0 视为未通过）
    "checks": [
        {"expr": "needCPU <= budgetCPU", "label": "CPU 总需求不超预算（含预留缓冲）"},
        {"expr": "needMem <= budgetMem", "label": "内存总需求不超预算（含预留缓冲）"},
        # 这条单独卡住“把预留比例调成 0 来骗过前两条”的投机解法
        {"expr": "reserveFrac >= 0.1", "label": "预留 ≥10% 缓冲，避免突发 OOM"},
        # 下面两条是“别把旋钮全拉到最小”的下限约束：
        #   副本 <3 就没有冗余，单点挂了整服务不可用；
        #   内存 <512MB 起不来典型 JVM / 中间件进程。
        # 有了它们，唯一解法变成“降 CPU 配额或加主机核数”，而不是无脑最小值。
        {"expr": "svcCount >= 3", "label": "至少 3 副本（单点挂掉服务仍可用）"},
        {"expr": "memPerSvc >= 512", "label": "单实例内存 ≥512MB（容得下运行时）"},
        # 主机规格是既定事实、不是可调项：把 hostCPU/hostMem 拉到最小再“刚好装下”
        # 等于自己编了一台机器。要求主机规格在合理区间内，逼你在真实机器上做配额规划。
        {"expr": "hostCPU >= 8", "label": "主机 ≥8 核（配额要按真实规格算，别缩机器）"},
        {"expr": "hostMem >= 8192", "label": "主机内存 ≥8GB（同上）"},
        # 配额压到 0.1 核等于把服务饿死：真实 Web 服务给 0.1 核连健康检查都超时。
        # 这条逼玩家去“加副本冗余”和“加主机”之间抉择，而不是无脑压小。
        {"expr": "cpuPerSvc >= 0.5", "label": "单实例 CPU ≥0.5 核（再小服务跑不动）"},
    ],
    "insight": (
        "配额要算总账：单实例看着小，副本一多总需求就线性上涨。"
        "且必须留 headroom（通常 10%~20%）给突发流量与系统进程开销——"
        "否则即使调度器允许部署，运行时也会被 OOMKill 或 CPU throttle。"
        "docker run 的 --cpus / --memory 是硬上限，超了直接被杀而非变慢。"
    ),
}


# ============================================================================
# mw-ch03 · Redis 高可用：哨兵判定与主从切换
# ----------------------------------------------------------------------------
# 教学点（本章第一考点，最容易记反的三件事）：
#   1. quorum 是「确认 SDOWN 的哨兵数门槛」，用于达成 ODOWN，**不是**多数派；
#   2. 真正执行故障转移的 leader 选举才需要 >N/2 多数派；
#   3. min-replicas-to-write 让主库在健康从节点不足时**拒绝写入**，防脑裂丢数据。
# 另外复制延迟直接影响切过去会不会丢近窗数据。
# 可玩性：默认 sentinelsDown=2 → 只剩 1 个哨兵，quorum=3 → 达不成 ODOWN；
# 且 minReplicas=0 让“健康从节点不足也照写”，延迟 20s 也超阈值。
# 三处都得调对才能同时满足，凑解的过程正好把三个知识点各走一遍。
# ============================================================================
mw_ch03 = {
    "kind": "sandbox",
    "title": "哨兵怎么判定该切主",
    "brief": (
        "哨兵的 quorum 是「确认 SDOWN 的哨兵数门槛」，要达成 ODOWN 需存活哨兵数 ≥ quorum；"
        "真正执行转移还需 >N/2 多数派。min-replicas-to-write 让主库在健康从节点过少时拒绝写入以防脑裂丢数据。"
        "拖存活守卫、quorum、复制延迟与从节点数，凑出一次安全切换。"
    ),
    "params": [
        # 主从复制延迟（秒）。>10s 视为不安全：切过去会丢近窗数据
        {"key": "replLag", "label": "主从复制延迟", "min": 0, "max": 30, "step": 1, "value": 20, "unit": "s"},
        # ODOWN 确认门槛。默认 3 = 必须三个哨兵全同意，是最严但最脆的配置
        {"key": "quorum", "label": "ODOWN 确认门槛 quorum", "min": 1, "max": 3, "step": 1, "value": 3},
        # 已宕哨兵数（集群共 3 个）。默认 2，只剩 1 个活着
        {"key": "sentinelsDown", "label": "已宕哨兵数（共3）", "min": 0, "max": 3, "step": 1, "value": 2},
        # min-replicas-to-write：主库要求的最少健康从节点数。默认 0 = 不设防
        {"key": "minReplicas", "label": "min-replicas-to-write", "min": 0, "max": 2, "step": 1, "value": 0},
        # 当前健康从节点数
        {"key": "healthyReplicas", "label": "健康从节点数", "min": 0, "max": 2, "step": 1, "value": 1},
    ],
    "metrics": [
        # 存活哨兵数 = 总数 3 − 已宕数
        {"key": "availSent", "label": "存活哨兵数", "expr": "3 - sentinelsDown", "unit": "个", "fmt": "int"},
        # 能否达成 ODOWN：存活数 ≥ quorum 即可（注意这里**不是**多数派）
        {"key": "odown", "label": "能否达成 ODOWN", "expr": "if(availSent >= quorum, 1, 0)", "fmt": "int"},
        # 主库能否写入：健康从节点数 ≥ min-replicas-to-write
        {"key": "canWrite", "label": "主库能否写入", "expr": "if(healthyReplicas >= minReplicas, 1, 0)", "fmt": "int"},
        # 复制延迟是否在安全线内（≤10s）
        {"key": "lagSafe", "label": "复制延迟是否安全", "expr": "if(replLag <= 10, 1, 0)", "fmt": "int"},
    ],
    "checks": [
        {"expr": "odown == 1", "label": "存活哨兵数 ≥ quorum，能达成 ODOWN 触发转移"},
        {"expr": "canWrite == 1", "label": "健康从节点 ≥ min-replicas-to-write，主库允许写入"},
        {"expr": "lagSafe == 1", "label": "复制延迟 ≤ 10s，从节点数据较新"},
        # 下限约束：quorum=1 等于“任一哨兵说了就算”，是生产事故配置；
        # min-replicas=0 等于不设脑裂防线。两条一起逼玩家做出“真的安全”的配置，
        # 而不是把旋钮全拉到最小值。
        {"expr": "quorum >= 2", "label": "quorum ≥2（单个哨兵误判不足以触发下线）"},
        {"expr": "minReplicas >= 1", "label": "min-replicas ≥1（至少一个健康从节点才允许写，防脑裂）"},
    ],
    "insight": (
        "哨兵的 quorum 只是「确认下线的哨兵数门槛」，用于达成 ODOWN，不要求多数派、"
        "通常小于哨兵总数；真正执行故障转移的 leader 选举才需要 >N/2 多数派，二者独立配置。"
        "min-replicas-to-write 是主库在健康从节点不足时拒绝写入——宁可停写也不在脑裂里丢数据。"
        "复制延迟过大时切过去会丢近窗数据，所以延迟也要压进阈值。"
    ),
}


# ============================================================================
# mw-ch05 · Kafka：消息积压能不能在 SLA 内清掉
# ----------------------------------------------------------------------------
# 教学点：积压治理看「净速率 = 消费总速 − 生产速」。
#   - 净速率 ≤ 0：积压永远涨，加消费者也只是把涨速变慢；
#   - 净速率 > 0：清场时间 = 初始积压 / 净速率，还要压进 SLA 才算真解决。
# 默认消费者只有 1 个（500 条/s）却在 3000 条/s 生产 → 净速率 −2500，必挂。
# 把消费者加到 6 个（3000）也只是打平；要 7 个以上（3500）才有 500/s 净消化，
# 清 500000 条需 1000s，仍然超 120s 的 SLA → 必须同时砍初始积压或抬 slaSec。
#
# ⚠️ 除零陷阱（这条注释是本章最重要的实现细节）
#   两套求值器里的 if(c, a, b) 都是**急切求值**：a、b 两个分支都会先算完。
#   所以写成 if(netRate > 0, backlog0 / netRate, -1) 时，只要 netRate == 0，
#   那个除法照样执行 → ZeroDivisionError（审计里显示为空消息的“求值失败”）。
#   解法：给除数加一个“仅在 ≤0 时生效”的兜底，保证除数恒 ≥1：
#       backlog0 / (netRate + if(netRate > 0, 0, 1))
#   netRate > 0 时除数是 netRate 本身；netRate ≤ 0 时除数是 netRate+1（≥1，安全）。
# ============================================================================
mw_ch05 = {
    "kind": "sandbox",
    "title": "积压能不能在 SLA 内清掉",
    "brief": (
        "积压清理看净速率 = 消费总速 − 生产速。消费总速 = 单消费者速率 × 消费者数。"
        "净速率转正积压才下降；再拿初始积压除以净速率看清场时间是否压进 SLA。"
        "拖生产/消费速率、消费者数与 SLA。"
    ),
    "params": [
        # 生产速率：默认 3000 条/s，是一个“消费端明显跟不上”的典型线上值
        {"key": "prodRate", "label": "生产速率", "min": 100, "max": 5000, "step": 100, "value": 3000, "unit": "条/s"},
        # 单消费者速率：默认 500 条/s
        {"key": "consRate", "label": "单消费者速率", "min": 100, "max": 3000, "step": 100, "value": 500, "unit": "条/s"},
        # 消费者数：默认 1，这是积压的根因
        {"key": "consumers", "label": "消费者数", "min": 1, "max": 10, "step": 1, "value": 1},
        # 初始积压：默认 50 万条
        {"key": "backlog0", "label": "初始积压", "min": 0, "max": 1000000, "step": 50000, "value": 500000, "unit": "条"},
        # 清场 SLA：默认 120s，是「两分钟必须清完」的运营口径
        {"key": "slaSec", "label": "清场 SLA", "min": 30, "max": 600, "step": 30, "value": 120, "unit": "s"},
    ],
    "metrics": [
        # 消费总速率（本沙盒按“加消费者线性提升”简化，真实受分区数上限约束）
        {"key": "totalCons", "label": "消费总速率", "expr": "consRate * consumers", "unit": "条/s", "fmt": "int"},
        # 净消化速率：正数才在下降，负数表示越积越多
        {"key": "netRate", "label": "净消化速率", "expr": "consRate * consumers - prodRate", "unit": "条/s", "fmt": "int"},
        # 积压是否仍在涨（netRate < 0 → 1）
        {"key": "backlogGrows", "label": "积压是否仍在涨", "expr": "if(netRate < 0, 1, 0)", "fmt": "int"},
        # 预计清场时间：净速率 ≤0 时无意义，返回 -1。除数做了防零处理（见上方注释）
        {"key": "drainTime", "label": "预计清场时间",
         "expr": "if(netRate > 0, backlog0 / (netRate + if(netRate > 0, 0, 1)), -1)",
         "unit": "s", "fmt": "fix2"},
        # 是否在 SLA 内清场：既要净速率为正，又要清场时间 ≤ SLA
        {"key": "meetsSLA", "label": "是否在 SLA 内清场",
         "expr": "if(netRate > 0, if(backlog0 / (netRate + if(netRate > 0, 0, 1)) <= slaSec, 1, 0), 0)",
         "fmt": "int"},
    ],
    "checks": [
        {"expr": "netRate > 0", "label": "消费总速率 > 生产速率，积压开始下降"},
        {"expr": "backlogGrows == 0", "label": "积压不再增长（净速率非负）"},
        {"expr": "meetsSLA == 1", "label": "在 SLA 内清空积压（加消费者/提速消费）"},
        # 下限约束：初始积压清零（backlog0=0）等于没有积压，绕过了“清理”这件事本身；
        # 单个消费者在生产速率面前毫无冗余；
        # prodRate 也不是你能调的——线上生产速率由业务决定，调低它属于作弊，
        # 所以要求它 ≥1000 条/s，逼你在“真实流量”下做容量规划。
        {"expr": "backlog0 >= 100000", "label": "初始积压 ≥10 万条（要面对真实积压）"},
        {"expr": "consumers >= 2", "label": "至少 2 个消费者（无单点，且能并行消费分区）"},
        {"expr": "prodRate >= 1000", "label": "生产速率 ≥1000 条/s（生产不受你控制，别靠降流量通关）"},
    ],
    "insight": (
        "积压治理看「净速率 = 消费总速 − 生产速」。加消费者线性提总速，但受分区数上限约束"
        "（本沙盒简化为线性）；真问题常是消费逻辑慢或分区太少，光加人可以缓解但不是根治。"
        "netRate>0 只是不涨，要清空还得看 backlog0/netRate 是否压进 SLA——"
        "积压越大、SLA 越紧，越要提前扩容。"
    ),
}


# ---------------------------------------------------------------------------
# 落盘：按章节键写入 labs.json 的 chapters
# ---------------------------------------------------------------------------
def main() -> int:
    """读取 labs.json → 写入三个 sandbox 条目 → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    # 章节键必须与目录 <学科>/<章> 完全一致，否则 gen_interactive.py 会警告
    # “精修表里指向不存在的章节”，且模块不会进入任何 interactive.json
    for key, mod in (
        ("tooling/tool-ch06", tool_ch06),
        ("middleware/mw-ch03", mw_ch03),
        ("middleware/mw-ch05", mw_ch05),
    ):
        # 覆盖写：保证脚本幂等（重复运行结果一致，不会叠加出两份）
        chapters[key] = [mod]
        print(f"added {key}  ({len(mod['params'])} params / {len(mod['checks'])} checks)")

    # indent=1 + newline="\n"：与仓库现有风格逐字节一致
    # （用 indent=2 或让 Python 自己翻 CRLF，都会让整份文件产生几千行假 diff）
    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
