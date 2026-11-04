# -*- coding: utf-8 -*-
"""来源锚点真实性守门：`_manifest.json` 的 github_notes 里 § 指向的小节，必须真实存在。

为什么需要它
------------
`audit_sources.py` 的 `ok_anchor` 只要资源文本里出现 `1.1`、`2.2`、`第 2 节` 就算通过——
而这些片段常常来自 B 站表格或正文里的旧文本，与 GitHub notes 是否真的定位到本章小节
毫无关系。结果是一批「编号虚构」的 notes（例如 py-ch01 写 `§1.2 讲「流程控制与分支」`，
而该章 concept 的真实小节是「一、名字与对象：绑定而不是装箱」）全部通过审计。

本脚本用独立判据重算：
  Q1 编号越界  §x.y 的 x 超过本章 concept 文件数（该小节不可能存在）
  Q3 标题漂移  锚点片段与所指向的小节标题二元组重合度 < 阈值

退出码
------
0  无 Q1 且 Q3 为 0
1  存在 Q1 或 Q3
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

SEG_SPLIT = re.compile(r"[·｜|；;]")
NUM_HEAD = re.compile(r"^§\s*([0-9]+)\.([0-9]+)")
QUOTED = re.compile(r"讲\s*[「“]([^」”]+)[」”]")
NOISE = re.compile(r"[\s\-_（）()「」【】《》，,。.、:：;；`'\"“”~→/]")

THRESH = 0.34


def norm(s: str) -> str:
    return NOISE.sub("", s)


def bigrams(s: str) -> set[str]:
    n = norm(s)
    return {n[i:i + 2] for i in range(len(n) - 1)}


def overlap(a: str, b: str) -> float:
    ga, gb = bigrams(a), bigrams(b)
    if not ga:
        return 0.0
    return len(ga & gb) / len(ga)


def chapter_titles(ch_dir: Path) -> list[list[str]]:
    """按 concept 文件顺序返回 [[该文件的小节标题, ...], ...]。"""
    cdir = ch_dir / "concept"
    if not cdir.exists():
        return []
    out: list[list[str]] = []
    for f in sorted(cdir.glob("*.md")):
        titles = [
            ln[3:].strip()
            for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.startswith("## ") and not ln.startswith("### ")
            and ln[3:].strip() != "三视角解析"
        ]
        out.append(titles)
    return out


def anchors(note: str) -> list[str]:
    segs = [s.strip() for s in SEG_SPLIT.split(note) if s.strip().startswith("§")]
    if not segs and note.strip().startswith("§"):
        segs = [note.strip()]
    return segs


def judge_anchor(seg: str, per_file: list[list[str]]) -> tuple[str, str]:
    """返回 ("ok"|"Q1"|"Q3", 说明)。"""
    if not per_file:
        return "Q3", "本章无 concept 文件"
    m = NUM_HEAD.match(seg)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        if x < 1 or x > len(per_file) or y < 1:
            return "Q1", f"§{x}.{y} 越界（本章 {len(per_file)} 个概念文件）"
        targets = per_file[x - 1]
    else:
        targets = [t for ts in per_file for t in ts]
    if not targets:
        return "Q3", "目标文件无小节标题"
    best = max((overlap(seg, t) for t in targets), default=0.0)
    if best < THRESH:
        return "Q3", f"重合 {best:.2f}｜{seg[:46]}"
    return "ok", f"{best:.2f}"


def iter_units(subj: str, data: dict):
    units = list(data.get("chapters", []))
    if subj == "clang":
        units = list(((data.get("clang_module") or {}).get("units")) or [])
    return units


def main() -> None:
    only = sys.argv[1:] or None
    subjects = only or [
        p.name for p in sorted(CONTENT.iterdir()) if (p / "_manifest.json").exists()
    ]
    total = ok = 0
    q1_list: list[str] = []
    q3_list: list[str] = []
    bad_ch: dict[str, int] = {}

    for subj in subjects:
        mf = CONTENT / subj / "_manifest.json"
        if not mf.exists():
            continue
        data = json.loads(mf.read_text(encoding="utf-8"))
        for ch in iter_units(subj, data):
            cid = ch.get("id")
            notes = ((ch.get("resources") or {}).get("github_notes")) or []
            if not notes:
                continue
            per_file = chapter_titles(CONTENT / subj / cid)
            for i, note in enumerate(notes, 1):
                segs = anchors(note)
                if not segs:
                    continue  # 无 § 的不在本脚本职责内（由 audit_sources 管）
                total += 1
                verdict, why = judge_anchor(segs[0], per_file)
                if verdict == "ok":
                    ok += 1
                elif verdict == "Q1":
                    q1_list.append(f"Q1 {subj}/{cid}#{i} {why}")
                    bad_ch[f"{subj}/{cid}"] = bad_ch.get(f"{subj}/{cid}", 0) + 1
                else:
                    q3_list.append(f"Q3 {subj}/{cid}#{i} {why}")
                    bad_ch[f"{subj}/{cid}"] = bad_ch.get(f"{subj}/{cid}", 0) + 1

    print(f"§ 锚点总数 {total} ｜真实命中 {ok} ｜编号越界 {len(q1_list)} ｜标题漂移 {len(q3_list)}")
    if q1_list:
        print("\n-- 编号越界（该小节不可能存在）--")
        for s in q1_list:
            print("  " + s)
    if q3_list:
        print("\n-- 标题漂移（前 40 条）--")
        for s in q3_list[:40]:
            print("  " + s)
        if len(q3_list) > 40:
            print(f"  ... 另有 {len(q3_list)-40} 条")
    if bad_ch:
        print(f"\n有问题的章 {len(bad_ch)}：")
        line = "  " + "  ".join(f"{k}({v})" for k, v in sorted(bad_ch.items()))
        print(line)
    sys.exit(0 if not q1_list and not q3_list else 1)


if __name__ == "__main__":
    main()
