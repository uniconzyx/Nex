# -*- coding: utf-8 -*-
"""把分学科的内容分片 + GitHub 检索到的真实元数据，合并成 career-projects.json。

为什么分片：
    110 个项目的正文一次性维护在一个文件里既难写也难审。按学科拆成
    content/_projects/career/<track>.json，每片只放人写的内容（summary/learn/steps…），
    元数据（stars/license/pushed…）由脚本从 .scratch/gh_discover 回填，避免手工抄错、
    也避免随时间漂移。

用法：
    python -m scripts.build_career_library            # 构建
    python -m scripts.build_career_library --check    # 只校验，不写文件
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PIECES = ROOT / "content" / "_projects" / "career"
DISCOVER = ROOT.parent / ".scratch" / "gh_discover"
OUT = ROOT / "content" / "_projects" / "career-projects.json"
PLAN = ROOT / "content" / "_projects" / "career-plan.json"

TRACK_ORDER = [
    "clang", "cpp", "java", "spring", "python", "fullstack", "database",
    "middleware", "ai", "bigdata", "data", "fundamentals", "tooling",
]
TIERS = ("t1", "t2", "t3", "t4")


def load_meta() -> dict[str, dict]:
    """repo(full_name 小写) → 元数据。

    两级来源：
      1. .scratch/gh_discover/*.json —— 本轮按学科检索的实测结果；
      2. 旧版 career-projects.json —— 首轮逐仓验真的结果，补齐检索未覆盖的仓库。
    同一仓库两边都有时用检索结果（更新）。
    """
    meta: dict[str, dict] = {}

    legacy = ROOT / "content" / "_projects" / "career-projects.json"
    if legacy.exists():
        try:
            for it in json.loads(legacy.read_text(encoding="utf-8")).get("items", []):
                m = it.get("meta") or {}
                if m.get("repo_url"):
                    meta[(it.get("repo") or "").lower()] = {
                        "full_name": it["repo"],
                        "repo_url": m.get("repo_url"),
                        "stars": m.get("stars", 0),
                        "forks": m.get("forks", 0),
                        "language": m.get("language"),
                        "license": m.get("license"),
                        "pushed": m.get("pushed"),
                        "size_kb": m.get("size_kb", 0),
                        "archived": m.get("archived", False),
                        "desc": m.get("desc", ""),
                        "topics": m.get("topics", []),
                        "open_issues": m.get("open_issues", 0),
                    }
        except Exception:  # noqa: BLE001
            pass

    if not DISCOVER.exists():
        return meta
    for f in DISCOVER.glob("*.json"):
        for it in json.loads(f.read_text(encoding="utf-8")):
            meta[it["full_name"].lower()] = it
    return meta


def load_pieces() -> tuple[list[dict], list[str]]:
    items: list[dict] = []
    errors: list[str] = []
    for f in sorted(PIECES.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        arr = data["items"] if isinstance(data, dict) else data
        for it in arr:
            it["_file"] = f.name
            items.append(it)
    return items, errors


def validate(items: list[dict], meta: dict[str, dict], plan: dict) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for it in items:
        slug = it.get("slug", "")
        src = it.get("_file", "?")
        if not slug:
            errs.append(f"{src}: 缺 slug")
        elif slug in seen:
            errs.append(f"{slug}: slug 重复")
        seen.add(slug)

        if it.get("track") not in TRACK_ORDER:
            errs.append(f"{slug}: track 非法 {it.get('track')!r}")
        if it.get("tier") not in TIERS:
            errs.append(f"{slug}: tier 非法 {it.get('tier')!r}")
        if it.get("level") not in ("easy", "mid", "hard"):
            errs.append(f"{slug}: level 非法 {it.get('level')!r}")
        if not isinstance(it.get("hours"), int) or not (1 <= it["hours"] <= 200):
            errs.append(f"{slug}: hours 非法 {it.get('hours')!r}")

        for key, low in (("learn", 3), ("steps", 3), ("accept", 3), ("interview", 2)):
            v = it.get(key) or []
            if len(v) < low:
                errs.append(f"{slug}: {key} 少于 {low} 条（现 {len(v)}）")

        repo = (it.get("repo") or "").lower()
        if not repo:
            errs.append(f"{slug}: 缺 repo")
        elif repo not in meta:
            errs.append(f"{slug}: repo {it.get('repo')} 不在检索结果里（先跑 gh_discover）")

    # 梯度覆盖：每个学科必须 t1-t4 齐全（fundamentals/tooling 允许无 t4）
    if plan:
        bp = plan.get("track_blueprint") or {}
        for track, spec in bp.items():
            got = {i["tier"] for i in items if i.get("track") == track}
            for t in TIERS:
                want = int(spec.get(t) or 0)
                if want > 0 and t not in got:
                    errs.append(f"{track}: 规划要 {t} × {want}，实际 0")
    return errs


def build(write: bool = True) -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8")) if PLAN.exists() else {}
    meta = load_meta()
    items, _ = load_pieces()

    errs = validate(items, meta, plan)

    # 按学科顺序 + 梯度顺序稳定排序
    def sort_key(it: dict):
        return (
            TRACK_ORDER.index(it["track"]) if it["track"] in TRACK_ORDER else 99,
            TIERS.index(it["tier"]) if it["tier"] in TIERS else 99,
            it["slug"],
        )

    items.sort(key=sort_key)

    missing_meta = sum(1 for it in items if (it.get("repo") or "").lower() not in meta)
    print(f"分片 {len(list(PIECES.glob('*.json')))} 个 / 条目 {len(items)} / 元数据缺失 {missing_meta}")
    for track in TRACK_ORDER:
        sub = [i for i in items if i.get("track") == track]
        if not sub:
            continue
        dist = {t: sum(1 for i in sub if i["tier"] == t) for t in TIERS}
        print(f"  {track:13s} {len(sub):>3}  t1={dist['t1']} t2={dist['t2']} t3={dist['t3']} t4={dist['t4']}  {sum(i['hours'] for i in sub)}h")

    if errs:
        print(f"\n校验失败 {len(errs)} 条：")
        for e in errs[:40]:
            print("  -", e)
        if len(errs) > 40:
            print(f"  ... 另有 {len(errs) - 40} 条")
        return 1

    if not write:
        print("\ncheck OK（未写文件）")
        return 0

    out_items = []
    for idx, it in enumerate(items):
        m = meta.get((it.get("repo") or "").lower(), {})
        out_items.append({
            "slug": it["slug"],
            "track": it["track"],
            "title": it["title"],
            "repo": m.get("full_name") or it["repo"],
            "tier": it["tier"],
            "hours": it["hours"],
            "level": it["level"],
            "summary": it["summary"],
            "stack": it["stack"],
            "learn": it["learn"],
            "career": it["career"],
            "steps": it["steps"],
            "accept": it["accept"],
            "interview": it["interview"],
            "meta": {
                "repo_url": m.get("repo_url") or f"https://github.com/{it['repo']}",
                "stars": m.get("stars", 0),
                "forks": m.get("forks", 0),
                "language": m.get("language"),
                "license": m.get("license"),
                "pushed": m.get("pushed"),
                "size_kb": m.get("size_kb", 0),
                "archived": m.get("archived", False),
                "desc": m.get("desc", ""),
                "topics": m.get("topics", []),
                "open_issues": m.get("open_issues", 0),
            },
        })

    doc = {
        "version": 3,
        "note": "由 scripts/build_career_library 从 content/_projects/career/*.json 合并生成，"
                "元数据来自 GitHub 检索实测（.scratch/gh_discover），请勿手改本文件。",
        "tracks": [t for t in TRACK_ORDER if any(i["track"] == t for i in out_items)],
        "tiers": plan.get("tiers") or [],
        "graduation": plan.get("graduation") or {},
        "routes": plan.get("routes") or [],
        "items": out_items,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n写入 {OUT}  ({len(out_items)} 条, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sys.exit(build(write=not a.check))
