"""补齐 GitHub 元数据快照：API 额度用尽时用 shields 徽章回退。

背景
--------------------------------------------------------------------
`fetch_repos.py` 逐个走 REST API，未认证额度 60 次/小时。第一次抓取后额度见底，
剩余仓库要么是 301 重命名（curl 未跟随后拿到空 body），要么是路径变更。
本脚本做两件事：
  1) 修正章节→仓库映射（重命名后的规范名、替换掉的 404 仓库）；
  2) 对仍缺的仓库用 shields.io 徽章取千位近似星数，并在快照里标记 approx=True。

用法：python server/scripts/_agent_src/patch_repos.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).parent
SNAP = HERE / "repos.json"

CHAPTERS: dict[str, list[str]] = {
    "agent-ch01": ["microsoft/AI-For-Beginners", "Hannibal046/Awesome-LLM",
                   "datawhalechina/self-llm", "eugeneyan/applied-ml"],
    "agent-ch02": ["dair-ai/Prompt-Engineering-Guide", "openai/openai-cookbook",
                   "anthropics/claude-cookbooks", "microsoft/promptflow"],
    "agent-ch03": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1",
                   "deepseek-ai/awesome-deepseek-integration", "ollama/ollama"],
    "agent-ch04": ["eugeneyan/applied-ml", "Azure-Samples/azure-search-openai-demo",
                   "GokuMohandas/Made-With-ML", "microsoft/AI-For-Beginners"],
    "agent-ch05": ["langchain-ai/langchain", "run-llama/llama_index",
                   "infiniflow/ragflow", "HKUDS/LightRAG"],
    "agent-ch06": ["vllm-project/vllm", "sgl-project/sglang",
                   "ggml-org/llama.cpp", "ollama/ollama"],
    "agent-ch07": ["huggingface/peft", "hiyouga/LLaMA-Factory",
                   "unslothai/unsloth", "huggingface/trl"],
    "agent-ch08": ["karpathy/nanoGPT", "karpathy/build-nanogpt",
                   "huggingface/transformers", "jingyaogong/minimind"],
    "agent-ch09": ["huggingface/diffusers", "openai/CLIP",
                   "AUTOMATIC1111/stable-diffusion-webui", "QwenLM/Qwen3-VL"],
    "agent-ch10": ["openai/evals", "EleutherAI/lm-evaluation-harness",
                   "explodinggradients/ragas", "microsoft/AI-For-Beginners"],
    "agent-ch11": ["langchain-ai/langgraph", "microsoft/autogen", "crewAIInc/crewAI",
                   "openai/openai-agents-python", "modelcontextprotocol/python-sdk",
                   "FoundationAgents/MetaGPT"],
    "agent-ch12": ["langgenius/dify", "n8n-io/n8n",
                   "Azure-Samples/azure-search-openai-demo", "microsoft/AI-For-Beginners"],
    "agent-ch13": ["mli/paper-reading", "dair-ai/ML-Papers-of-the-Week",
                   "Hannibal046/Awesome-LLM"],
    "agent-ch14": ["donnemartin/system-design-primer", "yangshun/tech-interview-handbook",
                   "alirezadir/Machine-Learning-Interviews", "chiphuyen/ml-interviews-book"],
    "agent-ch15": ["datawhalechina/llm-universe", "datawhalechina/happy-llm",
                   "langchain-ai/langgraph", "langgenius/dify"],
    "agent-ch16": ["alirezadir/Machine-Learning-Interviews", "chiphuyen/ml-interviews-book",
                   "GokuMohandas/Made-With-ML", "donnemartin/system-design-primer"],
}

# 已用 API 实测但第一次抓取未落盘的仓库（值为 API 原始结果）
KNOWN_EXACT = {
    "anthropics/claude-cookbooks": 53639,
}


def shields_stars(repo: str) -> tuple[int | None, bool]:
    """返回 (stars, approx)。徽章只给 '76k' / '9.9k' 这种千位值。"""
    p = subprocess.run(
        ["curl", "-sL", "--max-time", "20", "--noproxy", "*",
         f"https://img.shields.io/github/stars/{repo}.json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if p.returncode != 0:
        return None, True
    try:
        msg = json.loads(p.stdout).get("message", "")
    except json.JSONDecodeError:
        return None, True
    m = re.fullmatch(r"([\d.]+)([kKmM]?)", msg.strip())
    if not m:
        return None, True
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "k":
        val *= 1_000
    elif unit == "m":
        val *= 1_000_000
    return int(round(val, -2)) if val >= 1000 else int(val), True


def main() -> int:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    repos: dict[str, dict] = snap["repos"]

    for canon, stars in KNOWN_EXACT.items():
        repos[canon] = {"repo": canon, "ok": True, "stars": stars,
                        "license": "MIT", "pushed_at": "", "archived": False,
                        "description": "", "topics": [], "approx": False,
                        "stars_source": "github_api"}

    wanted = {r for group in CHAPTERS.values() for r in group}
    missing = [r for r in sorted(wanted) if r not in repos or not repos[r].get("ok")]
    print(f"待补 {len(missing)} 个：{', '.join(missing)}")
    for repo in missing:
        stars, approx = shields_stars(repo)
        if stars is None:
            print(f"[FAIL] {repo}")
            continue
        repos[repo] = {"repo": repo, "ok": True, "stars": stars,
                       "license": None, "pushed_at": "", "archived": False,
                       "description": "", "topics": [], "approx": approx,
                       "stars_source": "shields_io"}
        print(f"[ok] {repo} ≈{stars}")

    # 统一补字段，方便生成器按同一形状读取
    for item in repos.values():
        item.setdefault("approx", False)
        item.setdefault("stars_source", "github_api")

    snap["chapters"] = CHAPTERS
    snap["repos"] = repos
    snap["note"] = ("stars 为 GitHub REST API 实测（2026-10-21）；approx=true 者为 "
                    "shields.io 徽章千位近似，展示时加 ≈。")
    SNAP.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    absent = sorted(wanted - set(repos))
    print(f"\n章节引用 {len(wanted)} 个仓库，快照覆盖 {len(wanted) - len(absent)} 个")
    if absent:
        print("仍缺：", ", ".join(absent))
    return 0 if not absent else 1


if __name__ == "__main__":
    raise SystemExit(main())
