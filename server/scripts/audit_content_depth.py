"""章节完整性 & 深度审计（只读）。

产出：server/.scratch/content-audit.json + 终端摘要

真实目录结构（2026-10 现状，与 server/scripts/validate_content.py 一致）：
    <subject>/<前缀>-chNN/
        concept/*.md      概念讲解（可多篇）
        examples/*.json   可运行示例（带真实输出）
        exercises.json    练习
        interview.json    面试题
        goals.md          学习目标
        pitfalls.md       踩坑
        project.json      实战项目

判定口径（避免"看起来完整"的自欺）：
    完整  —— 必需五类齐全：concept/ 非空、examples/ 非空、exercises.json、
             interview.json、goals.md、pitfalls.md
    深度  —— 正文 ≥ 12KB 且 示例 ≥ 4 且 concept 篇数 ≥ 2 且包含
             「复杂度 / 对比 / 边界 / 为什么」类论证词
这里量的是**体量与结构**，不是知识正确性；正确性由 verify_* 脚本负责。
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"
OUT = Path(__file__).resolve().parent.parent / ".scratch" / "content-audit.json"

REQUIRED_FILES = ["exercises.json", "interview.json", "goals.md", "pitfalls.md"]
DEEP_MARKERS = ["复杂度", "对比", "边界", "为什么", "区别", "代价", "陷阱"]


def size_kb(p: Path) -> float:
    return p.stat().st_size / 1024 if p.exists() else 0.0


def scan(d: Path) -> dict:
    concept_dir = d / "concept"
    example_dir = d / "examples"
    concepts = sorted(concept_dir.glob("*.md")) if concept_dir.is_dir() else []
    examples = sorted(example_dir.glob("*.json")) if example_dir.is_dir() else []

    concept_kb = sum(size_kb(f) for f in concepts)
    ex_kb = sum(size_kb(f) for f in examples)
    other_kb = sum(size_kb(d / f) for f in REQUIRED_FILES + ["project.json"])
    total = concept_kb + ex_kb + other_kb

    prose = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in concepts)
    code_blocks = len(re.findall(r"```", prose)) // 2
    markers = [m for m in DEEP_MARKERS if m in prose]

    missing = []
    if not concepts:
        missing.append("concept/")
    if not examples:
        missing.append("examples/")
    for f in REQUIRED_FILES:
        if not (d / f).exists():
            missing.append(f)

    return {
        "id": d.name,
        "subject": d.parent.name,
        "concept_files": len(concepts),
        "example_files": len(examples),
        "concept_kb": round(concept_kb, 1),
        "example_kb": round(ex_kb, 1),
        "total_kb": round(total, 1),
        "code_blocks": code_blocks,
        "markers": len(markers),
        "missing": missing,
        "deep": total >= 12 and len(examples) >= 4 and len(concepts) >= 2 and len(markers) >= 2,
        "shallow": total < 8 or len(examples) < 3 or len(markers) < 2,
    }


def main() -> None:
    rows = []
    for sub in sorted(p for p in CONTENT.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for d in sorted(sub.iterdir()):
            if d.is_dir() and re.match(r".+-ch\d+$", d.name):
                rows.append(scan(d))

    cov = json.loads((CONTENT / "_coverage.json").read_text(encoding="utf-8"))
    declared = {
        u["id"]
        for u in cov.get("planning", {}).get("units", [])
        if u.get("module") == "chapter"
    }
    on_disk = {r["id"] for r in rows}

    agg = defaultdict(lambda: {"n": 0, "kb": [], "ex": [], "deep": 0, "shallow": 0, "bad": 0})
    for r in rows:
        a = agg[r["subject"]]
        a["n"] += 1
        a["kb"].append(r["total_kb"])
        a["ex"].append(r["example_files"])
        a["deep"] += r["deep"]
        a["shallow"] += r["shallow"]
        a["bad"] += 1 if r["missing"] else 0

    summary = {
        "declared_chapters": len(declared),
        "on_disk_chapters": len(rows),
        "missing_chapters": sorted(declared - on_disk),
        "extra_on_disk": sorted(on_disk - declared),
        "structurally_incomplete": [{"id": r["id"], "missing": r["missing"]} for r in rows if r["missing"]],
        "median_kb": round(statistics.median(r["total_kb"] for r in rows), 1),
        "min_kb": min(r["total_kb"] for r in rows),
        "max_kb": max(r["total_kb"] for r in rows),
        "deep_count": sum(r["deep"] for r in rows),
        "shallow_count": sum(r["shallow"] for r in rows),
        "median_examples": statistics.median(r["example_files"] for r in rows),
        "median_concept_files": statistics.median(r["concept_files"] for r in rows),
        "total_kb": round(sum(r["total_kb"] for r in rows), 1),
        "by_subject": {
            k: {
                "chapters": v["n"],
                "median_kb": round(statistics.median(v["kb"]), 1),
                "min_kb": min(v["kb"]),
                "median_examples": statistics.median(v["ex"]),
                "deep": v["deep"],
                "shallow": v["shallow"],
                "structurally_bad": v["bad"],
            }
            for k, v in sorted(agg.items())
        },
        "thinnest": [
            {k: r[k] for k in ("id", "total_kb", "concept_files", "example_files", "markers", "missing")}
            for r in sorted(rows, key=lambda r: r["total_kb"])[:12]
        ],
        "thickest": [
            {k: r[k] for k in ("id", "total_kb", "concept_files", "example_files", "markers")}
            for r in sorted(rows, key=lambda r: -r["total_kb"])[:8]
        ],
    }

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "chapters": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"声明 {summary['declared_chapters']} 章 / 磁盘 {summary['on_disk_chapters']} 章")
    print(f"缺口: {summary['missing_chapters'] or '无'} | 多余: {summary['extra_on_disk'] or '无'}")
    print(f"结构不全: {len(summary['structurally_incomplete'])} 章 {summary['structurally_incomplete'][:3]}")
    print(f"体量 中位 {summary['median_kb']}KB 最小 {summary['min_kb']}KB 最大 {summary['max_kb']}KB 合计 {summary['total_kb']/1024:.1f}MB")
    print(f"深度 达标 {summary['deep_count']} / 偏浅 {summary['shallow_count']} / 共 {len(rows)}")
    print(f"示例 中位 {summary['median_examples']} 个 | concept 中位 {summary['median_concept_files']} 篇")
    print("\n按学科:")
    for k, v in summary["by_subject"].items():
        print(f"  {k:12s} {v['chapters']:3d}章  中位{v['median_kb']:6.1f}KB  最小{v['min_kb']:5.1f}KB  示例中位{v['median_examples']:.0f}  深{v['deep']:2d}  浅{v['shallow']:2d}  结构缺{v['structurally_bad']:2d}")
    print("\n最薄的 12 章:")
    for r in summary["thinnest"]:
        print(f"  {r['id']:14s} {r['total_kb']:6.1f}KB  concept {r['concept_files']}篇  示例 {r['example_files']:2d}  论证词 {r['markers']}")
    print("\n最厚的 8 章:")
    for r in summary["thickest"]:
        print(f"  {r['id']:14s} {r['total_kb']:7.1f}KB  concept {r['concept_files']}篇  示例 {r['example_files']:2d}")


if __name__ == "__main__":
    main()
