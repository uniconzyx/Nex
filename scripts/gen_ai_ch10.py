# -*- coding: utf-8 -*-
"""生成 ai-ch10（训练工程与规模化）的 examples / exercises / interview / project。

原则同 gen_ai_ch09.py：expected_output 全部来自真实运行；只用 NumPy。

用法：
    python scripts/gen_ai_ch10.py            # 生成全部
    python scripts/gen_ai_ch10.py --check    # 只跑示例并打印状态
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "content" / "ai" / "ai-ch10"

EXAMPLES: list[tuple[str, str, str]] = [
    (
        "ex01-init-variance",
        "三种初始化下 50 层前向的激活方差",
        r'''
import numpy as np
rng = np.random.default_rng(0)
d, L, n = 256, 50, 1024

def run(mode):
    x = rng.normal(size=(n, d))
    stds = []
    for l in range(L):
        if mode == "naive":
            std = 1.0
        elif mode == "xavier":
            std = np.sqrt(2.0 / (d + d))
        else:  # he
            std = np.sqrt(2.0 / d)
        W = rng.normal(0, std, (d, d))
        x = np.maximum(x @ W, 0)          # ReLU
        if (l + 1) % 10 == 0:
            stds.append(x.std())
    return stds

print(f"每层 std（d={d}, ReLU, 50 层）：")
print("层数      " + "".join(f"{i:>10d}" for i in (10, 20, 30, 40, 50)))
for mode in ("naive", "xavier", "he"):
    s = run(mode)
    print(f"{mode:<9s}" + "".join(f"{v:10.2e}" for v in s))
print()
print("理论：Xavier std=sqrt(2/(nin+nout))={:.5f}, He std=sqrt(2/nin)={:.5f}".format(
    np.sqrt(2.0 / (2 * d)), np.sqrt(2.0 / d)))
print("结论：naive 初始化逐层指数爆炸；Xavier 配 ReLU 会指数衰减；")
print("      He 是唯一让 50 层后激活仍与输入同量级的选项（0.45~0.74 vs 1e52 / 1e-8）")
''',
    ),
    (
        "ex02-spectral-norm",
        "随机矩阵 vs 正交矩阵的谱半径",
        r'''
import numpy as np
rng = np.random.default_rng(1)
n = 256

G = rng.normal(0, 1.0 / np.sqrt(n), (n, n))     # He 缩放后的高斯矩阵
sv = np.linalg.svd(G, compute_uv=False)
Q, _ = np.linalg.qr(rng.normal(size=(n, n)))    # 正交矩阵
sv_q = np.linalg.svd(Q, compute_uv=False)

print(f"Gaussian/sqrt(n): max sigma = {sv.max():.4f}, min = {sv.min():.4f}, 条件数 = {sv.max()/sv.min():.2f}")
print(f"正交矩阵:          max sigma = {sv_q.max():.4f}, min = {sv_q.min():.4f}, 条件数 = {sv_q.max()/sv_q.min():.2f}")
print(f"理论上高斯缩放矩阵 max sigma -> 2（Marchenko-Pastur 上界 2*sqrt(n)*1/sqrt(n)=2）")
print("结论：即使按 1/sqrt(n) 缩放，高斯矩阵的谱范数仍约 2（每层放大 2 倍），")
print("      正交初始化把奇异值全钉在 1，才是真正的『等距』，因而深链/RNN 更稳")
''',
    ),
    (
        "ex03-layernorm-rmsnorm",
        "LayerNorm 与 RMSNorm 的数值对比",
        r'''
import numpy as np
x = np.array([0.5, -1.5, 2.0, 3.0, -0.5])
eps = 1e-5

mu = x.mean()
var = x.var()
ln = (x - mu) / np.sqrt(var + eps)
rms = 1.0 / np.sqrt((x ** 2).mean() + eps)
y_rms = x * rms

print(f"x      = {x}")
print(f"mean={mu:.4f} var={var:.4f} rms={np.sqrt((x**2).mean()):.4f}")
print(f"LayerNorm 输出 = {np.round(ln, 6)}  (mean={ln.mean():.2e}, std={ln.std():.6f})")
print(f"RMSNorm  输出 = {np.round(y_rms, 6)}  (mean={y_rms.mean():.6f}, rms={np.sqrt((y_rms**2).mean()):.6f})")
print()
print("差异：LN 减均值 + 除 std，输出零均值单位方差；RMSNorm 只除 RMS，保留均值偏移")
print(f"LN 不改变方向（与 x-mean 同向）；RMSNorm 与 x 同向，但尺度只由二阶矩决定")
print("成本：LN 需一次减均值 + 一次方差归约；RMSNorm 只做平方均值归约（少一次归约，kernel 更快）")
''',
    ),
    (
        "ex04-preln-postln",
        "Pre-LN 与 Post-LN 的信号传播对比",
        r"""
import numpy as np
rng = np.random.default_rng(3)
d, L, eps = 32, 24, 1e-5

def ln_fwd(x):
    mu = x.mean(-1, keepdims=True)
    inv = 1.0 / np.sqrt(x.var(-1, keepdims=True) + eps)
    xhat = (x - mu) * inv
    return xhat, (xhat, inv)

def ln_bwd(dy, cache):
    xhat, inv = cache
    dd = xhat.shape[-1]
    return (inv / dd) * (dd * dy - dy.sum(-1, keepdims=True)
                         - xhat * (dy * xhat).sum(-1, keepdims=True))

def experiment(mode):
    # W ~ N(0, 1/d)：F(x)=xW^T 的方差与 Var(x) 同量级（残差分支会 doubling）
    Ws = [rng.normal(0, np.sqrt(1.0 / d), (d, d)) for _ in range(L)]
    x = rng.normal(size=(8, d))
    h, caches, norm_in = x, [], []
    for W in Ws:
        if mode == "pre":
            norm_in.append(h.var())          # 归一化层的输入就是残差流 h
            y, c = ln_fwd(h)
            h = h + y @ W.T
        else:
            u = h + h @ W.T                  # 先加残差再归一化
            norm_in.append(u.var())
            y, c = ln_fwd(u)
            h = y
        caches.append((c, W))
    g = np.ones_like(h) / np.sqrt(h.size)
    gn = []
    for l in reversed(range(L)):
        c, W = caches[l]
        if mode == "pre":
            dln = ln_bwd(g @ W, c)
            g = g + dln
        else:
            du = ln_bwd(g, c)
            g = du + du @ W
        gn.append(float(np.linalg.norm(g)))
    return norm_in, gn[::-1]

for mode, name in (("pre", "Pre-LN "), ("post", "Post-LN")):
    ni, gn = experiment(mode)
    pick = [ni[i] for i in (0, 5, 11, 17, 23)]
    print(f"{name} 归一化层输入的方差（第 1/6/12/18/24 层）: " + "  ".join(f"{v:.2e}" for v in pick))
    gp = [gn[i] for i in (0, 5, 11, 17, 23)]
    print(f"{name} 反传到各层的梯度范数            : " + "  ".join(f"{v:.2e}" for v in gp))
    print(f"{name} 首层/末层 梯度范数比 = {gn[0]/gn[-1]:.3e}")
    print()
print("读数据：Pre-LN 的残差流方差线性增长（0.9 -> 25），反传梯度始终 O(1)，与深度无关；")
print("        Post-LN 24 层内梯度衰减到 1e-17 量级（相对输出端缩小 17 个数量级），")
print("        浅层几乎收不到有效梯度 -> 这就是 Post-LN 必须靠 warmup + 更小 lr 才能启动的原因；")
print("        Pre-LN 把 LN 关进分支内，残差流是纯恒等路径，梯度可直通")
""",
    ),
    (
        "ex05-adam-vs-adamw",
        "Adam+L2 与 AdamW 的衰减强度差异",
        r'''
import numpy as np

# 纯衰减场景：数据梯度为 0，只观察 weight decay 单独作用时的行为
def run(decoupled, theta0, steps=200, lr=0.05, wd=0.1, b1=0.9, b2=0.999, eps=1e-8):
    theta = theta0.astype(float).copy()
    m = np.zeros_like(theta); v = np.zeros_like(theta)
    trace = []
    for t in range(1, steps + 1):
        g = np.zeros_like(theta)                 # 无数据梯度
        if not decoupled:
            g = g + wd * theta                   # L2：进梯度
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g ** 2
        theta = theta - lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + eps)
        if decoupled:
            theta = theta - lr * wd * theta      # 解耦：直接乘 (1 - lr*wd)
        if t in (50, 100, 200):
            trace.append((t, theta.copy()))
    return theta, trace

theta0 = np.array([0.1, 1.0, 10.0])
fails, tr_f = run(False, theta0)
ok, tr_d = run(True, theta0)
print("初始 theta = [0.1, 1.0, 10.0]（跨越两个数量级），wd=0.1, lr=0.05, 200 步纯衰减")
print()
for name, tr in (("Adam+L2", tr_f), ("AdamW  ", tr_d)):
    for t, th in tr:
        print(f"{name}  step {t:>3d}: {np.round(th, 6)}")
    print()
print(f"最终 Adam+L2: {np.round(fails, 4)}  -> 小参数被推过零，大参数几乎没瘦")
print(f"最终 AdamW  : {np.round(ok, 4)}  -> 所有参数同比例缩放")
print(f"理论比例 (1-lr*wd)^200 = {(1-0.05*0.1)**200:.6f}，10.0*该值 = {10.0*(1-0.05*0.1)**200:.4f}")
print()
print("结论：Adam+L2 的衰减是『每步固定步长』（与参数大小无关），因为它被 sqrt(v) 归一化了；")
print("      AdamW 是『按比例衰减』（大参数衰减多、小参数衰减少），这才是 weight decay 的本意")
''',
    ),
    (
        "ex06-warmup-cosine",
        "warmup + cosine 调度曲线",
        r'''
import numpy as np
peak, warmup, total, floor_ratio = 3e-4, 2000, 20000, 0.1
lr_min = peak * floor_ratio

def lr_at(t):
    if t < warmup:
        return peak * (t + 1) / warmup
    p = (t - warmup) / (total - warmup)
    return lr_min + 0.5 * (peak - lr_min) * (1 + np.cos(np.pi * p))

print("step       lr")
for t in (0, 999, 1999, 2000, 5000, 11000, 15000, 19999):
    print(f"{t:>6d}   {lr_at(t):.3e}")
print()
print(f"峰值 {peak:.1e}，warmup {warmup} 步（占 10%），末端下限 {lr_min:.1e}")
print(f"t=11000 处 cos 相位 = half，lr 恰为 (peak+min)/2 = {(peak+lr_min)/2:.3e}")
print("结论：warmup 段线性升、cosine 段对称降；总『面积』(lr 积分) 决定等效训练步长预算")
''',
    ),
    (
        "ex07-grad-clip",
        "全局范数裁剪：只改长度不改方向",
        r'''
import numpy as np
g = np.array([3.0, 4.0, 0.0])     # ||g|| = 5
c = 1.0
norm = np.linalg.norm(g)
scale = min(1.0, c / norm)
g_clip = g * scale
cos = float(g @ g_clip / (norm * np.linalg.norm(g_clip)))

print(f"原梯度 norm = {norm:.4f}, 方向 = {g/norm}")
print(f"裁剪系数 scale = {scale:.4f}")
print(f"裁剪后 norm = {np.linalg.norm(g_clip):.4f}, 方向 = {g_clip/np.linalg.norm(g_clip)}")
print(f"方向余弦 = {cos:.10f}（=1 表示方向完全不变）")
print()
print("对比逐元素裁剪 (clamp to [-1,1])：")
g_el = np.clip(g, -c, c)
print(f"  {g_el}, norm={np.linalg.norm(g_el):.4f}, 方向={g_el/np.linalg.norm(g_el)}")
print("  方向余弦 = {:.4f} -> 方向被改变".format(float(g @ g_el / (norm * np.linalg.norm(g_el)))))
print("结论：全局范数裁剪是等比缩放（保方向，等价于降学习率）；逐元素裁剪会扭曲更新方向")
''',
    ),
    (
        "ex08-fp16-overflow",
        "fp16 的上溢/下溢与 loss scaling",
        r'''
import numpy as np
np.seterr(over="ignore", under="ignore")

print(f"fp16 最大有限值 = {np.finfo(np.float16).max}")
print(f"fp16 最小正规数 = {np.finfo(np.float16).tiny:.3e}")
print(f"fp16 最小可表示（含 denormal） = {np.nextafter(np.float16(0), np.float16(1)):.3e}")

big = np.float16(60000) + np.float16(10000)
print(f"60000 + 10000 (fp16) = {big}   -> 上溢为 inf")
tiny = np.float16(1e-8)
print(f"1e-8 存成 fp16 = {tiny}        -> 下溢为 0（梯度消失的隐形原因）")

S = 1 << 14
scaled = np.float16(1e-8 * S)
print(f"loss scale S=2^14={S}: 1e-8*S = {1e-8*S:.3e} -> fp16 = {scaled}  (可表示)")
print(f"还原：{scaled} / S = {float(scaled)/S:.3e}")
print()
print(f"bf16 的指数位与 fp32 相同，最大有限值 = {np.finfo(np.float32).max:.3e}（Python 无原生 bf16，用 fp32 范围代表）")
print("结论：fp16 必须做 loss scaling 且需 fp32 主权重；bf16 范围够大，无需缩放")
''',
    ),
    (
        "ex09-memory-accounting",
        "训练显存账：16 B/参数从哪来",
        r'''
import numpy as np
per_param = {"fp16 参数": 2, "fp16 梯度": 2, "fp32 主权重": 4, "Adam m": 4, "Adam v": 4}
total_per_param = sum(per_param.values())

print("每参数字节数：")
for k, v in per_param.items():
    print(f"  {k:<12s} {v} B")
print(f"  {'合计':<12s} {total_per_param} B/参数")
print()
print("模型规模 -> 仅模型状态显存（不含激活）：")
for name, N in (("1B", 1e9), ("7B", 7e9), ("13B", 13e9), ("70B", 70e9)):
    gb = total_per_param * N / (1024 ** 3)
    print(f"  {name:>4s}: {gb:7.1f} GB   单张 80GB 卡能否装下: {'可以' if gb < 80 else '不行'}")

print()
print("激活估算（含重计算关闭）：batch*seq*hidden*L*2B 量级")
b, s, h, L = 8, 2048, 4096, 32
act = b * s * h * L * 2 * 12 / (1024 ** 3)   # 12x：MLP 中间层(4h)、注意力、多个张量
print(f"  7B 级模型 b={b}, s={s}, h={h}, L={L} -> 约 {act:.1f} GB（×12 系数的数量级估算）")
print(f"  开激活重计算后可降到 O(sqrt(L)) 倍量级，约 {act/np.sqrt(L):.1f} GB")
print()
print("对照：推理 fp16 只需 2 B/参数 -> 7B 约 {:.1f} GB（差 8 倍）".format(2 * 7e9 / (1024 ** 3)))
''',
    ),
    (
        "ex10-zero-stages",
        "ZeRO 三阶段的每卡显存（8 卡）",
        r'''
import numpy as np
N, K = 7e9, 8
opt_states = 12          # fp32 master 4 + m 4 + v 4
param16, grad16 = 2, 2

def gb(bytes_per_param):
    return bytes_per_param * N / (1024 ** 3)

print(f"7B 模型，{K} 卡，单位 GB（仅模型状态）")
print(f"{'方案':<12s}{'B/参数':>10s}{'每卡显存':>12s}   说明")
rows = [
    ("DDP/基线", param16 + grad16 + opt_states, "完整副本"),
    ("ZeRO-1", param16 + grad16 + opt_states / K, "只分片优化器状态"),
    ("ZeRO-2", param16 + grad16 / K + opt_states / K, "再分片梯度"),
    ("ZeRO-3/FSDP", (param16 + grad16 + opt_states) / K, "再分片参数（通信最多）"),
]
for name, bpp, note in rows:
    print(f"{name:<12s}{bpp:>10.2f}{gb(bpp):>12.1f}   {note}")

print()
print(f"显存节省倍数（相对基线）：ZeRO-1 {16/(2+2+12/K):.1f}x, ZeRO-2 {16/(2+2/K+12/K):.1f}x, ZeRO-3 {K:.0f}x")
print("代价：ZeRO-3 前向/反向需逐层 gather 参数，通信量约为基线 1.5 倍")
print("结论：先 ZeRO-2（几乎无额外通信、收益最大），装不下再 ZeRO-3")
''',
    ),
    (
        "ex11-chinchilla",
        "Chinchilla：给定算力求最优参数量与数据量",
        r'''
import numpy as np
print("约束 C = 6*N*D，最优 D = 20*N  =>  C = 120*N^2  =>  N = sqrt(C/120)")
print()
for C in (1e21, 1e22, 1e23, 1e24):
    N = np.sqrt(C / 120)
    D = 20 * N
    print(f"C={C:.0e} FLOPs -> N_opt={N/1e9:7.2f}B 参数, D_opt={D/1e9:8.1f}B tokens, "
          f"校验 6ND={6*N*D:.2e}")

print()
print("反推：7B 模型的 Chinchilla 最优数据量 = {:.0f}B tokens".format(7e9 * 20 / 1e9))
print("过训练：7B 训 2T tokens -> C = {:.2e} FLOPs（约 Chinchilla 最优的 {:.1f} 倍算力）".format(
    6 * 7e9 * 2e12, 6 * 7e9 * 2e12 / (6 * 7e9 * 140e9)))
print()
print("结论：C 每涨 10 倍，N 与 D 各涨 ~3.16 倍（sqrt(10)）；")
print("      过训练是『用训练算力换推理成本』，Chinchilla 只优化训练侧")
''',
    ),
    (
        "ex12-grad-accum",
        "梯度累积与真大 batch 的等价性（以及 BN 的反例）",
        r'''
import numpy as np
rng = np.random.default_rng(5)
n_in, n_out, B, K = 6, 4, 16, 4
X = rng.normal(size=(B, n_in))
Y = rng.normal(size=(B, n_out))
W = rng.normal(0, 0.3, (n_in, n_out))
b = np.zeros(n_out)

def grad(Xb, Yb):
    pred = Xb @ W + b
    err = 2 * (pred - Yb) / pred.size
    return Xb.T @ err, err.sum(0)

# ① 真大 batch
gW_full, gb_full = grad(X, Y)
# ② 梯度累积：4 个 micro-batch，各自求平均后取平均
gW_acc = np.zeros_like(W); gb_acc = np.zeros_like(b)
for k in range(K):
    sl = slice(k * (B // K), (k + 1) * (B // K))
    gw, gbi = grad(X[sl], Y[sl])
    gW_acc += gw; gb_acc += gbi          # 每个 micro-batch 内部已按自身样本数平均
gW_acc /= K; gb_acc /= K
print(f"① 真大 batch 与累积的 dW 最大差 = {np.abs(gW_full-gW_acc).max():.3e}")
print(f"② 两者 db 最大差              = {np.abs(gb_full-gb_acc).max():.3e}")
print("  -> 无状态层下数学等价（误差为浮点误差量级）")

# ③ 反例：micro-batch 内的『批归一化』破坏等价
def bn_stats(Xb):
    return Xb.mean(0), Xb.var(0)

mu_full, var_full = bn_stats(X)
mus, vars_ = [], []
for k in range(K):
    sl = slice(k * (B // K), (k + 1) * (B // K))
    m, v = bn_stats(X[sl]); mus.append(m); vars_.append(v)
mu_avg = np.mean(mus, 0); var_avg = np.mean(vars_, 0)
print(f"③ BN 统计量差异：均值 max|diff|={np.abs(mu_full-mu_avg).max():.4f}, "
      f"方差 max|diff|={np.abs(var_full-var_avg).max():.4f}")
print("  -> micro-batch 的统计量 != 全 batch 统计量，因此 BN 网络下『累积 != 大 batch』")
print()
print("结论：累积前 loss 必须除 K；BN/SyncBN 是累积与大 batch 不等价的唯一结构原因（另加 dropout 的随机性差异）")
''',
    ),
]


def run_example(code: str) -> tuple[str, int]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=300)
    return p.stdout, p.returncode


def build_examples(check_only: bool) -> None:
    out_dir = CH / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, title, code in EXAMPLES:
        stdout, rc = run_example(code)
        print(f"[{'OK ' if rc == 0 else 'ERR'}] {name} ({len(stdout)} chars)")
        if rc != 0:
            p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                               encoding="utf-8")
            print(stdout, p.stderr[:2000])
            raise SystemExit(f"{name} 运行失败")
        if check_only:
            continue
        obj = {
            "title": title, "code_lang": "python", "code_std": "python3",
            "stdin": "", "expected_output": stdout, "code": code,
        }
        (out_dir / f"{name}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


EXERCISES = {
    "meta": {
        "chapter": "ai-ch10",
        "title": "训练工程与规模化 —— 习题集",
        "count": 8,
        "note": "8 题，基础题 4 + 算法题 4（平台题仅存元数据与链接，不复述题面）",
    },
    "items": [
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 3,
            "title": "为什么必须存 fp32 主权重",
            "content_md": "混合精度训练时，参数更新为什么必须在 fp32 主副本上做，而不能直接更新 fp16 参数？",
            "answer": {
                "correct": ["B"],
                "explain": "fp16 的 ulp 随数值大小变化：参数在 1 附近时 ulp 约 $2^{-10}\\approx10^{-3}$，而典型更新量 $\\eta g$ 可能是 $10^{-5}$ 量级，直接加到 fp16 上会被舍入掉（$\\theta+\\Delta\\theta=\\theta$），训练「在跑但参数不变」。\n\nA 错：与算力无关；C 错：fp16 存得下参数；D 错：梯度裁剪解决的是爆炸，不解决舍入。"
            },
            "explanation": "master weights 是混合精度可训练的必要条件，不是可选项。",
            "tags": ["混合精度", "master weights", "fp16"],
            "source": "self",
            "source_ref": "Micikevicius et al., 2017 · Mixed Precision Training",
            "options": [
                {"key": "A", "text": "因为 fp16 计算速度比 fp32 慢"},
                {"key": "B", "text": "fp16 的精度不足以表示小更新量，直接更新会被舍入掉"},
                {"key": "C", "text": "因为 fp16 无法存储大于 1 的数"},
                {"key": "D", "text": "为了配合梯度裁剪的阈值计算"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "AdamW 与 Adam + L2 的差别",
            "content_md": "把 weight decay 作为 $\\lambda\\theta$ 加进梯度再交给 Adam（即 Adam + L2），与 AdamW 的解耦衰减相比，主要问题是什么？",
            "answer": {
                "correct": ["C"],
                "explain": "Adam 用 $\\sqrt{\\hat v}$ 做逐参数缩放，$\\lambda\\theta$ 进入 $v$ 后，等效衰减强度被 $\\sqrt{\\hat v}$ 除掉——**梯度大的参数衰减被削弱、梯度小的被加强**，这不是想要的均匀正则。AdamW 把 $\\eta\\lambda\\theta$ 直接作用在参数上，与梯度尺度无关。\n\nA 错：两者都合法；B 错：不是数值溢出；D 错：AdamW 也更新一阶矩，只是衰减不入梯度。"
            },
            "explanation": "解耦衰减 = 把「正则」与「自适应缩放」分开，是 LLM 训练默认 AdamW 的原因。",
            "tags": ["AdamW", "weight decay", "L2"],
            "source": "self",
            "source_ref": "Loshchilov & Hutter, 2019 · Decoupled Weight Decay Regularization",
            "options": [
                {"key": "A", "text": "没有区别，两者在数学上完全等价"},
                {"key": "B", "text": "$\\lambda\\theta$ 会让梯度上溢成 inf"},
                {"key": "C", "text": "衰减项被 $\\sqrt{\\hat v}$ 归一化，导致不同参数的衰减强度不一致"},
                {"key": "D", "text": "Adam + L2 无法更新一阶矩估计"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 3,
            "title": "ZeRO 三个阶段各分片什么",
            "content_md": "ZeRO-1 / ZeRO-2 / ZeRO-3 依次增加了哪部分的分片？",
            "answer": {
                "correct": ["B"],
                "explain": "ZeRO-1 分片**优化器状态**（fp32 master + m + v，共 12 B/参数）；ZeRO-2 再加上**梯度**；ZeRO-3（FSDP 是其工程实现）再加上**参数**。\n\nA 错：数据从来没被分片（那是 DP 的语义）；C 错：激活分片是 activation partitioning，不在 ZeRO 三阶段定义内；D 错：顺序不能反，分片参数必然要求同时分片梯度与优化器状态。"
            },
            "explanation": "ZeRO 的分片是「由内到外」：优化器状态 → 梯度 → 参数。",
            "tags": ["ZeRO", "FSDP", "并行"],
            "source": "self",
            "source_ref": "Rajbhandari et al., 2020 · ZeRO: Memory Optimizations Toward Training Trillion Parameter Models",
            "options": [
                {"key": "A", "text": "依次分片：数据 → 模型 → 激活"},
                {"key": "B", "text": "依次分片：优化器状态 → 梯度 → 参数"},
                {"key": "C", "text": "依次分片：激活 → 梯度 → 优化器状态"},
                {"key": "D", "text": "三个阶段分片对象相同，只是通信量不同"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "Pre-LN 为什么能省掉长 warmup",
            "content_md": "GPT-2 之后普遍改用 Pre-LN（$x_{l+1}=x_l+F(\\mathrm{LN}(x_l))$）而非原始 Post-LN。最主要的原因是：",
            "answer": {
                "correct": ["B"],
                "explain": "Pre-LN 把归一化放进分支内，残差是**纯恒等路径** $x_l$，梯度可沿 $\\partial x_L/\\partial x_l=\\prod(I+\\partial F)$ 中的全 $I$ 项直通到底层，浅层不会因反复被 LN 缩放而梯度量级失控，因此不需要长 warmup 也能训深。\n\nA 错：预算是常数级变化；C 错：相反，Post-LN 才是「深层好、浅层难」；D 错：位置编码与 LN 位置无关。"
            },
            "explanation": "梯度能否直通底层，决定了深网要不要靠 warmup 兜住早期不稳定。",
            "tags": ["Pre-LN", "Post-LN", "梯度路径"],
            "source": "self",
            "source_ref": "Xiong et al., 2020 · On Layer Normalization in the Transformer Architecture",
            "options": [
                {"key": "A", "text": "Pre-LN 的计算量比 Post-LN 少一半"},
                {"key": "B", "text": "残差是恒等路径，梯度可直通底层，不依赖 warmup 抑制早期不稳定"},
                {"key": "C", "text": "Pre-LN 让深层梯度更大，因此需要更小的学习率"},
                {"key": "D", "text": "Pre-LN 改变了位置编码的注入方式"},
            ],
        },
        {
            "type": "output",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "算 13B 模型的训练显存",
            "content_md": "用 Adam + 混合精度全参训练 13B 模型，仅模型状态需要多少显存（按 16 B/参数，结果用 GB，$1\\text{GB}=1024^3$ 字节）？单张 80GB 卡能装下吗？",
            "answer": {
                "explain": "$16\\times13\\times10^9=2.08\\times10^{11}$ 字节 $=208\\times10^9/1024^3\\approx193.7$ GB。\n\n单张 80GB 装不下（差 2.4 倍），必须分片：ZeRO-2 在 8 卡下每卡 $2+2/8+12/8=3.75$ B/参数 → $3.75\\times13\\text{B}\\approx45.4$ GB，加激活才可运行。\n\n注意这还没算激活（数十 GB），实际至少要 ZeRO-2/3 或 16 卡以上。"
            },
            "explanation": "16 B/参数是训练显存口算的基准，13B→193.7GB 是必背量级。",
            "tags": ["显存", "13B", "训练"],
            "source": "self",
            "source_ref": "ZeRO 论文的 16 B/参数口径",
        },
        {
            "type": "output",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "算 ZeRO-2 每卡显存",
            "content_md": "7B 模型用 ZeRO-2、8 卡训练，每卡仅模型状态占多少 GB？相对 DDP 的基线节省了几倍？（$1\\text{GB}=1024^3$）",
            "answer": {
                "explain": "ZeRO-2：参数 2 + 梯度 $2/8$ + 优化器状态 $12/8$ = $2+0.25+1.5=3.75$ B/参数。\n\n每卡：$3.75\\times7\\times10^9/1024^3\\approx24.4$ GB。基线 16 B/参数 → $16\\times7\\text{B}\\approx104.3$ GB，节省 $16/3.75\\approx4.27$ 倍。\n\n结论：ZeRO-2 让 7B 从「需要 2 张 80G」变成「单张 40G 可跑」，且几乎无额外通信。"
            },
            "explanation": "ZeRO-2 是性价比最高的阶段：分片梯度与优化器状态，参数仍全量复制。",
            "tags": ["ZeRO-2", "显存", "7B"],
            "source": "self",
            "source_ref": "ZeRO 论文的 stage 划分",
        },
        {
            "type": "output",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "算 warmup + cosine 的某一时刻学习率",
            "content_md": "峰值 lr $=3\\times10^{-4}$，warmup 2000 步，总 20000 步，cosine 衰减到峰值的 10%。求第 11000 步（0-based）的学习率。",
            "answer": {
                "explain": "$\\eta_{\\min}=3\\times10^{-5}$，进度 $p=(11000-2000)/(20000-2000)=9000/18000=0.5$。\n\n$\\eta=\\eta_{\\min}+\\frac{1}{2}(\\eta_{\\max}-\\eta_{\\min})(1+\\cos(\\pi\\cdot0.5))$\n$=3\\times10^{-5}+\\frac{1}{2}(2.7\\times10^{-4})(1+0)=3\\times10^{-5}+1.35\\times10^{-4}=1.65\\times10^{-4}$。\n\n巧记：cosine 段正中间（$p=0.5$）的学习率恰为 $\\eta_{\\min}$ 与 $\\eta_{\\max}$ 的算术平均。"
            },
            "explanation": "cosine 段的中点值 = (max+min)/2，是最常被考的一个点。",
            "tags": ["学习率", "cosine", "warmup"],
            "source": "self",
            "source_ref": "cosine decay 标准公式",
        },
        {
            "type": "fix_error",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "梯度累积后训练发散的修复",
            "content_md": "下面这段梯度累积实现，把 micro-batch 从 1 增加到 4 之后训练立刻发散（loss 飙升）。指出问题并给出修正：\n\n```python\nfor i, batch in enumerate(loader):\n    loss = model(batch)\n    loss.backward()                    # 没有除累积步数\n    if (i + 1) % 4 == 0:\n        optimizer.step()\n        optimizer.zero_grad()\n```",
            "answer": {
                "reference_code": "import torch\n\naccum = 4\nfor i, batch in enumerate(loader):\n    loss = model(batch)\n    (loss / accum).backward()           # 关键：除以累积步数\n    if (i + 1) % accum == 0:\n        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)\n        optimizer.step()\n        optimizer.zero_grad()\n\n# 若用 AMP，scaler 要同步：\n# scaler.scale(loss / accum).backward()\n# scaler.unscale_(optimizer); clip_grad_norm_(...); scaler.step(optimizer); scaler.update()",
                "explain": "`loss.backward()` 在 4 个 micro-batch 上把梯度**累加**了 4 份，等效学习率变成 4 倍 → 发散。\n\n修正三条：① `loss = loss / accum` 再 backward（或 backward 后手动 `p.grad /= accum`）；② `optimizer.step()` 与 `zero_grad()` 严格每 accum 次一次；③ 用 AMP 时 scaler 的 step/update 也要同频，否则 loss scale 的统计会错。"
            },
            "explanation": "「除以累积步数」是梯度累积唯一容易漏的一行，漏了就等于偷偷把 lr 乘 K。",
            "tags": ["梯度累积", "学习率", "AMP"],
            "source": "self",
            "source_ref": "梯度累积的等价性条件",
        },
    ],
}


INTERVIEW = {
    "meta": {"chapter": "ai-ch10", "title": "训练工程与规模化 —— 面试题", "count": 6},
    "items": [
        {
            "question": "7B 模型为什么单张 80G 卡训不动？如果必须在这张卡上做，你会怎么改？",
            "answer_md": "先算账再回答，这是这类题的正确打开方式。\n\n**账**：Adam + 混合精度训练需要 16 B/参数 —— fp16 参数 2 + fp16 梯度 2 + fp32 主权重 4 + Adam 的 $m$ 4 + $v$ 4。7B 就是 $16\\times7\\approx112$ GB，**已经超过 80GB**，还没算激活（数十 GB）。所以不是「优化一下就能跑」，而是账本身不成立。\n\n**方案的优先级**（从便宜到贵）：\n1. **LoRA/QLoRA**：只训适配器，模型权重冻结（可 4-bit 量化），模型状态降到 ~2-4 B/参数，24G 卡都能跑。这是「必须在这张卡上做」的正确答案。\n2. **激活重计算**：把激活从 $O(L)$ 降到 $O(\\sqrt{L})$，省 30%-50% 显存，代价 ~30% 算力。\n3. **ZeRO-2/3 或 FSDP**：跨卡分片；但这就不是「一张卡」了。\n4. **降序列长度/微 batch + 梯度累积**：省激活，但改不了 112GB 的模型状态。\n\n关键判断：**模型状态是刚性的，只有「不训全参」或「分片到多卡」两条路**；重计算、降 batch 只能救激活。",
            "follow_ups": [
                "LoRA 的显存账具体是多少？",
                "ZeRO-3 在 8 卡上能不能把这 112GB 压到 80GB 以下？",
                "为什么 112GB 比「7B × 4 字节」大这么多？",
            ],
            "difficulty": 4,
            "company_tags": ["字节跳动", "阿里", "蚂蚁", "百度"],
        },
        {
            "question": "Adam 和 AdamW 有什么区别？为什么现在大模型都用 AdamW？",
            "answer_md": "**公式上的差别只有一处**：Adam + L2 把 $\\lambda\\theta$ 加进梯度再走 Adam；AdamW 把它从梯度里拿出来，直接作用在参数上：\n\n$$\\theta\\leftarrow\\theta-\\eta\\Big(\\frac{\\hat m}{\\sqrt{\\hat v}+\\epsilon}+\\lambda\\theta\\Big)$$\n\n**为什么这个位置很重要**：Adam 的分母 $\\sqrt{\\hat v}$ 是逐参数的，把 $\\lambda\\theta$ 丢进梯度后，衰减项也被这个分母归一化了 —— 梯度大的参数衰减被削弱、梯度小的参数被过度衰减，正则强度与参数本身的重要性耦合在一起，这违背了「均匀收缩」的初衷。AdamW 的衰减是 $\\eta\\lambda\\theta$，与梯度尺度无关，等价于每步乘 $(1-\\eta\\lambda)$。\n\n**为什么大模型更敏感**：Transformer 里不同参数的梯度尺度差异极大（embedding、LayerNorm、注意力、FFN 差几个数量级），耦合衰减的偏差被放大；再加上大模型通常训很久，微小偏差会累积成泛化差距。所以 AdamW 在 LLM 上稳定优于 Adam+L2，而小模型上差异不明显。\n\n**配套细节**：bias 与 LayerNorm 的 $\\gamma$ 排除 weight decay；$\\beta_2$ 常从 0.999 降到 0.95 以适应梯度尺度变化。",
            "follow_ups": [
                "为什么 β2 在 LLM 里常用 0.95 而不是 0.999？",
                "解耦衰减在数学上等价于什么（proximal 视角）？",
                "SGD 为什么在某些视觉任务上泛化更好？",
            ],
            "difficulty": 4,
            "company_tags": ["OpenAI", "字节跳动", "商汤", "腾讯"],
        },
        {
            "question": "混合精度训练里，loss scaling 和 fp32 主权重分别解决什么问题？",
            "answer_md": "两个问题完全不同，一个是**范围**，一个是**精度**。\n\n**loss scaling 解决下溢**：fp16 的最小正规数约 $6\\times10^{-5}$，而很多梯度小于这个值，直接变成 0（表现为「loss 不降但也不报错」）。做法是把 loss 乘 $S$（如 $2^{14}$），梯度整体放大到可表示区间，更新前再除回去。动态 scaling 会在连续无溢出时增大 $S$、溢出时跳过该步并减半。\n\n**fp32 主权重解决舍入**：fp16 的 ulp 随数值变化，参数在 1 附近时 ulp 约 $10^{-3}$，而典型更新量是 $10^{-5}$ 量级，$\theta+\\Delta\theta=\theta$（更新被吃掉）。所以必须保留一份 fp32 参数做累加，计算时再 cast 成低精度。\n\n**补充两点**：① 上溢（>65504）需要靠梯度裁剪/更好的初始化，loss scaling 只防下溢；② bf16 指数位与 fp32 相同，范围够大，**不需要 loss scaling**，但精度更差（7 位尾数），所以累加仍要 fp32。这就是 LLM 训练用 bf16、视觉用 fp16+AMP 的分野。",
            "follow_ups": [
                "bf16 为什么不用 loss scaling？",
                "fp16 在什么情况下会 inf，怎么排查？",
                "fp8 训练需要什么额外机制？",
            ],
            "difficulty": 4,
            "company_tags": ["NVIDIA", "字节跳动", "华为", "阿里"],
        },
        {
            "question": "DDP、ZeRO、TP、PP 分别在切什么？给定 32 张卡训 70B，你怎么组合？",
            "answer_md": "**先分清切什么**：\n- DDP：切数据，每卡一份完整模型，每步 AllReduce 梯度。\n- ZeRO/FSDP：切**模型状态**（优化器状态→梯度→参数），按需 gather。\n- TP：切**单层矩阵**（列并行 + 行并行配对），每层两次 AllReduce，对延迟极敏感。\n- PP：切**层**（stage），点对点传激活，有 bubble。\n\n**70B 的账**：16 B/参数 → 1120GB 模型状态。32 卡若每卡 80GB，总共 2560GB，模型状态占 44%，剩下的留给激活与碎片 —— 可行但不宽裕。\n\n**方案**：\n- 单机 8 卡内做 **TP=8**（NVLink 域内，两次 AllReduce 才付得起）；\n- 4 个节点做 **PP=4**（每节点 4 个 stage 的层，跨机只传激活）；\n- 再叠加 **ZeRO-1**（分片优化器状态，几乎无额外通信）；\n- 若显存仍紧，用 **ZeRO-3/FSDP 替代 DP 维度的复制**。\n- micro-batch 数取 $\\ge4P$ 压 bubble（$P=4$ 时 ≥16）。\n\n**一句话原则**：**TP 不出机、PP 跨机、ZeRO 兜底、DP 扩吞吐**。", 
            "follow_ups": [
                "为什么 TP 不能跨机？",
                "PP 的 bubble 比例怎么算？",
                "MoE 的 EP 有什么额外问题？",
            ],
            "difficulty": 5,
            "company_tags": ["字节跳动", "阿里", "华为", "商汤"],
        },
        {
            "question": "训练中 loss 突然出现尖峰（spike），你怎么定位和恢复？",
            "answer_md": "**先分类再动手**，spike 有四类成因：\n\n1. **异常数据**：单 batch 的 loss 突然 ×10，之后立刻恢复 → 查该 batch 的样本（超长、乱码、重复），清洗或跳过。\n2. **优化器状态污染**：spike 后 loss 持续高位不恢复 → $v$ 被大梯度污染，必须回滚到 spike 前的 checkpoint。\n3. **数值溢出**：出现 inf/nan → 查 fp16 溢出点（注意力 logits、exp 未减最大值、LayerNorm eps）、检查 loss scale 是否在频繁回退。\n4. **结构性不稳定**：周期性 spike，与数据无关 → 降 lr、加长 warmup、加 QK-norm/z-loss、降 batch。\n\n**恢复流程**（工程标准做法）：保存最近 N 个 checkpoint + dataloader 状态；spike 后回滚到前一个稳定点，**跳过引发 spike 的若干 batch** 继续训；同时记录 lr、grad norm、优化器状态范数、数据 id 做归因。\n\n**预防**：全局范数裁剪（$c=1.0$）、bf16 替代 fp16、embedding/LayerNorm 用 fp32、监控 grad norm 与 update/param ratio。\n\n注意：裁剪只是「把发散变成缓慢漂移」，不能修复结构性不稳定 —— 如果长期有 10% 的步被裁剪，说明 lr 太大。",
            "follow_ups": [
                "什么情况下应该直接重启而不是回滚？",
                "grad norm 与 update/param ratio 的健康值是多少？",
                "为什么 fp16 比 bf16 更容易出现 spike？",
            ],
            "difficulty": 5,
            "company_tags": ["字节跳动", "蚂蚁", "百度", "快手"],
        },
        {
            "question": "Chinchilla 说 20 tokens/参数最优，为什么现在大家都在「过训练」？",
            "answer_md": "因为两者的**目标函数不同**。\n\nChinchilla 在固定**训练**算力 $C=6ND$ 下最小化 loss，得到 $N\\propto D\\propto C^{0.5}$、$D/N\\approx20$ —— 这是「训练最省」的解。\n\n但产品要最小化**总成本 = 训练 + 推理 × 生命周期调用量**。推理成本正比于参数量 $N$，而调用量可能远超训练 token 数。于是把 $N$ 调小、$D$ 调大（过训练）能让推理便宜得多，训练多花的钱在生命周期内被摊平。7B 训 2T tokens（约 14 倍于 Chinchilla 比例）就是这个逻辑。\n\n**代价与边界**：过训练会让「达到同等 loss」的训练算力更高，且超过约 4 个 epoch 的重复数据边际收益迅速衰减 —— 所以「堆数据」必须配去重与质量过滤。\n\n**反过来也要会答**：如果数据受限（垂直领域只有 50B tokens），强行按 20:1 配比会让模型欠训练，此时应该缩小模型规模、或引入通用数据做预训练再接领域微调。",
            "follow_ups": [
                "过训练到什么程度开始不划算？",
                "数据受限时最优策略是什么？",
                "Scaling Law 在能力层面为什么失效（涌现/逆缩放）？",
            ],
            "difficulty": 4,
            "company_tags": ["OpenAI", "DeepMind", "字节跳动", "阿里"],
        },
    ],
}


PROJECT = {
    "meta": {
        "chapter": "ai-ch10",
        "title": "训练工程与规模化 —— 综合项目",
        "category": "dl",
        "count": 1,
    },
    "items": [
        {
            "title": "写一个「训练可行性评估器 + 迷你训练管线」（NumPy only）",
            "requirement_md": "目标：把本章的「算账」与「诊断」两件事变成可运行工具，而不是停留在公式。\n\n**Part A · 显存/算力评估器**（纯计算，无训练）\n1. 输入：参数量 $N$、卡数 $K$、单卡显存 $M$、精度（fp32/fp16/bf16）、ZeRO stage（0-3）、是否开重计算、batch、seq、hidden、层数。\n2. 输出：每卡模型状态（按 16 B/参数或对应精度口径）、激活估算、是否可行、推荐的最小 stage、以及若不可行时的三条建议（按性价比排序）。\n3. 用 7B/13B/70B × 8/32/64 卡各跑一遍，输出一张可行性表。\n\n**Part B · 迷你训练管线**（真实训练一个 8 层 MLP 回归任务）\n4. 实现 He 初始化 + LayerNorm + AdamW + warmup-cosine + 全局范数裁剪，训练一个 8 层 MLP 拟合 2 维非线性函数。\n5. 做三组消融：① 初始化（naive / Xavier / He）；② 归一化（无 / LN）；③ 优化器（SGD / Adam / AdamW）。每组打印最终验证 loss 与前 200 步的 grad norm 曲线（每 20 步一个点）。\n6. 做一次「故意崩」实验：把 lr 调大 10 倍，记录 loss 第几步开始 NaN、当时 grad norm 多大、裁剪是否救住（对比开/关裁剪）。\n7. 用 Part A 的评估器给 Part B 的模型算一次账，并解释「为什么玩具模型算出来只要几 MB，实际训练仍要 GPU」（提示：算力与并行开销，不是显存）。\n\n**Part C · 报告**\n8. 一张表汇总 9 组消融的最终 loss；一段 300 字以内的归因（哪一项影响最大、为什么）；一段「如果要把这个模型放大 100 倍，我会先改什么」的方案。",
            "tasks": [
                {
                    "title": "显存/算力评估器",
                    "verification": {
                        "type": "output",
                        "desc": "对 7B/8 卡输出「112GB 不可行，建议 ZeRO-2 后 24.4GB 可行」；对 70B/32 卡输出「ZeRO-1 + PP=4 + TP=8 可行」。所有数字与 16 B/参数口径一致（误差 < 1%）。",
                    },
                },
                {
                    "title": "迷你训练管线跑通",
                    "verification": {
                        "type": "output",
                        "desc": "8 层 MLP 在 5000 步内验证 loss 下降 > 90%；打印的 grad norm 每层同量级（首末层比 < 100）。",
                    },
                },
                {
                    "title": "初始化消融",
                    "verification": {
                        "type": "output",
                        "desc": "三组各训一次并打印最终 loss；naive 初始化应明显最差（或直接 NaN），He 应最好；给出「方差保持」与 loss 的关系解释。",
                    },
                },
                {
                    "title": "归一化/优化器消融",
                    "verification": {
                        "type": "output",
                        "desc": "无 LN vs 有 LN、SGD vs Adam vs AdamW 各打印最终 loss 与第 200 步 grad norm；AdamW 的 ||θ|| 应小于 Adam+L2（若实现了 L2 对照）。",
                    },
                },
                {
                    "title": "故意崩实验",
                    "verification": {
                        "type": "output",
                        "desc": "lr×10 时记录首次 NaN 的 step 与当步 grad norm；开裁剪的版本应能撑更久或恢复，打印两者对比。",
                    },
                },
                {
                    "title": "评估器与训练的对照报告",
                    "verification": {
                        "type": "output",
                        "desc": "输出 Part A 的可行性表 + Part B 的 9 组消融表 + 300 字归因；结论需明确「显存可行 ≠ 算力可行」。",
                    },
                },
            ],
            "tags": ["显存账", "AdamW", "初始化", "梯度裁剪", "消融实验"],
        }
    ],
}


def main() -> int:
    check_only = "--check" in sys.argv
    build_examples(check_only)
    if check_only:
        return 0
    (CH / "exercises.json").write_text(json.dumps(EXERCISES, ensure_ascii=False, indent=2), encoding="utf-8")
    (CH / "interview.json").write_text(json.dumps(INTERVIEW, ensure_ascii=False, indent=2), encoding="utf-8")
    (CH / "project.json").write_text(json.dumps(PROJECT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出 exercises({len(EXERCISES['items'])}) / interview({len(INTERVIEW['items'])}) / project(1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
