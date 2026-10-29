# -*- coding: utf-8 -*-
"""audit_reexam_code.py —— 机试题代码可复跑守门
=============================================================================
背景：机试题的「③ 完整代码」曾只在创建时跑过一次，入库后再无手段验证
「代码还能不能跑出那个答案」。本脚本把这件事变成可复跑的门禁：

  对 content/_tracks/reexam.json 里每道机试题：
    1) 用 g++ -std=c++17 重新编译 code；
    2) 用 sampleIn 作为 stdin 重新运行；
    3) 逐字符比对 stdout 与 sampleOut（允许末尾换行差异之外严格相等）。

用法：
    python scripts/audit_reexam_code.py            # 全部
    python scripts/audit_reexam_code.py --limit 5  # 只跑前 5 道（快速自检）
    python scripts/audit_reexam_code.py --id sysu-2021-lru

缺 g++ 时直接报错退出（不静默跳过），因为没有编译器就无法证明代码可运行。
=============================================================================
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK = ROOT / "content/_tracks/reexam.json"


def compile_and_run(code: str, stdin_data: str) -> tuple[bool, str]:
    """编译并运行，返回 (成功?, stdout 或 错误信息)"""
    tmp = tempfile.mkdtemp(prefix="rx-audit-")
    try:
        src = os.path.join(tmp, "a.cpp")
        exe = os.path.join(tmp, "a.exe")
        with io.open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        c = subprocess.run(
            ["g++", "-std=c++17", "-O2", "-o", exe, src],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if c.returncode != 0:
            return False, "编译失败:\n" + (c.stderr or "")[:900]
        r = subprocess.run(
            [exe], input=stdin_data, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        if r.returncode != 0:
            return False, "运行失败 rc=%d:\n%s" % (r.returncode, (r.stderr or "")[:600])
        return True, r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def norm(s: str) -> str:
    """行尾空白不计，末尾换行不计"""
    return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n")).strip("\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 道")
    ap.add_argument("--id", default="", help="只跑指定 id")
    args = ap.parse_args()

    if not shutil.which("g++"):
        print("[FAIL] 未找到 g++，无法验证机试代码可编译")
        return 1

    data = json.loads(io.open(TRACK, encoding="utf-8").read())
    tests = data["machineTests"]
    if args.id:
        tests = [t for t in tests if t["id"] == args.id]
    if args.limit:
        tests = tests[: args.limit]
    if not tests:
        print("[FAIL] 没有匹配的机试题")
        return 1

    fail = 0
    print("机试代码可复跑审计：%d 道" % len(tests))
    for t in tests:
        tid = t["id"]
        if "sampleIn" not in t or "sampleOut" not in t:
            print("  ✗ %-30s 缺 sampleIn/sampleOut（无法验证）" % tid)
            fail += 1
            continue
        ok, out = compile_and_run(t["code"], t["sampleIn"])
        if not ok:
            print("  ✗ %-30s %s" % (tid, out.splitlines()[0]))
            fail += 1
            continue
        if norm(out) != norm(t["sampleOut"]):
            print("  ✗ %-30s 输出不符\n      期望=%r\n      实际=%r"
                  % (tid, norm(t["sampleOut"])[:120], norm(out)[:120]))
            fail += 1
            continue
        print("  ✓ %-30s -> %r" % (tid, norm(out).replace("\n", " | ")[:48]))

    print()
    if fail:
        print("REEXAM_CODE_FAIL (%d/%d)" % (fail, len(tests)))
        return 1
    print("REEXAM_CODE_OK (%d/%d)" % (len(tests), len(tests)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
