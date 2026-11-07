#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证两个原生包里装的确实是「当前设计」的应用图标（防回归）。

起因（2026-11-07）：换了 icon.ico 并重编 EXE，ExtractIconExW 取出来却还是
蓝底白方块占位图——build.rs 没声明 icons/icon.ico 依赖，Cargo 复用了旧
libresource.a。APK 一侧则曾把 0 字节的 libnex.so 打进去差点白屏。
所以「设计稿对了」不等于「包里对了」，必须验产物。

用法：python deploy/package/verify_icons.py
依赖：Pillow；EXE 校验仅 Windows（ctypes 调 Win32，不用 .NET 反射）。
"""
from __future__ import annotations

import ctypes
import pathlib
import sys
import zipfile
from ctypes import wintypes

from PIL import Image, ImageChops, ImageStat

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXE = ROOT / "release/nex-shell/Nex-Desktop-1.0.exe"
APK = ROOT / "release/nex-shell/Nex-Mobile-1.0-arm64.apk"
ICO = ROOT / "src-tauri/icons/icon.ico"
LAUNCHER_ICO = ROOT / "deploy/launcher/nex.ico"
ANDROID_SRC = ROOT / "deploy/package/icons/android/mipmap-xxhdpi/ic_launcher.png"
OLD_ICON_PATH = ROOT / "scratch/icons-backup-20261107/tauri-icons/icon.ico"

results = []


def chk(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail if detail else ""))


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG), ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD), ("bmBitsPixel", wintypes.WORD),
        ("bmBits", wintypes.LPVOID),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def exe_icon_image(exe: pathlib.Path) -> Image.Image | None:
    """从 EXE 的 RT_ICON 资源取 32x32 位图（不经系统图标缓存）。"""
    if sys.platform != "win32":
        return None
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.ExtractIconExW.argtypes = [
        wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.HICON),
        ctypes.POINTER(wintypes.HICON), wintypes.UINT]
    shell32.ExtractIconExW.restype = wintypes.UINT
    user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
    user32.GetIconInfo.restype = wintypes.BOOL
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    gdi32.GetObjectW.argtypes = [wintypes.HGDIOBJ, ctypes.c_int, wintypes.LPVOID]
    gdi32.GetObjectW.restype = ctypes.c_int
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        wintypes.LPVOID, ctypes.POINTER(BITMAPINFOHEADER), wintypes.UINT]
    gdi32.GetDIBits.restype = ctypes.c_int

    large, small = wintypes.HICON(), wintypes.HICON()
    n = shell32.ExtractIconExW(str(exe), 0, ctypes.byref(large),
                               ctypes.byref(small), 1)
    if not n or not large.value:
        return None
    ii = ICONINFO()
    if not user32.GetIconInfo(large, ctypes.byref(ii)):
        return None
    hbm = ii.hbmColor or ii.hbmMask
    bm = BITMAP()
    gdi32.GetObjectW(hbm, ctypes.sizeof(BITMAP), ctypes.byref(bm))
    w, h = bm.bmWidth, abs(bm.bmHeight)
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth, bi.biHeight = w, -h
    bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(user32.GetDC(0), hbm, 0, h, buf, ctypes.byref(bi), 0)
    im = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1).copy()
    user32.DestroyIcon(large)
    user32.DestroyIcon(small)
    return im


def ico_frame(path: pathlib.Path, size: int) -> Image.Image:
    im = Image.open(path)
    return im.ico.getimage((size, size)).convert("RGBA")


def main() -> None:
    for p in (EXE, APK, ICO, LAUNCHER_ICO, ANDROID_SRC):
        chk(f"存在 {p.relative_to(ROOT)}", p.is_file(),
            f"{p.stat().st_size} bytes" if p.is_file() else "MISSING")
    if not all(results[:5]):
        raise SystemExit("缺少必要文件")

    # 1) 三处 Windows 图标同源
    chk("EXE 图标与 launcher 图标同源",
        ICO.read_bytes() == LAUNCHER_ICO.read_bytes())

    # 2) EXE 里装的确实是新设计，不是旧占位方块
    icon = exe_icon_image(EXE)
    if icon is None:
        chk("EXE 图标可提取", False, "非 Windows 或资源缺失")
    else:
        colors = len(icon.getcolors(maxcolors=1 << 20) or [])
        chk("EXE 图标不是旧的纯色占位图", colors > 40, f"{colors} 种颜色")
        want = ico_frame(ICO, 32).resize(icon.size)
        diff = ImageStat.Stat(ImageChops.difference(icon.convert("RGB"),
                                                    want.convert("RGB"))).mean
        avg = sum(diff) / len(diff)
        chk("EXE 图标与当前设计稿一致", avg < 45, f"平均色差 {avg:.1f}/255")

    # 3) APK 里存在与 xxhdpi 设计稿逐像素一致的启动图标
    src = Image.open(ANDROID_SRC).convert("RGBA")
    hit = False
    with zipfile.ZipFile(APK) as z:
        for name in z.namelist():
            if not name.startswith("res/") or not name.endswith(".png"):
                continue
            try:
                cand = Image.open(__import__("io").BytesIO(z.read(name))).convert("RGBA")
            except Exception:
                continue
            if cand.size == src.size and ImageChops.difference(cand, src).getbbox() is None:
                hit = True
                chk("APK 启动图标与设计稿逐像素一致", True, name)
                break
    if not hit:
        chk("APK 启动图标与设计稿逐像素一致", False, "未找到匹配资源")

    # 4) APK 内原生库不是 0 字节（曾因符号链接打出白屏包）
    with zipfile.ZipFile(APK) as z:
        sos = [i for i in z.infolist() if i.filename.endswith("libnex.so")]
    chk("APK 内含完整 arm64 原生库",
        bool(sos) and all(i.file_size > 15 * 1024 * 1024 for i in sos),
        ", ".join(f"{i.file_size / 1024 / 1024:.1f}MB" for i in sos) or "NONE")

    passed = sum(1 for x in results if x)
    print(f"\nRESULT {passed}/{len(results)}")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
