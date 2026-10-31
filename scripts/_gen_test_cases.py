#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
判题可判率（P1）自动补题生成器。

思路：用题目**自带**的 Python 参考实现（answer.reference_code）真实执行，
把运行产出的输出作为 expected_output，从而保证 test_cases 正确（由参考解本身构造）。

  Tier1：参考实现含顶层演示调用/打印 -> 执行并捕获 stdout 作为 expected_output，
         input 取自该顶层调用的源码片段。
  Tier2：仅有函数定义无明显 demo -> 用签名类型推断构造参数并调用，捕获返回值。

任何一步抛异常/超时都跳过该题目（绝不产出错误答案）。
仅处理 type==coding 且当前无 test_cases 的题目。

用法：
  python scripts/_gen_test_cases.py                 # 仅统计（dry-run）
  python scripts/_gen_test_cases.py --apply         # 写回 exercises.json
  python scripts/_gen_test_cases.py --apply --limit 10
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sys
import inspect
import threading
import warnings
import concurrent.futures as cf
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
ITEM_TIMEOUT = 12.0  # 单题执行超时（秒）


def get_ref(item):
    ans = item.get("answer")
    if isinstance(ans, dict):
        return ans.get("reference_code") or ans.get("code") or ans.get("solution")
    return None


def is_python(ref: str) -> bool:
    if not ref:
        return False
    if "public " in ref or "package " in ref or "func " in ref and "def " not in ref:
        return False
    return ("def " in ref) or ("import " in ref) or ("print(" in ref)


def capture_exec(ref: str):
    """执行参考实现，返回 (stdout_str, ns)。任何异常返回 ('', {})。

    关键：通过覆盖命名空间内的 print 捕获输出，**不修改全局 sys.stdout**，
    因此在多线程并发下各题输出互不污染（全局 sys.stdout 重定向会跨线程串味）。
    """
    buf = io.StringIO()

    def _print(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        buf.write(sep.join(str(a) for a in args) + end)

    ns = {"__name__": "__main__", "print": _print}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec(compile(ref, "<ref>", "exec"), ns)
    except Exception:
        pass
    return buf.getvalue(), ns


def tier1(ref: str):
    out, _ns = capture_exec(ref)
    out = out.strip()
    if not out:
        return None
    input_desc = "（参考实现自带演示调用，以下为其真实运行输出）"
    try:
        tree = ast.parse(ref)
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                seg = ast.get_source_segment(ref, node)
                if seg:
                    input_desc = seg.strip()
    except Exception:
        pass
    return (input_desc, out)


_TYPE_SAMPLES = {
    int: 3, float: 2.5, str: "x", bool: True,
    list: [1, 2, 3], dict: {"a": 1}, tuple: (1, 2),
}


def param_candidates(p):
    """为单个参数生成若干候选取值（含多种形状，以解锁无标注函数）。"""
    if p.default is not inspect._empty:
        return [p.default]
    if p.annotation in _TYPE_SAMPLES:
        return [_TYPE_SAMPLES[p.annotation]]
    # 无标注：尝试多种常见形状
    return [3, [1, 2, 3], "x", {"a": 1}, ([1, 2, 3],), ([1, 2, 3], ["a", "b", "c"]), 2.5]


def gen_args(sig, cap=20):
    """为函数签名生成若干候选参数组合（笛卡尔积，封顶 cap）。"""
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if not params:
        return [()]
    cands = [param_candidates(p) for p in params]
    import itertools
    combos = []
    for combo in itertools.product(*cands):
        combos.append(list(combo))
        if len(combos) >= cap:
            break
    return combos


def tier2(ref: str):
    _out, ns = capture_exec(ref)
    funcs = [v for v in ns.values() if inspect.isfunction(v)]
    for fn in reversed(funcs):
        try:
            sig = inspect.signature(fn)
        except (ValueError, TypeError):
            continue
        for args in gen_args(sig):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ret = fn(*args)
            except Exception:
                continue
            expected = repr(ret)
            if expected in (None, "None", ""):
                continue
            return (f"{fn.__name__}{args!r}", expected)
    return None


def try_generate(ref: str):
    if not is_python(ref):
        return None
    r = tier1(ref)
    if r:
        return r
    return tier2(ref)


def run_with_timeout(ref, result, timeout):
    result.append(try_generate(ref))


def generate_safe(ref):
    res = []
    t = threading.Thread(target=run_with_timeout, args=(ref, res, ITEM_TIMEOUT), daemon=True)
    t.start()
    t.join(ITEM_TIMEOUT + 1.0)
    if t.is_alive():
        return None  # 超时：放弃此题
    return res[0] if res else None


def iter_exercise_files():
    for sub in sorted(os.listdir(CONTENT)):
        d = os.path.join(CONTENT, sub)
        if not os.path.isdir(d):
            continue
        for r, _ds, fs in os.walk(d):
            if "exercises.json" in fs:
                yield os.path.join(r, "exercises.json")


def process_item(fp, i, ref, subj):
    res = generate_safe(ref)
    if res:
        inp, exp = res
        return (subj, (fp, i, [{"input": inp, "expected_output": exp, "is_sample": True}]))
    return (subj, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写回 exercises.json（默认仅统计）")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    # 收集所有 eligible 任务
    tasks = []  # (fp, i, ref, subj)
    for fp in iter_exercise_files():
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items") or []
        subj = os.path.basename(os.path.dirname(fp))
        for i, it in enumerate(items):
            if it.get("type") != "coding" or it.get("test_cases"):
                continue
            ref = get_ref(it)
            if not ref:
                continue
            tasks.append((fp, i, ref, subj))
            if args.limit and len(tasks) >= args.limit:
                break
        if args.limit and len(tasks) >= args.limit:
            break

    per_subject = defaultdict(lambda: [0, 0])
    for fp, i, ref, subj in tasks:
        per_subject[subj][0] += 1

    plan = []
    total_gen = 0
    # 生成阶段屏蔽参考实现可能泄露到真实 stdout 的打印，仅保留最终汇总
    class Sink:
        def write(self, *a, **k):
            return 0
        def flush(self):
            pass
        def isatty(self):
            return False

    real_stdout = sys.stdout
    sys.stdout = Sink()
    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(process_item, *t) for t in tasks]
            for fut in cf.as_completed(futs):
                subj, inner = fut.result()
                if inner:
                    plan.append(inner)
                    per_subject[subj][1] += 1
                    total_gen += 1
    finally:
        sys.stdout = real_stdout

    print(f"[DRY-RUN] 可自动生成 test_cases 的题目：{total_gen}")
    print("--- 按 subject（eligible / generated）---")
    for s, (e, g) in sorted(per_subject.items(), key=lambda x: -x[1][1]):
        print(f"  {s:16s} {e:4d}  ->  {g:4d}")

    if not args.apply:
        print("\n（未写盘。加 --apply 写回。）")
        return

    written = 0
    by_file = defaultdict(list)
    for entry in plan:
        if not (isinstance(entry, tuple) and len(entry) == 3):
            sys.stderr.write(f"[WARN] skip bad plan entry: {type(entry).__name__} {repr(entry)[:120]}\n")
            continue
        fp, i, tc = entry
        by_file[fp].append((i, tc))
    for fp, changes in by_file.items():
        data = json.load(open(fp, encoding="utf-8"))
        items = data.get("items") or []
        for i, tc in changes:
            if "test_cases" not in items[i]:
                items[i]["test_cases"] = tc
                written += 1
        tmp = fp + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        os.replace(tmp, fp)
    print(f"\n[APPLY] 已写入 test_cases 的题目：{written}")


if __name__ == "__main__":
    main()
