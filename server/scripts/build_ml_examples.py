"""机器学习章节示例构建器：执行源码 → 落盘 examples/*.json（expected_output 为真实 stdout）。

为什么单独做这一步
--------------------------------------------------------------------
`verify_examples.py` 会重新执行 examples 里的代码并与 expected_output 比对。
如果 expected_output 是手写的，极容易出现「看起来对、跑起来差一行」的假实测。
本脚本把「运行」和「落盘」合并成一步：**expected_output 只可能来自真实执行**。

目录约定
--------------------------------------------------------------------
    server/scripts/_ml_src/<chapter>/exNN_<slug>.py      # 第一行写 `# title: ...`
    执行后生成
    content/ml/<chapter>/examples/exNN-<slug>.json

用法
--------------------------------------------------------------------
    python server/scripts/build_ml_examples.py ml-ch01
    python server/scripts/build_ml_examples.py            # 全部章节
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "server" / "scripts" / "_ml_src"
CONTENT = ROOT / "content" / "ml"
TIMEOUT = 60


def _title_of(code: str, fallback: str) -> tuple[str, str]:
    first, _, rest = code.partition("\n")
    m = re.match(r"^#\s*title\s*[:：]\s*(.+)$", first.strip())
    if m:
        return m.group(1).strip(), rest
    return fallback, code


def _clean_stdout(text: str) -> str:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def build(chapter: str) -> int:
    src_dir = SRC / chapter
    if not src_dir.is_dir():
        print(f"[skip] {chapter}: 无源码目录 {src_dir.relative_to(ROOT)}")
        return 0
    out_dir = CONTENT / chapter / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src_dir.glob("ex*.py"))
    if not files:
        print(f"[skip] {chapter}: 无 ex*.py")
        return 0

    built = 0
    for src in files:
        m = re.match(r"^(ex\d+)_(.+)\.py$", src.name)
        if not m:
            print(f"[warn] 跳过命名不合规的文件：{src.name}")
            continue
        tag, slug = m.group(1), m.group(2)
        code = src.read_text(encoding="utf-8")
        title, body = _title_of(code, slug.replace("-", " "))

        proc = subprocess.run(
            [sys.executable, "-c", body],
            cwd=str(src_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT,
        )
        if proc.returncode != 0:
            print(f"[FAIL] {chapter}/{src.name} rc={proc.returncode}")
            print((proc.stdout or "")[-800:])
            print((proc.stderr or "")[-1200:])
            return 1
        if proc.stderr.strip():
            print(f"[warn] {chapter}/{src.name} 有 stderr（教学性警告可接受）："
                  f"{proc.stderr.strip().splitlines()[0][:120]}")

        payload = {
            "title": title,
            "code_lang": "python",
            "code_std": "3.13",
            "stdin": "",
            "expected_output": _clean_stdout(proc.stdout),
            "code": body.lstrip("\n"),
        }
        dst = out_dir / f"{tag}-{slug}.json"
        dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        built += 1

    print(f"{chapter}: 生成 {built} 个示例 -> {out_dir.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", help="章节目录名，如 ml-ch01；省略则全部")
    args = ap.parse_args()
    targets = args.chapters or sorted(p.name for p in SRC.iterdir() if p.is_dir())
    for ch in targets:
        rc = build(ch)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
