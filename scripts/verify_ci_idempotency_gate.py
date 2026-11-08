"""反向验证 content-health 的生成物同步门禁。

验证 `git status --porcelain -- <产物路径>` 能抓到两类漂移：
  A. tracked 产物被改（modified）—— 旧 git diff --exit-code 也能抓
  B. 新增学科生成了新 .ts 但没入库（untracked）—— 旧判据抓不到，本次增强的重点
并确认验证过程本身不留下任何工作区噪声。
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATHS = [
    "frontend/src/data/exercises.ts",
    "frontend/src/data/clangUnits.ts",
    "frontend/src/data/chapterContent.ts",
    "frontend/src/data/viz/",
]


def status() -> str:
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", *PATHS],
        cwd=ROOT, capture_output=True, text=True,
    )
    return r.stdout.strip()


def baseline() -> str:
    r = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True
    )
    return r.stdout.strip()


def main() -> int:
    ok = True
    base = status()
    print("baseline (限定路径):", repr(base))
    if base:
        print("  FAIL: 基线不干净，无法验证")
        return 1

    # ---- A. tracked 产物被改 ----
    chapter = ROOT / "frontend/src/data/chapterContent.ts"
    orig = chapter.read_bytes()
    try:
        chapter.write_bytes(orig + b"// probe: stale artifact\n")
        s = status()
        hit = bool(s) and "chapterContent.ts" in s
        print("A modified  ->", repr(s[:120]), "HIT" if hit else "MISS")
        ok &= hit
    finally:
        chapter.write_bytes(orig)

    # ---- B. 新增学科文件没入库（untracked）----
    probe = ROOT / "frontend/src/data/viz/__probe_subject.ts"
    try:
        probe.write_text("export default [];\n", encoding="utf-8")
        s = status()
        hit = bool(s) and "__probe_subject.ts" in s and "??" in s
        print("B untracked ->", repr(s[:120]), "HIT" if hit else "MISS")
        ok &= hit
    finally:
        probe.unlink(missing_ok=True)

    # ---- 恢复后必须干净 ----
    after = status()
    print("restored (限定路径):", repr(after))
    ok &= (after == "")
    # 全局工作区只作参考打印：它可能本来就有其它改动（提交前的文档/脚本改动、
    # 新入库文件等），拿它当判据会在任何非干净 checkout 上假 FAIL。
    # 真正的判据是上面「限定产物路径内已恢复干净」。
    full = baseline()
    print("worktree after (仅供参考):",
          [l for l in full.splitlines() if l.strip()][:8])

    print("RESULT:", "PASS 2/2 (modified + untracked 均被拦下)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
