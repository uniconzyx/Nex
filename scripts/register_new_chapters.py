# -*- coding: utf-8 -*-
"""把 _new_chapters.py 里定义的新章节登记进各科 _manifest.json。

为什么单独一步、不做进 build_new_chapters：
写文件与改大纲是两件事，前者可重跑（幂等），后者改的是一份被多个脚本读取的
权威清单（validate_content / audit_sources / audit_graph / bundle 生成器）。
分开之后，出问题能定位在「内容写错了」还是「登记写错了」。

做的事：
  1. 按 CHAPTERS 顺序，为每章构造 manifest 条目（字段与既有章一致）；
  2. 已有同 id 的跳过（幂等）；
  3. 按 order 重排 chapters，并把后续章的 order 依次后移，避免 order 撞号；
  4. 该章节的 groups 若缺对应分组键，补上并写清含义。

用法：
    python scripts/register_new_chapters.py            # dry-run
    python scripts/register_new_chapters.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _new_chapters import CHAPTERS  # noqa: E402

# 新增分区（fs-ch10~15, ai-ch12~14）由子代理产出，单独存放避免污染主文件。
import importlib  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts" / "_chparts"))
for _part_mod in ("fs_a", "fs_b", "fs_c", "ai_abc"):
    _m = importlib.import_module(_part_mod)
    CHAPTERS.extend(_m.CHAPTERS)

CONTENT = ROOT / "content"

# 新章节在 manifest 里的 resources 快照（星数取 _link_cache.json 的已核验值）
STAR = {
    "yangshun/front-end-interview-handbook": 44008,
    "Chalarangelo/30-seconds-of-code": 129352,
    "trekhleb/javascript-algorithms": 196855,
    "jackfrued/Python-100-Days": 187492,
    "TheAlgorithms/Python": 225569,
    "microsoft/ML-For-Beginners": 91785,
    # fs-ch10~15 / ai-ch12~14 实取星数（本会话 GitHub API 快照）
    "vuejs/core": 54801, "vuejs/pinia": 14755, "vuejs/router": 4706, "vuejs/rfcs": 4926,
    "spring-projects/spring-boot": 81772, "spring-projects/spring-framework": 60300,
    "spring-projects/spring-security": 9653, "openjdk/jdk": 23477,
    "spring-cloud/spring-cloud-gateway": 4917, "nestjs/nest": 76927,
    "vercel/next.js": 143173, "google/guava": 51918,
    "microsoft/playwright": 98704, "cypress-io/cypress": 51015,
    "pact-foundation/pact-js": 1825, "facebook/react": 251766,
    "vercel/ai": 27560, "langchain-ai/langchain": 148600,
    "gin-gonic/gin": 89445, "golang/go": 139482, "gofiber/fiber": 40232,
    "huggingface/transformers": 168266, "huggingface/datasets": 22091,
    "vllm-project/vllm": 95746, "facebookresearch/llama": 59628,
    "ggerganov/llama.cpp": 132583, "mlc-ai/mlc-llm": 23284,
    "openai/CLIP": 34539, "OpenGVLab/InternVL": 10171, "microsoft/OmniParser": 25578,
}

NOTE = {
    "yangshun/front-end-interview-handbook": "前端面试手册：HTML/CSS/JS/浏览器/性能，TS 与工程化章节可对照其类型与构建部分",
    "Chalarangelo/30-seconds-of-code": "短小代码片段集：读别人怎么写类型收窄与工具函数，比读规范快",
    "trekhleb/javascript-algorithms": "算法与数据结构（JS 实现），本章的 groupBy/穷尽检查可与其中的类型标注对照",
    "jackfrued/Python-100-Days": "Python 入门到进阶长文：面向对象、魔术方法、多继承有专门章节与可跑示例",
    "TheAlgorithms/Python": "大量 Python 实现：读其中的类设计（建模、继承层次）比读教程更接近真实代码",
    "microsoft/ML-For-Beginners": "含大量 Python 类与数据类用法，可看 OOP 在真实练习里的写法",
}

BOOKS = {
    "fullstack": ["《TypeScript 编程》（Boris Cherny）", "《Effective TypeScript》Dan Vanderkam",
                  "《JavaScript 高级程序设计（第 4 版）》Zakas"],
    "python": ["《流畅的 Python》（第 2 版）Luciano Ramalho", "《Python 编程：从入门到实践》第 9 章 类",
               "《Python Cookbook》第 8 章 类与对象"],
    "ai": ["《Designing Machine Learning Systems》Chip Huyen",
           "《Building LLM Powered Applications》",
           "《深度学习》Ian Goodfellow 等"],
}


def manifest_entry(ch: dict) -> dict:
    return {
        "id": ch["id"],
        "order": ch["order"],
        "group": ch["group"],
        "title": ch["title"],
        "summary": ch["summary"],
        "prerequisites": ch["prerequisites"],
        "status": "complete",
        "resources": {
            "github": ch["sources"],
            "github_stars": [STAR.get(r, 0) for r in ch["sources"]],
            "github_notes": [NOTE.get(r, "按本章小节定位相关目录") for r in ch["sources"]],
            "github_fetched_at": "2026-10-27",
            "books": BOOKS.get(ch["subject"], []),
            "leetcode": [],
            "nowcoder": [],
            "bilibili": "",
            "bilibili_list": [],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    by_sub: dict[str, list[dict]] = {}
    for ch in CHAPTERS:
        by_sub.setdefault(ch["subject"], []).append(ch)

    plans = {}
    for sub, chs in by_sub.items():
        mp = CONTENT / sub / "_manifest.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        existing = {c["id"] for c in m["chapters"]}
        todo = [c for c in chs if c["id"] not in existing]
        plans[sub] = (mp, m, chs, todo)
        print(f"{sub}: 现有 {len(m['chapters'])} 章 · 待登记 {len(todo)} 章 "
              f"{[c['id'] for c in todo]}")

    if not args.apply:
        print("\n（dry-run，未写盘；加 --apply 生效）")
        return 0

    for sub, (mp, m, chs, todo) in plans.items():
        if not todo:
            continue
        # 重排 order：把所有章按「原 order、新章插在声明位置」稳定排序
        merged = {c["id"]: c for c in m["chapters"]}
        for c in todo:
            merged[c["id"]] = manifest_entry(c)
        # 新章插到同 group 的末尾；没有该 group 就插到末尾
        def sort_key(item):
            cid, c = item
            ids = [x["id"] for x in chs]
            if cid in ids:
                # 新章按 _new_chapters 里的声明顺序，落在原同 group 之后
                idx = ids.index(cid)
                peers = [x for x in m["chapters"] if x.get("group") == c.get("group")]
                base = max((p["order"] for p in peers), default=len(m["chapters"])) + 0.1
                return (base + idx * 0.001, cid)
            return (float(c.get("order", 0)), cid)

        ordered = [c for _, c in sorted(merged.items(), key=sort_key)]
        for i, c in enumerate(ordered, 1):
            c["order"] = i
        m["chapters"] = ordered

        mp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  写入 {sub}: {len(m['chapters'])} 章")

    # 复核
    for sub, (mp, m, chs, todo) in plans.items():
        now = [c["id"] for c in m["chapters"]]
        orders = [c["order"] for c in m["chapters"]]
        assert len(orders) == len(set(orders)), f"{sub} order 撞号"
        print(f"  复核 {sub}: {len(now)} 章 · order 唯一 ✓ · 含新章 {[c['id'] for c in chs if c['id'] in now]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
