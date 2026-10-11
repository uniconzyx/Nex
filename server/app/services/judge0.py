import httpx

from app.core.config import settings
from app.models.enums import CodeStd, SubmissionStatus

# Judge0 CE 语言 ID（默认对应官方 1.13.x 镜像的 GCC 9.2/11+ 环境，
# 部署后必须以 GET {JUDGE0_URL}/languages 实际返回值校准）
LANG_MAP: dict[CodeStd, int] = {
    CodeStd.c11: 50,
    CodeStd.c17: 50,
    CodeStd.cpp11: 54,
    CodeStd.cpp14: 54,
    CodeStd.cpp17: 54,
    CodeStd.cpp20: 54,
    CodeStd.cpp23: 54,
}

# Judge0 status_id → 内部状态
STATUS_MAP: dict[int, SubmissionStatus] = {
    1: SubmissionStatus.queued,
    2: SubmissionStatus.running,
    3: SubmissionStatus.ac,
    4: SubmissionStatus.wa,
    5: SubmissionStatus.tle,
    6: SubmissionStatus.ce,
    7: SubmissionStatus.re,
    8: SubmissionStatus.re,
    9: SubmissionStatus.re,
    10: SubmissionStatus.re,
    11: SubmissionStatus.re,
    12: SubmissionStatus.re,
    13: SubmissionStatus.ie,
    14: SubmissionStatus.ie,
}


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if settings.judge0_authn_token:
        h["X-Auth-Token"] = settings.judge0_authn_token
    return h


def _compile_flags(std: CodeStd) -> str:
    if std.value.startswith("cpp"):
        return f"-std={std.value.replace('cpp', 'c++')}"
    return f"-std={std.value}"


async def submit_batch(
    source_code: str,
    lang: CodeStd,
    cases: list[tuple[str, str]],
    time_limit_s: float,
    memory_limit_kb: int,
) -> list[str]:
    """按测试用例批量提交，返回 judge0 token 列表。沙箱限制在此设定。"""
    subs = [
        {
            "source_code": source_code,
            "language_id": LANG_MAP[lang],
            "stdin": stdin,
            "expected_output": expected if expected else None,
            "compiler_options": _compile_flags(lang),
            "cpu_time_limit": time_limit_s,
            "wall_time_limit": min(time_limit_s * 3, 15),
            "memory_limit": memory_limit_kb,
            "max_processes_and_or_threads": 64,
            "enable_per_process_and_thread_time_limit": True,
            "max_file_size": 1024,  # 输出 1MB 截断
        }
        for stdin, expected in cases
    ]
    async with httpx.AsyncClient(base_url=settings.judge0_url, timeout=30) as client:
        if len(subs) == 1:
            resp = await client.post(
                "/submissions", params={"base64_encoded": "false", "wait": "false"},
                json=subs[0], headers=_headers(),
            )
        else:
            resp = await client.post(
                "/submissions/batch", params={"base64_encoded": "false"},
                json={"submissions": subs}, headers=_headers(),
            )
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, dict):
        return [data["token"]]
    return [item["token"] for item in data]


async def fetch_results(tokens: list[str]) -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.judge0_url, timeout=30) as client:
        resp = await client.get(
            "/submissions/batch",
            params={"tokens": ",".join(tokens), "base64_encoded": "false",
                    "fields": "token,status,stdout,stderr,compile_output,time,memory,exit_code"},
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("submissions", [])


def is_finished(results: list[dict]) -> bool:
    return all(r["status"]["id"] not in (1, 2) for r in results) if results else False


def truncate(text: str | None, limit: int = 64 * 1024) -> str | None:
    if text is None:
        return None
    return text[:limit]
