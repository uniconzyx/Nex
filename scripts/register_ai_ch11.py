# -*- coding: utf-8 -*-
"""把 ai-ch11 登记进 content/ai/_manifest.json（A4 组末尾）。

仓库星数来自 2026-10-28 的 GitHub API 实取（curl 子进程，见本仓工具坑记录），
B 站 BV 号已逐个用 `x/web-interface/view` 验证可播（标题/时长人工核对）。

用法：python scripts/register_ai_ch11.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "ai" / "_manifest.json"

ENTRY = {
    "id": "ai-ch11",
    "order": 11,
    "group": "A4",
    "title": "模型服务化落地：从 train() 跑到线上不崩",
    "summary": (
        "训练跑通到服务上线之间缺的七件事：权重序列化与版本、输入契约、批处理、超时、降级、容量、可观测。"
        "动态 batching 的延迟-吞吐对冲（固定开销摊销、max_batch 与 max_wait 的乘性关系、"
        "等待窗口由 SLO 倒推）；输入契约五类校验（形状/数值/长度/编码/白名单）与 NaN 的三条反直觉性质；"
        "故障三形态（慢/错/挂）与超时退避抖动、降级策略矩阵、模型版本四段式命名与同名覆盖检测、"
        "金丝雀发布与「代码-模型一起回滚」、三层健康检查（alive/ready/warm）与冷启动预热。"
        "与 ai-ch08 的分工：ch08 讲「为什么快」，本章讲「怎么摆上去且半夜不崩」。"
    ),
    "prerequisites": ["ai-ch08", "fs-ch04"],
    "status": "complete",
    "books": [],
    "resources": {
        "github": [
            "vllm-project/vllm",
            "ggml-org/llama.cpp",
            "mlc-ai/mlc-llm",
            "huggingface/text-generation-inference",
            "triton-inference-server/server",
            "bentoml/BentoML",
        ],
        "github_stars": [95727, 132583, 23284, 10880, 11115, 8923],
        "github_notes": [
            "PagedAttention + 连续批的工业实现：看它如何把「请求级批」拆成「token 级批」，"
            "对应本章「批内请求同构」的第三条出路",
            "纯 C/C++ 推理：读 `examples/server` 的队列与超时实现，看最小可用的 batching 长什么样",
            "把模型编译成可部署产物：冷启动与产物体积的关系在这里最直观",
            "生产级推理服务的网关层：请求排队、动态批、token 流式返回的完整实现",
            "多框架统一服务：模型仓库、版本目录结构、并发实例配置，是「模型版本化」的现成范式",
            "把模型打成可部署 API：`service.py` 的并发与超时配置，适合做本章项目骨架的参考",
        ],
        "github_fetched_at": "2026-10-28",
        "books": [
            "《Designing Machine Learning Systems》Chip Huyen（第 7-8 章：模型部署与服务）",
            "《Site Reliability Engineering》Google（第 21 章：过载处理，退避与降级的经典论述）",
            "《Release It!》Michael Nygard（熔断、超时、快速失败的设计模式）",
        ],
        "leetcode": [],
        "nowcoder": [],
        "bilibili": "https://www.bilibili.com/video/BV14YopBEEGs/",
        "bilibili_list": [
            {
                "name": "vLLM 推理优化从入门到精通（KV Cache 与连续批）",
                "url": "https://www.bilibili.com/video/BV14YopBEEGs/",
                "note": "长视频，按需跳看：先看「调度与 batching」一节，回到本章验证 max_wait 的作用；"
                        "再看 KV Cache 分页，衔接 ai-ch13",
                "bv": "BV14YopBEEGs",
            },
            {
                "name": "10 分钟用 vLLM 部署大模型（喂饭教程）",
                "url": "https://www.bilibili.com/video/BV17gXaBnE6A/",
                "note": "最短的上手路径：起服务、发请求、看日志。用它对本章「七件事」逐条检查它没做什么",
                "bv": "BV17gXaBnE6A",
            },
            {
                "name": "大模型推理优化原理（6 分钟速览）",
                "url": "https://www.bilibili.com/video/BV1Guth61EJz/",
                "note": "先把 prefill/decode 两阶段的直觉建立起来，再读本章 batching 部分会顺很多",
                "bv": "BV1Guth61EJz",
            },
        ],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [c["id"] for c in m["chapters"]]
    if ENTRY["id"] in ids:
        print(f"  [skip] {ENTRY['id']} 已存在")
        return 0

    # 插在 A4 组最后（当前 A4 只有 ai-ch08），再统一重排 order
    a4 = [i for i, c in enumerate(m["chapters"]) if c["group"] == "A4"]
    pos = max(a4) + 1 if a4 else len(m["chapters"])
    m["chapters"].insert(pos, ENTRY)
    for i, c in enumerate(m["chapters"], 1):
        c["order"] = i
    assert len({c["order"] for c in m["chapters"]}) == len(m["chapters"]), "order 不唯一"

    order = [c["id"] for c in m["chapters"]]
    print(f"  ai 学科 {len(order)} 章 · 插入位置 {pos} · A4 组 = "
          f"{[c['id'] for c in m['chapters'] if c['group'] == 'A4']}")

    if not args.apply:
        print("\n  （dry-run，未写盘；加 --apply 生效）")
        return 0

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  已写入 {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
