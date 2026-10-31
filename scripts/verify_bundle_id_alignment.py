"""验证后端 bundle_id 与前端 BankExercise.id 的 1:1 对齐（不连库）。

做法：
  A. 用生成器 gen_exercise_bundle.build() 拿到前端 exercises.ts 实际使用的 id 集合
     （这是前端 BankExercise.id 的权威来源）。
  B. 用与 server/scripts/seed_and_import_bank.py 完全相同的规则独立重算「后端实际会导入」
     的 bundle_id 集合：
       - bundle_id 计算：全局 seen + `_c=1` while 去重（与 gen_exercise_bundle 同源，
         且在全量 items 上构建 seen，含最终会被 clean_items 丢弃的题——与 seed 行为一致）。
       - 复刻 clean_items 丢弃判定（coding 无 test_cases / choice 非法 option），
         被丢弃的题不计入后端导入集合。
  比对：后端导入集合 ⊆ 前端 id 集合（孤儿数应为 0）；允许的差额是前端的非法题（被丢弃，
  属预期，云端目录不标 ☁ 是正确行为）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server" / "scripts"))

import gen_exercise_bundle as gen  # 仅依赖标准库，可安全导入

CONTENT = ROOT / "content"

VALID_TYPES = {"choice", "fix_error", "output", "coding"}


def norm_type(t):
    if t in VALID_TYPES:
        return t
    return "output"


def _norm_options(opts):
    """复刻 seed_and_import_bank.norm_options：字符串列表 -> {key,text} 字典列表。"""
    if not isinstance(opts, list):
        return None
    out = []
    for i, o in enumerate(opts):
        if isinstance(o, dict):
            out.append(o)
        elif isinstance(o, str):
            m = re.match(r"^([A-Za-z])\.?\s*(.*)$", o)
            if m:
                out.append({"key": m.group(1).upper(), "text": m.group(2)})
            else:
                out.append({"key": chr(ord("A") + i), "text": o})
    return out or None


def _clean_keep(it: dict) -> bool:
    """复刻 seed_and_import_bank.clean_items 的丢弃判定（纯逻辑，不依赖 app）。"""
    t = norm_type(it.get("type"))
    ans = it.get("answer")
    if not isinstance(ans, dict):
        # 复刻 norm_answer 对 choice 的影响（字符串答案视为单选）
        if t == "choice" and isinstance(ans, str):
            ans = {"correct": [ans]}
        elif isinstance(ans, str):
            ans = {"text": ans}
        else:
            ans = {}
    if t == "coding":
        if not (it.get("test_cases") or []):
            return False  # 无用例的 coding 属已知缺口，跳过
    if t == "choice":
        opts = _norm_options(it.get("options")) or []
        keys = {o.get("key") for o in opts if isinstance(o, dict)}
        correct = ans.get("correct", [])
        correct = set(correct) if isinstance(correct, (list, tuple, set)) else {correct}
        if len(keys) < 2 or not correct or not correct.issubset(keys):
            return False  # 非法 choice，跳过
    return True


def parse_exercises_ts_ids() -> tuple[set[str], set[str]]:
    """从前端生成的 exercises.ts 解析出真实 id 集合（括号平衡，避免正文里的 ] 截断）。"""
    src = (ROOT / "frontend" / "src" / "data" / "exercises.ts").read_text(encoding="utf-8")
    marker = "export const EXERCISES: BankExercise[] ="
    mi = src.index(marker)
    # 类型注解 BankExercise[] 里也有 []，必须定位「] = [」之后数组真正的起点
    eq = src.index("] = [", mi)
    i = eq + len("] = [") - 1  # 指向数组开头的 '['
    depth = 0
    in_str = False
    esc = False
    start = i
    end = -1
    for j in range(i, len(src)):
        c = src[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = j
                break
    arr = json.loads(src[start : end + 1])
    return {e["id"] for e in arr}, {e.get("subj") for e in arr}


def importer_rule_ids() -> tuple[set[str], int]:
    """复刻 seed_and_import_bank 的「后端实际导入」bundle_id 集合。

    返回 (会被导入的 id 集合, 全量去重后的 id 数)。
    去重规则与 gen_exercise_bundle 同源（全局 seen + `_c=1` while），并在全量 items
    上构建 seen（含会被丢弃的题），保证与 seed 运行结果一致。
    """
    ids: set[str] = set()       # 后端实际会导入的 id（clean 后）
    seen_full: set[str] = set()  # 全量去重 seen（含被丢弃题），与 gen 对应
    for fp in sorted(CONTENT.glob("*/*/exercises.json")):
        sub = fp.parent.parent.name
        ch = fp.parent.name
        if sub.startswith("_"):
            continue
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw = doc.get("items") if isinstance(doc, dict) else doc
        if not isinstance(raw, list):
            continue
        for i, it in enumerate(raw):
            if not isinstance(it, dict):
                continue
            bid = str(it.get("id") or f"{ch}-{i + 1:02d}")
            if bid in seen_full:
                _c = 1
                while f"{bid}-{_c}" in seen_full:
                    _c += 1
                bid = f"{bid}-{_c}"
            seen_full.add(bid)
            if _clean_keep(it):
                ids.add(bid)
    return ids, len(seen_full)


def main() -> int:
    fe_ids, fe_subjs = parse_exercises_ts_ids()
    imp_ids, imp_full = importer_rule_ids()

    print(f"前端 exercises.ts 题数: {len(fe_ids)}  (学科 {len(fe_subjs)})")
    print(f"后端全量去重 bundle_id 数: {imp_full}")
    print(f"后端实际会导入的 bundle_id 数: {len(imp_ids)}")

    missing = fe_ids - imp_ids  # 前端有、后端无（=被丢弃的非法题，预期）
    extra = imp_ids - fe_ids    # 后端有、前端无（孤儿，应为 0）

    print(f"\n前端∩后端一致(均含): {len(fe_ids & imp_ids)}")
    print(f"后端孤儿(后端有但前端无, 必须为0): {len(extra)}")
    print(f"前端有/后端无(被丢弃非法题, 预期): {len(missing)}")

    if extra:
        print("\n--- 孤儿样例(前10) ---")
        for x in sorted(extra)[:10]:
            print("  ", x)
    if missing:
        print("\n--- 被丢弃样例(前10) ---")
        for x in sorted(missing)[:10]:
            print("  ", x)

    # 核心判定：后端导入集合必须 ⊆ 前端 id 集合（0 孤儿）。
    # 允许差额 = 被丢弃的非法题（前端有、后端无），属预期，不计入失败。
    ok = len(extra) == 0
    if ok:
        print("\n✅ 1:1 对齐：后端导入 bundle_id 集合 ⊆ 前端 id 集合，孤儿数 0"
              f"（被丢弃 {len(missing)} 道非法题，云端不标 ☁ 是正确行为）")
    else:
        print("\n❌ 存在孤儿（后端有、前端无），bundle_id 映射规则与生成器不一致，需修")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
