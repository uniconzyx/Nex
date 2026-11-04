# -*- coding: utf-8 -*-
"""从 content/_handmade/labs.json 为 13 章 sandbox 求出一组「通关参数解」。

复用 audit_handmade_labs 的求值器（ev / grid / sample_axes），对每个 sandbox
模块穷举第一组满足全部 checks 的参数组合，写成
frontend/scripts/sandbox_solutions.json，供 verify_labs_sandbox13.mjs 把旋钮
拖到全绿做真机验收。

输出格式：
  { "<subject>/<chapter>": {
      "ok": true,
      "params": [ {"key":..,"type":"range"|"opt","value":..}, ... ]
    }, ... }
"""
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import audit_handmade_labs as A  # noqa: E402

# 默认目标：第一/二批补的 13 章（历史清单，保持向后兼容）。
# 现在更推荐 `python scripts/solve_sandbox.py --all`——扫描 labs.json 里
# 所有带 sandbox 的章节，新增批次（tooling/middleware 等）会自动纳入，
# 不用再手改这个列表。两种方式输出的 JSON 结构完全一致。
TARGETS = [
    "ml/ml-ch03", "ml/ml-ch08", "ml/ml-ch09",
    "ai/ai-ch01", "ai/ai-ch02", "ai/ai-ch08", "ai/ai-ch10", "ai/ai-ch12", "ai/ai-ch14",
    "database/db-ch01", "database/db-ch05", "database/db-ch06", "database/db-ch07",
]


def metrics_of(vals, mod):
    env = dict(vals)
    for m in mod["metrics"]:
        env[m["key"]] = A.ev(m["expr"], env)
    return env


def ok_of(env, mod):
    for c in mod["checks"]:
        if A.ev(c["expr"], env) == 0:
            return False
    return True


def locked_value(mod, axis_key):
    """从 checks 里挖出 `key == 常数` 形式的锁定值。

    为什么需要这一步：`sample_axes` 是隔位抽样，会把 `rows == 4000` 这种
    「偶数下标靠后」的精确值抽掉，于是锁定判据永远不成立，误判「无解」。
    这里把被锁定的轴直接收窄成一个点，既避开抽样盲区，也把搜索空间砍掉一大截
    （8 个参数各抽 5 档也不够用，锁死后必然有解）。
    """
    import re
    pat = re.compile(rf"\b{re.escape(axis_key)}\s*==\s*([0-9]+(?:\.[0-9]+)?)\b")
    for c in mod["checks"]:
        m = pat.search(c["expr"])
        if m:
            return float(m.group(1))
    return None


def solve(key, mod):
    keys = [p["key"] for p in mod["params"]]
    axes = []
    for p in mod["params"]:
        full = A.grid(p)
        lock = locked_value(mod, p["key"])
        if lock is not None and lock in full:
            # 被 == 锁死的轴：直接钉到那一个值，不参与抽样
            axes.append([lock])
        else:
            axes.append(full)
    axes, _ = A.sample_axes(axes)
    for combo in itertools.product(*axes):
        vals = dict(zip(keys, combo))
        env = metrics_of(vals, mod)
        if ok_of(env, mod):
            out = []
            for p in mod["params"]:
                k = p["key"]
                if p.get("labels") and len(p["labels"]) >= 2:
                    out.append({"key": k, "type": "opt", "value": int(vals[k])})
                else:
                    out.append({"key": k, "type": "range", "value": float(vals[k])})
            return {"ok": True, "params": out}
    return {"ok": False, "params": []}


def main() -> int:
    labs = json.load(open(os.path.join(ROOT, "content", "_handmade", "labs.json"), encoding="utf-8"))
    chapters = labs.get("chapters") or {}
    # --all：扫描 labs.json 里所有含 sandbox 的章（新增批次自动纳入）
    if "--all" in sys.argv:
        targets = sorted(k for k, v in chapters.items()
                         if isinstance(v, list) and any(m.get("kind") == "sandbox" for m in v))
    else:
        targets = TARGETS
    result = {}
    for key in targets:
        mods = chapters.get(key, [])
        sb = next((m for m in mods if m.get("kind") == "sandbox"), None)
        if not sb:
            result[key] = {"ok": False, "params": [], "reason": "no sandbox module"}
            continue
        result[key] = solve(key, sb)
        print(f"{key}: {'OK ' + str(len(result[key]['params'])) + ' params' if result[key]['ok'] else 'NO SOLUTION'}")
    out_path = os.path.join(ROOT, "frontend", "scripts", "sandbox_solutions.json")
    # newline="\n"：Windows 上默认翻译成 CRLF，会让这份 JSON 的 diff 整文件翻转
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    ok = sum(1 for v in result.values() if v.get("ok"))
    print(f"written -> {out_path}  ({ok}/{len(result)} 有解)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
