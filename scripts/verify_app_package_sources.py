#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真应用封装「生成器 -> 入库产物」幂等门禁（纯标准库，CI Linux 可直接跑）。

只重放 prepare_app.py 里**不依赖 vite** 的部分（两份增量配置 + 两个构建脚本），
与库内文件做换行归一后的字节比对，然后恢复原字节；不跑 vite、不碰 staging。

防的坑与 verify_icon_sources.py 同源：曾有人手改产物 .cmd 却没改生成器模板，
下一次 prepare 被静默覆盖回旧版。比对用 norm() 归一 CRLF/LF，因为
.gitattributes 是 `* text=auto eol=lf` —— Windows 工作区与 CI checkout 的换行
本就不同，归一后相同即视为幂等（不把换行差异误报成漂移）。

用法：python scripts/verify_app_package_sources.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "deploy" / "package" / "prepare_app.py"
TARGETS = [
    ROOT / "src-tauri" / "tauri.app.desktop.conf.json",
    ROOT / "src-tauri" / "tauri.app.mobile.conf.json",
    ROOT / "deploy" / "package" / "build-app-exe.cmd",
    ROOT / "deploy" / "package" / "build-app-apk.cmd",
]


def norm(data: bytes) -> bytes:
    """GBK 的 .cmd 里 0x0D/0x0A 不会出现在双字节字符中间，替换是安全的。"""
    return data.replace(b"\r\n", b"\n")


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
        print(f"\nRESULT {sum(1 for _ in TARGETS) + 1}/"
              f"{len(TARGETS) + 1}" if ok else "\nRESULT FAILED")
        return 0 if ok else 1
    finally:
        # 无论成功失败都把库内文件恢复成原字节，不留 diff。
        for p, data in saved.items():
            p.write_bytes(data)


if __name__ == "__main__":
    sys.exit(main())
