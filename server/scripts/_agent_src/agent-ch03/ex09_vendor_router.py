# title: 多厂商路由：能力先过滤，成本/健康/延迟再加权打分
# 本地模拟 200 个请求，比较「全走一家」与「按需路由」的成本、成功率、P95。
# 路由的第一原则是硬约束过滤（要 tool call 就不能选不支持的一家），第二才是打分。

import random

VENDORS = {
    "alpha": {"tool": 3, "json": 3, "long": 3, "in": 3.0, "out": 9.0, "health": 0.990, "p95": 1200},
    "beta":  {"tool": 2, "json": 1, "long": 3, "in": 1.0, "out": 4.0, "health": 0.970, "p95": 600},
    "gamma": {"tool": 1, "json": 1, "long": 1, "in": 0.3, "out": 1.2, "health": 0.930, "p95": 400},
}
WEIGHTS = {"cap": 0.50, "cost": 0.30, "health": 0.20}
PROMPT, OUTPUT = 1200, 300


def req_cost(v):
    return (PROMPT * v["in"] + OUTPUT * v["out"]) / 1e6


def norm_cost():
    costs = {k: req_cost(v) for k, v in VENDORS.items()}
    lo, hi = min(costs.values()), max(costs.values())
    return {k: (hi - c) / (hi - lo) for k, c in costs.items()}


COST_NORM = norm_cost()


def score(name, need, long_req):
    v = VENDORS[name]
    if need and v[need] < 2:
        return None
    if long_req and v["long"] < 2:
        return None
    cap = v[need] / 3 if need else sum(v[k] for k in ("tool", "json", "long")) / 9
    s = WEIGHTS["cap"] * cap + WEIGHTS["cost"] * COST_NORM[name] + WEIGHTS["health"] * v["health"]
    if v["p95"] > 1000:
        s -= 0.05
    elif v["p95"] <= 500:
        s += 0.10
    return s


def make_requests(n=200, seed=11):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        r = rng.random()
        need = "tool" if r < 0.30 else ("json" if r < 0.60 else None)
        out.append((need, rng.random() < 0.20))
    return out


REQS = make_requests()
print(f"厂商能力矩阵（tool/json/long 0-3）与成本（元/百万 token）、健康度")
print(f"{'厂商':<7}{'tool':>5}{'json':>5}{'long':>5}{'单请求元':>10}{'健康度':>8}{'P95ms':>7}")
for k, v in VENDORS.items():
    print(f"{k:<7}{v['tool']:>5}{v['json']:>5}{v['long']:>5}{req_cost(v):>10.5f}{v['health']:>8.3f}{v['p95']:>7}")


def simulate(pick):
    rng = random.Random(99)
    ok = 0
    cost = 0.0
    p95 = 0
    unsupported = 0
    dist = {}
    for need, long_req in REQS:
        name = pick(need, long_req)
        dist[name] = dist.get(name, 0) + 1
        v = VENDORS[name]
        if (need and v[need] < 2) or (long_req and v["long"] < 2):
            unsupported += 1          # 能力不满足：请求直接失败，不产生调用成本
            continue
        cost += req_cost(v)
        if rng.random() < v["health"]:
            ok += 1
        p95 = max(p95, v["p95"])
    return ok / len(REQS), cost, p95, unsupported, dist


def router(need, long_req):
    cands = [(score(n, need, long_req), n) for n in VENDORS]
    cands = [(s, n) for s, n in cands if s is not None]
    return max(cands)[1]


print("\n路由打分（分数越高越优先）")
def fmt(s):
    return "不支持" if s is None else f"{s:.3f}"

for n in VENDORS:
    print(f"  {n:<6} 通用={fmt(score(n, None, False)):<7}"
          f" 需tool={fmt(score(n, 'tool', False)):<7}"
          f" 需json={fmt(score(n, 'json', False)):<7}"
          f" 需long={fmt(score(n, 'long', False))}")

print(f"\n{'策略':<20}{'成功率':>8}{'200次成本':>11}{'能力不满足':>10}{'最坏P95ms':>9}  路由分布")
for label, pick in (
    ("全走 alpha", lambda need, lg: "alpha"),
    ("全走 beta", lambda need, lg: "beta"),
    ("全走 gamma", lambda need, lg: "gamma"),
    ("能力+成本路由", router),
):
    rate, cost, p95, unsupported, dist = simulate(pick)
    dist_s = " ".join(f"{k}:{v}" for k, v in sorted(dist.items()))
    print(f"{label:<20}{rate:>8.2%}{cost:>11.4f}{unsupported:>10}{p95:>9}  {dist_s}")

print("\n读法：全走 beta 的单位成本只有 alpha 的 38%，但 30% 的请求是它做不了的 json；")
print("      全走 gamma 更便宜，可 60% 的请求它都接不了。单看成本选厂商，等于用不可用换便宜。")
print("      路由把 json 给 alpha、tool/long 给 beta、普通请求给 gamma：")
print("      成本约为全走 alpha 的 45%，成功率只低 3 个百分点。")
print("结论：路由表要由「硬能力」和「实时健康度」共同决定；")
print("      health 是滑动窗口统计，不是配置常量——写死 0.99 的路由器在故障时会把流量全压给坏节点。")
