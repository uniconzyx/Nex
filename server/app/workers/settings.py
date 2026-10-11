from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import ai_diagnose, daily_sync_cron, poll_judge, run_sync


def _parse_redis(url: str) -> RedisSettings:
    # redis://[:password@]host:port/db
    from urllib.parse import urlparse

    u = urlparse(url)
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        password=u.password,
        database=int((u.path or "/0").lstrip("/") or 0),
    )


redis_settings = _parse_redis(settings.redis_url)


class WorkerSettings:
    functions = [poll_judge, run_sync, ai_diagnose]
    cron_jobs = [cron(daily_sync_cron, hour=settings.sync_cron_hour, minute=0)]
    redis_settings = redis_settings
    max_jobs = 20
    job_timeout = 120
