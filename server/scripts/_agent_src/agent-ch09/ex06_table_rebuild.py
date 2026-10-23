# title: 表格单元格还原：线检测有无线，列坐标聚类，最后都变成二维表
import numpy as np

rng = np.random.default_rng(0)


def detect_lines(grid, axis):
    """投影法检测线：axis=1 检测横线（行方向连续黑像素占比高的行）。"""
    black = (grid == 0).astype(int)
    ratio = black.mean(axis=1) if axis == 1 else black.mean(axis=0)
    return [i for i, r in enumerate(ratio) if r > 0.8]


def rebuild_wired(grid):
    """有线表：横竖线交叉点切出单元格网格，取每格中心区域代表文本。"""
    hlines = detect_lines(grid, axis=1)
    vlines = detect_lines(grid, axis=0)
    cells = []
    for i in range(len(hlines) - 1):
        row = []
        for j in range(len(vlines) - 1):
            y0, y1 = hlines[i] + 1, hlines[i + 1]
            x0, x1 = vlines[j] + 1, vlines[j + 1]
            block = grid[y0:y1, x0:x1]
            row.append("T" if (block == 0).sum() > block.size * 0.05 else "")
        cells.append(row)
    return cells, (len(hlines) - 1, len(vlines) - 1)


def rebuild_wireless(text_rows, col_centers, tol=3):
    """无线表：列坐标聚类还原逻辑列，再按行把词块归列。"""
    cols = sorted(col_centers)
    groups = [[cols[0]]]
    for c in cols[1:]:
        if c - groups[-1][-1] <= tol:
            groups[-1].append(c)
        else:
            groups.append([c])
    bounds = [int(np.mean(g)) for g in groups]
    table = []
    for row in text_rows:
        rec = [""] * len(bounds)
        for word, cx in row:
            k = min(range(len(bounds)), key=lambda i: abs(bounds[i] - cx))
            rec[k] = word
        table.append(rec)
    return table, len(bounds)


# 1) 有线表：3 行 4 列的商品表（4 条横线 x 5 条竖线）
grid = np.full((16, 40), 255, dtype="uint8")
for y in (3, 7, 11, 15):      # 横线
    grid[y, :] = 0
for x in (0, 10, 20, 30, 39):  # 竖线
    grid[:, x] = 0
for y in (5, 9, 13):          # 每行涂文本块（第三行第 4 列留空，展示空单元格）
    for k, (x0, x1) in enumerate(((2, 8), (12, 18), (22, 28), (32, 37))):
        if y == 13 and k == 3:
            continue
        grid[y, x0:x1] = 0
cells, shape = rebuild_wired(grid)
print("== 1) 有线表：线检测还原网格 ==")
print(f"检测到网格形状 = {shape}（期望 (3, 4)）")
assert shape == (3, 4)
for r in cells:
    print("  " + " | ".join(f"{c or '·':^6}" for c in r))

# 2) 无线表：靠空格对齐的报表
rows = [
    [("Q1", 2), ("100", 12), ("OK", 28)],
    [("Q2", 2), ("250", 12), ("NG", 28)],
    [("Q3", 2), ("380", 12), ("OK", 28)],
]
table, ncol = rebuild_wireless(rows, col_centers=[2, 12, 28], tol=3)
print("\n== 2) 无线表：列坐标聚类还原逻辑列 ==")
print(f"还原出 {ncol} 列（期望 3）")
assert ncol == 3
for r in table:
    print("  " + " | ".join(f"{c:^8}" for c in r))

# 3) 列边界漂移的鲁棒性：同一列的词块 x 坐标抖动 ±2 仍归同一列
noisy = [[(w, c + rng.integers(-2, 3)) for w, c in row] for row in rows]
t2, _ = rebuild_wireless(noisy, col_centers=[2, 12, 28], tol=3)
assert t2 == table, "抖动应被容差吸收"
print("\n== 3) 鲁棒性：词块 x 抖动 ±2 被 tol=3 吸收，还原结果不变 ==")

print("\n结论：表格还原先把图变成二维结构（有无线两条路径），再按行映射成记录，下游才能按字段消费；")
print("读法：1. 有线表走投影线检测，阈值 0.8 是按线长占比的经验值；2. 无线表走列坐标聚类，tol 决定多近算同一列，与字号/扫描倾斜有关；3. 整张表当一大段文本丢给模型，字段级错误率会飙升——结构化行是下游正确率的前提；4. 本示例用 numpy 字符画模拟扫描件，未调用任何 OCR。")
