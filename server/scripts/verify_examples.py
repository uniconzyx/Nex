"""真实回放校验：把 examples/*.json 里的代码重新编译运行，与 expected_output 比对。

与 validate_content.py 的「输出健康度」不同，本脚本是**真执行**：
能抓住「expected_output 是编造的」「编译器报错被当成输出」「示例根本跑不通」三类问题。

用法：
    python server/scripts/verify_examples.py                 # 全量
    python server/scripts/verify_examples.py --chapter fund-ch05
    python server/scripts/verify_examples.py --subject fundamentals
    python server/scripts/verify_examples.py --json          # 机器可读汇总

比对口径（宽松但有效）：
    expected_output 去掉以 `$` 开头的「命令回显行」与空行后，剩余「实质输出行」
    必须按顺序出现在真实 stdout 中。实际输出允许有额外行（如编译进度）。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"

GCC = "D:/mingw64/bin/gcc.exe"
GXX = "D:/mingw64/bin/g++.exe"
PY_VENV = pathlib.Path(
    "C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/.workbuddy/pyenv-cppmind/Scripts/python.exe"
)
SYS_PY = "C:/Users/zyx/.workbuddy/binaries/python/versions/3.13.12/python.exe"
NODE = "C:/Users/zyx/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"

TIMEOUT = 60


def _py() -> str:
    return str(PY_VENV) if PY_VENV.exists() else SYS_PY


def _run(argv, cwd, stdin_text, timeout=TIMEOUT):
    """返回 (rc, stdout+stderr 合并文本)。"""
    try:
        p = subprocess.run(
            argv,
            cwd=str(cwd),
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"<超时 {timeout}s>"
    except FileNotFoundError as e:
        return 127, f"<找不到可执行文件: {argv[0]}> {e}"


def _std_flag(lang: str, code_std: str) -> str:
    s = (code_std or "").lower()
    if lang == "cpp":
        if "cpp23" in s or "c++23" in s:
            return "c++23"
        if "cpp20" in s or "c++20" in s:
            return "c++20"
        return "c++17"
    if lang == "c":
        if "c17" in s:
            return "c17"
        if "c99" in s:
            return "c99"
        return "c11"
    return ""


def _pick_srcname(ex: dict, lang: str) -> str:
    """从 expected_output 里回推源文件名（__FILE__ / 诊断行会带真实文件名）。"""
    exp = ex.get("expected_output") or ""
    m = re.search(r"\b([A-Za-z_][\w.-]*\.(?:cpp|cc|cxx|c))\b", exp)
    if m:
        return m.group(1)
    return "main.cpp" if lang == "cpp" else "main.c"


def _java_class_name(code: str) -> str:
    m = re.search(r"public\s+(?:final\s+|abstract\s+)?class\s+(\w+)", code)
    if m:
        return m.group(1)
    # 退化：含 main 的类
    for m in re.finditer(r"class\s+(\w+)", code):
        seg = code[m.start(): m.start() + 1200]
        if "static void main" in seg:
            return m.group(1)
    return "Main"


def run_example(ex: dict, workdir: pathlib.Path):
    """返回 (ok, detail)。detail 为失败原因或摘要。"""
    lang = (ex.get("code_lang") or "").lower()
    code = ex.get("code") or ""
    stdin_text = ex.get("stdin") or ""
    if lang in ("sql", "mysql", "html"):
        return True, "skip(无本地可执行环境)"
    if lang == "c":
        src = workdir / _pick_srcname(ex, "c")
        src.write_text(code, encoding="utf-8")
        std = _std_flag("c", ex.get("code_std"))
        rc, out = _run([GCC, f"-std={std}", "-O2", src.name, "-o", "main.exe"], workdir, "")
        if rc != 0:
            return False, f"编译失败 rc={rc}\n{out.strip()[:400]}"
        rc, out = _run([str(workdir / "main.exe")], workdir, stdin_text)
    elif lang == "cpp":
        src = workdir / _pick_srcname(ex, "cpp")
        src.write_text(code, encoding="utf-8")
        std = _std_flag("cpp", ex.get("code_std"))
        rc, out = _run(
            [GXX, f"-std={std}", "-O2", "-pthread", src.name, "-o", "main.exe"], workdir, ""
        )
        if rc != 0:
            return False, f"编译失败 rc={rc}\n{out.strip()[:400]}"
        rc, out = _run([str(workdir / "main.exe")], workdir, stdin_text)
    elif lang == "python":
        src = workdir / "main.py"
        src.write_text(code, encoding="utf-8")
        rc, out = _run([_py(), "main.py"], workdir, stdin_text)
    elif lang == "javascript":
        src = workdir / "main.js"
        src.write_text(code, encoding="utf-8")
        rc, out = _run([NODE, "main.js"], workdir, stdin_text)
    elif lang == "java":
        cls = _java_class_name(code)
        src = workdir / f"{cls}.java"
        src.write_text(code, encoding="utf-8")
        rc, out = _run(["javac", "-encoding", "UTF-8", f"{cls}.java"], workdir, "")
        if rc != 0:
            return False, f"编译失败 rc={rc}\n{out.strip()[:400]}"
        rc, out = _run(
            ["java", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8",
             "-cp", ".", cls],
            workdir, stdin_text,
        )
    else:
        return True, f"skip(未知语言 {lang})"

    stem = pathlib.Path(str(ex.get("_file", ""))).stem.lower()
    expect_fail = bool(ex.get("_expect_fail") or ex.get("expect_fail"))
    if not expect_fail and any(k in stem for k in ("assert", "violation", "terminate", "abort")):
        expect_fail = True  # 这些示例本就演示异常终止，非零退出属预期
    if rc != 0 and not expect_fail:
        return False, f"运行非零退出 rc={rc}\n{out.strip()[:400]}"

    exp_lines = _substance(ex.get("expected_output") or "")
    if not exp_lines:
        return True, "无实质期望输出"
    act_lines = [l.strip() for l in out.splitlines()]
    i = 0
    for e in exp_lines:
        if _volatile(e):
            continue
        found = False
        while i < len(act_lines):
            if act_lines[i] == e or e in act_lines[i]:
                found = True
                i += 1
                break
            i += 1
        if not found:
            return False, f"期望行未在真实输出中出现: {e[:120]!r}\n实际输出:\n{out.strip()[:500]}"
    return True, f"{len(exp_lines)} 行匹配"


_ADDR_RE = re.compile(r"(?:0x[0-9a-fA-F]{4,}|\b[0-9a-fA-F]{8,}\b)")


def _volatile(line: str) -> bool:
    """机器相关的期望行（内存地址等）不参与严格比对。"""
    if _ADDR_RE.search(line) and ("指向" in line or "address" in line.lower() or "0x" in line):
        return True
    return False


def _substance(text: str):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("$") or s.startswith("#"):
            continue
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter")
    ap.add_argument("--subject")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    files = sorted(CONTENT.rglob("examples/*.json"))
    if args.subject:
        files = [f for f in files if f.parent.parent.parent.name == args.subject]
    if args.chapter:
        files = [f for f in files if f.parent.parent.name == args.chapter]

    results = []
    for f in files:
        try:
            ex = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            results.append((str(f.relative_to(CONTENT)), False, f"JSON 解析失败: {e}"))
            continue
        ex["_file"] = f.stem
        ex["_chapter"] = f.parent.parent.name
        with tempfile.TemporaryDirectory(prefix="cppmind_verify_") as td:
            ok, detail = run_example(ex, pathlib.Path(td))
        results.append((str(f.relative_to(CONTENT)), ok, detail))

    bad = [r for r in results if not r[1]]
    if args.json:
        print(json.dumps(
            {"total": len(results), "ok": len(results) - len(bad),
             "failed": len(bad),
             "failures": [{"file": a, "detail": c} for a, _, c in bad]},
            ensure_ascii=False, indent=2))
    else:
        for path, ok, detail in results:
            if not ok:
                print(f"[FAIL] {path}\n       {detail.splitlines()[0]}")
        print(f"\n回放 {len(results)} 个示例：通过 {len(results) - len(bad)}，失败 {len(bad)}")
        for path, _, detail in bad:
            print(f"  - {path}: {detail.splitlines()[0]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
