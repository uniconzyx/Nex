# title: Adam vs SGD：病态二次型上的收敛速度对比
# 关键手法：同一个目标、同一初始点，只换更新规则；看损失与参数轨迹。
import numpy as np

# f(w) = 0.5*(w0^2 + 100*w1^2)，条件数 κ = 100
A = np.diag([1.0, 100.0])
def loss(w):
    return 0.5 * w @ A @ w
def grad(w):
    return A @ w

def run(kind, steps=400):
    w = np.array([1.0, 1.0])
    m = np.zeros(2); v = np.zeros(2)
    hist = []
    for t in range(1, steps + 1):
        g = grad(w)
        if kind == "sgd":
            w = w - 0.005 * g
        elif kind == "momentum":
            m = 0.9 * m + g
            w = w - 0.005 * m
        else:  # Adam
            m = 0.9 * m + 0.1 * g
            v = 0.999 * v + 0.001 * g * g
            mh = m / (1 - 0.9 ** t)
            vh = v / (1 - 0.999 ** t)
            w = w - 0.1 * mh / (np.sqrt(vh) + 1e-8)
        hist.append(loss(w))
    return np.array(hist), w

print(f"条件数 κ(A) = {np.linalg.cond(A):.0f}，初始点 (1, 1)，初始损失 {loss(np.ones(2)):.3f}")
print(f"\n{'步数':>6} " + " ".join(f"{k:>12}" for k in ("SGD", "Momentum", "Adam")))
res = {k: run(k) for k in ("sgd", "momentum", "adam")}
for t in (0, 20, 50, 100, 200, 399):
    row = " ".join(f"{res[k][0][t]:>12.3e}" for k in ("sgd", "momentum", "adam"))
    print(f"{t+1:>6} " + row)

print("\n最终参数与损失：")
for k in ("sgd", "momentum", "adam"):
    h, w = res[k]
    print(f"  {k:>8}: w = [{w[0]:+.4f}, {w[1]:+.4f}]  loss = {h[-1]:.3e}")

def steps_to(k, thr=1e-4):
    h, _ = res[k]
    idx = np.where(h < thr)[0]
    return int(idx[0] + 1) if len(idx) else None

print("\n达到 loss < 1e-4 所需步数：")
for k in ("sgd", "momentum", "adam"):
    s = steps_to(k)
    print(f"  {k:>8}: {s if s else '未达到（>400 步）'}")

print("\n读法：SGD 在曲率大的方向步长受限于 2/L（这里 L=100），只能小步走；")
print("Adam 用梯度二阶矩 v 给每个坐标单独缩放步长，等价于「每个方向一个学习率」。")
print("结论：Adam 收敛快、对尺度不敏感，是默认优化器；但它不保证更好的泛化，")
print("调到最优附近后，SGD/动量 + 调学习率常能拿到略好的最终精度。")
