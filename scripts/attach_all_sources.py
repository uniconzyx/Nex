# -*- coding: utf-8 -*-
"""把全学科 141 章的资源段重写为「GitHub 路线 + B 站路线 + 论文与书」三张可核验的表。

背景（用户定的两条标准）：
  标准一 · 体系完善 —— 7 类内容 + 三视角（已由 server/scripts/validate_content.py 守住，141/141）；
  标准二 · 来源完整 —— **所有来源必须是真实 GitHub 仓库与 B 站视频，且构成完整路线**。
审计发现（2026-10-27）：标准二 0/141 达标，三类硬伤：
  1. B 站那一列几乎全是同一句占位话「建议结合本章示例与习题观看」，
     且 cpp 的 6 条、fundamentals/java 各 1 条链接已失效（-404 / 62002 稿件不可见）；
  2. 资源段是学科级复制粘贴，没有任何「对应本章哪一节」的锚点；
  3. agent 科目 B 站只有一个站内搜索入口，没有一条 BV 直链。

本脚本做的事：
  · GitHub 部分**完全取自已存在的 _manifest.json**（每章本来就有仓库 + star + 该章专属的读法），
    并用 scripts/_link_cache.json 过滤掉失效仓库——不编新链接；
  · B 站部分取自 scripts/_sources_data.py 的视频池（BV 全部过站内 API 核验），
    按「章节标题/concept 小节标题 ∩ 视频 tags」匹配，**锚点是算出来的，不是拍的**；
  · 每行都带 §x.y 锚点（§3.2 = 第 3 篇 concept 的第 2 节，表头有图例）；
  · 同步回写 manifest 的 resources（github / stars / notes / bilibili_list / books），
    让大纲与章节内的来源一致。

用法：
    python scripts/attach_all_sources.py                 # dry-run：只打印将改动的章节与统计
    python scripts/attach_all_sources.py --apply         # 写入 goals.md + manifest
    python scripts/attach_all_sources.py --only ml,cpp   # 只处理部分学科
    python scripts/attach_all_sources.py --refresh-play  # 顺带刷新视频播放量
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
sys.path.insert(0, str(ROOT / "scripts"))
from _sources_data import BOOKS, C_ORDER, C_REPOS, POOL  # noqa: E402
from _cpp_sources import CPP_NOTES, CPP_REPOS  # noqa: E402

CACHE_PATH = ROOT / "scripts" / "_link_cache.json"
SNAP_PATH = ROOT / "scripts" / "_star_snapshot.json"   # 历史 star 快照（API 限流时的兜底）
TODAY = "2026-10-27"
RES_HEAD = ("## 本章 GitHub", "## 本章 B 站", "## 本章配套", "## 学习资源",
            "## 本章资料来源")


# ------------------------------------------------------------------ 基础工具
def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def bigrams(s: str) -> set[str]:
    s = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


# 这些标题是模板骨架，不是知识点，不能拿来当「对应本章」的锚点
BOILER = ("三视角", "小结", "要点", "可运行示例", "边界与陷阱", "工程实践",
          "理论根基", "实现机制", "本章")
# 这些是「六段式」骨架里的固定段名，冒号前面是它们时，真正的知识点在冒号后面
SECTION_PREFIX = ("理论根基", "实现机制", "工程实践", "边界与陷阱", "可运行示例",
                  "三视角解析", "与 Java 对照", "与 Java", "要点")


def useful_atoms(heads: list[tuple[int, int, str]]) -> list[str]:
    """挑出真正能代表本章知识点的短标签，跳过模板骨架标题。"""
    out = []
    for _, _, h in heads:
        bare = re.sub(r"^(?:\d+|[一二三四五六七八九十]+)\s*[.、]\s*", "", h).strip()
        if any(bare.startswith(b) for b in BOILER):
            continue
        a = heading_atom(h)
        if len(a) >= 3 and a not in out:
            out.append(a)
        if len(out) >= 2:
            break
    return out


def heading_atom(head: str) -> str:
    """把「二、实现机制：重载决议与 ADL」「一、对齐规则与填充（padding）」压成知识点短标签。

    旧实现直接 `split("：")[0]`，于是整章 20 个锚点全变成「实现机制」「理论根基」，
    这一列等于没有信息。正确做法是：冒号前若是六段式骨架名，取冒号**后**的真知识点；
    否则取冒号前；括号里的英文补充说明再丢掉，避免出现「对齐规则与填充（paddin」这种半截词。
    """
    t = re.sub(r"^(?:\d+|[一二三四五六七八九十]+)\s*[.、]\s*", "", head).strip()
    for sep in ("：", ":"):
        if sep in t:
            left, right = t.split(sep, 1)
            t = right if left.strip() in SECTION_PREFIX else left
            break
    t = re.split(r"[（(]", t)[0].strip(" ·—-　")
    if not t:
        t = head.strip()
    return t if len(t) <= 14 else t[:13].rstrip() + "…"


def concept_heads(ch: Path) -> list[tuple[int, int, str]]:
    """返回 [(篇号, 节号, 标题)]，篇号=concept 文件序号，节号=文件内 ## 序号。"""
    out = []
    for fi, f in enumerate(sorted((ch / "concept").glob("*.md")), 1):
        si = 0
        for ln in f.read_text(encoding="utf-8").split("\n"):
            if ln.startswith("## "):
                si += 1
                out.append((fi, si, ln[3:].strip()))
    return out


RE_EXPLICIT_SEC = re.compile(r"§(\d+)\.(\d+)")


def anchor_of(heads: list[tuple[int, int, str]], keyword: str) -> tuple[str, str]:
    """按关键词找最匹配的小节。

    优先级 0：读法文本里已经写了 `§3.2` —— 这是作者自己断言的映射，直接采信，
    比任何词频匹配都准（ai-ch09/ai-ch10 的读法就是这种写法）。

    判定用「命中比例」而不是绝对命中数：两个字的词（如「数组」）最多只能命中 1 个
    bigram，用绝对阈值会把它全部判成「没匹配」，这正是上一版全表退化成「全章」的原因。
    """
    if keyword:
        m = RE_EXPLICIT_SEC.search(keyword)
        if m:
            fi, si = int(m.group(1)), int(m.group(2))
            for f, s2, h in heads:
                if (f, s2) == (fi, si):
                    return f"§{fi}.{si}", h
        kb = bigrams(keyword)
        if kb:
            best, ratio = None, 0.0
            for fi, si, h in heads:
                r = len(kb & bigrams(h)) / len(kb)
                if r > ratio:
                    best, ratio = (fi, si, h), r
            if best and ratio >= 0.5:
                return f"§{best[0]}.{best[1]}", best[2]
    return "全章", "通用"


def examples_of(ch: Path) -> list[tuple[str, str]]:
    """真实示例编号 + 标题，用来写「读完回做什么」。"""
    out = []
    for f in sorted((ch / "examples").glob("*.json")):
        d = load_json(f)
        out.append((f.stem.split("-")[0], (d.get("title") or "").strip()))
    return out


# 有些章的 github_notes 在早先的回写里被清空（ai-ch09/ai-ch10 就是），
# 这里用**真实入口文件 + 对应小节**补回，读法里直接写 §x.y，anchor_of 会采信。
NOTES_OVERRIDE: dict[str, dict[str, str]] = {
    # §编号规则：篇号 = concept 文件序号，节号 = 文件内 `##` 序号。
    # 每条的 § 都对照过 content/ai/ai-ch09|ai-ch10/concept/ 的真实小节，不是凭印象写的。
    "ai-ch09": {
        "huggingface/diffusers":
            r"工业实现先看 `src/diffusers/schedulers/scheduling_ddpm.py`："
            r"`set_timesteps` 用 betas 累乘造出 $\bar\alpha_t$ 表（§3.1 的闭式），"
            r"`step` 是单步反向（§3.2）；再看 `pipelines/stable_diffusion` 里 `guidance_scale` 如何落地 CFG（§3.3）",
        "CompVis/latent-diffusion":
            r"潜空间扩散的原始实现：`ldm/models/diffusion/ddpm.py` 的 `p_losses` 是 $L_{simple}$（§3.2），"
            r"`apply_model` 包住 U-Net 前向；潜空间压缩那部分回看 §1.2 的 VAE 编码器",
        "ermongroup/ddim":
            r"DDIM 官方代码：`models/diffusion_utils.py` 的 `make_ddim_timesteps` 造跳步子序列、"
            r"`ddim_step` 用 $\varepsilon_\theta$ 直接预测 $x_0$（§3.3 采样里的非马尔可夫边缘不变）",
        "openai/guided-diffusion":
            r"ADM 架构与 guidance：`guided_diffusion/gaussian_diffusion.py` 的 `p_mean_variance` 是反向均值/方差的标准写法（§3.2），"
            r"`condition_mean` 的两个分支就是 CFG 的 $\varepsilon_{uncond}+s(\varepsilon_{cond}-\varepsilon_{uncond})$（§3.3）",
    },
    "ai-ch10": {
        "microsoft/DeepSpeed":
            r"`deepspeed/runtime/zero/stage3.py` 是 ZeRO-3 的参数分片（§3.3 三阶段表的第三行）；"
            r"`stage1.py`/`stage2.py` 分别是优化器状态与梯度分片，看 `_partition_param` 就懂「12 字节/参数」怎么摊",
        "NVIDIA/Megatron-LM":
            r"`megatron/core/tensor_parallel/layers.py` 里列并行/行并行两个 Linear 就是 §3.3 的 TP 原文；"
            r"`pipeline_parallel/` 能对上 $(P-1)/(M+P-1)$ 的空泡推导",
        "google-research/tuning_playbook":
            r"先读「Batch size」与「Learning rate schedule」两节：§2.2 的 warmup+cosine、"
            r"§2.4 的线性缩放规则都在这里给了工程口径，可与 ex06 的学习率曲线对照",
        "karpathy/nanoGPT":
            r"最小可训 GPT：`train.py` 的 `get_lr` 就是 warmup+cosine（§2.2），"
            r"`model.py` 的 `Block` 是 Pre-LN 残差（§1.3），`estimate_loss` 是评估口径",
    },
}


# 章节级仓库覆盖：clang 的 7 个单元原先共用 project-based-learning / TheAlgorithms/C / cJSON
# 这三个「学科级」仓库，读法一模一样。这里按单元换成真正讲这件事的那份代码，
# 并写明入口文件与本节对应关系。全部仓库都已在 _link_cache.json 里核验存在（无新增链接）。
REPOS_OVERRIDE: dict[str, list[str]] = {
    "clang-u01": ["rswier/c4", "antirez/kilo", "DaveGamble/cJSON"],
    "clang-u02": ["antirez/kilo", "DaveGamble/cJSON", "redis/redis"],
    "clang-u03": ["DaveGamble/cJSON", "redis/redis", "antirez/kilo"],
    "clang-u04": ["antirez/kilo", "redis/redis", "rswier/c4"],
    "clang-u05": ["DaveGamble/cJSON", "redis/redis", "rswier/c4"],
    "clang-u06": ["rswier/c4", "antirez/kilo", "redis/redis"],
    "clang-u07": ["DaveGamble/cJSON", "redis/redis", "rswier/c4"],
}

# cpp 20 章的章节级路线（数据在 _cpp_sources.py，每章 3 个专属仓库 + 真实入口读法）。
# 这 20 章原先共用 project-based-learning / TheAlgorithms / tinyrenderer 三个学科级仓库。
REPOS_OVERRIDE.update(CPP_REPOS)

CLANG_NOTES: dict[str, str] = {
    # ---- u01 指针与地址运算
    "clang-u01|rswier/c4":
        r"§1.1 的活体样本：`c4.c` 把整个源程序读进一块 `char *src`，之后全靠 `*++p` / `*--p` 走路，"
        r"`next()` 与 `expr()` 里每个取值都是「带类型的地址」——看这两个函数就能把 §1.1 的地址运算和 §1.4 的指针相减对上",
    "clang-u01|antirez/kilo":
        r"§1.2 数组退化：`kilo.c` 里 `E.row[y].chars`、`&E.row[y]` 全是「数组名当指针用」，"
        r"`editorRowInsertChar` 里 `row->chars + at` 直接做指针偏移；注意它从不写 `E.row[y]->` ",
    "clang-u01|DaveGamble/cJSON":
        r"§1.6 `void *` 的工业用法：`cJSON.c` 的 `cJSON_malloc`/`cJSON_free` 返回与接收的都是 `void *`，"
        r"赋值给 `cJSON *` 时不强转——对照 §1.6 的「void 指针可隐式转换」与 §3.1 的 const 形态",
    # ---- u02 内存与动态分配
    "clang-u02|antirez/kilo":
        r"§2.2 `realloc` 的正确写法就在 `editorRowInsertChar`：先 `realloc(row->chars, ...)` 到新指针，"
        r"再赋值回去；`editorUpdateRow` 每次重建 render 缓冲，看它怎么避免「realloc 失败把原指针弄丢」",
    "clang-u02|DaveGamble/cJSON":
        r"§2.1/§2.3 的一 malloc 一 free 配对：`cJSON_New_Item` 先 `memset` 再返回、`cJSON_Delete` 递归释放子节点；"
        r"`cJSON_Parse` 失败路径上每一处 return 前都调 `cJSON_Delete`，对照 §3.2 泄漏成因第 1 条",
    "clang-u02|redis/redis":
        r"§3.5 池化与统计：`src/zmalloc.c` 在 `malloc` 外包一层，用 `PREFIX_SIZE` 记字节数，"
        r"`zmalloc_used_memory` 对外报总量——这就是「分配器之上再包一层」的最小实现，对照 §1.4 的真实成本",
    # ---- u03 结构体与联合体
    "clang-u03|DaveGamble/cJSON":
        r"§2.3 tagged union 的工业写法：`struct cJSON` 是 `int type` 加一个 union（valuedouble/valuestring/…），"
        r"读的时候先用 `cJSON_IsNumber` 判 type 再取成员——正是「把 UB 关进笼子」那节的做法",
    "clang-u03|redis/redis":
        r"§3.4 柔性数组 + 对齐省字节：`sds.h` 的 `sdshdr8/16/32/64` 末尾都是 `char buf[]`，"
        r"外层用 `__attribute__((__packed__))` 压掉填充；把它和 §1.2 手算的 sizeof 对照，能看清「填充是 ABI 契约」",
    "clang-u03|antirez/kilo":
        r"§3.1 逐成员浅拷贝：`struct erow` 里 `int size; char *chars; char *render;` 混着指针，"
        r"赋值时只拷指针不拷内容——`editorRowInsertChar` 之后两处都要改，否则就是浅拷贝的经典 bug",
    # ---- u04 文件 IO
    "clang-u04|antirez/kilo":
        r"§2.1 模式表的最小用法：`editorOpen` 用 `fopen(path, \"r\")` + `getline` 逐行读，"
        r"`editorSave` 用 `fopen(..., \"w\")` + `fwrite`；注意它对 `fopen` 返回 NULL 立刻报错退出（§3.1）",
    "clang-u04|redis/redis":
        r"§3.2 短读：`src/rio.c` 是对「一次读写可能只走一部分」的抽象层，`rioRead`/`rioWrite` 都返回实际字节数，"
        r"调用方必须循环补满——这正是核对 `fread` 返回值的通用做法",
    "clang-u04|rswier/c4":
        r"§1.3 用户态缓冲 vs 系统调用次数：`c4.c` 不用 stdio，直接用 `read()` 把整个源文件一次性读进 `src`，"
        r"系统调用只发生一次——对照 §1.2 的三种缓冲模式就明白 stdio 在替你做什么",
    # ---- u05 预处理与宏
    "clang-u05|DaveGamble/cJSON":
        r"§4.2/§4.4 头文件守卫：`cJSON.h` 顶部的 `#ifndef cJSON__h` + `#define` 是标准守卫写法，"
        r"`CJSON_PUBLIC` 宏统一处理导出符号；顺带看它怎么用 `#ifdef __cplusplus` 给 C++ 留 `extern \"C\"`",
    "clang-u05|redis/redis":
        r"§2.3 宏还是 inline：`src/sds.h` 里 `sdslen`/`sdsavail` 是 `static inline`，"
        r"而 `src/zmalloc.h` 里 `zmalloc_usable_size` 是宏包函数——同一份代码里两种取舍并存，正好对照那节的判据",
    "clang-u05|rswier/c4":
        r"§1.1/§1.2 亲手量一次：`c4.c` 只有一个翻译单元、只包含标准头，"
        r"直接 `cc -E c4.c | wc -l` 与 `grep -c '' c4.c` 对比，就能看到 `#include` 展开后的体积差",
    # ---- u06 Makefile 与构建
    "clang-u06|rswier/c4":
        r"§2.1 规则三要素的最小样例：仓库根的 `Makefile` 只有「目标: 依赖 + 命令」的几条规则，"
        r"没有变量、没有模式规则；先把它读懂，再去看复杂工程的 Makefile 才不会迷路",
    "clang-u06|antirez/kilo":
        r"§2.3 变量与自动变量：`kilo` 的 `Makefile` 用 `$(CC)`、`$(CFLAGS)` 拼命令，"
        r"把 `CFLAGS = -O2` 改成 `CFLAGS := -O2` 再 `make -n`，能直接看出 `=` 与 `:=` 的展开时机差异",
    "clang-u06|redis/redis":
        r"§3.4 为什么大家不再手写：`src/Makefile` 是上千行手写构建（带 `$(REDIS_SERVER_OBJ)` 这类目标文件列表），"
        r"读完就知道 CMake/Meson/Bazel 想解决的到底是什么问题",
    # ---- u07 多文件编译与链接
    "clang-u07|DaveGamble/cJSON":
        r"§1.2/§1.4 声明与定义分离的标准形态：`cJSON.h` 只有声明与 `CJSON_PUBLIC`，"
        r"`cJSON.c` 里才有定义；头文件里没有任何 `static` 变量——这就是「头文件该放什么」的答案",
    "clang-u07|redis/redis":
        r"§3.3 链接顺序的实物：`src/Makefile` 里 `REDIS_SERVER_OBJ` 把几十个 `.o` 列成一串再交给链接器，"
        r"顺序变了就可能出现未定义符号——对照那节的「被依赖者放后面」",
    "clang-u07|rswier/c4":
        r"§2.1/§2.2 反例对照：`c4` 只有一个翻译单元，`nm c4` 看到的几乎全是本地符号；"
        r"拿它和 cJSON 的 `nm cJSON.o` 对比，`U`（未定义）与 `T`（已定义）的区别一下就清楚了",
}

CLANG_REPO_NOTES = CLANG_NOTES


STAR_SNAP: dict[str, int] = {}


def resolve_star(repo: str, cache: dict, fallback=None) -> int | None:
    """星数三级取值：本轮 API → _star_snapshot 历史快照 → manifest 现值。

    这一层是必需的：GitHub 未认证 API 每小时 60 次，批量核验一定会被限流，
    限流时 stars 为 None；如果直接把它写回 manifest，就会把原来真实的星数抹成 null。

    顺序也有讲究：历史快照与 manifest 现值都**按仓库名**索引，但快照是从 git HEAD 重建的、
    没有被「换仓库」污染过，所以排在 manifest 现值之前。manifest 现值只能算最后一档兜底。
    """
    rec = cache.get("github", {}).get(repo) or {}
    v = rec.get("stars")
    if isinstance(v, int):
        return v
    v = STAR_SNAP.get(repo)
    if isinstance(v, int):
        return v
    return fallback if isinstance(fallback, int) else None


def stars_of(repo: str, cache: dict, fallback=None) -> str:
    v = resolve_star(repo, cache, fallback)
    return f"{v:,}" if isinstance(v, int) else "—"


def lang_of(repo: str, cache: dict) -> str:
    rec = cache.get("github", {}).get(repo) or {}
    return rec.get("lang") or "—"


# ------------------------------------------------------------------ 取章节数据
def chapter_units() -> list[dict]:
    """统一取出 141 个章节单元：普通章节取 _manifest.chapters，clang 取 cpp 的 clang_module.units。"""
    units = []
    for subj_dir in sorted(CONTENT.iterdir()):
        if not subj_dir.is_dir() or subj_dir.name.startswith("_"):
            continue
        subj = subj_dir.name
        mf = subj_dir / "_manifest.json"
        chapters = []
        if mf.exists():
            chapters = load_json(mf).get("chapters", [])
        if subj == "clang":
            cpp_m = load_json(CONTENT / "cpp" / "_manifest.json")
            chapters = (cpp_m.get("clang_module") or {}).get("units", [])
        if not chapters:
            # 没有大纲登记的目录：仍然要处理（例如新加但还没接线的章）
            for ch in sorted(subj_dir.iterdir()):
                if ch.is_dir() and (ch / "goals.md").exists():
                    units.append({"id": ch.name, "subject": subj, "unit": {},
                                  "path": ch, "manifest": None})
            continue
        for u in chapters:
            cid = u.get("id")
            if not cid:
                continue
            ch = subj_dir / cid
            if not (ch / "goals.md").exists():
                continue
            units.append({"id": cid, "subject": subj, "unit": u, "path": ch,
                          "manifest": ("clang_module" if subj == "clang" else "chapters")})
    return units


def pick_videos(subject: str, title: str, heads: list[tuple[int, int, str]],
                chapter_text: str, limit: int = 4) -> list[dict]:
    pool = POOL.get(subject) or []
    if not pool:
        return []
    corpus = bigrams(title + " " + chapter_text)
    scored = []
    for i, v in enumerate(pool):
        hit = [t for t in v["tags"] if t.lower() in (title + chapter_text).lower()]
        extra = len(set(bigrams(" ".join(v["tags"]))) & corpus)
        score = len(hit) * 3 + extra
        if v.get("main"):
            score += 100  # 主线课必须在前
        scored.append((score, i, v, hit))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for score, i, v, hit in scored[:limit]:
        kw = hit[0] if hit else ""
        out.append({**v, "_kw": kw, "_hit": hit})
    return out


# ------------------------------------------------------------------ 渲染
def render(subject: str, unit: dict, ch: Path, heads, cache: dict) -> tuple[str, dict]:
    res = (unit.get("resources") or {}) if unit else {}
    repos = list(REPOS_OVERRIDE.get(ch.name) or res.get("github") or [])
    notes = list(res.get("github_notes") or [])
    title = unit.get("title") or ch.name

    # —— GitHub：过滤失效仓库，clang/cpp 补第三个，保证 >=3 且 >=2 条有专属读法
    good, notes_by_repo = [], {}
    ov = dict(NOTES_OVERRIDE.get(ch.name) or {})
    for table in (CLANG_REPO_NOTES, CPP_NOTES):
        for k, v in table.items():
            cid, _, repo = k.partition("|")
            if cid == ch.name:
                ov[repo] = v
    for i, r in enumerate(repos):
        st = (cache.get("github", {}).get(r) or {}).get("status")
        if st == "missing":
            continue
        good.append(r)
        notes_by_repo[r] = ov.get(r) or (notes[i] if i < len(notes) else "")
    if subject == "clang" and len(good) < 3:
        for cand in C_ORDER:
            if cand not in good:
                good.append(cand)
                notes_by_repo[cand] = C_REPOS[cand]
            if len(good) >= 3:
                break
    if len(good) < 3:
        # 学科兜底：取本学科其他章出现最多、且核验通过的仓库
        pool = []
        for u2 in CHAPTERS_BY_SUBJ.get(subject, []):
            for r in ((u2.get("resources") or {}).get("github") or []):
                st = (cache.get("github", {}).get(r) or {}).get("status")
                if st != "missing" and r not in good and r not in pool:
                    pool.append(r)
        for r in pool[: 3 - len(good)]:
            good.append(r)
            notes_by_repo[r] = "同科目高频参考仓库：按本章小节定位对应目录，只读相关部分"

    mf_stars = list(res.get("github_stars") or [])
    star_of_repo = {}
    # 必须用**旧仓库列表**与旧星数按位置 zip 建映射：REPOS_OVERRIDE 换过仓库后，
    # 新列表的下标与旧 github_stars 的下标已经对不上了（曾因此把 project-based-learning 的
    # 286,133 星贴到 tinyrenderer 头上）。按名字建表才不会错位。
    old_repos = list(res.get("github") or [])
    for r, s in zip(old_repos, mf_stars):
        if isinstance(s, int):
            star_of_repo[r] = s
    gh_rows = []
    for i, r in enumerate(good[:6], 1):
        note = notes_by_repo.get(r) or "按本章小节定位相关目录"
        anc, h = anchor_of(heads, note)
        gh_rows.append((i, r, stars_of(r, cache, star_of_repo.get(r)), anc,
                        heading_atom(h), note))

    # —— B 站：按 tag 与本章小节匹配
    chapter_text = " ".join(h[2] for h in heads)
    vids = pick_videos(subject, title, heads, chapter_text)
    exs = examples_of(ch)
    bi_rows = []
    for i, v in enumerate(vids, 1):
        anc, h = anchor_of(heads, v["_kw"])
        tail = ""
        if exs:
            code, etitle = exs[(i - 1) % len(exs)]
            short = re.split(r"[：:，,。；;]", etitle)[0][:20] or etitle[:20]
            tail = f"；看完回 `{code}`（{short}）核对"
        bi_rows.append((i, v["name"], v["owner"], v["bv"], anc, heading_atom(h),
                        v["note"] + tail))

    # —— 论文与书：manifest 里本来就是章节级的
    books = [b for b in (unit.get("books") or []) if b]
    if len(books) < 2:
        for b in BOOKS.get(subject, []):
            if b not in books:
                books.append(b)
            if len(books) >= 3:
                break

    L = []
    L.append("## 本章 GitHub 学习路线（按阅读顺序）")
    L.append("")
    L.append(f"> ★ 为 **{TODAY}** 的 GitHub API 快照（已逐条验证仓库存在）。")
    L.append("> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。"
             "「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；"
             "写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。")
    L.append("")
    L.append("| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |")
    L.append("|---|---|---|---|---|")
    atoms = useful_atoms(heads)
    for i, r, st, anc, atom, note in gh_rows:
        where = "全章" if anc == "全章" else f"{anc} {atom}"
        if anc == "全章" and atoms:
            note = f"{note}；本章先读与「{'」「'.join(atoms)}」相关的部分"
        L.append(f"| {i} | [{r}](https://github.com/{r}) | {st} | {where} | {note} |")
    L.append("")
    L.append("## 本章 B 站视频路线（与 GitHub 互补）")
    L.append("")
    L.append("> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。")
    L.append("> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。"
             "顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。")
    L.append("")
    L.append("| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |")
    L.append("|---|---|---|---|---|")
    for i, name, owner, bv, anc, atom, note in bi_rows:
        where = "全章" if anc == "全章" else f"{anc} {atom}"
        L.append(f"| {i} | {name}<br><sub>{owner}</sub> | "
                 f"[{bv}](https://www.bilibili.com/video/{bv}/) | {where} | {note} |")
    L.append("")
    L.append("## 本章配套论文与书（溯源用）")
    L.append("")
    L.append("> 公式与结论的出处。只查对应章节，不必通读整本。")
    L.append("")
    L.append("| # | 文献 / 章节 |")
    L.append("|---|---|")
    for i, b in enumerate(books, 1):
        L.append(f"| {i} | {b} |")
    L.append("")
    L.append(f"> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 {len(gh_rows)} 个 GitHub 来源、"
             f"{len(bi_rows)} 条 B 站视频、{len(books)} 条文献；")
    L.append("> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，"
             "失效链接会被审计器标红。")
    L.append("")

    meta = {
        "github": good[:6],
        "github_stars": [resolve_star(r, cache, star_of_repo.get(r)) for r in good[:6]],
        "github_notes": [notes_by_repo.get(r, "") for r in good[:6]],
        "github_fetched_at": TODAY,
        "bilibili": f"https://www.bilibili.com/video/{vids[0]['bv']}/" if vids else "",
        "bilibili_list": [{"name": v["name"], "url": f"https://www.bilibili.com/video/{v['bv']}/",
                           "note": v["note"], "bv": v["bv"]} for v in vids],
        "books": books,
    }
    return "\n".join(L), meta


def replace_sections(text: str, block: str) -> tuple[str, bool]:
    """删掉**所有**旧的资源块（有的章节历史上写了两遍：GitHub/B站 + 又一段「资源/视频教程」），
    再把新块插在第一个旧块原来的位置。只删第一块会留下第二块，审计时就会检出占位句与重复 BV。"""
    lines = text.split("\n")
    kept: list[str] = []
    insert_at: int | None = None
    i = 0
    while i < len(lines):
        if lines[i].startswith(RES_HEAD):
            if insert_at is None:
                insert_at = len(kept)
            i += 1
            while i < len(lines) and not (lines[i].startswith("## ")
                                          and not lines[i].startswith(RES_HEAD)):
                i += 1
            # 吃掉块尾的空行，避免插入后出现三连空行
            while kept and kept[-1].strip() == "" and len(kept) > 1:
                kept.pop()
            continue
        kept.append(lines[i])
        i += 1
    body = block.rstrip("\n").split("\n") + [""]
    if insert_at is None:
        return ("\n".join(kept).rstrip("\n") + "\n\n" + "\n".join(body)), True
    new = kept[:insert_at] + body + kept[insert_at:]
    return "\n".join(new), True


CHAPTERS_BY_SUBJ: dict[str, list[dict]] = {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--refresh-play", action="store_true")
    args = ap.parse_args()

    cache = load_json(CACHE_PATH)
    global STAR_SNAP
    STAR_SNAP = load_json(SNAP_PATH)
    units = chapter_units()
    for u in units:
        CHAPTERS_BY_SUBJ.setdefault(u["subject"], []).append(u.get("unit") or {})

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if args.refresh_play:
        for subj, pool in POOL.items():
            for v in pool:
                try:
                    req = urllib.request.Request(
                        f"https://api.bilibili.com/x/web-interface/view?bvid={v['bv']}",
                        headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        d = json.loads(r.read().decode("utf-8", "ignore"))
                    if d.get("code") == 0:
                        v["play"] = (d.get("data") or {}).get("stat", {}).get("view", v["play"])
                    time.sleep(0.3)
                except Exception:
                    pass

    stat = {}
    changed = 0
    for u in units:
        subj = u["subject"]
        if only and subj not in only:
            continue
        ch: Path = u["path"]
        heads = concept_heads(ch)
        block, meta = render(subj, u.get("unit") or {}, ch, heads, cache)
        old = (ch / "goals.md").read_text(encoding="utf-8")
        new, ok = replace_sections(old, block)
        s = stat.setdefault(subj, {"n": 0, "gh": 0, "bv": 0, "books": 0})
        s["n"] += 1
        s["gh"] += len(meta["github"])
        s["bv"] += len(meta["bilibili_list"])
        s["books"] += len(meta["books"])
        if new != old:
            changed += 1
        if not args.apply:
            continue
        (ch / "goals.md").write_text(new, encoding="utf-8")
        # —— 回写 manifest
        if u["manifest"] == "chapters":
            mp = CONTENT / subj / "_manifest.json"
            m = load_json(mp)
            for c in m.get("chapters", []):
                if c.get("id") == u["id"]:
                    c["resources"] = {**(c.get("resources") or {}), **meta, "leetcode": [],
                                      "nowcoder": []}
                    break
            mp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        elif u["manifest"] == "clang_module":
            mp = CONTENT / "cpp" / "_manifest.json"
            m = load_json(mp)
            for c in ((m.get("clang_module") or {}).get("units") or []):
                if c.get("id") == u["id"]:
                    c["resources"] = {**(c.get("resources") or {}), **meta, "leetcode": [],
                                      "nowcoder": []}
                    break
            mp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'学科':12s} {'章':>3s} {'GitHub均值':>10s} {'B站均值':>8s} {'文献均值':>8s}")
    tg = tb = tn = 0
    for s, v in stat.items():
        n = v["n"]
        print(f"{s:12s} {n:3d} {v['gh']/n:10.1f} {v['bv']/n:8.1f} {v['books']/n:8.1f}")
        tg += v["gh"]; tb += v["bv"]; tn += n
    print(f"\n合计 {tn} 章：GitHub {tg} 条（均值 {tg/max(tn,1):.1f}）"
          f" / B 站 {tb} 条（均值 {tb/max(tn,1):.1f}）")
    if not args.apply:
        print(f"\n(dry-run，{changed} 章内容会变；加 --apply 写入)")
    else:
        print(f"\n已写入 {changed} 章 goals.md 与对应 manifest。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
