from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_optional_user
from app.core.responses import AppError, NOT_FOUND, ok
from app.db import get_db
from app.models.enums import ProjectCategory
from app.models.project import Project, ProjectTask, ProjectTaskProgress
from app.models.user import User

router = APIRouter(tags=["projects"])


@router.get("/projects")
async def list_projects(
    category: ProjectCategory | None = None,
    db: AsyncSession = Depends(get_db),
):
    conds = [Project.deleted_at.is_(None)]
    if category:
        conds.append(Project.category == category)
    rows = (
        await db.execute(select(Project).where(*conds).order_by(Project.sort))
    ).scalars().all()
    return ok([
        {"id": p.id, "title": p.title, "category": p.category.value,
         "difficulty": p.difficulty.value, "chapter_id": p.chapter_id}
        for p in rows
    ])


@router.get("/projects/{project_id}")
async def project_detail(
    project_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if p is None or p.deleted_at is not None:
        raise AppError(NOT_FOUND, "项目不存在", http_status=404)

    done_task_ids: set[int] = set()
    if user is not None:
        done = (
            await db.execute(
                select(ProjectTaskProgress.task_id).where(ProjectTaskProgress.user_id == user.id)
            )
        ).scalars().all()
        done_task_ids = set(done)

    return ok({
        "id": p.id, "title": p.title, "category": p.category.value,
        "requirement_md": p.requirement_md, "architecture_md": p.architecture_md,
        "deploy_md": p.deploy_md, "interview_md": p.interview_md,
        "template_url": p.template_url, "difficulty": p.difficulty.value,
        "tasks": [
            {"id": t.id, "title": t.title, "description": t.description,
             "order_no": t.order_no, "verification": t.verification,
             "done": t.id in done_task_ids}
            for t in sorted(p.tasks, key=lambda x: x.order_no)
        ],
    })


@router.get("/projects/{project_id}/template")
async def project_template(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(Project, project_id)
    if p is None or not p.template_url:
        raise AppError(NOT_FOUND, "模板不存在", http_status=404)
    # MinIO 预签名在部署环境生成；此处返回存储路径，由 nginx/MinIO 网关直出
    return ok({"template_url": p.template_url})


@router.post("/project-tasks/{task_id}/complete")
async def complete_project_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(ProjectTask, task_id)
    if task is None:
        raise AppError(NOT_FOUND, "项目任务不存在", http_status=404)
    existing = (
        await db.execute(
            select(ProjectTaskProgress).where(
                ProjectTaskProgress.user_id == user.id,
                ProjectTaskProgress.task_id == task_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(ProjectTaskProgress(user_id=user.id, task_id=task_id, done_at=datetime.now(UTC)))
        await db.commit()
    return ok(message="已打卡")
