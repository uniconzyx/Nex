#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex 原生封装图标设计器（幂等 / 可复现）。

设计母题：把「凯喵」藏进「冰晶六边形」——六边形是 Nex 的知识晶体，
中间是项目自有的 Q 版凯喵头像，外圈一道掌握度圆弧呼应首页 conic 进度环。
色值全部取自唯一色源 frontend/src/styles/liquidglass.css 的 .km-app{}，
不引入新的品牌色。

产出：
  src-tauri/icons/icon.png / icon.ico          Windows EXE 图标
  deploy/launcher/nex.ico                     launcher 图标（与封装统一）
  web-preview/favicon-64.png                  浏览器 / 内嵌页标签
  src-tauri/gen/android/app/src/main/res/mipmap-*/  Android 五档图标
  res/drawable*/ic_launcher_*.xml             替换 Android 默认机器人矢量
  scratch/icon-preview.png                     多尺寸预览（不入库）

用法：python deploy/package/design_icons.py
"""
from __future__ import annotations

import math
import pathlib
from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[2]
SS = 2048  # 超采样边长，最后 LANCZOS 缩到目标尺寸，保证小尺寸抗锯齿

# ---- 唯一色源：frontend/src/styles/liquidglass.css .km-app{} ----
ENV_1 = (0xEB, 0xF4, 0xFA)    # --km-env-1
ENV_2 = (0xF6, 0xF9, 0xFC)    # --km-env-2
PRIMARY = (0x5D, 0xB4, 0xE5)  # --km-primary
PRIMARY_DEEP = (0x4A, 0x90, 0xE2)
PRIMARY_LIFT = (0x6E, 0xC6, 0xFF)
SECONDARY = (0xA2, 0xD2, 0xFF)
GLOW_A = (0xC5, 0xE4, 0xFF)
GLOW_B = (0xE3, 0xDE, 0xFF)
WHITE = (0xFF, 0xFF, 0xFF)

CAT_SRC = ROOT / "web-preview/assets/kaimao/mood-happy.png"
RES = ROOT / "src-tauri/gen/android/app/src/main/res"
MIPMAPS = {
    "mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192,
}
FOREGROUNDS = {
    "mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432,
}


def lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def ground_color(t: float) -> tuple:
    """纵向三段渐变：环境冰蓝白 -> 奶白 -> 品牌冰蓝。"""
    if t < 0.42:
        return lerp(ENV_1, ENV_2, t / 0.42)
    # 末端用深一档的品牌冰蓝：纯 --km-primary 在浅色桌面上会让小图标"消失"
    return lerp(ENV_2, PRIMARY_DEEP, (t - 0.42) / 0.58)


def hex_points(cx: float, cy: float, r: float, rot: float = -90.0):
    return [
        (cx + r * math.cos(math.radians(rot + 60 * i)),
         cy + r * math.sin(math.radians(rot + 60 * i)))
        for i in range(6)
    ]


def rounded_mask(round_icon: bool) -> Image.Image:
    m = Image.new("L", (SS, SS), 0)
    d = ImageDraw.Draw(m)
    if round_icon:
        d.ellipse((0, 0, SS - 1, SS - 1), fill=255)
    else:
        d.rounded_rectangle((0, 0, SS - 1, SS - 1), radius=int(SS * 0.225), fill=255)
    return m


def make_ground() -> Image.Image:
    """氛围渐变 + 两枚柔光光斑（呼应 APK 首页的底层氛围）。"""
    bg = Image.new("RGB", (SS, SS))
    d = ImageDraw.Draw(bg)
    for y in range(SS):
        d.line((0, y, SS, y), fill=ground_color(y / (SS - 1)))
    glow = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((int(-SS * 0.18), int(-SS * 0.26), int(SS * 0.52), int(SS * 0.28)),
              fill=GLOW_A + (150,))
    g.ellipse((int(SS * 0.55), int(SS * 0.62), int(SS * 1.22), int(SS * 1.28)),
              fill=GLOW_B + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(SS // 14))
    return Image.alpha_composite(bg.convert("RGBA"), glow)


def cat_avatar(diameter: int) -> Image.Image:
    """从项目自有凯喵立绘裁出头部，做圆形遮罩与白色描边环。"""
    src = Image.open(CAT_SRC).convert("RGBA")
    # 720x720 立绘：下移裁切框，让完整脸（鼻/嘴/腮红）进圆，而不是只有额头
    head = src.crop((110, 62, 610, 562)).resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter - 1, diameter - 1), fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(head, (0, 0), mask)
    ring = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    w = max(2, diameter // 34)
    ImageDraw.Draw(ring).ellipse(
        (w // 2, w // 2, diameter - 1 - w // 2, diameter - 1 - w // 2),
        outline=WHITE + (235,), width=w)
    return Image.alpha_composite(out, ring)


def render(include_ground: bool = True, round_icon: bool = False) -> Image.Image:
    canvas = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    if include_ground:
        ground = make_ground()
        ground.putalpha(rounded_mask(round_icon))
        canvas = Image.alpha_composite(canvas, ground)
        # 一圈极细的冰蓝轮廓：浅色桌面上 16px 仍能看出图标边界
        edge = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
        ed = ImageDraw.Draw(edge)
        w = int(SS * 0.009)
        if round_icon:
            ed.ellipse((w, w, SS - 1 - w, SS - 1 - w),
                       outline=SECONDARY + (150,), width=w)
        else:
            ed.rounded_rectangle((w, w, SS - 1 - w, SS - 1 - w),
                                 radius=int(SS * 0.225),
                                 outline=SECONDARY + (150,), width=w)
        canvas = Image.alpha_composite(canvas, edge)

    # 主体比首版放大约 9%：16/32px 下六边形与凯喵脸才有辨识度
    cx, cy = SS / 2, SS * 0.48
    R = SS * 0.365
    pts = hex_points(cx, cy, R)

    # 冰晶柔光阴影（只衬在真正浮起的玻璃体下方，不做常驻发光）
    shade = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    ImageDraw.Draw(shade).polygon(
        [(x, y + SS * 0.018) for x, y in pts], fill=(90, 140, 190, 70))
    shade = shade.filter(ImageFilter.GaussianBlur(SS // 90))
    canvas = Image.alpha_composite(canvas, shade)

    # 六边形玻璃体：半透白填充 + 顶部高光 + 冰蓝描边
    glass = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glass)
    gd.polygon(pts, fill=WHITE + (140,))
    gd.line(pts + [pts[0]], fill=WHITE + (225,), width=int(SS * 0.013), joint="curve")
    inner = hex_points(cx, cy, R * 0.87)
    gd.line(inner + [inner[0]], fill=SECONDARY + (105,),
            width=int(SS * 0.006), joint="curve")
    gd.arc((cx - R * 0.72, cy - R * 0.72, cx + R * 0.72, cy + R * 0.72),
           start=196, end=286, fill=WHITE + (215,), width=int(SS * 0.010))
    canvas = Image.alpha_composite(canvas, glass)

    # 凯喵头像（品牌真实资产，非占位图）
    D = int(SS * 0.49)
    # 淡冰蓝衬底：把浅金发 / 白脸从白色六边形里"托"出来
    plate = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    pad = int(SS * 0.012)
    oy = -SS * 0.012
    pd.ellipse((int(cx - D / 2 - pad), int(cy - D / 2 - pad + oy),
                int(cx + D / 2 + pad), int(cy + D / 2 + pad + oy)),
               fill=(0xE2, 0xEE, 0xF8, 165))
    canvas = Image.alpha_composite(canvas, plate)
    avatar = cat_avatar(D)
    canvas.alpha_composite(avatar, (int(cx - D / 2), int(cy - D / 2 - SS * 0.012)))

    # 掌握度圆弧：呼应首页 conic 圆环，端点一颗冰蓝珠
    ring = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rr = SS * 0.425
    box = (cx - rr, cy - rr, cx + rr, cy + rr)
    rd.arc(box, start=-90, end=186, fill=PRIMARY_LIFT + (235,),
           width=int(SS * 0.019))
    ang = math.radians(186)
    ex, ey = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
    rd.ellipse((ex - SS * 0.017, ey - SS * 0.017,
                ex + SS * 0.017, ey + SS * 0.017), fill=WHITE + (245,))
    canvas = Image.alpha_composite(canvas, ring)

    if not include_ground:
        # adaptive foreground：透明底，主体收进安全区
        fg = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
        small = canvas.resize((int(SS * 0.62), int(SS * 0.62)), Image.LANCZOS)
        fg.alpha_composite(small, ((SS - small.width) // 2, (SS - small.height) // 2))
        return fg
    return canvas


def write_png(master: Image.Image, path: pathlib.Path, size: int) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    master.resize((size, size), Image.LANCZOS).save(path, format="PNG", optimize=True)
    return path.stat().st_size


def write_ico(master: Image.Image, path: pathlib.Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = master.resize((256, 256), Image.LANCZOS)
    base.save(path, format="ICO",
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path.stat().st_size


def write_vectors() -> None:
    bg = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#E2EEF8" android:pathData="M0,0h108v108h-108z" />
    <path android:fillColor="#5DB4E5" android:pathData="M0,54h108v54h-108z" />
</vector>
"""
    fg = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FFFFFF"
        android:pathData="M54,25 L79,39 L79,69 L54,83 L29,69 L29,39 Z" />
    <path android:fillColor="#5DB4E5"
        android:pathData="M54,34 L71,44 L71,64 L54,74 L37,64 L37,44 Z" />
    <path android:fillColor="#EBF4FA"
        android:pathData="M54,42 L64,48 L64,60 L54,66 L44,60 L44,48 Z" />
</vector>
"""
    (RES / "drawable/ic_launcher_background.xml").write_text(bg, encoding="utf-8")
    (RES / "drawable-v24/ic_launcher_foreground.xml").write_text(fg, encoding="utf-8")


def preview(master: Image.Image) -> None:
    """多尺寸 × 亮/暗底拼版，供人眼复核（不入库）。"""
    sizes = [16, 32, 48, 64, 128, 256]
    pad, cell = 24, 300
    W = pad + cell * len(sizes)
    out = Image.new("RGB", (W, 2 * (cell + 50)), (246, 249, 252))
    d = ImageDraw.Draw(out)
    for row, bgc in enumerate([(246, 249, 252), (27, 42, 60)]):
        top = row * (cell + 50)
        d.rectangle((0, top, W, top + cell + 50), fill=bgc)
        for i, s in enumerate(sizes):
            im = master.resize((s, s), Image.LANCZOS).convert("RGBA")
            x = pad + i * cell + (cell - s) // 2
            y = top + 30 + (cell - s) // 2
            tile = Image.new("RGBA", (s, s), bgc + (255,))
            out.paste(Image.alpha_composite(tile, im).convert("RGB"), (x, y))
            d.text((pad + i * cell + 6, top + 8), f"{s}px",
                   fill=(90, 110, 130) if row == 0 else (200, 220, 240))
    p = ROOT / "scratch/icon-preview.png"
    p.parent.mkdir(exist_ok=True)
    out.save(p)
    print(f"  preview -> {p}")


def main() -> None:
    if not CAT_SRC.is_file():
        raise SystemExit(f"missing brand asset: {CAT_SRC}")
    print("[design-icons] rendering master ...", flush=True)
    master = render()
    round_master = render(round_icon=True)
    fg_master = render(include_ground=False)

    print("[design-icons] windows / launcher / favicon")
    print("  icon.png      ", write_png(master, ROOT / "src-tauri/icons/icon.png", 1024), "bytes")
    for p in [ROOT / "src-tauri/icons/icon.ico", ROOT / "deploy/launcher/nex.ico"]:
        print(f"  {p.name:14s}", write_ico(master, p), "bytes")
    print("  favicon-64.png", write_png(master, ROOT / "web-preview/favicon-64.png", 64), "bytes")

    print("[design-icons] android mipmaps")
    for dpi, size in MIPMAPS.items():
        d = RES / f"mipmap-{dpi}"
        write_png(master, d / "ic_launcher.png", size)
        write_png(round_master, d / "ic_launcher_round.png", size)
        write_png(fg_master, d / "ic_launcher_foreground.png", FOREGROUNDS[dpi])
        print(f"  {dpi:9s} {size:3d}px launcher / round / foreground {FOREGROUNDS[dpi]}px")

    write_vectors()
    print("[design-icons] replaced default Android robot vectors")
    # gen/android 整目录被 .gitignore 忽略：镜像一份到可入库目录，
    # 否则别人 clone 后重编 APK 又会变回 Tauri 默认图标。
    import shutil
    mirror = ROOT / "deploy/package/icons/android"
    for name in ["mipmap-" + k for k in MIPMAPS] + ["drawable", "drawable-v24"]:
        src_dir, dst_dir = RES / name, mirror / name
        if not src_dir.is_dir():
            continue
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
    print("[design-icons] mirrored Android icons ->", mirror)
    preview(master)
    print("[design-icons] done")


if __name__ == "__main__":
    main()
