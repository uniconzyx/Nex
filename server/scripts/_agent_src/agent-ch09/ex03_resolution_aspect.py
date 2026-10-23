# title: 分辨率与长宽比的代价：token、显存与「填白」造成的有效信息损失
import numpy as np


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


P = 14


def ledger(h, w, p=P):
    n = (h // p) * (w // p)
    return n, n * n * 4 / 1e6  # token 数, 注意力矩阵 MB(fp32)


print("== 1) 边长翻倍：token x4，注意力显存 x16（双平方） ==")
base_n, base_m = ledger(224, 224)
print(f"{'分辨率':<12}{'token':>8}{'注意力MB':>10}{'相对token':>10}{'相对显存':>10}")
for h, w in [(224, 224), (448, 448), (896, 896), (1792, 1792)]:
    n, m = ledger(h, w)
    print(f"{h}x{w:<9}{n:>8}{m:>10.2f}{n / base_n:>9.2f}x{m / base_m:>9.1f}x")
n2, _ = ledger(448, 448)
assert abs((n2 / base_n) - 4.0) < 1e-9

print("\n== 2) 长宽比：把 2000x500 长表格塞进 1024x1024 正方形 ==")
# 等边缩放取短边：500 -> 1024 意味着 x2.048 倍，长边 2000 -> 4096，被裁掉一半
scale = 1024 / 500
visible_w = 1024 / scale  # 塞进画布后仍可见的原图宽度
loss = 1 - visible_w / 2000
print(f"为填满正方形短边需放大 {scale:.2f}x，长边原内容 {visible_w:.0f}/2000 像素可见")
print(f"被裁掉的内容占比 = {loss:.1%}，且文字被非等比压缩，小字进一步丢失")
assert loss > 0.4

print("\n== 3) 按长宽比选画布：同样内容，token 差多少 ==")
for name, (h, w) in {"塞正方形(裁半)": (1024, 1024),
                     "按比例 1000x250": (1000, 250),
                     "anyres 2x448²+全局": (448, 896)}.items():
    n, m = ledger(h, w)
    if name == "anyres 2x448²+全局":
        sub, _ = ledger(448, 448)
        n, m = 2 * sub + 1, 0  # 全局图另算，此处只计子图
        print(f"{pad(name, 18)}{n:>8}{'按子图计':>10}")
    else:
        print(f"{pad(name, 18)}{n:>8}{m:>10.2f}")

print("\n结论：分辨率按面积烧 token、按平方烧注意力显存；破坏长宽比换来的「满画布」是负优化，")
print("读法：1. 边长翻倍 = token x4 = 注意力显存 x16，预算决策要用面积思维；2. 长图塞正方形的正确做法是按长宽比选画布或 anyres 切图；3. 「有效内容占比」应在入口处监控——填白越多，每个 token 携带的信息越少；4. 本示例只做数值实验，不加载任何真实图像。")
