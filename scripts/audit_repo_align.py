# -*- coding: utf-8 -*-
"""仓库-笔记错位守门：`_manifest.json` 的 github_notes 代码路径，必须属于本章登记的仓库。

为什么需要它
------------
`audit_source_anchor.py` 只校验 `§x.y` 是否命中真实小节标题，测不出另一种错位：
笔记里写的代码路径前缀挂错了仓库——例如把 `spark` 的 `sql/catalyst/...` 写进 hadoop 那一行的
notes。锚点标题判据对这种「行与仓库错配」完全失明。

本脚本独立校验：每条 note 里反引号括起、且形如真实代码路径的片段，至少要命中本章
某个已登记仓库的合法前缀；一个都不命中即「疑似错位」。

判定保守（宁松勿严），以避免误报：
  - 只把「带代码扩展名」或「≥2 级目录且含小写字母」的反引号片段当作代码路径；
    纯大写且无扩展名的串（如 `SELECT/INSERT/UPDATE/DELETE`）不是路径，不比对。
  - 逐位配对（github_notes[i] 对应 github[i]）：配对仓库未登记 → 不判；命中即过。
  - 配对仓库已登记但路径不命中时，放宽到「本章其它已登记仓库」任一命中即过
    （多笔记指向同仓库、或笔记跨本章多个仓库均属合法）。
  - 若笔记正文显式点名了配对仓库的 owner/slug（作者已写明归属），视为对齐。
  - 不强制 github 与 github_notes 等长：一条笔记可引用同仓库、或多笔记引用同仓库。

退出码
------
0  无路径错位
1  存在路径错位
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

_CODE_EXT = (".py", ".cc", ".rs", ".c", ".ts", ".h", ".hpp", ".md", ".scala",
             ".java", ".go", ".yml", ".yaml", ".json", ".xml", ".gradle",
             ".toml", ".sql", ".txt")

# 仓库 -> 该仓库内合法路径前缀（任一命中即算对得上）
PREFIX = {
    "tensorflow/tensorflow": ["tensorflow/", "keras/"],
    "huggingface/transformers": ["src/transformers/", "src/peft"],
    "huggingface/datasets": ["src/datasets/"],
    "huggingface/diffusers": ["src/diffusers/"],
    "huggingface/text-generation-inference": ["router/", "server/"],
    "firecrawl/firecrawl": ["apps/"],
    "langgenius/dify": ["api/", "web/", "dify-agent"],
    "langchain-ai/langchain": ["libs/"],
    "vllm-project/vllm": ["vllm/", "csrc/"],
    "ggml-org/llama.cpp": ["ggml/", "src/", "convert_hf", "examples/", "common/"],
    "ggerganov/llama.cpp": ["ggml/", "src/", "convert_hf", "examples/", "common/"],
    "triton-inference-server/server": ["src/"],
    "microsoft/DeepSpeed": ["deepspeed/"],
    "NVIDIA/Megatron-LM": ["megatron/"],
    "karpathy/nanoGPT": ["train.py", "model.py", "config/", "sample.py"],
    "microsoft/OmniParser": ["README.md", "omnitool/", "util/"],
    "openai/CLIP": ["clip/", "README.md", "model.py"],
    "OpenGVLab/InternVL": ["internvl_chat/", "README.md"],
    "CompVis/latent-diffusion": ["ldm/", "configs/"],
    "ermongroup/ddim": ["models/", "configs/", "runners/"],
    "openai/guided-diffusion": ["guided_diffusion/", "scripts/"],
    "facebookresearch/llama": ["README.md", "llama/"],
    "google-research/tuning_playbook": ["README.md", "「"],
    "Significant-Gravitas/AutoGPT": ["classic/", "autogpt_platform/", "README.md"],
    "pytorch/pytorch": ["torch/", "aten/"],
    "scikit-learn/scikit-learn": ["sklearn/"],
    "numpy/numpy": ["numpy/"],
    "pandas-dev/pandas": ["pandas/"],
    "redis/redis": ["src/"],
    "apache/kafka": ["clients/", "core/", "streams/", "internals/"],
    "spring-projects/spring-framework": ["spring-core/", "spring-web/", "spring-beans/",
                                        "org/springframework/", "spring-webmvc/"],
    "spring-projects/spring-boot": ["spring-boot-project/", "core/", "spring-boot/"],
    "apache/dubbo": ["dubbo-"],
    "macrozheng/mall": ["mall-", "mall-common/", "document/", "sql/", "code/"],
    "Snailclimb/JavaGuide": ["docs/"],
    "doocs/advanced-java": ["docs/"],
    "jwasham/coding-interview-university": ["README.md"],
    "TheAlgorithms/Java": ["src/"],
    "concurrent-programming": ["README.md"],
    "apache/spark": ["core/", "sql/", "streaming/"],
    "apache/hadoop": ["hadoop-"],
    "apache/hive": ["ql/", "standalone-metastore/", "common/"],
}


def is_code_path(p: str) -> bool:
    """只认真实代码路径：带代码扩展名，或 ≥2 级目录且含小写字母（排除纯大写伪路径）。"""
    if p.endswith(_CODE_EXT):
        return True
    if p.count("/") >= 2 and any(c.islower() for c in p):
        return True
    return False


def note_paths(note: str) -> list[str]:
    return [p for p in re.findall(r"`([^`]+)`", note)
            if is_code_path(p) and not p.startswith("http")]


def slug_owner(repo: str) -> tuple[str, str]:
    if "/" in repo:
        owner, slug = repo.split("/", 1)
        return slug, owner
    return repo, repo


def name_in_note(repo: str, note: str) -> bool:
    slug, owner = slug_owner(repo)
    n = note.lower()
    return slug.lower() in n or owner.lower() in n


def path_matches_repo(path: str, repo: str) -> bool:
    pre = PREFIX.get(repo)
    if not pre:
        return False  # 未登记仓库不参与比对
    for x in pre:
        if path.startswith(x) or x in path:
            return True
    return False


def note_aligned(repos: list[str], note: str, idx: int) -> bool:
    """note 的代码路径至少要命中本章某个已登记仓库，或正文点名了配对仓库。"""
    paths = note_paths(note)
    if not paths:
        return True  # 无代码路径可验

    paired = repos[idx] if idx < len(repos) else None
    if paired and path_matches_repo(paths[0], paired):
        return True
    # 放宽：命中本章任意其它已登记仓库也算过
    for r in repos:
        if r == paired:
            continue
        if path_matches_repo(paths[0], r):
            return True
    # 正文显式点名配对仓库 -> 作者已写明归属
    if paired and name_in_note(paired, note):
        return True
    # 配对仓库未登记、且其路径不匹配任何已登记仓库 -> 无法判定，放行（宁松勿严）
    if paired and paired not in PREFIX:
        return True
    return False


def iter_units(subj: str, data: dict):
    units = list(data.get("chapters", []))
    if subj == "clang":
        units = list(((data.get("clang_module") or {}).get("units")) or [])
    return units


def main() -> None:
    only = sys.argv[1:] or None
    subjects = only or [
        p.name for p in sorted(CONTENT.iterdir()) if (p / "_manifest.json").exists()
    ]
    total_bad = 0
    bad_lines: list[str] = []

    for subj in subjects:
        mf = CONTENT / subj / "_manifest.json"
        if not mf.exists():
            continue
        data = json.loads(mf.read_text(encoding="utf-8"))
        for ch in iter_units(subj, data):
            cid = ch.get("id") or ch.get("chapter_id")
            r = ch.get("resources") or {}
            repos = r.get("github") or []
            notes = r.get("github_notes") or []
            if not repos and not notes:
                continue
            n = max(len(repos), len(notes))
            for i in range(n):
                note = notes[i] if i < len(notes) else ""
                if not note:
                    continue
                if not note_aligned(repos, note, i):
                    total_bad += 1
                    repo = repos[i] if i < len(repos) else "?(无对应仓库)"
                    bad_lines.append(
                        f"  疑似错位 {subj}/{cid}#{i + 1}  {repo}  笔记路径未命中本章任何仓库前缀"
                    )

    print(f"仓库-笔记错位检查：合计 {total_bad} 条")
    if bad_lines:
        print()
        for ln in bad_lines[:60]:
            print(ln)
        if len(bad_lines) > 60:
            print(f"  ... 另有 {len(bad_lines) - 60} 条")
    sys.exit(0 if total_bad == 0 else 1)


if __name__ == "__main__":
    main()
