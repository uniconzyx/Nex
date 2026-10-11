from arq.connections import ArqRedis, create_pool

from app.workers.settings import redis_settings

_pool: ArqRedis | None = None


async def get_arq() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings)
    return _pool
