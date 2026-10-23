# -*- coding: utf-8 -*-
"""把 GitHub API 实测元数据回填进 career-projects.json，并做结构校验。

用法：
    python -m scripts.merge_career_meta --verified .scratch/gh_verified.json

设计意图：
  - 人写的部分是「教学拆解」（学什么、怎么复现、面试怎么讲）；
  - 机器写的部分是「事实」（star/语言/许可证/最近提交）。
  两者分离，避免手抄数字漂移。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "content" / "_projects" / "career-projects.json"

REQUIRED = ["title", "repo", "level", "summary", "stack", "learn",
            "career", "steps", "accept", "interview"]
LEVELS = {"easy", "mid", "hard"}


def load_verified(path: Path) -> dict[str, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    flat: dict[str, dict] = {}
    for _track, repos in raw.items():
        for r in repos:
            flat[r["full_name"].lower()] = r
    return flat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verified", required=True, help="gh_verified.json 路径")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    verified = load_verified(Path(args.verified))
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    tracks: dict[str, str] = doc["tracks"]
    items: list[dict] = doc["items"]

    errors: list[str] = []
    seen_slug: set[str] = set()
    missing_meta: list[str] = []

    for it in items:
        slug = it.get("slug", "")
        if not slug:
            errors.append("存在缺少 slug 的条目")
            continue
        if slug in seen_slug:
            errors.append(f"slug 重复: {slug}")
        seen_slug.add(slug)

        for k in REQUIRED:
            if not it.get(k):
                errors.append(f"{slug}: 缺少字段 {k}")
        if it.get("level") not in LEVELS:
            errors.append(f"{slug}: level 非法 {it.get('level')}")
        if it.get("track") not in tracks:
            errors.append(f"{slug}: track 未在 tracks 中登记 {it.get('track')}")

        meta = verified.get(it["repo"].lower())
        if meta is None:
            missing_meta.append(it["repo"])
            continue
        it["meta"] = {
            "repo_url": meta["url"],
            "stars": meta["stars"],
            "forks": meta["forks"],
            "language": meta["language"],
            "license": meta["license"],
            "pushed": meta["pushed"],
            "size_kb": meta["size_kb"],
            "archived": meta["archived"],
            "desc": meta["desc"],
            "topics": meta["topics"],
            "open_issues": meta["open_issues"],
        }

    # 每学科至少 2 个项目，保证「各学科都覆盖」
    per_track: dict[str, int] = {}
    for it in items:
        per_track[it["track"]] = per_track.get(it["track"], 0) + 1
    for code, name in tracks.items():
        if per_track.get(code, 0) < 2:
            errors.append(f"学科 {code}({name}) 项目数不足 2，当前 {per_track.get(code, 0)}")

    if missing_meta:
        errors.append("以下 repo 未在实测数据中找到: " + ", ".join(missing_meta))

    print(f"条目 {len(items)} / 学科 {len(tracks)}")
    print("每学科分布:")
    for code, name in tracks.items():
        print(f"  {code:13s} {name:12s} {per_track.get(code, 0)}")

    if errors:
        print("\n校验失败:")
        for e in errors:
            print("  -", e)
        return 1

    if not args.check_only:
        DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n已回填元数据 ->", DATA)
    else:
        print("\n校验通过（未写盘）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
