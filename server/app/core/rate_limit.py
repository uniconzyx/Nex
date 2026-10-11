from fastapi import Request

from app.core.redis_client import get_redis
from app.core.responses import AppError, RATE_LIMITED


async def check_rate_limit(key: str, limit: int, window_s: int) -> None:
    """固定窗口限流（Redis INCR + EXPIRE）。窗口内超限抛 1005。"""
    r = get_redis()
    bucket = f"rl:{key}"
    count = await r.incr(bucket)
    if count == 1:
        await r.expire(bucket, window_s)
    if count > limit:
        ttl = await r.ttl(bucket)
        raise AppError(RATE_LIMITED, "请求过于频繁，请稍后再试", http_status=429, data={"retry_after": max(ttl, 1)})


async def check_daily_quota(user_id: int, kind: str, limit: int) -> int:
    """每日配额计数。kind: judge | ai。返回剩余次数；超限抛 2001。"""
    from datetime import UTC, datetime

    from app.core.responses import QUOTA_EXCEEDED

    r = get_redis()
    today = datetime.now(UTC).strftime("%Y%m%d")
    key = f"quota:{kind}:{user_id}:{today}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 48 * 3600)
    if count > limit:
        await r.decr(key)  # 不计入超额请求
        raise AppError(QUOTA_EXCEEDED, f"今日{kind}配额已用完（{limit}次/日）", http_status=429)
    return limit - count


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
