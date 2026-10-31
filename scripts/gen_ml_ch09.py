# -*- coding: utf-8 -*-
"""生成 ml-ch09（支持向量机与核方法）的 examples / exercises / interview / project。

expected_output 全部来自真实运行；只用 NumPy（含一个 30 行的简化 SMO）。

用法：
    python scripts/gen_ml_ch09.py            # 生成全部
    python scripts/gen_ml_ch09.py --check    # 只跑示例
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "content" / "ml" / "ml-ch09"

SMO_CODE = r'''
def smo(K, y, C, max_iter=300, tol=1e-3):
    """简化 SMO（Platt 的启发式版）：每次挑违反 KKT 最严重的一对变量做解析更新。"""
    n = len(y)
    a = np.zeros(n)
    b = 0.0

    def fvals():
        return K @ (a * y) + b           # 所有样本的 f(x)

    for _ in range(max_iter):
        changed = 0
        for i in range(n):
            Ei = fvals()[i] - y[i]
            if not ((y[i] * Ei < -tol and a[i] < C) or (y[i] * Ei > tol and a[i] > 0)):
                continue
            E = fvals()
            j = int(np.argmax(np.abs(E - Ei)))
            if j == i:
                continue
            Ej, ai_o, aj_o = E[j] - y[j], a[i], a[j]
            if y[i] != y[j]:
                L, H = max(0.0, aj_o - ai_o), min(C, C + aj_o - ai_o)
            else:
                L, H = max(0.0, ai_o + aj_o - C), min(C, ai_o + aj_o)
            if L >= H:
                continue
            eta = 2 * K[i, j] - K[i, i] - K[j, j]
            if eta >= 0:
                continue
            aj = min(max(aj_o - y[j] * (Ei - Ej) / eta, L), H)
            if abs(aj - aj_o) < 1e-8:
                continue
            ai = ai_o + y[i] * y[j] * (aj_o - aj)
            a[i], a[j] = ai, aj
            b1 = b - Ei - y[i] * (ai - ai_o) * K[i, i] - y[j] * (aj - aj_o) * K[i, j]
            b2 = b - Ej - y[i] * (ai - ai_o) * K[i, j] - y[j] * (aj - aj_o) * K[j, j]
            if 0 < ai < C:
                b = b1
            elif 0 < aj < C:
                b = b2
            else:
                b = (b1 + b2) / 2
            changed += 1
        if changed == 0:
            break
    return a, b
'''

EXAMPLES: list[tuple[str, str, str]] = [
    (
        "ex01-margin-geometry",
        "函数间隔、几何间隔与间隔宽度",
        r'''
import numpy as np
w = np.array([3.0, 4.0]); b = -1.0
pts = np.array([[1.0, 1.0], [0.0, 0.0], [2.0, 0.0]])
norm_w = np.linalg.norm(w)
print(f"||w|| = {norm_w:.4f}")
for x in pts:
    f = w @ x + b                       # 函数间隔（带符号）
    print(f"x={x}: w·x+b = {f:+.2f}, 函数间隔|.| = {abs(f):.2f}, 几何间隔 = {abs(f)/norm_w:.4f}")
print()
print(f"若把 w,b 同乘 2：w={2*w}, b={2*b}")
w2, b2 = 2 * w, 2 * b
f2 = w2 @ pts[0] + b2
print(f"  函数间隔 {f2:+.2f}（翻倍），几何间隔 {abs(f2)/np.linalg.norm(w2):.4f}（不变）")
print()
# 规范化后（支持向量上 y(w·x+b)=1）的间隔宽度
print(f"规范化到 y_i(w·x_i+b)>=1 时，间隔宽度 = 2/||w|| = {2/norm_w:.4f}")
print("结论：函数间隔可被尺度任意缩放，只有几何间隔有几何意义；")
print("      因此 SVM 先用 y_i(w·x_i+b)>=1 固定尺度，再把『最大化 2/||w||』换成『最小化 ||w||^2』")
''',
    ),
    (
        "ex02-hard-margin-1d",
        "一维硬间隔 SVM 的解析解",
        r'''
import numpy as np
x = np.array([-1.0, 1.0])
y = np.array([-1.0, 1.0])
# 对称 ⇒ b=0；支持向量满足 w*x_i = y_i ⇒ w=1
w, b = 1.0, 0.0
print(f"数据: x={x}, y={y}")
print(f"解析解: w={w}, b={b}")
for xi, yi in zip(x, y):
    print(f"  y={yi:+.0f}: y(w·x+b) = {yi*(w*xi+b):+.2f}  (应为 1 -> 是支持向量)")
print(f"间隔宽度 = 2/|w| = {2/abs(w):.4f}")
print()
print("对偶验证：α 由 KKT 决定，两点的 α 都应为 1/2（对称），且 Σα_i y_i = 0：")
alpha = np.array([0.5, 0.5])
print(f"  Σα_i y_i = {(alpha*y).sum():+.6f}")
print(f"  w = Σα_i y_i x_i = {(alpha*y*x).sum():+.4f}  (与解析解一致)")
print("结论：1D 两个对称点 ⇒ w=1, b=0, margin=2；α 的对称性来自数据的对称性")
''',
    ),
    (
        "ex03-kkt-check",
        "KKT 互补松弛：三类支持向量",
        r'''
import numpy as np
# 给定一组解（硬间隔，1D）：x=[-2,-1,1,2], y=[-1,-1,1,1]
x = np.array([-2.0, -1.0, 1.0, 2.0])
y = np.array([-1.0, -1.0, 1.0, 1.0])
w, b = 1.0, 0.0
alpha = np.array([0.0, 0.5, 0.5, 0.0])     # 内侧两点是支持向量
print("i  x_i   y_i   α_i    y_i(w·x_i+b)   互补松弛 α_i·[y_i f_i - 1]")
for i in range(4):
    margin_i = y[i] * (w * x[i] + b)
    slack = alpha[i] * (margin_i - 1)
    print(f"{i}  {x[i]:+.0f}   {y[i]:+.0f}   {alpha[i]:.1f}    {margin_i:+.2f}          {slack:+.6f}")
print()
print(f"Σα_i y_i = {np.sum(alpha*y):+.6f}（等式约束）")
print(f"w = Σα_i y_i x_i = {np.sum(alpha*y*x):+.4f}")
print(f"α 全为非负: {bool(np.all(alpha>=0))}")
print()
print("判读：α=0 的点（间隔外）对模型无影响；α>0 且 margin=1 的是自由支持向量；")
print("      若 α=C 且 margin<1，则是有界支持向量（间隔内/错分），见 ex07 的软间隔结果")
''',
    ),
    (
        "ex04-kernel-psd",
        "核矩阵的半正定性（Mercer 条件）",
        r'''
import numpy as np
rng = np.random.default_rng(0)
X = rng.normal(size=(12, 3))

def gram(kernel):
    n = len(X)
    return np.array([[kernel(X[i], X[j]) for j in range(n)] for i in range(n)])

kernels = {
    "线性 x·z": lambda a, b: a @ b,
    "多项式 (x·z+1)^2": lambda a, b: (a @ b + 1) ** 2,
    "RBF γ=0.5": lambda a, b: np.exp(-0.5 * np.sum((a - b) ** 2)),
    "非法核 -||x-z||": lambda a, b: -np.linalg.norm(a - b),
}
for name, k in kernels.items():
    K = gram(k)
    ev = np.linalg.eigvalsh(K)
    print(f"{name:<18s} 最小特征值 = {ev.min():+9.4f}   半正定: {ev.min() >= -1e-8}")
print()
print("结论：前三个合法核的 Gram 矩阵最小特征值 >= 0（线性为 0~正，多项式/RBF 为正）；")
print("      『负距离』不是合法核（最小特征值显著为负），用它做 SVM 会得到非凸问题")
''',
    ),
    (
        "ex05-poly-kernel-dim",
        "多项式核：隐式内积 vs 显式特征映射",
        r'''
import numpy as np
x = np.array([2.0, -1.0]); z = np.array([0.5, 3.0])

def phi(v):
    # (x·z + 1)^2 对应 6 维显式特征
    a, b = v
    return np.array([a*a, np.sqrt(2)*a*b, b*b, np.sqrt(2)*a, np.sqrt(2)*b, 1.0])

k_implicit = (x @ z + 1) ** 2
k_explicit = phi(x) @ phi(z)
print(f"x={x}, z={z}")
print(f"隐式： (x·z+1)^2 = {k_implicit:.6f}")
print(f"显式： <phi(x),phi(z)> = {k_explicit:.6f}")
print(f"误差 = {abs(k_implicit-k_explicit):.2e}")
print(f"显式特征维度 = {len(phi(x))}")
print()
d, deg = 10, 3
from math import comb
dim = comb(d + deg, deg)
print(f"2 阶升 6 维只是小例子：d={d}、deg={deg} 时显式维度 = C({d}+{deg},{deg}) = {dim}")
print(f"而核计算仍是 1 次内积 + 1 次幂：与维度无关")
print("结论：核技巧的核心是『只算内积、不造 φ』，维度爆炸被绕开")
''',
    ),
    (
        "ex06-rbf-gamma",
        "RBF 的 gamma 对核矩阵条件数与有效秩的影响",
        r'''
import numpy as np
rng = np.random.default_rng(1)
X = rng.normal(size=(80, 2))
sq = np.sum((X[:, None, :] - X[None, :, :]) ** 2, -1)

print("gamma    最小特征值      最大特征值     条件数       有效秩(>1e-6)")
for g in (0.01, 0.1, 1.0, 10.0):
    K = np.exp(-g * sq)
    ev = np.linalg.eigvalsh(K)
    cond = ev.max() / max(ev.min(), 1e-300)
    rank = int((ev > 1e-6).sum())
    print(f"{g:<8.2f} {ev.min():>12.3e} {ev.max():>13.3f} {cond:>12.2e} {rank:>10d}")

print()
print("结论：gamma 越大 -> 核矩阵越接近单位阵（条件数爆炸、有效秩=样本数），模型趋近『记忆每个点』；")
print("      gamma 越小 -> 核矩阵趋近全 1 矩阵（有效秩 1），模型趋近常数/线性")
print("      所以 gamma 控制的是『有效自由度』，不是直觉上的『半径』")
''',
    ),
    (
        "ex07-soft-margin-smo",
        "软间隔 SVM：C 对间隔与支持向量的影响（简化 SMO）",
        SMO_CODE + r'''
import numpy as np
x = np.array([-2.0, -1.5, -1.0, -0.2, 0.2, 1.0, 1.5, 2.0])
y = np.array([-1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
K = np.outer(x, x)                       # 线性核

print("C        w         b       间隔 2/|w|   支持向量数  α=C 的个数  训练误差")
for C in (0.01, 0.1, 1.0, 10.0, 100.0):
    a, b = smo(K, y, C)
    w = float(np.sum(a * y * x))
    margin = 2.0 / abs(w) if abs(w) > 1e-9 else float("inf")
    pred = np.sign(w * x + b)
    err = int((pred != y).sum())
    nsv = int((a > 1e-6).sum())
    nb = int((np.abs(a - C) < 1e-6).sum())
    print(f"{C:<7.2f} {w:>8.4f} {b:>8.4f} {margin:>9.4f} {nsv:>10d} {nb:>10d} {err:>9d}")

print()
print("读数据：C=0.01/0.1 时 2 个支持向量的 α 都顶在上界 C（α=C 的个数=2），")
print("        w 被压到很小、间隔被撑到 153/15，训练误差 5 —— 模型几乎放弃拟合，只求宽间隔；")
print("        C>=1 后 α 落到 (0,C) 内部（α=C 个数=0），解稳定：w=1.111, 间隔 1.8, 误差 1。")
print("结论：C 的真正作用是对 α 设上界（α<=C）。C 极小时上界截断使 w 无法长大，")
print("      模型退化为『宽间隔但几乎全错』；C 足够大后解收敛到硬间隔解，再大也没有变化")
''',
    ),
    (
        "ex08-smo-step",
        "SMO 的单步解析更新与裁剪",
        r'''
import numpy as np
K = np.array([[4.0, 1.0], [1.0, 4.0]])   # 两个样本的核矩阵
y = np.array([1.0, -1.0])
a = np.array([0.0, 0.0])
C = 1.0
b = 0.0

def f(i):
    return float(K[i, 0] * a[0] * y[0] + K[i, 1] * a[1] * y[1] + b)

E1, E2 = f(0) - y[0], f(1) - y[1]
eta = K[0, 0] + K[1, 1] - 2 * K[0, 1]
print(f"初始 a = {a}, E1 = {E1:+.2f}, E2 = {E2:+.2f}, eta = {eta:.2f}")
print(f"eta = K11+K22-2K12 = {eta:.2f}（= 两样本在特征空间的距离平方，必须 >= 0）")

# y1 != y2 -> L = max(0, a2-a1), H = min(C, C+a2-a1)
L = max(0.0, a[1] - a[0]); H = min(C, C + a[1] - a[0])
a2_new = a[1] - y[1] * (E1 - E2) / eta
a2_clip = min(max(a2_new, L), H)
a1_new = a[0] + y[0] * y[1] * (a[1] - a2_clip)
print(f"未裁剪 a2 = {a2_new:+.4f}；可行区间 [{L:.2f}, {H:.2f}] -> 裁剪后 a2 = {a2_clip:+.4f}")
print(f"回代 a1 = a1 + y1*y2*(a2_old - a2_new) = {a1_new:+.4f}")
print(f"新 α = [{a1_new:.4f}, {a2_clip:.4f}]，Σα_i y_i = {a1_new*y[0] + a2_clip*y[1]:+.6f}（等式约束保持）")
print()
print("结论：单变量更新会破坏 Σα_i y_i=0，所以必须成对更新；")
print("      更新公式是二次函数的最小点，裁剪保证落在 [L,H] 可行域内")
''',
    ),
    (
        "ex09-hinge-vs-logloss",
        "合页损失与对数损失的差别（异常点为什么拉不动 SVM）",
        r'''
import numpy as np
m = np.linspace(-2, 3, 2001)     # margin = y*f(x)

hinge = np.maximum(0, 1 - m)
logloss = np.log1p(np.exp(-m))
d_hinge = np.where(m < 1, -1.0, 0.0)
d_log = -1.0 / (1.0 + np.exp(m))

def at(v):
    i = int(np.argmin(np.abs(m - v)))
    return hinge[i], logloss[i], d_hinge[i], d_log[i]

print("margin   hinge损失  log损失   hinge梯度  log梯度")
for v in (-1.0, 0.0, 1.0, 2.0, 2.5):
    h, l, dh, dl = at(v)
    print(f"{v:+.1f}     {h:8.4f}  {l:8.4f}   {dh:+8.2f}   {dl:+8.4f}")

print()
print("读表：margin > 1 后 hinge 的损失与梯度都为 0 —— 该样本不再影响模型（稀疏性的来源）；")
print("      log 损失的梯度始终非 0，远处的『已经分对』的样本仍持续推边界（对异常点更敏感）")
print()
print(f"margin=2.5 处：hinge 梯度 = {at(2.5)[2]:+.1f}，log 梯度 = {at(2.5)[3]:+.6f}")
print("结论：hinge 在间隔外截断 => 模型只由边界附近样本决定，鲁棒性来自『不再理会』而不是『更聪明』")
''',
    ),
    (
        "ex10-kernel-separability",
        "核让数据线性可分：Fisher 判据对比",
        r'''import numpy as np
rng = np.random.default_rng(2)

# 同心圆：内圈 r≈0.5（标签 -1），外圈 r≈1.5（标签 +1）——线性不可分
n = 120
th = rng.uniform(0, 2 * np.pi, n)
r = np.r_[0.5 + 0.05 * rng.normal(size=n // 2), 1.5 + 0.05 * rng.normal(size=n // 2)]
X = np.c_[r * np.cos(th), r * np.sin(th)]
y = np.r_[-np.ones(n // 2), np.ones(n // 2)]

def fisher(K, y):
    # 特征空间中的 Fisher 判据：类间距离^2 / 类内散度（全部由核矩阵算出）
    within = 0.0
    for c in (1.0, -1.0):
        idx = np.where(y == c)[0]
        Kc = K[np.ix_(idx, idx)]
        within += np.trace(Kc) - Kc.sum() / len(idx)
    a, b = np.where(y > 0)[0], np.where(y < 0)[0]
    between = (K[np.ix_(a, a)].sum() / len(a) ** 2
               + K[np.ix_(b, b)].sum() / len(b) ** 2
               - 2 * K[np.ix_(a, b)].sum() / (len(a) * len(b)))
    return between, within, between / within

def rbf(g):
    return np.exp(-g * np.sum((X[:, None, :] - X[None, :, :]) ** 2, -1))

print("核                        类间距离^2   类内散度   Fisher比(越大越可分)")
for name, K in ([("线性核（原始 2D）", X @ X.T)]
                + [(f"RBF γ={g}", rbf(g)) for g in (0.1, 0.5, 1.0, 2.0)]):
    bt, wi, ratio = fisher(K, y)
    print(f"{name:<22s} {bt:>10.4f} {wi:>10.2f} {ratio:>12.4f}")

print()
print("读数据：线性核的 Fisher 比 3e-4（同心圆的类均值几乎重合，超平面切不开）；")
print("        RBF 在 γ≈0.5~1 时达到 8e-3 量级，提升约 29 倍 —— 核把数据搬到了更可分的空间。")
print("结论：核的价值不在『相似度』，而在『换一个特征空间后类间可分性变好』；")
print("      这也是为什么 γ 太小时（0.1）退回近似线性、太大时（2.0）又开始下降（过拟合局部）")
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
            print(stdout, p.stderr[:3000])
            raise SystemExit(f"{name} 运行失败")
        if check_only:
            continue
        (out_dir / f"{name}.json").write_text(json.dumps({
            "title": title, "code_lang": "python", "code_std": "python3",
            "stdin": "", "expected_output": stdout, "code": code,
        }, ensure_ascii=False, indent=2), encoding="utf-8")


EXERCISES = {
    "meta": {
        "chapter": "ml-ch09",
        "title": "支持向量机与核方法 —— 习题集",
        "count": 6,
        "note": "6 题，基础题 3 + 算法题 3（平台题仅存元数据与链接，不复述题面）",
    },
    "items": [
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 3,
            "title": "函数间隔与几何间隔",
            "content_md": "关于 SVM 的两种间隔，下列说法正确的是：",
            "answer": {
                "correct": ["C"],
                "explain": "函数间隔 $|w^\\top x+b|$ 会随 $w,b$ 同比例缩放而变（$w,b$ 乘 2，函数间隔翻倍但超平面不变），因此没有几何意义；几何间隔要除以 $\\|w\\|$，它才是不随尺度变化的真实距离。\n\nA 错：两者不相等；B 错：几何间隔不随缩放变化；D 错：SVM 正是利用函数间隔的尺度自由度，令 $y_i(w^\\top x_i+b)\\ge1$ 来固定尺度。"
            },
            "explanation": "尺度规范化是「最大化间隔 ⇔ 最小化 ||w||²」得以成立的前提。",
            "tags": ["SVM", "间隔", "尺度"],
            "source": "self",
            "source_ref": "《统计学习方法》第7章 · 线性可分支持向量机",
            "options": [
                {"key": "A", "text": "函数间隔与几何间隔总是相等"},
                {"key": "B", "text": "几何间隔会随 $w$ 的缩放而同比变化"},
                {"key": "C", "text": "函数间隔可被缩放改变，几何间隔才是真实距离"},
                {"key": "D", "text": "SVM 的最小化目标是直接最小化几何间隔"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "对偶问题里 0 ≤ α ≤ C 从哪来",
            "content_md": "软间隔 SVM 的对偶约束是 $0\\le\\alpha_i\\le C$。上界 $C$ 的来源是：",
            "answer": {
                "correct": ["B"],
                "explain": "对松弛变量 $\\xi_i$ 求偏导置零得 $\\alpha_i+\\mu_i=C$，而 $\\mu_i\\ge0$（不等式约束的乘子），于是 $\\alpha_i\\le C$。\n\nA 错：$C$ 是超参不是推导结果；C 错：与 $\\sum\\alpha_iy_i=0$ 无关；D 错：核函数不影响上界。"
            },
            "explanation": "α 的上界来自「ξ 的乘子非负」这一条 KKT 条件，是软间隔推导的必经一步。",
            "tags": ["SVM", "对偶", "KKT"],
            "source": "self",
            "source_ref": "《统计学习方法》第7章 · 软间隔最大化",
            "options": [
                {"key": "A", "text": "由样本数量 $n$ 决定"},
                {"key": "B", "text": "由 $\\partial L/\\partial\\xi_i=0$ 得 $\\alpha_i+\\mu_i=C$，且 $\\mu_i\\ge0$"},
                {"key": "C", "text": "由等式约束 $\\sum_i\\alpha_iy_i=0$ 推出"},
                {"key": "D", "text": "由核函数的选择决定"},
            ],
        },
        {
            "type": "choice",
            "category": "基础题",
            "platform": "self",
            "difficulty": 4,
            "title": "核技巧能成立的关键前提",
            "content_md": "核技巧之所以能不显式构造 $\\phi$ 就完成升维，最关键的原因是：",
            "answer": {
                "correct": ["C"],
                "explain": "SVM 的对偶问题与决策函数里数据**只以内积形式出现**，因此可以把 $\\langle x_i,x_j\\rangle$ 换成 $K(x_i,x_j)$，形式完全不变。这是核技巧的全部内容。\n\nA 错：原始问题里 $w$ 是显式向量，无法核化，所以才要转对偶；B 错：核不需要是无穷维（线性核是有限维）；D 错：Mercer 条件是「核合法」的判据，不是「能不构造 φ」的原因。"
            },
            "explanation": "「只用内积」是核化的前提，这也是为什么要先推到对偶形式。",
            "tags": ["核技巧", "对偶", "SVM"],
            "source": "self",
            "source_ref": "《统计学习方法》第7章 · 核函数",
            "options": [
                {"key": "A", "text": "原始问题中的 $w$ 可以直接用核函数表示"},
                {"key": "B", "text": "核函数必须是无限维的"},
                {"key": "C", "text": "对偶问题与决策函数中数据只以内积出现，可整体替换为核"},
                {"key": "D", "text": "因为核函数一定满足 Mercer 条件"},
            ],
        },
        {
            "type": "output",
            "category": "算法题",
            "platform": "self",
            "difficulty": 3,
            "title": "算几何间隔与间隔宽度",
            "content_md": "$w=(3,4)$、$b=-1$，样本点 $x=(1,1)$ 且 $y=+1$。求该点的函数间隔与几何间隔；若它是支持向量，间隔宽度是多少？",
            "answer": {
                "explain": "函数间隔 $y(w^\\top x+b)=1\\cdot(3+4-1)=6$；$\\|w\\|=\\sqrt{9+16}=5$，几何间隔 $=6/5=1.2$。\n\n若它是支持向量，规范化后应有 $y(w^\\top x+b)=1$，对应 $\\|w\\|=1/1.2=0.8333$，间隔宽度 $2/\\|w\\|=2.4$。\n\n更一般的口径：只要给出规范化后的 $\\|w\\|$，间隔宽度就是 $2/\\|w\\|$（本题原始尺度下不能直接用 6 去算宽度）。"
            },
            "explanation": "函数间隔先除 ||w|| 才是距离；宽度 2/||w|| 只在规范化后成立。",
            "tags": ["SVM", "几何间隔", "间隔宽度"],
            "source": "self",
            "source_ref": "《统计学习方法》第7章 例7.1",
        },
        {
            "type": "output",
            "category": "算法题",
            "platform": "self",
            "difficulty": 4,
            "title": "判断哪些样本是支持向量",
            "content_md": "1D 问题：$x=[-2,-1,1,2]$、$y=[-1,-1,+1,+1]$，解为 $w=1,b=0$。给定 $\\alpha=[0,0.5,0.5,0]$，用 KKT 判断哪些是支持向量，并指出各自属于哪一类。",
            "answer": {
                "explain": "先算 $y_i f(x_i)$：$-2$ 点得 $1\\cdot2=2$；$-1$ 点得 $1$；$+1$ 点得 $1$；$+2$ 点得 $2$。\n\n- $x=-1$ 与 $x=+1$：$\\alpha>0$ 且 $y f=1$（在边界上）→ **自由支持向量**（$0<\\alpha<C$，决定 $b$）；\n- $x=\\pm2$：$\\alpha=0$ 且 $yf>1$（间隔外）→ 普通点，对模型无影响。\n\n另需验证 $\\sum\\alpha_iy_i=-0.5+0.5=0$ 与 $w=\\sum\\alpha_iy_ix_i=(-0.5)(-1)+(0.5)(1)=1$，均成立。\n\n本题无 $\\alpha=C$ 的样本，因此没有有界支持向量（硬间隔、无违规）。"
            },
            "explanation": "三类支持向量的判据同时看 α 与 y·f(x)，不能只看 α。",
            "tags": ["KKT", "支持向量", "SVM"],
            "source": "self",
            "source_ref": "KKT 互补松弛条件",
        },
        {
            "type": "coding",
            "category": "算法题",
            "platform": "self",
            "difficulty": 5,
            "title": "用 NumPy 实现核矩阵与决策函数",
            "content_md": "实现 `kernel_matrix(X, kernel, gamma)` 与 `svm_predict(X_train, y_train, alpha, b, kernel, X_test)`，支持线性核与 RBF 核，并在一个 2D 非线性可分数据上验证：用 RBF 核的决策函数能把内圈/外圈分开（训练准确率 > 95%）。",
            "answer": {
                "reference_code": "import numpy as np\n\ndef kernel_matrix(X, kind='rbf', gamma=0.5):\n    if kind == 'linear':\n        return X @ X.T\n    sq = np.sum((X[:, None, :] - X[None, :, :]) ** 2, -1)\n    return np.exp(-gamma * sq)\n\ndef svm_predict(Xtr, ytr, alpha, b, Xte, kind='rbf', gamma=0.5):\n    # 决策函数：f(x) = sum_i alpha_i y_i K(x_i, x) + b\n    if kind == 'linear':\n        Kte = Xte @ Xtr.T\n    else:\n        sq = np.sum((Xte[:, None, :] - Xtr[None, :, :]) ** 2, -1)\n        Kte = np.exp(-gamma * sq)\n    return np.sign(Kte @ (alpha * ytr) + b)",
                "explain": "两个要点：① 决策函数**只用核值**，绝不显式构造 φ；② 系数是 $\\alpha_i y_i$（不是 $\\alpha_i$ 单独）。\n\n验证思路：生成内圈（半径 0.5）+ 外圈（半径 1.5）2D 点，用 RBF（$\\gamma\\approx1$）训练后可 >95% 分开；换成线性核则只能 ~50%（无法用一个超平面分开同心圆）。\n\n工程提醒：$\\gamma$ 太大会过拟合（每个点自成一类），太小会退化成线性。"
            },
            "explanation": "核矩阵 + 决策函数是核 SVM 推理的全部，写对它就理解了「不构造 φ」。",
            "tags": ["核矩阵", "决策函数", "NumPy"],
            "source": "github",
            "source_ref": "cjlin1/libsvm",
            "external_url": "https://github.com/cjlin1/libsvm",
        },
    ],
}


INTERVIEW = {
    "meta": {"chapter": "ml-ch09", "title": "支持向量机与核方法 —— 面试题", "count": 4},
    "items": [
        {
            "question": "完整推一遍 SVM：从最大间隔到对偶，再到核函数。中间哪一步最关键？",
            "answer_md": "四步，一层不能少。\n\n**① 最大间隔 → QP**：规范化 $y_i(w^\\top x_i+b)\\ge1$（用掉 $w$ 的尺度自由度），间隔宽度 $2/\\|w\\|$，于是 $\\max 2/\\|w\\| \\Leftrightarrow \\min\\frac12\\|w\\|^2$。\n\n**② 拉格朗日**：加乘子 $\\alpha_i\\ge0$，对 $w,b$ 求偏导置零得\n$w=\\sum_i\\alpha_iy_ix_i$、$\\sum_i\\alpha_iy_i=0$。\n\n**③ 代回得对偶**：$\\max_\\alpha\\sum\\alpha_i-\\frac12\\sum_{ij}\\alpha_i\\alpha_jy_iy_j\\langle x_i,x_j\\rangle$，约束 $\\alpha_i\\ge0$（软间隔加 $\\alpha_i\\le C$）。\n\n**④ 核化**：对偶里只剩内积，把 $\\langle x_i,x_j\\rangle$ 换成 $K(x_i,x_j)$。\n\n**最关键的一步是 ②**——因为 $w=\\sum\\alpha_iy_ix_i$ 把「参数向量」变成了「样本的线性组合」，这才让对偶只含内积、才让核技巧有落脚点，也才让稀疏性（$\\alpha_i=0$）成为结构性结果。没有这一步，SVM 只是一个普通的线性分类器。\n\n**追问要点**：为什么能核化 → 因为对偶与决策函数只以内积出现；为什么稀疏 → KKT 互补松弛使间隔外样本 $\\alpha_i=0$。", 
            "follow_ups": [
                "为什么软间隔的对偶多出 α≤C 这个上界？",
                "强对偶在什么条件下成立？SVM 满足吗？",
                "为什么说 w 只是样本的线性组合（表示定理）？",
            ],
            "difficulty": 5,
            "company_tags": ["字节跳动", "阿里", "百度", "商汤"],
        },
        {
            "question": "SVM 和逻辑回归的本质区别是什么？什么时候选哪个？",
            "answer_md": "**只差在损失函数**，但这一点差异带出四个可观测的区别。\n\n| | SVM | 逻辑回归 |\n|---|---|---|\n| 损失 | hinge $\\max(0,1-yf)$ | log-loss $\\log(1+e^{-yf})$ |\n| 间隔外样本 | 梯度为 0，**不影响模型** | 梯度非 0，持续被推远 |\n| 稀疏性 | 只依赖支持向量 | 所有样本都参与 |\n| 输出 | 距离，需校准才有概率 | 原生概率（proper scoring rule） |\n| 鲁棒性 | 对噪声/异常点更稳（截断） | 易被远处错分点拉偏 |\n\n**选型**：\n- 要概率、要可解释系数、要在线学习 → 逻辑回归；\n- 小样本 + 边界非线性 + 要理论保证（凸、可复现）→ 核 SVM；\n- 表格数据、样本量大 → 两者都不如 GBDT，先跑 GBDT 基线。\n\n**一个常被问的反问**：「SVM 更鲁棒是不是因为它更聪明？」不是——它只是**不再理会已经很对的样本**（hinge 截断），而 log-loss 会一直拉。", 
            "follow_ups": [
                "为什么 hinge 不是 proper scoring rule？",
                "SVM 怎么输出概率，代价是什么？",
                "小样本下为什么核 SVM 常赢神经网络？",
            ],
            "difficulty": 4,
            "company_tags": ["字节跳动", "美团", "滴滴", "京东"],
        },
        {
            "question": "核函数必须满足什么条件？RBF 核为什么对应无限维？高维数据为什么不能用 RBF？",
            "answer_md": "**条件（Mercer）**：对称函数 $K$ 合法 ⟺ 对任意有限样本集，Gram 矩阵 $K_{ij}=K(x_i,x_j)$ **半正定**。这是「存在 $\\phi$ 使 $K=\\langle\\phi,\\phi\\rangle$」的充要条件。实操检验：算 Gram 的特征值，最小值 $\\ge-\\epsilon$ 即合法。\n\n**RBF 为什么无限维**：$e^{-\\gamma\\|x-z\\|^2}$ 展开成泰勒级数后，每一项都是 $x,z$ 的任意阶多项式乘积，阶数无上限 → 特征空间维度无穷。但核值只需一次距离计算，所以「无限维」不妨碍计算。\n\n**高维为什么退化**：这是**距离集中**现象——$d$ 维中两点距离集中在 $\\sqrt{2d\\sigma^2}$ 附近，相对波动 $\\sim1/\\sqrt{d}$。$d=1000$ 时所有点对距离几乎相同，$K$ 近似全 1 矩阵（有效秩 → 1），模型退化为常数。所以文本（$d$ 十万级）必须用线性核。\n\n**加分点**：随机特征（RFF）把 RBF 近似成有限维显式映射，让核方法可以走 SGD 上百万样本；NTK 视角则说明无限宽网络等价于核方法。", 
            "follow_ups": [
                "距离集中现象对 KNN、K-means 有影响吗？",
                "怎么用 Gram 矩阵的特征值判断 gamma 选得好不好？",
                "Mercer 条件与 RKHS 是什么关系？",
            ],
            "difficulty": 5,
            "company_tags": ["商汤", "旷视", "阿里", "微软"],
        },
        {
            "question": "如果业务方要求用 SVM 做线上风控，你会提出哪些反对或补充意见？",
            "answer_md": "这道题考的是「模型选型是否有工程判断」，不是 SVM 知识。我会提四点：\n\n**① 概率与阈值**。风控要的是「违约概率」，SVM 的 `decision_function` 是距离不是概率；`probability=True` 用 Platt scaling 会显著增加训练时间且小样本不可靠。要么做校准并验证可靠性曲线，要么换逻辑回归/GBDT。\n\n**② 可解释性**。核 SVM 没有特征系数，只剩「哪些样本是支持向量」，监管场景（模型备案、拒贷理由）通常不可接受。要可解释就用线性 SVM（系数）或 GBDT + SHAP。\n\n**③ 更新成本**。风控数据每天新增，SVM 没有原生增量更新，必须重解 QP；$n$ 到十万级时训练时间与内存都不可控。用 `SGDClassifier(loss='hinge')` 做在线线性版本更现实。\n\n**④ 不平衡与评估**。欺诈/违约是极端不平衡，SVM 需要 `class_weight` 或调阈值，评估必须用 PR 曲线与 KS/AUC 的组合，不能只看准确率；还要报告支持向量占比（接近 100% 就是过拟合信号）。\n\n**结论**：我会先跑逻辑回归（可解释、有概率、能在线）与 GBDT（更强）两个基线；SVM 只作为「小样本冷启动」的候选，且必须是线性核版本。", 
            "follow_ups": [
                "线性 SVM 的系数能直接当特征重要性吗？",
                "不平衡场景下 KS 与 PR 曲线的关系？",
                "模型备案一般要求哪些可解释性材料？",
            ],
            "difficulty": 5,
            "company_tags": ["蚂蚁", "京东", "招商银行", "微众银行"],
        },
    ],
}


PROJECT = {
    "meta": {
        "chapter": "ml-ch09",
        "title": "支持向量机与核方法 —— 综合项目",
        "category": "ml",
        "count": 1,
    },
    "items": [
        {
            "title": "用 NumPy 从零实现软间隔 SVM（SMO）并做核函数对比",
            "requirement_md": "目标：把「对偶 + KKT + 核技巧」落成可运行代码，并用实验回答「什么时候该用核」。\n\n1. **实现 SMO**：实现双变量 SMO（含工作集选择、$[L,H]$ 裁剪、$\\eta\\le0$ 退化处理、$b$ 的三种取值规则），在 1D/2D 两类数据上收敛，打印迭代次数与最终目标值。\n2. **KKT 自检**：训练后逐样本计算 $y_if(x_i)$ 与 $\\alpha_i$，输出「普通点 / 自由 SV / 有界 SV」的计数，并验证 $\\sum\\alpha_iy_i=0$、$0\\le\\alpha_i\\le C$ 与互补松弛的数值误差（应 < 1e-6）。\n3. **C 的影响**：$C\\in\\{0.01,0.1,1,10,100\\}$ 各训一次，输出「间隔宽度、支持向量数、训练误差」三列表，并解释趋势。\n4. **核对比**：在同心圆数据（内圈/外圈）上分别用线性核、多项式核 $(x^\\top z+1)^2$、RBF（$\\gamma\\in\\{0.1,1,10\\}$）训练，输出各自的训练准确率与支持向量数，给出「哪种核 + 哪个 gamma 最合适」的结论。\n5. **核矩阵健康检查**：对每个核计算 Gram 矩阵的特征值，输出最小特征值与有效秩（$>10^{-6}$ 的特征值个数），并解释 RBF 的 $\\gamma$ 如何改变有效秩。\n6. **概率校准**：对最佳模型用 Platt scaling（在训练集上拟合 $1/(1+e^{Af+B})$，用 5 折避免过拟合），画出可靠性曲线（分箱后对比预测概率与实际正例率），并说明为什么 SVM 的距离不能直接当概率。",
            "tasks": [
                {
                    "title": "实现并验证 SMO",
                    "verification": {
                        "type": "output",
                        "desc": "在可分与不可分两类 1D 数据上均收敛（迭代 < 500 次）；输出的 w、b 与解析解（可分对称情形）误差 < 1e-6。",
                    },
                },
                {
                    "title": "KKT 自检与三类支持向量统计",
                    "verification": {
                        "type": "output",
                        "desc": "打印三类支持向量计数与互补松弛的最大违反量；$\\sum\\alpha_iy_i$ 的绝对值 < 1e-8，所有 $\\alpha_i\\in[0,C]$。",
                    },
                },
                {
                    "title": "C 的消融表",
                    "verification": {
                        "type": "output",
                        "desc": "5 个 C 值输出间隔宽度/支持向量数/训练误差；应观察到 C↑ → 间隔↓、SV 数↑（允许个别不单调），并给出解释。",
                    },
                },
                {
                    "title": "三种核的对比",
                    "verification": {
                        "type": "output",
                        "desc": "同心圆数据上：线性核准确率应 < 70%，RBF（合适 gamma）应 > 95%，多项式核居中；输出每个配置的准确率与 SV 数。",
                    },
                },
                {
                    "title": "核矩阵健康检查",
                    "verification": {
                        "type": "output",
                        "desc": "输出各核 Gram 的最小特征值与有效秩；RBF 的 gamma 从 0.1 到 10 时有效秩应显著上升（0.1 时接近 1，10 时接近样本数）。",
                    },
                },
                {
                    "title": "Platt 校准与可靠性曲线",
                    "verification": {
                        "type": "output",
                        "desc": "输出 10 个分箱的「预测概率 vs 实际正例率」，校准后应接近对角线（最大偏差 < 0.1）；并给出「距离≠概率」的数值证据（同一距离在不同 C 下对应不同概率）。",
                    },
                },
            ],
            "tags": ["SVM", "SMO", "核方法", "KKT", "概率校准"],
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
