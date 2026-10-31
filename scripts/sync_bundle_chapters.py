#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 content/<学科>/_manifest.json 里新增、但还没进 bundle.ts 的章节补进去。

【为什么需要这一步】
  frontend/src/data/bundle.ts 是「生成 + 一次合并补丁」的产物：
    gen_bundle_data.py 先按学科生成 agent / ml / ai 三包；
    merge_agent_ml_into_ai.py 再把 agent/ml 并进 ai（方案 A）。
  之后如果又往 content 里加了章节（例：ml-ch09 支持向量机），只重跑
  gen_bundle_data.py 会把合并打回三包，只跑 merge 又不会重新读 manifest，
  于是新章节永远到不了学习页 —— 内容在、题在、但地图上没有这一章。

【做法】
  只做加法：以 bundle 现状为基线，把 manifest 里有、bundle 里没有的章节
  按 merged 学科（agent/ml → ai）追加到对应包尾，order 取该包最大值 +1，
  group 用源 manifest 的组名，键统一编成 A<n> 继续排，避免和既有 A1..A13 撞。

  幂等：已经全在 bundle 里时不做任何写入。
  不触碰项目 / 指南 / 已有章节的任何字段（星标、读法、书单都不动）。

用法：
  python scripts/sync_bundle_chapters.py            # 报告差异
  python scripts/sync_bundle_chapters.py --write    # 真的写入
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "src" / "data" / "bundle.ts"

SUBJECT_ALIAS = {"agent": "ai", "ml": "ai"}

# 合并后的 ai 包用的是策展标签（"机器学习 · 监督学习"），
# 直接搬 ml 原标签（"课程一 · 监督学习…"）会在同一页里出现两种命名风格。
# 只给「新增组」补一条，既有 A1..A13 的标签一个字都不动。
GROUP_LABEL_OVERRIDE = {
    ("ai", "C4"): "机器学习 · 核方法与收口",
}

# 与 gen_bundle_data.py 的 load_chapters 保持同一口径：只取 UI 用得到的字段
def load_manifest_chapters() -> dict[str, dict]:
    packs: dict[str, dict] = {}
    for path in sorted((ROOT / "content").glob("*/_manifest.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        subject = d.get("subject") or path.parent.name
        subject = SUBJECT_ALIAS.get(subject, subject)
        pack = packs.setdefault(subject, {"groups": {}, "chapters": []})
        for k, v in (d.get("groups") or {}).items():
            pack["groups"].setdefault(k, v)
        for c in d.get("chapters") or []:
            res = c.get("resources") or {}
            pack["chapters"].append(
                {
                    "id": c["id"],
                    "order": c.get("order") or 0,
                    "group": c.get("group") or "",
                    "title": c.get("title") or "",
                    "summary": c.get("summary") or "",
                    "status": c.get("status") or "draft",
                    "prerequisites": c.get("prerequisites") or [],
                    "github": (res.get("github") or [])[:3],
                    "github_stars": (res.get("github_stars") or [])[:3],
                    "books": (res.get("books") or [])[:2],
                }
            )
    return packs


def split_bundle(text: str) -> tuple[str, dict]:
    """拆成「头部（含类型定义）」和 BUNDLE 对象，避免整文件重写类型。"""
    marker = "export const BUNDLE = "
    i = text.index(marker)
    head = text[:i]
    body = text[i + len(marker):]
    end = body.index(" as unknown as Bundle;")
    return head, json.loads(body[:end])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="真的写入 bundle.ts")
    args = ap.parse_args()

    text = OUT.read_text(encoding="utf-8")
    head, bundle = split_bundle(text)
    src_packs = load_manifest_chapters()

    added: list[str] = []
    for subject, pack in bundle["chapters"].items():
        have = {c["id"] for c in pack["chapters"]}
        src = src_packs.get(subject)
        if not src:
            continue
        next_order = max((c["order"] for c in pack["chapters"]), default=0) + 1
        # 下一个可用的 A 组编号
        used_groups = [int(m.group(1)) for k in pack["groups"] if (m := re.fullmatch(r"A(\d+)", k))]
        next_group = max(used_groups, default=0) + 1
        for c in src["chapters"]:
            if c["id"] in have:
                continue
            item = dict(c)
            item["order"] = next_order
            grp_label = GROUP_LABEL_OVERRIDE.get(
                (subject, c["group"]),
                src["groups"].get(c["group"], c["group"] or "未分组"),
            )
            gkey = f"A{next_group}"
            pack["groups"][gkey] = grp_label
            item["group"] = gkey
            pack["chapters"].append(item)
            added.append(f'{subject}: {c["id"]} · {c["title"][:28]} → {gkey}（order {next_order}）')
            next_order += 1
            next_group += 1

    missing_packs = sorted(set(src_packs) - set(bundle["chapters"]))
    for subject in missing_packs:
        print(f"! manifest 有 {subject} 学科，bundle 里没有这个包（本脚本不新建学科包）")

    if not added:
        print("bundle 已与 content 对齐，无需补章")
        return

    print(f"需要补 {len(added)} 章：")
    for line in added:
        print("  +", line)

    if not args.write:
        print("\n（只报告。加 --write 才写入）")
        return

    total = sum(len(p["chapters"]) for p in bundle["chapters"].values())
    head = re.sub(
        r"   项目 \d+ 条 / \d+h；.*?；指南 \d+ 条。 \*/",
        f"   项目 {bundle['projects']['total']} 条 / {bundle['projects']['hours']}h；"
        f"章节 {total} 章 / {len(bundle['chapters'])} 个学科；指南 {len(bundle['guides']['items'])} 条。 */",
        head,
        count=1,
        flags=re.S,
    )
    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(head + "export const BUNDLE = " + payload + " as unknown as Bundle;\n", encoding="utf-8")
    print(f"\n写入 {OUT.relative_to(ROOT)}：章节 {total} 章")


if __name__ == "__main__":
    main()
