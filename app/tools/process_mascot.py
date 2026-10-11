# -*- coding: utf-8 -*-
"""
缅因猫吉祥物图片处理脚本（可重复运行）。
输入：微信截图原图（含状态栏/红包角标/底部控制条）
输出：
  maine_coon.png        裁剪后的原始照片（粉色衣物 = 彩蛋主题保留）
  maine_coon_blue.png   蓝白融合版（粉色衣物色相偏移到蓝系，与主蓝 #3B82F6 协调）
  maine_coon.webp       Flutter 默认加载格式（蓝白融合版，体积更小）
  maine_coon_avatar.png 圆形羽化头像（蓝白融合版）
  maine_coon_hero.png   圆角全身像（蓝白融合版，用于启动页/对话页）
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = r"D:\xwechat_files\wxid_seynso6kc4zq22_3264\temp\RWTemp\2026-09\eb8ae8f6993d427f46d2e90ad0b92c06\08a0fed6749b6d6c0a29b43814f5df87.jpg"
OUT_ASSETS = r"C:\Users\zyx\WorkBuddy\2026-09-19-21-42-03\CppMind\app\assets\images\cat_mascot"
OUT_WEB = r"C:\Users\zyx\WorkBuddy\2026-09-19-21-42-03\CppMind\web-preview"

img = Image.open(SRC).convert("RGB")
W, H = img.size
print(f"source: {W}x{H}")

# ---------- 1) 裁出照片主体（按比例，适配不同截图尺寸） ----------
photo = img.crop((0, round(H * 0.222), W, round(H * 0.822)))
pw, ph = photo.size
print(f"photo: {pw}x{ph}")
photo.save(os.path.join(OUT_ASSETS, "maine_coon.png"))


# ---------- 2) 粉色衣物 -> 蓝白融合（选择性色相偏移） ----------
def rgb_to_hsv(arr):
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    maxc = np.max(arr, axis=-1)
    minc = np.min(arr, axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-8), 0)
    rc = np.where(delta > 0, (maxc - r) / np.maximum(delta, 1e-8), 0)
    gc = np.where(delta > 0, (maxc - g) / np.maximum(delta, 1e-8), 0)
    bc = np.where(delta > 0, (maxc - b) / np.maximum(delta, 1e-8), 0)
    h = np.where(maxc == r, bc - gc, np.where(maxc == g, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0
    h = np.where(delta == 0, 0.0, h)
    return h, s, v


def hsv_to_rgb(h, s, v):
    i = np.floor(h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


arr = np.asarray(photo).astype(np.float64) / 255.0
h, s, v = rgb_to_hsv(arr)
# 粉/品红色相带：0.82~1.0 与 0~0.06，且饱和度足够（排除银灰毛发）
pink = (s > 0.12) & ((h >= 0.82) | (h < 0.06))
h2 = np.where(pink, (h - 0.335) % 1.0, h)          # 粉(≈0.92) -> 蓝(≈0.585)
s2 = np.where(pink, np.clip(s * 0.82, 0, 1), s)    # 降一点饱和，更柔和贴近蓝白主题
blue_arr = hsv_to_rgb(h2, s2, v)
blue = Image.fromarray((np.clip(blue_arr, 0, 1) * 255).astype(np.uint8))
blue.save(os.path.join(OUT_ASSETS, "maine_coon_blue.png"))
print("blue-tint saved")


# ---------- 3) 圆形羽化头像（聚焦脸部） ----------
# 脸部中心约占照片 (0.44w, 0.34h)，方形边长取 0.66*ph
side = round(ph * 0.66)
cx, cy = round(pw * 0.44), round(ph * 0.34)
left, top = cx - side // 2, cy - side // 2
box = (max(0, left), max(0, top), min(pw, left + side), min(ph, top + side))
face = blue.crop(box).resize((512, 512), Image.LANCZOS)

mask = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(mask).ellipse((16, 16, 1008, 1008), fill=255)
mask = mask.resize((512, 512), Image.LANCZOS).filter(ImageFilter.GaussianBlur(4))
avatar = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
avatar.paste(face, (0, 0), mask)
avatar.save(os.path.join(OUT_ASSETS, "maine_coon_avatar.png"))
print("avatar saved, box =", box)


# ---------- 4) 圆角全身像（蓝白融合版） ----------
def rounded(im, radius_ratio=0.09):
    w, hgt = im.size
    r = round(min(w, hgt) * radius_ratio)
    m = Image.new("L", (w * 2, hgt * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((8, 8, w * 2 - 8, hgt * 2 - 8), radius=r * 2, fill=255)
    m = m.resize((w, hgt), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2))
    out = Image.new("RGBA", (w, hgt), (0, 0, 0, 0))
    out.paste(im, (0, 0), m)
    return out


hero = rounded(blue)
hero.save(os.path.join(OUT_ASSETS, "maine_coon_hero.png"))

# ---------- 5) WebP（Flutter 主格式，体积小） ----------
try:
    blue.save(os.path.join(OUT_ASSETS, "maine_coon.webp"), "WEBP", quality=90)
    print("webp saved")
except Exception as e:
    print("webp failed ->", e)

# ---------- 6) 同步一份到 web-preview 供演示页使用 ----------
for name in ("maine_coon.png", "maine_coon_blue.png", "maine_coon_avatar.png"):
    blue_src = {"maine_coon.png": photo}.get(name, None)
    src = {"maine_coon.png": photo, "maine_coon_blue.png": blue, "maine_coon_avatar.png": avatar}[name]
    src.save(os.path.join(OUT_WEB, name))

for f in sorted(os.listdir(OUT_ASSETS)):
    p = os.path.join(OUT_ASSETS, f)
    if os.path.isfile(p):
        print(f"{f:28s} {os.path.getsize(p) / 1024:7.1f} KB")
print("DONE")
