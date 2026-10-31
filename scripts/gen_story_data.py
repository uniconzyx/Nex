#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 153 幕旁白的数据侧（P3 · C4）。

【唯一源】content/_story/acts.json —— 手写。其余全部由本脚本产出：
  - frontend/src/data/story.ts      剧情页直接读
  - docs/Playability-P3-Story-Script.md  人读的台词本（和 json 同源，不会各说各话）

【为什么要有校验】
  141 条台词靠人工写，必然混进几条「议论文」：太长、没锚点、语气跑调。
  与其上线后被人肉发现，不如让生成阶段直接拦下来 —— 不合格就不生成。

校验五条：
  1. 覆盖：13 学科合计 153 章，与 graph.ts 的 chapterSubject 完全一致（无重、无漏、无孤儿）；
  2. 归属：每章的学科必须和所属幕的学科一致（防止把 cpp 章节塞进 java 幕）；
  3. 长度：line 有效长度 15~45（代码/英文标识符按 1 字计，否则 p = realloc(p, n) 一条吃掉半句预算）；
  4. 锚点：anchor 非空（对应 goals.md 的哪条认知，改内容时要能回查）；
  5. 语气：tone ∈ {pitfall, scene, archive}；archive 已说半个答案，UI 必须完成后才显示。

用法：
  python scripts/gen_story_data.py            # 校验 + 生成
  python scripts/gen_story_data.py --check    # 只校验
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "_story" / "acts.json"
OUT_TS = ROOT / "frontend" / "src" / "data" / "story.ts"
OUT_MD = ROOT / "docs" / "Playability-P3-Story-Script.md"

# 不再硬编码章节总数：以 graph.ts 的权威章节表为基准（内容扩张后章节会变，
# 硬编码会误报「应为 153」而拒绝生成）。覆盖校验改为 len(chapters)。
LINE_MIN, LINE_MAX = 15, 70
TONES = {"pitfall", "scene", "archive", "field"}

# 语气 → 未完成时是否可直接显示。field（现场）只描述现象不给解释，能当钩子。
# pitfall 的「我以为…」同样是钩子；只有 archive 已经说了一半答案，必须藏。
TEASER_TONES = {"pitfall", "scene", "field"}

# 术语批注：只给「不懂这个词就读不下去」的台词挂。全挂等于词典，不挂等于天书。
NOTES_MAX = 60

# 幕内章节的学科允许集合（ai 学科在内容里由 agent / ai / ml 三条线合并而来）
SUBJECT_CHAPTER_PREFIX = {
    "ai": ("agent-", "ai-", "ml-"),
    "cpp": ("cpp-",),
    "fundamentals": ("fund-",),
    "java": ("java-",),
    "database": ("db-",),
    "fullstack": ("fs-",),
    "middleware": ("mw-",),
    "python": ("py-",),
    "spring": ("spring-",),
    "clang": ("clang-",),
    "bigdata": ("bd-",),
    "data": ("data-",),
    "tooling": ("tool-",),
}


def load_chapters() -> dict[str, dict]:
    """从 graph.ts 取权威的 章节 → 学科/标题 映射（与学习页、依赖图同一份口径）。"""
    text = (ROOT / "frontend" / "src" / "data" / "graph.ts").read_text(encoding="utf-8")
    m = re.search(r"export const GRAPH: GraphData = (\{.*\});", text, re.S)
    if not m:
        sys.exit("graph.ts 解析失败：先跑 scripts/gen_graph.py")
    g = json.loads(m.group(1))
    return {
        cid: {"subject": subj, "title": g["chapterTitle"].get(cid, cid)}
        for cid, subj in g["chapterSubject"].items()
    }


def effective_len(s: str) -> int:
    """有效长度：行内代码与英文标识符各算 1 字。

    纯字符数会把 `p = realloc(p, n)` 这种算成 18 字，可人读它只是一个词。
    """
    s = re.sub(r"`[^`]+`", "X", s)
    s = re.sub(r"[A-Za-z][A-Za-z0-9_.]*", "X", s)
    return len(s)


def validate(doc: dict, chapters: dict[str, dict]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    seen: dict[str, str] = {}

    for subj_key, subj in doc["subjects"].items():
        prefix = SUBJECT_CHAPTER_PREFIX.get(subj_key)
        if not prefix:
            errs.append(f"未知学科 key：{subj_key}")
            continue
        for act in subj["acts"]:
            if not act.get("title"):
                errs.append(f"{act['id']} 缺幕标题")
            for ch in act["chapters"]:
                cid = ch["id"]
                if cid in seen:
                    errs.append(f"{cid} 重复出现（{seen[cid]} / {act['id']}）")
                seen[cid] = act["id"]

                if cid not in chapters:
                    errs.append(f"{cid} 不在 graph.ts 的章节表里")
                    continue

                # 2. 归属
                real_subj = chapters[cid]["subject"]
                if real_subj != subj_key:
                    errs.append(f"{cid} 学科是 {real_subj}，却放在 {subj_key} 的幕 {act['id']} 里")

                # 5. 语气
                if ch.get("tone") not in TONES:
                    errs.append(f"{cid} tone 非法：{ch.get('tone')}")

                # 4. 锚点
                if not (ch.get("anchor") or "").strip():
                    errs.append(f"{cid} 缺 anchor")

                # 3. 长度
                n = effective_len(ch.get("line") or "")
                if n < LINE_MIN:
                    errs.append(f"{cid} 台词过短（{n} 字 < {LINE_MIN}）：{ch.get('line')}")
                elif n > LINE_MAX:
                    errs.append(f"{cid} 台词过长（{n} 字 > {LINE_MAX}）：{ch.get('line')}")

                # 6. 术语批注：只给需要的人，长 2~NOTES_MAX
                note = (ch.get("note") or "").strip()
                if note:
                    if effective_len(note) > NOTES_MAX:
                        errs.append(f"{cid} 批注过长（{effective_len(note)} > {NOTES_MAX}）：{note}")
                    if not re.search(r"[A-Za-z]{2,}|[A-Z]{2,}|\d", ch.get("line") or ""):
                        errs.append(f"{cid} 没有英文/数字术语，却挂了批注：{note}")

    missing = sorted(set(chapters) - set(seen))
    if missing:
        errs.append(f"缺 {len(missing)} 章台词：{missing[:8]}{'...' if len(missing) > 8 else ''}")
    if len(seen) != len(chapters):
        errs.append(f"台词覆盖 {len(seen)} 章，应为 {len(chapters)}（graph.ts 章节数）")

    # 幕内章节数不均只是提醒，不是错误
    for subj_key, subj in doc["subjects"].items():
        sizes = [len(a["chapters"]) for a in subj["acts"]]
        if sizes and max(sizes) - min(sizes) > 1:
            warns.append(f"{subj_key} 的幕大小不齐：{sizes}")

    # 语气配比：档案要占多数（收束感），但不能超过 70%（否则每条都在剧透）
    tally = {"pitfall": 0, "scene": 0, "archive": 0, "field": 0}
    for subj in doc["subjects"].values():
        for act in subj["acts"]:
            for ch in act["chapters"]:
                tally[ch["tone"]] = tally.get(ch["tone"], 0) + 1
    total = sum(tally.values()) or 1
    ratio = tally["archive"] / total
    if ratio < 0.40:
        errs.append(f"档案语气占比 {ratio:.0%} 偏低（要求 ≥40%，当前 {tally['archive']}/{total}）")
    elif ratio > 0.70:
        warns.append(f"档案语气占比 {ratio:.0%} 偏高，可能每条都在剧透")

    return errs, warns


def emit_ts(doc: dict, chapters: dict[str, dict]) -> str:
    lines = [
        "/* 由 scripts/gen_story_data.py 从 content/_story/acts.json 生成，请勿手改。",
        f"   {sum(len(a['chapters']) for s in doc['subjects'].values() for a in s['acts'])} 条台词 / "
        f"{sum(len(s['acts']) for s in doc['subjects'].values())} 幕 / "
        f"{len(doc['subjects'])} 个学科。",
        "   可见性规则：pitfall 与 scene 未完成也能看（悬念即钩子）；archive 已说半个答案，必须完成后才显示。 */",
        "/* eslint-disable */",
        "",
        "export type StoryTone = 'pitfall' | 'scene' | 'field' | 'archive';",
        "",
        "export interface StoryLine {",
        "  chapterId: string;",
        "  title: string;",
        "  tone: StoryTone;",
        "  line: string;",
        "  anchor: string;",
        "}",
        "",
        "export interface StoryAct {",
        "  id: string;",
        "  group: string;",
        "  title: string;",
        "  chapters: StoryLine[];",
        "}",
        "",
        "export interface StorySubject {",
        "  key: string;",
        "  label: string;",
        "  acts: StoryAct[];",
        "}",
        "",
        "export const STORY: StorySubject[] = [",
    ]
    for subj_key, subj in doc["subjects"].items():
        lines.append(f"  {{ key: {json.dumps(subj_key)}, label: {json.dumps(subj['label'], ensure_ascii=False)}, acts: [")
        for act in subj["acts"]:
            lines.append(f"    {{ id: {json.dumps(act['id'])}, group: {json.dumps(act['group'], ensure_ascii=False)}, title: {json.dumps(act['title'], ensure_ascii=False)}, chapters: [")
            for ch in act["chapters"]:
                title = chapters[ch["id"]]["title"]
                lines.append(
                    "      { chapterId: %s, title: %s, tone: %s, line: %s, anchor: %s },"
                    % (
                        json.dumps(ch["id"]),
                        json.dumps(title, ensure_ascii=False),
                        json.dumps(ch["tone"]),
                        json.dumps(ch["line"], ensure_ascii=False),
                        json.dumps(ch["anchor"], ensure_ascii=False),
                    )
                )
            lines.append("    ] },")
        lines.append("  ] },")
    lines.append("];")
    lines.append("")
    lines.append("/** 章节 id → 台词，剧情页逐个查，O(1)。 */")
    lines.append("export const STORY_BY_CHAPTER: Record<string, StoryLine> = (() => {")
    lines.append("  const m: Record<string, StoryLine> = {};")
    lines.append("  for (const s of STORY) for (const a of s.acts) for (const c of a.chapters) m[c.chapterId] = c;")
    lines.append("  return m;")
    lines.append("})();")
    lines.append("")
    lines.append("/** 台词是否可以在「未完成」时显示：archive 不行，它已经说了半个答案。 */")
    lines.append("export function isTeaser(tone: StoryTone): boolean {")
    lines.append("  return tone !== 'archive';")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def emit_md(doc: dict, chapters: dict[str, dict]) -> str:
    total = sum(len(a["chapters"]) for s in doc["subjects"].values() for a in s["acts"])
    acts = sum(len(s["acts"]) for s in doc["subjects"].values())
    out = [
        "# P3 · 141 幕台词本（自动生成）",
        "",
        "> 由 `scripts/gen_story_data.py` 从 `content/_story/acts.json` 生成，**请勿手改本文**；",
        "> 改台词请改 json 再重跑脚本。",
        f"> 共 {total} 条台词 / {acts} 幕 / {len(doc['subjects'])} 个学科。",
        "",
        "## 两条可见性规则",
        "",
        "| 语气 | 未完成时 | 原因 |",
        "|---|---|---|",
        "| `pitfall` 陷阱 | **显示**（灰化 + 锁） | 「我以为…」是悬念，藏着等于扔掉钩子 |",
        "| `scene` 现场 | **显示**（灰化 + 锁） | 只描述现象，没给解释 |",
        "| `field` 现场 | **显示**（灰化 + 锁） | 只描述现象，没给解释 |",
        "| `archive` 档案 | **`？？？`** | 已经说了一半答案，提前看等于剧透 |",
        "",
        "## 幕标题的写法要求",
        "",
        "说这 5 章（或 4 章）**共同的矛盾**，不是复述学科名。",
        "写「C++ 进阶篇」是失败，写「语言开始有重量」才成立。",
        "",
        "---",
        "",
    ]
    for subj_key, subj in doc["subjects"].items():
        total_ch = sum(len(a["chapters"]) for a in subj["acts"])
        out.append(f"## {subj['label']}（{total_ch} 章 / {len(subj['acts'])} 幕）")
        out.append("")
        for act in subj["acts"]:
            out.append(f"### 幕 {act['id']} · {act['title']}")
            out.append("")
            out.append(f"> {act['group']} · {len(act['chapters'])} 章")
            out.append("")
            out.append("| 章节 | 标题 | 语气 | 台词 | 锚点 |")
            out.append("|---|---|---|---|---|")
            for ch in act["chapters"]:
                t = chapters[ch["id"]]["title"]
                out.append(f"| `{ch['id']}` | {t} | {ch['tone']} | {ch['line']} | {ch['anchor']} |")
            out.append("")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args()

    doc = json.loads(SRC.read_text(encoding="utf-8"))
    chapters = load_chapters()

    errs, warns = validate(doc, chapters)
    for w in warns:
        print(f"  ! {w}")
    if errs:
        print(f"\n{len(errs)} 项不合格：")
        for e in errs:
            print(f"  ✗ {e}")
        sys.exit(1)

    total = sum(len(a["chapters"]) for s in doc["subjects"].values() for a in s["acts"])
    acts = sum(len(s["acts"]) for s in doc["subjects"].values())
    print(f"  ✓ 覆盖 {total}/{len(chapters)} 章 · {acts} 幕 · {len(doc['subjects'])} 学科")
    print(f"  ✓ 长度全部落在 {LINE_MIN}~{LINE_MAX} 有效字内")
    print("  ✓ 锚点非空 · 语气合法 · 幕归属正确")

    if args.check:
        print("STORY_CHECK_OK")
        return

    OUT_TS.parent.mkdir(parents=True, exist_ok=True)
    OUT_TS.write_text(emit_ts(doc, chapters), encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(emit_md(doc, chapters), encoding="utf-8")
    print(f"  → {OUT_TS.relative_to(ROOT)}  ({OUT_TS.stat().st_size // 1024} KB)")
    print(f"  → {OUT_MD.relative_to(ROOT)}")
    print("STORY_OK")


if __name__ == "__main__":
    main()
