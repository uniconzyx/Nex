from fastapi import APIRouter

from app.api.v1 import admin, ai, auth, content, exercises, judge, progress, projects, resources

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(content.router)
api_router.include_router(exercises.router)
api_router.include_router(judge.router)
api_router.include_router(progress.router)
api_router.include_router(projects.router)
api_router.include_router(ai.router)
api_router.include_router(resources.router)
api_router.include_router(admin.router)
