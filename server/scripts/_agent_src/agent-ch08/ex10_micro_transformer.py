# title: 2 层微型 Transformer 前向与训练：字符级 loss 真的会降
# 纯 numpy 手写 forward + backward（含 LN、因果注意力、ReLU FFN），Adam 训练并做数值梯度检查。
import numpy as np

rng = np.random.default_rng(0)

TEXT = ("晴天的山谷里有一只狐狸。雨天的山谷里有一只兔子。"
        "晴天的河边有一匹马。雨天的河边有一头鹿。") * 10
chars = sorted(set(TEXT))
stoi = {c: i for i, c in enumerate(chars)}
data = np.array([stoi[c] for c in TEXT])
V = len(chars)

T, B, D, H, F, L = 16, 8, 32, 2, 64, 2
DH = D // H
split = int(0.8 * len(data))
train, val = data[:split], data[split:]

def init_params():
    p = {"E": rng.normal(0, 0.15, (V, D)), "P": rng.normal(0, 0.02, (T, D))}
    for l in range(L):
        p[f"Wq{l}"] = rng.normal(0, 0.15, (D, D))
        p[f"Wk{l}"] = rng.normal(0, 0.15, (D, D))
        p[f"Wv{l}"] = rng.normal(0, 0.15, (D, D))
        p[f"Wo{l}"] = rng.normal(0, 0.15, (D, D))
        p[f"W1_{l}"] = rng.normal(0, 0.15, (D, F))
        p[f"b1_{l}"] = np.zeros(F)
        p[f"W2_{l}"] = rng.normal(0, 0.10, (F, D))
        p[f"b2_{l}"] = np.zeros(D)
        p[f"ln1g{l}"] = np.ones(D); p[f"ln1b{l}"] = np.zeros(D)
        p[f"ln2g{l}"] = np.ones(D); p[f"ln2b{l}"] = np.zeros(D)
    p["lnfg"] = np.ones(D); p["lnfb"] = np.zeros(D)
    return p

def ln_fwd(x, g, b, eps=1e-5):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    inv = 1.0 / np.sqrt(var + eps)
    xh = (x - mu) * inv
    return xh * g + b, (xh, inv, g)

def ln_bwd(dy, cache):
    xh, inv, g = cache
    axes = tuple(range(dy.ndim - 1))
    dg = (dy * xh).sum(axis=axes)
    db = dy.sum(axis=axes)
    dxh = dy * g
    N = xh.shape[-1]
    dx = inv / N * (N * dxh - dxh.sum(-1, keepdims=True)
                    - xh * (dxh * xh).sum(-1, keepdims=True))
    return dx, dg, db

MASK = np.triu(np.ones((T, T)), 1) * -1e9

def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)

def forward(p, ids):
    Bn, Tn = ids.shape
    h = p["E"][ids] + p["P"][:Tn]
    cache = []
    for l in range(L):
        a, c1 = ln_fwd(h, p[f"ln1g{l}"], p[f"ln1b{l}"])
        q = (a @ p[f"Wq{l}"]).reshape(Bn, Tn, H, DH).transpose(0, 2, 1, 3)
        k = (a @ p[f"Wk{l}"]).reshape(Bn, Tn, H, DH).transpose(0, 2, 1, 3)
        v = (a @ p[f"Wv{l}"]).reshape(Bn, Tn, H, DH).transpose(0, 2, 1, 3)
        S = q @ k.transpose(0, 1, 3, 2) / np.sqrt(DH) + MASK[:Tn, :Tn]
        A = softmax(S)
        O = A @ v
        Oc = O.transpose(0, 2, 1, 3).reshape(Bn, Tn, D)
        h = h + Oc @ p[f"Wo{l}"]

        m, c2 = ln_fwd(h, p[f"ln2g{l}"], p[f"ln2b{l}"])
        z = m @ p[f"W1_{l}"] + p[f"b1_{l}"]
        r = np.maximum(z, 0)
        h = h + r @ p[f"W2_{l}"] + p[f"b2_{l}"]
        cache.append((a, q, k, v, A, Oc, c1, m, z, r, c2))
    hn, cf = ln_fwd(h, p["lnfg"], p["lnfb"])
    logits = hn @ p["E"].T
    return logits, (ids, cache, hn, cf)

def loss_and_grad(p, ids, targets):
    logits, (ids, cache, hn, cf) = forward(p, ids)
    Bn, Tn, _ = logits.shape
    z = logits - logits.max(-1, keepdims=True)
    logp = z - np.log(np.exp(z).sum(-1, keepdims=True))
    loss = -logp.reshape(-1, V)[np.arange(Bn * Tn), targets.reshape(-1)].mean()
    dl = np.exp(logp)
    dl.reshape(-1, V)[np.arange(Bn * Tn), targets.reshape(-1)] -= 1
    dl /= (Bn * Tn)

    g = {k: np.zeros_like(v) for k, v in p.items()}
    g["E"] = dl.reshape(-1, V).T @ hn.reshape(-1, D)
    dh = (dl @ p["E"]).reshape(Bn, Tn, D)

    dh, g["lnfg"], g["lnfb"] = ln_bwd(dh, cf)

    for l in range(L - 1, -1, -1):
        a, q, k, v, A, Oc, c1, m, z, r, c2 = cache[l]
        # FFN 分支
        dr = dh @ p[f"W2_{l}"].T
        g[f"W2_{l}"] = r.reshape(-1, F).T @ dh.reshape(-1, D)
        g[f"b2_{l}"] = dh.sum((0, 1))
        dz = dr * (z > 0)
        g[f"W1_{l}"] = m.reshape(-1, D).T @ dz.reshape(-1, F)
        g[f"b1_{l}"] = dz.sum((0, 1))
        dm = dz @ p[f"W1_{l}"].T
        dln2, g[f"ln2g{l}"], g[f"ln2b{l}"] = ln_bwd(dm, c2)
        dh = dh + dln2
        # 注意力分支
        dOc = (dh @ p[f"Wo{l}"].T).reshape(Bn, Tn, H, DH).transpose(0, 2, 1, 3)
        g[f"Wo{l}"] = Oc.reshape(-1, D).T @ dh.reshape(-1, D)
        dA = dOc @ v.transpose(0, 1, 3, 2)
        dv = A.transpose(0, 1, 3, 2) @ dOc
        dS = A * (dA - (dA * A).sum(-1, keepdims=True))
        dq = dS @ k / np.sqrt(DH)
        dk = dS.transpose(0, 1, 3, 2) @ q / np.sqrt(DH)
        to_flat = lambda x: x.transpose(0, 2, 1, 3).reshape(Bn * Tn, D)
        dqf, dkf, dvf = to_flat(dq), to_flat(dk), to_flat(dv)
        af = a.reshape(Bn * Tn, D)
        g[f"Wq{l}"] = af.T @ dqf
        g[f"Wk{l}"] = af.T @ dkf
        g[f"Wv{l}"] = af.T @ dvf
        da = (dqf @ p[f"Wq{l}"].T + dkf @ p[f"Wk{l}"].T
              + dvf @ p[f"Wv{l}"].T).reshape(Bn, Tn, D)
        dln1, g[f"ln1g{l}"], g[f"ln1b{l}"] = ln_bwd(da, c1)
        dh = dh + dln1

    np.add.at(g["E"], ids.reshape(-1), dh.reshape(-1, D))
    g["P"][:Tn] = dh.sum(0)
    return loss, g

def batch(seg, bs=B):
    starts = rng.integers(0, len(seg) - T - 1, size=bs)
    x = np.stack([seg[s:s + T] for s in starts])
    y = np.stack([seg[s + 1:s + T + 1] for s in starts])
    return x, y

def eval_loss(p, seg):
    losses = []
    for s in range(0, len(seg) - T - 1, B):
        starts = range(s, min(s + B, len(seg) - T - 1))
        x = np.stack([seg[i:i + T] for i in starts])
        y = np.stack([seg[i + 1:i + T + 1] for i in starts])
        lg, _ = forward(p, x)
        z = lg - lg.max(-1, keepdims=True)
        lp = z - np.log(np.exp(z).sum(-1, keepdims=True))
        losses.append(-lp.reshape(-1, V)[np.arange(x.size), y.reshape(-1)].mean())
    return float(np.mean(losses))

p = init_params()
n_params = sum(v.size for v in p.values())
print(f"字符表 {V} 个，训练 {len(train)} / 验证 {len(val)} 字符")
print(f"模型：L={L}, d={D}, H={H}, ffn={F}, T={T}，参数量 {n_params:,}")
print(f"随机基线 loss ≈ ln(V) = {np.log(V):.3f}")

# 数值梯度检查（训练前，固定一个 batch）
x_chk, y_chk = batch(train, bs=2)
loss_chk, grad_chk = loss_and_grad(p, x_chk, y_chk)
print("\n数值梯度检查（中心差分，eps=1e-4）：")
print(f"{'参数':<8}{'解析梯度':>12}{'数值梯度':>12}{'相对误差':>10}")
for name, idx in (("E", (int(x_chk[0, 0]), 3)), ("Wq0", (3, 5)), ("W1_1", (7, 9)), ("lnfg", (2,))):
    orig = p[name][idx]
    p[name][idx] = orig + 1e-4
    lp, _ = loss_and_grad(p, x_chk, y_chk)
    p[name][idx] = orig - 1e-4
    lm, _ = loss_and_grad(p, x_chk, y_chk)
    p[name][idx] = orig
    num = (lp - lm) / 2e-4
    ana = grad_chk[name][idx]
    rel = abs(num - ana) / (abs(num) + abs(ana) + 1e-12)
    print(f"{name:<8}{ana:>12.5e}{num:>12.5e}{rel:>10.1e}")

# Adam 训练
m_ad = {k: np.zeros_like(v) for k, v in p.items()}
v_ad = {k: np.zeros_like(v) for k, v in p.items()}
lr, b1, b2, eps = 8e-3, 0.9, 0.999, 1e-8
STEPS = 400
print(f"\n开始训练 {STEPS} 步（Adam, lr={lr}）")
print(f"{'step':>5}{'train':>9}{'val':>9}{'ppl':>9}")
for step in range(1, STEPS + 1):
    xb, yb = batch(train)
    loss, g = loss_and_grad(p, xb, yb)
    for k in p:
        m_ad[k] = b1 * m_ad[k] + (1 - b1) * g[k]
        v_ad[k] = b2 * v_ad[k] + (1 - b2) * g[k] ** 2
        mh = m_ad[k] / (1 - b1 ** step)
        vh = v_ad[k] / (1 - b2 ** step)
        p[k] -= lr * mh / (np.sqrt(vh) + eps)
    if step % 50 == 0 or step == 1:
        tr = loss
        vl = eval_loss(p, val)
        print(f"{step:>5}{tr:>9.3f}{vl:>9.3f}{np.exp(vl):>9.1f}")

def generate(p, prompt, n=40, temp=0.8):
    ids = np.array([[stoi[c] for c in prompt]])
    for _ in range(n):
        lg, _ = forward(p, ids[:, -T:])
        z = lg[0, -1] / temp
        z = z - z.max()
        prob = np.exp(z) / np.exp(z).sum()
        nxt = int(rng.choice(V, p=prob))
        ids = np.concatenate([ids, np.array([[nxt]])], axis=1)
    return "".join(chars[i] for i in ids[0])

print("\n训练后采样（prompt=晴天的山谷）：")
print("  " + generate(p, "晴天的山谷", n=28))
print("训练前同样 prompt（同一模型初始化重新采样，仅作对照）：")
p0 = init_params()
print("  " + generate(p0, "晴天的山谷", n=28))

print(f"\n结论：loss 从 {np.log(V):.2f} 降到 {eval_loss(p, val):.2f}（perplexity "
      f"{np.exp(eval_loss(p, val)):.1f}），注意力 + FFN + LN 的前向/反向都跑通了。")
print("读法：")
print("1. 先看 loss 是否低于 ln(V)，否则模型连词频都没学会；")
print("2. train 与 val 同步下降 = 欠拟合还没结束，继续训；val 先升 = 过拟合，早停；")
print("3. 数值梯度检查相对误差 <1e-4 才说明反向推导没写错（本实验实测见上表）；")
print("4. 小模型能背下训练语料，别用训练集 loss 宣称「学会了语言」。")
