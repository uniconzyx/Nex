#!/usr/bin/env python
"""考研题库校验器（阶段16）。

强制每道题都带四层讲解，缺一层就报错退出，避免「题目只有答案没有方法」。

四层顺序 = 呈现顺序，不可调换：
  1. framework  解题框架 —— 这一类题的通法，不含本题具体数字
  2. approach   解决思路 —— 本题从哪里切入，3 句以内
  3. points     知识点   —— 命中的考点，带 knowledge id 可跳转
  4. solution   详细解法 —— 完整推导到答案

覆盖范围由 content/_exam/_meta.json 决定，不再写死 408：
  math → m1/m2，english → e1/e2，politics → pol。
文件命名约定：
  knowledge/{exam}-{subject}.json   questions/{exam}-{subject}.json
  summaries/{exam}-{subject}.json   frameworks/{subject}.json（408 为 408-{subject}.json）

题型：choice 单选、multi 多选、blank 填空、calc 计算、design 写作/设计、judge 判断。
套卷小节：choice/multi 存题目 id；analysis/blank/calc/design 内联题目对象。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"

MIN_STEPS = 3
MIN_APPROACH = 20
MIN_SOLUTION = 80
MIN_SOLUTION_OBJ = 60  # 选择题/多选题的解析可以短一些，但仍要给出理由
MIN_SUMMARY_SKILLS = 1
LAYER_ORDER = ["framework", "approach", "points", "solution"]  # 讲解的固定四层顺序

VALID_TYPES = {"choice", "multi", "blank", "calc", "design", "judge"}
INLINE_SECTIONS = {"analysis", "blank", "calc", "design"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.stats: dict[str, object] = {}

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)


def load_json(path: Path, rep: Report) -> dict | None:
    if not path.exists():
        rep.err(f"缺文件 {path.relative_to(ROOT)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        rep.err(f"{path.relative_to(ROOT)} 解析失败：{exc}")
        return None


def exam_defs() -> list[dict]:
    meta = json.loads((EXAM / "_meta.json").read_text(encoding="utf-8"))
    return meta["exams"]


def fw_path(exam: str, subj: str) -> Path:
    name = f"408-{subj}.json" if exam == "408" else f"{subj}.json"
    return EXAM / "frameworks" / name


def check_walkthrough(q: dict, where: str, k_index: dict, patterns: dict, rep: Report) -> None:
    w = q.get("walkthrough")
    if not isinstance(w, dict):
        rep.err(f"{where} 缺 walkthrough（四层讲解）")
        return

    # 固定顺序：解题框架 → 解决思路 → 知识点 → 详细解法。
    # JSON 保留键的插入顺序，前端按 Object.keys 顺序渲染，所以顺序必须在这里守住。
    order = [k for k in w.keys() if k in LAYER_ORDER]
    if order != LAYER_ORDER:
        rep.err(f"{where} 四层顺序错：{order}，必须是 {LAYER_ORDER}")
    for k in LAYER_ORDER:
        if k not in w:
            rep.err(f"{where} 四层缺 {k}")

    fw = w.get("framework")
    if not isinstance(fw, dict):
        rep.err(f"{where} 缺 walkthrough.framework")
    else:
        steps = fw.get("steps")
        if not isinstance(steps, list) or len(steps) < MIN_STEPS:
            rep.err(f"{where} framework.steps 少于 {MIN_STEPS} 步")
        else:
            for i, s in enumerate(steps):
                if not isinstance(s, str) or len(s.strip()) < 4:
                    rep.err(f"{where} framework.steps[{i}] 过短或非字符串")
        if not str(fw.get("title", "")).strip():
            rep.err(f"{where} framework 缺 title（题型名）")
        pid = fw.get("pattern")
        if pid and pid not in patterns:
            rep.err(f"{where} framework.pattern={pid} 不在任何框架文件中")
        if len(str(fw.get("trap") or "").strip()) < 6:
            rep.err(f"{where} framework 缺 trap（这一步最容易错在哪）")

    ap = w.get("approach")
    if not isinstance(ap, str) or len(ap.strip()) < MIN_APPROACH:
        rep.err(f"{where} approach 少于 {MIN_APPROACH} 字")

    pts = w.get("points")
    if not isinstance(pts, list) or not pts:
        rep.err(f"{where} points 为空（至少要标 1 个知识点）")
    else:
        for i, p in enumerate(pts):
            if not isinstance(p, dict):
                rep.err(f"{where} points[{i}] 不是对象")
                continue
            kid = p.get("id", "")
            if kid not in k_index:
                rep.err(f"{where} points[{i}].id={kid} 不存在于 knowledge/")
            if not str(p.get("note", "")).strip():
                rep.err(f"{where} points[{i}] 缺 note（这道题具体考它的哪一面）")
            if not str(p.get("title", "")).strip():
                rep.err(f"{where} points[{i}] 缺 title（知识点名称，不能只给 id）")
            if len(str(p.get("core", "")).strip()) < 10:
                rep.err(f"{where} points[{i}] 缺 core（知识点的核心结论）")

    sol = w.get("solution")
    need = MIN_SOLUTION_OBJ if q.get("type") in {"choice", "multi"} else MIN_SOLUTION
    if not isinstance(sol, str) or len(sol.strip()) < need:
        rep.err(f"{where} solution 少于 {need} 字")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    rep = Report()
    defs = exam_defs()

    # ---------------- 知识点与题型索引 ----------------
    k_index: dict[str, dict] = {}
    k_by_topic: dict[str, set[str]] = defaultdict(set)
    topic_owner: dict[str, tuple[str, str]] = {}
    patterns: dict[str, str] = {}

    for exam in defs:
        for s in exam["subjects"]:
            subj = s["key"]
            data = load_json(EXAM / "knowledge" / f"{exam['key']}-{subj}.json", rep)
            if data:
                for topic in data.get("items", []):
                    tid = topic.get("topic", "")
                    if tid in topic_owner:
                        rep.err(f"专题 id 重复：{tid}（{topic_owner[tid]} 与 {exam['key']}/{subj}）")
                    topic_owner[tid] = (exam["key"], subj)
                    for k in topic.get("knowledge", []):
                        kid = k.get("id", "")
                        if not kid:
                            rep.err(f"{exam['key']}/{subj} 有知识点缺 id（topic={tid}）")
                            continue
                        if kid in k_index:
                            rep.err(f"知识点 id 重复：{kid}")
                        k_index[kid] = {"title": k.get("title", ""), "topic": tid,
                                        "subject": subj, "exam": exam["key"]}
                        k_by_topic[tid].add(kid)

            fw = load_json(fw_path(exam["key"], subj), rep)
            if fw:
                for t in fw.get("topics", []):
                    for p in t.get("patterns", []):
                        pid = p.get("id", "")
                        if not pid:
                            rep.err(f"{exam['key']}/{subj} 有题型缺 id")
                        elif pid in patterns:
                            rep.err(f"题型 id 重复：{pid}")
                        else:
                            patterns[pid] = fw.get("key", subj)

    # ---------------- 题库 ----------------
    all_ids: set[str] = set()
    by_topic: dict[str, list[dict]] = defaultdict(list)
    type_cnt: Counter[str] = Counter()
    per_exam: dict[str, int] = Counter()
    total = 0

    for exam in defs:
        for s in exam["subjects"]:
            subj = s["key"]
            data = load_json(EXAM / "questions" / f"{exam['key']}-{subj}.json", rep)
            if not data:
                continue
            items = data.get("items", [])
            if not items:
                rep.warn(f"{exam['key']}/{subj} 题库为空")
            for idx, q in enumerate(items):
                total += 1
                per_exam[exam["key"]] += 1
                qid = q.get("id", "")
                where = f"{exam['key']}/{subj}[{idx}] {qid or '<无 id>'}"
                if not qid:
                    rep.err(f"{where} 缺 id")
                elif qid in all_ids:
                    rep.err(f"{where} id 重复")
                else:
                    all_ids.add(qid)

                typ = q.get("type")
                if typ not in VALID_TYPES:
                    rep.err(f"{where} type={typ} 非法")
                type_cnt[typ or "?"] += 1

                if not str(q.get("stem", "")).strip():
                    rep.err(f"{where} 缺题干")

                opts = q.get("options") or []
                ans = (q.get("answer") or {}).get("correct")
                if typ == "choice":
                    if len(opts) < 2:
                        rep.err(f"{where} 选择题选项少于 2 个")
                    if not isinstance(ans, int) or not (0 <= ans < len(opts)):
                        rep.err(f"{where} answer.correct 越界（{ans}）")
                elif typ == "multi":
                    if len(opts) < 3:
                        rep.err(f"{where} 多选题选项少于 3 个")
                    if not isinstance(ans, list) or len(ans) < 2:
                        rep.err(f"{where} multi 的 answer.correct 必须是至少两个下标的数组")
                    elif any(not isinstance(i, int) or not (0 <= i < len(opts)) for i in ans):
                        rep.err(f"{where} multi 的 answer.correct 有越界下标")
                elif typ in {"blank", "calc", "design"}:
                    txt = (q.get("answer") or {}).get("text")
                    if not str(txt or "").strip():
                        rep.err(f"{where} 主观题缺 answer.text")

                kid = q.get("knowledge", "")
                if kid not in k_index:
                    rep.err(f"{where} knowledge={kid} 不存在于 knowledge/")
                elif k_index[kid]["exam"] != exam["key"] or k_index[kid]["subject"] != subj:
                    rep.err(f"{where} knowledge={kid} 不属于本学科")

                tid = q.get("topic", "")
                if tid not in k_by_topic:
                    rep.err(f"{where} topic={tid} 不在 knowledge/ 的专题里")
                elif topic_owner.get(tid) != (exam["key"], subj):
                    rep.err(f"{where} topic={tid} 不属于本学科")

                for p in (q.get("walkthrough") or {}).get("points", []) or []:
                    pk = p.get("id", "") if isinstance(p, dict) else ""
                    if pk in k_index and (k_index[pk]["exam"], k_index[pk]["subject"]) != (exam["key"], subj):
                        rep.warn(f"{where} 引用了其它学科的知识点 {pk}")

                check_walkthrough(q, where, k_index, patterns, rep)
                by_topic[tid].append(q)

    # ---------------- 分类总结 ----------------
    sum_done = 0
    for exam in defs:
        for s in exam["subjects"]:
            subj = s["key"]
            data = load_json(EXAM / "summaries" / f"{exam['key']}-{subj}.json", rep)
            if not data:
                continue
            groups = data.get("groups", [])
            seen_topics: set[str] = set()
            for gi, g in enumerate(groups):
                tid = g.get("topic", "")
                where = f"summary {exam['key']}/{subj}[{gi}] {tid or '<无 topic>'}"
                if tid in seen_topics:
                    rep.err(f"{where} 重复分类")
                seen_topics.add(tid)
                if tid not in k_by_topic:
                    rep.err(f"{where} 不是合法专题")
                    continue
                if not str(g.get("recognize", "")).strip():
                    rep.err(f"{where} 缺 recognize（怎么认出这类题）")
                fw = g.get("framework")
                if not isinstance(fw, list) or len(fw) < MIN_STEPS:
                    rep.err(f"{where} framework 少于 {MIN_STEPS} 步")
                skills = g.get("skills") or []
                if len(skills) < MIN_SUMMARY_SKILLS:
                    rep.err(f"{where} 缺 skills（解题技巧）")
                for si, sk in enumerate(skills):
                    if not isinstance(sk, dict):
                        rep.err(f"{where} skills[{si}] 不是对象（需 {{title, body}}）")
                        continue
                    if not str(sk.get("title", "")).strip():
                        rep.err(f"{where} skills[{si}] 缺 title")
                    if len(str(sk.get("body", "")).strip()) < 10:
                        rep.err(f"{where} skills[{si}] body 过短")
                if not g.get("traps"):
                    rep.err(f"{where} 缺 traps（易错点）")

                ids = g.get("questionIds") or []
                real = {q["id"] for q in by_topic.get(tid, []) if q.get("id")}
                if set(ids) != real:
                    miss = real - set(ids)
                    extra = set(ids) - real
                    if miss:
                        rep.err(f"{where} 漏统计题目 {sorted(miss)[:3]}")
                    if extra:
                        rep.err(f"{where} 统计了不存在的题目 {sorted(extra)[:3]}")
                sum_done += 1

            have = {t for t in by_topic if by_topic[t]}
            for t in have - seen_topics:
                if topic_owner.get(t) == (exam["key"], subj):
                    rep.err(f"{exam['key']}/{subj} 专题 {t} 有题目但缺分类总结")

    # ---------------- 套卷 ----------------
    paper_cnt = 0
    paper_by_exam: Counter[str] = Counter()
    for path in sorted((EXAM / "papers").glob("*.json")):
        data = load_json(path, rep)
        if not data:
            continue
        paper_cnt += 1
        paper_by_exam[data.get("exam", "?")] += 1
        pid = data.get("id", path.stem)
        where0 = f"paper {pid}"
        if data.get("kind") != "mock":
            rep.err(f"{where0} kind 必须是 mock（合规：不还原真题）")
        if not str(data.get("disclaimer", "")).strip():
            rep.err(f"{where0} 缺 disclaimer（必须声明非真题）")
        paper_total = data.get("totalScore")
        sections = data.get("sections") or []
        sec_sum = sum(int(s.get("score") or 0) for s in sections)
        if paper_total != sec_sum:
            rep.err(f"{where0} 分值不配平：totalScore={paper_total}，各节合计={sec_sum}")

        for s in sections:
            sname = s.get("name", "?")
            swhere = f"{where0} · {sname}"
            styp = s.get("type")
            items = s.get("items") or []
            if not items:
                rep.err(f"{swhere} 无题目")
                continue
            if styp in {"choice", "multi"}:
                for qid in items:
                    if qid not in all_ids:
                        rep.err(f"{swhere} 引用了不存在的题目 {qid}")
                if s.get("perScore") and len(items) * int(s["perScore"]) != int(s.get("score") or 0):
                    rep.err(f"{swhere} 题数×每题分值 ≠ 本节总分")
            elif styp in INLINE_SECTIONS:
                local = set()
                for qi, q in enumerate(items):
                    qid = q.get("id", "")
                    aw = f"{swhere}[{qi}] {qid or '<无 id>'}"
                    if not qid:
                        rep.err(f"{aw} 缺 id")
                    elif qid in local:
                        rep.err(f"{aw} id 重复")
                    else:
                        local.add(qid)
                    if not str(q.get("stem", "")).strip():
                        rep.err(f"{aw} 缺题干")
                    if styp == "analysis" and not q.get("ask"):
                        rep.err(f"{aw} 缺 ask（分问要求）")
                    check_walkthrough(q, aw, k_index, patterns, rep)
                if sum(int(q.get("score") or 0) for q in items) != int(s.get("score") or 0):
                    rep.err(f"{swhere} 各题分值合计 ≠ 本节总分")
            else:
                rep.err(f"{swhere} type={styp} 非法")

    rep.stats = {
        "questions": total,
        "by_exam": dict(per_exam),
        "by_type": dict(type_cnt),
        "knowledge": len(k_index),
        "patterns": len(patterns),
        "summaries": sum_done,
        "papers": paper_cnt,
        "papers_by_exam": dict(paper_by_exam),
        "errors": len(rep.errors),
        "warns": len(rep.warns),
    }

    if args.json:
        print(json.dumps({"stats": rep.stats, "errors": rep.errors, "warns": rep.warns},
                         ensure_ascii=False, indent=1))
    else:
        print(f"题目 {total} 道 / 知识点 {len(k_index)} 个 / 分类总结 {sum_done} 份 / 套卷 {paper_cnt} 套")
        print(f"分考试：{dict(per_exam)}")
        print(f"题型分布：{dict(type_cnt)}")
        for w in rep.warns:
            print(f"  [warn] {w}")
        for e in rep.errors:
            print(f"  [ERR ] {e}")
        print("通过" if not rep.errors else f"失败：{len(rep.errors)} 项")

    return 0 if not rep.errors else 1


if __name__ == "__main__":
    sys.exit(main())
