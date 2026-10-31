#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""依赖图自检（P2 · C2 的守门脚本）。

检查四件事，任何一条不过就返回非 0：

  1. 章节依赖无环（拓扑排序能吃完所有节点）；
  2. 没有悬空边：chapterDeps / projectRequires / bagua.chapterIds 里的 id
     都必须真实存在于 content 的 141 章里；
  3. 每个项目至少 1 条 requires，且依赖章节的学科与项目 track 一致
     （agent / ml 归一到 ai）；
  4. 图鉴条目绑章率 ≥ 95%（260 条里允许极少数反义词题没有词面锚点，
     但必须逐条列出来，不许悄悄放弃）。

另外顺带查一件「内容可达性」的事：题库里出现的章节 id 必须都能在学习页找到
（BUNDLE.chapters ∪ CLANG_CHAPTERS），否则那些题只存在于题库，地图上没有入口。

用法：python scripts/audit_graph.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH_TS = ROOT / "frontend" / "src" / "data" / "graph.ts"
BAGUA_TS = ROOT / "frontend" / "src" / "data" / "bagua.ts"
BUNDLE_TS = ROOT / "frontend" / "src" / "data" / "bundle.ts"
EX_TS = ROOT / "frontend" / "src" / "data" / "exercises.ts"

SUBJECT_ALIAS = {"agent": "ai", "ml": "ai"}
BAGUA_MIN_RATE = 0.95

fails: list[str] = []
warns: list[str] = []


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def bad(msg: str) -> None:
    fails.append(msg)
    print(f"  ✗ {msg}")


def warn(msg: str) -> None:
    warns.append(msg)
    print(f"  ! {msg}")


# ------------------------------------------------------------------ 解析
def parse_graph() -> dict:
    text = GRAPH_TS.read_text(encoding="utf-8")
    marker = "export const GRAPH: GraphData = "
    i = text.index(marker) + len(marker)
    end = text.index(";\n", i)
    return json.loads(text[i:end])


def parse_bagua() -> list[dict]:
    text = BAGUA_TS.read_text(encoding="utf-8")
    i = text.index("JSON.parse(")
    j = text.index("\n);", i)
    body = text[i + len("JSON.parse(") : j]
    chunks = re.findall(r'"(?:[^"\\]|\\.)*"', body)
    payload = "".join(json.loads(c) for c in chunks)
    return json.loads(payload)


def parse_bundle_chapters() -> dict[str, str]:
    """BUNDLE.chapters[*].chapters[*].id → subject"""
    text = BUNDLE_TS.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for m in re.finditer(r'"([a-z]+)":\{"title":"[^"]*","groups":\{', text):
        pass
    # 逐包扫描：先定位 "chapters":{"<subj>":{"title":...
    for m in re.finditer(r'"chapters":\{"([a-z]+)":\{"title":', text):
        subject = m.group(1)
        seg = text[m.end() : m.end() + 200000]
        for cm in re.finditer(r'"id":"([a-z0-9-]+)","order":', seg):
            out[cm.group(1)] = subject
    # clang 单元在 CLANG_CHAPTERS
    clang_ts = ROOT / "frontend" / "src" / "data" / "clangUnits.ts"
    if clang_ts.exists():
        for cm in re.finditer(r'"id":"(clang-u\d+)","order":', clang_ts.read_text(encoding="utf-8")):
            out[cm.group(1)] = "clang"
    return out


def parse_bank_chapters() -> set[str]:
    text = EX_TS.read_text(encoding="utf-8")
    m = re.search(r"export const EXERCISES: BankExercise\[\] = (\[)", text)
    arr = json.loads(text[m.start(1) : text.rindex("]") + 1])
    return {e["ch"] for e in arr}


# ------------------------------------------------------------------ 检查
def main() -> None:
    g = parse_graph()
    deps: dict[str, list[str]] = g["chapterDeps"]
    reqs: dict[str, list[str]] = g["projectRequires"]
    subj_of: dict[str, str] = g["chapterSubject"]
    title_of: dict[str, str] = g["chapterTitle"]
    known = set(title_of)

    print(f"章节 {len(known)} · 依赖边 {sum(map(len, deps.values()))} · 项目 {len(reqs)} · requires 边 {sum(map(len, reqs.values()))}")

    # 1) 环检测（Kahn）
    indeg = {n: 0 for n in known}
    adj: dict[str, list[str]] = {n: [] for n in known}
    for n, ps in deps.items():
        for p in ps:
            if p in known:
                adj[p].append(n)
                indeg[n] += 1
    q = [n for n, d in indeg.items() if d == 0]
    seen = 0
    while q:
        n = q.pop()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if seen == len(known):
        ok(f"章节依赖无环（拓扑序覆盖 {seen}/{len(known)}）")
    else:
        cyc = sorted(n for n, d in indeg.items() if d > 0)
        bad(f"章节依赖有环，涉及 {len(cyc)} 章：{cyc[:8]}")

    # 2) 悬空边
    dangling = [(n, p) for n, ps in deps.items() for p in ps if p not in known]
    dangling += [(slug, c) for slug, cs in reqs.items() for c in cs if c not in known]
    if dangling:
        bad(f"悬空依赖 {len(dangling)} 条：{dangling[:6]}")
    else:
        ok("无悬空依赖（章节 / 项目两个方向）")

    # 3) 项目 requires
    empty = [s for s, cs in reqs.items() if not cs]
    if empty:
        bad(f"{len(empty)} 个项目没有 requires：{empty[:6]}")
    else:
        ok(f"{len(reqs)} 个项目都有 ≥1 章 requires")

    # 项目 track 与依赖章节学科是否一致
    proj_doc = json.loads((ROOT / "content/_projects/career-projects.json").read_text(encoding="utf-8"))
    proj_subject = {
        p["slug"]: SUBJECT_ALIAS.get(p.get("track") or "", p.get("track") or "")
        for p in (proj_doc.get("items") or [])
    }
    cross = [
        (slug, c, proj_subject.get(slug), subj_of.get(c))
        for slug, cs in reqs.items()
        for c in cs
        if proj_subject.get(slug) and subj_of.get(c) != proj_subject.get(slug)
    ]
    if cross:
        bad(f"{len(cross)} 条 requires 跨学科（项目与章节学科不一致）：{cross[:4]}")
    else:
        ok("requires 全部落在项目本学科内")

    unknown_proj = sorted(set(proj_subject) - set(reqs))
    if unknown_proj:
        bad(f"{len(unknown_proj)} 个项目不在 graph.ts 里：{unknown_proj[:5]}")
    else:
        ok(f"项目覆盖完整（{len(proj_subject)} / {len(proj_subject)}）")

    # 4) 图鉴绑章率
    bagua = parse_bagua()
    bound = [b for b in bagua if b.get("chapterIds")]
    rate = len(bound) / max(len(bagua), 1)
    unbound = [b["id"] for b in bagua if not b.get("chapterIds")]
    bad_links = [(b["id"], c) for b in bagua for c in (b.get("chapterIds") or []) if c not in known]
    if bad_links:
        bad(f"图鉴绑定了不存在的章节 {len(bad_links)} 条：{bad_links[:5]}")
    if rate >= BAGUA_MIN_RATE:
        ok(f"图鉴绑章 {len(bound)}/{len(bagua)}（{rate * 100:.1f}% ≥ {BAGUA_MIN_RATE * 100:.0f}%）")
    else:
        bad(f"图鉴绑章率过低 {rate * 100:.1f}% < {BAGUA_MIN_RATE * 100:.0f}%")
    if unbound:
        warn(f"未绑章节 {len(unbound)} 条（无词面锚点，UI 需显示「暂无对应章节」）：{unbound}")

    # 5) 内容可达性：题库章节必须都能在学习页找到
    bundle_ch = parse_bundle_chapters()
    bank_ch = parse_bank_chapters()
    missing = sorted(bank_ch - set(bundle_ch))
    if missing:
        bad(f"题库有 {len(missing)} 章在学习页没有入口：{missing}")
    else:
        ok(f"题库 {len(bank_ch)} 章全部有学习页入口（bundle {len(bundle_ch)} 章）")
    orphan = sorted(set(bundle_ch) - bank_ch)
    if orphan:
        warn(f"{len(orphan)} 章没有配套题（学习页可读，但做不了关）：{orphan[:6]}")

    print()
    if fails:
        print(f"AUDIT_FAIL：{len(fails)} 项未通过，{len(warns)} 项提醒")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"AUDIT_OK：全部通过（{len(warns)} 项提醒）")


if __name__ == "__main__":
    main()
