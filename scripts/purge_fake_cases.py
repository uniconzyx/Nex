"""清除「伪判题用例」：参考代码不读 stdin 的题，不该假装可判。

问题
--------------------------------------------------------------------
go-judge 的判题契约是 **完整程序 + stdin → 比对 stdout**
（`server/app/services/judge0.py:62`）。但题库里有一批历史用例长这样：

    {"input": "schema 与样例数据见 external_url", "expected_output": "见 external_url"}
    {"input": "nums=[2,7,11,15], target=9",      "expected_output": "0 1"}

而对应题目的 `reference_code` 是「函数 + 硬编码 main」：

    public static void main(String[] args) {
        int[] r = twoSum(new int[]{2, 7, 11, 15}, 9);   // 参数写死，从不读 args
        System.out.println(r[0] + " " + r[1]);
    }

学生提交自己的代码后，判题器会把 `nums=[2,7,11,15], target=9` 这串**文本**
当作 stdin 喂进去。程序要么忽略它（永远输出同一行，判题变成假通过），
要么解析失败（假失败）。**这比"没有用例"更糟：它给出错误的反馈。**

判定标准（硬判据，不看描述）
--------------------------------------------------------------------
看参考实现里有没有真正读 stdin 的调用：

    python  sys.stdin / input(
    c       scanf / fgets(..., stdin) / getchar / read(0
    cpp     scanf / std::cin / cin >> / getline(cin
    java    Scanner / System.in / BufferedReader
    js      process.stdin / readline / readFileSync(0
    sql     —— 恒为否：SQL 题要连真实库执行，本来就不走 stdin

不读 stdin 的题：`test_cases` 移入 `samples`（保留作为题面样例展示，
不参与判题），并写入 `judge_note` 说明为什么不能自动判分。

用法
--------------------------------------------------------------------
    python scripts/purge_fake_cases.py            # dry-run
    python scripts/purge_fake_cases.py --apply
    python scripts/purge_fake_cases.py --restore
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
BACKUP = CONTENT / "_backup_purge_fake"

STDIN_PAT = {
    "python": re.compile(r"sys\.stdin|\binput\s*\("),
    "c": re.compile(r"scanf|fgets\s*\([^)]*stdin|getchar|\bread\s*\(\s*0"),
    "cpp": re.compile(
        r"scanf|std::cin|\bcin\s*>>|getline\s*\(\s*(std::)?cin|std::getline\s*\(\s*std::cin"
    ),
    "java": re.compile(r"Scanner|System\.in|BufferedReader"),
    "js": re.compile(r"process\.stdin|readline|readFileSync\s*\(\s*0"),
    "sql": re.compile(r"$^"),  # 永不匹配
}

SUBJ_LANG = {
    "cpp": "cpp", "clang": "c", "java": "java", "spring": "java",
    "python": "python", "ai": "python", "agent": "python", "ml": "python",
    "data": "python", "bigdata": "python", "tooling": "python",
    "database": "sql", "middleware": "sql", "fundamentals": "c", "fullstack": "js",
}


def lang_of(sub: str, code: str) -> str:
    """先认代码特征，再退回学科默认值（同学科会混语言）。"""
    if re.search(r"\bpublic\s+(final\s+)?class\b|System\.out\.print|\bimport\s+java\.", code):
        return "java"
    if re.search(r"#\s*include\s*<(iostream|vector|string|algorithm|stack|sstream|map|unordered_map)>", code) \
            or re.search(r"\bstd::", code):
        return "cpp"
    if re.search(r"#\s*include\s*<stdio\.h>", code):
        return "c"
    if re.search(r"^\s*def\s+\w+\s*\(|^\s*import\s+\w+|^\s*from\s+\w+\s+import", code, re.M):
        return "python"
    if re.search(r"\bfunction\s+\w+\s*\(|console\.log|=>", code):
        return "js"
    return SUBJ_LANG.get(sub, "python")


def reads_stdin(sub: str, code: str) -> tuple[bool, str]:
    lang = lang_of(sub, code)
    pat = STDIN_PAT.get(lang)
    return (bool(pat and pat.search(code)), lang)


NOTE = {
    "python": "本题参考实现是「函数 + 自测脚本」，没有 stdin 接口，离线不做自动判分。请对照 samples 与参考实现自评。",
    "c": "本题参考实现是函数片段，没有 stdin 接口，离线不做自动判分。请对照 samples 与参考实现自评。",
    "cpp": "本题参考实现是「函数 + 硬编码 main」，没有 stdin 接口，离线不做自动判分。请对照 samples 与参考实现自评。",
    "java": "本题参考实现是「方法 + 硬编码 main」，不读 args，离线不做自动判分。请对照 samples 与参考实现自评。",
    "js": "本题参考实现是函数片段，没有 stdin 接口，离线不做自动判分。请对照 samples 与参考实现自评。",
    "sql": "本题需要在真实数据库上执行 DDL/DML 才能验证，离线不做自动判分。请对照 samples 在本地库里跑一遍。",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP.exists():
            print("无备份")
            return 1
        snaps = sorted(p for p in BACKUP.iterdir() if p.is_dir())
        if not snaps:
            print("备份为空")
            return 1
        n = 0
        for src in snaps[-1].rglob("exercises.json"):
            dst = CONTENT / src.relative_to(snaps[-1])
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
        print(f"已从 {snaps[-1].name} 还原 {n} 个文件")
        return 0

    snap = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
    purged, kept, touched = 0, 0, {}

    for fp in sorted(CONTENT.glob("*/*/exercises.json")):
        sub = fp.parent.parent.name
        if sub.startswith("_"):
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        changed = False
        for it in data.get("items") or []:
            if (it.get("type") or "").lower() != "coding":
                continue
            tcs = it.get("test_cases") or []
            if not tcs:
                continue
            rc = (it.get("answer") or {}).get("reference_code") or ""
            ok, lang = reads_stdin(sub, rc)
            if ok:
                kept += 1
                continue
            # 伪用例：转成 samples，清掉 test_cases
            it["samples"] = tcs
            it.pop("test_cases", None)
            it["judge_note"] = NOTE.get(lang, NOTE["python"])
            purged += 1
            changed = True
            if args.verbose:
                print(f"  [purge] {sub}/{fp.parent.name} {str(it.get('title'))[:32]} ({lang})")
        if changed:
            touched[fp] = data

    print("\n==== 统计 ====")
    print(f"  清除伪用例   {purged}")
    print(f"  保留真用例   {kept}")
    print(f"  涉及文件     {len(touched)}")
    if args.apply and touched:
        for fp, data in touched.items():
            bak = snap / fp.relative_to(CONTENT)
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak)
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n已写入。备份：{snap}")
    elif not args.apply:
        print("\n(dry-run，未写入)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
