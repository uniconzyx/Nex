# title: BPR 成对损失训练：负采样 + 排序指标（AUC / HR@10）
# 隐式反馈没有「评分」，只有正样本。BPR 最大化 P(正 ≻ 负)：
#   L = −log σ(x̂_ui − x̂_uj) + λ‖·‖²
# 这里同时展示：负采样、梯度、以及「训练损失下降 → 排序指标上升」的对应关系。
import numpy as np

rng = np.random.default_rng(41)
n_u, n_i, k = 200, 150, 3
P_true = rng.normal(0, 0.8, (n_u, k))
Q_true = rng.normal(0, 0.8, (n_i, k))
S = P_true @ Q_true.T + rng.normal(0, 0.5, (n_u, n_i))

train_pos, test_pos = {}, {}
for u in range(n_u):
    thr = np.quantile(S[u], 0.94)          # 每人约 6% 的物品为正
    items = list(np.where(S[u] >= thr)[0])
    if len(items) < 4:
        items = list(np.argsort(-S[u])[:4])
    rng.shuffle(items)
    test_pos[u] = {items[-1]}              # 留 1 个做测试
    train_pos[u] = set(items[:-1])

P = rng.normal(0, 0.1, (n_u, k))
Q = rng.normal(0, 0.1, (n_i, k))
lr, lam, epochs = 0.05, 0.01, 40

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def bpr_loss():
    tot = 0.0
    for u in range(n_u):
        for i in train_pos[u]:
            j = rng.integers(n_i)
            while j in train_pos[u] or j in test_pos[u]:
                j = rng.integers(n_i)
            d = P[u] @ (Q[i] - Q[j])
            tot += -np.log(sigmoid(d) + 1e-12)
    return tot / sum(len(v) for v in train_pos.values())

print(f"用户 {n_u}，物品 {n_i}，正样本 {sum(len(v) for v in train_pos.values())}（每人约 3~6 个）")
print(f"{'epoch':>6}{'BPR loss':>11}")
for ep in range(1, epochs + 1):
    for u in range(n_u):
        for i in train_pos[u]:
            j = rng.integers(n_i)
            while j in train_pos[u] or j in test_pos[u]:
                j = rng.integers(n_i)
            d = P[u] @ (Q[i] - Q[j])
            g = 1.0 - sigmoid(d)               # δ = 1 − σ(d)，排序错得越狠梯度越大
            pu_old = P[u].copy()
            P[u] += lr * (g * (Q[i] - Q[j]) - lam * P[u])
            Q[i] += lr * (g * pu_old - lam * Q[i])
            Q[j] += lr * (-g * pu_old - lam * Q[j])
    if ep % 8 == 0:
        print(f"{ep:>6}{bpr_loss():>11.4f}")

# 评估：排除训练正样本后排序全库
auc_num = auc_den = 0
hr = 0
for u in range(n_u):
    scores = Q @ P[u]
    scores[list(train_pos[u])] = -np.inf
    neg_pool = [j for j in range(n_i) if j not in train_pos[u] and j not in test_pos[u]]
    te = list(test_pos[u])[0]
    for _ in range(20):
        j = neg_pool[rng.integers(len(neg_pool))]
        auc_den += 1
        auc_num += 1.0 if scores[te] > scores[j] else 0.0
    top10 = set(np.argsort(-scores)[:10])
    hr += 1 if top10 & test_pos[u] else 0

print(f"\n测试 AUC（采样负例）= {auc_num / auc_den:.4f}")
print(f"HR@10 = {hr / n_u:.4f}")
print(f"训练后 ‖P‖={np.linalg.norm(P):.1f}，‖Q‖={np.linalg.norm(Q):.1f}")

print("\n读法：")
print("1. BPR 只要求「正样本分数高于负样本」，不需要把未点击当 0 分；")
print("2. δ=1−σ(差值) 是自适应权重：已经排对的 pair 梯度趋近 0，模型专注难例；")
print("3. 负样本从「未交互」采，但必须排除训练/测试正样本，否则等于教模型把正样本压低；")
print("4. 损失下降与 HR@10 上升同向，但与 RMSE 无关——BPR 本来就不拟合评分。")
