#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex Android 真机验包助手。

用法（在仓库任意目录，或直接用绝对路径调用）：
    python deploy/package/verify_android.py            # 等手机 -> 装包 -> 启动 -> 抓日志
    python deploy/package/verify_android.py --check    # 只做 PC 侧自检，不要求插手机
    python deploy/package/verify_android.py --ip 192.168.1.7   # 覆盖探测到的局域网 IP
    python deploy/package/verify_android.py --wait 0   # 设备已连上时不再等待
    python deploy/package/verify_android.py --cold --wait 0  # 验「冷启动自动连上后端」的标准姿势

--cold 会先 pm clear 清掉 localStorage 再装包启动。验自动连接**必须带它**：
不清的话旧的手填地址会一直排在候选首位，测出来「连上了」也可能是假阳性。

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


def lan_ips() -> list[str]:
    """取所有「有默认网关的真实网卡」IPv4，跳过 VMware / WSL / Hyper-V 虚拟网卡。

    顺序即优先级：主网卡（默认路由那张）通常排在最前。
    prepare_app.py 复用本函数，把 PC 的多张可达地址一并注入 APK —— 主人
    从 WiFi 换到有线、或某张网卡临时掉线时不必重打包就能连上后端。
    """
    try:
        raw = subprocess.run(["ipconfig", "/all"], capture_output=True, timeout=15).stdout
        for enc in ("gbk", "utf8", "cp936"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return []
    except Exception:
        return []

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

    hits: list[str] = []
    for adapter, ip in found:
        if not any(h in adapter.lower() for h in VIRTUAL_HINTS) and ip not in hits:
            hits.append(ip)
    # 全是虚拟网卡时至少给一个，别让调用方拿到空列表（VM 里跑的场景）。
    if not hits and found:
        hits.append(found[0][1])
    return hits


def lan_ip() -> str | None:
    """兼容旧调用点：返回最优先的那张真实网卡 IPv4。"""
    return next(iter(lan_ips()), None)


def apk_baked_bases() -> list[str]:
    """从 APK 内的 libnex.so 读出打包时烤进去的后端地址。

    api_client.rs 用 option_env! 把 NEX_MOBILE_DEFAULT_BASES 编成 .rodata
    常量，所以字符串会原样躺在 .so 里。这是「APK 到底认得哪台 PC」唯一的
    自描述证据 —— 换过 WiFi 后 PC 的 IP 变了，靠这条比对就能立刻发现
    「包里还是旧地址」，而不是等手机一直重连才发现。
    """
    if not APK.is_file():
        return []
    try:
        with zipfile.ZipFile(APK) as z:
            names = [n for n in z.namelist() if n.endswith("libnex.so")]
            if not names:
                return []
            blob = z.read(names[0])
    except (zipfile.BadZipFile, OSError):
        return []
    hits: list[str] = []
    for m in re.finditer(rb"https?://[0-9A-Za-z._:-]+:8000", blob):
        s = m.group().decode("ascii", "ignore")
        if s not in hits:
            hits.append(s)
    return hits


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
    ap.add_argument("--cold", action="store_true",
                    help="安装前 pm clear，模拟无历史手填地址的真冷启动（验自动连接必带）")
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
    baked = apk_baked_bases()
    out(f"APK 内置地址: {', '.join(baked) or '未注入（旧包）'}")
    if ip and baked:
        if any(ip in b for b in baked):
            out("  与当前 PC 一致：手机冷启动应直连，无需手填")
        else:
            out("  ⚠ 与当前 PC 不一致（换过网络/IP 变了）：")
            out("    重跑 prepare_app.py + build-app-apk.cmd，或在 APP 设置页手填新地址")
    elif ip:
        out("  ⚠ 这个包没烤入默认地址：手机会退回 127.0.0.1，需手填")

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
    if args.cold:
        # 不清 localStorage 就不算冷启动：旧的手填地址会一直排在候选首位，
        # 验出来的「自动连上」是假的。这是 --cold 最关键的一步。
        out(f"  pm clear {PKG}（清掉 localStorage，模拟真冷启动）")
        out("  " + sh(adb, serial, f"pm clear {PKG}")[:120])
    p = run([adb, "-s", serial, "install", "-r", str(APK)], timeout=300)
    install_log = (p.stdout + p.stderr).decode("utf8", "replace").strip()
    out("  " + install_log.replace("\n", "\n  "))
    if p.returncode != 0 or "Success" not in install_log:
        # MuMu / 部分模拟器禁用增量安装（报 Incremental installation not
        # allowed，甚至让设备短暂 offline）。退回 push + pm install 即可。
        out("  增量安装被拒，改用 adb push + pm install -r …")
        remote = f"/data/local/tmp/{APK.name}"
        p1 = run([adb, "-s", serial, "push", str(APK), remote], timeout=300)
        if p1.returncode != 0:
            out("  push 失败：" + (p1.stdout + p1.stderr).decode("utf8", "replace")[:200])
            return 3
        p2 = sh(adb, serial, f"pm install -r {remote}", timeout=300)
        out("  " + p2[:200])
        sh(adb, serial, f"rm {remote}")
        if "Success" not in p2:
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

    out("\n=== 冷启动自动连接判据 ===")
    probe_lines = [l for l in log.splitlines() if "[api_probe]" in l]
    for line in probe_lines[-3:]:
        out("  " + line[:220])
    expected = f"http://{ip}:{PORT}"
    ok = any("reachable=true" in l and expected in l for l in probe_lines)
    out(f"  期望: {expected} 且 reachable=true")
    out(f"  结果: {'PASS —— 手机自己连上了 PC 后端' if ok else 'FAIL —— 见下方排查提示'}")
    if not ok:
        out("  排查: ① 后端是否 --host 0.0.0.0；② 是否残留 adb reverse tcp:8000；"
            "③ APK 内置地址是否与当前 PC 一致（见上面自检）")

    out(f"""
=== 真题模式人工验收清单（重点）===
  1. 冷启动应**直接连上**：APK 里已烤入打包时探测到的 PC 地址
     http://{ip}:{PORT}，无需手填、不该出现反复重试的红条。
     若仍显示「连不上内容服务」：
       a. 确认 PC 后端已用 --host 0.0.0.0 --port 8000 启动（上面 deep_health 要 OK）；
       b. 换过 WiFi / PC 改过 IP → 设置页填 http://{ip}:{PORT} 可立即恢复，
          或重跑 prepare_app.py + build-app-apk.cmd 把新 IP 烤进包里。
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
