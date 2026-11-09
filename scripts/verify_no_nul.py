#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""门禁：content/ 的 Markdown 里不得出现裸 NUL 字节（0x00）。

2026-11-09 真实事故：讲「C 字符串以 \0 结尾」时，两处把转义写成了真实的
NUL 字节。前端 chunk 里只是变成 \u0000 不可见字符，但后端把概念全文灌进
PostgreSQL 的 UTF8 Text 列时直接报 `invalid byte sequence ... 0x00`，
播种整批失败。两个生成器已做兜底替换，这里从源头堵住，避免脏字节再入库。

零第三方依赖；纯只读，不修改任何文件。
用法：python scripts/verify_no_nul.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


def main() -> None:
    files = sorted(p for p in CONTENT.rglob("*.md") if not p.name.startswith("."))
    bad: list[tuple[str, int]] = []
    for p in files:
        data = p.read_bytes()
        n = data.count(b"\x00")
        if n:
            bad.append((str(p.relative_to(ROOT)), n))
    if bad:
        print(f"FAIL 发现 {len(bad)} 个含裸 NUL 的 Markdown：")
        for rel, n in bad:
            print(f"  {rel}  NUL={n}  （讲 \\0 请写成字面反斜杠+0）")
        raise SystemExit(1)
    print(f"NO_NUL_OK  {len(files)} 个 Markdown 均无裸 NUL 字节")
    return None


if __name__ == "__main__":
    sys.exit(main())
