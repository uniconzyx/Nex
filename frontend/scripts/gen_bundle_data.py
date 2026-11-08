#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 content/ 下的真实数据打包成前端可直接 import 的 TS 模块。

为什么要打包而不是运行时 fetch：
- .exe / .apk 是离线客户端，用户不可能先起一个 FastAPI + PostgreSQL 才能看到内容；
- Tauri 的 asset 协议下 fetch 本地 JSON 在 Android WebView 里路径行为不一致；
- 打包后桌面端与手机端读的是同一份常量，从根上保证「功能内容一样」。

数据源（勿手改产物）：
  content/_projects/career-projects.json   → PROJECTS / PLAN
  content/<subject>/_manifest.json         → CHAPTERS
  content/_guides/11408.json               → GUIDES

用法：python scripts/gen_bundle_data.py

注意：本文件只做生成链的第 ① 步，产物还要经过
    scripts/merge_agent_ml_into_ai.py --apply   （agent/ml 并入 ai）
    scripts/sync_bundle_chapters.py --write    （补新章节 / 新学科包，幂等）
才是最终形态；单独重跑本脚本会把合并打回三包。详见 CONTRIBUTING §10.2。
"""
from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # CppMind/
OUT = Path(__file__).resolve().parents[1] / "src" / "data" / "bundle.ts"

TRACK_LABEL = {
    "clang": "C 语言",
    "cpp": "C / C++",
    "java": "Java",
    "spring": "Spring 生态",
    "python": "Python",
    "fullstack": "全栈开发",
    "database": "数据库",
    "middleware": "中间件",
    "ai": "AI / Agent",
    "bigdata": "大数据",
    "data": "数据分析",
    "fundamentals": "计算机基础",
    "tooling": "工具链",
}
TIER_LABEL = {"t1": "能跑起来", "t2": "能独立写", "t3": "能讲原理", "t4": "能进简历"}
TIER_HINT = {
    "t1": "4-12h · 跑通并改一处小功能",
    "t2": "12-30h · 脱教程做同构小系统",
    "t3": "30-60h · 读源码 + 改造 + 压测",
    "t4": "60-120h · 可量化结果 + 个人贡献边界",
}

# 产物里的类型定义：用显式接口而不是 as const，
# 否则下游 filter/map 会被字面量元组类型卡死（TS2345 / TS2339）。
TS_TYPES = """export interface BundleProject {
  slug: string;
  track: string;
  tier: 't1' | 't2' | 't3' | 't4';
  hours: number;
  title: string;
  repo: string;
  url: string;
  summary: string;
  stack: string[];
  learn: string[];
  career: string;
  steps: string[];
  accept: string[];
  interview: string[];
  stars: number;
  lang: string;
  license: string;
  pushed: string;
  archived: boolean;
}

export interface BundleTrack {
  key: string;
  label: string;
  n: number;
  hours: number;
  tiers: Record<string, number>;
}

export interface BundleTier {
  key: 't1' | 't2' | 't3' | 't4';
  label: string;
  hint: string;
  min_hours: number | null;
  max_hours: number | null;
}

export interface BundleChapter {
  id: string;
  order: number;
  group: string;
  title: string;
  summary: string;
  status: string;
  prerequisites: string[];
  github: string[];
  github_stars: number[];
  books: string[];
}

export interface BundleChapterPack {
  title: string;
  groups: Record<string, string>;
  chapters: BundleChapter[];
}

export interface BundleGuideItem {
  slug: string;
  kind: 'note' | 'experience' | 'external';
  subject: string;
  title: string;
  summary: string;
  points: string[];
  url: string | null;
  read_min: number;
  recommended: boolean;
}

export interface Bundle {
  projects: {
    tracks: BundleTrack[];
    tiers: BundleTier[];
    items: BundleProject[];
    total: number;
    hours: number;
    graduation: Record<string, unknown>;
  };
  chapters: Record<string, BundleChapterPack>;
  guides: {
    source: {
      key: string;
      title: string;
      repo: string | null;
      url: string | null;
      license: string | null;
      stars: number;
      note: string;
    };
    items: BundleGuideItem[];
  };
}

"""


def _s(x: object) -> str:
    """压成单行，避免 TS 模板里出现裸换行。"""
    return re.sub(r"\s+", " ", str(x or "")).strip()


def load_projects() -> dict:
    src = json.loads((ROOT / "content/_projects/career-projects.json").read_text(encoding="utf-8"))
    items = []
    for it in src["items"]:
        meta = it.get("meta") or {}
        items.append(
            {
                "slug": it["slug"],
                "track": it["track"],
                "tier": it["tier"],
                "hours": it["hours"],
                "title": _s(it["title"]),
                "repo": it["repo"],
                "url": meta.get("repo_url") or f"https://github.com/{it['repo']}",
                "summary": _s(it["summary"]),
                "stack": it.get("stack") or [],
                "learn": [_s(x) for x in (it.get("learn") or [])],
                "career": _s(it.get("career")),
                "steps": [_s(x) for x in (it.get("steps") or [])],
                "accept": [_s(x) for x in (it.get("accept") or [])],
                "interview": [_s(x) for x in (it.get("interview") or [])],
                "stars": meta.get("stars") or 0,
                "lang": meta.get("language") or "",
                "license": meta.get("license") or "",
                "pushed": meta.get("pushed") or "",
                "archived": bool(meta.get("archived")),
            }
        )
    order = {t: i for i, t in enumerate(src["tracks"])}
    items.sort(key=lambda x: (order.get(x["track"], 99), x["tier"], -x["stars"]))
    tracks = []
    for t in src["tracks"]:
        sub = [i for i in items if i["track"] == t]
        tracks.append(
            {
                "key": t,
                "label": TRACK_LABEL.get(t, t),
                "n": len(sub),
                "hours": sum(i["hours"] for i in sub),
                "tiers": {k: sum(1 for i in sub if i["tier"] == k) for k in ("t1", "t2", "t3", "t4")},
            }
        )
    tiers = [
        {
            "key": t["key"],
            "label": TIER_LABEL[t["key"]],
            "hint": TIER_HINT[t["key"]],
            "min_hours": t.get("min_hours"),
            "max_hours": t.get("max_hours"),
        }
        for t in src["tiers"]
    ]
    return {
        "tracks": tracks,
        "tiers": tiers,
        "items": items,
        "total": len(items),
        "hours": sum(i["hours"] for i in items),
        "graduation": src.get("graduation") or {},
    }


def load_chapters() -> dict:
    """按学科读 _manifest.json，只保留 UI 需要的字段（不搬正文）。"""
    out: dict[str, dict] = {}
    for path in sorted((ROOT / "content").glob("*/_manifest.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        subject = d.get("subject") or path.parent.name
        chapters = []
        for c in d.get("chapters") or []:
            res = c.get("resources") or {}
            chapters.append(
                {
                    "id": c["id"],
                    "order": c.get("order") or 0,
                    "group": c.get("group") or "",
                    "title": _s(c.get("title")),
                    "summary": _s(c.get("summary")),
                    "status": c.get("status") or "draft",
                    "prerequisites": c.get("prerequisites") or [],
                    "github": (res.get("github") or [])[:3],
                    "github_stars": (res.get("github_stars") or [])[:3],
                    "books": (res.get("books") or [])[:2],
                }
            )
        chapters.sort(key=lambda x: x["order"])
        out[subject] = {
            "title": _s(d.get("title")),
            "groups": d.get("groups") or {},
            "chapters": chapters,
        }
    return out


def load_guides() -> dict:
    d = json.loads((ROOT / "content/_guides/11408.json").read_text(encoding="utf-8"))
    src = d.get("source") or {}
    return {
        "source": {
            "key": src.get("key") or "11408",
            "title": _s(src.get("title")),
            "repo": src.get("repo"),
            "url": src.get("repo_url") or src.get("url"),
            "license": src.get("license"),
            "stars": src.get("stars") or 0,
            "note": _s(src.get("note")),
        },
        "items": [
            {
                "slug": it["slug"],
                "kind": it["kind"],
                "subject": it["subject"],
                "title": _s(it["title"]),
                "summary": _s(it.get("summary")),
                "points": [_s(x) for x in (it.get("points") or [])],
                "url": it.get("url"),
                "read_min": it.get("read_min") or 0,
                "recommended": bool(it.get("recommended")),
            }
            for it in (d.get("items") or [])
        ],
    }


def main() -> None:
    projects = load_projects()
    chapters = load_chapters()
    guides = load_guides()
    doc = {"projects": projects, "chapters": chapters, "guides": guides}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    header = (
        "/* 由 scripts/gen_bundle_data.py 从 content/ 生成，请勿手改。\n"
        f"   项目 {projects['total']} 条 / {projects['hours']}h；"
        f"章节学科 {len(chapters)} 个；指南 {len(guides['items'])} 条。 */\n\n"
        "/* eslint-disable */\n"
        + TS_TYPES
    )
    body = "export const BUNDLE = " + payload + " as unknown as Bundle;\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(header + body)
    print(
        f"wrote {OUT.relative_to(ROOT)} "
        f"{OUT.stat().st_size / 1024:.0f} KB | projects={projects['total']} "
        f"chapters={sum(len(v['chapters']) for v in chapters.values())} "
        f"guides={len(guides['items'])}"
    )


if __name__ == "__main__":
    main()
