#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 用：图标与封装资产「源级」防回归（不依赖 EXE / APK 二进制）。

为什么单独一层：EXE / APK 是 .gitignore 的本机产物，CI 上根本不存在，
`verify_icons.py` 的 10 项断言在那里无法执行。能进版本库的是这些：

  - 图标源文件（ico / png / favicon / Android 五档 mipmap + 矢量 XML）
  - 生成器 design_icons.py
  - build.rs 的 cargo:rerun-if-changed 声明
  - prepare.py 里的一键重编模板

本脚本校验它们，判据四条：

  1. **生成器幂等**：重跑 design_icons.py，把重生成结果与库内资产做
     **像素级**比对（不是字节比对 —— Pillow / zlib 版本差异会改变 PNG
     编码字节，但像素不该变）。比对完把库内资产原样恢复，工作区不留 diff。
  2. **三处 Windows 图标同源**：icon.ico 与 launcher/nex.ico 逐字节相同。
  3. **不是旧占位图**：ico 取帧后颜色数 > 40（旧图是 389B 蓝底白方块）。
  4. **构建链没退化**：build.rs 仍声明 icons/icon.ico 依赖（否则 Cargo
     复用旧 libresource.a，换了图标 EXE 里还是旧图）；prepare.py 模板
     仍带 `--target x86_64-pc-windows-gnu` 与直连 apksigner.jar 的签名。

用法：python deploy/package/verify_icon_sources.py
依赖：Pillow（与 design_icons.py 相同）

产物（EXE 图标色差 / APK 图标逐像素 / so 非 0 字节）由本机
`verify_icons.py` 守门；CI 上若产物被作为 artifact 放进来，条件步骤会
自动改跑完整校验。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "deploy/package/design_icons.py"
ICO = ROOT / "src-tauri/icons/icon.ico"
LAUNCHER_ICO = ROOT / "deploy/launcher/nex.ico"
MIRROR = ROOT / "deploy/package/icons/android"

DPIS = ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi")
KINDS = ("ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png")
ASSETS = [
    "src-tauri/icons/icon.png",
    "src-tauri/icons/icon.ico",
    "deploy/launcher/nex.ico",
    "web-preview/favicon-64.png",
] + [f"deploy/package/icons/android/mipmap-{d}/{k}" for d in DPIS for k in KINDS] + [
    "deploy/package/icons/android/drawable/ic_launcher_background.xml",
    "deploy/package/icons/android/drawable-v24/ic_launcher_foreground.xml",
]

results: list[bool] = []


def chk(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail if detail else ""))


def frames(path: pathlib.Path) -> dict[tuple, Image.Image]:
    """把 PNG 或 ICO 统一成 {尺寸: RGBA 图}，规避编码字节差异。"""
    im = Image.open(path)
    if path.suffix.lower() == ".ico":
        return {s: im.ico.getimage(s).convert("RGBA") for s in im.ico.sizes()}
    return {im.size: im.convert("RGBA")}


def same_pixels(a: pathlib.Path, b: pathlib.Path) -> tuple[bool, str]:
    if not b.is_file():
        return False, "重生成后文件缺失"
    if b.suffix.lower() == ".xml":
        return a.read_bytes() == b.read_bytes(), "XML 字节一致" if a.read_bytes() == b.read_bytes() else "XML 内容不同"
    try:
        fa, fb = frames(a), frames(b)
    except Exception as e:                                       # noqa: BLE001
        return False, "无法解码: %s" % str(e)[:100]
    if set(fa) != set(fb):
        return False, "帧尺寸不同 %s vs %s" % (sorted(fa), sorted(fb))
    for size in fa:
        if ImageChops.difference(fa[size], fb[size]).getbbox() is not None:
            return False, "%s 像素不同" % (size,)
    return True, "%d 帧像素一致" % len(fa)


def main() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="nex-icon-src-"))
    backup: dict[str, pathlib.Path] = {}
    try:
        for rel in ASSETS:
            p = ROOT / rel
            if not p.is_file():
                chk("存在 " + rel, False, "MISSING")
                continue
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            backup[rel] = dst
        chk("图标源资产齐全", len(backup) == len(ASSETS),
            "%d/%d 文件" % (len(backup), len(ASSETS)))
        if len(backup) != len(ASSETS):
            raise SystemExit("缺少必要文件")

        r = subprocess.run([sys.executable, str(GENERATOR)], cwd=str(ROOT),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        chk("design_icons.py 可重跑（干净环境）", r.returncode == 0,
            (r.stderr or "")[-180:] if r.returncode else "rc=0")

        bad = []
        for rel, bak in backup.items():
            ok, detail = same_pixels(bak, ROOT / rel)
            if not ok:
                bad.append("%s (%s)" % (rel, detail))
        chk("重生成结果与库内资产像素一致", not bad,
            "; ".join(bad[:3]) if bad else "%d 个文件" % len(backup))

        # 恢复原字节：本机跑也不能留下 diff（PNG 编码字节可能不同）
        for rel, bak in backup.items():
            shutil.copy2(bak, ROOT / rel)
        chk("库内资产已恢复", True, "%d 个文件" % len(backup))

        chk("EXE/launcher 图标同源", ICO.read_bytes() == LAUNCHER_ICO.read_bytes())
        ico_frames = frames(ICO)
        big = max(ico_frames)
        colors = len(ico_frames[big].getcolors(maxcolors=1 << 20) or [])
        chk("图标不是旧单色占位图", colors > 40, "%d 种颜色 / %s" % (colors, big))

        build_rs = (ROOT / "src-tauri/build.rs").read_text(encoding="utf-8")
        chk("build.rs 声明 icons/icon.ico 依赖",
            "cargo:rerun-if-changed=icons/icon.ico" in build_rs)
        prep = (ROOT / "deploy/package/prepare.py").read_text(encoding="utf-8")
        chk("prepare.py 模板带 --target x86_64-pc-windows-gnu",
            "--target x86_64-pc-windows-gnu" in prep)
        chk("prepare.py 模板直连 apksigner.jar",
            "apksigner.jar" in prep and "java.exe" in prep)
        chk("Android 图标镜像入库", len(list(MIRROR.rglob("*.*"))) == 17,
            "%d 个文件" % len(list(MIRROR.rglob("*.*"))))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for x in results if x)
    print("\nRESULT %d/%d" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
