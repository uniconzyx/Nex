# -*- coding: utf-8 -*-
"""生成 ai-ch09（生成模型）的 examples / exercises / interview / project。

设计原则（与项目既有章节一致）：
- examples 的 expected_output **必须来自真实运行**，不允许手写；
- 每个示例固定随机种子，输出对公式可逐项对账；
- 只用 NumPy，不依赖 PyTorch/TensorFlow（本机未安装）。

用法：
    python scripts/gen_ai_ch09.py            # 生成全部
    python scripts/gen_ai_ch09.py --check    # 只跑示例并打印输出，不写盘
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "content" / "ai" / "ai-ch09"

# ---------------------------------------------------------------- examples
EXAMPLES: list[tuple[str, str, str]] = [
    (
        "ex01-ae-forward",
        "自编码器前向与参数量",
        r'''
import numpy as np
rng = np.random.default_rng(0)
D, d = 8, 3                     # 输入 8 维，瓶颈 3 维
W1 = rng.normal(0, 0.3, (D, d)); b1 = np.zeros(d)
W2 = rng.normal(0, 0.3, (d, D)); b2 = np.zeros(D)
X = rng.normal(size=(5, D))
Z = np.tanh(X @ W1 + b1)        # 编码
Xhat = Z @ W2 + b2              # 解码
mse = ((X - Xhat) ** 2).mean()
print(f"输入形状 {X.shape} -> 隐表示 {Z.shape} -> 重建 {Xhat.shape}")
print(f"压缩比 d/D = {d}/{D} = {d/D:.3f}")
print(f"参数量 = {W1.size + b1.size + W2.size + b2.size}  (W1 {W1.size} + W2 {W2.size})")
print(f"随机初始化下重建 MSE = {mse:.4f}（未训练，只验证形状与参数量口径）")
''',
    ),
    (
        "ex02-vae-reparam-kl",
        "重参数化与高斯 KL 闭式解对账",
        r'''
import numpy as np
rng = np.random.default_rng(1)
mu = np.array([0.5, -1.2, 0.0])
logvar = np.array([0.0, -1.0, 0.7])
sigma = np.exp(0.5 * logvar)
# 闭式解: 0.5 * sum(mu^2 + sigma^2 - 1 - logvar)
kl_closed = 0.5 * (mu ** 2 + sigma ** 2 - 1.0 - logvar).sum()
print(f"sigma = {np.round(sigma, 4)}")
print(f"KL 闭式解 = {kl_closed:.6f}")
print("蒙特卡洛估计（重参数化 z = mu + sigma*eps）：")
for n in (100, 1000, 10000, 100000):
    eps = rng.normal(size=(n, 3))
    z = mu + sigma * eps                       # 梯度可穿过 mu/sigma
    log_q = -0.5 * (((z - mu) / sigma) ** 2 + logvar + np.log(2 * np.pi)).sum(1)
    log_p = -0.5 * (z ** 2 + np.log(2 * np.pi)).sum(1)
    est = (log_q - log_p).mean()               # E_q[log q - log p]
    print(f"  n={n:>6d}  KL_MC = {est:.6f}  |误差| = {abs(est - kl_closed):.6f}")
print("结论：误差量级约 sigma/sqrt(n)（n=100 时约 0.09，n=10000 时约 0.002），")
print("      不严格单调是随机波动的正常表现；闭式解与采样估计在同一量级即为一致")
''',
    ),
    (
        "ex03-elbo-numeric",
        "ELBO 是似然的下界（数值验证）",
        r'''
import numpy as np

x, sx = 1.0, 0.5                 # 数据点与解码器噪声标准差 p(x|z)=N(z, sx^2)
mu, logvar = 0.8, -0.5           # 编码器输出 q(z|x)=N(mu, sigma^2)
s = np.exp(0.5 * logvar)

# ELBO = E_q[log p(x|z)] - KL(q||p(z))
# 高斯期望项可解析： E[(x-z)^2] = (x-mu)^2 + s^2
rec = -0.5 * np.log(2 * np.pi * sx ** 2) - ((x - mu) ** 2 + s ** 2) / (2 * sx ** 2)
kl = 0.5 * (mu ** 2 + s ** 2 - 1.0 - logvar)
elbo = rec - kl

# 真实 log p(x) = log ∫ p(x|z) p(z) dz，用细网格数值积分
z = np.linspace(-10, 10, 400001)
pz = np.exp(-0.5 * z ** 2) / np.sqrt(2 * np.pi)
pxz = np.exp(-0.5 * ((x - z) / sx) ** 2) / (np.sqrt(2 * np.pi) * sx)
logp = np.log(np.trapezoid(pxz * pz, z))

print(f"重建项 E_q[log p(x|z)] = {rec:.6f}")
print(f"KL 项                 = {kl:.6f}")
print(f"ELBO                  = {elbo:.6f}")
print(f"真实 log p(x)         = {logp:.6f}")
print(f"gap = log p - ELBO    = {logp - elbo:.6f}  (应 >= 0)")
print(f"ELBO <= log p -> {elbo <= logp}")
''',
    ),
    (
        "ex04-gan-optimal-d",
        "GAN 最优判别器与 2*JSD-log4 的数值对账",
        r'''
import numpy as np

def gauss(x, m, s):
    return np.exp(-0.5 * ((x - m) / s) ** 2) / (s * np.sqrt(2 * np.pi))

x = np.linspace(-7, 7, 400001)
pd = 0.6 * gauss(x, -1.0, 1.0) + 0.4 * gauss(x, 1.2, 0.7)   # 真实分布
pg = 0.5 * gauss(x, 0.2, 1.1) + 0.5 * gauss(x, 2.0, 0.8)    # 生成分布

D_star = pd / (pd + pg)                    # 理论最优判别器
V = np.trapezoid(pd * np.log(D_star) + pg * np.log(1 - D_star), x)
m = (pd + pg) / 2
jsd = 0.5 * np.trapezoid(pd * np.log(pd / m) + pg * np.log(pg / m), x)
rhs = -np.log(4) + 2 * jsd

print(f"D* 取值范围 = [{D_star.min():.3f}, {D_star.max():.3f}]（理论应在 (0,1)）")
print(f"V(D*, G)            = {V:.6f}")
print(f"-log4 + 2*JSD       = {rhs:.6f}")
print(f"两者之差            = {abs(V - rhs):.2e}  (数值积分误差)")
print(f"密度比 pd/pg 在 x=0 处 = {(pd/(pg+1e-300))[200000]:.4f}；D*/(1-D*) = {(D_star/(1-D_star))[200000]:.4f}")
print("结论：最优判别器就是密度比估计器 D*/(1-D*) = pd/pg")
''',
    ),
    (
        "ex05-mode-collapse",
        "模式崩塌的诊断：均值几乎一样，覆盖差了 50%",
        r'''
import numpy as np
rng = np.random.default_rng(7)
# 真实分布：双峰，各 50%
n = 20000
real = np.where(rng.random(n) < 0.5, rng.normal(-1, 0.3, n), rng.normal(1, 0.3, n))
# A: 崩塌（只覆盖左峰）  B: 正常覆盖双峰
gen_col = rng.normal(-1, 0.3, n)
gen_ok = np.where(rng.random(n) < 0.5, rng.normal(-1, 0.3, n), rng.normal(1, 0.3, n))

def report(name, g):
    # 一维 W1 = 排序后分位数的平均绝对差
    w1 = np.abs(np.sort(real) - np.sort(g)).mean()
    left = np.mean(np.abs(g + 1) < 0.9)
    right = np.mean(np.abs(g - 1) < 0.9)
    hist, _ = np.histogram(g, bins=40, range=(-2.5, 2.5))
    peaks = sum(1 for i in range(1, len(hist) - 1) if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > n / 80)
    print(f"{name}: 均值={g.mean():+.4f} 标准差={g.std():.4f} W1={w1:.4f} "
          f"左峰覆盖={left:.3f} 右峰覆盖={right:.3f} 直方图峰数={peaks}")

print(f"真实: 均值={real.mean():+.4f} 标准差={real.std():.4f}")
report("A 崩塌", gen_col)
report("B 正常", gen_ok)
print("关键：A 的均值(-1.0) 与真实均值(0.0) 差 1.0，但 A 的『左峰覆盖』=1.0 看起来极好——")
print("      只看单峰内部的统计量无法发现崩塌，必须看覆盖（recall）与峰数。")
''',
    ),
    (
        "ex06-wgan-distance",
        "W1 距离：一维闭式 vs 线性 critic 的盲区",
        r'''
import numpy as np
rng = np.random.default_rng(3)
n = 200000
p = rng.normal(0.0, 1.0, n)
q = rng.normal(0.8, 2.0, n)     # 均值差 0.8，标准差差 1.0

# 一维 W1 闭式：|mu1-mu2| 只在同方差时成立；一般用经验分位数积分
w1 = np.abs(np.sort(p) - np.sort(q)).mean()
w1_gauss = np.sqrt((0.0 - 0.8) ** 2 + (1.0 - 2.0) ** 2)   # 高斯情形的闭式
print(f"经验 W1 = {w1:.4f}")
print(f"高斯闭式 sqrt((dmu)^2+(dsigma)^2) = {w1_gauss:.4f}")

# KR 对偶：sup_{|f|_L<=1} E_p[f]-E_q[f]
linear_best = np.mean(p) - np.mean(q)             # 线性 f(x)=x 的取值差
print(f"线性 critic f(x)=x 的 E_p[f]-E_q[f] = {linear_best:.4f}")
print(f"线性 critic 只能看到均值差，漏掉标准差差 {abs(1.0-2.0):.1f}")
print("结论：critic 必须是非线性网络，否则 W 距离估计会严重低估分布差异（这正是 WGAN 用深层 critic 的原因）")
''',
    ),
    (
        "ex07-diffusion-forward",
        "任意步加噪的闭式解 vs 逐步加噪（分布一致性）",
        r'''
import numpy as np
rng = np.random.default_rng(11)
T = 1000
betas = np.linspace(1e-4, 0.02, T)
abar = np.cumprod(1 - betas)
x0, n = 1.5, 40000

print("t     闭式均值   闭式方差   逐步均值   逐步方差   N(0,1)理论")
for t in (10, 250, 500, 999):
    # 闭式：x_t = sqrt(abar)*x0 + sqrt(1-abar)*eps
    direct = np.sqrt(abar[t]) * x0 + np.sqrt(1 - abar[t]) * rng.normal(size=n)
    # 逐步：从 x0 开始走 t+1 步
    x = np.full(n, x0)
    for s in range(t + 1):
        x = np.sqrt(1 - betas[s]) * x + np.sqrt(betas[s]) * rng.normal(size=n)
    print(f"{t:>4d}  {direct.mean():+.4f}    {direct.var():.4f}    "
          f"{x.mean():+.4f}    {x.var():.4f}    "
          f"var={1-abar[t]:.4f}")
print("结论：两列方差都约等于 1-abar_t，闭式解与逐步实现分布一致（但噪声样本不同，不能逐元素比较）")
''',
    ),
    (
        "ex08-noise-schedule",
        "噪声调度：linear vs cosine 的 abar 与 SNR",
        r'''
import numpy as np
T, s = 1000, 0.008
linear = np.cumprod(1 - np.linspace(1e-4, 0.02, T))
ts = np.arange(T + 1)
cos = np.cos((ts / T + s) / (1 + s) * np.pi / 2) ** 2
cos = cos / cos[0]                      # 归一化到 1
cos = cos[:T]

def snr(a):
    return a / (1 - a)

print("t/T     linear abar   linear SNR    cosine abar   cosine SNR")
for frac in (0.1, 0.25, 0.5, 0.75, 0.9, 0.99):
    i = int(frac * T) - 1
    print(f"{frac:>4.2f}    {linear[i]:.6f}      {snr(linear[i]):9.4f}     "
          f"{cos[i]:.6f}      {snr(cos[i]):9.4f}")
print(f"linear: abar 降到 0.5 的时刻 t≈{int(np.argmax(linear < 0.5))}")
print(f"cosine: abar 降到 0.5 的时刻 t≈{int(np.argmax(cos < 0.5))}")
print("结论：cosine 在前期降得更慢（保留结构更久），末段才快速趋近纯噪声；"
      "linear 在中段就把信息压掉，高分辨率下表现更差")
''',
    ),
    (
        "ex09-ddpm-reverse-step",
        "DDPM 反向单步：均值公式与「完美预测噪声」的回推",
        r'''
import numpy as np
T = 1000
betas = np.linspace(1e-4, 0.02, T)
alphas = 1 - betas
abar = np.cumprod(alphas)

x0, eps, t = 0.8, 0.6, 500
xt = np.sqrt(abar[t]) * x0 + np.sqrt(1 - abar[t]) * eps     # 前向
print(f"abar_t = {abar[t]:.6f}   x_t = {xt:.6f}")

# 假设网络完美预测出 eps
eps_theta = eps
mu = (xt - betas[t] / np.sqrt(1 - abar[t]) * eps_theta) / np.sqrt(alphas[t])
x_prev = mu                                                  # 取 sigma=0 看均值项
print(f"反向均值 mu_theta = {mu:.6f}")

# 解析的 x_{t-1} 真值（用同一个 eps 的前向）
xt_prev_true = np.sqrt(abar[t-1]) * x0 + np.sqrt(1 - abar[t-1]) * eps
print(f"解析 x_(t-1)      = {xt_prev_true:.6f}")
print(f"|mu - x_(t-1)|    = {abs(mu - xt_prev_true):.6f}")
print(f"sigma_t^2 = {betas[t] * (1 - abar[t-1]) / (1 - abar[t]):.8f}（后验方差，另一选项是 betas[t]={betas[t]:.6f}）")
print("结论：残差 |mu-x_(t-1)| 只有 0.003（信号尺度 0.8 的 0.4%），且该残差来自后验方差")
print("      sigma_t^2≈0.010 的随机性（E[x_(t-1)|x_t]=mu，单次用同一 eps 比较会有 O(sigma) 差异）")
''',
    ),
    (
        "ex10-ddim-vs-ddpm",
        "DDIM 确定性跳步 vs DDPM 随机单步",
        r'''
import numpy as np
T = 1000
betas = np.linspace(1e-4, 0.02, T)
alphas = 1 - betas
abar = np.cumprod(alphas)

x0, eps = 0.8, 0.6
t, t_prev = 999, 900          # DDIM 直接跳 99 步

xt = np.sqrt(abar[t]) * x0 + np.sqrt(1 - abar[t]) * eps
eps_theta = eps
x0_hat = (xt - np.sqrt(1 - abar[t]) * eps_theta) / np.sqrt(abar[t])
print(f"x_t={xt:.6f}  预测 x0_hat={x0_hat:.6f}（真值 {x0}）")

# DDIM 一步跳到 t_prev（确定性）
x_ddim = np.sqrt(abar[t_prev]) * x0_hat + np.sqrt(1 - abar[t_prev]) * eps_theta
print(f"DDIM 跳到 t={t_prev}: {x_ddim:.6f}")

# 解析真值（同一 eps 的前向）
x_true = np.sqrt(abar[t_prev]) * x0 + np.sqrt(1 - abar[t_prev]) * eps
print(f"解析真值            : {x_true:.6f}   误差 {abs(x_ddim-x_true):.2e}")

# DDPM 只能走 1 步到 t-1，且要加随机噪声
mu = (xt - betas[t] / np.sqrt(1 - abar[t]) * eps_theta) / np.sqrt(alphas[t])
print(f"DDPM 单步 t->{t-1} 均值: {mu:.6f}（走完 1000 步要 1000 次前向，DDIM 跳 99 步只要 1 次）")
print("结论：DDIM 用确定性映射 + 跳步，把 1000 次前向压到几十次；同权重、同 eps 下结果与解析真值一致")
''',
    ),
    (
        "ex11-cfg",
        "无分类器引导 CFG：外推强度 s 的作用",
        r'''
import numpy as np
eps_uncond, eps_cond = -0.20, 0.50
print(" s     eps_tilde    相对 eps_cond 的放大倍数   说明")
for s in (0.0, 1.0, 3.0, 7.5, 15.0):
    e = eps_uncond + s * (eps_cond - eps_uncond)
    ratio = (e - eps_uncond) / (eps_cond - eps_uncond) if eps_cond != eps_uncond else float("nan")
    note = "退化无条件" if s == 0 else ("无引导（等价条件模型）" if s == 1 else ("工业常用区间" if s <= 9 else "过饱和风险"))
    print(f"{s:>4.1f}   {e:+.4f}        {ratio:>6.2f}x              {note}")

print()
print("引导项 (eps_cond - eps_uncond) 近似 grad log p(c|x)：")
print(f"  s=1 时梯度强度 = {eps_cond-eps_uncond:+.4f}；s=7.5 时等价于把条件梯度放大 7.5 倍")
print("结论：s 线性放大条件信号，同时也放大与条件无关的高频分量 -> 过饱和；")
print("      s=1 接近原模型分布，s>1 用多样性换条件一致性")
''',
    ),
    (
        "ex12-fid-frechet",
        "FID 的 Fréchet 距离：一维闭式与多维 Bures 公式",
        r'''
import numpy as np

def sqrtm(A):
    w, V = np.linalg.eigh(A)
    return V @ np.diag(np.sqrt(np.clip(w, 0, None))) @ V.T

# 一维：FID = (dmu)^2 + (dsigma)^2
mr, sr = 0.0, 1.0
mg, sg = 0.3, 1.4
fid_1d = (mr - mg) ** 2 + (sr - sg) ** 2
print(f"1D: (dmu)^2+(dsigma)^2 = {fid_1d:.6f}")

# 二维：Bures 公式
mr2 = np.array([0.0, 0.0]); Sr = np.array([[1.0, 0.3], [0.3, 1.0]])
mg2 = np.array([0.3, -0.2]); Sg = np.array([[1.4, 0.1], [0.1, 0.9]])
S = sqrtm(Sr)
M = S @ Sg @ S
fid_2d = ((mr2 - mg2) ** 2).sum() + np.trace(Sr + Sg - 2 * sqrtm(M))
print(f"2D: |dmu|^2 = {((mr2-mg2)**2).sum():.6f}")
print(f"2D: Tr(Sr+Sg-2(Sr^1/2 Sg Sr^1/2)^1/2) = {np.trace(Sr+Sg-2*sqrtm(M)):.6f}")
print(f"2D FID = {fid_2d:.6f}")

# 退化到一维（协方差退化成标量）应与 1D 公式一致
A = np.array([[1.0]]); B = np.array([[1.44]])
fid_chk = 0.3 ** 2 + np.trace(A + B - 2 * sqrtm(sqrtm(A) @ B @ sqrtm(A)))
print(f"退化校验（1D 公式应约等于 {0.09 + (1.0-1.2)**2:.6f}）: {fid_chk:.6f}")
print("结论：FID 的两项分别对应『均值偏移』与『协方差（多样性/相关性）差异』")
''',
    ),
]


def run_example(code: str) -> tuple[str, int]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    p = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=300,
    )
    return p.stdout, p.returncode


def build_examples(check_only: bool) -> None:
    out_dir = CH / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (name, title, code) in enumerate(EXAMPLES, 1):
        stdout, rc = run_example(code)
        status = "OK " if rc == 0 else f"RC={rc}"
        print(f"[{status}] {name} ({len(stdout)} chars)")
        if rc != 0:
            print(stdout)
            err = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                 encoding="utf-8")
            print("STDERR:", err.stderr[:2000])
            raise SystemExit(f"示例 {name} 运行失败")
        if check_only:
            continue
        obj = {
            "title": title,
            "code_lang": "python",
            "code_std": "python3",
            "stdin": "",
            "expected_output": stdout,
            "code": code,
        }
        (out_dir / f"{name}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------- exercises
EXERCISES = {
    "meta": {
        "chapter": "ai-ch09",
        "title": "生成模型 —— 习题集",
        "count": 8,
        "note": "8 题，基础题 3 + 算法题 5（平台题仅存元数据与链接，不复述题面）",
    },
    "items": [
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 3,
            "title": "VAE 的 KL 项在做什么",
            "content_md": "VAE 的目标是 ELBO = 重建项 − KL(q(z|x)||p(z))。关于 KL 项的必要性，下列说法正确的是：",
            "answer": {
                "correct": ["C"],
                "explain": "KL 项把每个样本的后验拉向先验 N(0,I)，这才使『从先验采样再解码』有意义，从而具备生成能力。\n\nA 错：去掉 KL 项就是普通 AE，隐空间无序、不能采样生成；B 错：KL 项限制的是隐编码的信息量（rate），不是重建误差上限；D 错：KL 项不增加参数，也不改变网络结构。"
            },
            "explanation": "只保留重建项 = AE，只有两项同时存在才有生成模型语义。",
            "tags": ["VAE", "ELBO", "KL"],
            "source": "self",
            "source_ref": "Kingma & Welling, 2013 · Auto-Encoding Variational Bayes",
            "options": [
                {"key": "A", "text": "它是可选项：去掉 KL 项后模型退化成更强的自编码器，重建更准"},
                {"key": "B", "text": "它保证重建误差单调下降，否则训练不收敛"},
                {"key": "C", "text": "它把后验约束到先验附近，使先验采样点能被解码成有意义的样本"},
                {"key": "D", "text": "它通过增加参数容量来提高隐空间的表达能力"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "GAN 最优判别器的形式",
            "content_md": "固定生成器 G，使 GAN 目标 $\\mathbb{E}_{p_{data}}[\\log D]+\\mathbb{E}_{p_g}[\\log(1-D)]$ 最大化的判别器是：",
            "answer": {
                "correct": ["B"],
                "explain": "对 $D(x)$ 逐点求导置零可得 $D^*(x)=\\frac{p_{data}(x)}{p_{data}(x)+p_g(x)}$，即密度比 $\\frac{p_{data}}{p_{data}+p_g}$。代回目标函数得 $-\\log4+2D_{JS}(p_{data}\\|p_g)$。\n\nA 错：那是『永远判真』，不是最优；C 错：那是贝叶斯最优分类器（先验相等的假设下才与 B 同形，且分母缺失 1/2 因子）；D 错：最优判别器不依赖参数量。"
            },
            "explanation": "最优判别器本质是密度比估计器，这是把 GAN 与 f-GAN、引导采样串起来的关键恒等式。",
            "tags": ["GAN", "最优判别器", "JS散度"],
            "source": "self",
            "source_ref": "Goodfellow et al., 2014 · Generative Adversarial Nets",
            "options": [
                {"key": "A", "text": "$D^*(x)=1$（把所有样本判为真）"},
                {"key": "B", "text": "$D^*(x)=\\dfrac{p_{data}(x)}{p_{data}(x)+p_g(x)}$"},
                {"key": "C", "text": "$D^*(x)=\\dfrac{p_{data}(x)}{p_{data}(x)-p_g(x)}$"},
                {"key": "D", "text": "$D^*(x)$ 由判别器参数量决定，越大越接近最优"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "扩散模型在回归什么",
            "content_md": "DDPM 的简化目标 $\\mathcal{L}_{simple}=\\mathbb{E}\\|\\varepsilon-\\varepsilon_\\theta(x_t,t)\\|^2$ 中，网络实际预测的是：",
            "answer": {
                "correct": ["B"],
                "explain": "网络预测的是**加到 x_0 上的标准高斯噪声** $\\varepsilon$；由 $q$ 的闭式解可推出它等价于预测得分函数（差一个 $\\sqrt{1-\\bar\\alpha_t}$ 缩放）。\n\nA 错：这是 DDIM 里由 $\\varepsilon$ 反解出的量，不是网络直接输出；C 错：分类标签是无条件扩散里不存在的（条件扩散用 c 作输入）；D 错：$x_t$ 是网络输入，不是输出。"
            },
            "explanation": "ε-prediction 的目标尺度与 t 无关，因此训练最稳；它同时等价于 score prediction。",
            "tags": ["扩散模型", "DDPM", "ε预测"],
            "source": "self",
            "source_ref": "Ho et al., 2020 · Denoising Diffusion Probabilistic Models",
            "options": [
                {"key": "A", "text": "干净样本 $x_0$"},
                {"key": "B", "text": "前向过程加入的标准高斯噪声 $\\varepsilon$"},
                {"key": "C", "text": "时间步 $t$ 的类别标签"},
                {"key": "D", "text": "加噪后的样本 $x_t$ 本身"},
            ],
        },
        {
            "type": "output",
            "category": "基础题",
            "platform": "self",
            "difficulty": 3,
            "title": "手算任意步的加噪结果",
            "content_md": "设 $x_0=2.0$、$\\varepsilon=-0.5$、$\\bar\\alpha_t=0.64$。求 $x_t$，并说明 $\\bar\\alpha_t$ 与单步 $\\alpha_t$ 的关系。",
            "answer": {
                "explain": "$x_t=\\sqrt{0.64}\\cdot2.0+\\sqrt{1-0.64}\\cdot(-0.5)=0.8\\cdot2.0+0.6\\cdot(-0.5)=1.6-0.3=1.3$。\n\n$\\bar\\alpha_t=\\prod_{s=1}^{t}\\alpha_s$ 是**累积**保留系数，$\\alpha_t=1-\\beta_t$ 是单步系数；两者不可混用（用 $\\sqrt{\\alpha_t}$ 代替 $\\sqrt{\\bar\\alpha_t}$ 会让 $t$ 大时结果完全错）。\n\n附带口径：$\\mathrm{SNR}=\\bar\\alpha/(1-\\bar\\alpha)=0.64/0.36\\approx1.78$。"
            },
            "explanation": "这是扩散最基础的一次手算，公式里必须用累积系数。",
            "tags": ["扩散模型", "闭式解", "abar"],
            "source": "self",
            "source_ref": "DDPM 前向过程闭式解",
        },
        {
            "type": "output",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "手算 VAE 的 KL 项",
            "content_md": "某样本的编码器输出 $\\mu=0.5$、$\\log\\sigma^2=-1$（一维）。求 $D_{KL}(q(z|x)\\|\\mathcal{N}(0,1))$。",
            "answer": {
                "explain": "闭式：$D_{KL}=\\frac{1}{2}(\\mu^2+\\sigma^2-1-\\log\\sigma^2)$。\n\n$\\sigma^2=e^{-1}\\approx0.3679$，代入：$\\frac{1}{2}(0.25+0.3679-1+1)=\\frac{1}{2}(0.6179)\\approx0.3090$。\n\n校验：$\\mu=0,\\sigma=1$ 时结果应为 0；此处 $\\mu\\neq0$ 且 $\\sigma^2<1$，两项都贡献正数，合理。"
            },
            "explanation": "KL 闭式解是 VAE 实现的第一个公式，务必能脱稿手算。",
            "tags": ["VAE", "KL", "闭式解"],
            "source": "self",
            "source_ref": "高斯 KL 闭式解",
        },
        {
            "type": "output",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "FID 的两项分别是什么",
            "content_md": "一维情形下，真样本特征 $\\mu_r=0,\\sigma_r=1$，生成样本 $\\mu_g=0.5,\\sigma_g=1.5$。求 FID（1 维 Fréchet 距离），并指出哪一项对应『多样性差异』。",
            "answer": {
                "explain": "1 维 Fréchet：$\\mathrm{FID}=(\\mu_r-\\mu_g)^2+(\\sigma_r-\\sigma_g)^2=0.25+0.25=0.5$。\n\n- 第一项 $(\\Delta\\mu)^2$ 对应**整体偏移**（色调/结构系统性偏差）；\n- 第二项 $(\\Delta\\sigma)^2$ 对应**协方差差异**，即多样性与特征相关性结构。\n\n结论：本例两项各贡献 0.25，说明模型既偏又不够多样。"
            },
            "explanation": "FID 拆成均值项与协方差项，是解读指标的第一步。",
            "tags": ["FID", "评估", "Frechet距离"],
            "source": "self",
            "source_ref": "Heusel et al., 2017 · GANs Trained by a Two Time-Scale Update Rule",
        },
        {
            "type": "fix_error",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "这段 VAE 实现为什么训练不动",
            "content_md": "下面这段 VAE 的重参数化写法，训练时 encoder 的梯度始终为 None / 接近 0。指出问题并给出修正：\n\n```python\nsigma = decoder_ish  # 假设来自 encoder 的输出\nz = torch.distributions.Normal(mu, sigma).sample()   # 直接采样\nx_hat = dec(z)\nloss = mse(x_hat, x) + kl\nloss.backward()\n```",
            "answer": {
                "reference_code": "import torch\n# 正确：重参数化（随机性与参数解耦）\nlogvar = enc_logvar(x)                 # 输出 logvar 而非 sigma\nsigma = torch.exp(0.5 * logvar)\neps = torch.randn_like(sigma)\nz = mu + sigma * eps                   # 梯度可穿过 mu / sigma\nx_hat = dec(z)\nrec = ((x_hat - x) ** 2).mean()\nkl = 0.5 * (mu ** 2 + logvar.exp() - 1 - logvar).sum(1).mean()\nloss = rec + kl\nloss.backward()",
                "explain": "`Normal(mu, sigma).sample()` 是**不可重参数化**的采样：随机节点隔断了计算图，梯度无法回传到 `mu`/`sigma`，所以 encoder 学不到东西（或者靠 `.rsample()` 才能通）。\n\n修正两条：① 用 `z = mu + sigma * eps`（等价于 rsample）；② 让网络输出 `logvar` 而不是 `sigma`，保证正定且数值稳定，KL 直接用闭式。"
            },
            "explanation": "重参数化是 VAE 可训练的唯一原因，写错就等于 encoder 不学习。",
            "tags": ["VAE", "重参数化", "梯度"],
            "source": "self",
            "source_ref": "Kingma & Welling, 2013 · 重参数化技巧",
        },
        {
            "type": "coding",
            "category": "算法题",
            "platform": "github",
            "difficulty": 5,
            "title": "用 NumPy 实现 DDPM 采样循环",
            "content_md": "给定噪声调度与一个「完美的」噪声预测器 $\\varepsilon_\\theta(x_t,t)=\\varepsilon^\\star$（本题用解析函数模拟），实现 1000 步 DDPM 反向采样，并验证生成的样本接近目标 $x_0$。要求打印每 200 步的 $x_t$ 与 $\\hat{x}_0$ 估计。",
            "answer": {
                "reference_code": "import numpy as np\nT = 1000\nbetas = np.linspace(1e-4, 0.02, T)\nalphas = 1 - betas\nabar = np.cumprod(alphas)\nx0_target = 0.8\nrng = np.random.default_rng(0)\n\ndef eps_theta(xt, t):\n    # 完美预测器：由 xt 反解出前向时用的 eps\n    return (xt - np.sqrt(abar[t]) * x0_target) / np.sqrt(1 - abar[t])\n\nx = rng.normal()\nfor t in reversed(range(T)):\n    e = eps_theta(x, t)\n    mu = (x - betas[t] / np.sqrt(1 - abar[t]) * e) / np.sqrt(alphas[t])\n    sigma = np.sqrt(betas[t] * (1 - abar[t-1]) / (1 - abar[t])) if t > 0 else 0.0\n    x = mu + sigma * (rng.normal() if t > 0 else 0.0)\n    if t % 200 == 0:\n        x0_hat = (x - np.sqrt(1 - abar[t]) * e) / np.sqrt(abar[t])\n        print(f't={t:4d} x_t={x:+.4f} x0_hat={x0_hat:+.4f}')\nprint(f'最终样本 x_0 = {x:+.4f}（目标 {x0_target}）')",
                "explain": "关键三点：① 反向按 $t$ 从 $T-1$ 递减；② 均值用 $\\frac{1}{\\sqrt{\\alpha_t}}(x_t-\\frac{\\beta_t}{\\sqrt{1-\\bar\\alpha_t}}\\varepsilon_\\theta)$；③ 方差用后验 $\\tilde\\beta_t$，最后一步（t=0）不加噪。\n\n本题的预测器由目标反解得到，因此最终样本应精确回到 0.8 附近（误差来自随机采样的累积，量级 <1e-2）。"
            },
            "explanation": "采样循环是扩散工程的地基，四个量（α_t、β_t、ᾱ_t、σ_t）必须分清。",
            "tags": ["DDPM", "采样", "NumPy"],
            "source": "github",
            "source_ref": "hojonathanho/diffusion",
            "external_url": "https://github.com/hojonathanho/diffusion",
        },
    ],
}


# ---------------------------------------------------------------- interview
INTERVIEW = {
    "meta": {"chapter": "ai-ch09", "title": "生成模型 —— 面试题", "count": 6},
    "items": [
        {
            "question": "从目标函数的角度，VAE、GAN、扩散三者的本质区别是什么？",
            "answer_md": "三者的区别可以压缩成「优化什么」这一句：\n\n- **VAE**：优化对数似然的**下界**（ELBO = 重建 − KL）。它显式建模 $p(x)$ 的近似，因此能算似然下界、能编码；代价是样本偏糊（最优解码器输出后验均值）。\n- **GAN**：优化一个**对抗博弈**，等价于最小化 JS/W 距离。它不建模显式密度（隐式），因此样本锐利；代价是无似然、训练不稳、易模式崩塌。\n- **扩散**：优化一个**去噪回归**（$\|\\varepsilon-\\varepsilon_\\theta\|^2$），它本质是固定前向的层级 VAE、目标等价于得分匹配。既能算似然下界，又能生成高质量样本，代价是采样要几十到上千步。\n\n一句话收束：**VAE 用变分下界换可算似然，GAN 用对抗换锐利，扩散用迭代去噪换质量与稳定性**。",
            "follow_ups": [
                "为什么 VAE 的样本会糊，而扩散不会？",
                "如果把扩散的 T 设为 1，它退化成什么？",
                "哪种模型最适合做异常检测，为什么？",
            ],
            "difficulty": 4,
            "company_tags": ["字节跳动", "商汤", "百度", "阿里"],
        },
        {
            "question": "扩散模型的 ELBO 怎么推导到 L_simple？中间丢掉了什么？",
            "answer_md": "推导链四步：\n\n1. **写 ELBO**：对整条马尔可夫链求变分下界，得到 $\\mathbb{E}_q[\\log p(x_T)+\\sum_t\\log\\frac{p_\\theta(x_{t-1}|x_t)}{q(x_t|x_{t-1})}]$。\n2. **逐项配成高斯 KL**：每一项可化为 $D_{KL}(q(x_{t-1}|x_t,x_0)\\,\\|\\,p_\\theta(x_{t-1}|x_t))$，而 $q(x_{t-1}|x_t,x_0)$ 是均值 $\\tilde\\mu_t$、方差 $\\tilde\\beta_t$ 的高斯（闭式可算）。\n3. **重参数化**：把 $\\tilde\\mu_t=\\frac{1}{\\sqrt{\\alpha_t}}(x_t-\\frac{\\beta_t}{\\sqrt{1-\\bar\\alpha_t}}\\varepsilon)$ 代进去，最小化 KL 变成最小化 $\\|\\varepsilon-\\varepsilon_\\theta(x_t,t)\\|^2$。\n4. **丢权重**：KL 项的系数是 $\\frac{\\beta_t^2}{2\\sigma_t^2\\alpha_t(1-\\bar\\alpha_t)}$，DDPM 直接令其等于 1，得到 $\\mathcal{L}_{\\text{simple}}$。\n\n丢掉的是**按时间步的加权**。理论代价：目标不再是严格的 ELBO（等价于换了一个 SNR 重加权的目标）；实践收益：低噪声步的权重不再被过度放大，模型把容量放在结构上，FID 更好。这是「理论正确 ≠ 效果最好」的经典案例。",
            "follow_ups": [
                "如果保留原始权重会怎样？",
                "为什么预测 ε 比预测 x0 更稳？",
                "v-prediction 在什么场景下更优？",
            ],
            "difficulty": 5,
            "company_tags": ["OpenAI", "Stability AI", "快手", "蚂蚁"],
        },
        {
            "question": "DDIM 为什么能在不重新训练的情况下把采样步数从 1000 降到 20？",
            "answer_md": "核心是**训练与采样解耦**：DDPM 的训练目标只依赖前向边缘分布 $q(x_t|x_0)$，不依赖反向链的马尔可夫性。DDIM 构造了一族**非马尔可夫**的前向过程 $q_\\sigma(x_{t-1}|x_t,x_0)$，只要它的边缘 $q(x_t|x_0)$ 与 DDPM 相同，训练好的 $\\varepsilon_\\theta$ 就完全可复用。\n\n在这族过程里 $\\sigma_t$ 是一个自由参数：\n\n- $\\sigma_t=\\tilde\\beta_t$（最大）→ 退回 DDPM 的随机采样；\n- $\\sigma_t=0$ → **确定性**映射 $x_{t-1}=\\sqrt{\\bar\\alpha_{t-1}}\\hat{x}_0+\\sqrt{1-\\bar\\alpha_{t-1}}\\varepsilon_\\theta$。\n\n因为不再需要满足马尔可夫链的逐步约束，采样可以**只取时间步的一个子序列**（如 20 个点），每步仍然朝同一个确定性 ODE 的解靠近。$\\sigma=0$ 时该 ODE 就是概率流 ODE，轨迹唯一，因此同一起点得到同一结果（可复现、可插值）。\n\n代价：步数过少时细节损失、确定性采样少了随机探索导致多样性略降。",
            "follow_ups": [
                "DDIM 与概率流 ODE 的关系？",
                "为什么 η=0 时可以做隐空间插值？",
                "DPM-Solver 相比 DDIM 改进在哪？",
            ],
            "difficulty": 5,
            "company_tags": ["Stability AI", "Midjourney", "阿里", "腾讯"],
        },
        {
            "question": "CFG 为什么有效？s 调大会发生什么？",
            "answer_md": "CFG 的公式是 $\\tilde\\varepsilon=\\varepsilon(x_t,c=\\varnothing)+s(\\varepsilon(x_t,c)-\\varepsilon(x_t,\\varnothing))$。\n\n**为什么有效**：由贝叶斯公式 $\\nabla\\log p(x|c)=\\nabla\\log p(x)+\\nabla\\log p(c|x)$，而 $\\varepsilon_{\\text{cond}}-\\varepsilon_{\\text{uncond}}$ 近似于 $\\nabla\\log p(c|x)$（乘一个 $-\\sqrt{1-\\bar\\alpha}$ 的缩放）。所以 CFG 是在**显式地加上条件似然的梯度**，$s$ 就是它的强度。$s>1$ 等价于把条件后验抬到 $s$ 次方，分布更尖锐——更贴 prompt、多样性更低。\n\n**s 调大的问题**：① 放大的是整条 score，包含与条件无关的高频分量 → 过饱和、色彩崩坏、细节「烧焦」；② 采样成本翻倍（每步两次前向）；③ 多样性趋零，$s\\to\\infty$ 时退化成一个「最符合条件」的确定性输出。\n\n工程口径：$s\\in[4,9]$ 是常用区间，且可做时间调度（前期小、后期大），既能保证结构又能保住细节。",
            "follow_ups": [
                "为什么训练时要随机丢弃条件？",
                "CFG 与 classifier guidance 的区别？",
                "如何在不翻倍成本的前提下近似 CFG？",
            ],
            "difficulty": 5,
            "company_tags": ["字节跳动", "小红书", "美团", "百度"],
        },
        {
            "question": "FID 有什么缺陷？你会怎么设计一套完整的生成模型评估？",
            "answer_md": "FID 的四个已知问题：\n\n1. **依赖高斯假设**：只匹配 Inception 特征的一二阶矩，对多峰、流形结构无感 → 对模式崩塌不敏感；\n2. **样本数偏差**：协方差估计有偏，2k 与 50k 样本的 FID 不可比；\n3. **预处理敏感**：分辨率、resize 方式、归一化、Inception 权重不同，能差 5-10 个点；\n4. **与人类偏好不单调**：FID 最优不一定是人最喜欢。\n\n完整评估设计（三层）：\n\n- **第一层（分布级）**：FID（配固定 50k 真样本特征缓存）+ KID（小样本无偏）+ Precision/Recall（把保真与覆盖拆开）。\n- **第二层（语义级）**：CLIPScore / ImageReward（文图一致性）、类别条件准确率（可控性是否生效）。\n- **第三层（人评级）**：成对偏好胜率（A/B），并报告置信区间；产品上线前必须有人评。\n\n另外必须固定评估管线版本（VAE、tokenizer、分辨率、Inception 权重），否则指标变化无法归因。",
            "follow_ups": [
                "Precision/Recall 分别对应生成模型的什么错误？",
                "为什么小样本要用 KID 而不是 FID？",
                "如何检测模式崩塌？",
            ],
            "difficulty": 4,
            "company_tags": ["商汤", "旷视", "字节跳动", "腾讯"],
        },
        {
            "question": "只有一张 24G 显卡和一周时间，要做一个垂直领域的图像生成产品，你会怎么选型？",
            "answer_md": "选型按「算力 → 方案」倒推，而不是先选模型：\n\n**1. 不从头训**。24G 单卡无法做基础模型的预训练（几十万步、多卡），只做**微调或蒸馏**。\n\n**2. 基座选择**：优先选有成熟生态与蒸馏版的开放基座（SDXL / SD3.5 / Flux 系列），因为 ① 有大量 LoRA 与 ControlNet 可直接用；② 有 1-4 步蒸馏版满足实时性；③ diffusers/ComfyUI 能直接跑。\n\n**3. 定制路径**（成本从低到高）：\n- 先试 **LoRA（rank 8-32）+ 少量精标数据（几十到几百张）**，24G 够用；\n- 不够再加 **DreamBooth/文本编码器微调**；\n- 要控构图就用 **ControlNet**，别去微调主干。\n\n**4. 数据**：垂直领域的关键不是数量而是**一致性**（同一风格、同一质检口径），并保留 10% 做留出集算 FID/CLIPScore。\n\n**5. 推理**：DPM-Solver++ / LCM 20 步以内 + fp16 + xformers/FlashAttention；批量与缓存 prompt embedding。\n\n**6. 验收**：FID 作护栏 + 人评胜率 + 「结构错误率」（手指数、文字、logo 崩坏）三项。\n\n一句话：**单卡做产品 = 选对基座 + LoRA + ControlNet + 少步采样 + 人评兜底**，不要试图训模型。",
            "follow_ups": [
                "LoRA 的 rank 怎么选？",
                "垂直领域数据只有 200 张，怎么防过拟合？",
                "如何评估『风格一致性』这种主观指标？",
            ],
            "difficulty": 4,
            "company_tags": ["小红书", "得物", "快手", "美图"],
        },
    ],
}


# ---------------------------------------------------------------- project
PROJECT = {
    "meta": {
        "chapter": "ai-ch09",
        "title": "生成模型 —— 综合项目",
        "category": "dl",
        "count": 1,
    },
    "items": [
        {
            "title": "从零实现 VAE 与 DDPM，并做定量对比（NumPy only）",
            "requirement_md": "只用 NumPy（**不允许** PyTorch/TensorFlow）在一个 2 维玩具数据集（如双月/双峰）上完成两代生成模型的实现与对比，所有指标必须被打印且可复现（固定种子）。\n\n1. **VAE**：编码器/解码器各一层 MLP，输出 `mu` 与 `logvar`；手写重参数化与高斯 KL 闭式解；训练后打印 ELBO 曲线（前 10 个 epoch 的均值）、KL 项与重建项的量级。\n2. **扩散（DDPM）**：$T=200$，cosine 调度；噪声预测器用两层 MLP（时间步用正弦编码注入）；训练目标是 $\\|\\varepsilon-\\varepsilon_\\theta\\|^2$；采样用 DDPM 与 DDIM（$\\eta=0$，20 步）各跑一次。\n3. **定量对比**：对两种模型各生成 5000 个样本，计算 ① 均值/协方差与真实分布的 Fréchet 距离；② 网格覆盖率（把平面划成 20×20 格，统计被生成样本覆盖的格子比例）；③ 生成 5000 个样本的耗时。\n4. **消融**：DDPM 分别用 linear 与 cosine 调度训练，比较最终 Fréchet 距离与覆盖率的差异；VAE 用 $\\beta\\in\\{0.1,1,4\\}$ 各训一次，画出「重建误差 vs KL」的取舍。\n5. **报告**：用一张表给出 5 个配置的（Fréchet↓、覆盖率↑、采样耗时↓），并解释排名背后的原因（KL 项的作用、调度对 SNR 分布的影响、DDIM 跳步的代价）。",
            "tasks": [
                {
                    "title": "实现 VAE 并跑通训练",
                    "verification": {
                        "type": "output",
                        "desc": "打印 ELBO、重建项、KL 项三个数；KL 项不应在训练早期就贴 0（否则即后验坍塌，需调整 β 或网络容量）；重参数化的梯度检查：对 mu 做数值梯度与解析梯度对比，相对误差 < 1e-4。",
                    },
                },
                {
                    "title": "实现 DDPM 前向与训练",
                    "verification": {
                        "type": "output",
                        "desc": "打印 x_t 的均值/方差并与 sqrt(abar)*x0、1-abar 对账（误差 < 1e-6）；训练 loss 应在前 1000 步内下降一个数量级以上。",
                    },
                },
                {
                    "title": "DDPM 与 DDIM 采样",
                    "verification": {
                        "type": "output",
                        "desc": "DDPM 200 步与 DDIM 20 步各生成 5000 样本，打印两者的 Fréchet 距离与耗时；DDIM 耗时应约为 DDPM 的 1/10，Fréchet 差距不应超过 2 倍。",
                    },
                },
                {
                    "title": "调度消融",
                    "verification": {
                        "type": "output",
                        "desc": "linear 与 cosine 各训一次，打印两者的 abar 曲线关键点（t/T=0.25/0.5/0.75）与最终 Fréchet；给出「cosine 不差于 linear」的结论或反例。",
                    },
                },
                {
                    "title": "β 的率失真取舍",
                    "verification": {
                        "type": "output",
                        "desc": "β∈{0.1,1,4} 三组各打印重建误差与 KL；应观察到 β↑ → KL↓、重建误差↑ 的单调趋势（允许小幅波动）。",
                    },
                },
                {
                    "title": "覆盖率与耗时对比表",
                    "verification": {
                        "type": "output",
                        "desc": "输出 5 个配置的表（Fréchet、覆盖率、采样耗时），并给出 200 字以内的归因解释；覆盖率用 20×20 网格统计，数值在 [0,1] 内。",
                    },
                },
            ],
            "tags": ["VAE", "DDPM", "DDIM", "NumPy", "定量对比"],
        }
    ],
}


def main() -> int:
    check_only = "--check" in sys.argv
    build_examples(check_only)
    if check_only:
        return 0
    (CH / "exercises.json").write_text(
        json.dumps(EXERCISES, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (CH / "interview.json").write_text(
        json.dumps(INTERVIEW, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (CH / "project.json").write_text(
        json.dumps(PROJECT, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"写出 exercises({len(EXERCISES['items'])}) / interview({len(INTERVIEW['items'])}) / project(1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
