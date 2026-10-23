# title: 前向传播手算：一个神经元到底在算什么
# 关键手法：先按标量逐个算一遍，再用矩阵一次算完，两者必须逐位相等。
import numpy as np

x = np.array([1.0, 2.0])
W1 = np.array([[0.5, -0.3],
               [0.2,  0.8]])
b1 = np.array([0.1, -0.1])

print("输入 x =", x, " 形状", x.shape)
print("\n[第 1 层] 两个神经元各自做「加权和 + 偏置」：")
for j in range(2):
    s = W1[j, 0] * x[0] + W1[j, 1] * x[1] + b1[j]
    print(f"  神经元{j}: z = {W1[j,0]}*{x[0]} + {W1[j,1]}*{x[1]} + {b1[j]} = {s:.3f}")
z1 = W1 @ x + b1
h = np.maximum(z1, 0.0)
print("  向量化 z1 = W1 @ x + b1 =", np.round(z1, 3))
print("  ReLU 后 h =", np.round(h, 3), " （负值被截成 0）")

W2 = np.array([[1.0, -2.0]])
b2 = np.array([0.05])
out = W2 @ h + b2
print("\n[第 2 层] 1 个输出神经元（线性激活）：")
print(f"  z2 = 1.0*{h[0]:.3f} + (-2.0)*{h[1]:.3f} + 0.05 = {out[0]:.3f}")

# 批量：每行一个样本，维度约定 (m, d_in) @ (d_in, d_out)
X = np.array([[1.0, 2.0],
              [0.5, -1.0],
              [-1.0, 0.5]])
Z1 = X @ W1.T + b1          # 注意 W1 的形状是 (d_out, d_in)，所以转置
H = np.maximum(Z1, 0.0)
Y = H @ W2.T + b2
print("\n[批量前向] m=3 个样本：")
print("  X 形状", X.shape, " W1.T 形状", W1.T.shape, " -> Z1 形状", Z1.shape)
print("  Z1 =\n", np.round(Z1, 3))
print("  H  =\n", np.round(H, 3))
print("  Y 形状", Y.shape, " Y =", np.round(Y.ravel(), 3))

loop = np.array([W2 @ np.maximum(W1 @ X[i] + b1, 0) + b2 for i in range(len(X))])
print("\n批量结果与逐样本循环的最大差：", f"{np.abs(Y.ravel() - loop.ravel()).max():.2e}")

print("\n读法：一层 = 仿射变换（Wx+b）+ 逐元素非线性；单个样本是 (1,d_in)，")
print("批量是 (m,d_in)。形状对不上时，先检查 W 是 (d_out,d_in) 还是 (d_in,d_out)。")
print("结论：所谓「深层网络」，就是把这一行代码重复 L 次，中间不改变维度约定。")
