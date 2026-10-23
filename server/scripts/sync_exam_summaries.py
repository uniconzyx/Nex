#!/usr/bin/env python3
"""把题库中尚未登记进分类总结的题目，按 topic 补登到对应 group 的 questionIds。

背景：408 四科总结是手维护的，新增题目（尤其 design 题）不会自动进总结，
validate_exam.py 会报「漏统计题目」。本脚本做单向补齐：
- 只追加缺失的 id，不打乱既有顺序
- topic 找不到对应 group 时报错退出（不允许静默丢弃）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QDIR = ROOT / "content" / "_exam" / "questions"
SDIR = ROOT / "content" / "_exam" / "summaries"


def sync_exam(exam: str, subject: str) -> tuple[int, int]:
    qfile = QDIR / f"{exam}-{subject}.json"
    sfile = SDIR / f"{exam}-{subject}.json"
    bank = json.loads(qfile.read_text(encoding="utf-8"))
    summ = json.loads(sfile.read_text(encoding="utf-8"))

    topics = {g["topic"]: g for g in summ["groups"]}
    registered = {qid for g in summ["groups"] for qid in g.get("questionIds", [])}

    added, missing_topic = 0, []
    for q in bank["items"]:
        if q["id"] in registered:
            continue
        g = topics.get(q["topic"])
        if g is None:
            missing_topic.append((q["id"], q["topic"]))
            continue
        g.setdefault("questionIds", []).append(q["id"])
        registered.add(q["id"])
        added += 1

    if missing_topic:
        for qid, t in missing_topic:
            print(f"  [ERR] {qid} 的 topic={t} 在 {sfile.name} 中无对应分组")
        raise SystemExit(f"{sfile.name}: {len(missing_topic)} 道题无法归组")

    if added:
        # 每组内按题库顺序重排，保证可读与可复现
        order = {q["id"]: i for i, q in enumerate(bank["items"])}
        for g in summ["groups"]:
            g["questionIds"] = sorted(g.get("questionIds", []), key=lambda x: order.get(x, 1 << 30))
        sfile.write_text(json.dumps(summ, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added, len(summ["groups"])


def main() -> int:
    total = 0
    for exam, subjects in {
        "408": ["ds", "co", "os", "cn"],
        "math": ["m1", "m2"],
        "english": ["e1", "e2"],
        "politics": ["pol"],
        "discrete": ["dm"],
        "algorithm": ["algo"],
    }.items():
        for subj in subjects:
            qf = QDIR / f"{exam}-{subj}.json"
            sf = SDIR / f"{exam}-{subj}.json"
            if not (qf.exists() and sf.exists()):
                continue
            added, ngroups = sync_exam(exam, subj)
            total += added
            print(f"{exam}/{subj}: 补登 {added} 题 / {ngroups} 个分组")
    print(f"共补登 {total} 题")
    return 0


if __name__ == "__main__":
    sys.exit(main())
