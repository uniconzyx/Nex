#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成设计稿用的真实内容数据（章节 + 考研手札）。

设计稿是 file:// 直接打开，fetch 本地 JSON 会被 CORS 拦，所以打成 window 全局量。

用法：python web-preview/kaimao_content_data.py
产物：web-preview/assets/content-data.js
"""
from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # CppMind/
OUT = Path(__file__).resolve().parent / "assets" / "content-data.js"

SUBJECTS = [
    ("cpp", "C / C++", "C++"),
    ("clang", "C 语言", "C"),
    ("java", "Java", "Java"),
    ("spring", "Spring 生态", "Spring"),
    ("python", "Python", "Python"),
    ("fullstack", "全栈开发", "全栈"),
    ("database", "数据库", "数据库"),
    ("middleware", "中间件", "中间件"),
    ("ai", "AI / Agent 开发", "AI"),
    ("bigdata", "大数据", "大数据"),
    ("data", "数据分析", "数据分析"),
    ("fundamentals", "计算机基础", "基础"),
    ("tooling", "工具链", "工具链"),
]

GUIDE_SUBJECT = {
    "cs408": "408 计算机",
    "math": "数学",
    "english": "英语",
    "politics": "政治",
    "mindset": "心态",
    "general": "通用",
}


def one_line(x: object) -> str:
    return re.sub(r"\s+", " ", str(x or "")).strip()


def build() -> dict:
    subjects = []
    total = 0
    for key, label, short in SUBJECTS:
        p = ROOT / "content" / key / "_manifest.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        chapters = []
        for c in sorted(d.get("chapters") or [], key=lambda x: x.get("order") or 0):
            res = c.get("resources") or {}
            chapters.append(
                {
                    "id": c["id"],
                    "order": c.get("order") or 0,
                    "group": c.get("group") or "",
                    "title": one_line(c.get("title")),
                    "summary": one_line(c.get("summary")),
                    "status": c.get("status") or "draft",
                    "prereq": c.get("prerequisites") or [],
                    "github": (res.get("github") or [])[:3],
                    "stars": (res.get("github_stars") or [])[:3],
                    "books": (res.get("books") or [])[:2],
                }
            )
        total += len(chapters)
        subjects.append(
            {
                "key": key,
                "label": label,
                "short": short,
                "groups": d.get("groups") or {},
                "chapters": chapters,
            }
        )

    g = json.loads((ROOT / "content/_guides/11408.json").read_text(encoding="utf-8"))
    guides = [
        {
            "slug": it["slug"],
            "kind": it["kind"],
            "subject": GUIDE_SUBJECT.get(it["subject"], it["subject"]),
            "title": one_line(it["title"]),
            "summary": one_line(it.get("summary")),
            "points": [one_line(x) for x in (it.get("points") or [])],
            "url": it.get("url"),
            "read": it.get("read_min") or 0,
            "rec": bool(it.get("recommended")),
        }
        for it in (g.get("items") or [])
    ]

    return {
        "subjects": subjects,
        "total": total,
        "guides": {
            "source": {
                "key": "11408",
                "title": one_line((g.get("source") or {}).get("title")),
                "repo": (g.get("source") or {}).get("repo"),
                "url": (g.get("source") or {}).get("repo_url"),
                "license": (g.get("source") or {}).get("license"),
                "stars": (g.get("source") or {}).get("stars") or 0,
            },
            "items": guides,
        },
    }


def main() -> None:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        "/* 真实内容数据（由 web-preview/kaimao_content_data.py 生成，勿手改）\n"
        f"   {len(doc['subjects'])} 学科 / {doc['total']} 章 / {len(doc['guides']['items'])} 条手札 */\n"
        "window.NEX_CONTENT=" + json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )
    print(
        f"wrote {OUT.relative_to(ROOT)} {OUT.stat().st_size / 1024:.0f} KB | "
        f"subjects={len(doc['subjects'])} chapters={doc['total']} guides={len(doc['guides']['items'])}"
    )


if __name__ == "__main__":
    main()
