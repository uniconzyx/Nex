# -*- coding: utf-8 -*-
"""凯喵参考图批处理 v3：白底转透明 + 去水印 + 保留背景装饰。

管线（沿用验证过的护发参数）：
  1. 四角中位数估计背景色（float32 防 int16 溢出）
  2. 抹掉右下角「豆包AI生成」水印矩形（该区域只有水印与白底）
  3. 严格白阈值 dist<=14 + 边界泛洪（护浅金发：泛洪进不了闭合描边内部）
  4. 连通域过滤（scipy）：保留 人物(最大域) + 装饰模板质心命中(±60px) + <=1500px 小星光；
     删除其余大块（仅赛博朋克一类带纹理背景的噪声斑）
  5. choke 1px (MinFilter3) + GaussianBlur 0.6 羽化
  6. 前景 bbox 裁剪（含装饰）+ 方形画布 + 最长边 720
不做蓝色预乘（v2 教训：浅发染蓝）。
"""
import glob
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SRC = r"C:\Users\zyx\WorkBuddy\2026-09-19-21-42-03\CppMind\web-preview\assets\kaimao-src"
OUT = r"C:\Users\zyx\WorkBuddy\2026-09-19-21-42-03\CppMind\web-preview\assets\kaimao"
TOL = 14           # 严格白阈值，护浅金发
PAD = 6            # 处理前白边垫圈，保证边界是背景
WM = (0.78, 0.92)  # 水印矩形左上角比例
MAX_SIDE = 720
TEMPLATE = [(395, 1254), (1532, 1466), (1808, 679), (1847, 733), (1868, 802)]
TM_R = 60          # 模板质心匹配半径
SMALL = 2200       # 小星光保留上限（夜间行者有 ~2048px 的星饰）
MIN_AREA = 80      # 低于此面积一律视为 JPEG 碎点噪声（实测 1~2px 居多）
SAT_LOW = 0.12     # 低于此饱和度视为「贴白噪声斑」而非彩色装饰
BODY_RATIO = 0.96  # 人物主体高度占画布比例（14 张统一，避免切换时大小跳变）

JOBS = [
    ("src-1-idle.jpg",         "mood-idle.png"),
    ("src-2-think.jpg",        "mood-think.png"),
    ("src-3-happy.jpg",        "mood-happy.png"),
    ("src-4-shy.jpg",          "mood-shy.png"),
    ("src-5-aggrieved.jpg",    "mood-aggrieved.png"),
    ("src-6-sleepy.jpg",       "mood-sleepy.png"),
    ("src-7-cape.jpg",         "outfit-cape.png"),
    ("src-8-scarf.jpg",        "outfit-scarf.png"),
    ("src-9-glasses.jpg",      "outfit-glasses.png"),
    ("src-10-nightprowler.jpg", "outfit-nightprowler.png"),
    ("src-11-cyberpunk.jpg",   "outfit-cyberpunk.png"),
    ("src-12-panda.jpg",       "outfit-panda.png"),
    ("src-13-wizard.jpg",      "outfit-wizard.png"),
    ("src-14-celebrate.jpg",   "mood-celebrate.png"),
]


def estimate_bg(a):
    pts = [a[:24, :24], a[:24, -24:], a[-24:, :24], a[-24:, -24:]]
    return np.median(np.stack([p.reshape(-1, 3) for p in pts]), axis=(0, 1))


def flood_border(cand):
    b = np.zeros_like(cand)
    b[0, :] = cand[0, :]
    b[-1, :] = cand[-1, :]
    b[:, 0] = cand[:, 0]
    b[:, -1] = cand[:, -1]
    while True:
        g = b.copy()
        g[1:, :] |= b[:-1, :]
        g[:-1, :] |= b[1:, :]
        g[:, 1:] |= b[:, :-1]
        g[:, :-1] |= b[:, 1:]
        g &= cand
        if (g == b).all():
            return b
        b = g


def sat_of(mask, rgb):
    """连通域内像素的平均饱和度（0~1）。噪声斑贴白 → 近 0；彩纸糖果色 → 明显偏高。"""
    px = rgb[mask]
    if px.size == 0:
        return 0.0
    mx = px.max(-1)
    mn = px.min(-1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1.0), 0.0)
    return float(s.mean())


def keep_mask(fg, rgb):
    """保留人物 + 装饰（模板/彩纸/星光）；只删背景纹理噪声块。

    背景带纹理的图（如赛博朋克）会产生大量中尺寸噪声块，与真装饰无法按尺寸区分。
    判据不按「有无大块」而按「有无低饱和大块」：噪声斑是贴白的灰斑（饱和度≈0），
    而庆祝图的彩纸是高饱和糖果色，因此不会被误判为噪声图。
    """
    lab, n = ndimage.label(fg)
    if n <= 1:
        return fg, []
    sizes = np.bincount(lab.ravel())
    largest = int(np.argmax(sizes[1:])) + 1
    removed = []
    out = np.zeros_like(fg)

    # 预扫描：统计「非模板 + 大块 + 低饱和」的噪声块数量
    noisy = False
    lowsat_big = 0
    for lb in range(1, n + 1):
        if lb == largest or sizes[lb] <= SMALL:
            continue
        m = lab == lb
        ys, xs = np.where(m)
        cy, cx = ys.mean(), xs.mean()
        if any((cx - tx) ** 2 + (cy - ty) ** 2 <= TM_R ** 2 for tx, ty in TEMPLATE):
            continue
        if sat_of(m, rgb) < SAT_LOW:
            lowsat_big += 1
    if lowsat_big >= 3:
        noisy = True

    for lb in range(1, n + 1):
        m = lab == lb
        area = int(sizes[lb])
        if lb == largest:
            out |= m
            continue
        ys, xs = np.where(m)
        cy, cx = ys.mean(), xs.mean()
        hit = any((cx - tx) ** 2 + (cy - ty) ** 2 <= TM_R ** 2 for tx, ty in TEMPLATE)
        if hit:
            out |= m
            continue
        if noisy or area < MIN_AREA:
            removed.append((area, int(cx), int(cy)))
            continue
        out |= m
    return out, removed


def process(name, out_name):
    im = Image.open(os.path.join(SRC, name)).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.float32)
    bgc = estimate_bg(a)

    # 1) 去水印
    x0, y0 = int(w * WM[0]), int(h * WM[1])
    a[y0:, x0:] = bgc

    # 2) 严格白阈值 + 边界泛洪
    dist = np.sqrt(((a - bgc) ** 2).sum(-1))
    cand = np.pad(dist <= TOL, PAD, constant_values=True)
    truebg = flood_border(cand)
    fg = ~truebg[PAD:PAD + h, PAD:PAD + w]

    # 3) 连通域过滤（保留装饰）
    fg, removed = keep_mask(fg, a)

    # 4) alpha：choke + 羽化
    alpha = Image.fromarray((fg * 255).astype(np.uint8), "L")
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))

    # 5) 主体归一化：以人物(最大连通域)高度锁定画布，保证 14 张切换时大小不跳变
    rgba = im.convert("RGBA")
    rgba.putalpha(alpha)
    lab2, _ = ndimage.label(fg)
    sz2 = np.bincount(lab2.ravel())
    sz2[0] = 0
    body = int(np.argmax(sz2))
    ys, xs = np.where(lab2 == body)
    bx0, bx1 = int(xs.min()), int(xs.max())
    by0, by1 = int(ys.min()), int(ys.max())
    bh, bw = by1 - by0 + 1, bx1 - bx0 + 1
    side = int(round(max(bh, bw) / BODY_RATIO))
    ccx, ccy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(rgba, (int(round(side / 2.0 - ccx)), int(round(side / 2.0 - ccy))), rgba)
    if side != MAX_SIDE:
        canvas = canvas.resize((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    canvas.save(os.path.join(OUT, out_name))
    return out_name, canvas.size, int(fg.sum()), removed


os.makedirs(OUT, exist_ok=True)
for src, dst in JOBS:
    n, size, kept, removed = process(src, dst)
    msg = f"{n}  {size[0]}x{size[1]}  fg_px={kept}"
    if removed:
        msg += "  removed=" + str([(s, x, y) for s, x, y in sorted(removed, reverse=True)[:6]])
    print(msg)
print("ALL_DONE")
