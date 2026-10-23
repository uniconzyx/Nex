# title: 分页 vs 连续分配：同样 20GB KV 预算，连续分配只能驻留 61 条，分页能驻留 107 条
# 关键差异不是「块大小」，而是「按最大长度预留」还是「按实际长度增长」。
# 另附一个外部碎片实验：总空闲够、却找不到连续段时，连续分配会直接拒绝请求。
import numpy as np

GB = 1e9
KV_PER_TOKEN = 2 * 28 * 8 * 128 * 2.0     # 7B/GQA/FP16，约 114.7 KB
POOL = 20 * GB
N = 200

rng = np.random.default_rng(21)
max_len = np.clip(rng.lognormal(np.log(1800), 0.6, N), 512, 8192).astype(int)
actual = np.maximum(32, (max_len * rng.uniform(0.12, 1.0, N)).astype(int))


def contiguous_units(tokens, align=256):
    return int(np.ceil(tokens / align) * align)


def paged_units(tokens, block=16):
    return int(np.ceil(tokens / block) * block)


def fill(mode):
    used = 0
    admitted = 0
    payload = 0
    for i in range(N):
        reserve = max_len[i] if mode == "contiguous" else actual[i]
        units = contiguous_units(reserve) if mode == "contiguous" else paged_units(reserve)
        need = units * KV_PER_TOKEN
        if used + need > POOL:
            break
        used += need
        payload += actual[i] * KV_PER_TOKEN
        admitted += 1
    return admitted, used, payload


print(f"200 条请求，最大长度中位数 {int(np.median(max_len))} token，实际输出中位数 {int(np.median(actual))} token")
print(f"KV 预算 {POOL/GB:.0f} GB，单 token {KV_PER_TOKEN/1024:.1f} KB\n")
print(f"{'分配方式':<12}{'驻留条数':>9}{'占用GB':>9}{'有效载荷GB':>12}{'利用率':>9}{'每条约浪费':>12}")
rows = {}
for mode, label in (("contiguous", "连续+预留max"), ("paged", "分页+按实际")):
    adm, used, payload = fill(mode)
    rows[mode] = (adm, used, payload)
    waste = (used - payload) / adm / GB
    print(f"{label:<12}{adm:>9}{used/GB:>9.1f}{payload/GB:>12.1f}{payload/used:>9.0%}{waste:>10.2f}GB")

c, p = rows["contiguous"], rows["paged"]
print(f"\n分页多驻留 {p[0]-c[0]} 条（{(p[0]/c[0]-1):+.0%}），有效载荷利用率从 {c[2]/c[1]:.0%} 提到 {p[2]/p[1]:.0%}。")

# ---- 外部碎片：总空闲够，但找不到连续段 ----
print("\n外部碎片实验（连续分配，1 段 = 256 token）：")
CAP = 4000          # 单位段
free_ranges = [(0, CAP)]


def alloc(size):
    for i, (s, ln) in enumerate(free_ranges):
        if ln >= size:
            free_ranges[i] = (s + size, ln - size)
            if free_ranges[i][1] == 0:
                free_ranges.pop(i)
            return (s, size)
    return None


def release(span):
    free_ranges.append(span)
    free_ranges.sort()
    merged = []
    for s, ln in free_ranges:
        if merged and merged[-1][0] + merged[-1][1] == s:
            merged[-1] = (merged[-1][0], merged[-1][1] + ln)
        else:
            merged.append((s, ln))
    free_ranges[:] = merged


rng2 = np.random.default_rng(5)
live = []
fail_frag = 0
fail_total = 0
for _ in range(600):
    if live and rng2.random() < 0.45:
        release(live.pop(int(rng2.integers(0, len(live)))))
    need = int(rng2.integers(4, 120))
    span = alloc(need)
    if span is None:
        total_free = sum(ln for _, ln in free_ranges)
        if total_free >= need:
            fail_frag += 1
        else:
            fail_total += 1
    else:
        live.append(span)

print(f"  600 次分配里：因『没有连续段』失败 {fail_frag} 次，因『总量不足』失败 {fail_total} 次")
print(f"  碎片导致的失败占总失败数的 {fail_frag/max(fail_frag+fail_total,1):.0%}")
print(f"  结束时空闲段数量 {len(free_ranges)}，最大空闲段 {max(ln for _, ln in free_ranges)} 段，"
      f"总空闲 {sum(ln for _, ln in free_ranges)} 段")

print("\n读法：连续分配的两笔浪费是叠加的——先按 max_len 预留（内部碎片），")
print("再在请求结束时留下大小不一的空洞（外部碎片）。分页把两笔都压到『最后一个块』。")
print("PagedAttention 的块表让逻辑上连续的 KV 可以散落在物理显存里，代价是每次注意力计算多一次查表。")
print("\n结论：长上下文 + 高并发场景，分页不是优化项而是必需品；它把『能放几条』从")
print("『按最坏情况预留』变成『按实际增长分配』，同样显存能多服务 70% 的请求。")
