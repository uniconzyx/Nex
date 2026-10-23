# title: 单任务四元成本拆解：token、卡时、向量库与人工兜底各占多少
# 单价均为教学假设（示例测算），仅用于展示账本结构；兜底率按真实分布估计。
import numpy as np

P_IN = 0.008 / 1000   # 输入 ¥/token（示例测算）
P_OUT = 0.024 / 1000  # 输出 ¥/token（示例测算）


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def task_cost(tok_in, tok_out, gpu, vec, fb_rate, human):
    """四元成本：返回分项 dict 与合计"""
    tok = tok_in * P_IN + tok_out * P_OUT
    fb = fb_rate * human
    return {"token": tok, "gpu": gpu, "vector": vec, "fallback": fb,
            "total": tok + gpu + vec + fb}


# 三类任务（示例测算参数）：售前咨询短平快、售后工单长上下文、知识问答重检索
TASKS = {
    "售前咨询": dict(tok_in=1200, tok_out=300, gpu=0.006, vec=0.002, fb_rate=0.15, human=3.0),
    "售后工单": dict(tok_in=3000, tok_out=400, gpu=0.012, vec=0.004, fb_rate=0.40, human=5.0),
    "知识问答": dict(tok_in=2500, tok_out=500, gpu=0.010, vec=0.003, fb_rate=0.25, human=4.0),
}

print("== 单任务四元成本测算表（示例测算） ==")
print(f"{pad('任务类型', 10)}{'token':>9}{'卡时':>8}{'向量库':>8}{'兜底':>9}{'合计':>9}{'兜底占比':>9}")
rows = {}
for name, p in TASKS.items():
    c = task_cost(p["tok_in"], p["tok_out"], p["gpu"], p["vec"], p["fb_rate"], p["human"])
    rows[name] = c
    print(f"{pad(name, 10)}{c['token']:>9.3f}{c['gpu']:>8.3f}{c['vector']:>8.3f}"
          f"{c['fallback']:>9.3f}{c['total']:>9.3f}{c['fallback']/c['total']:>9.0%}")

# 报价下限：p = c / (1 - g)；注意不是 c*(1+g)
g = 0.70
print(f"\n== 报价下限（目标毛利率 {g:.0%}） ==")
for name, c in rows.items():
    print(f"{pad(name, 10)}: 成本 ¥{c['total']:.3f} → 下限 ¥{c['total']/(1-g):.2f}/任务")

# 敏感性：兜底率 ±10pp 对合计的影响（以售后工单为例）
base = TASKS["售后工单"]
c0 = task_cost(**base)
for d in (-0.10, 0.10):
    p = dict(base, fb_rate=base["fb_rate"] + d)
    c1 = task_cost(**p)
    print(f"售后工单 兜底率 {base['fb_rate']:.0%}→{p['fb_rate']:.0%}：合计 ¥{c1['total']:.3f}"
          f"（{c1['total']/c0['total']-1:+.1%}）")

print("\n结论：人工兜底是四元里最大且最刚性的项（三类任务中兜底占比均超过九成），")
print("读法：1. 账本必须四项分开记——token/卡时可随技术优化压缩，兜底率只能靠质量与路由改善，混在一起算就无法归因；2. 报价下限用 c/(1-g) 而非 c×(1+g)，后者会把 70% 毛利报成 2.3 倍价还以为只加了 70%；3. 兜底率 ±10pp 对合计的影响远大于 token 单价波动，优化优先级最高；4. 本示例单价为教学假设（示例测算），真实计价以服务商与人工成本为准，但账本结构一致。")
