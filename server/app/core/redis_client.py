"""Redis 客户端 + 可选依赖降级（fail-open）。

设计取舍
--------
Redis 在本项目里承担三件事：限流、AI/判题每日配额、少量缓存。三者都是
**旁路能力**——没有它们，业务正确性不受影响，只是少了防刷和计数。

硬依赖 Redis 会让"单机离线部署"（无 Docker、无 Redis 的 Windows 桌面机）直接
500，而本项目的第一交付形态恰恰就是单机离线 exe/APK。所以这里的策略是
fail-open：连不上就跳过保护能力并打一次告警日志，业务照常放行。

生产（docker-compose 起 Redis）下行为与之前完全一致，不会静默降级——
只有在真的拿不到连接时才走到降级分支。
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("nex.redis")

_pool: aioredis.Redis | None = None
_down_logged = False


def get_redis() -> aioredis.Redis:
    """Redis 单例客户端。用途：缓存 / 限流 / AI 与编译配额计数。"""
    global _pool
    if _pool is None:
        # socket_connect_timeout 要短：离线机器上连 6379 会被系统直接 RST，
        # 但某些防火墙配置下会挂到默认超时，把接口拖成十几秒。
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
    return _pool


def mark_down(exc: BaseException) -> None:
    """记录一次降级（只打一次，避免刷屏）。"""
    global _down_logged
    if not _down_logged:
        _down_logged = True
        logger.warning("Redis 不可用，已降级为无缓存/无限流模式：%s", exc)


async def try_redis():
    """尝试拿一个 ping 得通的连接；不可用返回 None（不抛异常）。"""
    r = get_redis()
    try:
        await r.ping()
        return r
    except Exception as exc:  # noqa: BLE001 - 任何连接层异常都视为不可用
        mark_down(exc)
        return None
