# title: 系统设计容量账本：QPS→存储→带宽→卡数，与哪一项先爆
# 本地模拟：容量估算器 + 预算上限对照，不调用任何外部服务。
# 目的：把「面试现场 5 分钟推完的账」落成可复算的代码——每个数字带公式与假设。

import math


def capacity(docs, doc_kb, qps, dim=1024, bytes_per=4, replicas=3,
             chunks_per_doc=5, ctx_kb=3, ans_bytes=512, gpu_qps=20):
    """返回四类估算：原文存储(B)、向量存储(B)、出口带宽(B/s)、生成卡数(张, 不含冗余)。"""
    raw = docs * doc_kb * 1024 * replicas                 # 原文 × 3 副本
    chunks = docs * chunks_per_doc                        # 20KB 文档按 4KB 切块 ≈ 5 块
    vec = chunks * dim * bytes_per * 1.5                  # 向量 + HNSW 索引系数 1.5
    bw = qps * (ctx_kb * 1024 + ans_bytes)                # 每请求 3KB 上下文 + 0.5KB 答案
    gpus = max(1, math.ceil(qps / gpu_qps))               # 单卡 7B fp16 约 20 QPS（经验值）
    return raw, vec, bw, gpus


# 预算上限（面试场景给定：现有集群余量）
BUDGET = {"raw": 100e9, "vec": 100e9, "bw": 10e6, "gpus": 8}

base = capacity(docs=100_000, doc_kb=20, qps=50)
raw, vec, bw, gpus = base
print("== 基线账本（10 万文档 × 20KB，峰值 50 QPS） ==")
print(f"  原文存储 = 10万 × 20KB × 3 副本      = {raw/1e9:.1f} GB")
print(f"  向量存储 = 10万 × 5 块 × 1024 维 × 4B × 1.5 = {vec/1e9:.2f} GB")
print(f"  出口带宽 = 50 QPS × (3KB + 0.5KB)   = {bw/1e3:.0f} KB/s")
print(f"  生成卡数 = ceil(50 / 20)             = {gpus} 张（另留 1 张冗余）")

# 与参考解逐项比对（面试官手里的「标准答案」量级）
ref = {"raw": 6.1e9, "vec": 3.1e9, "bw": 1.8e5, "gpus": 3}
for k, got in zip(("raw", "vec", "bw", "gpus"), base):
    ratio = got / ref[k]
    assert 0.5 <= ratio <= 2.0, f"{k} 与参考解差 {ratio:.1f} 倍，超出 2 倍容差"
print("  与参考解比对：四项全部在 2 倍量级容差内（报假设比报结果重要）")

# ---------- 敏感性：哪一项先爆 ----------
print("\n== 敏感性：规模放大后哪项先超预算 ==")
print(f"{'场景':<18}{'存储(GB)':>10}{'向量(GB)':>10}{'带宽(KB/s)':>11}{'卡数':>6}  先爆项")
scenarios = [
    ("基线", 100_000, 20, 50),
    ("QPS×2（活动）", 100_000, 20, 100),
    ("QPS×5（爆款）", 100_000, 20, 250),
    ("文档×10（并库）", 1_000_000, 20, 50),
    ("文档×10 且 QPS×2", 1_000_000, 20, 100),
]
for name, d, kb, q in scenarios:
    r, v, b, g = capacity(d, kb, q)
    over = [k for k, val, lim in
            (("存储", r, BUDGET["raw"]), ("向量", v, BUDGET["vec"]),
             ("带宽", b, BUDGET["bw"]), ("卡数", g, BUDGET["gpus"])) if val > lim]
    print(f"{name:<18}{r/1e9:>10.1f}{v/1e9:>10.1f}{b/1e3:>11.0f}{g:>6}  {'、'.join(over) or '无'}")

r5, v5, b5, g5 = capacity(100_000, 20, 250)
assert g5 > BUDGET["gpus"] and r5 < BUDGET["raw"] and b5 < BUDGET["bw"]
print("  结论：QPS×5 时先爆的是生成卡数（13 张 > 8 张预算），存储与带宽都还宽松；")
print("  扩容第一优先级因此是生成层——而最快的解法往往不是买卡：缓存 + 批处理两个杠杆叠加即可回到预算内（见下）。")

# ---------- 缓存杠杆 ----------
hot_share, hit_rate = 0.2, 0.8
gen_before = 250
gen_after = gen_before * ((1 - hot_share) + hot_share * (1 - hit_rate))
print(f"\n== 两个杠杆叠加：缓存（20% 热点 × 80% 命中）+ 连续批处理（单卡 20→30 QPS） ==")
print(f"  仅缓存：生成量 {gen_before} -> {gen_after:.0f} QPS，卡数 {math.ceil(gen_before/20)} -> {math.ceil(gen_after/20)}（仍超 8 张预算）")
gpu_batched = 30
g_after = math.ceil(gen_after / gpu_batched)
print(f"  再加批处理：卡数 -> ceil({gen_after:.0f}/30) = {g_after} <= 8，回到预算内")
assert g_after <= BUDGET["gpus"]

print("\n结论：容量账的顺序是 QPS→存储→带宽→卡数，而扩容优先级由「哪项先爆」决定，不由哪项数字大决定；")
print("读法：1. 存储要乘副本系数（3）、索引系数（1.5），请求出站带的是上下文片段不是整篇文档——这两处是面试最常抓的口径错；2. 卡数 = ceil(QPS ÷ 单卡吞吐)，单卡 20 QPS 是 7B fp16 的经验值，换量化/更大批量要重标；3. 先爆的项决定扩容方向，也决定「先上缓存还是先买卡」——缓存是零质量损失的吞吐杠杆；4. 本示例为本地估算，真实参数按集群实测标定（ch14/ch15 的部署与成本口径）。")
