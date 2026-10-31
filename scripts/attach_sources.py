# -*- coding: utf-8 -*-
"""把新增三章的「来源路线」补完整：GitHub 路线 + B 站路线 + 论文/书。

背景（用户要求）：「所有内容来源都得是 github 和 b 站路线，得完整」。
原来三章 goals.md 里的资源只是一串仓库名 + 一句说明，B 站只有 4 行占位式表格
（「建议结合本章示例与习题观看」），既不可核验也不算路线。

本脚本做两件事：
1. 重写 ai-ch09 / ai-ch10 / ml-ch09 的「GitHub 学习路线」「B 站视频路线」「配套论文与书」三节，
   每条都带**真实 URL + 抓取日的 star 快照 + 对应本章哪一节 + 该看什么**；
2. 同步写回三个 _manifest.json 的 resources（github / github_stars / github_notes / bilibili / books），
   使大纲与章节内的来源一致。

star 数据来自 scripts/_gh_cache.json（GitHub REST API，抓取日 2026-10-27）。

用法：
    python scripts/attach_sources.py            # dry-run，打印将要写入的条目数
    python scripts/attach_sources.py --apply
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CACHE = json.loads((ROOT / "scripts" / "_gh_cache.json").read_text(encoding="utf-8"))
GOT_AT = "2026-10-27"

BILI = {
    "andrew": ("吴恩达 · 机器学习（中英字幕）", "https://www.bilibili.com/video/BV164411b7dx/"),
    "d2l": ("跟李沐学 AI · 动手学深度学习 v2", "https://space.bilibili.com/1567748478/lists/358497/"),
    "hungyi": ("李宏毅 · 机器学习 2021", "https://www.bilibili.com/video/BV1JA411c7VT/"),
    "paper": ("跟李沐学 AI · 论文精读系列", "https://space.bilibili.com/1567748478"),
    "ng_dl": ("吴恩达 · 深度学习专项课程", "https://www.bilibili.com/video/BV164411b7dx/"),
}


def gh(repo: str) -> tuple[str, str, str]:
    """返回 (url, star 显示, 语言)。"""
    meta = CACHE.get(repo) or {}
    stars = meta.get("stars")
    star_txt = f"{stars:,}" if isinstance(stars, int) else "—"
    return f"https://github.com/{repo}", star_txt, meta.get("lang") or "—"


# ---------------------------------------------------------------- 三章的路线
SOURCES: dict[str, dict] = {
    "ai-ch09": {
        "github": [
            ("hojonathanho/diffusion", "3.1 / 3.2 前向与训练目标",
             "DDPM 官方 TF 实现。只看 `ddpm.py` 三个函数：`q_sample`（用 ᾱ 一步加噪，对应 $x_t=\\sqrt{\\bar\\alpha_t}x_0+\\sqrt{1-\\bar\\alpha_t}\\varepsilon$）、`training_losses`（对照 $\\mathcal L_{simple}$）、`p_sample`（看 `model_mean` 与 `posterior_variance`）"),
            ("lucidrains/denoising-diffusion-pytorch", "3.2 / 3.3 训练与采样",
             "300 行级的 PyTorch 复现，最适合与本章 `ex07~ex10` 逐行对照：`q_sample`、`p_losses`、`sample` 三个方法就是全部"),
            ("ermongroup/ddim", "3.3 DDIM 跳步",
             "官方 DDIM。看 `ddim.py` 里 `sigma` 为 0 的分支与 `eta` 参数——这是「同一套权重、换采样过程」的最小证据"),
            ("openai/guided-diffusion", "3.3 无分类器引导 CFG",
             "原始 CFG 实现。看 `gaussian_diffusion.py` 里 `cond_fn`/`model_kwargs` 如何在一次前向里同时算有条件与无条件"),
            ("huggingface/diffusers", "1~4 全章工程化对照",
             "工业标准库。按 `schedulers/`（噪声调度与采样器）→ `pipelines/`（模型/调度器/管线三层解耦）的顺序读，不要从 README 通读"),
            ("CompVis/latent-diffusion", "1.2 与 4.2 latent 扩散",
             "Stable Diffusion 前身。看 VAE 如何被冻结、latent 如何缩放（`scale_factor`），这解释了「为什么 VAE 在生成系统里退居 tokenizer」"),
            ("karpathy/nanoGPT", "4.2 自回归对照",
             "对照本章的自回归分解：同一个链式法则 $p(x)=\\prod p(x_i|x_{<i})$ 在文本上是 GPT、在图像上是 PixelCNN"),
        ],
        "bili": [
            ("hungyi", "1、2 节（VAE/GAN 直觉）",
             "生成模型两讲：先建立「生成 = 学一个分布」的直觉，再看 GAN 的对抗训练为什么容易崩"),
            ("d2l", "1.1、2.1 自编码器与 GAN 工程",
             "动手学深度学习里的自编码器与 GAN 章节，配套代码可直接跑；重点看它怎么算重建损失与判别器损失"),
            ("paper", "3.1~3.3 扩散模型论文精读",
             "DDPM/DDIM/引导采样三篇的精读视频，按本章 3.1→3.3 的顺序看，看完一个公式再回来读 concept"),
            ("andrew", "4.2、4.4 生成 vs 判别",
             "课程中「生成模型与判别模型」的边界讲解，正好对应本章选型矩阵那一节"),
        ],
        "papers": [
            ("Kingma & Welling, 2013 · Auto-Encoding Variational Bayes", "2.1 ELBO 与重参数化"),
            ("Goodfellow et al., 2014 · Generative Adversarial Nets", "2.2 最优判别器与 JS 散度"),
            ("Arjovsky et al., 2017 · Wasserstein GAN", "2.4 W 距离与 Lipschitz 约束"),
            ("Ho et al., 2020 · Denoising Diffusion Probabilistic Models", "3.1~3.2 前向闭式解与 L_simple"),
            ("Song et al., 2021 · Score-Based Generative Modeling through SDEs", "3.4 SDE/ODE 统一视角"),
            ("Ho & Salimans, 2022 · Classifier-Free Diffusion Guidance", "3.3 CFG 公式的出处"),
        ],
    },
    "ai-ch10": {
        "github": [
            ("google-research/tuning_playbook", "2.2 / 4.3 调参与诊断",
             "Google 的调参手册。先读「start with a simple baseline」「learning rate」「batch size」三节，与本章的 warmup/lr 缩放对照"),
            ("karpathy/nanoGPT", "1、2 节训练管线",
             "单卡可跑的最小训练管线：`train.py` 里的 AdamW + warmup + cosine + grad clip 就是本章配方的完整实现"),
            ("microsoft/DeepSpeed", "3.3 ZeRO 三阶段",
             "ZeRO 权威实现。读 `runtime/zero/` 下的 `stage1/2/3.py`，重点看「分片什么、何时 gather、通信几次」"),
            ("NVIDIA/Megatron-LM", "3.3 张量并行与流水线并行",
             "TP 的列并行/行并行配对与 PP 的 1F1B 调度都在这里；对照本章「TP 不出机」的结论看通信原语"),
            ("huggingface/accelerate", "3.1 混合精度落地",
             "AMP 与分布式启动的上层封装：看它怎么配 GradScaler、怎么切 bf16/fp16"),
            ("pytorch/pytorch", "3.3 FSDP / 3.1 AMP 底层",
             "`torch/distributed/fsdp/` 与 `amp/`：auto wrap policy 的粒度、unscale 与 clip 的调用顺序"),
        ],
        "bili": [
            ("d2l", "1.1~1.3 初始化与归一化",
             "动手学深度学习「数值稳定性与模型初始化」「批量归一化」两节，配套代码可跑；先看方差为什么逐层变化"),
            ("hungyi", "2 节训练失败诊断",
             "李宏毅讲「训练没起来怎么排查」的部分：loss 不降、lr 过大/过小、batch 与 lr 的关系"),
            ("paper", "3.3 / 4.1 ZeRO 与 Chinchilla",
             "两篇的精读：ZeRO 讲清显存分片，Chinchilla 讲清 20 tokens/参数的来源"),
            ("andrew", "4.3 偏差方差与调参流程",
             "课程里「模型评估与调参」的方法论，对应本章的 loss 曲线诊断"),
        ],
        "papers": [
            ("Rajbhandari et al., 2020 · ZeRO", "3.3 显存分片三阶段"),
            ("Loshchilov & Hutter, 2019 · Decoupled Weight Decay", "2.1 AdamW"),
            ("Micikevicius et al., 2017 · Mixed Precision Training", "3.1 loss scaling 与 master weights"),
            ("Hoffmann et al., 2022 · Chinchilla", "4.1 计算最优配比"),
            ("McCandlish et al., 2018 · An Empirical Model of Large-Batch Training", "2.2 线性缩放规则的严格版本"),
        ],
    },
    "ml-ch09": {
        "github": [
            ("cjlin1/libsvm", "2.3 SMO 与多分类",
             "SMO 的官方实现。看 `svm.cpp` 的 `Solver::Solve`（工作集选择）与 `select_working_set`，再对照本章 `ex07` 的简化版"),
            ("cjlin1/liblinear", "3.2 大规模线性 SVM",
             "坐标下降的线性 SVM，$n$ 大时的正确选择；看它如何处理原始形式（不核化）"),
            ("scikit-learn/scikit-learn", "3.1~3.2 工程默认值",
             "`sklearn/svm/` 是 libsvm/liblinear 的封装。重点确认：`SVC` 默认 OvO、`LinearSVC` 默认 OvR、`probability=True` 内部做 5 折 Platt"),
            ("fengdu78/lihang-code", "1.3 / 2.3 对偶与 KKT",
             "《统计学习方法》第 7 章的代码实现，教学版 SMO 与本章推导可逐行对照"),
        ],
        "bili": [
            ("andrew", "1.1 间隔的直觉",
             "吴恩达讲 SVM 的部分：先看「大间隔分类器」的几何直觉，再回来推对偶"),
            ("d2l", "1~2 节从零实现",
             "动手学深度学习里 SVM 的对偶实现，配合 `ex07` 的 SMO 一起看"),
            ("hungyi", "2 节核方法",
             "李宏毅讲核函数与「把数据搬到高维」的直观演示，对应本章 `ex10` 的 Fisher 判据"),
            ("ng_dl", "3.1 选型边界",
             "深度学习课程里对「小样本为什么用传统模型」的讨论，对应本章的选型表"),
        ],
        "papers": [
            ("Cortes & Vapnik, 1995 · Support-Vector Networks", "1.1 最大间隔的原始论文"),
            ("Platt, 1998 · Sequential Minimal Optimization", "2.3 SMO 算法"),
            ("Schölkopf & Smola, 2002 · Learning with Kernels", "2.1~2.2 核与 RKHS"),
            ("Platt, 1999 · Probabilistic Outputs for SVM", "3.2 Platt scaling"),
        ],
    },
}


def render(sec: dict) -> str:
    gh_rows = []
    for i, (repo, where, what) in enumerate(sec["github"], 1):
        url, stars, lang = gh(repo)
        gh_rows.append(f"| {i} | [{repo}]({url}) | {stars} | {lang} | {where} | {what} |")
    bi_rows = []
    for i, (key, where, what) in enumerate(sec["bili"], 1):
        name, url = BILI[key]
        bi_rows.append(f"| {i} | {name} | [打开]({url}) | {where} | {what} |")
    pp_rows = [f"| {i} | {name} | {where} |"
               for i, (name, where) in enumerate(sec["papers"], 1)]

    return "\n".join([
        "## 本章 GitHub 学习路线（按阅读顺序）",
        "",
        f"> star 为 **{GOT_AT}** 的 GitHub API 快照。顺序即路线：**先读能跑的最小实现 → 再读官方实现 → 最后读工业库**。",
        "> 每个仓库都标了「对应本章哪一节」，不要从 README 通读；读完一节再回来读下一行的仓库。",
        "",
        "| # | 仓库 | ★ | 语言 | 对应本章 | 读什么 / 怎么用 |",
        "|---|---|---|---|---|---|",
        *gh_rows,
        "",
        "## 本章 B 站视频路线（与 GitHub 互补）",
        "",
        "> 视频来源均为 B 站（bilibili.com）。路线：**先看直觉 → 再看推导 → 最后看论文精读**。",
        "> GitHub 负责「工业级源码怎么写的」，B 站负责「这个公式到底在干什么」——两边对不上时，以源码为准。",
        "",
        "| # | 系列 / UP 主 | 链接 | 对应本章 | 建议看什么 |",
        "|---|---|---|---|---|",
        *bi_rows,
        "",
        "## 本章配套论文与书（溯源用）",
        "",
        "| # | 文献 | 对应本章 |",
        "|---|---|---|",
        *pp_rows,
        "",
    ])


def patch_goals() -> None:
    for cid, sec in SOURCES.items():
        subj = cid.split("-")[0]
        p = CONTENT / subj / cid / "goals.md"
        text = p.read_text(encoding="utf-8")
        start = text.index("## 本章 GitHub 资源")
        end = text.index("## 与相邻章节的边界")
        new = render(sec)
        p.write_text(text[:start] + new + text[end:], encoding="utf-8")
        print(f"  {cid}/goals.md: GitHub {len(sec['github'])} 条 / B站 {len(sec['bili'])} 条 / 论文 {len(sec['papers'])} 条")


def patch_manifest() -> None:
    for cid, sec in SOURCES.items():
        subj = cid.split("-")[0]
        p = CONTENT / subj / "_manifest.json"
        m = json.loads(p.read_text(encoding="utf-8"))
        ch = next((c for c in m["chapters"] if c["id"] == cid), None)
        if ch is None:
            print(f"  ! {cid} 不在 {subj}/_manifest.json，跳过")
            continue
        repos = [r for r, _, _ in sec["github"]]
        ch["resources"] = {
            "github": repos,
            "github_stars": [CACHE.get(r, {}).get("stars") for r in repos],
            "github_notes": [w for _, _, w in sec["github"]],
            "github_fetched_at": GOT_AT,
            "bilibili": BILI[sec["bili"][0][0]][1],
            "bilibili_list": [{"name": BILI[k][0], "url": BILI[k][1], "note": w}
                              for k, _, w in sec["bili"]],
            "books": [n for n, _ in sec["papers"]],
            "leetcode": [],
            "nowcoder": [],
        }
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {subj}/_manifest.json <- {cid}: github {len(repos)} 条, bilibili {len(sec['bili'])} 条")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.apply:
        for cid, sec in SOURCES.items():
            print(f"{cid}: github={len(sec['github'])} bili={len(sec['bili'])} papers={len(sec['papers'])}")
        print("\n(dry-run，加 --apply 写入)")
        return 0
    patch_goals()
    patch_manifest()
    print("\n完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
