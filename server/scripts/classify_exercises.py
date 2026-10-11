"""为存量 exercises.json 批量补齐「基础题 / 算法题」分类与来源平台。

背景：阶段 7 新增硬性要求——每道习题必须标注 category（基础题|算法题）与
platform（self|github|leetcode|nowcoder|book），以便在学习端区分题型并溯源。

分类规则（可重复执行，幂等）：
  - platform 为 leetcode / nowcoder / github  → category = 算法题（来自刷题平台/开源题单）
  - 其余（self / book，即教材知识点题、语法输出题、Debug 题）→ category = 基础题
  - platform 推断优先级：显式 platform > source 字段 > source_ref 文本线索
      * source_ref 含「LeetCode」→ leetcode；含「牛客」→ nowcoder
      * source_ref 含「github.com」→ github
      * source_ref 含《》→ book
      * 否则 self

用法：
    python server/scripts/classify_exercises.py [--content-dir content] [--dry-run]

--dry-run 只打印将要做的改动，不写盘。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_ALGO_PLATFORMS = ("leetcode", "nowcoder", "github")


def _infer_platform(item: dict) -> str:
    """推断题目来源平台。"""
    # 1) 显式声明
    p = item.get("platform")
    if p in ("self", "github", "leetcode", "nowcoder", "book"):
        return p
    # 2) source 字段（老数据用 source 记平台）
    src = item.get("source", "self")
    if src in _ALGO_PLATFORMS:
        return src
    # 3) source_ref 文本线索
    ref = f"{item.get('source_ref', '')} {item.get('external_url', '')}"
    if re.search(r"leetcode", ref, re.I):
        return "leetcode"
    if re.search(r"牛客|nowcoder", ref, re.I):
        return "nowcoder"
    if re.search(r"github\.com", ref, re.I):
        return "github"
    if "《" in ref or "〈" in ref:
        return "book"
    return "self"


def classify_item(item: dict) -> tuple[str, str, bool]:
    """返回 (category, platform, changed)。不覆盖已存在的合法 category。"""
    plat = _infer_platform(item)
    cat = item.get("category")
    changed = False
    if cat not in ("基础题", "算法题"):
        cat = "算法题" if plat in _ALGO_PLATFORMS else "基础题"
        item["category"] = cat
        changed = True
    if item.get("platform") != plat:
        item["platform"] = plat
        changed = True
    return cat, plat, changed


def main() -> int:
    ap = argparse.ArgumentParser(description="批量补齐习题分类（基础题/算法题）与来源平台")
    ap.add_argument("--content-dir", default="content")
    ap.add_argument("--dry-run", action="store_true", help="只预览不写盘")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent
    cdir = Path(args.content_dir)
    if not cdir.is_absolute():
        cdir = (repo_root / args.content_dir) if (repo_root / args.content_dir).exists() else (here.parent / args.content_dir)

    total_items = 0
    total_changed = 0
    stat: dict[str, dict[str, int]] = {}

    for ex_file in sorted(cdir.glob("*/**/exercises.json")):
        chapter = ex_file.parent.name
        try:
            data = json.loads(ex_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[SKIP] {ex_file}: JSON 解析失败 {e}")
            continue

        items = data.get("items", [])
        n_changed = 0
        counts = {"基础题": 0, "算法题": 0}
        for it in items:
            total_items += 1
            cat, plat, changed = classify_item(it)
            counts[cat] = counts.get(cat, 0) + 1
            if changed:
                n_changed += 1
        total_changed += n_changed
        stat[chapter] = counts

        tag = "DRY " if args.dry_run else "WRITE"
        print(f"[{tag}] {chapter}: 共 {len(items)} 题 → 基础题 {counts.get('基础题',0)} / 算法题 {counts.get('算法题',0)}（改动 {n_changed}）")

        if not args.dry_run and n_changed:
            ex_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("-" * 60)
    print(f"习题总数 {total_items} · 本次改动 {total_changed} 项" + ("（dry-run 未写盘）" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
