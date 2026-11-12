from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.responses import PARAM_ERROR, AppError, error_response, ok


def create_app() -> FastAPI:
    app = FastAPI(title="Nex API", version="0.1.0", docs_url="/docs")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # 真机（Android WebView）从 http://tauri.localhost 访问局域网
        # http://<PC-IP>:8000 时，Chromium 会先发 Private Network Access
        # 预检（Access-Control-Request-Private-Network: true）。Starlette 的
        # CORSMiddleware 默认拒绝并返回 400 "Disallowed CORS private-network"，
        # 表现为手机上「连不上内容服务」。白名单是显式 Origin 列表而非 "*"，
        # 开启该开关只对已授信的 Tauri Origin 放行，桌面端不受影响。
        allow_private_network=True,
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return error_response(exc.code, exc.message, exc.http_status, exc.data)

    # FastAPI 默认的 422 是 {"detail": [...]}，与本项目统一响应包不一致。
    # 统一成 {code, message, data, traceId}，客户端只写一套错误处理。
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return error_response(
            PARAM_ERROR, "请求参数校验失败", 400,
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.get("/health")
    async def health():
        return ok({"status": "up"})

    app.include_router(api_router)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    return app


app = create_app()
