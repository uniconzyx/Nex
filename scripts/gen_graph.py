#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成「章节 → 项目 → 图鉴」依赖图的数据侧（P2 · C2）。

【为什么要自动生成，而不是手写】
  153 章 × 110 个项目 = 16 830 对可能关系。手写必然漏、必然过期；
  而项目身上现成的字段（stack / learn / title / summary）和章节的
  title / summary 本来就是同一批术语写的 —— 用词重合度是**可计算**的，
  算完再由 audit_graph.py 守门（无环、无悬空边、每个项目至少 1 章）。

【算法】同一学科内，按 IDF 加权的 n-gram 重合度：
  1. 中文取 2-gram，英文/数字取长度 ≥2 的小写词；
  2. 某个词在越多章里出现，说明它越泛（「数据」「函数」），权重 1/log(2+df) 越低；
  3. 章节得分 = 项目词 ∩ 章节词 的权重和；标题再乘 2（标题是这一章的主题声明）；
  4. 按 tier 控制数量与「章号上限」：T1 只能依赖前 8 章，
     否则会出现「第 1 个项目要求先学完第 19 章」的荒唐门槛。

产物：frontend/src/data/graph.ts（请勿手改）
用法：python scripts/gen_graph.py
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "src" / "data" / "graph.ts"

SUBJECT_ALIAS = {"agent": "ai", "ml": "ai"}

# 每个 tier 最多依赖几章、只允许依赖前多少章
TIER_RULE = {
    "t1": (2, 8),
    "t2": (3, 14),
    "t3": (3, 20),
    "t4": (4, 99),
}

CJK = re.compile(r"[\u4e00-\u9fff]")
ASCII_WORD = re.compile(r"[a-z][a-z0-9+#.]{1,}")


def words(text: str) -> Counter:
    """返回 {token: 出现次数}。中文 2-gram + 英文词。"""
    text = (text or "").lower()
    out: Counter = Counter()
    # 英文 / 数字词
    for w in ASCII_WORD.findall(text):
        out[w] += 1
    # 中文连续片段 → 所有 2-gram
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(len(run) - 1):
            out[run[i : i + 2]] += 1
    return out


def load_chapters() -> list[dict]:
    rows: list[dict] = []
    for path in sorted((ROOT / "content").glob("*/_manifest.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        subject = SUBJECT_ALIAS.get(d.get("subject") or path.parent.name, d.get("subject") or path.parent.name)
        for c in d.get("chapters") or []:
            rows.append(
                {
                    "id": c["id"],
                    "subject": subject,
                    "order": c.get("order") or 0,
                    "title": c.get("title") or "",
                    "summary": c.get("summary") or "",
                    "prerequisites": [p for p in (c.get("prerequisites") or []) if p],
                }
            )
        for u in (d.get("clang_module") or {}).get("units") or []:
            rows.append(
                {
                    "id": u["id"],
                    "subject": "clang",
                    "order": u.get("order") or 0,
                    "title": u.get("title") or "",
                    "summary": u.get("summary") or "",
                    "prerequisites": [p for p in (u.get("prerequisites") or []) if p],
                }
            )
    return rows


def load_projects() -> list[dict]:
    doc = json.loads((ROOT / "content/_projects/career-projects.json").read_text(encoding="utf-8"))
    return doc.get("items") or doc.get("projects") or []


def main() -> None:
    chapters = load_chapters()
    projects = load_projects()
    by_subject: dict[str, list[dict]] = {}
    for c in chapters:
        by_subject.setdefault(c["subject"], []).append(c)
    for arr in by_subject.values():
        arr.sort(key=lambda x: x["order"])

    all_ids = {c["id"] for c in chapters}

    # ---- 章节依赖边：manifest 里已经是 id，但仍然兜底校验一次 ----
    deps: dict[str, list[str]] = {}
    dangling: list[str] = []
    for c in chapters:
        keep = []
        for p in c["prerequisites"]:
            if p in all_ids:
                keep.append(p)
            else:
                dangling.append(f'{c["id"]} → {p}')
        deps[c["id"]] = keep

    # ---- 项目 requires：IDF 加权词重合 ----
    requires: dict[str, list[str]] = {}
    for p in projects:
        slug = p["slug"]
        track = SUBJECT_ALIAS.get(p.get("track") or "", p.get("track") or "")
        pool = by_subject.get(track) or []
        n_tier, order_cap = TIER_RULE.get(p.get("tier") or "t2", (2, 99))
        if not pool:
            requires[slug] = []
            continue

        # 该学科的 IDF
        df: Counter = Counter()
        doc_words: dict[str, Counter] = {}
        for c in pool:
            w = words(c["title"])
            w.update(words(c["summary"]))
            # 标题出现的词加权：标题是主题声明，不是顺带一提
            for t in words(c["title"]):
                w[t] += 1
            doc_words[c["id"]] = w
            for t in w:
                df[t] += 1
        idf = {t: 1.0 / math.log(2 + n) for t, n in df.items()}

        proj_words = words(" ".join([p.get("title") or "", p.get("summary") or ""] +
                                   [str(x) for x in (p.get("stack") or [])] +
                                   [str(x) for x in (p.get("learn") or [])]))
        scored = []
        for c in pool:
            if c["order"] > order_cap:
                continue
            shared = set(proj_words) & set(doc_words[c["id"]])
            if not shared:
                continue
            score = sum(idf.get(t, 0.0) for t in shared)
            scored.append((score, -c["order"], c["id"]))
        scored.sort(reverse=True)
        picked = [cid for _, _, cid in scored[:n_tier]]
        if not picked:
            # 没有任何词重合：退化成「这门课的前 n 章」，保证门槛可检查且不悬空
            picked = [c["id"] for c in pool if c["order"] <= order_cap][:n_tier]
        requires[slug] = sorted(picked, key=lambda cid: next(c["order"] for c in pool if c["id"] == cid))

    # ---- 写产物 ----
    chapter_subject = {c["id"]: c["subject"] for c in chapters}
    meta = {c["id"]: c["title"] for c in chapters}

    body = {
        "chapterDeps": deps,
        "projectRequires": requires,
        "chapterSubject": chapter_subject,
        "chapterTitle": meta,
    }
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    header = f"""/* 由 scripts/gen_graph.py 从 content/ 生成，请勿手改。
   章节 {len(chapters)} 个 / 依赖边 {sum(len(v) for v in deps.values())} 条；
   项目 {len(projects)} 个 / requires 边 {sum(len(v) for v in requires.values())} 条。
   生成口径见脚本头注释：同一学科内 IDF 加权词重合，按 tier 限制数量与章号上限。 */
/* eslint-disable */
export interface GraphData {{
  /** 章节 → 前置章节 id */
  chapterDeps: Record<string, string[]>;
  /** 项目 slug → 需要的章节 id（按章号升序） */
  projectRequires: Record<string, string[]>;
  /** 章节 → 学科 key（agent / ml 已归一到 ai） */
  chapterSubject: Record<string, string>;
  /** 章节 → 标题，避免为了显示一个名字去遍历 BUNDLE */
  chapterTitle: Record<string, string>;
}}

export const GRAPH: GraphData = """
    trailer = ";\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(header + payload + trailer, encoding="utf-8")

    print(f"chapters={len(chapters)} deps={sum(len(v) for v in deps.values())} projects={len(projects)}")
    if dangling:
        print(f"! 悬空前置 {len(dangling)} 条（已丢弃）：{dangling[:5]}")
    no_req = [p["slug"] for p in projects if not requires.get(p["slug"])]
    print(f"requires 为空的项目 {len(no_req)} 个")
    print(f"写入 {OUT.relative_to(ROOT)} {OUT.stat().st_size / 1024:.1f} KB")

    # 抽样自查：打印 8 个项目的依赖，人工看是否讲得通
    print("\n抽样（项目 → 依赖章节）：")
    for p in projects[:8]:
        ids = requires[p["slug"]]
        print(f'  {p["slug"]:24s} {p["tier"]} → ' + " | ".join(meta[i][:18] for i in ids))


if __name__ == "__main__":
    main()
