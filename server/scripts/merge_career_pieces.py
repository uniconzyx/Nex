# -*- coding: utf-8 -*-
"""把一批增量条目合并进 content/_projects/career/<track>.json 分片。

用法：
    python -m scripts.merge_career_pieces ../.scratch/add_*.json
    python -m scripts.merge_career_pieces --dry-run ../.scratch/add_java.json

规则：
    * 以 slug 为唯一键，已存在则跳过（不覆盖人工修改过的正文）；
    * 条目的 track 必须与目标分片一致；
    * 合并后按 tier + slug 排序，保持文件 diff 稳定。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PIECES = ROOT / "content" / "_projects" / "career"
TIERS = ("t1", "t2", "t3", "t4")


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    arr = data["items"] if isinstance(data, dict) else data
    if not isinstance(arr, list):
        raise SystemExit(f"{path}: 结构不认识")
    return arr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="增量 JSON（支持通配符）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    paths: list[Path] = []
    for pattern in a.files:
        if any(ch in pattern for ch in "*?["):
            paths.extend(Path(p) for p in glob.glob(pattern))
        else:
            paths.append(Path(pattern))

    buckets: dict[str, list[dict]] = {}
    for p in paths:
        for it in load(p):
            track = it.get("track")
            if not track:
                raise SystemExit(f"{p}: 条目 {it.get('slug')} 缺 track")
            if it.get("tier") not in TIERS:
                raise SystemExit(f"{p}: {it.get('slug')} tier 非法")
            buckets.setdefault(track, []).append(it)

    total_added = 0
    for track, new_items in sorted(buckets.items()):
        target = PIECES / f"{track}.json"
        doc = {"track": track, "items": []}
        if target.exists():
            doc = json.loads(target.read_text(encoding="utf-8"))
        existing = {x["slug"] for x in doc["items"]}
        added, skipped = [], []
        for it in new_items:
            if it["slug"] in existing:
                skipped.append(it["slug"])
                continue
            doc["items"].append(it)
            existing.add(it["slug"])
            added.append(it["slug"])
        doc["items"].sort(key=lambda x: (TIERS.index(x["tier"]), x["slug"]))
        dist = Counter(x["tier"] for x in doc["items"])
        print(f"{track:13s} +{len(added):>2}  跳过 {len(skipped):>2}  "
              f"合计 {len(doc['items']):>2}  "
              + " ".join(f"{t}={dist.get(t, 0)}" for t in TIERS))
        total_added += len(added)
        if not a.dry_run:
            target.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\n共新增 {total_added} 条{'（dry-run 未写盘）' if a.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
