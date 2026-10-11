from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import check_rate_limit
from app.core.responses import AppError, NOT_FOUND, PARAM_ERROR, UNAUTHORIZED, ok
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models.user import User, UserProfile
from app.schemas.auth import LoginIn, ProfilePatch, RefreshIn, RegisterIn

router = APIRouter(tags=["auth"])


@router.post("/auth/register")
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if exists:
        raise AppError(PARAM_ERROR, "该邮箱已注册")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    db.add(UserProfile(user_id=user.id, nickname=body.nickname or body.email.split("@")[0]))
    await db.commit()
    return ok({"user_id": user.id, "uuid": str(user.uuid)}, "注册成功")


@router.post("/auth/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(f"login:{body.account}", 10, 300)
    user = (
        await db.execute(
            select(User).where(or_(User.email == body.account, User.phone == body.account))
        )
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(UNAUTHORIZED, "账号或密码错误", http_status=401)
    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return ok({
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": settings.access_token_ttl_s,
    })


@router.post("/auth/refresh")
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
    except jwt.PyJWTError:
        raise AppError(UNAUTHORIZED, "refresh token 无效或已过期", http_status=401)
    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise AppError(NOT_FOUND, "用户不存在", http_status=404)
    # 旋转刷新：旧 refresh 立即作废由客户端丢弃；服务端可加 Redis 黑名单（后续增强）
    return ok({
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": settings.access_token_ttl_s,
    })


@router.get("/users/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    return ok({
        "uuid": str(user.uuid),
        "email": user.email,
        "profile": {
            "nickname": profile.nickname if profile else "",
            "avatar_url": profile.avatar_url if profile else "",
            "direction": profile.direction.value if profile and profile.direction else None,
            "daily_minutes": profile.daily_minutes if profile else 60,
            "plan": profile.plan.value if profile else "free",
            "theme": profile.theme.value if profile else "system",
            "reduced_motion": profile.reduced_motion if profile else False,
            "font_scale": float(profile.font_scale) if profile else 1.0,
        },
    })


@router.patch("/users/me")
async def patch_me(
    body: ProfilePatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    await db.commit()
    return ok(message="已更新")
