"""把 content/agent（16 章）与 content/ml（9 章）并入前端的 ai 学科（方案 A）。

背景
--------------------------------------------------------------------
`content/agent/` 和 `content/ml/` 各有 7 类文件齐全的完整章节，但它们不在
`frontend/src/lib/subject.ts` 的学科胶囊里，`BUNDLE.chapters` 也没有对应键，
于是这些章节**在 UI 上永远选不到** —— 有内容、无入口。

方案 A：不新增学科（保持学科胶囊口径稳定），把两科挂到 `ai` 学科下。
`ai` 的 label 本来就是「AI / Agent 开发」，项目库已含 agent 项目，语义自洽。

分组映射（保留原子结构，不揉成一坨）：
    ai 原有 A1..A4  ── 深度学习 / 大模型 / 提示与知识增强 / Agent 工程化
    agent G1..G6    → A5..A10
    ml    C1..C3    → A11..A13
章节 order 从 9 续到 32（之后新增章节由 sync_bundle_chapters.py 续排）。

用法
--------------------------------------------------------------------
    python scripts/merge_agent_ml_into_ai.py            # dry-run
    python scripts/merge_agent_ml_into_ai.py --apply    # 写入 bundle.ts
    python scripts/merge_agent_ml_into_ai.py --restore  # 还原

注意：本脚本是 bundle.ts 生成链的**第 2 步** ——
    gen_bundle_data.py → merge_agent_ml_into_ai.py --apply → sync_bundle_chapters.py --write
单独重跑第 1 步会把合并打回三包（ai 从 39 章退回 14 章）。详见 CONTRIBUTING §10.2。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "frontend" / "src" / "data" / "bundle.ts"
CONTENT = ROOT / "content"
BACKUP = ROOT / "frontend" / "src" / "data" / "_backup_bundle"

BUNDLE_RE = re.compile(
    r"(export const BUNDLE = )(\{.*\})( as unknown as Bundle;)", re.S
)

# 源学科 → (目标分组起始序号, 分组短标签)
# 短标签是 UI 上直接显示的胶囊文字，不能用 manifest 里那句「认知与基座（DAY 1-7）：…」，
# 否则分组栏会被撑爆。
SOURCES: list[tuple[str, int, list[str]]] = [
    ("agent", 5, [
        "Agent · 认知与基座",
        "Agent · 知识与部署",
        "Agent · 原理与多模态",
        "Agent · 产品与系统",
        "Agent · 前沿与职业",
        "Agent · 交付与求职",
    ]),
    ("ml", 11, [
        "机器学习 · 监督学习",
        "机器学习 · 高级算法",
        "机器学习 · 无监督与强化",
    ]),
]


def load_manifest(sub: str) -> dict:
    p = CONTENT / sub / "_manifest.json"
    return json.loads(p.read_text(encoding="utf-8"))


def build_pack(ai_pack: dict) -> tuple[dict, list[str]]:
    """在 ai pack 上追加 agent/ml 章节，返回 (新 pack, 变更日志)。"""
    log: list[str] = []
    chapters: list[dict] = list(ai_pack.get("chapters") or [])
    groups: dict[str, str] = dict(ai_pack.get("groups") or {})
    used_ids = {c.get("id") for c in chapters}
    next_order = max([int(c.get("order") or 0) for c in chapters] or [0]) + 1

    for sub, start_idx, short_names in SOURCES:
        mf = load_manifest(sub)
        src_groups: dict[str, str] = mf.get("groups") or {}
        # 源组 key 按 manifest 里的出现顺序，依次映射到 A{n}，标签用短名
        gmap: dict[str, str] = {}
        for i, (gk, _gname) in enumerate(src_groups.items()):
            target = f"A{start_idx + i}"
            gmap[gk] = target
            groups[target] = short_names[i] if i < len(short_names) else f"{sub} 第 {i + 1} 组"

        added = 0
        for ch in mf.get("chapters") or []:
            cid = ch.get("id")
            if not cid or cid in used_ids:
                continue
            chapters.append({
                "id": cid,
                "order": next_order,
                "group": gmap.get(ch.get("group"), f"A{start_idx}"),
                "title": ch.get("title") or "",
                "summary": ch.get("summary") or "",
                "status": ch.get("status") or "complete",
                "prerequisites": ch.get("prerequisites") or [],
                "github": [],
                "github_stars": [],
                "books": ch.get("books") or [],
            })
            used_ids.add(cid)
            next_order += 1
            added += 1
        log.append(f"{sub}: +{added} 章, 组 {len(gmap)} 个")

    new_pack = dict(ai_pack)
    new_pack["groups"] = groups
    new_pack["chapters"] = chapters
    return new_pack, log


def rewrite_bundle(data: dict) -> str:
    text = BUNDLE.read_text(encoding="utf-8")
    m = BUNDLE_RE.search(text)
    if not m:
        raise SystemExit("bundle.ts 里没找到 `export const BUNDLE = {...} as unknown as Bundle;`")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text[: m.start(2)] + payload + text[m.end(2):]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP.exists():
            print("无备份")
            return 1
        snaps = sorted(p for p in BACKUP.iterdir() if p.is_dir())
        if not snaps:
            print("备份为空")
            return 1
        shutil.copy2(snaps[-1] / "bundle.ts", BUNDLE)
        print(f"已从 {snaps[-1].name} 还原 bundle.ts")
        return 0

    text = BUNDLE.read_text(encoding="utf-8")
    m = BUNDLE_RE.search(text)
    if not m:
        print("解析 BUNDLE 失败")
        return 1
    data = json.loads(m.group(2))
    ch = data.get("chapters") or {}
    if "ai" not in ch:
        print("bundle 里没有 ai 学科")
        return 1

    before = len(ch["ai"].get("chapters") or [])
    new_pack, log = build_pack(ch["ai"])
    ch["ai"] = new_pack
    after = len(new_pack["chapters"])

    # 首行注释里的「章节学科 12 个」保持不变（学科数没变），补一句说明
    text_new = rewrite_bundle(data)
    head_note = "/* 由 scripts/gen_bundle_data.py 从 content/ 生成，请勿手改。"
    if head_note in text_new and "agent/ml 并入 ai" not in text_new:
        text_new = text_new.replace(
            head_note,
            head_note + "\n   agent(16 章) 与 ml(9 章) 已按方案 A 并入 ai 学科（scripts/merge_agent_ml_into_ai.py）。",
            1,
        )

    print("==== 合并结果 ====")
    for line in log:
        print("  " + line)
    print(f"  ai 章节：{before} -> {after}")
    print(f"  ai 分组：{[f'{k}={v}' for k, v in new_pack['groups'].items()]}")
    ids = [c["id"] for c in new_pack["chapters"]]
    print(f"  agent 章在 ai 中：{len([i for i in ids if i.startswith('agent-')])}")
    print(f"  ml 章在 ai 中：{len([i for i in ids if i.startswith('ml-')])}")

    if args.apply:
        snap = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
        snap.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUNDLE, snap / "bundle.ts")
        BUNDLE.write_text(text_new, encoding="utf-8")
        print(f"\n已写入 bundle.ts。备份：{snap}")
    else:
        print("\n(dry-run，未写入)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
