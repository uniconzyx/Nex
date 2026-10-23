# title: 激活函数对比：值、导数与饱和区
# 关键手法：导数决定梯度能不能传回去；数值微分用来验证你记的公式。
import numpy as np

def sigmoid(z):
    z = np.clip(z, -50, 50)
    return 1.0 / (1.0 + np.exp(-z))

act = {
    "sigmoid": (sigmoid, lambda z: sigmoid(z) * (1 - sigmoid(z))),
    "tanh": (np.tanh, lambda z: 1 - np.tanh(z) ** 2),
    "relu": (lambda z: np.maximum(z, 0), lambda z: (z > 0).astype(float)),
    "leaky_relu": (lambda z: np.where(z > 0, z, 0.01 * z),
                   lambda z: np.where(z > 0, 1.0, 0.01)),
}

xs = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
print("激活函数取值 f(x)：")
print(f"{'x':>6} " + " ".join(f"{k:>12}" for k in act))
for x in xs:
    print(f"{x:>6.1f} " + " ".join(f"{act[k][0](np.array([x]))[0]:>12.4f}" for k in act))

print("\n导数 f'(x)（决定反向传播时梯度被放大还是压扁）：")
print(f"{'x':>6} " + " ".join(f"{k:>12}" for k in act))
for x in xs:
    print(f"{x:>6.1f} " + " ".join(f"{act[k][1](np.array([x]))[0]:>12.4f}" for k in act))

# 数值微分校验解析导数：中心差分
z0 = 0.7
eps = 1e-6
print(f"\n在 z={z0} 处用中心差分校验导数（步长 {eps:g}）：")
for k, (f, df) in act.items():
    num = (f(np.array([z0 + eps]))[0] - f(np.array([z0 - eps]))[0]) / (2 * eps)
    ana = df(np.array([z0]))[0]
    print(f"  {k:>10}: 解析 {ana:>8.5f}  数值 {num:>8.5f}  误差 {abs(num-ana):.2e}")

# 饱和与死亡：这两件事是「训练不动」的最常见原因
print("\n饱和/死亡统计：")
print(f"  sigmoid'(5)  = {act['sigmoid'][1](np.array([5.0]))[0]:.5f}"
      f"  (是 sigmoid'(0)={act['sigmoid'][1](np.array([0.0]))[0]:.4f} 的"
      f" {act['sigmoid'][1](np.array([5.0]))[0]/0.25:.1%})")
rng = np.random.default_rng(0)
pre = rng.normal(-0.5, 1.0, 10000)   # 偏置把神经元整体往负半轴推
print(f"  某层 10000 个 pre-activation 中 ReLU 输出为 0 的比例：{np.mean(pre <= 0):.1%}")
print(f"  这些位置的 ReLU 导数恒为 0 —— 梯度到此为止，参数永远不更新（dead ReLU）。")

print("\n读法：sigmoid/tanh 在 |z|>3 后导数接近 0，深堆会衰减梯度；")
print("ReLU 正区间导数恒为 1，计算便宜，但负区间会死。")
print("结论：隐藏层默认 ReLU（或 Leaky ReLU），输出层按任务选：")
print("二分类 sigmoid、多分类 softmax、回归 linear（恒等）。")
