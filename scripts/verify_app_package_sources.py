#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真应用封装「生成器 -> 入库产物」幂等门禁 + 判题运行时源级防回归。

纯标准库，CI Linux 可直接跑。分两层：

  A. 幂等：只重放 prepare_app.py 里**不依赖 vite** 的部分（两份增量配置 +
     两个构建脚本），与库内文件做换行归一后的字节比对，然后恢复原字节。
     防的是「手改产物 .cmd 却没改生成器模板，下次 prepare 被静默覆盖」。
  B. 判题运行时：Pyodide 资源必须本地化且随包入库、桌面 go-judge 必须随
     EXE 落盘。这两件事在浏览器 dev 模式完全看不出来，但封装后一个会让
     移动端判题 100% 失败，另一个会让桌面判题静默降级成 mock 直跑。

比对用 norm() 归一 CRLF/LF：.gitattributes 是 `* text=auto eol=lf`，
Windows 工作区与 CI checkout 的换行本就不同，归一后相同即视为幂等。

用法：python scripts/verify_app_package_sources.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "deploy" / "package" / "prepare_app.py"
TARGETS = [
    ROOT / "src-tauri" / "tauri.app.desktop.conf.json",
    ROOT / "src-tauri" / "tauri.app.mobile.conf.json",
    ROOT / "deploy" / "package" / "build-app-exe.cmd",
    ROOT / "deploy" / "package" / "build-app-apk.cmd",
]
PYODIDE_REQUIRED = (
    "pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm",
    "python_stdlib.zip", "pyodide-lock.json",
)


def norm(data: bytes) -> bytes:
    """GBK 的 .cmd 里 0x0D/0x0A 不会出现在双字节字符中间，替换是安全的。"""
    return data.replace(b"\r\n", b"\n")


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""))
    return ok


def runtime_checks() -> int:
    """B 层：判题运行时的静态防回归，不依赖任何本机二进制产物。"""
    results = []

    proto = (ROOT / "frontend/src/lib/pyodide/protocol.ts").read_text(encoding="utf-8")
    results.append(check(
        "Pyodide 指向同源 /pyodide/（非 CDN）",
        "DEFAULT_INDEX_URL = `/pyodide/`" in proto
        and "DEFAULT_INDEX_URL = `https://" not in proto,
    ))
    m = re.search(r"PYODIDE_VERSION\s*=\s*'([^']+)'", proto)
    fetch = (ROOT / "scripts/fetch_pyodide.py").read_text(encoding="utf-8")
    fm = re.search(r'VERSION\s*=\s*"([^"]+)"', fetch)
    results.append(check(
        "SDK 版本：protocol.ts == fetch_pyodide.py",
        bool(m and fm and m.group(1) == fm.group(1)),
        f"{m.group(1) if m else '?'} / {fm.group(1) if fm else '?'}",
    ))

    pub = ROOT / "frontend/public/pyodide"
    absent = [n for n in PYODIDE_REQUIRED if not (pub / n).is_file()]
    wasm = pub / "pyodide.asm.wasm"
    results.append(check(
        "public/pyodide 五件运行时齐备且 wasm 非空",
        not absent and wasm.stat().st_size > 1024 * 1024,
        f"缺 {absent}" if absent else f"wasm {wasm.stat().st_size / 1024 / 1024:.2f} MB",
    ))

    exe_txt = (ROOT / "deploy/package/build-app-exe.cmd").read_text(encoding="gbk")
    results.append(check(
        "EXE 构建脚本落盘 go-judge.exe（Rust 只认同级 binaries/）",
        "binaries\\go-judge.exe" in exe_txt
        and "nex-shell\\binaries" in exe_txt,
    ))

    gen_txt = GEN.read_text(encoding="utf-8")
    results.append(check(
        "生成器守 staging 的 Pyodide 资源闭包",
        "PYODIDE_REQUIRED" in gen_txt and "py_missing" in gen_txt,
    ))

    csp_ok = all(
        "wasm-unsafe-eval" in (ROOT / "src-tauri" / n).read_text(encoding="utf-8")
        for n in ("tauri.app.desktop.conf.json", "tauri.app.mobile.conf.json")
    )
    results.append(check(
        "真应用双端 CSP 放行 wasm 编译（否则判题永久卡住）", csp_ok,
    ))
    return len(results), sum(results)


def main() -> int:
    saved = {p: p.read_bytes() for p in TARGETS}
    try:
        spec = importlib.util.spec_from_file_location("prepare_app", GEN)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        # 只重放模板部分；build_staging()/verify_staging() 需要 vite，CI 不跑。
        mod.write_conf("tauri.app.desktop.conf.json", "Nex 学习版")
        mod.write_conf("tauri.app.mobile.conf.json", None)
        mod.write_build_scripts()

        ok = True
        for p in TARGETS:
            same = norm(p.read_bytes()) == norm(saved[p])
            ok = ok and same
            print(("PASS " if same else "FAIL ") + str(p.relative_to(ROOT)))

        # 生成器自带的隔离自检也必须过：输出名绝不能覆盖设计稿包。
        mod.self_check()
        print("PASS self-check: 产物名与设计稿包隔离")

        total, passed = runtime_checks()
        ok = ok and passed == total
        all_total = len(TARGETS) + 1 + total
        all_pass = sum(1 for p in TARGETS if norm(p.read_bytes()) == norm(saved[p])) \
            + 1 + passed
        print(f"\nRESULT {all_pass}/{all_total}")
        return 0 if ok else 1
    finally:
        # 无论成功失败都把库内文件恢复成原字节，不留 diff。
        for p, data in saved.items():
            p.write_bytes(data)


if __name__ == "__main__":
    sys.exit(main())
