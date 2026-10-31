# -*- coding: utf-8 -*-
"""逐条跑 examples，比对 expected_output 与实际输出。不一致就是假实测，直接失败。

为什么必须有这一步：`validate_content._check_example_outputs` 只能查「脏数据」
（空输出、占位符、Traceback 当成正常输出），它查不出「输出是对的另一回事」。
新增章节的 10×N 条示例如果靠人推输出，必然有几条对不上，而学生照着跑一次就废了。

做法：
  · python → 写临时文件，用管理版 Python 子进程跑；带 stdin 就喂进去；
  · javascript → 写 .mjs，用 node 子进程跑；
  · 超时 10s；stderr 非空且退出码非 0 视为失败；
  · 输出比对时右侧去空白、去尾随空行（避免行尾空格造成的假失败，但保留内部换行）。

用法：
    python scripts/verify_examples.py                 # 全部章节
    python scripts/verify_examples.py --only fs-ch09  # 指定章节
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

PY_BIN = sys.executable
NODE_BIN = r"C:\Users\zyx\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"
if not Path(NODE_BIN).exists():
    NODE_BIN = shutil.which("node") or "node"

# 抖动的输出（时间戳、随机数、地址）比对时忽略的行首标记
VOLATILE = ("0x", "耗时", "elapsed", "Time:", "内存")


def norm(s: str) -> str:
    lines = [ln.rstrip() for ln in s.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def run_one(ex: dict) -> tuple[bool, str, str, str]:
    lang = (ex.get("code_lang") or "python").lower()
    code = ex.get("code") or ""
    stdin = ex.get("stdin") or ""
    expected = norm(ex.get("expected_output") or "")

    with tempfile.TemporaryDirectory() as td:
        if lang in ("python", "py"):
            p = Path(td) / "main.py"
            p.write_text(code, encoding="utf-8")
            cmd = [PY_BIN, str(p)]
        elif lang in ("javascript", "js", "typescript", "ts"):
            p = Path(td) / "main.mjs"
            p.write_text(code, encoding="utf-8")
            cmd = [NODE_BIN, str(p)]
        else:
            return False, "", expected, f"不支持的语言 {lang}"

        try:
            r = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                               timeout=15, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return False, "", expected, "超时 >15s"

    actual = norm(r.stdout)
    err = norm(r.stderr)
    if r.returncode != 0:
        return False, actual, expected, f"退出码 {r.returncode}: {err[:200]}"
    ok = actual == expected
    return ok, actual, expected, "" if ok else "输出不一致"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔章节 id")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    total = bad = 0
    failures = []
    for ch_dir in sorted(CONTENT.glob("*/*/")):
        cid = ch_dir.name
        if not (ch_dir / "examples").is_dir():
            continue
        if only and cid not in only:
            continue
        for f in sorted((ch_dir / "examples").glob("*.json")):
            ex = json.loads(f.read_text(encoding="utf-8"))
            total += 1
            ok, actual, expected, why = run_one(ex)
            if not ok:
                bad += 1
                failures.append((cid, f.name, ex.get("title", ""), actual, expected, why))

    print(f"跑了 {total} 个示例 · 通过 {total - bad} · 失败 {bad}")
    for cid, fname, title, actual, expected, why in failures:
        print(f"\n✗ {cid}/{fname}  {title}\n  原因: {why}")
        print(f"  期望: {expected[:300]!r}")
        print(f"  实际: {actual[:300]!r}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
