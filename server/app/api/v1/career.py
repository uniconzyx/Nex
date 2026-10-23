"""就业级实战项目库 API。

设计要点：
  - 列表按学科(track)过滤，返回轻量卡片字段，避免把长文一次性推给客户端；
  - 详情才返回 learn/steps/accept/interview 长文；
  - 步骤打卡复用用户身份，游客可读不可打卡。
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_optional_user
from app.core.responses import AppError, NOT_FOUND, ok, page_data
from app.db import get_db
from app.models.career import (
    CareerProject,
    CareerProjectStep,
    CareerRoute,
    CareerStepProgress,
)
from app.models.enums import CareerTrack, Difficulty, ProjectTier
from app.models.user import User

router = APIRouter(tags=["career"])

TRACK_LABEL = {
    CareerTrack.cpp: "C / C++",
    CareerTrack.clang: "C 语言",
    CareerTrack.java: "Java",
    CareerTrack.spring: "Spring 生态",
    CareerTrack.python: "Python",
    CareerTrack.fullstack: "全栈开发",
    CareerTrack.database: "数据库",
    CareerTrack.middleware: "中间件",
    CareerTrack.ai: "AI / Agent 开发",
    CareerTrack.bigdata: "大数据",
    CareerTrack.data: "数据分析",
    CareerTrack.fundamentals: "计算机基础",
    CareerTrack.tooling: "工具链",
}

TIER_LABEL = {
    ProjectTier.t1: "入门 · 能跑起来",
    ProjectTier.t2: "进阶 · 能独立写",
    ProjectTier.t3: "核心 · 能讲清原理",
    ProjectTier.t4: "门槛 · 能写进简历",
}

# 排序时 tier 需要按梯度先后而非字典序
TIER_ORDER = {ProjectTier.t1: 1, ProjectTier.t2: 2, ProjectTier.t3: 3, ProjectTier.t4: 4}


def _track_label(track: str) -> str:
    try:
        return TRACK_LABEL.get(CareerTrack(track), track)
    except ValueError:
        return track


def _card(p: CareerProject) -> dict:
    return {
        "slug": p.slug,
        "track": p.track.value,
        "track_label": TRACK_LABEL.get(p.track, p.track.value),
        "title": p.title,
        "repo": p.repo,
        "repo_url": p.repo_url,
        "summary": p.summary,
        "level": p.level.value,
        "tier": p.tier.value,
        "tier_label": TIER_LABEL.get(p.tier, p.tier.value),
        "hours": p.hours,
        "stack": p.stack or [],
        "stars": p.stars,
        "language": p.language,
        "license": p.license,
        "last_pushed": p.last_pushed.isoformat() if p.last_pushed else None,
        "archived": p.archived,
    }


@router.get("/career-tracks")
async def list_tracks(db: AsyncSession = Depends(get_db)):
    """学科维度 + 每学科项目数，供前端渲染筛选条。"""
    rows = (
        await db.execute(
            select(CareerProject.track, func.count(CareerProject.id))
            .where(CareerProject.deleted_at.is_(None), CareerProject.is_active.is_(True))
            .group_by(CareerProject.track)
        )
    ).all()
    counts = {track.value: n for track, n in rows}
    data = [
        {"track": t.value, "label": TRACK_LABEL.get(t, t.value), "count": counts.get(t.value, 0)}
        for t in CareerTrack
    ]
    return ok({"tracks": data, "total": sum(counts.values())})


@router.get("/career-routes")
async def list_career_routes(db: AsyncSession = Depends(get_db)):
    """岗位路线：每条路线要求哪些学科的哪些梯度，共需多少项目、多少工时。"""
    rows = (
        await db.execute(
            select(CareerRoute)
            .where(CareerRoute.deleted_at.is_(None), CareerRoute.is_active.is_(True))
            .order_by(CareerRoute.sort.asc())
        )
    ).scalars().all()
    return ok({
        "routes": [
            {
                "key": r.key,
                "title": r.title,
                "summary": r.summary,
                "tracks": [
                    {
                        "track": t,
                        "label": _track_label(t),
                        "tiers": tiers,
                    }
                    for t, tiers in (r.tracks or {}).items()
                ],
                "t4_required": r.t4_required,
                "projects": r.projects,
                "hours": r.hours,
                "deliverables": r.deliverables or [],
                "interview_bar": r.interview_bar or [],
            }
            for r in rows
        ]
    })


@router.get("/career-coverage")
async def career_coverage(db: AsyncSession = Depends(get_db)):
    """学科 × 梯度的真实供给，用于回答「这个方向到底要练多少项目」。"""
    rows = (
        await db.execute(
            select(
                CareerProject.track,
                CareerProject.tier,
                func.count(CareerProject.id),
                func.coalesce(func.sum(CareerProject.hours), 0),
            )
            .where(CareerProject.deleted_at.is_(None), CareerProject.is_active.is_(True))
            .group_by(CareerProject.track, CareerProject.tier)
        )
    ).all()

    by_track: dict[str, dict] = {}
    for track, tier, n, hours in rows:
        slot = by_track.setdefault(track.value, {"count": 0, "hours": 0, "tiers": {}})
        slot["count"] += n
        slot["hours"] += int(hours or 0)
        slot["tiers"][tier.value] = {"count": n, "hours": int(hours or 0)}

    for v in by_track.values():
        for k in ("t1", "t2", "t3", "t4"):
            v["tiers"].setdefault(k, {"count": 0, "hours": 0})

    return ok({
        "tiers": [
            {"key": k.value, "label": TIER_LABEL[k]} for k in ProjectTier
        ],
        "tracks": [
            {
                "track": t,
                "label": TRACK_LABEL.get(CareerTrack(t), t),
                **v,
            }
            for t, v in sorted(by_track.items())
        ],
        "total": sum(v["count"] for v in by_track.values()),
        "total_hours": sum(v["hours"] for v in by_track.values()),
        "graduation": {
            "track_pass": "全部 t1 + t2 完成，且至少 1 个 t3 通过验收",
            "track_strong": "track_pass 且至少 1 个 t4（无 t4 的学科用 2 个 t3 替代）",
            "hirable": "路线要求的全部学科达到 track_strong，且至少 2 个 t4 带可复现量化数据",
        },
    })


@router.get("/career-projects")
async def list_career_projects(
    track: CareerTrack | None = Query(None, description="学科，缺省返回全部"),
    tier: ProjectTier | None = Query(None, description="能力梯度 t1~t4"),
    level: Difficulty | None = Query(None, description="难度"),
    q: str | None = Query(None, description="标题/仓库/简介关键词"),
    sort: str = Query("default", pattern="^(default|stars|level|recent|tier)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    conds = [CareerProject.deleted_at.is_(None), CareerProject.is_active.is_(True)]
    if track:
        conds.append(CareerProject.track == track)
    if tier:
        conds.append(CareerProject.tier == tier)
    if level:
        conds.append(CareerProject.level == level)
    if q:
        kw = f"%{q.strip()}%"
        conds.append(or_(
            CareerProject.title.ilike(kw),
            CareerProject.repo.ilike(kw),
            CareerProject.summary.ilike(kw),
        ))

    total = (
        await db.execute(select(func.count(CareerProject.id)).where(*conds))
    ).scalar_one()

    order = {
        "stars": CareerProject.stars.desc(),
        "level": CareerProject.level.asc(),
        "recent": CareerProject.last_pushed.desc().nullslast(),
        # PG 枚举按声明顺序比较，正好就是 t1 → t4
        "tier": CareerProject.tier.asc(),
        "default": CareerProject.sort.asc(),
    }[sort]

    rows = (
        await db.execute(
            select(CareerProject).where(*conds).order_by(order)
            .offset((page - 1) * size).limit(size)
        )
    ).scalars().all()

    return ok(page_data([_card(p) for p in rows], total, page, size))


@router.get("/career-projects/{slug}")
async def career_project_detail(
    slug: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    p = (
        await db.execute(select(CareerProject).where(CareerProject.slug == slug))
    ).scalar_one_or_none()
    if p is None or p.deleted_at is not None:
        raise AppError(NOT_FOUND, "项目不存在", http_status=404)

    done: set[int] = set()
    if user is not None:
        done = set(
            (
                await db.execute(
                    select(CareerStepProgress.step_id).where(
                        CareerStepProgress.user_id == user.id
                    )
                )
            ).scalars().all()
        )

    return ok({
        **_card(p),
        "forks": p.forks,
        "size_kb": p.size_kb,
        "open_issues": p.open_issues,
        "repo_desc": p.repo_desc,
        "topics": p.topics or [],
        "learn": p.learn or [],
        "career_value": p.career_value,
        "accept": p.accept or [],
        "interview": p.interview or [],
        "steps": [
            {
                "id": s.id,
                "order_no": s.order_no,
                "title": s.title,
                "done": s.id in done,
            }
            for s in sorted(p.steps, key=lambda x: x.order_no)
        ],
        "progress": {
            "done": sum(1 for s in p.steps if s.id in done),
            "total": len(p.steps),
        },
    })


@router.post("/career-steps/{step_id}/complete")
async def complete_career_step(
    step_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    step = await db.get(CareerProjectStep, step_id)
    if step is None:
        raise AppError(NOT_FOUND, "步骤不存在", http_status=404)
    existing = (
        await db.execute(
            select(CareerStepProgress).where(
                CareerStepProgress.user_id == user.id,
                CareerStepProgress.step_id == step_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(CareerStepProgress(user_id=user.id, step_id=step_id, done_at=datetime.now(UTC)))
        await db.commit()
    return ok(message="已打卡")
