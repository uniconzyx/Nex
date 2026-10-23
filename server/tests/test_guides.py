# -*- coding: utf-8 -*-
"""指南（11408 笔记索引）的离线测试。

覆盖三件事：
  1. 内容合规：每条都有原文链接、要点非空、subject 必须在 subjects 里声明；
  2. 路由可导入：guides 与 career 两个路由都注册成功（防止漏 import 的符号错误）；
  3. DDL 可生成：guide_kind 枚举只建一次，两张表都在。
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_mock_engine

import app.models  # noqa: F401
from app.db import Base
from app.models.guide import GuideItem, GuideSource

ROOT = Path(__file__).resolve().parent.parent.parent
GUIDES = ROOT / "content" / "_guides"


@pytest.fixture(scope="module")
def docs():
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(GUIDES.glob("*.json"))]


def test_guides_content_valid(docs):
    assert docs, "content/_guides 下没有指南文件"

    slugs: set[str] = set()
    for doc in docs:
        subjects = {s["key"] for s in doc.get("subjects") or []}
        assert subjects, "subjects 不能为空"
        for it in doc.get("items") or []:
            assert it["slug"] not in slugs, f"{it['slug']}: slug 重复"
            slugs.add(it["slug"])
            assert it["kind"] in {"note", "experience", "external"}
            assert it["subject"] in subjects, f"{it['slug']}: subject 未声明"
            assert it["title"].strip()
            # 经验贴必须提炼成可扫读要点；纯外链/摘要型笔记允许更短
            min_points = 3 if it["kind"] == "experience" else 1
            assert len(it.get("points") or []) >= min_points, (
                f"{it['slug']}: 要点少于 {min_points} 条"
            )
            assert it["url"].startswith("https://"), f"{it['slug']}: 原文链接无效"
            assert it.get("read_min", 0) > 0


def test_routes_importable():
    """回归：career.py 曾漏 import CareerRoute/ProjectTier，导致启动即 NameError。"""
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])
    for p in ("/guides", "/guides/{source_key}", "/career-projects", "/career-routes",
              "/career-coverage", "/career-tracks"):
        assert f"/api/v1{p}" in paths, f"缺少路由 /api/v1{p}"


def test_guide_ddl():
    stmts: list[str] = []

    def dump(sql, *args, **kwargs):
        stmts.append(str(sql.compile(dialect=eng.dialect)))

    eng = create_mock_engine("postgresql://", dump)
    Base.metadata.create_all(eng, checkfirst=False)
    ddl = "\n".join(stmts)

    assert ddl.count("CREATE TYPE guide_kind") == 1
    assert "CREATE TABLE guide_sources" in ddl
    assert "CREATE TABLE guide_items" in ddl
    assert "CREATE TABLE career_routes" in ddl


def test_guide_columns():
    cols = {c.name for c in GuideItem.__table__.c}
    for name in ("source_key", "slug", "kind", "subject", "summary", "points",
                 "read_min", "recommended", "source_path", "url"):
        assert name in cols, f"guide_items 缺列 {name}"
    assert "subjects" in {c.name for c in GuideSource.__table__.c}
