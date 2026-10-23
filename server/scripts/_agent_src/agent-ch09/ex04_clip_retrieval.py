# title: CLIP 双塔检索：归一化余弦、top-k 与分数断层路由
import numpy as np

GAP = 0.05  # top1 领先 top2 不足该值视为不确定


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def retrieve(img_feats, q, k=3, gap=GAP):
    """双塔检索：两侧都归一化，点积即余弦相似度；返回 top-k 索引、分数、是否进路由。"""
    I = img_feats / np.linalg.norm(img_feats, axis=1, keepdims=True)
    u = q / np.linalg.norm(q)
    sims = I @ u
    order = np.argsort(-sims)
    top = order[:k]
    uncertain = (sims[top[0]] - sims[top[1]]) < gap
    return top, sims[top], uncertain


rng = np.random.default_rng(0)
feats = rng.normal(size=(6, 8))  # 模拟 6 张图的图像塔输出（未归一化）

# 情形 A：查询与图 2 同源（应断层领先，直接返回）
q_a = feats[2] + rng.normal(scale=0.1, size=8)
# 情形 B：纯随机查询（分数接近，应进路由）
q_b = rng.normal(size=8)
# 情形 C：查询由两张图等权混合而成（歧义查询，应进路由）
q_c = 0.5 * feats[0] + 0.5 * feats[3]

print(f"{'查询类型':<16}{'top-3索引':<16}{'分数':<30}{'top1-top2':>10}{'动作':>10}")
for name, q in [("同源查询", q_a), ("随机查询", q_b), ("歧义查询", q_c)]:
    idx, s, uncertain = retrieve(feats, q)
    d = s[0] - s[1]
    action = "进人工/重排" if uncertain else "直接返回"
    print(f"{pad(name, 14)}{str(idx.tolist()):<16}{str(np.round(s, 3).tolist()):<30}{d:>10.3f}{action:>12}")

# 验证：同源查询 top-1 就是源图，且断层领先
idx_a, s_a, unc_a = retrieve(feats, q_a)
assert idx_a[0] == 2 and not unc_a and s_a[0] > 0.9
# 验证：歧义查询 top1/top2 接近，触发路由
_, s_c, unc_c = retrieve(feats, q_c)
assert unc_c

print("\n== 归一化的作用：不归一化时分数不可比 ==")
raw = feats @ q_a  # 未归一化直接点积
norm_sims = (feats / np.linalg.norm(feats, axis=1, keepdims=True)) @ (q_a / np.linalg.norm(q_a))
print(f"未归一化 top-1 分数 = {np.sort(raw)[::-1][0]:.3f}，归一化后 = {np.sort(norm_sims)[::-1][0]:.3f}")
print(f"未归一化 top-1/top-2 差 = {np.sort(raw)[::-1][0] - np.sort(raw)[::-1][1]:.3f}（混入了向量模长，不是纯方向）")

print("\n结论：检索质量来自训练时的对齐，推理期只做归一化 + 点积 + top-k；分数接近时 top-1 是噪声，")
print("读法：1. 两侧都必须 L2 归一化，否则分数里混入模长、跨查询不可比；2. 断层阈值 GAP=0.05 是经验值，应按业务错误成本标定；3. 不确定时的正确动作是重排/候选列表/澄清，而不是硬取 top-1；4. 本示例用随机向量模拟双塔输出，未加载任何真实模型。")
