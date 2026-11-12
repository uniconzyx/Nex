#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex Android 真机验包助手。

用法（在仓库任意目录，或直接用绝对路径调用）：
    python deploy/package/verify_android.py            # 等手机 -> 装包 -> 启动 -> 抓日志
    python deploy/package/verify_android.py --check    # 只做 PC 侧自检，不要求插手机
    python deploy/package/verify_android.py --ip 192.168.1.7   # 覆盖探测到的局域网 IP
    python deploy/package/verify_android.py --wait 0   # 设备已连上时不再等待

前置：
    1. PC 上后端已用 `--host 0.0.0.0 --port 8000` 启动（health?deep=true 全绿）；
    2. 手机与 PC 在同一局域网（同一 WiFi，且网络无 AP 隔离）；
    3. 手机开 USB 调试并授权本机；APK 只带 arm64-v8a so，需 64 位 ARM、Android 8.0+。

脚本不修改 APK、不改动仓库，只做安装/启动/日志采集。真题模式的 UI 验收
清单会在末尾打印，需要人工在手机上走一遍。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
APK = ROOT / "release" / "nex-shell" / "Nex.apk"
PKG = "com.nex.app"
ACTIVITY = "com.nex.app/.MainActivity"
PORT = 8000

# 虚拟网卡不算「手机能连上」的地址；优先真实 WLAN / 以太网。
VIRTUAL_HINTS = ("vmware", "vethernet", "wsl", "virtualbox", "loopback", "docker", "hyper-v")


def run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def out(text: str = "") -> None:
    print(text, flush=True)


def find_adb() -> str:
    candidates = [
        pathlib.Path("D:/Sdk/platform-tools/adb.exe"),
        pathlib.Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe",
    ]
    import os
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(key):
            candidates.append(pathlib.Path(os.environ[key]) / "platform-tools/adb.exe")
    for p in candidates:
        if p.is_file():
            return str(p)
    return "adb"  # 交给 PATH


def lan_ip() -> str | None:
    """取「有默认网关的真实网卡」IPv4，跳过 VMware / WSL / Hyper-V 虚拟网卡。"""
    try:
        raw = subprocess.run(["ipconfig", "/all"], capture_output=True, timeout=15).stdout
        for enc in ("gbk", "utf8", "cp936"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return None
    except Exception:
        return None

    adapter = ""
    ip = None
    gateway = False
    found = []
    for line in text.splitlines():
        if line.strip() and not line.startswith(" ") and ("适配器" in line or "adapter" in line.lower()):
            if ip and gateway:
                found.append((adapter, ip))
            adapter = line.strip().rstrip(":：")
            ip, gateway = None, False
            continue
        s = line.strip()
        if "IPv4" in s:
            m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", s)
            if m:
                ip = m.group(1)
        if ("默认网关" in s or "Default Gateway" in s) and re.search(r"\d+\.\d+\.\d+\.\d+", s):
            gateway = True
    if ip and gateway:
        found.append((adapter, ip))

    for adapter, ip in found:
        if not any(h in adapter.lower() for h in VIRTUAL_HINTS):
            return ip
    return found[0][1] if found else None


def backend_ok(ip: str) -> bool:
    """PC 侧确认 0.0.0.0 绑定与数据库链路。"""
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(f"http://{ip}:{PORT}/api/v1/system/health?deep=true", timeout=8) as r:
            import json
            d = json.loads(r.read())["data"]
            return bool(d["database"]["ok"]) and all(
                d["features"][k] for k in ("exam", "content", "exercises", "progress")
            )
    except Exception:
        return False


def devices(adb: str) -> list[tuple[str, str]]:
    p = run([adb, "devices"], timeout=15)
    text = p.stdout.decode("utf8", "replace")
    result = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            result.append((parts[0], parts[1]))
    return result


def sh(adb: str, serial: str, cmd: str, timeout: int = 20) -> str:
    p = run([adb, "-s", serial, "shell", cmd], timeout=timeout)
    return p.stdout.decode("utf8", "replace").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只自检 PC 侧条件，不等设备")
    ap.add_argument("--ip", help="覆盖探测到的局域网 IP")
    ap.add_argument("--wait", type=int, default=90, help="等设备秒数（默认 90）")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    out("=== Nex 真机验包 ===")
    adb = find_adb()
    ip = args.ip or lan_ip()
    out(f"adb      : {adb}")
    out(f"APK      : {APK}  ({APK.stat().st_size / 2**20:.2f} MiB)" if APK.is_file() else f"APK      : 缺失 {APK}")
    out(f"局域网 IP: {ip or '未探测到'}")
    out(f"后端      : http://{ip}:{PORT}  deep_health={'OK' if ip and backend_ok(ip) else 'FAIL'}")
    if not APK.is_file():
        out("APK 不存在，先跑 build-app-apk.cmd")
        return 1
    if not ip or not backend_ok(ip):
        out("后端未就绪：请确认 `--host 0.0.0.0 --port 8000` 且 health?deep=true 全绿")
        return 1

    with zipfile.ZipFile(APK) as z:
        abis = sorted({n.split("/")[1] for n in z.namelist() if n.startswith("lib/")})
    out(f"APK ABI  : {', '.join(abis) or '无'}  （设备须为 arm64-v8a）")

    if args.check:
        out("\nPC 侧自检完成；--check 不检查设备。")
        return 0

    deadline = time.time() + args.wait
    serial = None
    while True:
        ds = devices(adb)
        good = [s for s, st in ds if st == "device"]
        if good:
            serial = good[0]
            break
        if time.time() >= deadline:
            out("\n未检测到已授权设备。当前状态：")
            for s, st in ds:
                out(f"  {s}  {st}")
            out("\n请插上手机 → 开启 USB 调试 → 在弹出的授权框点「允许」；"
                "若显示 unauthorized，重插数据线后重新授权。")
            out("（APK 仅 arm64-v8a，x86_64 模拟器装不上，必须用真机。）")
            return 2
        out("  等待设备接入…（Ctrl+C 取消）")
        time.sleep(3)

    out(f"\n=== 设备 {serial} ===")
    for key, label in [
        ("ro.product.model", "型号"),
        ("ro.build.version.release", "Android"),
        ("ro.product.cpu.abilist", "ABI"),
    ]:
        out(f"  {label:9s}: {sh(adb, serial, 'getprop ' + key)}")

    out("\n=== 安装 APK ===")
    p = run([adb, "-s", serial, "install", "-r", str(APK)], timeout=300)
    install_log = (p.stdout + p.stderr).decode("utf8", "replace").strip()
    out("  " + install_log.replace("\n", "\n  "))
    if p.returncode != 0 or "Success" not in install_log:
        out("安装失败，先排查：签名冲突（卸载旧包）、存储空间、Android 版本 < 8.0")
        return 3

    out("\n=== 设备 → 后端连通性 ===")
    probe = sh(adb, serial, f"toybox wget -q -O - http://{ip}:{PORT}/api/v1/system/health")
    out("  " + (probe[:160] if probe else "设备侧 wget 不可用（不影响，请在 APP 内确认）"))

    out("\n=== 启动应用 ===")
    out("  " + sh(adb, serial, f"am start -n {ACTIVITY}")[:200])
    sh(adb, serial, "logcat -c")
    out("  已清空 logcat，等待 8 秒收集启动日志…")
    time.sleep(8)
    log = sh(adb, serial, "logcat -d -v time", timeout=30)
    keys = ("nex", "tauri", "webview", "chromium", "net::err", "cleartext", "private-network", "fatal", "exception")
    hits = [l for l in log.splitlines() if any(k in l.lower() for k in keys)]
    out(f"\n=== 关键日志（{len(hits)} 行，最多显示 25 行）===")
    for line in hits[-25:]:
        out("  " + line[:180])
    if not hits:
        out("  无异常关键字（不代表功能正常，仍需按下面清单走 UI）")

    out(f"""
=== 真题模式人工验收清单（重点）===
  1. 首次进入若提示「连不上内容服务」：设置页 → 内容服务 → 地址填
     http://{ip}:{PORT}
     保存后会自动重连并记住；只要填一次，之后冷启动直连。
  2. 首页 → 考研 → 套卷（或 408 → 套卷）→ 应看到 18 套 408 卷、
     数学/英语/政治/离散/算法各 8 套，共 74 套。
  3. 打开「408 计算机网络 · 专项模拟卷（1）」→ 2 个分区、题目列表齐全，
     解析默认折叠（不剧透答案），点开才展示四层讲解。
  4. 切到「训练」视图 → 题库返回题目 → 作答 → 提交判分，能看到判定结果。
  5. 断网/换 WiFi 后重进：应提示离线但已缓存内容不白屏。

  验收时如出现白屏/报错，把手机上此刻的 logcat 发回即可定位：
     {adb} -s {serial} logcat -d -v time > nex-device.log
""")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        out("\n已取消")
        raise SystemExit(130)
