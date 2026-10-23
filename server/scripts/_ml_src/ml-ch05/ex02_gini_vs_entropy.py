# title: 基尼 vs 熵：曲率差异如何改变分裂偏好
# 1) 画出二分类下两条不纯度曲线的端点斜率；
# 2) 构造同一父结点（50/50）上的两个候选切分，让两种口径给出相反排序。
import numpy as np


def H(p):
    p = np.asarray(p, float)
    q = 1 - p
    out = np.zeros_like(p)
    m = (p > 0) & (q > 0)
    out[m] = -(p[m] * np.log2(p[m]) + q[m] * np.log2(q[m]))
    return out


def G(p):
    p = np.asarray(p, float)
    return 2 * p * (1 - p)


print("二分类结点的不纯度（p = 正例占比）")
print(f"{'p':>5}{'H(p)':>9}{'Gini(p)':>9}{'dH/dp':>9}{'dGini/dp':>11}")
for p in (0.0, 0.01, 0.05, 0.10, 0.20, 0.30, 0.50):
    h, g = H(p), G(p)
    # 解析导数：dH/dp = -log2(p/(1-p))；dGini/dp = 2 - 4p
    dh = -np.log2(p / (1 - p)) if 0 < p < 1 else float("nan")
    dg = 2 - 4 * p
    print(f"{p:>5.2f}{h:>9.4f}{g:>9.4f}{dh:>9.3f}{dg:>11.3f}")

print()
print("读法：p→0 时 dH/dp→−∞，而 dGini/dp→2。")
print("      熵在『接近纯』的区域极其陡峭，所以它愿意为『把一小撮样本变纯』付出代价；")
print("      基尼是二次函数，端点斜率有限，更偏好把两个子结点都推到中间偏纯的位置。")

# 两个候选切分，父结点均为 50/50、共 100 条样本
def split_gain(w, p1):
    """左子结点占比 w、正例率 p1；父结点正例率固定 0.5，反解右子结点。"""
    p2 = (0.5 - w * p1) / (1 - w)
    eh = float(H([0.5])[0] - (w * H([p1])[0] + (1 - w) * H([p2])[0]))
    eg = float(G([0.5])[0] - (w * G([p1])[0] + (1 - w) * G([p2])[0]))
    return p2, eh, eg


A = split_gain(0.10, 0.00)   # 10% 切出来完全纯，剩余 90% 是 0.556
B = split_gain(0.20, 0.15)   # 20% 切到 0.15，剩余 80% 是 0.588

print()
print("候选切分（父结点：50 正 / 50 负）")
print(f"{'切分':<6}{'左占比':>7}{'左p':>7}{'右p':>8}{'ΔH(bit)':>10}{'ΔGini':>9}")
for name, w, p1, res in (("A", 0.10, 0.00, A), ("B", 0.20, 0.15, B)):
    print(f"{name:<6}{w:>7.2f}{p1:>7.2f}{res[0]:>8.3f}{res[1]:>10.4f}{res[2]:>9.4f}")

print()
print(f"信息增益：A={A[1]:.4f} > B={B[1]:.4f}，熵选 A（切出一小块绝对纯的结点）")
print(f"基尼增益：A={A[2]:.4f} < B={B[2]:.4f}，基尼选 B（两个子结点都更均衡地变纯）")
print("结论：两种不纯度不是单调等价的。差异只在『端点曲率』，但在小样本、类别不平衡时，")
print("      它足以改变树的结构；不要假设 sklearn 的 gini 与 entropy 结果只是数值噪声。")
