#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 content/<subject>/_bagua.json 打包成前端可 import 的 TS 模块。

为什么单独一个产物、不塞进 bundle.ts：
  bundle.ts 是「章节 / 项目 / 指南」三条主线，体积已经有 270KB；
  八股是玩法侧（图鉴情报）消费的独立资产，单独文件才能被路由按需加载，
  也便于 audit_playability 单独核对「260 条是否都被读到」。

数据源：content/*/_bagua.json（15 学科）
产物：  frontend/src/data/bagua.ts（请勿手改）

用法：python frontend/scripts/gen_bagua_data.py
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # CppMind/
CONTENT = ROOT / "content"
OUT = Path(__file__).resolve().parents[1] / "src" / "data" / "bagua.ts"

# agent / ml 两科的章节已由 scripts/merge_agent_ml_into_ai.py 并入 ai 学科
# （见 bundle.ts 头注释）。图鉴若不跟着改口径，会出现「选 ai 查不到 agent 那 24 条」
# 的断层，所以这里做科目归一，原科名保留在 rawSubject 里可追溯。
SUBJECT_ALIAS = {"agent": "ai", "ml": "ai"}

ASCII_WORD = re.compile(r"[a-z][a-z0-9+#.]{1,}")

# 标签里常见的缩写：章节标题写的是全称，不展开就永远匹配不上
TAG_ALIAS = {
    "js": ["javascript"],
    "ts": ["typescript"],
    "k8s": ["kubernetes"],
    "gc": ["垃圾回收", "内存"],
}


def words(text: str) -> Counter:
    """中文 2-gram + 英文词，与 scripts/gen_graph.py 同一口径。"""
    text = (text or "").lower()
    out: Counter = Counter()
    for w in ASCII_WORD.findall(text):
        out[w] += 1
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(len(run) - 1):
            out[run[i : i + 2]] += 1
    return out


def _first_paragraph(path: Path, limit: int = 500) -> str:
    """取 Markdown 第一个非标题段落。C 语言单元的 manifest 没有 summary 字段，
    真正的「这一单元讲什么」在 goals.md 里，不读它就只能靠标题十几个字去匹配。"""
    if not path.exists():
        return ""
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            if buf:
                break
            continue
        buf.append(s)
        if sum(len(x) for x in buf) > limit:
            break
    return "".join(buf)[:limit]


def load_chapters() -> dict[str, list[dict]]:
    """学科 → 章节（title / summary），用于把八股条目绑到具体章节。"""
    packs: dict[str, list[dict]] = {}
    for path in sorted(CONTENT.glob("*/_manifest.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        subj = SUBJECT_ALIAS.get(d.get("subject") or path.parent.name, d.get("subject") or path.parent.name)
        rows = packs.setdefault(subj, [])
        for c in d.get("chapters") or []:
            rows.append({"id": c["id"], "order": c.get("order") or 0,
                         "title": c.get("title") or "", "summary": c.get("summary") or ""})
        for u in (d.get("clang_module") or {}).get("units") or []:
            # C 语言的 7 个单元挂在 cpp 的 manifest 里，但学科是 clang
            # （学习页用 CLANG_CHAPTERS 展示），绑章节时必须落在 clang 包里，
            # 否则 20 条 clang 八股一条都匹配不到。
            packs.setdefault("clang", []).append(
                {"id": u["id"], "order": u.get("order") or 0,
                 "title": u.get("title") or "",
                 "summary": u.get("summary") or _first_paragraph(CONTENT / "clang" / u["id"] / "goals.md")}
            )
    return packs


def bind_chapters(item: dict, pool: list[dict], idf: dict[str, float]) -> list[str]:
    """按标签 + 题干与章节标题/摘要的词重合度，绑最多 3 章。

    为什么标签权重乘 3：八股条目的 tags 是作者手写的主题词（「智能指针」「RAG」），
    题干里的自然语言则混着「下列」「说法」这类噪音；不放大标签，
    匹配会退化成「谁摘要长谁中」。
    """
    if not pool:
        return []
    q = words(item["q"])
    tags: Counter = Counter()
    for t in item["tags"]:
        tags.update(words(t))
        for alt in TAG_ALIAS.get(str(t).strip().lower(), []):
            tags.update(words(alt))
    for t in tags:
        tags[t] *= 3
    mine = q + tags
    scored = []
    for c in pool:
        cw = words(c["title"])
        for t in words(c["title"]):
            cw[t] += 1
        cw.update(words(c["summary"]))
        shared = set(mine) & set(cw)
        if not shared:
            continue
        score = sum(idf.get(t, 0.0) * mine[t] for t in shared)
        if score <= 0:
            continue
        scored.append((score, -c["order"], c["id"]))
    scored.sort(reverse=True)
    return [cid for _, _, cid in scored[:3]]

TS_TYPES = """/**
 * bagua.ts —— 八股情报库（图鉴「情报」面板与情报库 Tab 的唯一数据源）
 *
 * 由 frontend/scripts/gen_bagua_data.py 从 content/<subject>/_bagua.json 生成，请勿手改。
 * 合规：只存要点与出处，不搬运第三方题面。
 */
export interface BaguaItem {
  /** 稳定 id：<subject>/<category>/<序号>，图鉴按 tags 命中后靠它去重 */
  id: string;
  /** 学科 key，与 SUBJECTS[].key 一致 */
  subject: string;
  category: string;
  categoryId: string;
  q: string;
  a: string;
  tags: string[];
  difficulty: string;
  /** 面试热度 1~5，用于图鉴里排「先看哪条」 */
  hot: number;
  src?: string;
  /** 这条八股对应到具体哪几章（由 tags 与章节标题的词重合算出，最多 3 章） */
  chapterIds: string[];
  /** 合并前的原始学科（agent / ml → ai），仅作溯源 */
  rawSubject?: string;
}
"""


def main() -> None:
    files = sorted(CONTENT.glob("*/_bagua.json"))
    items: list[dict] = []
    by_subject: dict[str, list[str]] = {}
    categories: dict[str, dict[str, str]] = {}
    chapter_packs = load_chapters()

    # 每个学科的 IDF：词越泛（「数据」「方法」）权重越低，避免每条八股都绑到第 1 章
    idf_by_subject: dict[str, dict[str, float]] = {}
    for subj, pool in chapter_packs.items():
        df: Counter = Counter()
        for c in pool:
            w = words(c["title"]) + words(c["summary"])
            for t in w:
                df[t] += 1
        idf_by_subject[subj] = {t: 1.0 / math.log(2 + n) for t, n in df.items()}

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        raw = data.get("subject") or f.parent.name
        subj = SUBJECT_ALIAS.get(raw, raw)
        bucket = by_subject.setdefault(subj, [])
        cats = categories.setdefault(subj, {})
        for cat in data.get("categories", []):
            cid = str(cat.get("id") or "misc")
            cats[cid] = str(cat.get("title") or cid)
            for i, it in enumerate(cat.get("items", []), 1):
                q = (it.get("q") or "").strip()
                a = (it.get("a") or "").strip()
                if not q or not a:
                    # 空白条目不入库：图鉴展示空题目等于假数据
                    continue
                # id 用原始科目前缀，避免 agent/lang/01 与 ai/lang/01 撞车
                item = {
                    "id": f"{raw}/{cid}/{i:02d}",
                    "subject": subj,
                    "category": cats[cid],
                    "categoryId": cid,
                    "q": q,
                    "a": a,
                    "tags": [str(t) for t in (it.get("tags") or []) if str(t).strip()],
                    "difficulty": it.get("difficulty") or "medium",
                    "hot": int(it.get("hot") or 0),
                    "src": (it.get("source_ref") or "").strip() or None,
                    "chapterIds": bind_chapters(
                        {"q": q, "tags": [str(t) for t in (it.get("tags") or [])]},
                        chapter_packs.get(subj, []),
                        idf_by_subject.get(subj, {}),
                    ),
                }
                if raw != subj:
                    item["rawSubject"] = raw
                items.append(item)
                bucket.append(item["id"])

    for subj, arr in by_subject.items():
        print(f"  {subj:14s} {len(arr):3d} 条  {len(categories.get(subj, {}))} 类")

    bound = sum(1 for it in items if it["chapterIds"])
    print(f"  绑定到章节：{bound} / {len(items)} 条（{bound / max(len(items), 1) * 100:.1f}%）")
    unbound = [it["id"] for it in items if not it["chapterIds"]]
    if unbound:
        print(f"  ! 未绑章节 {len(unbound)} 条：{unbound[:8]}")

    used = {it["id"] for it in items}
    missing = [i for arr in by_subject.values() for i in arr if i not in used]
    assert not missing, f"分组里引用了不存在的 id：{missing[:5]}"

    body = json.dumps(items, ensure_ascii=False, indent=None, separators=(",", ":"))
    chunks = [body[i : i + 3200] for i in range(0, len(body), 3200)]
    payload = " + \n  ".join(json.dumps(c, ensure_ascii=False) for c in chunks)

    header = (
        "/* 由 frontend/scripts/gen_bagua_data.py 从 content/<学科>/_bagua.json 生成，请勿手改。\n"
        f"   {len(by_subject)} 学科 / {len(items)} 条八股情报。 */\n\n"
        "/* eslint-disable */\n"
    )
    out = [
        header,
        TS_TYPES,
        "\nexport const BAGUA: BaguaItem[] = JSON.parse(\n  ",
        payload,
        ",\n);\n",
        "\nexport const BAGUA_BY_SUBJECT: Record<string, BaguaItem[]> = BAGUA.reduce(\n"
        "  (acc, it) => {\n"
        "    (acc[it.subject] ??= []).push(it);\n"
        "    return acc;\n"
        "  },\n"
        "  {} as Record<string, BaguaItem[]>,\n"
        ");\n",
        "\nexport const BAGUA_SUBJECTS: string[] = Object.keys(BAGUA_BY_SUBJECT);\n",
        "\n/** 学科内按热度降序，图鉴里「先看哪条」直接取前 N */\n"
        "export function baguaOfSubject(subject: string): BaguaItem[] {\n"
        "  return [...(BAGUA_BY_SUBJECT[subject] ?? [])].sort((a, b) => b.hot - a.hot);\n"
        "}\n",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(out), encoding="utf-8")
    print(f"\n写入 {OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.1f} KB  {len(items)} 条")


if __name__ == "__main__":
    main()
