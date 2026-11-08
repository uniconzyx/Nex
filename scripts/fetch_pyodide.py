# -*- coding: utf-8 -*-
"""把 Pyodide 0.28.3 的运行时资源拉到本地 public/pyodide/。

判题沙箱原先从 cdn.jsdelivr.net 动态 import pyodide.mjs，在封装包里有两个硬伤：
  1) Tauri 的 CSP 是 script-src 'self'，跨源动态 import 会被拦；
  2) 离线使用时根本没网，判题直接失败。
本脚本从 npm tarball 取同版本资源（与 protocol.ts 的 PYODIDE_VERSION 对齐），
只保留 loadPyodide 真正会读的文件，落到 frontend/public/pyodide/。
可反复执行（已存在且大小一致则跳过）。
"""
from __future__ import annotations

import io
import json
import pathlib
import tarfile
import urllib.request

# 本脚本在 scripts/ 下只有一层，仓库根是 parents[1]。
# （deploy/package/ 下的生成器是两层，那里才是 parents[2]，别照抄。）
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "pyodide"
VERSION = "0.28.3"
# loadPyodide 的必备资源；其余 package 数据按需从 lock 文件解析，不放进包
NEEDED = (
    "pyodide.mjs",
    "pyodide.asm.js",
    "pyodide.asm.wasm",
    "python_stdlib.zip",
    "pyodide-lock.json",
)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url: str) -> bytes:
    with opener.open(url, timeout=60) as r:
        return r.read()


def main() -> None:
    meta = json.loads(get(f"https://registry.npmjs.org/pyodide/{VERSION}"))
    tar_url = meta["dist"]["tarball"]
    print(f"[fetch_pyodide] tarball = {tar_url}")
    blob = get(tar_url)
    print(f"[fetch_pyodide] downloaded {len(blob) / 1024 / 1024:.2f} MB")

    tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    # npm tarball 里文件都在 package/ 下；full 资源在 package/ 根目录
    members = {m.name.split("/", 1)[-1]: m for m in tf.getmembers() if m.isfile()}
    OUT.mkdir(parents=True, exist_ok=True)
    for name in NEEDED:
        m = members.get(name)
        if m is None:
            print(f"[fetch_pyodide] SKIP (not in tarball): {name}")
            continue
        data = tf.extractfile(m).read()
        target = OUT / name
        if target.is_file() and target.stat().st_size == len(data):
            print(f"[fetch_pyodide] unchanged {name} ({len(data) / 1024:.1f} KB)")
            continue
        target.write_bytes(data)
        print(f"[fetch_pyodide] wrote {name} ({len(data) / 1024 / 1024:.2f} MB)")

    total = sum(f.stat().st_size for f in OUT.iterdir() if f.is_file())
    print(f"[fetch_pyodide] local runtime = {total / 1024 / 1024:.2f} MB")
    have = {f.name for f in OUT.iterdir() if f.is_file()}
    missing = [n for n in ("pyodide.mjs", "pyodide.asm.wasm", "python_stdlib.zip",
                           "pyodide-lock.json") if n not in have]
    if missing:
        raise SystemExit("[fetch_pyodide] 缺关键文件: " + ", ".join(missing))
    print("[fetch_pyodide] OK")


if __name__ == "__main__":
    main()
