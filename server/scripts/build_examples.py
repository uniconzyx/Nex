"""通用章节示例构建器：`_<subject>_src/<chapter>/exNN_*.py` → `content/<subject>/<chapter>/examples/*.json`。

与 `build_ml_examples.py` 的区别
--------------------------------------------------------------------
ml 版把 subject 硬编码成 `ml`。AI Agent 学科要复用同一套「真实执行才落盘」的机制，
所以这里把 subject 参数化，逻辑保持一致（第一行 `# title:`、真实 stdout、JSON 载荷）。

用法：
    python server/scripts/build_examples.py --subject agent agent-ch01
    python server/scripts/build_examples.py --subject agent          # 该学科全部章节
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TIMEOUT = 90


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


def build(subject: str, chapter: str) -> int:
    src_root = ROOT / "server" / "scripts" / f"_{subject}_src"
    src_dir = src_root / chapter
    if not src_dir.is_dir():
        print(f"[skip] {chapter}: 无源码目录 {src_dir.relative_to(ROOT)}")
        return 0
    out_dir = ROOT / "content" / subject / chapter / "examples"
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
            print(f"[warn] {chapter}/{src.name} stderr："
                  f"{proc.stderr.strip().splitlines()[0][:120]}")

        payload = {
            "title": title,
            "code_lang": "python",
            "code_std": "3.13",
            "stdin": "",
            "expected_output": _clean_stdout(proc.stdout),
            "code": body.lstrip("\n"),
        }
        (out_dir / f"{tag}-{slug}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        built += 1

    print(f"{chapter}: 生成 {built} 个示例 -> {out_dir.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True, help="学科目录名，如 agent")
    ap.add_argument("chapters", nargs="*", help="章节目录名，如 agent-ch01；省略则全部")
    args = ap.parse_args()

    src_root = ROOT / "server" / "scripts" / f"_{args.subject}_src"
    targets = args.chapters or sorted(p.name for p in src_root.iterdir()
                                      if p.is_dir() and p.name.startswith(args.subject))
    for ch in targets:
        if build(args.subject, ch):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
