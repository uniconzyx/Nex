"""抓取 AI Agent 学科各章 GitHub 资源的真实元数据（stars / license / 最近推送）。

为什么不让模型凭记忆写 star 数
--------------------------------------------------------------------
star 数是时间敏感数据，模型记忆里的一定是旧值。本脚本用 GitHub REST API
实测后落盘，生成 manifest 时只读这份快照。快照带 fetched_at，过期可重抓。

用法：
    python server/scripts/_agent_src/fetch_repos.py
输出：
    server/scripts/_agent_src/repos.json
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

OUT = pathlib.Path(__file__).with_name("repos.json")

# 按章节归属列出候选取样：同一仓库可被多章复用，抓取时去重
CHAPTERS: dict[str, list[str]] = {
    "agent-ch01": [
        "microsoft/AI-For-Beginners",
        "Hannibal046/Awesome-LLM",
        "datawhalechina/self-llm",
        "eugeneyan/applied-ml",
    ],
    "agent-ch02": [
        "dair-ai/Prompt-Engineering-Guide",
        "openai/openai-cookbook",
        "anthropics/anthropic-cookbook",
        "microsoft/promptflow",
    ],
    "agent-ch03": [
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
        "deepseek-ai/awesome-deepseek-integration",
        "ollama/ollama",
    ],
    "agent-ch04": [
        "pair-code/people-and-ai-guide",
        "microsoft/HAX",
        "Azure-Samples/azure-search-openai-demo",
        "GokuMohandas/Made-With-ML",
    ],
    "agent-ch05": [
        "langchain-ai/langchain",
        "run-llama/llama_index",
        "infiniflow/ragflow",
        "HKUDS/LightRAG",
    ],
    "agent-ch06": [
        "vllm-project/vllm",
        "sgl-project/sglang",
        "ggml-org/llama.cpp",
        "ollama/ollama",
    ],
    "agent-ch07": [
        "huggingface/peft",
        "hiyouga/LLaMA-Factory",
        "unslothai/unsloth",
        "huggingface/trl",
    ],
    "agent-ch08": [
        "karpathy/nanoGPT",
        "karpathy/build-nanogpt",
        "huggingface/transformers",
        "jingyaogong/minimind",
    ],
    "agent-ch09": [
        "huggingface/diffusers",
        "openai/CLIP",
        "AUTOMATIC1111/stable-diffusion-webui",
        "QwenLM/Qwen2.5-VL",
    ],
    "agent-ch10": [
        "openai/evals",
        "EleutherAI/lm-evaluation-harness",
        "explodinggradients/ragas",
        "pair-code/people-and-ai-guide",
    ],
    "agent-ch11": [
        "langchain-ai/langgraph",
        "microsoft/autogen",
        "crewAIInc/crewAI",
        "openai/openai-agents-python",
        "modelcontextprotocol/python-sdk",
        "geekan/MetaGPT",
    ],
    "agent-ch12": [
        "langgenius/dify",
        "n8n-io/n8n",
        "Azure-Samples/azure-search-openai-demo",
        "microsoft/AI-For-Beginners",
    ],
    "agent-ch13": [
        "mli/paper-reading",
        "dair-ai/ML-Papers-of-the-Week",
        "Hannibal046/Awesome-LLM",
    ],
    "agent-ch14": [
        "kamranahmedse/developer-roadmap",
        "donnemartin/system-design-primer",
        "yangshun/tech-interview-handbook",
        "alirezadir/Machine-Learning-Interviews",
    ],
    "agent-ch15": [
        "datawhalechina/llm-universe",
        "datawhalechina/happy-llm",
        "langchain-ai/langgraph",
        "langgenius/dify",
    ],
    "agent-ch16": [
        "alirezadir/Machine-Learning-Interviews",
        "chiphuyen/ml-interviews-book",
        "GokuMohandas/Made-With-ML",
        "donnemartin/system-design-primer",
    ],
}


def fetch(repo: str) -> dict:
    cmd = [
        "curl", "-sL", "--max-time", "20", "--noproxy", "*",
        "-H", "Accept: application/vnd.github+json",
        f"https://api.github.com/repos/{repo}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0 or not p.stdout.strip():
        return {"repo": repo, "ok": False, "error": "curl failed"}
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"repo": repo, "ok": False, "error": "bad json"}
    if "message" in d and "stargazers_count" not in d:
        return {"repo": repo, "ok": False, "error": d["message"]}
    lic = (d.get("license") or {}).get("spdx_id")
    return {
        "repo": d.get("full_name") or repo,
        "ok": True,
        "stars": d.get("stargazers_count"),
        "license": lic,
        "pushed_at": (d.get("pushed_at") or "")[:10],
        "archived": bool(d.get("archived")),
        "description": (d.get("description") or "").strip(),
        "topics": (d.get("topics") or [])[:6],
    }


def main() -> int:
    seen: list[str] = []
    for repos in CHAPTERS.values():
        for r in repos:
            if r not in seen:
                seen.append(r)

    data: dict[str, dict] = {}
    bad: list[str] = []
    for repo in seen:
        item = fetch(repo)
        data[repo] = item
        flag = "ok " if item["ok"] else "ERR"
        print(f"[{flag}] {repo} {item.get('stars', item.get('error'))}")
        if not item["ok"]:
            bad.append(repo)

    payload = {
        "fetched_at": "2026-10-21",
        "source": "GitHub REST API /repos/{owner}/{repo}",
        "chapters": CHAPTERS,
        "repos": data,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\n抓取 {len(seen)} 个，成功 {len(seen) - len(bad)}，失败 {len(bad)}")
    if bad:
        print("失败列表：", ", ".join(bad))
    print(f"-> {OUT}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
