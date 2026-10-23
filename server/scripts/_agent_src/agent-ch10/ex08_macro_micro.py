# title: 混淆矩阵与宏/微平均：accuracy 80% 的系统，拒答类可能只有 0.33 F1
import numpy as np

# 50 条黄金集上的意图分类结果（行=真值，列=预测），类别不均衡：查询 30 / 计算 10 / 创作 6 / 拒答 4。
# 直接构造混淆矩阵（而非抽样），保证每个数字可手算复核。
CLASSES = ["查询", "计算", "创作", "拒答"]
CM = np.array([
    [28, 1, 1, 0],   # 真值 查询(30)
    [1, 8, 0, 1],    # 真值 计算(10)
    [2, 1, 3, 0],    # 真值 创作(6)
    [2, 1, 0, 1],    # 真值 拒答(4)
], dtype=int)


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def prf(cm):
    """逐类 precision / recall / F1（one-vs-rest）。"""
    tp = np.diag(cm).astype(float)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    p = tp / np.maximum(tp + fp, 1)
    r = tp / np.maximum(tp + fn, 1)
    f = 2 * p * r / np.maximum(p + r, 1e-12)
    return p, r, f


n = CM.sum()
acc = np.trace(CM) / n
p, r, f = prf(CM)

print("== 1) 混淆矩阵（行=真值，列=预测） ==")
header = pad("真值\\预测", 10) + "".join(pad(c, 6) for c in CLASSES) + pad("合计", 6)
print(header)
for i, c in enumerate(CLASSES):
    row = pad(c, 10) + "".join(f"{CM[i, j]:>4d}  " for j in range(len(CLASSES)))
    print(row + f"{CM[i].sum():>4d}")
print(f"对角线命中 {np.trace(CM)}/{n}，accuracy = {acc:.1%}")

print("\n== 2) 逐类指标 ==")
print(f"{pad('类别', 8)}{'support':>8}{'precision':>10}{'recall':>9}{'F1':>8}")
for i, c in enumerate(CLASSES):
    print(f"{pad(c, 8)}{CM[i].sum():>8}{p[i]:>10.2f}{r[i]:>9.2f}{f[i]:>8.2f}")

macro_f1 = f.mean()
micro_f1 = acc                      # 单标签多分类中 micro-P = micro-R = micro-F1 = accuracy
weighted_f1 = (f * CM.sum(axis=1)).sum() / n
print(f"\nmacro-F1（各类等权）   = {macro_f1:.3f}")
print(f"micro-F1（样本等权）   = {micro_f1:.3f}  <- 单标签多分类下恒等于 accuracy")
print(f"weighted-F1（按 support 加权）= {weighted_f1:.3f}")
print(f"accuracy = {acc:.1%} 看起来不错，但拒答类 recall 只有 {r[3]:.2f}：4 条该拒的样本 3 条被当成其他意图硬答")

print("\n== 3) 修一个少数类，指标各自涨多少 ==")
CM2 = CM.copy()
CM2[3, 3] += 3; CM2[3, 0] -= 2; CM2[3, 1] -= 1     # 拒答漏判的 3 条全部判对
p2, r2, f2 = prf(CM2)
acc2 = np.trace(CM2) / n
print(f"accuracy:   {acc:.1%} -> {acc2:.1%}（+{(acc2 - acc) * 100:.0f}pp）")
print(f"macro-F1:   {macro_f1:.3f} -> {f2.mean():.3f}（+{f2.mean() - macro_f1:.3f}）")
print(f"同一次修复，accuracy 只涨 {(acc2 - acc) * 100:.0f}pp，macro-F1 涨 {f2.mean() - macro_f1:.2f}"
      f"——报哪个指标，决定团队优先修哪类错误")

print("\n== 4) 宏/微平均的使用口径 ==")
print("micro：样本等权，被大类主导——适合「整体流量错得多少」；")
print("macro ：类别等权，少数类失败会显形——适合「每类意图都不能崩」的 SLA；")
print("weighted：折中，既反映 support 又不完全被大类淹没——周报常用，但要与 macro 同时报。")

print("\n结论：accuracy/micro-F1 会被大类掩盖问题，拒答类的漏判在 accuracy 上几乎看不见，却是「不懂也硬答」的直接来源；")
print("读法：1. 混淆矩阵先看非对角线集中在哪（本例是创作/拒答被错分到查询）；2. 类别不均衡时 macro-F1 与逐类 recall 必须和 accuracy 同时报；3. 单标签多分类下 micro-F1 恒等于 accuracy，两个都报不会增加信息，要补 macro；4. 本示例的混淆矩阵为构造值，数字可由矩阵手算复核。")
