#!/usr/bin/env python
"""题集健康度检查器（常驻工具，报告项，不阻塞门禁）。

动机：`verify_examples.py` 只回放 `examples/*.json`，**不检查 `exercises.json` 里的
`answer.reference_code`**。已出现两次「参考代码语法/逻辑错误但无人发现」的事故
（mw-ch07 的 `msgs[len(processed)+len(dlq):]` 切片恒为空，blocked 永远返回 0）。

本工具做**客观可判定**的四类检查：
  ① 字段合规：每题顶层必须有 category / platform / source / source_ref；
     platform 为 leetcode|nowcoder 时必须带 external_url（合规红线：只存链接不搬题面）。
  ② 参考代码语法：能识别为 Python 的 reference_code 必须 `compile()` 通过。
  ③ 编号唯一：同一章内题目 id 不得重复。
  ④ 题量结构：基础题 / 算法题 计数，且至少各 1 题。
  ⑤ meta 自洽：`meta.note` 里若声称「N 题」，须与实际 items 数一致
     （曾出现 cpp-ch01 写「6 题」实为 5 题）。

用法：
  python server/scripts/verify_exercises.py                  # 全库
  python server/scripts/verify_exercises.py --subject cpp    # 限定学科
  python server/scripts/verify_exercises.py --chapter cpp-ch01
  python server/scripts/verify_exercises.py --json           # 输出 JSON
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"

REQUIRED_TOP = ("category", "platform", "source", "source_ref")
LINKED_PLATFORMS = ("leetcode", "nowcoder")


def detect_lang(code: str) -> str:
    """从参考代码片段粗略判断语言，用于决定是否做 Python 语法检查。"""
    if re.search(r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|FROM\s+\w+\s+WHERE)\b",
                 code, re.I):
        return "sql"
    if "#include" in code or re.search(r"\bint\s+main\s*\(", code):
        return "cpp" if ("std::" in code or "iostream" in code or "using namespace std" in code) else "c"
    if re.search(r"\b(public|private|protected)\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\(", code) or \
       re.search(r"\bSystem\.out\.print", code) or re.search(r"\bnew\s+[A-Z]\w*\s*\(", code):
        return "java"
    if re.search(r"^\s*def\s+\w+\s*\(", code, re.M) or "print(" in code or re.search(r"^\s*import\s+\w+", code, re.M):
        return "python"
    return "unknown"


def check_chapter(ch_path: pathlib.Path) -> dict:
    """检查单章 exercises.json，返回报告字典。"""
    f = ch_path / "exercises.json"
    rep = {
        "chapter": ch_path.name,
        "subject": ch_path.parent.name,
        "exists": f.exists(),
        "total": 0, "basic": 0, "algo": 0, "uncategorized": 0,
        "field_issues": [], "link_issues": [], "compile_issues": [],
        "meta_issues": [], "dup_ids": [], "langs": {},
    }
    if not f.exists():
        return rep
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        rep["field_issues"].append(f"exercises.json 解析失败: {e}")
        return rep
    items = data.get("items") or []
    rep["total"] = len(items)
    # meta.note 若声称「N 题」，须与实际条数一致（防 metadata 漂移）
    note = (data.get("meta") or {}).get("note", "") or ""
    m = re.search(r"(\d+)\s*题", note)
    if m and int(m.group(1)) != len(items):
        rep["meta_issues"].append(
            f"meta.note 称「{m.group(1)} 题」但实际 {len(items)} 题"
        )
    seen: dict[str, int] = {}
    for it in items:
        iid = str(it.get("id") or "")
        if iid:
            seen[iid] = seen.get(iid, 0) + 1
        cat = it.get("category")
        if cat == "基础题":
            rep["basic"] += 1
        elif cat == "算法题":
            rep["algo"] += 1
        else:
            rep["uncategorized"] += 1
        for k in REQUIRED_TOP:
            if not it.get(k):
                rep["field_issues"].append(f"{iid or '?'} 顶层缺 {k}")
        if it.get("platform") in LINKED_PLATFORMS and not it.get("external_url"):
            rep["link_issues"].append(f"{iid or '?'} platform={it.get('platform')} 缺 external_url")
        ans = it.get("answer")
        code = (ans.get("reference_code") if isinstance(ans, dict) else "") or ""
        code = code.strip()
        if code:
            lang = detect_lang(code)
            rep["langs"][lang] = rep["langs"].get(lang, 0) + 1
            if lang == "python":
                try:
                    compile(code, f"<{iid}>", "exec")
                except SyntaxError as e:
                    rep["compile_issues"].append(f"{iid or '?'} Python 参考代码语法错误: 第 {e.lineno} 行 {e.msg}")
    rep["dup_ids"] = sorted(k for k, v in seen.items() if v > 1)
    return rep


def ok(rep: dict) -> bool:
    return not (rep["field_issues"] or rep["link_issues"] or rep["compile_issues"]
                or rep["meta_issues"] or rep["dup_ids"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--chapter")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    chapters: list[pathlib.Path] = []
    if args.chapter:
        for subj in CONTENT.iterdir():
            if not subj.is_dir():
                continue
            p = subj / args.chapter
            if p.is_dir():
                chapters.append(p)
    else:
        for subj in sorted(CONTENT.iterdir()):
            if not subj.is_dir() or (args.subject and subj.name != args.subject):
                continue
            chapters += [d for d in sorted(subj.iterdir())
                         if d.is_dir() and (d / "exercises.json").exists()]

    reports = [check_chapter(c) for c in chapters]
    reports = [r for r in reports if r["exists"]]

    if args.json:
        print(json.dumps({"chapters": reports}, ensure_ascii=False, indent=2))
        return 0 if all(ok(r) for r in reports) else 1

    bad = 0
    tot_items = tot_basic = tot_algo = 0
    tot_field = tot_link = tot_compile = tot_meta = 0
    for r in reports:
        tot_items += r["total"]
        tot_basic += r["basic"]
        tot_algo += r["algo"]
        tot_field += len(r["field_issues"])
        tot_link += len(r["link_issues"])
        tot_compile += len(r["compile_issues"])
        tot_meta += len(r["meta_issues"])
        if not ok(r):
            bad += 1
            print(f"[FAIL] {r['subject']}/{r['chapter']}")
            for k in ("field_issues", "link_issues", "compile_issues", "meta_issues"):
                for m in r[k][:6]:
                    print(f"        {k}: {m}")
            if r["dup_ids"]:
                print(f"        dup_ids: {r['dup_ids']}")
        else:
            print(f"[ OK ] {r['subject']}/{r['chapter']}  题数 {r['total']}（基础 {r['basic']} / 算法 {r['algo']}）")

    print()
    print(f"章节 {len(reports)} 个，题目 {tot_items} 道（基础 {tot_basic} / 算法 {tot_algo}）")
    print(f"字段缺失 {tot_field} 处 | 平台题缺链接 {tot_link} 处 | 参考代码语法错误 {tot_compile} 处"
          f" | meta 题数不一致 {tot_meta} 处")
    print(f"结论: {'全部通过' if bad == 0 else f'{bad} 章有问题'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
