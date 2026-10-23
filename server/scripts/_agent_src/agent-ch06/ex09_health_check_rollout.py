# title: 灰度与探活模拟器：无探活直切 20% 请求出错，灰度+探活+摘流把爆炸半径压到个位数
# 10 个新版本副本，其中 20% 是带 bug 的坏副本（每个请求都返回错误）。
# 四种策略只改「何时探活、是否摘流、是否灰度」，请求流完全一致，便于对比。
import numpy as np

rng = np.random.default_rng(7)
N = 10                      # 新版本副本数
BAD = 0.20                  # 坏副本比例（本构建版本，经验判断）
WINDOW = 2000               # 滚动窗口总请求数
PROBE = 200                 # 探活间隔（请求数）
CANARY = 0.10               # 灰度首阶段流量比例
THRESH = 0.02               # 灰度阶段错误率止损阈值
OLD_ERR = 0.005             # 老版本兜底错误率

bad = rng.random(N) < BAD
old_err = rng.random(WINDOW) < OLD_ERR
n_bad = int(bad.sum())
print(f"新版本 {N} 副本，坏副本 {n_bad} 个（占比 {BAD:.0%}）；老版本兜底错误率 {OLD_ERR:.1%}")
print(f"滚动窗口 {WINDOW} 请求；探活间隔 {PROBE}；灰度首阶段 {CANARY:.0%} 流量；止损阈值 {THRESH:.0%}\n")


def simulate(strategy):
    pulled = set()
    canary_on = (strategy == "灰度+探活+摘流")
    expanded = not canary_on
    stopped = False
    total_err = 0
    new_err = 0
    peak = 0.0
    auto = "否"
    canary_new_req = 0
    canary_new_err = 0
    canary_decided = False
    n_int = WINDOW // PROBE
    for k in range(n_int):
        base = k * PROBE
        frac = CANARY if (canary_on and not expanded) else (0.0 if stopped else 1.0)
        new_req = int(round(frac * PROBE))
        # 新版本请求：轮询分配到未摘流副本
        active = [r for r in range(N) if r not in pulled]
        if active:
            bad_active = sum(1 for r in active if bad[r])
            n_bad_req = new_req * bad_active // len(active)
        else:
            n_bad_req = 0
        if canary_on and not expanded:
            canary_new_req += new_req
            canary_new_err += n_bad_req
        # 老版本请求（兜底）
        old_req = PROBE - new_req
        o_err = int(old_err[base + new_req: base + PROBE].sum())
        i_err = n_bad_req + o_err
        rate = i_err / PROBE
        if rate > peak:
            peak = rate
        total_err += i_err
        new_err += n_bad_req
        # 灰度决策：首阶段结束时，按灰度流量上的错误率判断
        if canary_on and not canary_decided:
            canary_decided = True
            canary_rate = canary_new_err / canary_new_req if canary_new_req else 0.0
            if canary_rate > THRESH:
                stopped = True
                auto = "是"
            else:
                expanded = True
        # 探活：区间末发现坏副本，并按策略决定是否摘流
        for r in range(N):
            if bad[r] and strategy in ("有探活且摘流", "灰度+探活+摘流"):
                pulled.add(r)
                auto = "是"
    return total_err / WINDOW, new_err, peak, auto


rows = []
for s in ("无探活直切", "有探活不摘流", "有探活且摘流", "灰度+探活+摘流"):
    rate, blast, peak, auto = simulate(s)
    rows.append((s, rate, blast, peak, auto))

print(f"{'策略':<14}{'整体错误率':>10}{'爆炸半径':>10}{'峰值区间错误率':>14}{'自动止损':>8}")
for s, rate, blast, peak, auto in rows:
    print(f"{s:<14}{rate*100:>9.1f}%{blast:>10}{peak*100:>13.1f}%{auto:>9}")

print("\n读法：")
print("1) 探活只是『发现』，摘流才是『止损』——『有探活不摘流』和『无探活直切』错误率完全一样；")
print("2) 摘流把错误总量从 400 个请求压到 40 个，但峰值仍由『探测间隔』决定（一个区间的延迟无法消除）；")
print("3) 灰度把爆炸半径再砍一个数量级：首阶段只放 10% 流量，坏构建在探测到高错误率后立即停，")
print("   绝大多数请求始终走老版本兜底，所以峰值和总量同时下降。")

print("\n结论：上线新模型的默认姿势是『灰度 + 探活 + 摘流』三件套，缺一不可：")
print("灰度限制爆炸半径，探活发现问题，摘流执行止损。单独任何一项都挡不住一次坏构建。")
