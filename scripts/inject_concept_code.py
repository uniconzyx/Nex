# -*- coding: utf-8 -*-
"""给「concept 无可运行代码」的章节补 §代码 小节。

问题（2026-10-28 审计）：`scripts/audit_depth.py` 记录 30 章 concept 目录里
``code_blocks == 0``——理论讲了，但读者看不到任何一行能跑的东西。这 30 章里有
完整可运行的 ``examples/*.json``（代码 + 真实期望输出），只是**没有被嵌进正文**。

本脚本的做法（为什么不"另写一段代码"）：
  代码全部**取自该章 examples/*.json 的真实内容**，期望输出也取 ``expected_output``
  原值。这样正文里写的「跑出来是什么」与判题台真跑的结果是同一条字符串，
  不会出现「书上说输出 X，实际输出 Y」。
  若某章暂无合适的 example，脚本**不编造**，而是跳过并在报告里列出。

嵌入位置：`## 三视角解析` 之前；没有该节的章（cpp-ch01/03/04 这类骨架章）插在
最后一个 `##` 小节之后。每章最多嵌 2 个示例，取 examples 里编号最小、且带
expected_output 的两个（编号小的通常是先修概念）。

用法：
    python scripts/inject_concept_code.py --dry-run
    python scripts/inject_concept_code.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
sys.path.insert(0, str(ROOT / "scripts"))

MARK = "<!-- injected-code -->"
MAX_PER_CHAPTER = 2
# 这些语言的 concept 正文里嵌代码是最有价值的；其余按同一规则处理，不做特例
LANG_FENCE = {
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "python": "python",
    "javascript": "js",
    "typescript": "ts",
    "bash": "bash",
    "sql": "sql",
    "go": "go",
    "rust": "rust",
}


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def pick_examples(ch: Path, limit: int = MAX_PER_CHAPTER) -> list[dict]:
    """挑能自解释的示例：有代码、有期望输出、期望输出不是占位。"""
    out = []
    for f in sorted((ch / "examples").glob("*.json")):
        d = load(f)
        code = (d.get("code") or "").strip()
        exp = (d.get("expected_output") or "").strip()
        if not code or not exp:
            continue
        # 输出截断到 900 字而不是整条丢弃：tool-ch06 这类演示型脚本的期望输出
        # 动辄 2~4KB，但前 900 字已经足以看清「跑出来长什么样」，剩下的留给判题台。
        truncated = len(exp) > 900
        out.append({
            "file": f.name,
            "title": (d.get("title") or f.stem).strip(),
            "lang": (d.get("code_lang") or "java").strip().lower(),
            "code": code,
            "expected": exp[:900].rstrip() + ("\n…（后续输出略，完整结果见判题台）" if truncated else ""),
            "stdin": (d.get("stdin") or "").strip(),
        })
        if len(out) >= limit:
            break
    return out


def build_block(exs: list[dict]) -> str:
    L = [MARK, "## 可运行代码：把上面的说法跑一遍", ""]
    L.append("下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，"
             "不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。")
    L.append("")
    for e in exs:
        fence = LANG_FENCE.get(e["lang"], e["lang"] or "text")
        L.append(f"### {e['title']}")
        L.append("")
        if e["stdin"]:
            L.append(f"标准输入：`{e['stdin'][:120]}`")
            L.append("")
        L.append(f"```{fence}")
        L.append(e["code"].rstrip())
        L.append("```")
        L.append("")
        L.append("实际输出：")
        L.append("")
        L.append("```text")
        L.append(e["expected"].rstrip())
        L.append("```")
        L.append("")
        L.append(f"> 出处：`examples/{e['file']}`。改一处再看输出变没变，比读三遍解释有用。")
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def insert_into(md_path: Path, block: str) -> str:
    """返回 'inserted' / 'already' / 'no-slot'。插在「三视角解析」之前。"""
    text = md_path.read_text(encoding="utf-8")
    if MARK in text:
        return "already"
    if "```" in text:
        return "has-code"

    lines = text.split("\n")
    target = None
    # 1) 有「## 三视角解析」就插在它前面（cpp/fundamentals/clang 风格）
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and "三视角" in ln:
            target = i
            break
    # 2) 没有 ## 级节（bigdata 三章用「# 一、」当节标题）：插在第一个视角 ### 之前
    if target is None:
        for i, ln in enumerate(lines):
            if ln.startswith("### ") and ("视角" in ln or "🧑‍💻" in ln or "🎓" in ln):
                target = i
                break
    # 3) 骨架章：插在最后一个 ## / # 节之后（文件末尾）
    if target is None:
        idx = max((i for i, ln in enumerate(lines) if ln.startswith("## ")), default=-1)
        if idx < 0:
            idx = max((i for i, ln in enumerate(lines) if ln.startswith("# ")), default=-1)
        if idx < 0:
            return "no-slot"
        target = len(lines)

    head = "\n".join(lines[:target]).rstrip() + "\n\n"
    tail = "\n".join(lines[target:])
    md_path.write_text(head + block + "\n" + tail, encoding="utf-8")
    return "inserted"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    depth = load(CONTENT / "_depth_audit.json")
    targets = [c for c in depth["chapters"] if c["metrics"]["code_blocks"] == 0]
    targets.sort(key=lambda c: c["id"])

    done, skipped, stats = [], [], []
    for c in targets:
        ch_dir = None
        for sub in CONTENT.iterdir():
            if not sub.is_dir() or sub.name.startswith("_"):
                continue
            cand = sub / c["id"]
            if cand.is_dir():
                ch_dir = cand
                break
        if ch_dir is None:
            skipped.append((c["id"], "目录不存在"))
            continue

        exs = pick_examples(ch_dir)
        if not exs:
            skipped.append((c["id"], "examples 里没有带期望输出的可跑示例"))
            continue

        block = build_block(exs)
        files = sorted((ch_dir / "concept").glob("*.md"))
        if not files:
            skipped.append((c["id"], "concept 目录为空"))
            continue

        # 只往第一篇 concept 里插一次：代码是章级的，不该篇篇重复
        first = files[0]
        state = "dry" if not apply else insert_into(first, block)
        if state in ("inserted", "dry"):
            done.append((c["id"], first.name, len(exs)))
        else:
            skipped.append((c["id"], f"跳过：{state}"))

    print(f"目标 {len(targets)} 章 · 补入 {len(done)} 章 · 跳过 {len(skipped)} 章")
    for cid, fname, n in done:
        print(f"  + {cid:14s} {fname}  ({n} 个示例)")
    for cid, why in skipped:
        print(f"  - {cid:14s} {why}")
    if not apply:
        print("\n（dry-run，未写盘；加 --apply 生效）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
