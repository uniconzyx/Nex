#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 content/<subject>/<chapter>/concept/*.md 的**全文**打进前端。

背景
--------------------------------------------------------------------
`chapterContent.ts` 一直只是切片（goals / pitfalls 条目 + concept 首标题），
723 篇概念正文（约 6.7MB）从没进过包 —— 学习页能看「本章讲了哪些概念」，
却读不到概念本身。2026-11-08 把它接进来。

为什么按学科切而不是按章切
--------------------------------------------------------------------
`deploy/package/prepare_app.py` 用 vite 直接输出到 staging，并设了
「>120 文件 / >40MB 即判异常」的挡错阈值。按 167 章切会让 chunk 数直接
撞线；按 16 个学科目录切只多 16 个 chunk，且 `import()` 是 Vite 能静态
分析的，chunk 会随整个 vite outDir 一起进包（verify_staging 的引用闭包
只做「引用到的文件必须存在」校验，不是「只拷闭包」）。
首屏不加载：模块级 CACHE + 用户点开折叠面板才 `import()`。

产物（全部请勿手改）
--------------------------------------------------------------------
  frontend/src/data/concepts/types.ts        ConceptDoc 接口
  frontend/src/data/concepts/<subject>.ts    该学科全部章节的正文
  frontend/src/data/concepts/index.ts        16 个 loader + 167 章映射 + CACHE

用法：python scripts/gen_concept_docs.py
幂等：内容不变则写出的字节完全一致（git status 判空）。零第三方依赖。
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "frontend" / "src" / "data" / "concepts"

HEADER = (
    "/* 由 scripts/gen_concept_docs.py 从 content/<subject>/<chapter>/concept/*.md 生成，请勿手改。 */\n"
    "/* eslint-disable */\n"
)


def write(path: Path, text: str) -> None:
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def read_md(path: Path) -> str:
    t = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return t[1:] if t.startswith("\ufeff") else t


def js_literal(obj: object) -> str:
    """JSON 当 TS 对象字面量用。U+2028/2029 在早期 JS 里会截断字符串，转义掉。"""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def collect() -> dict[str, dict[str, list[dict[str, str]]]]:
    packs: dict[str, dict[str, list[dict[str, str]]]] = {}
    for p in sorted(CONTENT.glob("*/*/concept/*.md")):
        rel = p.relative_to(CONTENT).parts
        subject, chapter = rel[0], rel[1]
        if subject.startswith("_"):
            continue
        text = read_md(p)
        m = re.search(r"^#\s+(.+)$", text, re.M)
        packs.setdefault(subject, {}).setdefault(chapter, []).append(
            {"name": p.stem, "title": (m.group(1).strip() if m else p.stem), "markdown": text}
        )
    for pack in packs.values():
        for docs in pack.values():
            docs.sort(key=lambda d: d["name"])
    return packs


def emit_types() -> str:
    return (
        "/* 由 scripts/gen_concept_docs.py 生成，请勿手改。 */\n"
        "/** 一篇概念正文：文件名 / 首个 # 标题 / 完整 Markdown 原文。 */\n"
        "export interface ConceptDoc {\n"
        "  name: string;\n"
        "  title: string;\n"
        "  markdown: string;\n"
        "}\n"
    )


def emit_index(packs: dict[str, dict[str, list[dict[str, str]]]]) -> str:
    lines = [
        "/* 由 scripts/gen_concept_docs.py 生成，请勿手改。",
        f"   概念全文按学科切成 {len(packs)} 个懒加载 chunk：学习页展开某章时才 import，",
        "   不占首屏主 chunk。章节 → 学科模块的映射由生成器从 content/ 推出。 */",
        "import type { ConceptDoc } from './types';",
        "export type { ConceptDoc } from './types';",
        "",
        "type Loader = () => Promise<Record<string, ConceptDoc[]>>;",
        "",
        "const LOADERS: Record<string, Loader> = {",
    ]
    for subject in sorted(packs):
        lines.append(f'  "{subject}": () => import(\'./{subject}\').then((m) => m.default),')
    lines += ["};", "", "const MODULE_OF: Record<string, string> = {"]
    n_chapters = 0
    for subject in sorted(packs):
        for chapter in sorted(packs[subject]):
            lines.append(f'  "{chapter}": "{subject}",')
            n_chapters += 1
    lines += [
        "};",
        "",
        "const CACHE = new Map<string, Record<string, ConceptDoc[]>>();",
        "",
        "/** 这一章是否有概念正文（没有就不渲染入口，避免空面板）。 */",
        "export function hasConceptDocs(chapterId: string): boolean {",
        "  return chapterId in MODULE_OF;",
        "}",
        "",
        "/** 取某章全部概念正文；同一学科只加载一次。 */",
        "export async function loadConceptDocs(chapterId: string): Promise<ConceptDoc[]> {",
        "  const mod = MODULE_OF[chapterId];",
        "  if (!mod) return [];",
        "  let pack = CACHE.get(mod);",
        "  if (!pack) {",
        "    const load = LOADERS[mod];",
        "    if (!load) return [];",
        "    pack = await load();",
        "    CACHE.set(mod, pack);",
        "  }",
        "  return pack[chapterId] ?? [];",
        "}",
        "",
        "/** 已注册的章节 id（门禁核对用）。 */",
        "export const CONCEPT_CHAPTERS: string[] = Object.keys(MODULE_OF);",
        "",
    ]
    return "\n".join(lines) + f"\n/* {n_chapters} 章 */\n"


def main() -> None:
    packs = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "types.ts", emit_types())

    n_docs = 0
    n_bytes = 0
    for subject, pack in packs.items():
        body = HEADER + "import type { ConceptDoc } from './types';\n\n" + (
            "export default " + js_literal(pack) + " as unknown as Record<string, ConceptDoc[]>;\n"
        )
        write(OUT / f"{subject}.ts", body)
        n_docs += sum(len(v) for v in pack.values())
        n_bytes += len(body.encode("utf-8"))

    write(OUT / "index.ts", emit_index(packs))

    # 学科目录被删掉时清掉残留模块（types/index 是固定文件，不动）
    keep = {f"{s}.ts" for s in packs} | {"types.ts", "index.ts"}
    for p in sorted(OUT.glob("*.ts")):
        if p.name not in keep:
            p.unlink()
            print(f"  - 清理残留模块 {p.name}")

    n_chapters = sum(len(v) for v in packs.values())
    print(
        f"wrote frontend/src/data/concepts/: {len(packs)} 学科 / "
        f"{n_chapters} 章 / {n_docs} 篇 / {n_bytes / 1024 / 1024:.2f} MB"
    )


if __name__ == "__main__":
    main()
