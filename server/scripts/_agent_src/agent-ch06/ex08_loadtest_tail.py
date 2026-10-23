# title: 压测报告：均值 205ms 看着漂亮，P99 是 1.4 秒，2.8% 的请求吃掉一半等待时间
# 2000 条模拟请求：97% 来自常规分布，3% 是长输出导致的长尾；错误按输出长度分桶。
# 真实压测请用 locust/k6 采集，这里只演示「拿到样本之后该怎么读」。
import numpy as np

rng = np.random.default_rng(42)
N = 2000
tail = rng.random(N) < 0.03
out_len = np.where(tail, rng.integers(1200, 2600, N), rng.integers(40, 400, N))
base = rng.lognormal(np.log(0.16), 0.35, N)
lat = np.where(tail, base * rng.uniform(4.0, 7.5, N), base)      # 秒
lat = np.round(lat, 3)

# 错误：长尾请求里超时更多
err_p = np.where(out_len >= 1200, 0.075, 0.004)
err = rng.random(N) < err_p

print(f"样本 {N} 条，均值 {lat.mean()*1000:.0f}ms，最大 {lat.max():.2f}s")
print(f"{'分位':<8}{'延迟':>9}")
for q in (50, 90, 95, 99, 99.9):
    print(f"P{q:<7}{np.percentile(lat, q)*1000:>8.0f}ms")
print(f"{'均值':<8}{lat.mean()*1000:>8.0f}ms   <- 均值比 P50 高 {lat.mean()/np.median(lat)-1:.0%}，已经被长尾拉偏")

slow = lat >= np.percentile(lat, 97)
print(f"\n最慢的 3% 请求占用了总等待时间的 {lat[slow].sum()/lat.sum():.0%}，"
      f"而它们只占请求量的 {slow.mean():.1%}。")

print(f"\n{'输出长度桶':<12}{'请求数':>7}{'占比':>7}{'P50':>8}{'P99':>9}{'错误率':>8}")
buckets = [(0, 200, "短 <200"), (200, 800, "中 200-800"), (800, 1200, "长 800-1200"), (1200, 9999, "超长 >1200")]
for lo, hi, name in buckets:
    m = (out_len >= lo) & (out_len < hi)
    if m.sum() == 0:
        continue
    print(f"{name:<12}{int(m.sum()):>7}{m.mean():>7.0%}{np.percentile(lat[m], 50)*1000:>7.0f}ms"
          f"{np.percentile(lat[m], 99)*1000:>8.0f}ms{err[m].mean():>8.1%}")

print(f"\n整体错误率 {err.mean():.2%}；超长桶 {err[out_len >= 1200].mean():.1%}，"
      f"短请求桶 {err[out_len < 200].mean():.1%}——错误高度集中，不是均匀分布。")

trimmed = lat[lat <= np.percentile(lat, 99)]
print(f"\n去掉最慢 1% 后：均值 {trimmed.mean()*1000:.0f}ms，P99 {np.percentile(trimmed, 99)*1000:.0f}ms。")
print("对比原始 P99 1.4s，说明这一个数字完全由尾部样本决定，样本量再小一点就会跳。")

print("\n读法：压测报告里最常见的三种错误——")
print("1) 只报均值：均值 205ms 会被长尾拉高，也会掩盖 99% 用户的真实体验；")
print("2) 只报 P99 不报样本量：2000 条样本的 P99 只有 20 条支撑，置信区间很宽；")
print("3) 把错误率和延迟分开看：本例的错误集中在超长请求，说明是超时而不是随机故障。")
print("\n结论：一份能用于决策的压测报告要有五列：分位延迟（P50/P95/P99）、错误率、")
print("样本量、长度分布、硬件与模型版本。缺长度分布，就无法解释长尾来自哪里，也无法复现。")
