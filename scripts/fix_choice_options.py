"""修复选择题的两类数据缺陷（可回滚、默认 dry-run）。

背景
--------------------------------------------------------------------
`content/<subject>/<chapter>/exercises.json` 里 320 道 choice 题中：
  1. 83 道题（agent / ml / ai / tooling 等学科）把选项**内联写在
     `content_md` 正文里**（形如 "A. 算力层\nB. 模型层..."），没有独立的
     `options` 数组 —— 前端 `gen_exercise_bundle.py` 只认 `options` 字段，
     于是这些题在 UI 上「有题目、无选项」，等于废题。
  2. 部分题的 `answer.correct` 是字符串 "A" 或 "A、C、D"，而非数组
     ["A"] / ["A","C","D"]；还有少量答案字母不在选项集合内。

本脚本做三件事（全部幂等，重复跑不会二次破坏）：
  A. 从 `content_md` / `stem_md` 解析行首选项（A. / A、 / A) / A: / A．），
     抽成 `options: [{key, text}]`，并从正文里剥离选项段。
  B. 把 `answer.correct` 规范化成大写字母数组（兼容 "A"、"A、C"、"AC"、
     整数下标）。
  C. 校验 correct ⊆ 选项 key；校验不了的题**不改答案**，只打印清单供人工处理。

原文件先整体备份到 `content/_backup_choice_fix/<时间戳>/`，随时可还原：
    python scripts/fix_choice_options.py --restore

用法
--------------------------------------------------------------------
    python scripts/fix_choice_options.py              # dry-run，只报告
    python scripts/fix_choice_options.py --apply      # 写入
    python scripts/fix_choice_options.py --apply -v   # 写入并逐题打印
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
BACKUP_ROOT = CONTENT / "_backup_choice_fix"

# 行首选项：A. / A、 / A) / A） / A: / A： / A． / （A） / (A)
OPT_LINE = re.compile(
    r"^\s*(?:[（(]?\s*([A-Ha-h])\s*[）)]?)\s*[.、,，)）:：．·]\s*(?=\S)(.+?)\s*$"
)
# 答案里的字母提取
ANS_LETTERS = re.compile(r"[A-H]")


def _is_choice(item: dict) -> bool:
    return (item.get("type") or "").lower() == "choice"


# 题库历史上用过 20 多种 answer 键名，选择题这里只需认出"哪个键装答案"
ANS_KEYS = ("correct", "choice", "value", "index", "option", "key")


def _answer_correct(item: dict) -> tuple[object, str | None]:
    """返回 (答案原值, 来源键名)。"""
    ans = item.get("answer")
    if isinstance(ans, dict):
        for k in ANS_KEYS:
            if ans.get(k) not in (None, "", [], {}):
                return ans[k], k
        return None, None
    return ans, "answer"


def _set_answer_correct(item: dict, letters: list[str], src_key: str | None) -> str:
    """把答案统一写到 `answer.correct`，并清掉旧键，避免出现两个答案源。

    返回被清理掉的旧键名（用于日志）。
    """
    ans = item.get("answer")
    if not isinstance(ans, dict):
        item["answer"] = {"correct": letters}
        return ""
    dropped = ""
    if src_key and src_key != "correct" and src_key in ans:
        ans.pop(src_key, None)
        dropped = src_key
    ans["correct"] = letters
    return dropped


def _strip_fenced_code(text: str) -> tuple[str, set[int]]:
    """把 ``` 围栏代码块的内容替换成空行（保留行号），返回 (新文本, 代码块行号集合)。

    为什么必须这么做：CppMind 大量题目题干里嵌 makefile / cpp / python 代码，
    代码中的 `C := $(D)`、`B = 1` 这类行会被「行首字母 + 分隔符」误判成选项，
    进而让选项序列变成 C,C,B,D 这种乱序，整体解析失败。
    """
    lines = text.split("\n")
    code_lines: set[int] = set()
    in_fence = False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            code_lines.add(i)
            continue
        if in_fence:
            code_lines.add(i)
    if not code_lines:
        return text, code_lines
    out = ["" if i in code_lines else ln for i, ln in enumerate(lines)]
    return "\n".join(out), code_lines


def parse_options_from_md(text: str) -> tuple[list[dict], str, str]:
    """从 Markdown 正文里抽出选项。

    返回 (options, 去掉选项后的正文, 说明)。
    只有当选项从 A 开始、连续、且 >= 2 项时才认为是选项段，
    避免把正文里的 "A. 某句中提到的" 误判成选项。
    """
    if not text:
        return [], text, "空正文"
    masked, code_lines = _strip_fenced_code(text)
    lines = masked.split("\n")
    hits: list[tuple[int, str, str]] = []  # (行号, key, 文本)
    for i, line in enumerate(lines):
        if i in code_lines:
            continue
        m = OPT_LINE.match(line)
        if m:
            hits.append((i, m.group(1).upper(), m.group(2).strip()))
    if len(hits) < 2:
        return [], text, f"内联选项行不足（{len(hits)}）"

    # 必须是 A,B,C... 连续序列，否则认为不是选项段
    keys = [h[1] for h in hits]
    expect = [chr(ord("A") + i) for i in range(len(keys))]
    if keys != expect:
        return [], text, f"选项不连续: {''.join(keys)}"

    options = [{"key": k, "text": t} for _, k, t in hits]
    # 剥离：删掉这些行（基于原文行号，两张表行号一致），以及它们紧邻的空行（尾部）
    drop = {h[0] for h in hits}
    raw_lines = text.split("\n")
    kept = [ln for i, ln in enumerate(raw_lines) if i not in drop]
    body = "\n".join(kept).rstrip()
    # 题干末尾若残留 "以下选项：" 之类的引导语，保留（无害）
    return options, body, f"解析出 {len(options)} 项"


def normalize_letters(raw) -> tuple[list[str], str]:
    """把各种答案形态统一成大写字母数组。"""
    if raw is None:
        return [], "空"
    if isinstance(raw, bool):
        return [], "bool"
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        i = int(raw)
        return ([chr(ord("A") + i)], f"整数下标 {i}") if 0 <= i < 8 else ([], f"下标越界 {i}")
    if isinstance(raw, (list, tuple, set)):
        out: list[str] = []
        for v in raw:
            ls, _ = normalize_letters(v)
            out.extend(ls)
        return sorted(set(out)), "数组"
    s = str(raw).strip()
    if not s:
        return [], "空串"
    up = s.upper()
    # 单独一个多字母串且全为字母（如 "ACD"、"BD"）
    if re.fullmatch(r"[A-H]+", up):
        return sorted(set(up)), f"字母串 {s!r}"
    letters = ANS_LETTERS.findall(up)
    if letters:
        return sorted(set(letters)), f"文本 {s!r}"
    return [], f"无法识别 {s!r}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入（默认 dry-run）")
    ap.add_argument("--restore", action="store_true", help="从最近一次备份还原")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP_ROOT.exists():
            print("没有找到备份目录", BACKUP_ROOT)
            return 1
        snaps = sorted([p for p in BACKUP_ROOT.iterdir() if p.is_dir()])
        if not snaps:
            print("备份目录为空")
            return 1
        snap = snaps[-1]
        n = 0
        for src in snap.rglob("exercises.json"):
            rel = src.relative_to(snap)
            dst = CONTENT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
        print(f"已从 {snap.name} 还原 {n} 个文件")
        return 0

    files = sorted(
        p for p in CONTENT.glob("*/*/exercises.json") if not p.parts[-3].startswith("_")
    )
    if not files:
        print("未找到任何 exercises.json")
        return 1

    snap_dir = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")

    stat = {
        "files": 0,
        "choice": 0,
        "opt_parsed": 0,       # A：从正文抽出选项
        "opt_failed": 0,
        "ans_fixed": 0,        # B：答案格式规范化
        "unresolved": [],      # C：仍需人工
    }

    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {fp}: {e}")
            continue
        items = data.get("items") or []
        changed = False
        stat["files"] += 1

        for it in items:
            if not isinstance(it, dict) or not _is_choice(it):
                continue
            stat["choice"] += 1
            eid = it.get("bundle_id") or it.get("id") or "?"

            # ---- A. 选项 ----
            opts = [o for o in (it.get("options") or []) if isinstance(o, dict) and o.get("key")]
            if len(opts) < 2:
                for field in ("content_md", "stem_md"):
                    md = it.get(field)
                    if not isinstance(md, str) or not md.strip():
                        continue
                    parsed, body, why = parse_options_from_md(md)
                    if parsed:
                        it["options"] = parsed
                        it[field] = body
                        opts = parsed
                        changed = True
                        stat["opt_parsed"] += 1
                        if args.verbose:
                            print(f"  [opt] {eid} <- {field} {why}")
                        break
                    elif args.verbose:
                        print(f"  [opt-skip] {eid} {field}: {why}")

            keys = {str(o.get("key")).upper() for o in opts}

            # ---- B. 答案 ----
            raw, src_key = _answer_correct(it)
            letters, how = normalize_letters(raw)
            if letters:
                already_ok = src_key == "correct" and isinstance(raw, list) and raw == letters
                if not already_ok:
                    dropped = _set_answer_correct(it, letters, src_key)
                    changed = True
                    stat["ans_fixed"] += 1
                    if args.verbose:
                        note = f" (原键 {dropped!r})" if dropped else ""
                        print(f"  [ans] {eid} {raw!r} -> {letters} ({how}){note}")

            # ---- C. 校验 ----
            if len(opts) < 2:
                stat["opt_failed"] += 1
                stat["unresolved"].append((str(fp.relative_to(ROOT)), eid, "缺选项", str(it.get("title"))[:40]))
            elif not letters:
                stat["unresolved"].append((str(fp.relative_to(ROOT)), eid, "答案空/无法解析", str(it.get("title"))[:40]))
            elif not set(letters).issubset(keys):
                stat["unresolved"].append(
                    (str(fp.relative_to(ROOT)), eid, f"答案 {letters} 不在 {sorted(keys)}", str(it.get("title"))[:40])
                )

        if changed and args.apply:
            snap_dir.mkdir(parents=True, exist_ok=True)
            rel = fp.relative_to(CONTENT)
            bak = snap_dir / rel
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak)
            fp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    print("\n==== 统计 ====")
    for k in ("files", "choice", "opt_parsed", "opt_failed", "ans_fixed"):
        print(f"  {k:12} {stat[k]}")
    print(f"  仍待人工     {len(stat['unresolved'])}")
    if stat["unresolved"]:
        print("\n==== 待人工清单 ====")
        for f, eid, why, title in stat["unresolved"]:
            print(f"  {f}  {eid}  [{why}]  {title}")
    if args.apply and stat["opt_parsed"] + stat["ans_fixed"]:
        print(f"\n已写入。备份：{snap_dir}")
        print("还原命令：python scripts/fix_choice_options.py --restore")
    elif not args.apply:
        print("\n(dry-run，未写入。加 --apply 生效)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
