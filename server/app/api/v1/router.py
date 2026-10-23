from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    auth,
    career,
    content,
    exam,
    exercises,
    guides,
    judge,
    progress,
    projects,
    resources,
    system,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(content.router)
api_router.include_router(exercises.router)
api_router.include_router(judge.router)
api_router.include_router(progress.router)
api_router.include_router(projects.router)
api_router.include_router(career.router)
api_router.include_router(guides.router)
api_router.include_router(exam.router)
api_router.include_router(ai.router)
api_router.include_router(resources.router)
api_router.include_router(admin.router)
api_router.include_router(system.router)
