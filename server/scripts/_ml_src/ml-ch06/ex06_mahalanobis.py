# title: 马氏距离：让协方差结构参与异常判定
# 强相关各向异性数据上，对比三种检测器：欧氏距离、完整协方差的马氏距离、
# 对角协方差（假装特征独立）。看「边际正常、联合异常」的点谁能抓住。
import numpy as np

rng = np.random.default_rng(13)
n = 400
Sigma = np.array([[2.5, 1.5], [1.5, 1.0]])          # 强相关 + 各向异性
L = np.linalg.cholesky(Sigma)
X = rng.normal(size=(n, 2)) @ L.T
mu = X.mean(0)
evals, evecs = np.linalg.eigh(Sigma)                # 升序
v_major, v_minor = evecs[:, 1], evecs[:, 0]         # 长轴 / 短轴方向

# 两类注入异常（都从 μ 出发）
famA = mu + np.c_[rng.uniform(1.5, 2.0, 10), rng.uniform(1.0, 1.4, 10)] @ np.c_[v_major, v_minor].T
famB = mu + 6.0 * v_major + 0.0 * v_minor + rng.normal(0, 0.02, size=(10, 2)) @ np.c_[v_major, v_minor].T
anom = np.vstack([famA, famB])
fam = np.r_[np.zeros(10, int), np.ones(10, int)]

Sigma_hat = np.cov(X, rowvar=False, bias=True)      # MLE（除以 n）
D_hat = np.diag(np.diag(Sigma_hat))                 # 对角近似：假装特征独立
Sigma_inv = np.linalg.inv(Sigma_hat)
D_inv = np.linalg.inv(D_hat)

dX = X - mu
dA = anom - mu
scores_normal = {
    "欧氏距离": np.linalg.norm(dX, axis=1),
    "马氏(完整Σ)": np.sqrt(np.einsum("ij,jk,ik->i", dX, Sigma_inv, dX)),
    "马氏(对角Σ)": np.sqrt(np.einsum("ij,jk,ik->i", dX, D_inv, dX)),
}
scores_anom = {
    "欧氏距离": np.linalg.norm(dA, axis=1),
    "马氏(完整Σ)": np.sqrt(np.einsum("ij,jk,ik->i", dA, Sigma_inv, dA)),
    "马氏(对角Σ)": np.sqrt(np.einsum("ij,jk,ik->i", dA, D_inv, dA)),
}

print(f"协方差 Σ = [[{Sigma[0, 0]}, {Sigma[0, 1]}], [{Sigma[1, 0]}, {Sigma[1, 1]}]]，"
      f"特征值 = [{evals[0]:.3f}, {evals[1]:.3f}]（长轴/短轴 = {np.sqrt(evals[1] / evals[0]):.1f} 倍）")
print(f"长轴方向 v₁=({v_major[0]:.3f},{v_major[1]:.3f})，短轴方向 v₂=({v_minor[0]:.3f},{v_minor[1]:.3f})")
print("异常设计：家族 A = 1.5~2.0·v₁ + 1.0~1.4·v₂（沿短轴偏 3~5 个短轴标准差，欧氏距离只有 ~2）；")
print("          家族 B = 6·v₁（欧氏距离 6，显眼的强异常）\n")

thr = {k: float(np.percentile(v, 97.5)) for k, v in scores_normal.items()}
print(f"{'检测器':<14}{'阈值(97.5%)':>12}{'正常误报/400':>14}{'家族A检出':>12}{'家族B检出':>12}")
for k in scores_normal:
    fa = int((scores_normal[k] > thr[k]).sum())
    ca = int((scores_anom[k][fam == 0] > thr[k]).sum())
    cb = int((scores_anom[k][fam == 1] > thr[k]).sum())
    print(f"{k:<14}{thr[k]:>12.3f}{fa:>14}{ca:>10}/10{cb:>10}/10")

# 单个家族 A 样本的解剖
d0 = dA[0]
z = np.array([d0[0] / np.sqrt(Sigma_hat[0, 0]), d0[1] / np.sqrt(Sigma_hat[1, 1])])
d_full = float(np.sqrt(d0 @ Sigma_inv @ d0))
d_diag = float(np.sqrt(d0 @ D_inv @ d0))
print(f"\n解剖家族 A 第 1 个点：偏移 Δ=({d0[0]:.2f},{d0[1]:.2f})")
print(f"  欧氏距离 = {np.linalg.norm(d0):.2f} < 阈值 {thr['欧氏距离']:.2f} → 漏检")
print(f"  马氏距离 = {d_full:.2f} > 阈值 {thr['马氏(完整Σ)']:.2f} → 抓住（ whitening 后 "
      f"{np.linalg.norm(np.linalg.inv(np.linalg.cholesky(Sigma_hat)) @ d0):.2f}，与上式一致）")
print(f"  对角马氏 = {d_diag:.2f} < 阈值 {thr['马氏(对角Σ)']:.2f} → 漏检")
print(f"  边际 z 分数 = ({z[0]:.2f}, {z[1]:.2f})：两个特征单独看都正常，联合看是 {d_full:.1f}σ 事件")

print("\n结论：")
print("1. 读法：欧氏距离和对角协方差把家族 A 全部漏掉（欧氏距离 ~2.3 埋在正常范围里），")
print("   完整协方差的马氏距离 10/10 抓住——它知道『沿短轴偏 3~5 个标准差』比『沿长轴偏 2σ』更异常；")
print("2. 机理：马氏距离 d²=(x−μ)ᵀΣ⁻¹(x−μ) 就是白化空间里的欧氏距离：先把椭圆捏成圆球，")
print("   再量长度。对角 Σ 等价于假设特征独立，遇到相关特征时，沿短轴的偏移被长轴的方差『掩护』，")
print("   边际 z 分数看起来人畜无害，联合密度却已经掉到尾部。")
print("3. 工程：① 异常检测不要直接用欧氏距离，先看特征相关图，强相关就上完整协方差；")
print("   ② 完整 Σ 有 d(d+1)/2 个参数，d 大时估计不稳——要正则化（shrinkage）或降维后再估；")
print("   ③ 协方差本身也会被异常点带偏（一个极端点就能扭歪主轴），实践中先 Robust 估计再检测。")
