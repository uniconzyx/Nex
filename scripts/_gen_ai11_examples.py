"""ai-ch11 示例代码生成前的实跑脚本：每个 demo 单独跑，取其真实 stdout。

用法：python scripts/_gen_ai11_examples.py
产出：scripts/_ai11_out/ex01.txt ... ex10.txt（真实输出，供脚本读回写 JSON）
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "_ai11_out"
OUT.mkdir(exist_ok=True)

DEMOS: dict[str, str] = {}

# ---------------------------------------------------------------- ex01
DEMOS["ex01"] = '''"""批处理耗时曲线：固定开销 + 每样本线性项，看摊销效果。"""

def batch_latency_ms(n):
    return 20 + 2.5 * n          # 20ms 固定开销 + 每样本 2.5ms

print("批大小 | 总耗时ms | 每样本ms | 固定开销占比")
print("------|---------|---------|------------")
for n in (1, 2, 4, 8, 16, 32, 64, 128):
    total = batch_latency_ms(n)
    per = total / n
    overhead = 20 / total * 100
    print("%5d | %7.1f | %7.2f | %10.1f%%" % (n, total, per, overhead))

# 吞吐：每秒能完成多少样本
print()
print("批大小 | 吞吐(样本/s)")
print("------|-----------")
for n in (1, 8, 32, 128):
    print("%5d | %9.1f" % (n, 1000.0 / batch_latency_ms(n) * n))

# 边际收益：每增加一倍批大小，每样本耗时下降多少
print()
prev = None
for n in (1, 2, 4, 8, 16, 32, 64, 128):
    per = batch_latency_ms(n) / n
    if prev is not None:
        drop = (prev - per) / prev * 100
        print("批 %3d -> %3d: 每样本耗时再降 %5.1f%%" % (n // 2, n, drop))
    prev = per
'''

# ---------------------------------------------------------------- ex02
DEMOS["ex02"] = '''"""动态批处理模拟：max_batch 与 max_wait 的交互。

到达过程用泊松分布（指数间隔），服务时间为 20 + 2.5n 毫秒。
不依赖任何外部库，固定随机种子保证可复现。
"""
import random


def batch_latency_ms(n):
    return 20 + 2.5 * n


def simulate(arrival_rate, max_batch, max_wait_ms, duration_s=20.0, seed=42):
    """按「批」推进的离散事件模拟。

    真实 batching 的时序是：
      1. 批在 t0 打开，开始收请求；
      2. 收满 max_batch 个，或持续到 max_wait_ms 仍不满 —— 任一先发生就「关批」；
      3. 关批后开始计算，耗时 20+2.5n 毫秒；
      4. 计算完成，下一批按「请求已到 + 服务空闲」的时刻打开。

    注意关批条件用的是「打开时刻 + max_wait」，不涉及计算耗时——
    这是所有推理引擎的真实行为（先凑批，再算）。
    """
    rng = random.Random(seed)
    arrivals, t = [], 0.0
    while True:
        t += rng.expovariate(arrival_rate)
        if t >= duration_s:
            break
        arrivals.append(t)

    latencies, batches = [], 0
    free_at = 0.0
    i = 0
    while i < len(arrivals):
        start = max(arrivals[i], free_at)       # 批打开的时刻
        close = start + max_wait_ms / 1000.0    # 关批截止时刻
        k = i
        while k < len(arrivals) and (k - i) < max_batch and arrivals[k] <= close:
            k += 1
        n = k - i
        # 计算起点 = 这一批「关批」的时刻。关批有两种触发：
        #   a) 收满 max_batch 个 -> 第 max_batch 个请求到达时立即关批（不等满窗口）
        #   b) 窗口到期仍不满  -> 关批时刻就是 close
        # 用 max(..., arrivals[k-1]) 兜住 a)，保证 finish 不早于批内任何请求的到达时刻。
        close_at = arrivals[k - 1] if n == max_batch else close
        finish = close_at + batch_latency_ms(n) / 1000.0
        for m in range(i, k):
            latencies.append((finish - arrivals[m]) * 1000.0)
        i, free_at = k, finish
        batches += 1

    # 物理约束自检：任何请求的延迟都必须非负
    assert all(v >= 0 for v in latencies), "出现负延迟，模拟逻辑有误"

    latencies.sort()
    total = len(latencies)
    return {
        "arrivals": len(arrivals),
        "batches": batches,
        "avg_batch": total / batches if batches else 0,
        "p50": latencies[total // 2] if total else 0,
        "p99": latencies[min(total - 1, int(total * 0.99))] if total else 0,
    }


print("到达率 | max_batch | max_wait | 请求数 | 批数 | 均批 | P50ms | P99ms")
print("------|-----------|----------|-------|------|------|-------|------")
for rate, mb, mw in (
    (20, 8, 50),
    (20, 64, 200),
    (20, 8, 500),
    (60, 8, 50),
    (60, 32, 100),
    (60, 64, 300),
):
    r = simulate(rate, mb, mw)
    print("%5d | %9d | %6dms | %5d | %4d | %4.1f | %5.0f | %5.0f"
          % (rate, mb, mw, r["arrivals"], r["batches"], r["avg_batch"], r["p50"], r["p99"]))

print()
print("读法（对照上表）：")
print("  · 20/s + 等待 50ms  -> 均批 2.1，P50 73ms。批很浅，满窗口就发出去了")
print("  · 20/s + 等待 500ms -> 均批 7.5，P50 210ms。批更满了，但每个请求都多等 130ms")
print("    低负载时等待窗口的收益全被「白白等待」吃掉：批数从 175 减到 49，")
print("    看着省了算力，代价是所有人的延迟翻三倍。")
print("  · 60/s + 批上限 8   -> 均批 4.8，P50 72ms。吞不下，靠高频发批硬扛")
print("  · 60/s + 批上限 64 + 等待 300ms -> 均批 21.6，P50 265ms")
print("    高负载下大窗口才划算：同样处理 1167 个请求，批数从 241 降到 54。")
print()
print("结论：等待窗口的性价比取决于负载。低负载应调小（少等），"
      "高负载应调大（多凑）。静态配置只能取折中，")
print("所以成熟服务会让 max_wait 随队列深度自适应：队列越深，越值得等。")
'''

# ---------------------------------------------------------------- ex03
DEMOS["ex03"] = '''"""延迟预算倒推 max_wait：给定 SLO 与模型耗时，算等待窗口与可用批大小。"""

BATCH_MODEL = lambda n: 20 + 2.5 * n


def max_batch_within(budget_ms):
    """在给定「计算耗时」预算内，最多能处理多少个样本。"""
    n = 1
    while BATCH_MODEL(n + 1) <= budget_ms:
        n += 1
    return n


def plan(slo_p99_ms, framework_overhead_ms=50, network_ms=30):
    print("SLO P99 = %dms" % slo_p99_ms)
    print("  扣除框架开销 %dms、网络 %dms -> 可用计算+排队 %.0fms"
          % (framework_overhead_ms, network_ms,
             slo_p99_ms - framework_overhead_ms - network_ms))
    # 先用一半预算给计算，一半给排队/凑批
    for share in (0.5, 0.6, 0.7):
        compute = (slo_p99_ms - framework_overhead_ms - network_ms) * share
        wait = (slo_p99_ms - framework_overhead_ms - network_ms) - compute
        n = max_batch_within(compute)
        throughput = n / (compute / 1000.0)
        print("    计算占 %.0f%%: 计算 %.0fms(批<=%d) 等待 %.0fms -> 单副本吞吐 %.1f 样本/s"
              % (share * 100, compute, n, wait, throughput))
    print()


for slo in (500, 200, 1000):
    plan(slo)

print("结论：SLO 越紧，能用的批越小、等待窗口越窄，单副本吞吐越低，"
      "需要的副本数越多。")
print("SLO=100ms 时，扣除固定开销后几乎没有空间凑批，只能加副本或换更小模型。")
'''

# ---------------------------------------------------------------- ex04
DEMOS["ex04"] = '''"""输入契约校验：形状/数值/长度/编码/白名单五类，逐条给出拒绝原因。"""
import json
import math


class BadInput(ValueError):
    pass


def validate_vector(x, *, dim, name="x"):
    if not isinstance(x, (list, tuple)):
        raise BadInput("%s 必须是数组，收到 %s" % (name, type(x).__name__))
    if dim <= 0:
        # 模型要的维度本身就不该是 0：空序列会让下游 zip(*[]) 静默返回 []
        raise BadInput("%s 的目标维度必须 >= 1，收到 %d" % (name, dim))
    if len(x) != dim:
        raise BadInput("%s 维度应为 %d，收到 %d" % (name, dim, len(x)))
    out = []
    for i, v in enumerate(x):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise BadInput("%s[%d] 必须是数值，收到 %s" % (name, i, type(v).__name__))
        f = float(v)
        if not math.isfinite(f):
            raise BadInput("%s[%d] 为 %r，非有限值" % (name, i, f))
        out.append(f)
    return out


LABELS = ("positive", "neutral", "negative")


def validate_label(s):
    if s not in LABELS:
        raise BadInput("未知类别 %r，允许 %s" % (s, LABELS))
    return s


CASES = [
    ("正常", lambda: validate_vector([0.1, 0.2, 0.3], dim=3)),
    ("长度不对", lambda: validate_vector([0.1, 0.2], dim=3)),
    ("不是数组", lambda: validate_vector("0.1,0.2,0.3", dim=3)),
    ("含 NaN", lambda: validate_vector([0.1, float("nan"), 0.3], dim=3)),
    ("含 inf", lambda: validate_vector([0.1, float("inf"), 0.3], dim=3)),
    ("布尔混入", lambda: validate_vector([0.1, True, 0.3], dim=3)),
    ("空序列", lambda: validate_vector([], dim=0)),
    ("空序列但目标维度=3", lambda: validate_vector([], dim=3)),
    ("合法类别", lambda: validate_label("neutral")),
    ("未知类别", lambda: validate_label("happy")),
]

for name, fn in CASES:
    try:
        r = fn()
        print("[PASS] %-10s -> %r" % (name, r))
    except BadInput as e:
        print("[400 ] %-10s -> %s" % (name, e))

# NaN 的三条反直觉性质
nan = float("nan")
print()
print("NaN 性质:")
print("  nan == nan      ->", nan == nan)
print("  nan != nan      ->", nan != nan)
print("  isfinite(nan)   ->", math.isfinite(nan))
print("  str(nan) 含 'nan' ->", "nan" in str(nan))
print("  json.dumps 结果 ->", json.dumps({"v": nan}))
'''

# ---------------------------------------------------------------- ex05
DEMOS["ex05"] = '''"""NaN 静默传播：一次 NaN 如何污染整条推理链路，以及拦截点在哪。"""
import math


def softmax(xs):
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


def linear(x, w, b):
    return [sum(xi * wi for xi, wi in zip(row, w)) + bb for row, bb in zip([x], b)]


def batch_softmax(rows):
    return [softmax(r) for r in rows]


base = [
    [1.0, 2.0, 0.5],
    [0.0, 1.0, 3.0],
    [2.0, 0.0, 1.0],
]

print("干净输入:")
for r in batch_softmax(base):
    print("  ", [round(v, 4) for v in r])

print()
print("混入一个 NaN 后:")
dirty = [row[:] for row in base]
dirty[1][2] = float("nan")
for i, r in enumerate(batch_softmax(dirty)):
    print("   批内第 %d 条 ->" % i, r)

print()
print("观察：NaN 只污染它所在的那一条，同批其它两条仍正常。")
print("但若下游对整个批做 sum/mean，整批结果都会变成 nan：")
tot = sum(sum(r) for r in batch_softmax(dirty))
print("   整批求和 ->", tot)
print("   整批均值 ->", tot / 3)

print()
print("拦截点对比:")
print("  1) 入口 isfinite 检查 -> 该请求返回 400，同批其它请求不受影响")
print("  2) 不拦 -> 该请求返回 nan，若下游有聚合则整批污染")
print()
print("工程结论：批内逐请求 try/except + 入口 isfinite，两层都要有。")
'''

# ---------------------------------------------------------------- ex06
DEMOS["ex06"] = '''"""容量规划：从 QPS 与 SLO 反推副本数与显存。"""
import math


def batch_latency_ms(n):
    return 20 + 2.5 * n


def max_batch_within(budget_ms):
    n = 1
    while batch_latency_ms(n + 1) <= budget_ms:
        n += 1
    return n


def plan(qps, slo_p99_ms, fixed_overhead_ms=80, weight_mb=1400, kv_per_req_mb=180,
         max_batch_hw=64):
    """按 SLO 反推：可用批大小、单副本吞吐、副本数、显存。

    真实约束有两条，必须同时满足：
      a) 单批耗时 <= SLO 余量（否则一个请求从进批到出结果就超时了）
      b) 批大小 <= 硬件/显存允许的上限（KV Cache 线性占显存）
    少了 b)，算出来的批会是几百，显存直接爆掉——这是纯按延迟反推的经典陷阱。
    """
    compute_budget = slo_p99_ms - fixed_overhead_ms
    n_by_latency = max_batch_within(compute_budget)
    n = min(n_by_latency, max_batch_hw)
    per_batch_s = batch_latency_ms(n) / 1000.0
    per_replica = n / per_batch_s
    raw_replicas = qps / per_replica
    replicas = math.ceil(raw_replicas)
    vram = weight_mb + n * kv_per_req_mb
    print("QPS=%-5g SLO P99=%-5dms" % (qps, slo_p99_ms))
    print("  延迟允许批 %d，硬件上限 %d -> 实际批 %d（单批 %.0fms）"
          % (n_by_latency, max_batch_hw, n, batch_latency_ms(n)))
    print("  单副本吞吐 %.0f 请求/s，需要 %.1f 副本 -> 取 %d 副本（含 1 冗余 = %d）"
          % (per_replica, raw_replicas, replicas, replicas + 1))
    print("  单副本显存 = %dMB 权重 + %d x %dMB KV = %.1f GB"
          % (weight_mb, n, kv_per_req_mb, vram / 1024))
    print("  集群总显存 = %d 副本 x %.1f GB = %.1f GB"
          % (replicas + 1, vram / 1024, (replicas + 1) * vram / 1024))
    print()


for qps in (200, 800, 2000):
    for slo in (1000, 500, 200):
        plan(qps, slo)

print("读法（三个关键对比）：")
print("  · 同一 QPS 下 SLO 从 1000ms 收到 200ms：延迟允许的批从 360 掉到 40。")
print("    1000/500ms 两档都被硬件上限 64 卡住，说明「延迟不是唯一约束，显存才是」。")
print("  · 批被卡在 64 时单副本吞吐约 356/s，这是硬件天花板；")
print("    2000 QPS 需要 6 副本，800 QPS 需要 3 副本——副本数与 QPS 近似线性。")
print("  · SLO 200ms 档：批只有 40，显存最省（8.4GB）但吞吐 333/s 最低，")
print("    同样的 QPS 要多配副本。省显存和省副本不可兼得。")
print("结论：批大小 = min(延迟允许, 硬件允许)。只看延迟会算出爆显存的天真方案；")
print("只看硬件会算出必超时的方案。两个都要算，取小。")
'''

# ---------------------------------------------------------------- ex07
DEMOS["ex07"] = '''"""超时重试与退避抖动：对比「无抖动」与「有抖动」的重试时刻分布。"""
import random


def retry_times(attempts=4, base=0.05, jitter=False, n_clients=200, seed=7):
    """模拟 n_clients 个客户端同时超时后的重试时刻（秒）。"""
    rng = random.Random(seed)
    stamps = []
    for _ in range(n_clients):
        t = 0.0
        for a in range(attempts):
            d = base * (2 ** a)
            if jitter:
                d *= (0.5 + rng.random())
            t += d
            stamps.append(t)
    return stamps


def report(name, stamps, bucket=0.01):
    """按 10ms 分桶，统计每桶有多少次重试。"""
    import collections
    c = collections.Counter(round(s / bucket) for s in stamps)
    peak_bucket, peak_n = c.most_common(1)[0]
    occupied = len(c)
    total = len(stamps)
    print("%s:" % name)
    print("  重试总次数 %d，落在 %d 个时间桶内（桶宽 %.0fms）" % (total, occupied, bucket * 1000))
    print("  最挤的一桶：%.0fms 处有 %d 次（占 %.0f%%）"
          % (peak_bucket * bucket * 1000, peak_n, peak_n / total * 100))
    # 打印前 6 个桶
    top = sorted(c.items())[:8]
    print("  前 8 桶分布:", ", ".join("%.0fms:%d" % (k * bucket * 1000, v) for k, v in top))
    print()


report("无抖动（固定退避）", retry_times(jitter=False))
report("有抖动（0.5~1.5 倍随机）", retry_times(jitter=True))

print("结论：无抖动时所有客户端在同一毫秒重试，形成尖峰；")
print("有抖动时重试被摊开到整个窗口，服务端压力被平滑。")
print("峰值占比就是「重试风暴」的定量指标：越接近 100% 越危险。")
'''

# ---------------------------------------------------------------- ex08
DEMOS["ex08"] = '''"""降级策略矩阵：三种故障 x 三种降级，算出用户看到的结果与代价。"""

POLICIES = {
    "fail_fast":     {"name": "直接报错", "ok_rate": 0.0, "quality": None, "msg": "服务繁忙，请稍后再试"},
    "small_model":   {"name": "降级小模型", "ok_rate": 1.0, "quality": 0.62, "msg": "（简化回答）"},
    "cached_answer": {"name": "返回缓存", "ok_rate": 1.0, "quality": 0.41, "msg": "（历史相似答案）"},
}

# 业务场景对「答非所问」的容忍度：0 = 完全不能接受，1 = 无所谓
SCENARIOS = {
    "闲聊助手":   0.9,
    "代码补全":   0.7,
    "知识问答":   0.5,
    "客服售后":   0.25,
    "医疗咨询":   0.05,
}

# 正常服务的质量基线
BASELINE_QUALITY = 0.85

print("%-12s %-12s %-8s %-8s %-8s %s" % ("场景", "策略", "成功率", "相对质量", "净收益", "判定"))
print("-" * 74)
for scen, tolerance in SCENARIOS.items():
    for key, p in POLICIES.items():
        if p["quality"] is None:
            # 直接报错：拿到明确失败，用户可重试；不算「低质回答」
            benefit = 0.0
            verdict = "可接受" if tolerance < 0.6 else "偏保守"
        else:
            relative = p["quality"] / BASELINE_QUALITY
            # 净收益：有结果的收益 × 场景容忍度 - 低质回答的风险
            benefit = p["ok_rate"] * tolerance - (1 - relative)
            verdict = "可接受" if benefit >= 0 else "不可接受"
        print("%-12s %-12s %-8.1f %-8s %-8.2f %s"
              % (scen, p["name"], p["ok_rate"],
                 "n/a" if p["quality"] is None else "%.2f" % (p["quality"] / BASELINE_QUALITY),
                 benefit, verdict))
    print()

print("读法：容忍度高的场景（闲聊）降级有利；容忍度低的场景（医疗）任何降级都不可接受，")
print("只有 fail_fast 是负责任的默认。所以降级策略必须按场景配置，不能全局统一。")
'''

# ---------------------------------------------------------------- ex09
DEMOS["ex09"] = '''"""模型版本命名与回滚检测：从文件名解析出版本，找出被同名覆盖的权重。"""
import hashlib
import os
import re

NAME_RE = re.compile(r"^(?P<model>[a-z0-9-]+)-v(?P<ver>\\d+)-(?P<date>\\d{8})-(?P<hash>[0-9a-f]{6})\\.(?P<ext>\\w+)$")


def parse(fn):
    m = NAME_RE.match(fn)
    if not m:
        return None
    d = m.groupdict()
    d["ver"] = int(d["ver"])
    return d


FILES = [
    "intent-clf-v1-20260901-a1b2c3.safetensors",
    "intent-clf-v2-20261010-d4e5f6.safetensors",
    "intent-clf-v3-20261028-9a8b7c.safetensors",
    "intent-clf-v3-20261028-1f2e3d.safetensors",   # 同版本同日不同哈希 -> 覆盖风险
    "intent-clf-v2-20261010-000000.pt",
    "model.safetensors",                            # 无版本，无法追溯
    "intent-clf-v10-20261101-abcdef.safetensors",   # 两位数版本，测试排序
]

parsed = []
print("文件名解析:")
for f in FILES:
    d = parse(f)
    if d is None:
        print("  [WARN] %-42s 命名不合规，无法追溯" % f)
    else:
        print("  [OK  ] %-42s model=%-11s v%-2d %s hash=%s"
              % (f, d["model"], d["ver"], d["date"], d["hash"]))
        parsed.append((f, d))

print()
print("冲突检测（同 model 同 ver 同 date 但 hash 不同）:")
buckets = {}
for f, d in parsed:
    key = (d["model"], d["ver"], d["date"])
    buckets.setdefault(key, []).append((f, d["hash"]))
found = False
for key, items in sorted(buckets.items()):
    if len(items) > 1:
        found = True
        print("  [冲突] %s v%d %s 有 %d 个不同哈希: %s"
              % (key[0], key[1], key[2], len(items), [h for _, h in items]))
if not found:
    print("  无冲突")

print()
print("版本排序（按 ver 数值，而非字典序）:")
ordered = sorted(parsed, key=lambda x: (x[1]["ver"], x[1]["date"]))
print("  ", " < ".join("v%d" % d["ver"] for _, d in ordered))
print("  注意：字典序会把 v10 排到 v2 前面，必须解析成整数比较。")
'''

# ---------------------------------------------------------------- ex10
DEMOS["ex10"] = '''"""健康检查三层 + 启动预热：用一个确定性的模型状态机演示 ready/warm 的差别。

注意：不用 time.perf_counter() 测真实墙钟——那种输出在不同机器/负载下会漂移，
示例必须可复现。这里直接用固定开销模型表达「未预热 = 首请求慢一倍」。
"""


class FakeModel:
    """模拟模型的生命周期：未加载 -> 已加载 -> 已预热。"""

    def __init__(self, base_ms=45, load_ms=300, warmup_n=3):
        self.loaded = False
        self.warm = False
        self.base_ms = base_ms
        self.load_ms = load_ms
        self.warmup_n = warmup_n
        self.warmup_calls = 0
        self.loaded_ms = 0

    def load(self):
        # 读权重、分配显存：一次性开销，发生在启动期
        self.loaded = True
        self.loaded_ms = self.load_ms

    def warmup(self):
        if not self.loaded:
            raise RuntimeError("未加载不能预热")
        # 预热跑 n 次真实推理，目的是触发 kernel 编译与显存池化
        for _ in range(self.warmup_n):
            self.warmup_calls += 1
        self.warm = True

    def infer(self):
        # 未预热：首次推理要额外付 kernel 编译/内存分配的钱，约等于慢一倍
        return self.base_ms if self.warm else self.base_ms * 2


def health(m):
    return {"alive": True, "ready": m.loaded, "warm": m.warm}


m = FakeModel()
print("启动时 health:", health(m))

m.load()
print("加载后 health:", health(m), "（加载耗时 %dms）" % m.loaded_ms)

m.warmup()
print("预热后 health:", health(m), "（预热跑了 %d 次）" % m.warmup_calls)

print()
print("首次推理耗时对比（同一输入，预热后理论 %dms）:" % m.base_ms)
m.warm = False
print("  预热前: %dms（首请求含 kernel 编译/显存分配）" % m.infer())
m.warm = True
print("  预热后: %dms" % m.infer())

print()
print("读法：ready 只表示权重已在内存，warm 才表示「第一次推理不会慢」。")
print("若网关只看 alive，会在预热完成前就放流量进来，用户首请求超时。")
print("所以摘流条件应是 ready AND warm：ready 之前不接流量，warm 之前不摘保护。")
print()
print("另一个推论：预热必须用「真实形状」的输入。用长度 1 的假数据预热，")
print("分配不到长序列需要的显存块，真实请求仍会首次变慢——预热就白做了。")
'''


def main() -> int:
    ok = 0
    for name, code in DEMOS.items():
        src = OUT / f"{name}.py"
        src.write_text(code, encoding="utf-8")
        r = subprocess.run([sys.executable, str(src)], capture_output=True, text=True,
                           encoding="utf-8", timeout=120)
        if r.returncode != 0:
            print(f"[FAIL] {name}\n{r.stderr[:1200]}")
            continue
        (OUT / f"{name}.txt").write_text(r.stdout, encoding="utf-8")
        ok += 1
        print(f"[ok] {name}  ({len(r.stdout)} 字)")
    print(f"\n跑通 {ok}/{len(DEMOS)}")
    return 0 if ok == len(DEMOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
