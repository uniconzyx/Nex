# -*- coding: utf-8 -*-
"""CI 用：flutter create 生成 android 平台后，注入 Nex 图标与应用名。

用法: python deploy/ci/inject_android_icons.py <icon.png> <app_res_dir>
  <icon.png>     方形源图（建议 1024x1024）
  <app_res_dir>  app/android/app/src/main/res

动作:
  1. 各密度 mipmap-*/ 写入 ic_launcher.png 与 ic_launcher_round.png
  2. AndroidManifest.xml 的 android:label 改为 Nex
"""
import os
import re
import sys

from PIL import Image, ImageDraw

DENSITIES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def rounded(im, size):
    """圆形裁剪（用于 ic_launcher_round）。"""
    im = im.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    icon_path, res_dir = sys.argv[1], sys.argv[2]
    src = Image.open(icon_path).convert("RGBA")

    for d, size in DENSITIES.items():
        ddir = os.path.join(res_dir, d)
        os.makedirs(ddir, exist_ok=True)
        sq = src.resize((size, size), Image.LANCZOS).convert("RGBA")
        sq.save(os.path.join(ddir, "ic_launcher.png"))
        rounded(src, size).save(os.path.join(ddir, "ic_launcher_round.png"))
        print(f"[OK] {d}: {size}px")

    # 改应用显示名为 Nex
    mf = os.path.join(res_dir, "AndroidManifest.xml")
    if os.path.exists(mf):
        with open(mf, "r", encoding="utf-8") as f:
            xml = f.read()
        xml2, n = re.subn(r'android:label="[^"]*"', 'android:label="Nex"', xml)
        if n:
            with open(mf, "w", encoding="utf-8") as f:
                f.write(xml2)
            print(f"[OK] AndroidManifest label -> Nex ({n})")
        else:
            print("[WARN] android:label not found")
    print("DONE")


if __name__ == "__main__":
    main()
