# -*- coding: utf-8 -*-
"""只重写指定章节的 pitfalls.md（不动 concept/examples/manifest）。

用法：
    python scripts/_regen_pitfalls.py fs-ch09 py-ch09
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _new_chapters import CHAPTERS  # noqa: E402
from build_new_chapters import build_pitfalls  # noqa: E402

CONTENT = ROOT / "content"
BY_ID = {c["id"]: c for c in CHAPTERS}


def main(argv: list[str]) -> int:
    ids = argv or list(BY_ID)
    rc = 0
    for cid in ids:
        ch = BY_ID.get(cid)
        if not ch:
            print(f"  [skip] {cid}: 不在 _new_chapters.py")
            rc = 1
            continue
        path = CONTENT / ch["subject"] / cid / "pitfalls.md"
        if not path.parent.exists():
            print(f"  [skip] {cid}: 章目录不存在")
            rc = 1
            continue
        path.write_text(build_pitfalls(ch), encoding="utf-8")
        print(f"  [ok] {cid}: 重写 pitfalls.md（{len(ch['pitfalls'])} 条）")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
