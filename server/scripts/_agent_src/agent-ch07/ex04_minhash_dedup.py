# title: MinHash + LSH 去重：把 O(n²) 的两两比较降到候选对
# 字符 3-gram → MinHash 签名 → 分带 LSH 找候选 → 精确 Jaccard 复核 → 并查集聚类。
import hashlib
import numpy as np

DOCS = [
    "请把这段话翻译成英文：今天的会议推迟到下午三点。",
    "请把这段话翻译成英文：今天的会议推迟到下午三点举行。",
    "请把这段话翻译成英文，今天的会议推迟到下午3点。",
    "退货政策是什么？订单签收后七天内可以无理由退货。",
    "退货政策是什么？订单签收后 7 天内支持无理由退货。",
    "如何修改发票抬头？在订单详情页点击发票管理。",
    "公司的报销流程需要先提交纸质单据吗？",
    "请把下面这句话翻译为英文：会议改到下午三点。",
]

def shingles(text, k=3):
    t = "".join(ch for ch in text if not ch.isspace())
    return {t[i:i + k] for i in range(max(0, len(t) - k + 1))}

def stable_hash(s):
    return int.from_bytes(hashlib.md5(s.encode("utf-8")).digest()[:8], "big")

PRIME = (1 << 61) - 1
K, BANDS, ROWS = 64, 32, 2          # 阈值约 (1/32)^(1/2) ≈ 0.18，偏召回
rng = np.random.default_rng(2024)
A = rng.integers(1, PRIME, K)
B = rng.integers(0, PRIME, K)

def signature(sh):
    hv = np.array([stable_hash(s) % PRIME for s in sh], dtype=object)
    sig = []
    for a, b in zip(A, B):
        sig.append(int(np.min((a * hv + b) % PRIME)))
    return np.array(sig)

sh_sets = [shingles(d) for d in DOCS]
sigs = np.stack([signature(s) for s in sh_sets], axis=1)   # K × n

def jaccard(i, j):
    a, b = sh_sets[i], sh_sets[j]
    return len(a & b) / len(a | b)

# 分带 LSH：任一带完全相同 → 候选
buckets = {}
for band in range(BANDS):
    for j in range(len(DOCS)):
        key = (band, tuple(sigs[band * ROWS:(band + 1) * ROWS, j]))
        buckets.setdefault(key, []).append(j)

candidates = set()
for members in buckets.values():
    for x in range(len(members)):
        for y in range(x + 1, len(members)):
            candidates.add((members[x], members[y]))

print(f"{len(DOCS)} 条数据，两两比较 {len(DOCS)*(len(DOCS)-1)//2} 对；"
      f"LSH 候选 {len(candidates)} 对，减少 "
      f"{1-len(candidates)/(len(DOCS)*(len(DOCS)-1)//2):.0%} 的比较量")

print(f"\n{'候选对':<10}{'精确 Jaccard':>14}  判定（阈值 0.55）")
THRESH = 0.55
kept = []
for i, j in sorted(candidates):
    jac = jaccard(i, j)
    print(f"({i},{j})".ljust(10) + f"{jac:>14.3f}  {'重复' if jac >= THRESH else '保留'}")
    if jac >= THRESH:
        kept.append((i, j))

# 并查集合并重复簇
parent = list(range(len(DOCS)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for i, j in kept:
    parent[find(j)] = find(i)
clusters = {}
for i in range(len(DOCS)):
    clusters.setdefault(find(i), []).append(i)

print("\n去重后的簇：")
removed = 0
for root, members in clusters.items():
    if len(members) > 1:
        removed += len(members) - 1
        print(f"  保留 #{members[0]}，删除 {members[1:]}  （{len(members)} 条近重复）")
print(f"原始 {len(DOCS)} 条 → 保留 {len(DOCS)-removed} 条，去重率 {removed/len(DOCS):.0%}")

print("\n阈值敏感性（同一批候选对，只改判定线）：")
print(f"{'阈值':>6}{'删除条数':>10}{'说明':>28}")
all_pairs = sorted((jaccard(i, j), i, j) for i, j in candidates)
for th in (0.45, 0.55, 0.65, 0.75):
    pairs = [(i, j) for jac, i, j in all_pairs if jac >= th]
    p = list(range(len(DOCS)))
    def f(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    for i, j in pairs:
        p[f(j)] = f(i)
    n_removed = len(DOCS) - len({f(i) for i in range(len(DOCS))})
    note = "过松：可能误删同主题不同意图" if th <= 0.45 else (
        "较稳：对话去重常用" if th < 0.65 else "过严：漏删改写型重复")
    print(f"{th:>6.2f}{n_removed:>10}{note:>28}")

print("\n结论：MinHash 只负责「找出可能重复」，最终是否合并必须用精确 Jaccard + 人工定阈值。")
print("读法：3-4 是同一退货政策的改写（Jaccard 0.517），0.55 会漏掉它、0.45 才能合并；")
print("      而 0.45 又可能误删同主题不同意图的样本 —— 阈值没有通用值，必须抽 30 对人工校准。")
print("      语义重复（换同义词、换语序）MinHash 抓不到，要再叠一层 embedding 聚类。")
