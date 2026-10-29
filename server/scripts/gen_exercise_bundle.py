"""把 content/<subject>/<chapter>/exercises.json 打包成前端可用的题库模块。

为什么需要这一步
--------------------------------------------------------------------
`frontend/src/data/bundle.ts` 只打包了 projects / chapters / guides，
818 道练习题从来没有进过安装包 —— 桌面端和手机端都是「题库存在但看不见」。
后端虽有 /api/v1/exercises，但需要 PostgreSQL，而 exe/apk 是离线单机，
不能指望一个数据库。

所以这里把题库直接编成 TS 常量，和 bundle 一样的思路：离线、零配置、双端一致。

answer 字段为什么要归一化
--------------------------------------------------------------------
818 道题的 `answer` 有 20 多种键组合（correct / value / index / choice /
output / expected_output / stdout / reference_code / code / explain /
explanation / explanation_md / fix_explanation_md / reference / reference_text /
text ...）。如果让 UI 自己判断，每加一种形态就要改一次前端，必然出漏。
这里一次性收敛成 7 个字段，并**记录每一道题实际用到了哪个原键**（供排查）。
原文件不动 —— 归一化只发生在产物里。

用法
--------------------------------------------------------------------
    python server/scripts/gen_exercise_bundle.py            # 生成
    python server/scripts/gen_exercise_bundle.py --check    # 只统计不写文件
    python server/scripts/gen_exercise_bundle.py --json     # 打印统计
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
OUT = ROOT / "frontend" / "src" / "data" / "exercises.ts"
DERIVED = CONTENT / "_derived_cases.json"

TYPES = ("choice", "coding", "output", "fix_error", "explain", "design")
DIFFS = ("easy", "medium", "hard")

# 方案 A：agent(16 章) 与 ml(8 章) 挂到 ai 学科下（见 scripts/merge_agent_ml_into_ai.py）。
# 这里必须在打题时就把 subj 归一，否则前端按 SUBJECTS 过滤题库时这 144 道题
# 会因为 subj="agent"/"ml" 而永远筛不出来。
SUBJ_ALIAS = {"agent": "ai", "ml": "ai"}


# --------------------------------------------------------------------------
# 语言推断
# --------------------------------------------------------------------------
def infer_lang(subject: str, code: str | None, hint: str | None = None) -> str | None:
    """推断这道题该用什么语言判。

    先看 hint（题库里少数题会写 language），再用参考代码的语法特征，
    最后退回学科默认值。顺序不能反：同一个学科里会混语言
    （bigdata 有 Python 也有 SQL，fullstack 有 JS 也有 Python）。
    """
    if hint:
        h = hint.strip().lower()
        if h in {"python", "py", "python3"}:
            return "python"
        if h in {"c"}:
            return "c"
        if h in {"cpp", "c++"}:
            return "cpp"
        if h == "java":
            return "java"
        if h in {"js", "javascript", "ts", "typescript"}:
            return "js"
        if h == "sql":
            return "sql"
        if h in {"bash", "sh", "shell"}:
            return "shell"

    c = code or ""
    # 顺序有意为之：Java 的 System.out.println 里也有 "print"，
    # C++ 的 printf 里也有 "c"，所以强特征必须先判。
    if re.search(r"\bpublic\s+(final\s+)?class\b|\bSystem\.out\.print|\bimport\s+java\.", c):
        return "java"
    if re.search(r"^\s*#\s*include\s*<(iostream|vector|string|algorithm|bits/stdc\+\+\.h)>", c, re.M):
        return "cpp"
    if re.search(r"\bstd::|\bcout\s*<<|\busing\s+namespace\s+std\b|#include\s*<bits/", c):
        return "cpp"
    if re.search(r"^\s*#\s*include\s*<stdio\.h>", c, re.M) and not re.search(r"\bstd::|\bcout\b", c):
        return "c"
    if re.search(r"^\s*(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|EXPLAIN)\b", c, re.M | re.I):
        return "sql"
    if re.search(r"^\s*def\s+\w+\s*\(|^\s*import\s+\w+|^\s*from\s+\w+\s+import\b|\bprint\(", c, re.M):
        return "python"
    if re.search(r"\bfunction\s+\w+\s*\(|=>|\bconst\s+\w+\s*=|console\.log|\brequire\(", c):
        return "js"
    if re.search(r"^\s*(docker|git|kubectl|systemctl|sudo|apt|make|gcc|g\+\+)\b", c, re.M):
        return "shell"

    # 学科兜底
    return {
        "clang": "c",
        "cpp": "cpp",
        "java": "java",
        "spring": "java",
        "python": "python",
        "ai": "python",
        "data": "python",
        "bigdata": "python",
        "tooling": "shell",
        "database": "sql",
        "middleware": "sql",
        "fundamentals": "c",
        "fullstack": "js",
        "agent": "python",
        "ml": "python",
    }.get(subject)


# --------------------------------------------------------------------------
# answer 归一化
# --------------------------------------------------------------------------
def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, (int, float)):
        return [str(v)]
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return []


def _letter_of_index(i: int) -> str:
    return chr(ord("A") + i) if 0 <= i < 26 else str(i)


def _norm_options(raw) -> list[dict]:
    """把选项归一成 [{key,text}]。

    兼容三种写法：
      1) [{"key": "A", "text": "..."}]        —— 标准写法，原样保留
      2) ["A. 文本", "B. 文本", ...]          —— 文本自带字母前缀
      3) ["文本1", "文本2", ...]              —— 纯文本，按顺序补 A/B/C/D
    """
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for i, o in enumerate(raw):
        if isinstance(o, dict):
            key = o.get("key")
            text = o.get("text")
            if key and isinstance(text, str):
                out.append({"key": str(key).strip().upper(), "text": text})
            elif isinstance(text, str):
                out.append({"key": _letter_of_index(i), "text": text})
            continue
        if isinstance(o, (int, float)):
            out.append({"key": _letter_of_index(i), "text": str(o)})
            continue
        if not isinstance(o, str):
            continue
        m = re.match(r"^\s*([A-Za-z])\s*[.、)．]\s*(.+)$", o)
        if m:
            out.append({"key": m.group(1).upper(), "text": m.group(2).strip()})
        else:
            out.append({"key": _letter_of_index(i), "text": o.strip()})
    return out


def _coerce_correct(correct: list[str]) -> list[str]:
    """把 ["1"] / ["0"] 这类下标型答案转成 ["B"] / ["A"]。"""
    out: list[str] = []
    for c in correct:
        s = str(c).strip()
        if s.isdigit():
            out.append(_letter_of_index(int(s)))
        else:
            out.append(s.upper() if len(s) == 1 and s.isalpha() else s)
    return out


def normalize_answer(item: dict) -> tuple[dict, list[str]]:
    """把一题的 answer 拆成统一字段，同时返回用到了哪些原键（审计用）。

    返回字段：
        correct  选择题/判断题的正确答案（字母数组，或判断题的文本结论）
        expect   题目本身给出的期望输出
        code     参考代码
        note     参考答案的补充说明（非代码的长文）
        explain  解析
        external 外链
    """
    a = item.get("answer")
    used: list[str] = []
    out: dict = {}

    if isinstance(a, str):
        out["note"] = a
        used.append("answer(str)")
        a = {}
    elif not isinstance(a, dict):
        a = {}

    def take(key: str):
        if key in a and a[key] not in (None, "", [], {}):
            used.append(f"answer.{key}")
            return a[key]
        return None

    # --- 正确答案 ---
    correct = _as_list(take("correct"))
    # 判断题常见的等价写法：单字母 / 索引 / 文本结论
    for k in ("choice", "value"):
        v = take(k)
        if v is None:
            continue
        if isinstance(v, str) and len(v) == 1 and v.isalpha():
            correct = correct or [v.upper()]
        elif isinstance(v, str):
            # {"value": "[('a','1')]"} 这类是期望输出，不是选项
            out.setdefault("expect", v)
        else:
            out.setdefault("expect", str(v))
    idx = take("index")
    if isinstance(idx, int) and not correct:
        correct = [_letter_of_index(idx)]
    if correct:
        out["correct"] = _coerce_correct(correct)

    # --- 期望输出 ---
    for k in ("output", "expected_output", "stdout"):
        v = take(k)
        if isinstance(v, str) and v.strip():
            out["expect"] = v
            break

    # --- 参考代码 ---
    for k in ("reference_code", "code"):
        v = take(k)
        if isinstance(v, str) and v.strip():
            out["code"] = v
            break

    # --- 参考答案文本 ---
    for k in ("reference", "reference_text", "text", "tests_md", "external_note"):
        v = take(k)
        if isinstance(v, str) and v.strip():
            out.setdefault("note", v)
            break

    # --- 解析：题目顶层的 explanation 优先（它才是给人看的解说）---
    for src, key in (
        (item, "explanation"),
        (a, "explanation"),
        (a, "explain"),
        (a, "explanation_md"),
        (a, "fix_explanation_md"),
    ):
        v = src.get(key)
        if isinstance(v, str) and v.strip():
            out["explain"] = v
            break

    if item.get("explanation"):
        used.append("explanation")

    ext = item.get("external_url")
    if isinstance(ext, str) and ext.strip():
        out["external"] = ext

    return out, used


def normalize_cases(item: dict) -> list[dict]:
    """test_cases → 判题台 TestCase。只保留 input/expected_output 都像样的。"""
    raw = item.get("test_cases") or []
    cases = []
    for i, tc in enumerate(raw):
        if not isinstance(tc, dict):
            continue
        stdin = tc.get("input")
        exp = tc.get("expected_output")
        if exp is None:
            exp = tc.get("expected")
        if not isinstance(stdin, str) or not isinstance(exp, str):
            continue
        name = tc.get("name") or (f"样例 {i + 1}" if tc.get("is_sample") else f"用例 {i + 1}")
        cases.append({"name": name, "stdin": stdin, "expected": exp})
    return cases


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def chapter_titles() -> dict[str, dict]:
    """chapter id → {title, order, subject}。用来在题库里显示章节名。"""
    idx = {}
    for mf in CONTENT.glob("*/_manifest.json"):
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        subj = mf.parent.name
        for c in m.get("chapters", []):
            idx[c["id"]] = {
                "title": c.get("title", ""),
                "order": c.get("order", 0),
                "subject": subj,
            }
        # C 语言单元挂在 cpp 的 clang_module 下，不是 chapters 数组，
        # 但它们是真实存在的 7 个单元，必须让题库认得自己的章节名。
        for u in (m.get("clang_module") or {}).get("units") or []:
            if u.get("id"):
                idx[u["id"]] = {"title": u.get("title", ""), "order": u.get("order") or 0, "subject": "clang"}
    return idx


def load_derived() -> dict:
    """可选：外部补出来的用例（由 promote_outputs.py 验证后写入）。"""
    if DERIVED.exists():
        try:
            return json.loads(DERIVED.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def build() -> tuple[list[dict], dict]:
    titles = chapter_titles()
    derived = load_derived().get("cases", {})
    items: list[dict] = []
    audit: dict = {
        "types": {},
        "diffs": {},
        "answer_keys": {},
        "langs": {},
        "with_cases": 0,
        "derived_cases": 0,
        "missing_manifest": [],
    }
    seen: set[str] = set()

    for f in sorted(CONTENT.glob("*/*/exercises.json")):
        subj = SUBJ_ALIAS.get(f.parent.parent.name, f.parent.parent.name)
        ch = f.parent.name
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] {f}: {e}", file=sys.stderr)
            continue
        raw_items = doc.get("items") if isinstance(doc, dict) else doc
        if not isinstance(raw_items, list):
            continue
        if ch not in titles:
            audit["missing_manifest"].append(ch)

        for i, it in enumerate(raw_items):
            if not isinstance(it, dict):
                continue
            etype = it.get("type") if it.get("type") in TYPES else "coding"
            diff = it.get("difficulty") if it.get("difficulty") in DIFFS else "medium"

            eid = str(it.get("id") or f"{ch}-{i + 1:02d}")
            if eid in seen:
                # 全局递增计数，保证跨章节唯一（同一显式 id 出现在多个章节时不会撞车）
                _c = 1
                while f"{eid}-{_c}" in seen:
                    _c += 1
                eid = f"{eid}-{_c}"
            seen.add(eid)

            md = it.get("content_md") or it.get("stem_md") or ""
            ans, used = normalize_answer(it)

            # 选项：兼容 [{key,text}] / ["A. 文本"] / ["文本"] 三种写法
            options = _norm_options(it.get("options"))

            cases = normalize_cases(it)
            if not cases:
                d = derived.get(eid) or []
                for j, c in enumerate(d):
                    if isinstance(c, dict) and isinstance(c.get("stdin"), str) and isinstance(c.get("expected"), str):
                        cases.append({"name": c.get("name") or f"用例 {j + 1}", "stdin": c["stdin"], "expected": c["expected"]})
                if cases:
                    audit["derived_cases"] += 1
            if cases:
                audit["with_cases"] += 1

            lang = infer_lang(subj, ans.get("code"), it.get("language"))

            rec: dict = {
                "id": eid,
                "subj": subj,
                "ch": ch,
                "type": etype,
                "diff": diff,
                "title": it.get("title") or "(无标题)",
                "md": md,
            }
            if options:
                rec["options"] = options
            if ans.get("correct"):
                rec["correct"] = ans["correct"]
            if ans.get("expect"):
                rec["expect"] = ans["expect"]
            if ans.get("code"):
                rec["code"] = ans["code"]
            if ans.get("note"):
                rec["note"] = ans["note"]
            if ans.get("explain"):
                rec["explain"] = ans["explain"]
            if ans.get("external"):
                rec["external"] = ans["external"]
            if it.get("tags"):
                rec["tags"] = [str(t) for t in it["tags"]][:8]
            if lang:
                rec["lang"] = lang
            if cases:
                rec["cases"] = cases
            ref = it.get("source_ref") or it.get("external_id") or it.get("source")
            if ref:
                rec["src"] = str(ref)[:160]

            items.append(rec)

            audit["types"][etype] = audit["types"].get(etype, 0) + 1
            audit["diffs"][diff] = audit["diffs"].get(diff, 0) + 1
            k = "+".join(used) or "(empty)"
            audit["answer_keys"][k] = audit["answer_keys"].get(k, 0) + 1
            if lang:
                audit["langs"][lang] = audit["langs"].get(lang, 0) + 1

    return items, audit


HEADER = """/* 由 server/scripts/gen_exercise_bundle.py 从 content/ 生成，请勿手改。   {n} 题 / {subjects} 学科；带判题用例 {wc} 题。
   重新生成：python server/scripts/gen_exercise_bundle.py */

/* eslint-disable */

/** 题型。choice=选择、coding=编程、output=看代码写输出、fix_error=找错改错、
 *  explain=问答、design=设计/实践题。 */
export type BankType = {type_union};

export type BankDiff = 'easy' | 'medium' | 'hard';

export interface BankCase {{
  name: string;
  stdin: string;
  expected: string;
}}

export interface BankOption {{
  key: string;
  text: string;
}}

/** 一道题。字段全部可选片段化 —— 不是每种题型都有选项或参考代码。 */
export interface BankExercise {{
  /** 稳定 id，形如 cpp-ch01-03 */
  id: string;
  /** 学科 key，与 BundleProject.track / BUNDLE.chapters 的键一致 */
  subj: string;
  /** 章节 id，与 BUNDLE.chapters[*].chapters[*].id 一致 */
  ch: string;
  type: BankType;
  diff: BankDiff;
  title: string;
  /** Markdown 题面 */
  md: string;
  options?: BankOption[];
  /** 客观题的正确选项（字母），判断题可能是整句结论 */
  correct?: string[];
  /** 题目自带的期望输出 */
  expect?: string;
  /** 参考代码 */
  code?: string;
  /** 参考答案的文字说明（不是解析） */
  note?: string;
  /** 解析 */
  explain?: string;
  /** 外链（LeetCode/牛客原题等） */
  external?: string;
  tags?: string[];
  /** 推断出的判题语言 */
  lang?: string;
  /** 可直接判题的用例；有它才能「去判题台」 */
  cases?: BankCase[];
  /** 来源标注 */
  src?: string;
}}

"""


CLANG_OUT = ROOT / "frontend" / "src" / "data" / "clangUnits.ts"

CLANG_HEADER = """/* 由 server/scripts/gen_exercise_bundle.py 从 content/cpp/_manifest.json
   的 clang_module.units 生成，请勿手改。

   为什么单独一个文件：C 语言的 7 个单元在 cpp 的 manifest 里是「平级模块」，
   从来没有进过 BUNDLE.chapters。结果 SUBJECTS 里有「C 语言」这一项，
   切过去却是一张空页（7 单元 × 15 题 = 105 道题无法到达）。
   这里把它们摊平成和 BundleChapter 同构的形状，学习页直接 concat 即可。 */

/* eslint-disable */
import type { BundleChapter } from './bundle';

/** C 语言的 7 个单元，字段与 BundleChapter 同构，学习页可直接 concat。 */
export const CLANG_CHAPTERS: BundleChapter[] = """


def _first_paragraph(md_path: pathlib.Path, limit: int = 220) -> str:
    """取 goals.md 的第一段正文当摘要（去掉标题、列表符与行内标记）。"""
    if not md_path.exists():
        return ""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return ""
    for block in re.split(r"\n\s*\n", text):
        lines = [
            ln.strip()
            for ln in block.splitlines()
            if ln.strip() and not ln.lstrip().startswith(("#", "|", "```", ">"))
        ]
        if not lines:
            continue
        s = " ".join(ln.lstrip("-*0123456789. ").strip() for ln in lines)
        s = re.sub(r"[*`_\[\]]", "", s)
        s = re.sub(r"\([^)]*\)$", "", s).strip()
        if len(s) >= 20:
            return s[:limit] + ("…" if len(s) > limit else "")
    return ""


def build_clang_chapters() -> list[dict]:
    mf = CONTENT / "cpp" / "_manifest.json"
    if not mf.exists():
        return []
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return []
    units = (m.get("clang_module") or {}).get("units") or []
    out = []
    for i, u in enumerate(units):
        uid = u.get("id")
        if not uid:
            continue
        res = u.get("resources") or {}
        out.append(
            {
                "id": uid,
                "order": u.get("order") or i + 1,
                "group": "C 语言独立模块",
                "title": u.get("title") or uid,
                "summary": _first_paragraph(CONTENT / "clang" / uid / "goals.md"),
                "status": u.get("status") or "complete",
                "prerequisites": [units[i - 1]["id"]] if i > 0 else [],
                "github": [str(g) for g in res.get("github") or []],
                "github_stars": [int(s) for s in res.get("github_stars") or []],
                "books": [str(b) for b in res.get("books") or []],
            }
        )
    return out


def emit_clang_ts(chapters: list[dict]) -> str:
    body = json.dumps(chapters, ensure_ascii=False, separators=(",", ":"))
    return f"{CLANG_HEADER}{body};\n"


def emit_ts(items: list[dict], audit: dict) -> str:
    type_union = " | ".join(f"'{t}'" for t in TYPES)
    subjects = len({i["subj"] for i in items})
    body = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    head = HEADER.format(n=len(items), subjects=subjects, wc=audit["with_cases"], type_union=type_union)
    return f"{head}export const EXERCISES: BankExercise[] = {body};\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只统计，不写文件")
    ap.add_argument("--json", action="store_true", help="打印统计 JSON")
    args = ap.parse_args()

    items, audit = build()

    if args.json:
        print(json.dumps({"total": len(items), **audit}, ensure_ascii=False, indent=2))
    else:
        print(f"题库：{len(items)} 题，覆盖 {len({i['subj'] for i in items})} 学科")
        print("题型：", ", ".join(f"{k}={v}" for k, v in sorted(audit["types"].items())))
        print("难度：", ", ".join(f"{k}={v}" for k, v in sorted(audit["diffs"].items())))
        print("语言：", ", ".join(f"{k}={v}" for k, v in sorted(audit["langs"].items())))
        print(f"可直接判题：{audit['with_cases']} 题（其中外部补出 {audit['derived_cases']} 题）")
        if audit["missing_manifest"]:
            print("[warn] 以下章节没有 manifest 条目：", ", ".join(audit["missing_manifest"]), file=sys.stderr)

    if args.check:
        return 0

    ts = emit_ts(items, audit)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(ts, encoding="utf-8")
    kb = len(ts.encode()) / 1024
    print(f"写入 {OUT.relative_to(ROOT)}（{kb:.0f} KB）")

    clang = build_clang_chapters()
    if clang:
        CLANG_OUT.write_text(emit_clang_ts(clang), encoding="utf-8")
        print(f"写入 {CLANG_OUT.relative_to(ROOT)}（{len(clang)} 个 C 语言单元）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
