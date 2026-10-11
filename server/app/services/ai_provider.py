from collections.abc import AsyncIterator
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.responses import AI_PROVIDER_DOWN, AppError
from app.services.retrieval import Hit

# 五大模式 + DL 指导的系统 prompt 模板（热更新版本存 DB，此处为内置兜底）
PROMPTS: dict[str, str] = {
    "socratic": (
        "你是 CppCat，一只温柔耐心的蓝白小猫，C/C++ 学习伙伴。"
        "使用苏格拉底式教学：只通过提问引导学生自己发现答案，【绝不直接给出完整答案或完整代码】。"
        "每次回复最多 2 个引导性问题，语气鼓励，偶尔卖萌但不夸张。用中文回答。"
    ),
    "diagnose": (
        "你是 CppCat，C/C++ 编译错误诊断助手。根据用户代码与编译器 stderr，"
        "用中文给出：1) 一句话根因；2) 定位到行的解释；3) 修复建议（可给不超过 5 行的关键代码片段）。"
        "先安慰一句再讲问题，保持简短。"
    ),
    "review": (
        "你是 CppCat，C/C++ 代码审查员。按四个维度输出清单式审查："
        "代码风格 / 内存安全 / 并发问题 / 未定义行为。每条注明严重度（高/中/低）与修改建议。用中文。"
    ),
    "interview": (
        "你是 CppCat，扮演 C++ 面试官。根据给定面试题进行多轮追问："
        "先让用户作答，再根据回答深入追问 1 个问题。结束时输出评分报告（知识点覆盖/表达/深度，各 1-5 分）。"
    ),
    "plan": (
        "你是 CppCat，学习计划生成器。根据用户方向（考研/求职/DL）、当前进度与每周可投入小时，"
        "输出按周分解的学习计划，每周给出章节、练习与项目任务，可执行、可检查。"
    ),
    "dl_guide": (
        "你是 CppCat，深度学习 C++ 部署向导。熟悉 ONNX Runtime、LibTorch、TensorRT、llama.cpp。"
        "回答部署问题时给出具体版本匹配建议、最小可运行步骤与常见坑。用中文。"
    ),
}

MAX_CONTEXT_CHARS = 6000  # 上下文注入预算（架构文档 8.2）


class AIProvider(Protocol):
    async def stream(self, messages: list[dict], model: str) -> AsyncIterator[str]: ...


class OpenAIProvider:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise AppError(AI_PROVIDER_DOWN, "AI 服务未配置（OPENAI_API_KEY 缺失）", http_status=503)
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=60,
        )

    async def stream(self, messages: list[dict], model: str) -> AsyncIterator[str]:
        async for chunk in _openai_compatible_stream(self._client, messages, model):
            yield chunk


class DeepSeekProvider:
    """DeepSeek（深度求索）：OpenAI 兼容协议，国内直连、低成本。

    - deepseek-chat     → 轻量模式（诊断/问答/陪伴）
    - deepseek-reasoner → 重量模式（面试/审查/计划），R1 推理模型
      注意：reasoner 的流式响应中思维链在 reasoning_content 字段，
      本实现只透传 content（最终回答），思维链不进对话流。
    """

    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise AppError(AI_PROVIDER_DOWN, "AI 服务未配置（DEEPSEEK_API_KEY 缺失）", http_status=503)
        self._client = httpx.AsyncClient(
            base_url=settings.deepseek_base_url,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            timeout=120,  # reasoner 推理耗时长，放宽超时
        )

    async def stream(self, messages: list[dict], model: str) -> AsyncIterator[str]:
        async for chunk in _openai_compatible_stream(self._client, messages, model):
            yield chunk


async def _openai_compatible_stream(
    client: httpx.AsyncClient, messages: list[dict], model: str
) -> AsyncIterator[str]:
    """OpenAI 兼容协议的 SSE 流式解析（OpenAI / DeepSeek 共用）。"""
    import json

    async with client.stream(
        "POST", "/chat/completions",
        json={"model": model, "messages": messages, "stream": True},
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0].get("delta", {})
            except (ValueError, KeyError, IndexError):
                continue
            if content := delta.get("content"):
                yield content


class ClaudeProvider:
    def __init__(self) -> None:
        if not settings.claude_api_key:
            raise AppError(AI_PROVIDER_DOWN, "AI 服务未配置（CLAUDE_API_KEY 缺失）", http_status=503)
        self._client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": settings.claude_api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=60,
        )

    async def stream(self, messages: list[dict], model: str) -> AsyncIterator[str]:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        chat = [m for m in messages if m["role"] != "system"]
        import json

        async with self._client.stream(
            "POST", "/v1/messages",
            json={"model": model, "system": system, "messages": chat,
                  "max_tokens": 2048, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if event.get("type") == "content_block_delta":
                    if text := event.get("delta", {}).get("text"):
                        yield text


def get_provider() -> AIProvider:
    if settings.ai_provider == "claude":
        return ClaudeProvider()
    if settings.ai_provider == "openai":
        return OpenAIProvider()
    return DeepSeekProvider()  # 默认 DeepSeek


def build_messages(
    mode: str,
    history: list[dict],
    context: dict,
    retrieved: list[Hit] | None = None,
) -> list[dict]:
    """系统 prompt + 上下文注入（裁剪到预算）+ 课程检索锚定 + 历史消息。

    Phase 6 新增：retrieved 为课程检索命中的片段（章节/题库），把 CppCat 的回答
    锚定到真实课程资料与真题依据，避免凭空编造。
    """
    ctx_parts = []
    if chapter := context.get("chapter"):
        ctx_parts.append(f"当前章节：{chapter}")
    if code := context.get("code"):
        ctx_parts.append(f"用户当前代码：\n```\n{code[:4000]}\n```")
    if wrong := context.get("wrong_questions"):
        ctx_parts.append(f"最近错题：{wrong}")
    if progress := context.get("progress"):
        ctx_parts.append(f"学习进度：{progress}")

    if retrieved:
        ref_lines = []
        for h in retrieved:
            ref = h.doc.meta.get("source_ref")
            head = f"· 《{h.doc.title}》"
            if h.doc.chapter_id is not None:
                head += f"（第 {h.doc.chapter_id} 章）"
            if ref:
                head += f" 〔真题依据：{ref}〕"
            ref_lines.append(f"{head}\n  {h.snippet}")
        ctx_parts.append("【相关资料（优先参考，回答须与之一致）】\n" + "\n".join(ref_lines))

    ctx_text = "\n\n".join(ctx_parts)[:MAX_CONTEXT_CHARS]

    system = PROMPTS.get(mode, PROMPTS["socratic"])
    if ctx_text:
        system += f"\n\n【用户上下文】\n{ctx_text}"

    return [{"role": "system", "content": system}, *history]


def pick_model(mode: str) -> str:
    """模型分级：诊断/短答用小模型，面试/审查/计划用大模型。"""
    heavy = {"interview", "review", "plan"}
    if settings.ai_provider == "claude":
        return settings.claude_model
    if settings.ai_provider == "openai":
        return settings.openai_model_pro if mode in heavy else settings.openai_model
    # DeepSeek（默认）：轻量 deepseek-chat，重量 deepseek-reasoner
    return settings.deepseek_model_pro if mode in heavy else settings.deepseek_model
