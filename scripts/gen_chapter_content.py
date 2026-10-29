#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 content/<学科>/<章节>/ 抽取章节正文切片，生成 frontend/src/data/chapterContent.ts。

用途：P2 单章总结表（7 维）的「目标/概念/易错/面试/项目」维度需要章节正文，
而 BUNDLE 只带章节元数据（标题/摘要/前置/github），不带正文。本脚本把正文切片
打进前端可 import 的 TS 文件，使 chapterSummary.ts 能产出真实的 7 维表。

切片口径（轻量、与 validate_content.py 同构）：
  - goals:      goals.md 的条目行（# / - / * / 数字. 起头）
  - pitfalls:   pitfalls.md 的条目行
  - concepts:   concept/*.md 的首个标题（# 行）或文件名
  - interviews: interview.json items[].question
  - projects:   project.json items[].title

幂等；纯生成，不回写 content。改 content 后重跑本脚本即可。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "frontend" / "src" / "data" / "chapterContent.ts"

CAP = 15  # 每维度最多切片条数，避免 bundle 过大


def parse_items(md_text: str) -> list[str]:
    out: list[str] = []
    for line in md_text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(#{1,6}\s+|[-*]\s+|\d+[.、]\s+)(.*)$", s)
        if not m:
            continue
        text = re.sub(r"[*`_>#]", "", m.group(2)).strip()
        if text and len(text) <= 80:
            out.append(text)
    return out


def first_heading(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line.strip())
        if m:
            t = re.sub(r"[*`_>#]", "", m.group(1)).strip()
            if t:
                return t
    return fallback


def main() -> None:
    chapters: dict[str, dict] = {}
    for ch_dir in sorted(CONTENT.glob("*/*")):
        if not ch_dir.is_dir():
            continue
        subject = ch_dir.parent.name
        cid = ch_dir.name
        if not (ch_dir / "goals.md").exists() and not (ch_dir / "exercises.json").exists():
            continue  # 不是真章节目录

        goals = parse_items((ch_dir / "goals.md").read_text(encoding="utf-8")) if (ch_dir / "goals.md").exists() else []
        pitfalls = parse_items((ch_dir / "pitfalls.md").read_text(encoding="utf-8")) if (ch_dir / "pitfalls.md").exists() else []

        concepts: list[str] = []
        concept_dir = ch_dir / "concept"
        if concept_dir.is_dir():
            for cf in sorted(concept_dir.glob("*.md")):
                concepts.append(first_heading(cf.read_text(encoding="utf-8"), cf.stem))

        interviews: list[str] = []
        ij = ch_dir / "interview.json"
        if ij.exists():
            try:
                data = json.loads(ij.read_text(encoding="utf-8"))
                for it in data.get("items", []) or []:
                    q = it.get("question")
                    if q:
                        interviews.append(q)
            except Exception:
                pass

        projects: list[str] = []
        pj = ch_dir / "project.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                for it in data.get("items", []) or []:
                    t = it.get("title")
                    if t:
                        projects.append(t)
            except Exception:
                pass

        chapters[cid] = {
            "id": cid,
            "subject": subject,
            "title": cid,  # 运行时以 graph.chapterName 为准
            "goals": goals[:CAP],
            "pitfalls": pitfalls[:CAP],
            "concepts": concepts[:CAP],
            "interviews": interviews[:CAP],
            "projects": projects[:CAP],
        }

    lines = [
        "/* 由 scripts/gen_chapter_content.py 从 content/ 生成，请勿手改。",
        "   切片：goals/pitfalls 取条目行，concept 取首标题，interview/project 取问题/标题。",
        f"   章节数：{len(chapters)}。改 content 后请重跑 gen_chapter_content.py。 */",
        "/* eslint-disable */",
        "",
        "export interface ChapterContent {",
        "  id: string;",
        "  subject: string;",
        "  title: string;",
        "  goals: string[];",
        "  pitfalls: string[];",
        "  concepts: string[];",
        "  interviews: string[];",
        "  projects: string[];",
        "}",
        "",
        "export const CHAPTER_CONTENT: Record<string, ChapterContent> = {",
    ]
    for cid in sorted(chapters):
        c = chapters[cid]
        lines.append(f"  {json.dumps(cid)}: {{")
        lines.append(f"    id: {json.dumps(c['id'])},")
        lines.append(f"    subject: {json.dumps(c['subject'])},")
        lines.append(f"    title: {json.dumps(c['title'])},")
        lines.append(f"    goals: {json.dumps(c['goals'], ensure_ascii=False)},")
        lines.append(f"    pitfalls: {json.dumps(c['pitfalls'], ensure_ascii=False)},")
        lines.append(f"    concepts: {json.dumps(c['concepts'], ensure_ascii=False)},")
        lines.append(f"    interviews: {json.dumps(c['interviews'], ensure_ascii=False)},")
        lines.append(f"    projects: {json.dumps(c['projects'], ensure_ascii=False)},")
        lines.append("  },")
    lines.append("};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"写入 {OUT.relative_to(ROOT)}：{len(chapters)} 章")


if __name__ == "__main__":
    main()
