# title: 权限过滤：先取后删只返回 8 条、黄金丢 1 条；先删后取 10 条全中
# 240 个块、3 个租户、4 个密级；用户属于租户 A、密级 2。检索打分用词命中数模拟。
# 第四个配置演示最危险的一类：缓存键只按 query 文本，把 B 租户的结果直接发给 A。
import numpy as np

rng = np.random.default_rng(11)
TERMS = [f"t{i}" for i in range(12)]
QUERY = ["t0", "t1", "t2", "t3"]

chunks = []
for i in range(240):
    tenant = ["A", "B", "C"][i % 3]
    level = int(rng.integers(0, 4))
    terms = list(rng.choice(TERMS, 4, replace=False))
    chunks.append({"id": f"c{i:03d}", "tenant": tenant, "level": level, "terms": set(terms)})

# 5 条黄金块：租户 A、密级 2 以内、同时命中 3 个查询词
for j in range(5):
    chunks[j] = {"id": f"gold{j}", "tenant": "A", "level": 2, "terms": {"t0", "t1", "t2", "x"}}

# 租户 B 造 40 条高分块：它们同样命中查询词，但无权被 A 看到
for j in range(40, 80):
    chunks[j] = {"id": f"b{j}", "tenant": "B", "level": 1, "terms": {"t0", "t1", "t2", "t3"}}


def score(c):
    return len(c["terms"] & set(QUERY))


def rank(items, k):
    return sorted(items, key=lambda c: (-score(c), c["id"]))[:k]


USER = {"tenant": "A", "level": 2}
gold = {c["id"] for c in chunks if c["id"].startswith("gold")}
pool = [c for c in chunks if c["tenant"] == USER["tenant"] and c["level"] <= USER["level"]]


def run(name, ranked, returned_note=""):
    got = {c["id"] for c in ranked}
    leak = sum(1 for c in ranked if c["tenant"] != USER["tenant"] or c["level"] > USER["level"])
    print(f"{name:<22}{len(ranked):>6}{len(gold & got):>8}/5{leak:>8}{returned_note}")


print(f"用户 tenant=A level=2；语料 240 块，其中 A 租户可见 {len(pool)} 块，黄金块 5 条。")
print(f"{'配置':<20}{'返回':>6}{'黄金命中':>10}{'越权':>8}")

run("① 不过滤", rank(chunks, 10))
cand = rank(chunks, 60)
post = [c for c in cand if c["tenant"] == "A" and c["level"] <= 2][:10]
run("② 先取后删(post)", post)
run("③ 先删后取(pre)", rank(pool, 10))

cached = rank([c for c in chunks if c["tenant"] == "B"], 6)
print(f"{'④ 缓存键漏租户':<18}{len(cached):>6}{0:>8}/5{len(cached):>8}  <- B 的结果发给 A")

pre = rank(pool, 10)
cand200 = rank(chunks, 60)
polluted = sum(1 for c in cand200 if c["tenant"] != "A" or c["level"] > 2) / len(cand200)

print(f"\npost-filter 的候选集里 {polluted:.0%} 是无权块：它们不占最终返回，但占掉了排序预算。")
print("候选池固定 60 条时，B 租户的高分块把 A 的相关块挤出了池子——这叫『过滤后召回塌陷』。")
pregold = len(gold & {c["id"] for c in post})
print(f"post-filter 只返回 {len(post)} 条而不是 10 条，且黄金命中 {pregold}/5；")
print("\n读法：pre-filter 把权限条件下推成索引过滤（租户分区 + 密级数值范围），")
print("代价是每路召回都要带过滤条件，索引要支持按元数据裁剪，否则会退化成全量扫描。")
print("缓存那条更致命：泄漏 6 条、0 条命中，而且日志上看一切正常。")
print("\n结论：权限过滤只有一种正确位置——检索之前。缓存键必须包含 tenant_id、密级上限、")
print("以及权限版本号（用户被降权后旧缓存要立刻失效）；三者缺一，越权就是时间问题。")
