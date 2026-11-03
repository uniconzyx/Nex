#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互微游戏数据管线 · interactive.json
=====================================

把每章已有的**真实素材**转成可运行的交互模块数据，组件层只认数据、不认学科。

只读素材（绝不写）：
    exercises.json   → boss（真题选择题，题干/选项/解析原样引用）
    pitfalls.md      → match（易错点：现象 ↔ 正确写法，一对一配对）
    concept/*.md     → sequence（流程步骤排序）/ fill（代码关键标识符挖空）
    examples/*.json  → 场景文案（工作现场的实测指标）

写出：
    content/<subject>/<chapter>/interactive.json   每章一份
    viz/interactive/src/data/index.ts              章节索引（生成物）
    viz/interactive/src/data/labs/*.json           每章数据，预览台按需 import()

用法：
    python scripts/gen_interactive.py            # 全量生成
    python scripts/gen_interactive.py --check    # 只校验，不落盘
    python scripts/gen_interactive.py --only middleware/mw-ch04 -v

幂等：数据里只放素材指纹（sha1 前 10 位），不放时间戳 —— 重复跑 diff 为空。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OUT_TS = os.path.join(ROOT, "viz", "interactive", "src", "data", "index.ts")
# 手工精修的 sandbox / debug 模块。自动抽取对这两种玩法不可靠
# （"拖哪个旋钮"、"缺的是哪条语句"都是作者判断，不是正则能猜的），
# 所以数据单独放一份，生成器原样并入 interactive.json —— 重跑不会覆盖掉。
HANDMADE = os.path.join(CONTENT, "_handmade", "labs.json")

# ── 可参与 fill 的语言（sql/yaml 也算，database 章几乎全是 sql） ──
CODE_LANGS = {
    "python", "py", "cpp", "c++", "c", "java", "javascript", "js",
    "typescript", "ts", "tsx", "jsx", "go", "rust", "sql", "kotlin",
    "swift", "csharp", "cs", "php", "ruby", "scala", "yaml", "xml", "dart",
}

# ── 挖空时要避开的通用词（跨语言关键字 + 常见内建 + 常见库名） ──
STOP_TOKENS = set("""
if else elif for while do return break continue switch case default try catch finally throw
throw new class struct enum interface public private protected static const final void int long
short float double bool boolean char byte unsigned signed auto let var val fun func fn def lambda
import from export package namespace using template typename typename self this super nil null
None True False true false and or not in is as with yield async await goto sizeof typedef
print println printf cout cin cerr endl std string String list List dict Dict set Set map Map
array Array vector Vector push_back size length empty begin end main args argv argc
select from where join left right inner outer on group by order having limit offset union all
distinct insert into values update set delete create table index primary key foreign references
and or not null is like between exists in case when then else end as
redis mysql postgres sqlite django flask numpy pandas torch
TODO NOTE XXX hello world foo bar baz tmp test demo example
range sum min max len abs map filter zip enumerate sorted reversed round open input format next iter
assert pass break global nonlocal del raise except with finally lambda yield property classmethod
staticmethod isinstance hasattr getattr setattr append extend insert remove pop keys values items get
strip split join replace lower upper startswith endswith encode decode read write close seek
curl wget sudo apt npm pip git docker kubectl
""".split())

KEYWORDS_HINT = re.compile(
    r"\b(if|for|while|return|switch|Select|SELECT|INSERT|UPDATE|DELETE)\b|->|=>|==|!=|:=|\bcall\b"
)


# ═══════════════════════════════ 基础工具 ═══════════════════════════════


def read(p: str) -> str:
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def sha10(*parts: str) -> str:
    h = hashlib.sha1()
    for x in parts:
        h.update(x.encode("utf-8", "ignore"))
    return h.hexdigest()[:10]


def clip(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def clip_sentence(s: str, n: int = 110) -> str:
    """按句读截断，宁可短一句也不要出现半个词。"""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = -1
    for m in re.finditer(r"[。；;！!？?]", s[:n]):
        cut = m.end()
    if cut >= int(n * 0.5):
        return s[:cut]
    for m in re.finditer(r"[，,、]", s[:n]):
        cut = m.end()
    if cut >= int(n * 0.5):
        return s[: cut - 1] + "…"
    return s[: n - 1] + "…"


SUB_DIGIT = "₀₁₂₃₄₅₆₇₈₉"
LATEX_MAP = {
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\le": "≤", r"\leq": "≤",
    r"\ge": "≥", r"\geq": "≥", r"\neq": "≠", r"\approx": "≈", r"\oplus": "⊕",
    r"\bmod": " mod ", r"\log": " log", r"\ln": " ln", r"\max": " max",
    r"\min": " min", r"\sum": "Σ", r"\Sigma": "Σ", r"\tau": "τ", r"\Phi": "Φ",
    r"\phi": "φ", r"\alpha": "α", r"\beta": "β", r"\lambda": "λ", r"\mu": "μ",
    r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒", r"\quad": " ",
    r"\qquad": "  ", r"\ldots": "…", r"\dots": "…", r"\infty": "∞",
    r"\sigma": "σ", r"\exp": "exp", r"\top": "ᵀ", r"\|": "‖", r"\Delta": "Δ",
}


def delatex(s: str) -> str:
    """把行内 LaTeX 降级成前端能直接读的纯文本。

    InteractiveLab 的配对右栏 / 时序卡片是纯文本节点（不走 KaTeX），
    原样保留 `$\\log_2 V$` 会让 408、数学那几科整片显示 LaTeX 源码。
    """
    s = re.sub(r"\\(?:text|mathrm|operatorname|mathbf)\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", s)
    s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", s)
    for k in sorted(LATEX_MAP, key=len, reverse=True):
        # 长命令先替换，`\leq` 才不会被 `\le` 抢走；不加 lookahead，
        # 否则 `\cdotlogvar` 这种紧贴标识符的写法会漏掉
        s = s.replace(k, LATEX_MAP[k])
    s = re.sub(r"_\{([^{}]*)\}", r"_\1", s)
    s = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", s)
    # 数字下标换成 Unicode：`log_2` → `log₂`
    s = re.sub(r"_(\d)", lambda m: SUB_DIGIT[int(m.group(1))], s)
    return re.sub(r"\s+", " ", s.replace("$", "")).strip()


def strip_md(s: str) -> str:
    """去掉行内 markdown 强调/代码/链接，保留文字。

    关键：代码段与 `$...$` 公式要先「存起来」再处理，否则 `[*_]{1,2}` 会把
    `lora_B` / `node_modules` / `std::erase_if` / `$\\log_2 V$` 里的下划线一起删掉，
    前端看到的就是 `loraB`、`nodemodules`——比丢字更糟，是悄悄改写了标识符。
    """
    keep: List[str] = []

    def stash_code(m: "re.Match[str]") -> str:
        keep.append(m.group(1))
        return f"\x00{len(keep) - 1}\x00"

    def stash_tex(m: "re.Match[str]") -> str:
        keep.append(delatex(m.group(1)))
        return f"\x00{len(keep) - 1}\x00"

    s = re.sub(r"`([^`]+)`", stash_code, s)      # 行内代码：原样保留
    s = re.sub(r"\$([^$]+)\$", stash_tex, s)     # 行内公式：降级成纯文本
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    # 斜体只认成对的单个 `*`（`*怎么改*`）；孤立 `_` 多半是标识符，不碰
    s = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"\1", s)
    s = re.sub(r"(?<![\w])_([^_\s][^_]*?)_(?![\w])", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def subject_dirs() -> List[str]:
    out = []
    for d in sorted(os.listdir(CONTENT)):
        if d.startswith("_") or d.startswith("."):
            continue
        if os.path.isdir(os.path.join(CONTENT, d)):
            out.append(d)
    return out


def chapter_dirs(subject: str) -> List[str]:
    base = os.path.join(CONTENT, subject)
    return [c for c in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, c)) and not c.startswith("_")]


def chapter_title(chap_path: str, cid: str, subject: str) -> str:
    g = read(os.path.join(chap_path, "goals.md"))
    m = re.search(r"^#\s+(.+)$", g, re.M)
    if m:
        t = m.group(1)
        t = re.sub(r"^\s*(学习目标|本章目标)\s*[:：·・]\s*", "", t)
        t = re.sub(r"^\s*" + re.escape(cid) + r"\s*[·・:：]?\s*", "", t)
        t = re.sub(r"^\s*(学习目标|本章目标)\s*[:：·・]\s*", "", t)
        t = re.sub(r"\s*学习目标\s*$", "", t)
        t = t.strip(" ·-—")
        if t and len(t) >= 2:
            return t
    return cid


# ═══════════════════════════════ boss ═══════════════════════════════


def pick_options(text: str) -> str:
    """content_md 尾部常有 "A. xxx" 选项行，剥掉，只留题干。"""
    lines = text.split("\n")
    cut = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r"^\s*[A-H][.、)．]\s*\S", lines[i]):
            cut = i
        elif lines[i].strip():
            break
    return "\n".join(lines[:cut]).strip()


def build_boss(chap_path: str, limit: int = 4) -> Optional[Dict[str, Any]]:
    p = os.path.join(chap_path, "exercises.json")
    if not os.path.exists(p):
        return None
    try:
        d = json.loads(read(p))
    except json.JSONDecodeError:
        return None
    items = d.get("items", d) if isinstance(d, dict) else d
    qs: List[Dict[str, Any]] = []
    for idx, it in enumerate(items or []):
        if it.get("type") != "choice":
            continue
        opts = it.get("options") or []
        if len(opts) < 3 or not isinstance(opts[0], dict):
            continue  # 只认 {key,text}，字符串数组前端无法作答
        cor = (it.get("answer") or {}).get("correct")
        cor = [cor] if isinstance(cor, str) else list(cor or [])
        cor = [c for c in cor if c]
        if not cor:
            continue
        qs.append({
            "id": it.get("id") or f"q{idx}",
            "stem": clip(pick_options(it.get("content_md") or it.get("title", "")), 400),
            "title": clip(strip_md(it.get("title", "")), 60),
            "options": [{"key": o["key"], "text": strip_md(o.get("text", ""))} for o in opts],
            "correct": cor,
            "explain": clip(strip_md(it.get("explanation", "")), 300),
        })
        if len(qs) >= limit:
            break
    if not qs:
        return None
    return {"kind": "boss", "questions": qs}


# ═══════════════════════════════ match ═══════════════════════════════

# 易错点有三种写法，都必须认：
#   A. 同行：  1. **标题** —— 说明 + 正确写法：xxx
#   B. 列表块：1. **标题**
#                - 现象：…  - 正确做法：…
#   C. 标题块：## 1. **标题**
#                - 现象：…  - 正确做法：…
# 关键：`\*\*` 之后不能再让 \s* 吃掉换行，否则 "- 现象" 会被当成破折号分隔符，
# 结果把"现象"当成了"正解"——这是第一版最坑的 bug。
PIT_ITEM = re.compile(
    r"^(?:#{2,4}\s*)?\s*(?:\d{1,2}[.、)]|[-*])\s*\*\*(?P<title>.+?)\*\*(?P<rest>[^\n]*)$", re.M
)
# `- **现象**：` 这种是块内小标题，不是陷阱标题
PIT_SUBHEAD = re.compile(r"^(现象|根因|原因|表现|后果|正确|说明|解法|修复|影响|判据|触发)")
FIX_STRONG = (
    # 这些词本身已经指明「正确做法」，后面就算不写冒号（`正确写法 \`(a>0)&(a<5)\``）也算
    r"(?:正确(?:的)?(?:写法|做法|姿势|方式|解法|改法|用法|口径|答案|方向|顺序)"
    r"|正解|修法|怎么改|如何改|怎么避免|如何避免|改正)"
)
FIX_WEAK = r"(?:正确|应该(?:这样|是)|改为)"
FIX_RE = re.compile(
    # 语料里有三种写法：「正确写法：」「**正确做法** 是」「正确写法 `code`」
    r"(?:" + FIX_STRONG + r"\*{0,2}\s*(?:(?:是|为)\s*|[:：，]\s*|\s+)"
    # 弱标记必须带冒号/是/为，否则「正确反例」这类普通行文会被误当成正解
    r"|" + FIX_WEAK + r"\*{0,2}\s*(?:(?:是|为)\s*|[:：，]\s*))"
    r"(?P<fix>.+?)"
    # 到第一个句号就收：否则「正确做法是 X。**正确做法**：Y」会把后面加的那行一起吞掉
    r"(?=。|\n\s*(?:#{2,4}\s|[-*]\s|\d{1,2}[.、)])|\Z)",
    re.S,
)
# 后半代语料更爱用 ✅ 标正解（cpp 全家、fullstack、db-ch04…）：它本身就是「这条该怎么写」，
# 不是猜出来的，可以直接当右栏。❌ 反过来标错法，绝不能取。
CHECK_RE = re.compile(r"✅\s*(?P<fix>[^\n]+)")


def build_match(chap_path: str, limit: int = 4) -> Optional[Dict[str, Any]]:
    txt = read(os.path.join(chap_path, "pitfalls.md"))
    if not txt:
        return None
    ms = list(PIT_ITEM.finditer(txt))
    pairs = []
    for i, m in enumerate(ms):
        title = strip_md(m.group("title"))
        if len(title) < 6 or PIT_SUBHEAD.match(title):
            continue
        end = ms[i + 1].start() if i + 1 < len(ms) else len(txt)
        block = (m.group("rest") or "") + "\n" + txt[m.end():end]
        fm = FIX_RE.search(block)
        if not fm:
            fm = CHECK_RE.search(block)  # 退到 ✅ 标记
        if not fm:
            continue  # 没写正解的条目宁可不收，也不要拿「现象」冒充解法
        right = clip_sentence(strip_md(fm.group("fix")), 110)
        # 右栏是「现象描述」还是「做法」肉眼难辨，但括号不平衡一眼能看出是半句残片：
        # 「（正确是 8000×8 = 64kbps）」被从中间切开就会只剩 `8000×8 = 64kbps）。`
        if len(right) < 10:
            continue
        if right.count("）") > right.count("（") or right.count(")") > right.count("("):
            continue
        if right.startswith(("）", ")", "。", "，", "、", "；", "：")):
            continue
        pairs.append({"id": len(pairs) + 1, "left": clip(title, 46), "right": right})
        if len(pairs) >= limit:
            break
    if len(pairs) < 3:
        return None
    return {"kind": "match", "pairs": pairs,
            "tip": "左边是线上真出事的写法，右边是正确做法。一对一连上才算过。"}


# ═══════════════════════════════ sequence ═══════════════════════════════

# 时序题只认「真的有先后」的小节：步骤 / 流程 / 阶段 / 链路 / 生命周期 / 握手…
# 清单型标题（三个真相、选型、治理、要点）即使带编号也不是时序，硬做成排序题就是错的。
SEQ_HEAD = re.compile(r"步骤|流程|时序|顺序|阶段|链路|生命周期|执行流|流水线|握手|归因|诊断|推导|解析")
SEQ_BAD = re.compile(r"真相|选型|治理|要点|清单|规范|技巧|误区|对比|区别|推荐|准则|陷阱|原则|三个|四条|五条")
# 人工复核后排除：标题像时序、内容是并列要点 —— 硬做成排序题会教错
SEQ_BLOCK = {
    "cpp-ch03",                        # 「生命周期」讲悬垂引用，不是时序
    "db-ch04", "fund-ch08",            # 上线治理清单 / 流水线要点
    "agent-ch03",                      # SSE 三条解析规则
    "tool-ch05",                       # 缓存键机制说明
    "fund-ch12",                       # TLS 1.3 的三条改进
    "ai-ch10",                         # 「决策流程」实为四个并列考量
}
NUMLINE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(\d{1,2})[.、)](?:\*\*)?\s*(.+)$", re.M)


def concept_files(chap_path: str) -> List[str]:
    d = os.path.join(chap_path, "concept")
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".md")]


def build_sequence(chap_path: str, limit: int = 6) -> Optional[Dict[str, Any]]:
    if os.path.basename(chap_path) in SEQ_BLOCK:
        return None
    best: Optional[Dict[str, Any]] = None
    for cf in concept_files(chap_path):
        txt = read(cf)
        heads = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r"^#{2,3}\s*(.+)$", txt, re.M)]
        for i, (_, hend, h) in enumerate(heads):
            if not SEQ_HEAD.search(h) or SEQ_BAD.search(h):
                continue
            end = heads[i + 1][0] if i + 1 < len(heads) else len(txt)
            seg = re.sub(r"```.*?```", "", txt[hend:end], flags=re.S)
            items = [strip_md(m.group(2)) for m in NUMLINE.finditer(seg)]
            items = [x for x in items if 6 <= len(x) <= 70]
            if len(items) < 3:
                continue
            items = items[:limit]
            cand = {"kind": "sequence", "heading": clip(strip_md(h), 40),
                    "steps": [clip(x, 70) for x in items],
                    "file": os.path.basename(cf)}
            if best is None or len(cand["steps"]) > len(best["steps"]):
                best = cand
    return best


# ═══════════════════════════════ fill ═══════════════════════════════

FENCE = re.compile(r"^```([A-Za-z0-9+#.-]*)\n(.*?)^```", re.M | re.S)
IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,24}\b")


def code_blocks(txt: str) -> List[Tuple[str, List[str]]]:
    out = []
    for m in FENCE.finditer(txt):
        lang = (m.group(1) or "").lower()
        body = m.group(2)
        if lang not in CODE_LANGS:
            continue
        lines = body.rstrip("\n").split("\n")
        out.append((lang, lines))
    return out


def blank_candidates(lines: List[str]) -> List[Tuple[int, int, str]]:
    """返回 (行号, 列起点, token) —— 只在有逻辑的行上挖，且同块唯一。"""
    joined = "\n".join(lines)
    seen: Dict[str, int] = {}
    for t in IDENT.findall(joined):
        seen[t] = seen.get(t, 0) + 1
    cands = []
    for i, ln in enumerate(lines):
        if not KEYWORDS_HINT.search(ln):
            continue
        for m in IDENT.finditer(ln):
            tok = m.group(0)
            if tok in STOP_TOKENS or tok.lower() in STOP_TOKENS:
                continue
            if not tok[0].islower():      # 类名 / 枚举值 / 数据值，挖了没教学价值
                continue
            if seen.get(tok, 0) != 1:
                continue
            if len(tok) < 4:
                continue
            if re.fullmatch(r"[A-Z_]+", tok) and len(tok) < 6:  # 常数名太泛
                continue
            cands.append((i, m.start(), tok))
    # 行号分散：同一条候选行只取一个，最多 3 个，且行距 >= 1
    picked, used_rows = [], set()
    for i, col, tok in cands:
        if i in used_rows:
            continue
        used_rows.add(i)
        picked.append((i, col, tok))
        if len(picked) >= 3:
            break
    return picked


def build_fill(chap_path: str, pool: Dict[str, List[str]]) -> Optional[Dict[str, Any]]:
    blocks: List[Tuple[str, List[str], str]] = []
    for cf in concept_files(chap_path):
        for lang, lines in code_blocks(read(cf)):
            n = len([x for x in lines if x.strip()])
            if 6 <= n <= 45:
                blocks.append((lang, lines, os.path.basename(cf)))
    blocks.sort(key=lambda b: (0 if 8 <= len(b[1]) <= 26 else 1))
    for lang, lines, fname in blocks:
        picks = blank_candidates(lines)
        if len(picks) < 1:  # 单空也算一道题：只挖 1 处时它往往就是那行的关键 API
            continue
        own = set(IDENT.findall("\n".join(lines)))
        ans_lens = [len(p[2]) for p in picks]
        answers = [p[2] for p in picks]
        # 干扰项只取同语言池。额外要求：小写开头 —— 首字母大写的多是数据值（Alice / Beijing）
        # 或类名，混进来会让人一眼看出「这不是标识符」。
        full = pool.get(lang, [])
        if not full:
            continue
        # 用章节指纹做起点，让每章的干扰项不同（否则全站都是 action / alias）
        start = int(sha10(chap_path), 16) % len(full)
        cands = full[start:] + full[:start]
        distractors: List[str] = []
        for t in cands:
            if t in own or t in STOP_TOKENS or len(t) < 4:
                continue
            if not t[0].islower():
                continue
            if re.fullmatch(r"[a-z0-9_]+", t) is None:  # 混了奇怪字符
                continue
            if any(t in a or a in t for a in answers):  # dept / dept_id 这种一眼像的不要
                continue
            if min(abs(len(t) - L) for L in ans_lens) > 5:
                continue
            if t not in distractors:
                distractors.append(t)
            if len(distractors) >= 2:
                break
        if len(distractors) < 2:
            continue
        # 用占位符替换，占位符必须在原文不出现
        marker = "\u2039{}\u203A"  # ‹1›
        render = list(lines)
        blanks = []
        for k, (i, col, tok) in enumerate(picks):
            render[i] = render[i].replace(tok, marker.format(k + 1), 1)
            blanks.append({"id": f"b{k+1}", "answer": tok, "line": i + 1})
        code = "\n".join(render)
        return {"kind": "fill", "lang": lang, "file": fname, "code": code,
                "marker": marker.format("%n"), "blanks": blanks,
                "distractors": distractors,
                "tip": "把缺失的标识符拖回代码里的空位 —— 位置对、词对才算补回来。"}
    return None


# ═══════════════════════════════ 场景文案 ═══════════════════════════════


def build_scenario(chap_path: str, cid: str, boss: Optional[Dict[str, Any]],
                   match: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    work = ""
    ex_dir = os.path.join(chap_path, "examples")
    if os.path.isdir(ex_dir):
        for f in sorted(os.listdir(ex_dir)):
            if not f.endswith(".json"):
                continue
            try:
                d = json.loads(read(os.path.join(ex_dir, f)))
                t = d.get("title") if isinstance(d, dict) else None
                if t:
                    work = clip(strip_md(t), 42)
                    break
            except json.JSONDecodeError:
                continue
    work_sub = match["pairs"][0]["left"] if match else (boss["questions"][0]["title"] if boss else "")
    exam = boss["questions"][0]["title"] if boss else ""
    return {
        "work": {"tag": "工作现场", "head": clip(work or work_sub, 44),
                 "body": clip(work_sub, 56) if work else ""},
        "exam": {"tag": "考场视角", "head": clip(exam or work_sub, 44),
                 "body": clip(f"{cid} · 本章真题口径", 56)},
    }


# ═══════════════════════════════ 组装 ═══════════════════════════════


def collect_pool() -> Dict[str, List[str]]:
    """
    全局 token 池（当干扰项），按代码语言分桶。

    只留「跨章节通用」的词（document frequency >= 3）：`abar`、`abc123` 这类
    只出现在单章里的临时变量/测试串会被滤掉，剩下的才是 status / stdout / sorted
    这种真 API 名 —— 干扰项才骗得到人。
    """
    by_lang: Dict[str, Dict[str, int]] = {}   # lang -> token -> 出现章节数
    for s in subject_dirs():
        for c in chapter_dirs(s):
            per_lang: Dict[str, set] = {}
            for cf in concept_files(os.path.join(CONTENT, s, c)):
                for lang, lines in code_blocks(read(cf)):
                    per_lang.setdefault(lang, set()).update(IDENT.findall("\n".join(lines)))
            for lang, toks in per_lang.items():
                bucket = by_lang.setdefault(lang, {})
                for t in toks:
                    if t in STOP_TOKENS or len(t) < 4 or not t[0].islower():
                        continue
                    if re.fullmatch(r"[a-z0-9_]+", t) is None:
                        continue
                    bucket[t] = bucket.get(t, 0) + 1
    return {lang: sorted(t for t, df in bucket.items() if df >= 3)
            for lang, bucket in by_lang.items()}


def load_handmade() -> Dict[str, List[Dict[str, Any]]]:
    """读手工精修模块表：{"cpp/cpp-ch18": [ {kind: sandbox, …} ]}"""
    if not os.path.exists(HANDMADE):
        return {}
    try:
        d = json.loads(read(HANDMADE))
    except json.JSONDecodeError as e:
        print(f"!! {HANDMADE} 解析失败：{e}")
        return {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for k, v in (d.get("chapters") or {}).items():
        if isinstance(v, list) and v:
            out[k] = v
    return out


def build_chapter(subject: str, cid: str, pool: Dict[str, List[str]],
                  handmade: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                  verbose: bool = False) -> Optional[Dict[str, Any]]:
    chap_path = os.path.join(CONTENT, subject, cid)
    title = chapter_title(chap_path, cid, subject)
    boss = build_boss(chap_path)
    match = build_match(chap_path)
    seq = build_sequence(chap_path)
    fill = build_fill(chap_path, pool)
    auto = [m for m in (seq, match, boss, fill) if m]
    # 精修模块排在最前：它是本章最值得玩的一个，页签默认就落在它上面
    hand = list((handmade or {}).get(f"{subject}/{cid}") or [])
    hand_kinds = {m.get("kind") for m in hand}
    modules = hand + [m for m in auto if m["kind"] not in hand_kinds]
    if not modules:
        return None
    sc = build_scenario(chap_path, cid, boss, match)
    fp_src = "".join(read(os.path.join(chap_path, f)) for f in
                     ("exercises.json", "pitfalls.md")) + "".join(
        read(p) for p in concept_files(chap_path))
    # 指纹只喂"这一章真的用了精修模块"的内容：没精修时喂一个空串，
    # 否则 122 章无关章节的指纹会一起变（前端 seed 跟着变，洗牌顺序全乱）
    if hand:
        fp_src += json.dumps(hand, ensure_ascii=False)
    data = {
        "chapter": cid,
        "subject": subject,
        "title": title,
        "fingerprint": sha10(fp_src),
        "scenario": sc,
        "modules": modules,
    }
    if verbose:
        print(f"  {subject}/{cid:<12} {title[:20]:<22} "
              f"{' '.join(m['kind'] for m in modules)}")
    return data


TS_HEAD = """/* 自动生成 · 请勿手改 —— python scripts/gen_interactive.py */
/**
 * 章节目录（轻量索引，约 25KB）。
 * 正文数据在 ./labs/<subject>__<chapter>.json，由预览台按需 import()，
 * 所以首页不会因为 165 章的数据把 bundle 撑到 700KB。
 */

export interface LabIndexItem {
  key: string;
  subject: string;
  title: string;
  kinds: string[];
  fingerprint: string;
}

export const LAB_INDEX: LabIndexItem[] = ["""


def write_ts(all_labs: Dict[str, Dict[str, Any]], check: bool) -> None:
    if check:
        return
    os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
    labs_dir = os.path.join(os.path.dirname(OUT_TS), "labs")
    os.makedirs(labs_dir, exist_ok=True)

    # ① 每章一份独立 JSON —— 交给 import.meta.glob 懒加载
    keep = set()
    for key, d in all_labs.items():
        fname = key.replace("/", "__") + ".json"
        keep.add(fname)
        with open(os.path.join(labs_dir, fname), "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
    # 清掉素材已消失的旧文件，避免 glob 里留孤儿
    for f in os.listdir(labs_dir):
        if f not in keep:
            os.remove(os.path.join(labs_dir, f))

    # ② 轻量索引
    lines = [TS_HEAD]
    for k in sorted(all_labs):
        d = all_labs[k]
        kinds = sorted({m["kind"] for m in d["modules"]})
        lines.append(
            "  { key: %s, subject: %s, title: %s, kinds: %s, fingerprint: %s },"
            % (
                json.dumps(k, ensure_ascii=False),
                json.dumps(d["subject"], ensure_ascii=False),
                json.dumps(d["title"], ensure_ascii=False),
                json.dumps(kinds, ensure_ascii=False),
                json.dumps(d["fingerprint"], ensure_ascii=False),
            )
        )
    lines.append("];")
    lines.append("")
    lines.append("export const LAB_KEYS = LAB_INDEX.map((x) => x.key).sort();")
    lines.append("")
    lines.append("export const LAB_SUBJECTS: Record<string, string> = Object.fromEntries(")
    lines.append("  LAB_INDEX.map((x) => [x.key, x.subject]),")
    lines.append(");")
    lines.append("")
    with open(OUT_TS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只统计不落盘")
    ap.add_argument("--only", default="", help="subject/chapter 或 subject 前缀")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    print("· 收集干扰项 token 池 …")
    pool = collect_pool()
    print(f"  池大小 {len(pool)}")
    handmade = load_handmade()
    print(f"· 手工精修 {sum(len(v) for v in handmade.values())} 个模块 / {len(handmade)} 章")
    unknown = [k for k in handmade if not os.path.isdir(os.path.join(CONTENT, k))]
    if unknown:
        print("  !! 精修表里指向不存在的章节:", ", ".join(unknown))

    all_labs: Dict[str, Dict[str, Any]] = {}
    stat: Dict[str, int] = {}
    missing: List[str] = []
    for s in subject_dirs():
        if args.only and not (s == args.only or s.startswith(args.only + "/")):
            continue
        for c in chapter_dirs(s):
            key = f"{s}/{c}"
            if "/" in args.only and key != args.only:
                continue
            d = build_chapter(s, c, pool, handmade, args.verbose)
            if d is None:
                missing.append(key)
                continue
            all_labs[key] = d
            for m in d["modules"]:
                stat[m["kind"]] = stat.get(m["kind"], 0) + 1

    print(f"\n· 章节 {len(all_labs)} 有数据 / {len(missing)} 无 → 模块统计 {stat}")
    if missing:
        print("  无模块章节:", ", ".join(missing[:12]), "…" if len(missing) > 12 else "")
    total = sum(stat.values())
    print(f"  模块总数 {total}，平均 {total / max(len(all_labs), 1):.2f} / 章")

    if not args.check:
        # 每章落 interactive.json
        for key, d in all_labs.items():
            s, c = key.split("/")
            p = os.path.join(CONTENT, s, c, "interactive.json")
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
                f.write("\n")
        write_ts(all_labs, args.check)
        print(f"· 已写 {len(all_labs)} 份 interactive.json + {os.path.relpath(OUT_TS, ROOT)}")
    else:
        for key in list(all_labs)[:5]:
            print("  sample", key, [m["kind"] for m in all_labs[key]["modules"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
