# title: 扩散生成参数实验：CFG 引导、步数收益递减与种子可复现性
import numpy as np

rng = np.random.default_rng(0)


def cfg_guided(eps_uncond, eps_cond, w):
    """CFG：把无条件预测往条件方向外推，w=1 时退化为普通条件采样。"""
    return eps_uncond + w * (eps_cond - eps_uncond)


def denoise_score(seed, steps, noise_scale=1.0):
    """模拟去噪：固定种子的初始噪声，每步按 1/sqrt(step) 收缩，返回「样本」与「与目标的偏差」。"""
    r = np.random.default_rng(seed)
    x = r.normal(size=4) * noise_scale
    target = np.array([1.0, -1.0, 0.5, 0.0])
    for s in range(1, steps + 1):
        grad = (x - target) / (1 + s * 0.5)     # 步数越多越贴近目标
        x = x - grad * 0.3
    return x, float(np.abs(x - target).mean())


# 1) CFG：w 增大把预测外推得更远，w=1 时等于条件预测本身
eps_u = np.zeros(4)
eps_c = np.array([1.0, -1.0, 0.5, 0.0])
print("== 1) CFG 引导系数扫描（eps_uncond=0, eps_cond=[1,-1,.5,0]） ==")
for w in (1.0, 3.0, 7.5, 12.0, 20.0, 30.0):
    e = cfg_guided(eps_u, eps_c, w)
    print(f"w={w:5.1f} -> {np.round(e, 2)}")
assert np.allclose(cfg_guided(eps_u, eps_c, 1.0), eps_c)

# 2) 步数收益递减：偏差下降，但边际收益越来越小
print("\n== 2) 采样步数与「样本-目标偏差」 ==")
errs = {}
for steps in (1, 2, 5, 10, 20, 40, 80):
    _, err = denoise_score(seed=7, steps=steps)
    errs[steps] = err
    print(f"steps={steps:3d}: 平均偏差 = {err:.4f}")
base = errs[1]
print(f"1->5 步改善 {(1 - errs[5] / base):.1%}，20->40 步仅改善 {(1 - errs[40] / errs[20]):.1%}（收益锐减）")

# 3) 种子可复现：同种子同参数完全一致，换种子才变
x1, _ = denoise_score(seed=42, steps=10)
x2, _ = denoise_score(seed=42, steps=10)
x3, _ = denoise_score(seed=43, steps=10)
print("\n== 3) 种子可复现性 ==")
print(f"同种子两次运行逐元素一致: {np.array_equal(x1, x2)}")
print(f"换种子结果不同: {not np.array_equal(x1, x3)}")
assert np.array_equal(x1, x2) and not np.array_equal(x1, x3)

print("\n结论：w 调大不是无限变好、步数 20 后收益锐减、同种子同参数才能复现——三个旋钮各有代价，")
print("读法：1. CFG 外推公式 w=1 退化为普通条件采样，w 过大把分布推到流形外（过饱和/伪影）；2. 步数超过 20~30 边际收益锐减，省时优先砍步数而不是砍分辨率；3. 生产必须持久化「模型版本+种子+CFG+步数+提示词原文」，否则投诉无法复现；4. 本示例用确定性模拟演示参数效应，未加载任何真实扩散模型。")
