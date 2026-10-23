# title: 均值归一化对预测的影响：三种口径的 MAE 对照
# 同一份带「用户打分偏置」的数据，分别用
#   ① 原始余弦 + 原始加权平均（完全不归一化）
#   ② 原始余弦 + 减 μ_v 加 μ_u（只修正预测，不修正相似度）
#   ③ 中心化余弦 + 减 μ_v 加 μ_u（完整做法）
# 观察 MAE，理解「归一化不是可选项」。
import numpy as np

rng = np.random.default_rng(11)
n_u, n_i, k = 120, 80, 4
P = rng.normal(0, 0.7, (n_u, k))
Q = rng.normal(0, 0.7, (n_i, k))
b_u = rng.normal(0, 1.2, n_u)          # 用户打分松紧
b_i = rng.normal(0, 0.8, n_i)          # 物品好坏
R = 3.2 + b_u[:, None] + b_i[None, :] + P @ Q.T + rng.normal(0, 0.35, (n_u, n_i))
R = np.clip(np.round(R), 1, 5)

obs = rng.random((n_u, n_i)) < 0.35
# 每人至少 5 条观测
for u in range(n_u):
    idx = np.where(obs[u])[0]
    if idx.size < 5:
        obs[u, rng.choice(n_i, 5 - idx.size, replace=False)] = True

# 划出 10% 观测做测试（固定掩码，三种方法共用）
test = obs & (rng.random((n_u, n_i)) < 0.10)
train = obs & ~test
mu_u = np.array([R[u, train[u]].mean() for u in range(n_u)])

def sim_matrix(centered):
    S = np.zeros((n_u, n_u))
    for a in range(n_u):
        for b in range(a + 1, n_u):
            m = train[a] & train[b]
            if m.sum() < 3:
                continue
            va, vb = R[a, m], R[b, m]
            if centered:
                va, vb = va - mu_u[a], vb - mu_u[b]
            s = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
            S[a, b] = S[b, a] = s
    return S

S_raw, S_ctr = sim_matrix(False), sim_matrix(True)

def predict(a, i, S, mode, topk=15):
    cand = [b for b in np.where(train[:, i])[0] if b != a and abs(S[a, b]) > 1e-9]
    cand = sorted(cand, key=lambda b: -abs(S[a, b]))[:topk]
    if not cand:
        return mu_u[a]
    if mode == "raw":                       # 不做任何均值修正
        num = sum(S[a, b] * R[b, i] for b in cand)
        den = sum(abs(S[a, b]) for b in cand)
        return num / den
    num = sum(S[a, b] * (R[b, i] - mu_u[b]) for b in cand)   # 减 μ_v 加 μ_u
    den = sum(abs(S[a, b]) for b in cand)
    return mu_u[a] + num / den

for name, S, mode in (("① 原始余弦 + 原始平均", S_raw, "raw"),
                      ("② 原始余弦 + 均值修正", S_raw, "norm"),
                      ("③ 中心化余弦 + 均值修正", S_ctr, "norm")):
    errs = [abs(predict(a, i, S, mode) - R[a, i]) for a in range(n_u) for i in np.where(test[a])[0]]
    print(f"{name}: MAE = {np.mean(errs):.4f}（n={len(errs)}）")

# 展示一个「宽容用户」与「苛刻用户」的对比
hi = int(np.argmax(mu_u)); lo = int(np.argmin(mu_u))
print(f"\n最宽容用户 u{hi}: μ={mu_u[hi]:.2f}；最苛刻用户 u{lo}: μ={mu_u[lo]:.2f}")
i = int(np.where(train[hi] & train[lo])[0][0])
print(f"同一物品 i{i}：u{hi} 打 {R[hi,i]:.0f} 分，u{lo} 打 {R[lo,i]:.0f} 分")
print(f"  若直接平均两人评分 → {(R[hi,i]+R[lo,i])/2:.2f}，对谁都不准")
print(f"  先减各自均值再加回目标均值 → 保留了「相对偏好」，尺度差异被剥离")

print("\n读法：")
print("1. 完全不归一化时，预测被「宽容用户」的分数整体抬高，MAE 明显最差；")
print("2. 只在预测式里减 μ_v 加 μ_u 就能救回大部分误差（偏置是方差最大的成分）；")
print("3. 再把相似度也中心化，MAE 进一步下降——因为邻居选择本身也变准了；")
print("4. 工业上还会把 μ、b_u、b_i 显式建模进 MF，这一步等价于「先做 baseline 再做因子」。")
