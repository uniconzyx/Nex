# -*- coding: utf-8 -*-
"""把 scripts/_ai11_out/exNN.{py,txt} 写成 content/ai/ai-ch11/examples/exNN-*.json。

纪律：expected_output 直接读真实跑出的 txt，绝不手写。
用法：python scripts/_write_ai11_examples.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scripts" / "_ai11_out"
DEST = ROOT / "content" / "ai" / "ai-ch11" / "examples"

META = {
    "ex01": ("批处理耗时曲线：固定开销如何被摊销", "固定开销 20ms + 每样本 2.5ms 时，批大小对每样本耗时与吞吐的影响"),
    "ex02": ("动态批处理模拟：max_batch 与 max_wait 的交互", "泊松到达下的离散事件模拟，验证等待窗口的性价比随负载变化"),
    "ex03": ("从 SLO 倒推批大小与等待窗口", "给定 P99 预算，扣除框架与网络开销后能用的计算预算与批大小"),
    "ex04": ("输入契约校验：五类非法输入与 NaN 的三条反直觉性质", "形状/类型/数值/下限/白名单逐条拒绝，并展示 NaN != NaN"),
    "ex05": ("NaN 在批内的传播边界", "单个 NaN 只污染所在条目，但下游聚合会让整批变 nan"),
    "ex06": ("容量规划：延迟约束与硬件约束取小", "同一 QPS 下 SLO 收紧如何压低批大小；副本数随 QPS 线性增长"),
    "ex07": ("重试退避的抖动：峰值占比的定量对比", "无抖动时 200 客户端在同一毫秒重试，有抖动后峰值占比降到 7%"),
    "ex08": ("降级策略矩阵：按场景容忍度算净收益", "五种业务场景 x 三种降级策略，判定哪些组合可接受"),
    "ex09": ("模型版本命名解析与同名覆盖检测", "从文件名解析版本与哈希，检出同版本不同哈希的覆盖风险"),
    "ex10": ("健康检查三层与冷启动：ready 不等于 warm", "未预热时首次推理耗时翻倍，摘流条件应为 ready AND warm"),
}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    n = 0
    for key in sorted(META):
        py = OUT / f"{key}.py"
        txt = OUT / f"{key}.txt"
        if not py.exists() or not txt.exists():
            print(f"  [skip] {key}: 缺 py 或 txt")
            continue
        title, note = META[key]
        slug = {
            "ex01": "batch-latency-curve",
            "ex02": "dynamic-batching-sim",
            "ex03": "slo-to-batch-size",
            "ex04": "input-contract",
            "ex05": "nan-propagation",
            "ex06": "capacity-planning",
            "ex07": "retry-jitter",
            "ex08": "degrade-matrix",
            "ex09": "model-versioning",
            "ex10": "health-and-warmup",
        }[key]
        obj = {
            "title": title,
            "code_lang": "python",
            "code_std": "python3",
            "stdin": "",
            "note": note,
            "expected_output": txt.read_text(encoding="utf-8"),
            "code": py.read_text(encoding="utf-8"),
        }
        path = DEST / f"{key}-{slug}.json"
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        n += 1
        print(f"  [ok] {path.name}")
    print(f"\n写出 {n} 个示例")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
