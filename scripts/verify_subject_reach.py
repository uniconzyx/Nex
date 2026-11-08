#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""学科/章节「入口闭环」门禁：防止「有数据、无入口」再次发生。

背景（2026-11-08）
--------------------------------------------------------------------
content/discrete-math/ 三章的题目、概念、实验、图解全都在包里，但
BUNDLE.chapters 没有这个学科、SUBJECTS 没有对应胶囊、剧情没台词，
于是学习页选不到、题库筛不到 —— 数据 100% 齐，用户却一个字都看不到。
根因：sync_bundle_chapters.py 当年只补「已有学科的新章节」，遇到整个
新学科只打一行告警就跳过。修完数据之后必须有门禁守住这条链路。

检查（纯标准库、只读、零第三方依赖）
--------------------------------------------------------------------
  1. content/*/_manifest.json 的每个学科都进 BUNDLE.chapters（agent/ml 按
     方案 A 归入 ai），且不多出学科；
  2. 每个 manifest 章节 id 都在 BUNDLE.chapters 里，或属于 clang 独立模块；
  3. SUBJECTS 的 key 恰好 = BUNDLE.chapters 的 key + clang；
  4. graph.ts 的 167 章全部被剧情 story.ts 覆盖，且无孤儿台词；
  5. 题库里出现的 subj 全部是已注册学科，且每个学科至少有 1 道题；
  6. 每个学科在八股 / 实验 / 可视化 / 图解四个辅助面板里至少有一处入口；
  7. 概念全文 167 章全覆盖，且映射到的学科模块文件真实存在。

用法：python scripts/verify_subject_reach.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ALIAS = {"agent": "ai", "ml": "ai"}
# C 语言的 7 个单元由 clangUnits.ts 独立提供，历史上就不进 BUNDLE.chapters
SPECIAL_SUBJECTS = {"clang"}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def json_const(text: str, marker: str, tail: str = ";") -> dict:
    """从 `export const X = {...};` 里抠出对象字面量。"""
    i = text.index(marker) + len(marker)
    j = text.rindex(tail)
    return json.loads(text[i:j])


def manifest_subjects() -> tuple[set[str], set[str]]:
    subjects: set[str] = set()
    chapters: set[str] = set()
    for p in sorted((ROOT / "content").glob("*/_manifest.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        s = d.get("subject") or p.parent.name
        subjects.add(SUBJECT_ALIAS.get(s, s))
        chapters.update(c["id"] for c in (d.get("chapters") or []))
        for u in (d.get("clang_module") or {}).get("units") or []:
            if isinstance(u, dict) and u.get("id"):
                chapters.add(u["id"])
    return subjects, chapters


def main() -> int:
    errors: list[str] = []
    info: list[str] = []

    man_subjects, man_chapters = manifest_subjects()
    bundle = json_const(read("frontend/src/data/bundle.ts"), "export const BUNDLE = ", " as unknown as Bundle;")
    bundle_packs = bundle["chapters"]
    bundle_subjects = set(bundle_packs)
    bundle_chapters = {c["id"] for p in bundle_packs.values() for c in p["chapters"]}

    subjects = re.findall(r"\{\s*key:\s*'([^']+)'", read("frontend/src/lib/subject.ts"))
    subject_set = set(subjects)

    graph = json_const(read("frontend/src/data/graph.ts"), "export const GRAPH: GraphData = ")
    graph_map: dict[str, str] = graph["chapterSubject"]
    graph_ids = set(graph_map)
    clang_ids = {cid for cid, s in graph_map.items() if s == "clang"}

    story_text = read("frontend/src/data/story.ts")
    story_ids = set(re.findall(r'chapterId:\s*"([^"]+)"', story_text))
    bank_text = read("frontend/src/data/exercises.ts")
    bank_subjects = set(re.findall(r'"subj"\s*:\s*"([^"]+)"', bank_text))

    bagua_text = read("frontend/src/data/bagua.ts")       # JSON.parse("...") 里是转义过的 \"subject\":\"ai\"
    labs_text = read("frontend/src/data/labs/index.ts")   # subject: "agent"
    viz_text = read("frontend/src/data/viz/index.ts")     # 'discrete-math': () => import(...)
    diagram_text = read("frontend/src/data/diagrams.ts")  # 独立 key 命名空间（fund/cpp/dm...）
    bagua_subjects = set(re.findall(r'\\"subject\\":\\"([^"\\]+)\\"', bagua_text))
    lab_subjects = set(re.findall(r'subject:\s*"([^"]+)"', labs_text))
    viz_subjects = set(re.findall(r"^\s*'?([\w-]+)'?:\s*\(\)\s*=>\s*import", viz_text, re.M))
    diagram_subjects = set(re.findall(r'"key"\s*:\s*"([^"]+)"', diagram_text))

    # 1. 学科包闭环
    if man_subjects - bundle_subjects:
        errors.append(f"BUNDLE.chapters 缺学科：{sorted(man_subjects - bundle_subjects)}")
    if bundle_subjects - man_subjects:
        errors.append(f"BUNDLE.chapters 有 manifest 里不存在的学科：{sorted(bundle_subjects - man_subjects)}")

    # 2. 章节闭环（clang 走独立模块）
    missing_ch = man_chapters - bundle_chapters - clang_ids
    if missing_ch:
        errors.append(f"manifest 有 {len(missing_ch)} 章没进学习页：{sorted(missing_ch)[:12]}")
    orphan_ch = bundle_chapters - man_chapters
    if orphan_ch:
        errors.append(f"BUNDLE 有 {len(orphan_ch)} 章在 manifest 里找不到：{sorted(orphan_ch)[:12]}")

    # 3. 胶囊闭环
    want = bundle_subjects | SPECIAL_SUBJECTS
    if subject_set != want:
        errors.append(f"SUBJECTS 与 BUNDLE 不一致：缺 {sorted(want - subject_set)} / 多 {sorted(subject_set - want)}")
    if len(subjects) != len(subject_set):
        errors.append("SUBJECTS 里有重复 key")

    # 4. 剧情覆盖
    missing_story = graph_ids - story_ids
    if missing_story:
        errors.append(f"剧情缺 {len(missing_story)} 章台词：{sorted(missing_story)[:12]}")
    orphan_story = story_ids - graph_ids
    if orphan_story:
        errors.append(f"剧情有 {len(orphan_story)} 条孤儿台词：{sorted(orphan_story)[:12]}")

    # 5. 题库
    if bank_subjects - subject_set:
        errors.append(f"题库出现未注册学科：{sorted(bank_subjects - subject_set)}")
    no_bank = subject_set - bank_subjects
    if no_bank:
        errors.append(f"这些学科胶囊在题库里一道题都没有：{sorted(no_bank)}")

    # 6. 辅助面板入口（四个面板的 key 命名空间不完全一致，用文本存在性判定，
    #    只抓「整个学科一个辅助入口都没有」，不因 agent/ml 别名差异误报）
    aux_text = "\n".join((bagua_text, labs_text, viz_text, diagram_text))
    no_aux = sorted(s for s in man_subjects if s not in aux_text)
    if no_aux:
        errors.append(f"这些学科在八股/实验/可视化/图解里一个入口都没有：{no_aux}")

    # 7. 概念全文：index.ts 的 MODULE_OF 段就是「章节 → 学科模块」映射
    concept_index = read("frontend/src/data/concepts/index.ts")
    seg = concept_index.split("const MODULE_OF: Record<string, string> = {", 1)[1].split("};", 1)[0]
    concept_pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', seg)
    concept_chapters = {cid for cid, _mod in concept_pairs}
    concept_modules = {mod for _cid, mod in concept_pairs}
    missing_concept = graph_ids - concept_chapters
    if missing_concept:
        errors.append(f"概念全文缺 {len(missing_concept)} 章：{sorted(missing_concept)[:12]}")
    orphan_concept = concept_chapters - graph_ids
    if orphan_concept:
        errors.append(f"概念全文有 {len(orphan_concept)} 个孤儿章：{sorted(orphan_concept)[:12]}")
    for mod in sorted(concept_modules):
        if not (ROOT / "frontend" / "src" / "data" / "concepts" / f"{mod}.ts").is_file():
            errors.append(f"概念模块 {mod}.ts 不存在")

    info.append(f"manifest 学科 {len(man_subjects)} / BUNDLE 学科 {len(bundle_subjects)} / 胶囊 {len(subjects)}")
    info.append(f"manifest 章节 {len(man_chapters)} / 学习页 {len(bundle_chapters)} + clang {len(clang_ids)} / 依赖图 {len(graph_ids)}")
    info.append(f"剧情 {len(story_ids)} 章 · 题库 {len(bank_subjects)} 学科 · 概念全文 {len(concept_chapters)} 章 / {len(concept_modules)} 模块")
    info.append(
        f"八股 {len(bagua_subjects)}({','.join(sorted(bagua_subjects))}) · "
        f"实验 {len(lab_subjects)} · 可视化 {len(viz_subjects)} · 图解 {len(diagram_subjects)}"
    )

    for line in info:
        print("  " + line)
    if errors:
        print(f"\n入口闭环 FAIL（{len(errors)} 项）：")
        for e in errors:
            print("  ✗ " + e)
        return 1
    print("\nSUBJECT_REACH_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
