import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import AppError, FORBIDDEN, UNAUTHORIZED
from app.core.security import decode_token
from app.db import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if cred is None:
        raise AppError(UNAUTHORIZED, "未登录", http_status=401)
    try:
        payload = decode_token(cred.credentials, "access")
    except jwt.PyJWTError:
        raise AppError(UNAUTHORIZED, "登录已过期，请重新登录", http_status=401)
    user = await db.get(User, int(payload["sub"]))
    if user is None or user.status != UserStatus.active:
        raise AppError(UNAUTHORIZED, "账号不可用", http_status=401)
    return user


async def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选鉴权：游客返回 None。游客仅可访问 is_free 章节的完整内容。"""
    if cred is None:
        return None
    try:
        payload = decode_token(cred.credentials, "access")
    except jwt.PyJWTError:
        return None
    user = await db.get(User, int(payload["sub"]))
    if user is None or user.status != UserStatus.active:
        return None
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise AppError(FORBIDDEN, "需要管理员权限", http_status=403)
    return user


def guard_chapter_access(chapter_is_free: bool, user: User | None) -> None:
    """游客访问付费章节 → 4021 引导登录。"""
    from app.core.responses import GUEST_RESTRICTED

    if user is None and not chapter_is_free:
        raise AppError(GUEST_RESTRICTED, "该章节需要登录后学习（前 3 章可免费体验）", http_status=401)
