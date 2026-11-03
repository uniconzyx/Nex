#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给「只有打靶模块」的章节补『**正确做法**：』行，让 match 能从 pitfalls 自动长出来。

只做一件事：在指定条目的块尾追加一行（3 空格缩进 + 中文全角冒号）。
不新增列表项（`RE_LI` 只认 `- ` / `* ` / `1. ` 开头），所以 audit_depth 的陷阱条数不会虚增。
内容全部取自该条自己的正文结论，不引入原文以外的新知识点。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_interactive as G  # noqa: E402

# {章节: {条目序号: 正确做法正文}}
PATCH: dict = {
    "ai/ai-ch04": {
        3: "A 高斯随机、B 全零，保证 ΔW = B@A 从 0 起步，预训练能力无损。",
        4: "调 r 时按 alpha = 2r 同步缩放，保持有效缩放 alpha/r 不变。",
        7: "把指令段与 pad 位置的 label 置为 -100，只对回答段算损失。",
        15: "训练用 QLoRA（前向临时反量化），部署用 GPTQ/AWQ，两条路线不混用。",
    },
    "data/data-ch04": {
        1: '要广播回原表用 groupby("k")["v"].transform("mean")，结果与原表同长同索引。',
        4: 'merge 前用 validate="one_to_many" 声明基数，或先 drop_duplicates 再合并。',
        8: "时间操作前先 sort_index()，并断言 index.is_monotonic_increasing。",
        10: "性能判据只写布尔量（加速比>1: True）或确定性计数，不写机器相关耗时。",
    },
    "database/db-ch06": {
        1: "未选作主键的候选键一律补 UNIQUE 约束，让业务唯一性由库保证。",
        3: "先求出全部候选键取并集，再判主属性，别只看主键。",
        8: "闭包等于 U 只说明是超键，还要逐个去掉属性验证极小性。",
        12: "M:N 新建中间表，主键为两端主键的组合，联系自身属性放中间表。",
    },
    "fundamentals/fund-ch07": {
        1: "补码只有一个 0（0000_0000），1000_0000 定义为 $-2^{n-1}$，8 位即 -128。",
        2: "有符号溢出用 $C_{n-1} \\oplus C_{n-2}$ 判，或直接看「同号相加得异号」。",
        6: "偏置取 $2^{k-1} - 1$：单精度 127、双精度 1023。",
        8: "浮点比较用容差（绝对或相对误差），金额改用整数或十进制类型。",
    },
    "fundamentals/fund-ch08": {
        1: "先用总行数 ÷ $k$ 算出**组数**，再用组数定 index 位。",
        3: "$\\text{AMAT} = T_{hit} + m \\times T_{miss}$，多级必须嵌套展开，不能把各级命中时间相加。",
        4: "节拍取最慢段的 $T_{max}$，总时间 $= T_{max} \\times (k + n - 1)$。",
        6: "load-use 冒险必须停 1 拍；ALU 结果走旁路可 0 停顿。",
    },
    "fundamentals/fund-ch20": {
        7: "答题先写清前提（目录项与 inode 是否在内存），再按「读索引块 1 次 + 读数据块 1 次」计数。",
        8: "块号从 0 起：字号 = `b / 字长`（整除），位号 = `b % 字长`；块号从 1 起要先减 1。",
        9: "用 `lsof | grep deleted` 找出还开着已删文件的进程，重启该进程才真正释放块。",
        14: "排查顺序固定为 `df -i` → `lsof +L1` → 稀疏文件与预留块，别拿 `du` 当磁盘占用。",
    },
    "fundamentals/fund-ch22": {
        1: "比特率 = 波特率 × $\\log_2 V$，题目给了调制方式就必须乘。",
        3: "先把 dB 换算成倍数 $S/N = 10^{\\text{dB}/10}$，再代进 $\\log_2(1 + S/N)$。",
        4: "奈氏与香农各算一次取 min，并说明谁在起约束作用。",
        10: "解码值 = 内积 ÷ 码片长度；+1 收到 1、−1 收到 0、0 表示该站静默。",
    },
    "fundamentals/fund-ch23": {
        2: "发送方每见 5 个连续 1 就插一个 0；接收方对称地每见 5 个 1 删掉后面那个 0。",
        7: "GBN 取 $W \\le 2^n - 1$，SR 取 $W \\le 2^{n-1}$。",
        9: "最小帧长 = 速率 × $2\\tau$，$2\\tau$ 是往返时延（10Mbps 下 51.2μs → 64B）。",
        12: "VLAN Tag 插在源 MAC 之后、类型字段之前，帧长上限从 1518 变 1522，MTU 仍 1500。",
    },
    "python/py-ch06": {
        1: "校验格式一律用 `re.fullmatch`，或自己给模式加 `^...$`。",
        3: '替换模板统一用原始字符串 `r"\\1"` 或 `r"\\g<1>"`。',
        8: "按行匹配加 `re.M`，跨行匹配加 `re.S`，两个 flag 各管一件事。",
        17: "拼接用户输入前一律 `re.escape(user_input)`。",
    },
    "python/py-ch08": {
        3: "布尔条件写 `(a > 0) & (a < 5)`，每个条件都要加括号。",
        4: "`a - a.mean(axis=1, keepdims=True)`，让被减向量的轴长保留下来。",
        10: '`df.loc[df.a > 0, "b"] = 1`，单次 `loc` 落地，不要链式赋值。',
        13: '编号/电话/身份证列在 `read_csv` 时显式 `dtype=str`。',
    },
}

PREFIX = "   **正确做法**："


def patch(path: str, items: dict, dry: bool) -> str:
    txt = G.read(path)
    ms = list(G.PIT_ITEM.finditer(txt))
    plan = []
    for idx, body in items.items():
        if idx > len(ms):
            return f"条目 {idx} 超出 {len(ms)} 条"
        m = ms[idx - 1]
        end = ms[idx].start() if idx < len(ms) else len(txt)
        block = txt[m.start():end]
        if "**正确做法**" in block:
            continue  # 幂等：已经有了
        stripped = block.rstrip()
        at = m.start() + len(stripped)
        plan.append((at, PREFIX + body))
    if not plan:
        return "无需改动（已存在）"
    for at, line in sorted(plan, reverse=True):  # 从后往前插，避免偏移错乱
        txt = txt[:at] + "\n" + line + txt[at:]
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
    return f"补 {len(plan)} 条"


def main() -> None:
    dry = "--write" not in sys.argv
    for key, items in PATCH.items():
        s, c = key.split("/")
        p = os.path.join(G.CONTENT, s, c, "pitfalls.md")
        msg = patch(p, items, dry)
        ok = G.build_match(os.path.join(G.CONTENT, s, c))
        print(f"{'[dry]' if dry else '[write]'} {key:<24} {msg:<12} match={'✓' if ok else '✗'}")


if __name__ == "__main__":
    main()
