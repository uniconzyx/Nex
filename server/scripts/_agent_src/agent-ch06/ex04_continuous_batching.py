# title: 连续批处理 vs 静态批处理：输出长度方差大时吞吐 1.9 倍，方差小只剩 1.05 倍
# 离散事件模拟：每步 5ms，一个请求占一个 slot，prefill 按 64 token/步 折算。
# 队列、到达时间、输出长度都由固定种子生成，可复现；真实引擎还有 chunked prefill 与抢占。
import numpy as np

DT = 0.005          # 每步 5ms
SLOTS = 8           # 单卡并发 slot 数
N = 160
LAMBDA = 30.0       # 到达率 req/s（刻意高于服务能力，让队列积压）


def make_workload(sigma, seed=3):
    rng = np.random.default_rng(seed)
    gaps = rng.exponential(1.0 / LAMBDA, N)
    arrivals = np.cumsum(gaps)
    prefill = rng.integers(200, 900, N)                     # 输入 token
    decode = np.clip(rng.lognormal(np.log(110), sigma, N), 20, 900).astype(int)
    return arrivals, prefill, decode


def static_batch(arr, prefill, decode, c=SLOTS):
    n = len(arr)
    lat, busy_steps, t, makespan = [], 0, 0, 0.0
    idx = 0
    while idx < n:
        batch = list(range(idx, min(idx + c, n)))
        start = max(arr[batch[-1]], t)   # 等最后一条到齐，且上一批必须已经跑完
        steps = max(int(np.ceil(prefill[i] / 64)) + decode[i] for i in batch)
        end = start + steps * DT
        lat.extend(end - arr[i] for i in batch)
        busy_steps += len(batch) * steps
        idx += c
        t = end
        makespan = max(makespan, end)
    return np.array(lat), n / makespan, busy_steps / (c * (makespan / DT))


def continuous_batch(arr, prefill, decode, c=SLOTS):
    n = len(arr)
    running, waiting, i, t, steps, busy = [], [], 0, 0.0, 0, 0
    lat = []
    while i < n or running:
        while i < n and arr[i] <= t + 1e-12 and len(running) < c:
            running.append({"arr": arr[i], "pf": int(np.ceil(prefill[i] / 64)), "dec": decode[i]})
            i += 1
        if not running:
            t = arr[i]                       # 空转等待下一个到达
            continue
        busy += len(running)
        nxt = []
        for r in running:
            if r["pf"] > 0:
                r["pf"] -= 1
            else:
                r["dec"] -= 1
            if r["pf"] == 0 and r["dec"] <= 0:
                lat.append(t + DT - r["arr"])
            else:
                nxt.append(r)
        running = nxt
        t += DT
        steps += 1
    return np.array(lat), n / t, busy / (c * max(steps, 1))


for sigma, label in ((0.8, "输出长度高方差 σ=0.8"), (0.05, "输出长度低方差 σ=0.05")):
    arr, pf, dec = make_workload(sigma)
    ls, thr_s, us = static_batch(arr, pf, dec)
    lc, thr_c, uc = continuous_batch(arr, pf, dec)
    print(f"\n{label}（均值 {dec.mean():.0f} token，P95 {np.percentile(dec, 95):.0f}）")
    print(f"{'策略':<10}{'吞吐 req/s':>12}{'均值延迟':>10}{'P95 延迟':>10}{'slot 利用率':>12}")
    print(f"{'静态批':<8}{thr_s:>12.2f}{ls.mean():>10.2f}{np.percentile(ls, 95):>10.2f}{us:>12.1%}")
    print(f"{'连续批':<8}{thr_c:>12.2f}{lc.mean():>10.2f}{np.percentile(lc, 95):>10.2f}{uc:>12.1%}")
    print(f"吞吐倍率 {thr_c/thr_s:.2f}x，P95 延迟变化 {np.percentile(lc, 95) - np.percentile(ls, 95):+.2f}s")

print("\n读法：静态批的浪费来自『陪跑』——一批 8 条里只要有 1 条输出 600 token，")
print("另外 7 个 slot 在它结束前都不能接新活。输出方差越大，这种空转越严重。")
print("连续批在每条结束时立刻补位，因此方差越大，它相对静态批的优势越大。")
print("\n读法 2：连续批不是免费午餐。它把请求拆成 step 级调度，")
print("同一 step 里 prefill 与 decode 混跑会拉高 TPOT 的抖动，需要 chunked prefill 配合。")
print("\n结论：如果你的业务输出长度稳定（比如固定模板生成），静态批足够，且实现简单；")
print("只要是开放域问答、Agent、代码补全这类长度不可控的场景，连续批处理是第一优先级。")
