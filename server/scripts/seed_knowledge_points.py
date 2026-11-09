#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 content/ 的概念体系播种进后端内容表（幂等 / 纯增量）。

背景
--------------------------------------------------------------------
`init_db.py` 原本只建 2 门课 / 27 章 / 4 个成就，`knowledge_points` 一直 0 行。
于是 `/chapters` 的 mastery_avg 恒为 0、`/chapters/{id}/mindmap` 返回空节点、
`/search` 搜不到任何知识点 —— 掌握度相关的接口全是空壳。

本脚本从**唯一事实源** `content/<subject>/<chapter>/concept/*.md` 出发，
补齐 course / chapter / knowledge_point / lesson / mind_map_node 五张表，
让 167 章 / 723 篇概念在后端也真实存在（lesson 带全文，不是占位符）。

设计约束
--------------------------------------------------------------------
1. 纯增量：不删任何行、不覆盖已有的非空字段（init_db 建的章节标题保留）。
2. 幂等：按自然键判重，第二次运行应报 0 新增。
3. clang 别名：init_db 用 `clang-chNN`，content 用 `clang-uNN`。按 `clang-uNN`
   找不到时回落 `clang-chNN` 复用同一行，避免凭空多出 7 章。
4. difficulty 是**可复现的启发式**（按正文字符数分 1..5），不是编造的人工标注；
   后续若有人工难度标注，直接 UPDATE 覆盖即可，本脚本不会改回。
5. 只建表不补列（沿用 create_all 语义）；已有旧库缺列请先跑 Alembic 迁移。

用法（cwd = server/）
--------------------------------------------------------------------
    python -m scripts.seed_knowledge_points           # 播种
    python -m scripts.seed_knowledge_points --check    # 只核对，不写库
    DATABASE_URL=postgresql://user:pwd@host/db python -m scripts.seed_knowledge_points

`DATABASE_URL` 由 app.core.config 读取；注入外部库时不需要 Docker 之外的依赖。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
sys.path.insert(0, str(SERVER_ROOT))

from sqlalchemy import select  # noqa: E402

import app.models  # noqa: F401,E402  注册全部模型到 metadata
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models.content import (  # noqa: E402
    Chapter,
    Course,
    KnowledgePoint,
    Lesson,
    MindMapNode,
)
from app.models.enums import LessonType  # noqa: E402

CONTENT = REPO_ROOT / "content"

TITLE_RE = re.compile(r"^#\s+(.+)$", re.M)
MD_MARK_RE = re.compile(r"[*`_>\[\]()#]")


def clean_text(s: str, limit: int) -> str:
    """标题/摘要用的纯文本：去 Markdown 标记、折叠空白、限长（列宽 200/300）。"""
    s = MD_MARK_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def concept_title(text: str, fallback: str) -> str:
    m = TITLE_RE.search(text)
    return clean_text(m.group(1) if m else fallback, 200)


def concept_summary(text: str) -> str:
    """取首个 # 标题之后的第一个正文段落；跳过代码围栏/表格/列表开头。"""
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if buf:
                break
            continue
        if line.startswith(("#", "```", "|", ">")):
            if buf:
                break
            continue
        if re.match(r"^([-*+]\s+|\d+[.)]\s+)", line):
            if buf:
                break
            continue
        buf.append(line)
        if sum(len(x) for x in buf) >= 400:
            break
    return clean_text(" ".join(buf), 300)


def difficulty_of(chars: int) -> int:
    """可复现的难度启发式：正文越长，覆盖的概念层次通常越多。"""
    if chars < 4000:
        return 1
    if chars < 8000:
        return 2
    if chars < 12000:
        return 3
    if chars < 18000:
        return 4
    return 5


def load_titles() -> tuple[dict[str, str], dict[str, str]]:
    """从各学科 _manifest.json 收集 course.title 与 chapter.title。

    clang 没有独立 manifest，它的 7 个单元挂在 cpp 的 clang_module.units 里；
    ml 没有 manifest，章节标题回落到章节 id（概念自身标题仍然真实）。
    """
    course_titles: dict[str, str] = {}
    chapter_titles: dict[str, str] = {}
    for mf in sorted(CONTENT.glob("*/_manifest.json")):
        subject = mf.parent.name
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("title"):
            course_titles[subject] = str(data["title"])[:100]
        for ch in data.get("chapters", []) or []:
            if ch.get("id") and ch.get("title"):
                chapter_titles[ch["id"]] = str(ch["title"])[:100]
        units = (data.get("clang_module") or {}).get("units") or []
        for u in units:
            if u.get("id") and u.get("title"):
                chapter_titles[u["id"]] = str(u["title"])[:100]
    return course_titles, chapter_titles


def collect() -> dict[str, dict[str, list[dict]]]:
    """按学科 / 章 / 概念 md 分组，顺序稳定（文件名排序 → sort 可复现）。"""
    packs: dict[str, dict[str, list[dict]]] = {}
    for p in sorted(CONTENT.glob("*/*/concept/*.md")):
        parts = p.relative_to(CONTENT).parts
        subject, chapter = parts[0], parts[1]
        if subject.startswith("_"):
            continue
        text = p.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        # 防御：裸 NUL 字节会被 PostgreSQL 的 UTF8 Text 列拒绝（0x00 invalid byte
        # sequence）。源里讲 C 字符串结束符应写字面 `\0`，这里兜底纠正。
        text = text.replace("\x00", "\\0")
        if text.startswith("\ufeff"):
            text = text[1:]
        packs.setdefault(subject, {}).setdefault(chapter, []).append(
            {
                "file": p.stem,
                "title": concept_title(text, p.stem),
                "summary": concept_summary(text),
                "difficulty": difficulty_of(len(text)),
                "markdown": text,
            }
        )
    for pack in packs.values():
        for docs in pack.values():
            docs.sort(key=lambda d: d["file"])
    return packs


def clang_alias(chapter_code: str) -> str | None:
    """content 的 clang-uNN ↔ init_db 的 clang-chNN。"""
    m = re.fullmatch(r"clang-u(\d{2})", chapter_code)
    return f"clang-ch{m.group(1)}" if m else None


async def seed(check_only: bool = False) -> dict[str, int]:
    packs = collect()
    course_titles, chapter_titles = load_titles()
    want_chapters = sum(len(v) for v in packs.values())
    want_docs = sum(len(d) for v in packs.values() for d in v.values())

    async with engine.begin() as conn:
        if not check_only:
            await conn.run_sync(Base.metadata.create_all)

    stats = {"course": 0, "chapter": 0, "kp": 0, "lesson": 0, "node": 0}

    async with SessionLocal() as db:
        courses = {c.code: c for c in (await db.execute(select(Course))).scalars().all()}
        chapters = {c.code: c for c in (await db.execute(select(Chapter))).scalars().all()}
        kp_keys = {
            (k.chapter_id, k.title) for k in (await db.execute(select(KnowledgePoint))).scalars().all()
        }
        lesson_keys = {
            (l.chapter_id, l.type.value, l.title)
            for l in (await db.execute(select(Lesson))).scalars().all()
        }
        node_rows = (await db.execute(select(MindMapNode))).scalars().all()
        node_keys = {(n.chapter_id, n.label, n.kp_id) for n in node_rows}
        # 根节点按章缓存，第二次跑要拿它的 id 给概念节点当 parent_id
        roots = {n.chapter_id: n for n in node_rows if n.kp_id is None}

        if check_only:
            print(
                f"[check] 期望 {len(packs)} 学科 / {want_chapters} 章 / {want_docs} 篇概念；"
                f" 现有 courses={len(courses)} chapters={len(chapters)} "
                f"knowledge_points={len(kp_keys)} lessons={len(lesson_keys)} "
                f"mind_map_nodes={len(node_keys)}"
            )
            missing = 0
            for subject in sorted(packs):
                for code in sorted(packs[subject]):
                    ch = chapters.get(code) or chapters.get(clang_alias(code) or "")
                    if ch is None:
                        missing += 1
                        continue
                    for d in packs[subject][code]:
                        if (ch.id, d["title"]) not in kp_keys:
                            missing += 1
            print(f"[check] 缺失条目 {missing}（0 表示已播种完整）")
            return {"missing": missing}

        for sort_course, subject in enumerate(sorted(packs)):
            course = courses.get(subject)
            if course is None:
                course = Course(
                    code=subject,
                    title=course_titles.get(subject, f"CppMind · {subject}")[:100],
                    description="",
                    sort=sort_course,
                )
                db.add(course)
                await db.flush()
                courses[subject] = course
                stats["course"] += 1

            for idx, code in enumerate(sorted(packs[subject])):
                ch = chapters.get(code)
                if ch is None:
                    alias = clang_alias(code)
                    ch = chapters.get(alias) if alias else None  # 复用 init_db 的 clang-chNN
                if ch is None:
                    ch = Chapter(
                        course_id=course.id,
                        idx=idx,
                        code=code,
                        title=chapter_titles.get(code, code)[:100],
                        goals=[],
                        estimated_minutes=60,
                        is_free=False,
                    )
                    db.add(ch)
                    await db.flush()
                    chapters[code] = ch
                    stats["chapter"] += 1

                root_label = ch.title[:200]
                root = roots.get(ch.id)
                if root is None:
                    root = MindMapNode(
                        chapter_id=ch.id,
                        kp_id=None,
                        parent_id=None,
                        label=root_label,
                        pos_x=0,
                        pos_y=0,
                        sort=0,
                    )
                    db.add(root)
                    await db.flush()
                    roots[ch.id] = root
                    node_keys.add((ch.id, root_label, None))
                    stats["node"] += 1

                for i, d in enumerate(packs[subject][code]):
                    kp_key = (ch.id, d["title"])
                    kp_id = None
                    if kp_key not in kp_keys:
                        kp = KnowledgePoint(
                            chapter_id=ch.id,
                            title=d["title"],
                            summary=d["summary"],
                            difficulty=d["difficulty"],
                            sort=i,
                        )
                        db.add(kp)
                        await db.flush()
                        kp_id = kp.id
                        kp_keys.add(kp_key)
                        stats["kp"] += 1
                    else:
                        # 已存在：查回 id 给 lesson / node 挂外键（只在第二次跑时发生）
                        kp_id = (
                            await db.execute(
                                select(KnowledgePoint.id).where(
                                    KnowledgePoint.chapter_id == ch.id,
                                    KnowledgePoint.title == d["title"],
                                )
                            )
                        ).scalar_one()

                    lesson_key = (ch.id, "concept", d["title"])
                    if lesson_key not in lesson_keys:
                        db.add(
                            Lesson(
                                chapter_id=ch.id,
                                kp_id=kp_id,
                                type=LessonType.concept,
                                title=d["title"],
                                content_md=d["markdown"],
                                sort=i,
                            )
                        )
                        lesson_keys.add(lesson_key)
                        stats["lesson"] += 1

                    node_key = (ch.id, d["title"][:200], kp_id)
                    if node_key not in node_keys:
                        db.add(
                            MindMapNode(
                                chapter_id=ch.id,
                                kp_id=kp_id,
                                parent_id=root.id,
                                label=d["title"][:200],
                                pos_x=float((i % 4) * 180),
                                pos_y=float((i // 4 + 1) * 100),
                                sort=i + 1,
                            )
                        )
                        node_keys.add(node_key)
                        stats["node"] += 1

        await db.commit()

    print(
        f"SEED_OK 新增 course={stats['course']} chapter={stats['chapter']} "
        f"kp={stats['kp']} lesson={stats['lesson']} node={stats['node']}；"
        f" 覆盖 {len(packs)} 学科 / {want_chapters} 章 / {want_docs} 篇概念，"
        f" 库内 knowledge_points 共 {len(kp_keys)} 行"
    )
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="从 content/ 播种知识点（幂等）")
    ap.add_argument("--check", action="store_true", help="只核对，不写库")
    args = ap.parse_args()
    asyncio.run(seed(check_only=args.check))


if __name__ == "__main__":
    main()
