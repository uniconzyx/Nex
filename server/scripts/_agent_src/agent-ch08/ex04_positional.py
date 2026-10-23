# title: 位置编码对比：正弦编码的距离结构 vs 学习式编码
# 比较两种编码的余弦相似度矩阵：正弦编码的相似度只依赖「相对位移」，学习式没有这个先验。
import numpy as np

T, D = 32, 16

def sinusoidal(T, D):
    pos = np.arange(T)[:, None]
    i = np.arange(0, D, 2)[None, :]
    angle = pos / (10000 ** (i / D))
    pe = np.zeros((T, D))
    pe[:, 0::2] = np.sin(angle)
    pe[:, 1::2] = np.cos(angle)
    return pe

PE_sin = sinusoidal(T, D)
PE_learn = np.random.default_rng(3).normal(0, 0.02, size=(T, D))   # 模拟训练后的查表

def cos_sim(P):
    Pn = P / np.linalg.norm(P, axis=1, keepdims=True)
    return Pn @ Pn.T

S_sin, S_learn = cos_sim(PE_sin), cos_sim(PE_learn)

print(f"位置数 {T}，维度 {D}")
print(f"{'位移':>5}{'正弦平均cos':>13}{'学习式平均cos':>15}")
for off in range(1, 9):
    a = np.mean([S_sin[i, i + off] for i in range(T - off)])
    b = np.mean([S_learn[i, i + off] for i in range(T - off)])
    print(f"{off:>5}{a:>13.4f}{b:>15.4f}")

print("\n正弦编码的「相对性」检验（同一位移，不同起点）：")
for off in (1, 4, 8):
    vals = [S_sin[i, i + off] for i in range(0, T - off, 5)]
    print(f"  位移 {off}: " + " ".join(f"{v:.4f}" for v in vals) +
          f"   极差={max(vals)-min(vals):.2e}")

# RoPE 的二维直觉：旋转后点积只依赖角度差
print("\nRoPE 二维直觉（旋转 θ=pos·ω，q·k 只与 pos 差有关）：")
omega = 0.3
q0 = np.array([1.0, 0.0])
k0 = np.array([0.8, 0.6])

def rotate(v, angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])

print(f"{'pos_q':>6}{'pos_k':>6}{'位移':>6}{'旋转后点积':>12}")
for pq, pk in ((0, 3), (5, 8), (10, 13), (0, 10), (10, 20)):
    d = rotate(q0, pq * omega) @ rotate(k0, pk * omega)
    print(f"{pq:>6}{pk:>6}{pk-pq:>6}{d:>12.6f}")
print("同位移 (0,3)/(5,8)/(10,13) 的点积完全相同 —— 这就是 RoPE 的相对位置性质。")

print("\n结论：正弦编码把位置变成「不同频率的相位」，相似度随位移总体衰减但有振荡")
print("      （多个频率叠加，不是干净的单调核）；学习式编码没有距离先验，超出训练长度无法外推。")
print("读法：绝对学习编码适合固定长度任务；长上下文与外推要用 RoPE/ALiBi 这类相对方案。")
print("      注意正弦编码不是「给每个位置一个唯一 ID」，而是给相对位移一个可计算的结构。")
