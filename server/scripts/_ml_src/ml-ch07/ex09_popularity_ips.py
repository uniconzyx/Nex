# title: 流行度偏差与 IPS 去偏：朴素估计为什么会高估新策略
# 记录策略 π0 偏向「热门 × 高亲和」的物品；直接用日志点击率评估新策略会有选择偏差。
# 对比：朴素均值 / IPS / SNIPS（截断），并给出解析真值。
import numpy as np

rng = np.random.default_rng(61)
n_u, n_i, n_imp = 300, 80, 8000
P = rng.normal(0, 1.0, (n_u, 2))
Q = rng.normal(0, 1.0, (n_i, 2))
pop = 1.0 / (np.arange(n_i) + 1) ** 0.9
pop = pop / pop.sum()
z = P @ Q.T
z = (z - z.mean()) / z.std()

click_p = 1 / (1 + np.exp(-(1.3 * z - 1.2)))          # 真实点击概率只由亲和度决定
logits0 = 1.1 * z + 0.9 * np.log(pop)[None, :]        # π0：偏向高亲和 + 热门
pi0 = np.exp(logits0 - logits0.max(axis=1, keepdims=True))
pi0 /= pi0.sum(axis=1, keepdims=True)
cum = np.cumsum(pi0, axis=1)

users = rng.integers(0, n_u, n_imp)
items = np.array([np.searchsorted(cum[u], r) for u, r in zip(users, rng.random(n_imp))])
items = np.clip(items, 0, n_i - 1)
clicks = (rng.random(n_imp) < click_p[users, items]).astype(float)
w0 = pi0[users, items]
print(f"日志 {n_imp} 条曝光，真实平均点击率 {clicks.mean():.3f}")
print(f"曝光最多的 5 个物品: {np.argsort(-np.bincount(items, minlength=n_i))[:5]}"
      f"（流行度排名 {np.argsort(-pop)[:5]}）")

def evaluate(name, target_items, K=10):
    target = set(target_items)
    mask = np.array([i in target for i in items])
    naive = clicks[mask].mean() if mask.sum() else float("nan")
    raw_w = np.where(mask, (1.0 / K) / w0, 0.0)
    ips = float(np.mean(raw_w * clicks))
    w_clip = np.minimum(raw_w, 20.0)
    snips = float(np.sum(w_clip * clicks) / max(np.sum(w_clip), 1e-12))
    true = float(np.mean([click_p[u, list(target)].mean() for u in range(n_u)]))
    final = list(target)
    print(f"\n策略「{name}」：Top-{K} = {final[:5]}...（共 {len(target)} 个）")
    print(f"  日志命中曝光 {mask.sum():>5} 条，平均流行度分位 {np.mean([np.where(np.argsort(-pop)==i)[0][0] for i in target]):.1f}")
    print(f"  朴素均值 = {naive:.4f}   IPS = {ips:.4f}   SNIPS = {snips:.4f}   真值 = {true:.4f}")
    return naive, ips, snips, true

evaluate("全站热门", list(np.argsort(-pop)[:10]))
evaluate("长尾物品", list(np.argsort(pop)[:10]))

print("\n读法：")
print("1. 热门策略的朴素估计明显高于真值：日志里的曝光偏向「高亲和 × 热门」，样本不是总体的随机抽样；")
print("2. IPS 用 1/π0 把每个样本的代表性还原，理论上无偏，但方差大；SNIPS 归一化后更稳；")
print("3. 长尾策略的 π0 接近 0，权重爆炸——这就是 positivity 被破坏，离线无法可靠评估；")
print("4. 工程上必须留随机曝光（π0 有下界）、做权重截断，并同时报告置信区间与有效样本量。")
