import uuid
from typing import Any

from fastapi.responses import JSONResponse


# 错误码段（与 Phase3 文档第 5 节一致）
OK = 0
PARAM_ERROR = 1001
UNAUTHORIZED = 1002
FORBIDDEN = 1003
NOT_FOUND = 1004
RATE_LIMITED = 1005
QUOTA_EXCEEDED = 2001
GUEST_RESTRICTED = 4021
AI_PROVIDER_DOWN = 4001
AI_BUDGET_DEGRADED = 4002


class AppError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 400, data: Any = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": OK, "message": message, "data": data, "traceId": uuid.uuid4().hex[:16]}


def error_response(code: int, message: str, http_status: int = 400, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": data, "traceId": uuid.uuid4().hex[:16]},
    )


def page_data(items: list, total: int, page: int, size: int) -> dict:
    return {"items": items, "total": total, "page": page, "size": size}
