# -*- coding: utf-8 -*-
"""就业级项目库的离线测试（不依赖数据库进程）。

覆盖三件事：
  1. 数据集完整性：13 学科全覆盖、slug 唯一、必填字段齐全；
  2. 模式安全：同名 PG 枚举只 CREATE TYPE 一次（否则 create_all 会报 type already exists）；
  3. SQL 可编译：列表接口的筛选/排序/分页组合能生成合法 PostgreSQL 语句。
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_mock_engine, func, or_, select
from sqlalchemy.dialects import postgresql

import app.models  # noqa: F401  触发全部模型注册
from app.db import Base
from app.models.career import CareerProject, CareerProjectStep, CareerStepProgress
from app.models.enums import CareerTrack, Difficulty
from app.models.project import Project

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "content" / "_projects" / "career-projects.json"


@pytest.fixture(scope="module")
def doc():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_dataset_covers_all_tracks(doc):
    tracks = doc["tracks"]
    assert len(tracks) == 13, f"学科数应为 13，实际 {len(tracks)}"

    per = {}
    for it in doc["items"]:
        per[it["track"]] = per.get(it["track"], 0) + 1

    missing = [t for t in tracks if per.get(t, 0) < 2]
    assert not missing, f"以下学科项目不足 2 个: {missing}"


def test_dataset_fields_valid(doc):
    slugs = [it["slug"] for it in doc["items"]]
    assert len(slugs) == len(set(slugs)), "slug 存在重复"

    for it in doc["items"]:
        assert it["title"].strip()
        assert it["repo"].count("/") == 1, f"{it['slug']}: repo 格式应为 owner/name"
        assert it["level"] in {e.value for e in Difficulty}
        assert it["track"] in {e.value for e in CareerTrack}
        for key in ("learn", "steps", "accept", "interview"):
            assert len(it[key]) >= 3, f"{it['slug']}: {key} 少于 3 条"
        meta = it.get("meta") or {}
        assert meta.get("repo_url"), f"{it['slug']}: 缺少实测元数据，请先跑 merge_career_meta"
        assert isinstance(meta.get("stars"), int)
        assert meta.get("stars") > 0, f"{it['slug']}: stars 未回填"


def test_tier_distribution_matches_blueprint(doc):
    """学科 × 梯度必须覆盖规划；t4 不足的学科允许，但已规划的档位不能缺。"""
    plan = json.loads(
        (ROOT / "content" / "_projects" / "career-plan.json").read_text(encoding="utf-8")
    )
    bp = plan["track_blueprint"]
    got: dict[str, set[str]] = {}
    for it in doc["items"]:
        assert it["tier"] in {"t1", "t2", "t3", "t4"}, f"{it['slug']}: tier 非法"
        assert 1 <= int(it["hours"]) <= 200, f"{it['slug']}: hours 不合理"
        got.setdefault(it["track"], set()).add(it["tier"])

    for track, spec in bp.items():
        for tier in ("t1", "t2", "t3", "t4"):
            if int(spec.get(tier) or 0) > 0:
                assert tier in got.get(track, set()), f"{track} 缺 {tier}"

    total_hours = sum(int(it["hours"]) for it in doc["items"])
    assert total_hours > 3000, f"总工时 {total_hours}h 偏低，梯度内容可能没铺满"


def test_pg_enum_created_once():
    """project_difficulty 被 projects 与 career_projects 共用，必须只建一次。"""
    assert Project.__table__.c.difficulty.type is CareerProject.__table__.c.level.type

    stmts: list[str] = []

    def dump(sql, *args, **kwargs):
        stmts.append(str(sql.compile(dialect=eng.dialect)))

    eng = create_mock_engine("postgresql://", dump)
    Base.metadata.create_all(eng, checkfirst=False)
    ddl = "\n".join(stmts)

    assert ddl.count("CREATE TYPE project_difficulty") == 1
    assert ddl.count("CREATE TYPE career_track") == 1
    assert "CREATE TABLE career_projects" in ddl
    assert "CREATE TABLE career_project_steps" in ddl
    assert "CREATE TABLE career_step_progress" in ddl


def test_career_relations_configured():
    assert CareerProjectStep.__table__.c.project_id.foreign_keys
    fk = next(iter(CareerProjectStep.__table__.c.project_id.foreign_keys))
    assert fk.column.table is CareerProject.__table__

    uniques = {c.name for c in CareerStepProgress.__table__.constraints if c.name}
    assert "uq_user_career_step" in uniques


def test_list_query_compiles():
    """复刻 /career-projects 的筛选 + 排序 + 分页，确认能编译成 PG SQL。"""
    conds = [
        CareerProject.deleted_at.is_(None),
        CareerProject.is_active.is_(True),
        CareerProject.track == CareerTrack.cpp,
        CareerProject.level == Difficulty.mid,
    ]
    kw = "%server%"
    conds.append(or_(
        CareerProject.title.ilike(kw),
        CareerProject.repo.ilike(kw),
        CareerProject.summary.ilike(kw),
    ))

    q = (
        select(CareerProject)
        .where(*conds)
        .order_by(CareerProject.stars.desc())
        .offset(0)
        .limit(20)
    )
    sql = str(q.compile(dialect=postgresql.dialect(),
                        compile_kwargs={"literal_binds": True}))
    assert "career_projects.track" in sql
    assert "ILIKE" in sql.upper()
    assert "LIMIT 20" in sql.upper()

    # recent 排序用了 nullslast，单独编译一次
    q2 = select(CareerProject).order_by(CareerProject.last_pushed.desc().nullslast())
    assert "NULLS LAST" in str(q2.compile(dialect=postgresql.dialect())).upper()


def test_track_count_query_compiles():
    q = (
        select(CareerProject.track, func.count(CareerProject.id))
        .where(CareerProject.deleted_at.is_(None))
        .group_by(CareerProject.track)
    )
    sql = str(q.compile(dialect=postgresql.dialect()))
    assert "GROUP BY" in sql.upper()
