#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手工精修模块守门 · content/_handmade/labs.json
================================================

两件事，任一不过就 exit 1：

1. 结构合规
   sandbox: 参数区间合法、指标公式可求值、checks 非空
   debug  : code 里的占位符个数 == slots 个数；每个槽位恰好一块能补上；
            块 id 不重复；expect / pass 不能空

2. 可通关
   sandbox 的 checks 是 `expr`，写错一个括号、调错一个函数名，前端就是一排
   ✗ 且永远不可能变 ✓——玩家拖到手抽筋也不知道是数据错了。
   这里把参数区间按 step 穷举，确认至少有一组参数让所有 checks 为真；
   同时确认默认值**不是**开局就通关（否则模块一进来就"通过"，等于没玩）。

公式求值器与 `viz/interactive/lab/expr.ts` 同文法（数字/标识符/四则/幂/
比较/逻辑/三元/12 个纯函数），两边必须同步改。Python 侧只用于校验，
不参与产出，所以宁可写得笨一点。

用法：
    python scripts/audit_handmade_labs.py
    python scripts/audit_handmade_labs.py -v      # 打印每章的默认值/解
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDMADE = os.path.join(ROOT, "content", "_handmade", "labs.json")
CONTENT = os.path.join(ROOT, "content")

# ══════════════════════════ 公式求值（同 expr.ts） ══════════════════════════

FN = {
    "min": lambda a, b: min(a, b),
    "max": lambda a, b: max(a, b),
    "abs": lambda a: abs(a),
    "ceil": lambda a: math.ceil(a),
    "floor": lambda a: math.floor(a),
    "round": lambda a: round(a),
    "sqrt": lambda a: math.sqrt(a),
    "pow": lambda a, b: a ** b,
    "log": lambda a: math.log(a),
    "ln": lambda a: math.log(a),
    "log2": lambda a: math.log2(a),
    "log10": lambda a: math.log10(a),
    "exp": lambda a: math.exp(a),
    "clamp": lambda x, a, b: min(b, max(a, x)),
    "if": lambda c, a, b: a if c else b,
}

TOK = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|>=|<=|==|!=|&&|\|\||[-+*/%^<>!?:(),]))")


class ExprError(Exception):
    pass


def lex(src: str) -> List[str]:
    out, i = [], 0
    while i < len(src):
        m = TOK.match(src, i)
        if not m or m.end() == i:
            if src[i:].strip() == "":
                break
            raise ExprError(f"不认识的字符 {src[i]!r}")
        out.append(m.group(1) or m.group(2) or m.group(3))
        i = m.end()
    return out


def ev(src: str, vars: Dict[str, float]) -> float:  # noqa: A002
    tk, p = lex(src), 0

    def peek() -> Optional[str]:
        return tk[p] if p < len(tk) else None

    def eat(t: Optional[str] = None) -> str:
        nonlocal p
        if t is not None and peek() != t:
            raise ExprError(f"期望 {t}，实际 {peek() or 'EOF'}")
        if p >= len(tk):
            raise ExprError("公式意外结束")
        p += 1
        return tk[p - 1]

    def unary() -> float:
        if peek() == "-":
            eat()
            return -unary()
        if peek() == "+":
            eat()
            return unary()
        if peek() == "!":
            eat()
            return 0.0 if unary() else 1.0
        return power()

    def power() -> float:
        base = primary()
        if peek() in ("^", "**"):
            eat()
            return base ** unary()
        return base

    def primary() -> float:
        t = peek()
        if t is None:
            raise ExprError("公式意外结束")
        if t == "(":
            eat("(")
            v = ternary()
            eat(")")
            return v
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            eat()
            return float(t)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t):
            eat()
            if peek() == "(":
                eat("(")
                args = []
                if peek() != ")":
                    args.append(ternary())
                    while peek() == ",":
                        eat(",")
                        args.append(ternary())
                eat(")")
                if t not in FN:
                    raise ExprError(f"不认识函数 {t}")
                return float(FN[t](*args))
            if t not in vars:
                raise ExprError(f"未定义的量 {t}")
            return float(vars[t])
        raise ExprError(f"不认识的符号 {t}")

    def mul() -> float:
        v = unary()
        while peek() in ("*", "/", "%"):
            op = eat()
            r = unary()
            if op == "/" and r == 0:
                raise ZeroDivisionError
            v = v * r if op == "*" else (v / r if op == "/" else math.fmod(v, r))
        return v

    def add() -> float:
        v = mul()
        while peek() in ("+", "-"):
            op = eat()
            r = mul()
            v = v + r if op == "+" else v - r
        return v

    def cmp() -> float:
        v = add()
        while peek() in ("<", ">", "<=", ">=", "==", "!="):
            op = eat()
            r = add()
            v = float({
                "<": v < r, ">": v > r, "<=": v <= r, ">=": v >= r,
                "==": v == r, "!=": v != r,
            }[op])
        return v

    def conj() -> float:
        v = cmp()
        while peek() == "&&":
            eat()
            # 必须先把右边解析完再合并：写成 `v and cmp()` 会短路，
            # 右边没被消费，解析器就卡在下一个 token 上（实测报"期望 )"）
            r = cmp()
            v = 1.0 if (v and r) else 0.0
        return v

    def disj() -> float:
        v = conj()
        while peek() == "||":
            eat()
            r = conj()
            v = 1.0 if (v or r) else 0.0
        return v

    def ternary() -> float:
        c = disj()
        if peek() == "?":
            eat("?")
            a = ternary()
            eat(":")
            b = ternary()
            return a if c else b
        return c

    v = ternary()
    if p != len(tk):
        raise ExprError(f"尾部多余内容 {' '.join(tk[p:])}")
    return v


# ══════════════════════════════ 校验 ══════════════════════════════

SANDBOX_KEYS = ("kind", "title", "brief", "params", "metrics", "checks", "insight")
DEBUG_KEYS = ("kind", "title", "lang", "symptom", "code", "marker", "slots", "blocks", "expect", "pass")


def grid(p: Dict[str, Any]) -> List[float]:
    lo, hi, st = float(p["min"]), float(p["max"]), float(p["step"])
    if st <= 0 or hi < lo:
        raise ValueError(f"参数 {p['key']} 区间非法：{lo}..{hi} step {st}")
    n = int(round((hi - lo) / st))
    if n > 5000:
        raise ValueError(f"参数 {p['key']} 档位 {n+1} 太多（>5000）")
    return [lo + i * st for i in range(n + 1)]


MAX_COMBOS = 20000


def sample_axes(axes: List[List[float]]) -> Tuple[List[List[float]], bool]:
    """参数组合可能爆炸（4 个旋钮各 100 档就是 1 亿组）。

    按"点最多的那个轴减半"逐轮抽样，直到 ≤ MAX_COMBOS。抽样不是穷举，
    所以只用来回答"有没有解"，不保证找到全部解 —— 报告里会标明是否抽样。

    **必须保留首尾端点**：截断式 `[::2]` 会把 `rows=4000` 这种「偶数下标靠后」的
    档位抽掉，于是 `rows == 4000` 这类锁定判据永远不成立，误报"这一关不可能通关"。
    端点又恰好是最常见的解（默认值、上下界），丢了它们等于丢掉了大半可行域。
    """
    cur = [list(a) for a in axes]
    sampled = False
    while math.prod(len(a) for a in cur) > MAX_COMBOS:
        i = max(range(len(cur)), key=lambda k: len(cur[k]))
        if len(cur[i]) <= 2:
            break
        cur[i] = cur[i][::2]
        # 补回被抽掉的末端点——它是边界解所在处，不能丢
        if cur[i][-1] != axes[i][-1]:
            cur[i].append(axes[i][-1])
        sampled = True
    return cur, sampled


def run_sandbox(ch: str, mod: Dict[str, Any], verbose: bool) -> Tuple[List[str], List[str]]:
    errs: List[str] = []
    notes: List[str] = []
    for k in SANDBOX_KEYS:
        if k not in mod:
            errs.append(f"缺字段 {k}")
    if errs:
        return errs, notes
    keys = [p["key"] for p in mod["params"]]
    if len(set(keys)) != len(keys):
        errs.append("参数 key 重复")
    axes = []
    for p in mod["params"]:
        try:
            axes.append(grid(p))
        except ValueError as e:
            errs.append(str(e))
    if errs:
        return errs, notes

    def metrics_of(vals: Dict[str, float]) -> Tuple[Dict[str, float], Optional[str]]:
        env = dict(vals)
        for m in mod["metrics"]:
            try:
                env[m["key"]] = ev(m["expr"], env)
            except (ExprError, ZeroDivisionError, ValueError) as e:
                return env, f"指标 {m['key']} 求值失败：{e}"
        return env, None

    def ok_of(env: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        for c in mod["checks"]:
            try:
                if ev(c["expr"], env) == 0:
                    return False, None
            except (ExprError, ZeroDivisionError, ValueError) as e:
                return False, f"判据求值失败：{e}"
        return True, None

    # 默认值不能开局通关
    default = {p["key"]: float(p["value"]) for p in mod["params"]}
    for p in mod["params"]:
        if not (float(p["min"]) <= float(p["value"]) <= float(p["max"])):
            errs.append(f"参数 {p['key']} 的 value={p['value']} 不在区间内")
    denv, derr = metrics_of(default)
    if derr:
        errs.append(f"默认参数下 {derr}")
    else:
        dok, dcerr = ok_of(denv)
        if dcerr:
            errs.append(f"默认参数下 {dcerr}")
        elif dok:
            errs.append("默认参数已经满足全部判据 —— 一进来就通关，等于没得玩")

    # 穷举（或抽样）找解
    # 先把被 `key == 常数` 锁死的轴钉成一个点：这类「既定事实」判据本来就要求
    # 精确命中，而 sample_axes 的隔位抽样极易把它抽掉（rows==4000、cores==8…），
    # 会误报「这一关不可能通关」。锁死后搜索空间也更小，解更稳定。
    for i, p in enumerate(mod["params"]):
        m = re.search(rf"\b{re.escape(p['key'])}\s*==\s*([0-9]+(?:\.[0-9]+)?)\b",
                      " ".join(c["expr"] for c in mod["checks"]))
        if m:
            lock = float(m.group(1))
            if lock in axes[i]:
                axes[i] = [lock]
            else:
                # 锁定的值不在网格上（如 min=16 step=16 时网格是 16,32,…,192,208，
                # 永远取不到 200）→ 这条判据恒假，必须明确报出来，
                # 否则结论会伪装成「不可能通关」，让人去查公式而不是查档位。
                errs.append(
                    f"判据要求 {p['key']} == {lock:g}，但参数网格 "
                    f"({p['min']}~{p['max']} step {p['step']}) 取不到该值")
    axes, sampled = sample_axes(axes)
    sol: Optional[Dict[str, float]] = None
    for combo in itertools.product(*axes):
        vals = dict(zip(keys, combo))
        env, e = metrics_of(vals)
        if e:
            errs.append(e)
            break
        ok, ce = ok_of(env)
        if ce:
            errs.append(ce)
            break
        if ok and sol is None:
            sol = vals
    else:
        if sol is None:
            errs.append("穷举完所有参数组合都没有通过判据的解 —— 这一关不可能通关")
        else:
            notes.append(("抽样解：" if sampled else "解：") + ", ".join(f"{k}={v:g}" for k, v in sol.items()))

    if verbose:
        mets = " ".join(f"{m['key']}={denv.get(m['key'], float('nan')):.4g}" for m in mod["metrics"])
        notes.insert(0, f"默认 {mets}")
    return errs, notes


def run_debug(ch: str, mod: Dict[str, Any], verbose: bool) -> Tuple[List[str], List[str]]:
    errs: List[str] = []
    notes: List[str] = []
    for k in DEBUG_KEYS:
        if k not in mod:
            errs.append(f"缺字段 {k}")
    if errs:
        return errs, notes

    slots = [s["id"] for s in mod["slots"]]
    if len(set(slots)) != len(slots):
        errs.append("槽位 id 重复")
    ids = [b["id"] for b in mod["blocks"]]
    if len(set(ids)) != len(ids):
        errs.append("块 id 重复")

    # 占位符个数必须与槽位数一致，否则空位渲染不出来 / 多出来的块永远补不上
    mark = mod["marker"]
    at = mark.index("%n")
    pat = re.compile(re.escape(mark[:at]) + r"(\d+)" + re.escape(mark[at + 2:]))
    nums = [int(x) for x in pat.findall(mod["code"])]
    if sorted(nums) != list(range(1, len(slots) + 1)):
        errs.append(f"代码里的占位符 {sorted(nums)} 与槽位数 {len(slots)} 不匹配")

    for s in slots:
        hits = [b for b in mod["blocks"] if b.get("for") == s]
        if len(hits) != 1:
            errs.append(f"槽位 {s} 有 {len(hits)} 块能补上（必须恰好 1 块）")
    for b in mod["blocks"]:
        # 干扰块故意不带 for（for 为空串），它不是"补到别处"，而是"哪都补不上"
        if b.get("for") and b["for"] not in slots:
            errs.append(f"块 {b['id']} 的 for={b.get('for')} 不是任何槽位")
    correct_ids = {b["id"] for b in mod["blocks"] if b.get("for")}
    no_why = [b["id"] for b in mod["blocks"] if b["id"] not in correct_ids and not b.get("why")]
    if no_why:
        errs.append(f"干扰块缺 why：{no_why}")
    if len(mod["blocks"]) <= len(slots):
        errs.append("没有干扰块 —— 拼装题至少要有一块错的才需要判断")
    for k in ("expect", "pass", "symptom"):
        if not str(mod.get(k, "")).strip():
            errs.append(f"{k} 为空")
    if verbose:
        notes.append(f"{len(slots)} 空 / {len(mod['blocks'])} 块")
    return errs, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(HANDMADE):
        print(f"!! 没有 {HANDMADE}")
        return 1
    data = json.loads(open(HANDMADE, encoding="utf-8").read())
    chapters: Dict[str, List[Dict[str, Any]]] = data.get("chapters") or {}

    total = bad = 0
    stat: Dict[str, int] = {}
    for key in sorted(chapters):
        subj, _, cid = key.partition("/")
        chap_dir = os.path.join(CONTENT, subj, cid)
        if not os.path.isdir(chap_dir):
            print(f"✗ {key}: 章节目录不存在")
            bad += 1
            continue
        for mod in chapters[key]:
            total += 1
            kind = mod.get("kind")
            stat[kind] = stat.get(kind, 0) + 1
            if kind == "sandbox":
                errs, notes = run_sandbox(key, mod, args.verbose)
            elif kind == "debug":
                errs, notes = run_debug(key, mod, args.verbose)
            else:
                errs, notes = [f"不认识的 kind={kind}"], []
            if errs:
                bad += 1
                print(f"✗ {key} · {mod.get('title', '?')}")
                for e in errs:
                    print(f"    - {e}")
            elif args.verbose:
                print(f"✓ {key} · {mod.get('title', '?')}" + ("  |  " + " ; ".join(notes) if notes else ""))

    print(f"\n{total - bad}/{total} 模块通过 · {stat} · {len(chapters)} 章")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
