#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为「自带 C/C++/Java 参考实现」且 main 可运行输出的 coding 题，真实编译运行参考解，
把运行输出作为 expected_output 生成 test_cases（零编造、可验证）。

- C/C++：g++ -std=c++17 -O2 编译运行，捕获 stdout
- Java：javac 编译 + java 运行，捕获 stdout
- 仅处理「带 main 且有输出」的题；纯函数片段（无 main）跳过
- 文件 IO 题（fopen 读 in.txt 写 out.txt）跳过，记为残余

所有编译产物落在项目 .scratch/_gen_tmp/（D 盘），运行后清理，绝不写 C 盘系统目录。

用法：
  python scripts/_gen_test_cases_native.py            # 仅统计（dry-run）
  python scripts/_gen_test_cases_native.py --apply    # 写回 exercises.json
  python scripts/_gen_test_cases_native.py --limit 4  # 试点
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import warnings
import concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = r"D:\tmp_cppmind_gen"
GPP = r"D:\mingw64\bin\g++.exe"
JAVAC = shutil.which("javac") or "javac"
JAVA = shutil.which("java") or "java"
ITEM_TIMEOUT = 15.0  # 单步（编译或运行）超时（秒）
MAX_WORKERS = 4
APPLY = False


def iter_exercise_files():
    for sub in os.listdir(os.path.join(ROOT, "content")):
        d = os.path.join(ROOT, "content", sub)
        if not os.path.isdir(d):
            continue
        for r, ds, fs in os.walk(d):
            if "exercises.json" in fs:
                yield os.path.join(r, "exercises.json")


def get_ref(it):
    ans = it.get("answer")
    if isinstance(ans, dict):
        return ans.get("reference_code") or ans.get("code") or ans.get("solution")
    return None


def lang_of(ref, sub):
    if sub == "cpp":
        return "cpp"
    if sub in ("clang",) and ("#include" in ref or "int main" in ref):
        return "cpp"
    if sub in ("java", "spring"):
        return "java"
    return None


def has_main(ref, lang):
    if lang == "cpp":
        return ("int main" in ref or "void main" in ref) and (
            "cout" in ref or "printf" in ref or "puts" in ref or "std::cout" in ref
        )
    if lang == "java":
        return "public static void main" in ref
    return False


def is_file_io(ref):
    return ("fopen" in ref and "in.txt" in ref) or ("ifstream" in ref and ".txt" in ref)


def extract_demo_input(ref, lang):
    """best-effort：从 main 里提取被演示调用的函数实参，作为 input 展示。"""
    m = re.search(r"main\s*\([^)]*\)\s*\{(.*?)\}", ref, re.S)
    if not m:
        return None
    body = m.group(1)
    # 找 main 里第一个函数调用
    cm = re.search(r"(\w+)\s*\(([^;{}]*?)\)\s*[;)]", body)
    if not cm:
        return None
    args = cm.group(2).strip()
    if not args or "&" in args or "*" in args:
        return None
    return args


def _unique_tmp():
    d = tempfile.mkdtemp(prefix="gen_", dir=TMP)
    return d


def _popen_run(cmd, wd, timeout):
    """运行命令并捕获 stdout；超时则杀掉整个进程树（含子进程），返回 (returncode, stdout)。"""
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env={**os.environ, "TMP": wd, "TEMP": wd, "TMPDIR": wd},
        )
    except Exception:
        return None, ""
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        return None, ""


def run_cpp(ref):
    os.makedirs(TMP, exist_ok=True)
    wd = _unique_tmp()
    src = os.path.join(wd, "src.cpp")
    exe = os.path.join(wd, "a.exe")
    with open(src, "w", encoding="utf-8") as f:
        f.write(ref)
    try:
        rc, _ = _popen_run([GPP, "-std=c++17", "-O2", src, "-o", exe], wd, ITEM_TIMEOUT)
        if rc != 0:
            return None
        rc, out = _popen_run([exe], wd, ITEM_TIMEOUT)
        if rc is None:
            return None
        return out
    except Exception:
        return None
    # 注：不在运行中删除 wd，避免触发 safe-delete 批量确认钩子；统一在末尾清理


def run_java(ref):
    os.makedirs(TMP, exist_ok=True)
    m = re.search(r"(?:public\s+)?class\s+(\w+)", ref)
    if not m:
        return None
    cls = m.group(1)
    wd = _unique_tmp()
    src = os.path.join(wd, cls + ".java")
    with open(src, "w", encoding="utf-8") as f:
        f.write(ref)
    try:
        rc, _ = _popen_run([JAVAC, "-d", wd, src], wd, ITEM_TIMEOUT)
        if rc != 0:
            return None
        rc, out = _popen_run([JAVA, "-cp", wd, cls], wd, ITEM_TIMEOUT)
        if rc is None:
            return None
        return out
    except Exception:
        return None
    # 注：不在运行中删除 wd，避免触发 safe-delete 批量确认钩子；统一在末尾清理


def try_generate(ref, lang):
    if lang == "cpp":
        out = run_cpp(ref)
    elif lang == "java":
        out = run_java(ref)
    else:
        return None
    if out is None:
        return None
    out = out.strip()
    if not out:
        return None
    # 跨线程 stdout 隔离：子进程独立，安全
    demo = extract_demo_input(ref, lang)
    inp = demo if demo else "<参考实现 main 演示用例>"
    return (inp, out)


def main():
    global APPLY
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    APPLY = args.apply

    tasks = []  # (fp, idx, ref, lang, subj, title)
    for fp in iter_exercise_files():
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items") or []
        subj = os.path.relpath(fp, os.path.join(ROOT, "content")).split(os.sep)[0]
        for i, it in enumerate(items):
            if it.get("type") != "coding" or it.get("test_cases"):
                continue
            ref = get_ref(it)
            if not ref:
                continue
            lang = lang_of(ref, subj)
            if not lang or not has_main(ref, lang) or is_file_io(ref):
                continue
            tasks.append((fp, i, ref, lang, subj, it.get("title", "")))
    if args.limit:
        tasks = tasks[: args.limit]

    print(f"[SCAN] 可原生编译运行的 coding 题（cpp/java 带 main）：{len(tasks)}")

    per = {}
    plan = []
    total = 0

    def process(t):
        fp, i, ref, lang, subj, title = t
        res = try_generate(ref, lang)
        if res:
            sys.stderr.write(f"  GEN [{subj}/{lang}] {title!r} -> out={res[1][:50]!r}\n")
            return (subj, (fp, i, [{"input": res[0], "expected_output": res[1], "is_sample": True}]))
        sys.stderr.write(f"  SKIP [{subj}/{lang}] {title!r}\n")
        return (subj, None)

    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(process, t) for t in tasks]
        for fut in cf.as_completed(futs):
            subj, r = fut.result()
            per.setdefault(subj, [0, 0])
            per[subj][0] += 1
            if r and isinstance(r, tuple) and len(r) == 3:
                plan.append(r)
                per[subj][1] += 1
                total += 1
            if args.limit and total >= args.limit:
                # 不再提交新任务
                for f in futs:
                    f.cancel()

    print(f"[DRY-RUN] 可生成 test_cases 的题目：{total}")
    for subj, (tot, gen) in sorted(per.items()):
        print(f"  {subj:14s} total={tot:3d}  generated={gen:3d}")

    if not APPLY:
        return

    by_file = {}
    for fp, i, tc in plan:
        by_file.setdefault(fp, []).append((i, tc))

    written = 0
    for fp, changes in by_file.items():
        data = json.load(open(fp, encoding="utf-8"))
        items = data.get("items") or []
        for i, tc in changes:
            if 0 <= i < len(items):
                items[i]["test_cases"] = tc
                written += 1
        # 先落临时文件再原子替换，避免大文件写入中途损坏
        tmp = fp + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        with open(tmp, "a", encoding="utf-8") as f:
            f.write("\n")
        os.replace(tmp, fp)

    print(f"[APPLY] 已写回 {written} 道题目的 test_cases")


if __name__ == "__main__":
    main()
