# -*- coding: utf-8 -*-
"""把新增的 ai-ch09（生成模型）/ ai-ch10（训练工程）接入大纲与前端 bundle。

做三件事：
1. content/ai/_manifest.json 追加两章（A1 深度学习基础 / A2 大模型原理与训练），
   使「规划覆盖」分母从 138 变 140；
2. frontend/src/data/bundle.ts 的 ai 学科追加两章（order 续到 33/34），
   否则 UI 里选不到这两章（有内容、无入口的老问题）；
3. 打印前后对比，便于核对。

用法：
    python scripts/add_ai_dl_chapters.py            # dry-run
    python scripts/add_ai_dl_chapters.py --apply
    python scripts/add_ai_dl_chapters.py --restore
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "ai" / "_manifest.json"
BUNDLE = ROOT / "frontend" / "src" / "data" / "bundle.ts"
BACKUP = ROOT / "content" / "_backup_manifest" / "ai_dl"
BUNDLE_BACKUP = ROOT / "frontend" / "src" / "data" / "_backup_bundle"

BUNDLE_RE = re.compile(r"(export const BUNDLE = )(\{.*\})( as unknown as Bundle;)", re.S)

NEW_CHAPTERS = [
    {
        "id": "ai-ch09",
        "order": 9,
        "group": "A1",
        "title": "生成模型：从自编码器到扩散",
        "summary": "AE 的重建目标与「不是生成模型」的边界；VAE 的 ELBO 推导、重参数化、高斯 KL 闭式解与后验坍塌；"
                   "GAN 的最优判别器（密度比估计）与 2JSD−log4、模式崩塌、WGAN/谱归一化、条件生成；"
                   "扩散的前向闭式解、ELBO→L_simple 的推导与丢弃权重的代价、ε 预测＝得分预测、DDIM 跳步、CFG 引导、"
                   "SDE/概率流 ODE 与 Flow Matching 的统一视角；归一化流、自回归与生成模型评估（FID 的四个偏差、"
                   "precision/recall 与 CLIPScore 三件套）。",
        "prerequisites": ["ai-ch01", "ai-ch02"],
        "status": "complete",
        "books": [
            "《Deep Learning》Goodfellow 第14章（自编码器）、第20章（深度生成模型）",
            "Kingma & Welling, 2013 · Auto-Encoding Variational Bayes",
            "Goodfellow et al., 2014 · Generative Adversarial Nets",
            "Ho et al., 2020 · Denoising Diffusion Probabilistic Models",
            "Song et al., 2021 · Score-Based Generative Modeling through SDEs",
        ],
        "bundle_github": ["huggingface/diffusers", "CompVis/latent-diffusion", "ermongroup/ddim", "openai/guided-diffusion"],
    },
    {
        "id": "ai-ch10",
        "order": 10,
        "group": "A2",
        "title": "训练工程与规模化：从「能跑通」到「能训起来」",
        "summary": "初始化的方差保持（Xavier/He/正交）与动力学等距；BN/LN/RMSNorm/GroupNorm 的统计维度差异、"
                   "BN 的训练/推理不一致、Pre-LN vs Post-LN 的梯度路径；Adam/AdamW 的解耦权重衰减、warmup+cosine、"
                   "梯度裁剪与 loss spike 的四类成因与回滚策略；fp16/bf16 的范围-精度取舍、loss scaling、fp32 主权重；"
                   "训练显存账（16 B/参数）、激活重计算；DDP/TP/PP/EP 与 ZeRO 三阶段、FSDP；"
                   "Scaling Law（$C=6ND$、Chinchilla 20 tokens/参数、过训练）、数据配比与去重、loss 曲线诊断与可复现性。",
        "prerequisites": ["ai-ch01", "ai-ch03"],
        "status": "complete",
        "books": [
            "《Deep Learning》Goodfellow 第7-8章（正则化、优化）",
            "Rajbhandari et al., 2020 · ZeRO: Memory Optimizations Toward Training Trillion Parameter Models",
            "Loshchilov & Hutter, 2019 · Decoupled Weight Decay Regularization",
            "Hoffmann et al., 2022 · Training Compute-Optimal Large Language Models（Chinchilla）",
        ],
        "bundle_github": ["microsoft/DeepSpeed", "NVIDIA/Megatron-LM", "google-research/tuning_playbook", "karpathy/nanoGPT"],
    },
]


def apply_manifest(dry: bool) -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = {c["id"] for c in m["chapters"]}
    added = []
    for ch in NEW_CHAPTERS:
        if ch["id"] in ids:
            print(f"  manifest: {ch['id']} 已存在，跳过")
            continue
        item = {
            "id": ch["id"], "order": ch["order"], "group": ch["group"],
            "title": ch["title"], "summary": ch["summary"],
            "prerequisites": ch["prerequisites"], "status": ch["status"],
            "books": ch["books"],
            "resources": {
                "github": ch["bundle_github"], "github_stars": [], "github_notes": [],
                "github_fetched_at": "2026-10-27", "bilibili": "", "books": [],
                "leetcode": [], "nowcoder": [],
            },
        }
        m["chapters"].append(item)
        added.append(ch["id"])
    if not added:
        return
    m["chapters"].sort(key=lambda c: int(c.get("order") or 0))
    m["note"] = m["note"].replace(
        "覆盖深度学习基础 → 大模型原理",
        "覆盖深度学习基础（含生成模型 ai-ch09）→ 大模型原理与训练工程（含 ai-ch10）",
    )
    print(f"  manifest: +{added} -> 共 {len(m['chapters'])} 章")
    if not dry:
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_bundle(dry: bool) -> None:
    text = BUNDLE.read_text(encoding="utf-8")
    mt = BUNDLE_RE.search(text)
    if not mt:
        raise SystemExit("bundle.ts 解析失败")
    data = json.loads(mt.group(2))
    pack = data["chapters"]["ai"]
    have = {c["id"] for c in pack["chapters"]}
    before = len(pack["chapters"])
    next_order = max(int(c.get("order") or 0) for c in pack["chapters"]) + 1
    added = []
    for ch in NEW_CHAPTERS:
        if ch["id"] in have:
            print(f"  bundle: {ch['id']} 已存在，跳过")
            continue
        pack["chapters"].append({
            "id": ch["id"], "order": next_order, "group": ch["group"],
            "title": ch["title"], "summary": ch["summary"],
            "status": "complete", "prerequisites": ch["prerequisites"],
            "github": ch["bundle_github"], "github_stars": [], "books": ch["books"],
        })
        next_order += 1
        added.append(ch["id"])
    if not added:
        return
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    new_text = text[: mt.start(2)] + payload + text[mt.end(2):]
    print(f"  bundle: ai 章节 {before} -> {len(pack['chapters'])}（+{added}）")
    if not dry:
        snap = BUNDLE_BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
        snap.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUNDLE, snap / "bundle.ts")
        BUNDLE.write_text(new_text, encoding="utf-8")
        print(f"  备份：{snap}")


def restore() -> int:
    snaps = sorted(p for p in BACKUP.iterdir() if p.is_dir()) if BACKUP.exists() else []
    if not snaps:
        print("无 manifest 备份")
        return 1
    shutil.copy2(snaps[-1] / "_manifest.json", MANIFEST)
    print(f"已还原 manifest（{snaps[-1].name}）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.restore:
        return restore()
    dry = not args.apply
    if not dry:
        BACKUP.mkdir(parents=True, exist_ok=True)
        snap = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
        snap.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MANIFEST, snap / "_manifest.json")
    apply_manifest(dry)
    apply_bundle(dry)
    if dry:
        print("\n(dry-run，未写入；加 --apply 执行)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
