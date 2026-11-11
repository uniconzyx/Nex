"""生成 Android 启动图标：让手机上的显示效果与桌面 EXE 图标一致。

背景（为什么会「看起来不一样」）：
  `src-tauri/icons/icon.png` 是一张**自带圆角底衬的完整图标**，内容满幅铺到
  画布边缘。Android 侧有三种图标形态，蒙版规则各不相同：

  1. **ic_launcher.png（传统图标）**
     启动器**原样显示**，不额外套蒙版。→ 直接缩放即可，绝不能放大，否则
     源图自己的圆角边缘会被裁掉，四个角会变成直角/缺块。

  2. **ic_launcher_round.png（圆形图标）**
     有些启动器（如 Pixel Launcher「圆形图标」开关、部分国产 ROM）会优先用它。
     需要一个圆形 alpha 蒙版。这里不做 zoom：源图圆角半径较小，直接套圆会
     把四个角的底衬裁掉——这正是要的效果（圆形图标本来就该是圆的）。

  3. **ic_launcher_foreground.png（自适应图标前景，API 26+）**
     仅当存在 `mipmap-anydpi-v26/ic_launcher.xml` 时才会被使用。
     前景是 108dp 画布，系统按不同形状（圆/方/水滴/松鼠）裁切，
     只有中间 72dp 是「安全区」。→ 内容必须缩到 72/108 居中，
     这样任何蒙版形状下都完整。

  当前工程**没有** anydpi-v26 的 XML（见 README 说明），所以实际生效的是
  ic_launcher.png / ic_launcher_round.png。foreground 仍一并生成，
  便于以后启用自适应图标时直接可用。

用法：
    python deploy/package/gen_android_icons.py            # 写到 deploy/package/icons/android
    python deploy/package/gen_android_icons.py --verify   # 只做像素比对，不写文件
"""

import os
import sys

from PIL import Image

# 本脚本位于 <repo>/deploy/package/ → 仓库根要上跳两层
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src-tauri", "icons", "icon.png")
DST_BASE = os.path.join(ROOT, "deploy", "package", "icons", "android")

# 标准 launcher 尺寸（与 Android 资源目录约定一致）
LAUNCHER_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
# 自适应图标前景：108dp 基准（内容区 72dp，安全区 66dp）
FOREGROUND_SIZES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def load_square() -> Image.Image:
    """读源图并裁成正方形（若本身是正方形则原样返回）。"""
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
    return im


def make_square(src: Image.Image, size: int) -> Image.Image:
    """传统图标：原样缩放，不裁剪。

    源图已自带圆角底衬且满幅，任何 zoom-in 都会吃掉它自己的圆角边缘。
    """
    return src.resize((size, size), Image.LANCZOS)


def make_round(src: Image.Image, size: int) -> Image.Image:
    """圆形图标：方形图 + 圆形 alpha 蒙版（4x 超采样后缩回，边缘更干净）。"""
    from PIL import ImageDraw

    square = make_square(src, size)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(square, (0, 0), mask)
    return out


def make_foreground(src: Image.Image, size: int) -> Image.Image:
    """自适应图标前景：内容缩到 72/108 放在透明画布中央。

    108dp 画布会被系统按各形状蒙版裁切，只有中间 72dp 保证可见，
    所以内容必须先缩小到安全区内，否则圆/水滴蒙版会切掉边角。
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(round(size * 72 / 108))
    content = src.resize((inner, inner), Image.LANCZOS)
    off = (size - inner) // 2
    canvas.paste(content, (off, off), content)
    return canvas


def verify() -> int:
    """把已生成的 ic_launcher 与「源图直接缩放」做像素比对。

    平均通道差 < 1.0 即视为同源（LANCZOS 重采样带来的抖动在此量级）。
    """
    from PIL import ImageChops, ImageStat

    src = load_square()
    bad = 0
    for folder, size in LAUNCHER_SIZES.items():
        path = os.path.join(DST_BASE, folder, "ic_launcher.png")
        if not os.path.exists(path):
            print(f"  [MISS] {folder}/ic_launcher.png")
            bad += 1
            continue
        got = Image.open(path).convert("RGBA")
        want = make_square(src, size)
        # 只比 RGB（alpha 在圆角外缘天然有微小差异）
        a = got.convert("RGB")
        b = want.convert("RGB")
        stat = ImageStat.Stat(ImageChops.difference(a, b))
        mean = sum(stat.mean) / 3.0
        flag = "OK  " if mean < 1.0 else "DIFF"
        if mean >= 1.0:
            bad += 1
        print(f"  [{flag}] {folder}: {got.size} mean_diff={mean:.3f}/255")
    print(f"[verify] {'全部同源' if bad == 0 else f'{bad} 个不一致'}")
    return 0 if bad == 0 else 1


def main() -> int:
    if not os.path.exists(SRC):
        print(f"[icons] 源图不存在: {SRC}")
        return 1

    if "--verify" in sys.argv:
        return verify()

    src = load_square()
    print(f"[icons] 源图 {src.size} → {DST_BASE}")

    for folder, size in LAUNCHER_SIZES.items():
        d = os.path.join(DST_BASE, folder)
        os.makedirs(d, exist_ok=True)

        make_square(src, size).save(os.path.join(d, "ic_launcher.png"), optimize=True)
        make_round(src, size).save(
            os.path.join(d, "ic_launcher_round.png"), optimize=True
        )
        make_foreground(src, FOREGROUND_SIZES[folder]).save(
            os.path.join(d, "ic_launcher_foreground.png"), optimize=True
        )
        print(
            f"  {folder}: launcher={size} round={size} "
            f"foreground={FOREGROUND_SIZES[folder]}"
        )

    print("[icons] done")
    return verify()


if __name__ == "__main__":
    sys.exit(main())
