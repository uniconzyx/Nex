"""Redis fail-closed 回归测试（自包含，桩掉重依赖）。

直接加载真实源码 redis_client.py / rate_limit.py，在两种模式下验证：
  - closed：Redis 缺失/掉线 -> 抛 503（SERVICE_UNAVAILABLE, code=1006）
  - open  ：Redis 缺失      -> fail-open 放行（return None / 返回 limit）

运行：python scripts/_verify_redis_fail_closed.py
"""
import importlib.util
import sys
import types

ROOT = __file__.rsplit("scripts", 1)[0]


def _fake_module(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


# --- 桩：app / app.core 命名空间 ---
app_pkg = _fake_module("app")
app_core = _fake_module("app.core")

# --- 桩：app.core.responses（仅放测试需要的符号）---
resp = _fake_module("app.core.responses")


class AppError(Exception):
    def __init__(self, code, message, http_status=400, data=None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data


resp.AppError = AppError
resp.SERVICE_UNAVAILABLE = 1006
resp.RATE_LIMITED = 1005
resp.QUOTA_EXCEEDED = 2001

# --- 桩：app.core.config.settings（可切换 redis_fails_closed）---
cfg = _fake_module("app.core.config")


class _Settings:
    redis_url = "redis://localhost:6379/0"
    redis_fails_closed = False  # 测试时切换


cfg.settings = _Settings()

# --- 桩：redis.asyncio（控制 ping 成功/失败）---
STATE = {"ping_ok": True}
redis_mod = _fake_module("redis")
redis_async = _fake_module("redis.asyncio")


class FakeRedis:
    def __init__(self, url):
        self.url = url

    async def ping(self):
        if not STATE["ping_ok"]:
            raise ConnectionError("redis down")


def from_url(url, **kw):
    return FakeRedis(url)


redis_async.from_url = from_url
redis_mod.asyncio = redis_async

# --- 桩：fastapi（rate_limit 顶部 from fastapi import Request）---
fastapi = _fake_module("fastapi")


class Request:
    pass


fastapi.Request = Request


def load(name, relpath):
    spec = importlib.util.spec_from_file_location(
        name, f"{ROOT}{relpath}", submodule_search_locations=[]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


redis_client = load("app.core.redis_client", "server/app/core/redis_client.py")
rate_limit = load("app.core.rate_limit", "server/app/core/rate_limit.py")

settings = cfg.settings


def reset_pool():
    redis_client._pool = None
    redis_client._down_logged = False


PASS = 0
FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


async def run():
    # ---- 1. require_redis：closed + 缺失 -> 503 ----
    reset_pool()
    settings.redis_fails_closed = True
    STATE["ping_ok"] = False
    try:
        await redis_client.require_redis()
        check("require_redis closed+down 应抛 503", False)
    except AppError as e:
        check("require_redis closed+down 抛 503", e.http_status == 503 and e.code == 1006)

    # ---- 2. require_redis：open + 缺失 -> None ----
    reset_pool()
    settings.redis_fails_closed = False
    STATE["ping_ok"] = False
    r = await redis_client.require_redis()
    check("require_redis open+down 返回 None", r is None)

    # ---- 3. require_redis：closed + 正常 -> 返回连接 ----
    reset_pool()
    settings.redis_fails_closed = True
    STATE["ping_ok"] = True
    r = await redis_client.require_redis()
    check("require_redis closed+ok 返回连接", r is not None)

    # ---- 4. check_rate_limit：open + 缺失 -> 放行（不抛）----
    reset_pool()
    settings.redis_fails_closed = False
    STATE["ping_ok"] = False
    try:
        await rate_limit.check_rate_limit("k", 10, 300)
        check("check_rate_limit open+down 放行", True)
    except AppError:
        check("check_rate_limit open+down 放行", False)

    # ---- 5. check_rate_limit：closed + 缺失 -> 503 ----
    reset_pool()
    settings.redis_fails_closed = True
    STATE["ping_ok"] = False
    try:
        await rate_limit.check_rate_limit("k", 10, 300)
        check("check_rate_limit closed+down 应抛 503", False)
    except AppError as e:
        check("check_rate_limit closed+down 抛 503", e.http_status == 503 and e.code == 1006)

    # ---- 6. check_daily_quota：open + 缺失 -> 返回 limit ----
    reset_pool()
    settings.redis_fails_closed = False
    STATE["ping_ok"] = False
    left = await rate_limit.check_daily_quota(1, "ai", 20)
    check("check_daily_quota open+down 返回 limit", left == 20)

    # ---- 7. check_daily_quota：closed + 缺失 -> 503 ----
    reset_pool()
    settings.redis_fails_closed = True
    STATE["ping_ok"] = False
    try:
        await rate_limit.check_daily_quota(1, "ai", 20)
        check("check_daily_quota closed+down 应抛 503", False)
    except AppError as e:
        check("check_daily_quota closed+down 抛 503", e.http_status == 503 and e.code == 1006)


import asyncio

asyncio.run(run())
print(f"\n结果：{PASS} 通过 / {FAIL} 失败")
sys.exit(1 if FAIL else 0)
