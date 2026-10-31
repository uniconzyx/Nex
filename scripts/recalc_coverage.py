"""重算 content/_coverage.json（原生成脚本已丢失，本脚本接管）。

为什么需要它
--------------------------------------------------------------------
`_coverage.json` 早已过期且**严重低估**当前内容：它记录 agent-ch01 的
`interview=0`、`project=0`，而磁盘上实际是 4 条面试题 + 1 个项目任务；
它还说 `total_chapters=136 / incomplete=6 / orphan_dirs=[ml-ch04, ml-ch08]`，
而磁盘上 ml-ch04/ch08 早已被 `ml/_manifest.json` 收录、7 类文件齐全。
过期的覆盖率会直接误导排期（"这章没做完，得补"），因此必须重算。

计数口径（写在脚本里，避免以后再出现"不知道数字怎么来的"）
--------------------------------------------------------------------
    goals       goals.md 存在 ? 1 : 0
    concept     concept/*.md 篇数
    pitfalls    pitfalls.md 里 `1.` `2.` 形式的顶层编号条目数
    exercises   exercises.json 的 items 数
    examples    examples/*.json 文件数
    interview   interview.json 的 items 数
    project     project.json 里 tasks/items/steps/milestones 的最大长度
    complete    七项全部 >= thresholds（沿用旧文件里的阈值）

保留策略
--------------------------------------------------------------------
旧文件里有些字段算不出来（tri_view 三视角明细、bagua 八卦图校验），
这些**原样保留**，只覆盖 present / passed / complete / issues 与顶层汇总，
避免把"重算"变成"删数据"。

用法
--------------------------------------------------------------------
    python scripts/recalc_coverage.py            # dry-run
    python scripts/recalc_coverage.py --apply    # 写回
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
COV = CONTENT / "_coverage.json"
BACKUP = CONTENT / "_backup_coverage"

SUBJECT_ORDER = [
    "cpp", "clang", "java", "spring", "python", "fullstack", "database",
    "middleware", "ai", "bigdata", "data", "fundamentals", "tooling", "agent", "ml",
]

NUM_ITEM = re.compile(r"^\s*\d+\.\s+\S", re.M)


def count_pitfalls(p: pathlib.Path) -> int:
    if not p.exists():
        return 0
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return 0
    n = len(NUM_ITEM.findall(txt))
    if n:
        return n
    # 退回：markdown 二级/三级标题当作条目
    return len(re.findall(r"^#{2,3}\s+\S", txt, re.M))


def count_project(p: pathlib.Path) -> int:
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return 0
    if not isinstance(d, dict):
        return 0
    best = 0
    for k in ("tasks", "items", "steps", "milestones", "deliverables"):
        v = d.get(k)
        if isinstance(v, list):
            best = max(best, len(v))
    return best or (1 if d else 0)


def count_items(p: pathlib.Path) -> int:
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return 0
    items = d.get("items") if isinstance(d, dict) else None
    return len(items) if isinstance(items, list) else 0


def scan_chapter(d: pathlib.Path) -> dict:
    concept = d / "concept"
    examples = d / "examples"
    present = {
        "goals": 1 if (d / "goals.md").exists() else 0,
        "concept": len(list(concept.glob("*.md"))) if concept.is_dir() else 0,
        "pitfalls": count_pitfalls(d / "pitfalls.md"),
        "exercises": count_items(d / "exercises.json"),
        "examples": len(list(examples.glob("*.json"))) if examples.is_dir() else 0,
        "interview": count_items(d / "interview.json"),
        "project": count_project(d / "project.json"),
    }
    return present


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    old = json.loads(COV.read_text(encoding="utf-8")) if COV.exists() else {}
    thresholds = old.get("thresholds") or {
        "goals": 1, "concept": 3, "pitfalls": 3, "exercises": 5,
        "examples": 10, "interview": 3, "project": 1,
    }
    old_by_id = {c.get("id"): c for c in (old.get("chapters") or []) if c.get("id")}

    rows: list[dict] = []
    for sub in SUBJECT_ORDER:
        sdir = CONTENT / sub
        if not sdir.is_dir():
            continue
        for d in sorted(p for p in sdir.iterdir() if p.is_dir() and not p.name.startswith("_")):
            cid = d.name
            present = scan_chapter(d)
            passed = {k: present.get(k, 0) >= thresholds.get(k, 1) for k in thresholds}
            issues = [
                f"{k} 不足：{present.get(k, 0)}/{thresholds[k]}"
                for k in thresholds
                if not passed[k]
            ]
            row = dict(old_by_id.get(cid) or {})
            row.update({
                "id": cid,
                "subject": sub,
                "complete": all(passed.values()),
                "present": present,
                "passed": passed,
                "issues": issues,
            })
            rows.append(row)

    # ---- manifest 对账 ----
    declared: dict[str, set[str]] = {}
    for sub in SUBJECT_ORDER:
        mp = CONTENT / sub / "_manifest.json"
        if not mp.exists():
            declared[sub] = set()
            continue
        try:
            m = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            declared[sub] = set()
            continue
        declared[sub] = {c.get("id") for c in (m.get("chapters") or []) if c.get("id")}

    disk_ids = {r["id"] for r in rows}
    missing_units, orphan_dirs = [], []
    for sub, ids in declared.items():
        for cid in sorted(ids):
            if cid not in disk_ids:
                missing_units.append({"subject": sub, "id": cid})
    for r in rows:
        if declared.get(r["subject"]) and r["id"] not in declared[r["subject"]]:
            orphan_dirs.append({"subject": r["subject"], "id": r["id"], "kind": "orphan"})

    planned_total = sum(len(v) for v in declared.values())
    complete = sum(1 for r in rows if r["complete"])

    new = dict(old)
    new.update({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_by": "scripts/recalc_coverage.py",
        "total_chapters": len(rows),
        "complete": complete,
        "incomplete": len(rows) - complete,
        "coverage_pct": round(complete / len(rows) * 100, 1) if rows else 0.0,
        "thresholds": thresholds,
        "chapters": rows,
        "orphan_dirs": orphan_dirs,
    })
    planning = dict(old.get("planning") or {})
    planning.update({
        "planned_total": planned_total,
        "planned_complete": planned_total - len(missing_units),
        "planned_missing": len(missing_units),
        "planning_coverage_pct": round((planned_total - len(missing_units)) / planned_total * 100, 1) if planned_total else 0.0,
        "missing_units": missing_units,
    })
    new["planning"] = planning

    print("==== 重算结果 ====")
    print(f"  章节总数   {len(rows)}（旧记录 {old.get('total_chapters')}）")
    print(f"  完整       {complete}（旧记录 {old.get('complete')}）")
    print(f"  不完整     {len(rows) - complete}（旧记录 {old.get('incomplete')}）")
    print(f"  覆盖率     {new['coverage_pct']}%（旧记录 {old.get('coverage_pct')}%）")
    print(f"  manifest 计划单元 {planned_total}，磁盘缺失 {len(missing_units)}（旧记录 {len(old.get('planning', {}).get('missing_units') or [])}）")
    print(f"  孤儿目录   {len(orphan_dirs)}（旧记录 {len(old.get('orphan_dirs') or [])}）")
    inc = [r for r in rows if not r["complete"]]
    if inc:
        print("\n  仍不完整的章节：")
        for r in inc[:20]:
            print(f"    {r['subject']}/{r['id']}: {'; '.join(r['issues'])}")
    by_sub: dict[str, list[int]] = {}
    for r in rows:
        a = by_sub.setdefault(r["subject"], [0, 0])
        a[0] += 1
        a[1] += 1 if r["complete"] else 0
    print("\n  逐学科（完整/总）：")
    for s in SUBJECT_ORDER:
        if s in by_sub:
            print(f"    {s:13} {by_sub[s][1]}/{by_sub[s][0]}")

    if args.apply:
        BACKUP.mkdir(parents=True, exist_ok=True)
        snap = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
        snap.mkdir(parents=True, exist_ok=True)
        if COV.exists():
            shutil.copy2(COV, snap / "_coverage.json")
        COV.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"\n已写入 {COV}。备份：{snap}")
    else:
        print("\n(dry-run，未写入)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
