#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
判题可判率（P1）度量 + 校验脚本。

职责：
1. 扫描 content/ 下全部 exercises.json，统计 coding 类型题目的 test_cases 覆盖率（判题可判率）。
2. 列出缺 test_cases 的 coding 题目（缺口清单）。
3. 校验已存在 test_cases 的结构合法性（input / expected_output 必备，is_sample 为 bool）。
4. 校验 content/_exam/summaries 中 73 个分类总结的 suggestedOrder / questionIds 是否都能在题库里解析到真实题号。

用法：
    python scripts/_verify_judge_coverage.py
退出码：0 = 校验通过；1 = 发现结构性错误（test_cases 非法 / suggestedOrder 悬空 id）。
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")

# ---- 1. 收集全部 exercises.json ----
def iter_exercise_files():
    for sub in sorted(os.listdir(CONTENT)):
        d = os.path.join(CONTENT, sub)
        if not os.path.isdir(d):
            continue
        for r, _ds, fs in os.walk(d):
            if "exercises.json" in fs:
                yield os.path.join(r, "exercises.json")


# ---- 2. 可判率统计 ----
def measure():
    per_subject = defaultdict(lambda: [0, 0])  # subject -> [coding_total, with_tc]
    per_platform = defaultdict(lambda: [0, 0])
    gap = []  # (subject, path, title) 缺 test_cases 的 coding 题
    malformed = []  # test_cases 结构非法

    for fp in iter_exercise_files():
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] 解析失败: {fp}: {e}")
            continue
        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            continue
        # subject 取 meta.chapter 前两段或目录名
        meta = data.get("meta") or {}
        subj = meta.get("chapter") or os.path.basename(os.path.dirname(fp))
        subj = subj.split("/")[-1]
        for it in items:
            if it.get("type") != "coding":
                continue
            plat = it.get("platform") or "?"
            per_subject[subj][0] += 1
            per_platform[plat][0] += 1
            tc = it.get("test_cases")
            if not tc:
                gap.append((subj, fp, it.get("title", "?")))
                continue
            per_subject[subj][1] += 1
            per_platform[plat][1] += 1
            # 结构校验
            if not isinstance(tc, list):
                malformed.append((fp, it.get("title"), "test_cases 非 list"))
                continue
            for i, c in enumerate(tc):
                if not isinstance(c, dict):
                    malformed.append((fp, it.get("title"), f"case[{i}] 非对象"))
                    continue
                if "input" not in c or "expected_output" not in c:
                    malformed.append((fp, it.get("title"), f"case[{i}] 缺 input/expected_output"))
                if "is_sample" in c and not isinstance(c["is_sample"], bool):
                    malformed.append((fp, it.get("title"), f"case[{i}] is_sample 非 bool"))

    return per_subject, per_platform, gap, malformed


# ---- 3. 分类总结 suggestedOrder 校验 ----
def collect_question_ids():
    ids = set()
    for sub in sorted(os.listdir(os.path.join(CONTENT, "_exam", "questions"))):
        if not sub.endswith(".json"):
            continue
        d = json.load(open(os.path.join(CONTENT, "_exam", "questions", sub), encoding="utf-8"))
        for it in d.get("items", []):
            if isinstance(it, dict) and it.get("id"):
                ids.add(it["id"])
    return ids


def validate_summaries(qids):
    dangling = []  # (file, group_topic, field, missing_id)
    group_count = 0
    sdir = os.path.join(CONTENT, "_exam", "summaries")
    for f in sorted(os.listdir(sdir)):
        if not f.endswith(".json"):
            continue
        d = json.load(open(os.path.join(sdir, f), encoding="utf-8"))
        for grp in d.get("groups", []):
            group_count += 1
            topic = grp.get("topic", "?")
            for field in ("suggestedOrder", "questionIds"):
                vals = grp.get(field) or []
                for vid in vals:
                    if vid not in qids:
                        dangling.append((f, topic, field, vid))
    return group_count, dangling


def main():
    print("=" * 70)
    print("判题可判率（P1）度量 + 校验")
    print("=" * 70)

    per_subject, per_platform, gap, malformed = measure()

    total = sum(v[0] for v in per_subject.values())
    with_tc = sum(v[1] for v in per_subject.values())
    rate = (with_tc / total * 100) if total else 0.0

    print(f"\n[总览] coding 题 {total} 道，含 test_cases {with_tc} 道 → 判题可判率 {rate:.1f}%")
    print(f"[目标] 40%+  =>  {'已达成 ✅' if rate >= 40 else '未达成 ❌'}（缺口 {max(0, int(total*0.4)-with_tc)} 道）")

    print("\n--- 按 subject（coding 总数 / 含 test_cases / 率）---")
    for subj, (tot, wt) in sorted(per_subject.items(), key=lambda x: -x[1][0]):
        r = (wt / tot * 100) if tot else 0
        print(f"  {subj:16s} {tot:4d}  tc={wt:3d}  {r:5.1f}%")

    print("\n--- 按 platform ---")
    for plat, (tot, wt) in sorted(per_platform.items(), key=lambda x: -x[1][0]):
        r = (wt / tot * 100) if tot else 0
        print(f"  {plat:12s} {tot:4d}  tc={wt:3d}  {r:5.1f}%")

    print(f"\n[缺口] 缺 test_cases 的 coding 题：{len(gap)} 道")

    # summaries 校验
    qids = collect_question_ids()
    group_count, dangling = validate_summaries(qids)
    print(f"\n[分类总结] 共 {group_count} 个 group；suggestedOrder/questionIds 悬空 id：{len(dangling)}")
    for f, topic, field, vid in dangling[:30]:
        print(f"  ⚠ {f} | {topic} | {field} -> 缺失 {vid}")

    print("\n--- test_cases 结构合法性 ---")
    if malformed:
        print(f"  发现 {len(malformed)} 处非法：")
        for fp, title, msg in malformed[:30]:
            print(f"  ⚠ {fp} | {title} | {msg}")
    else:
        print("  全部 test_cases 结构合法 ✅")

    ok = (not malformed) and (not dangling)
    print("\n" + ("校验通过 ✅" if ok else "校验发现错误 ❌"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
