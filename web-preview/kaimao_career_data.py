"""把后端项目库 JSON 转成桌面端设计稿可直接 <script src> 的数据文件。

源：CppMind/content/_projects/career-projects.json（由 server/scripts/build_career_library.py 生成）
出：CppMind/web-preview/assets/career-data.js（window.NEX_CAREER）

设计稿是 file:// 直接打开的，不能 fetch JSON，所以打成一个 JS 全局变量。
用法：python web-preview/kaimao_career_data.py
"""

from __future__ import annotations

import collections
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "_projects" / "career-projects.json"
OUT = ROOT / "web-preview" / "assets" / "career-data.js"

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


def main() -> None:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    items = []
    for it in src["items"]:
        m = it.get("meta") or {}
        items.append(
            {
                "slug": it["slug"],
                "track": it["track"],
                "tier": it["tier"],
                "hours": it["hours"],
                "title": it["title"],
                "repo": it["repo"],
                "summary": it["summary"],
                "stack": it["stack"],
                "learn": it["learn"],
                "career": it["career"],
                "steps": it["steps"],
                "accept": it["accept"],
                "interview": it["interview"],
                "stars": m.get("stars") or 0,
                "lang": m.get("language") or "",
                "license": m.get("license") or "",
                "pushed": m.get("pushed") or "",
                "url": m.get("repo_url") or ("https://github.com/" + it["repo"]),
                "archived": bool(m.get("archived")),
            }
        )

    order = {t: i for i, t in enumerate(src["tracks"])}
    items.sort(key=lambda x: (order[x["track"]], x["tier"], -x["stars"]))

    tracks = []
    for t in src["tracks"]:
        sub = [i for i in items if i["track"] == t]
        tracks.append(
            {
                "key": t,
                "label": TRACK_LABEL[t],
                "n": len(sub),
                "hours": sum(i["hours"] for i in sub),
                "tiers": dict(collections.Counter(i["tier"] for i in sub)),
            }
        )

    doc = {
        "tracks": tracks,
        "tiers": [{**t, "label": TIER_LABEL[t["key"]]} for t in src["tiers"]],
        "items": items,
        "total": len(items),
        "hours": sum(i["hours"] for i in items),
        "graduation": src.get("graduation", {}),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* 就业级项目库数据（由 content/_projects/career-projects.json 生成，勿手改）\n")
        f.write(f"   13 学科 / {doc['total']} 个项目 / {doc['hours']}h；元数据来自 GitHub 实测。 */\n")
        f.write("window.NEX_CAREER=" + json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.relative_to(ROOT)} · {doc['total']} items · {doc['hours']}h")


if __name__ == "__main__":
    main()
