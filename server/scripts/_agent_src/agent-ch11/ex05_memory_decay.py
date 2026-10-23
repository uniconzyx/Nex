# title: 长期记忆的写入、检索与衰减：重要度与遗忘曲线的权衡
# 本地模拟：词袋向量模拟嵌入 + 衰减打分，不调用真实 LLM/向量库。
import numpy as np

rng = np.random.default_rng(7)
VOCAB = [f"w{i:02d}" for i in range(20)]
HALF = len(VOCAB) // 2


def vec(words):
    """词袋 one-hot 模拟嵌入（真实系统是 embedding 模型，见 ai 学科）。"""
    v = np.zeros(len(VOCAB))
    for w in words:
        v[VOCAB.index(w)] = 1.0
    return v


def cos(a, b):
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / d) if d else 0.0


# ---------- 1) 写入：三类记忆（重要度 x 年龄 的四种组合） ----------
def add_bank(n, kind, imp, age, pool):
    for i in range(n):
        words = list(rng.choice(pool, size=3, replace=False))
        memories.append({"text": f"{kind}-{i:02d}", "vec": vec(words), "imp": imp, "age": age})


memories = []
add_bank(12, "旧重要", 0.90, 30, VOCAB[:HALF])    # 重要但旧
add_bank(12, "新琐碎", 0.15, 1, VOCAB[HALF:])     # 琐碎但新
add_bank(8, "旧琐碎", 0.15, 30, VOCAB[:HALF])     # 既旧又不重要（清理候选）

# ---------- 2) 查询：一半指向旧重要记忆，一半指向新琐碎记忆 ----------
# 每个查询 = 目标 3 词 + 2 个来自另一半词表的噪声词（保证与对手类记忆有低相似度重叠）
queries = []
for m in [x for x in memories if x["text"].startswith("旧重要")]:
    qv = m["vec"] + vec([str(rng.choice(VOCAB[HALF:])) for _ in range(2)])
    queries.append({"q": qv, "target": m["text"], "kind": "旧重要"})
for m in [x for x in memories if x["text"].startswith("新琐碎")]:
    qv = m["vec"] + vec([str(rng.choice(VOCAB[:HALF])) for _ in range(2)])
    queries.append({"q": qv, "target": m["text"], "kind": "新琐碎"})


def retrieve(q, lam):
    """打分 = 余弦相似度 x 重要度 x 时间衰减 exp(-lam*age)，返回降序列表。"""
    scored = [(cos(q, m["vec"]) * m["imp"] * float(np.exp(-lam * m["age"])), m) for m in memories]
    scored.sort(key=lambda x: -x[0])
    return scored


print("== 不同衰减系数 lambda 下的 top-1 命中率（共 24 个查询） ==")
print(f"{'lambda':>7}{'旧重要 命中':>12}{'新琐碎 命中':>12}{'总 top-1':>10}")
rows = {}
for lam in (0.0, 0.03, 0.05, 0.08, 0.3):
    hit_old = hit_new = 0
    for item in queries:
        top1 = retrieve(item["q"], lam)[0][1]["text"]
        if top1 == item["target"]:
            if item["kind"] == "旧重要":
                hit_old += 1
            else:
                hit_new += 1
    rows[lam] = (hit_old, hit_new)
    print(f"{lam:>7.2f}{hit_old:>9}/12{hit_new:>9}/12{(hit_old + hit_new) / 24:>9.1%}")

# U 型曲线两端：不衰减时新事实被旧重要记忆淹没；过衰减时旧重要事实被遗忘
assert rows[0.0][1] < 12 and rows[0.3][0] < 12 and rows[0.05] == (12, 12)

# ---------- 3) 遗忘执行：清理「年龄大且不重要」的记忆 ----------
lam = 0.02
THRESH = 0.1
kept = [m for m in memories if m["imp"] * float(np.exp(-lam * m["age"])) >= THRESH]
pruned = [m for m in memories if m not in kept]
print(f"\n== 遗忘执行（lambda={lam}，清理 重要度x衰减 < {THRESH} 的记忆） ==")
print(f"库规模 {len(memories)} -> {len(kept)}；清理 {len(pruned)} 条，全部是「旧琐碎」：{sorted({m['text'][:3] for m in pruned})}")
assert len(kept) == 24 and all(m["text"].startswith("旧琐碎") for m in pruned)

# 竞争案例：双命中查询（同时含旧重要与新琐碎的词），看 top1 随 lambda 翻转
m_old, m_new = memories[0], memories[12]
q_both = m_old["vec"] + m_new["vec"]
print("\n== 双命中查询的 top1 翻转（旧重要 vs 新琐碎） ==")
for lam in (0.0, 0.05, 0.1, 0.3):
    top = retrieve(q_both, lam)[0][1]["text"]
    print(f"lambda={lam:>4.2f}：top1 = {top}")

print("\n结论：长期记忆的排序 = 相似度 x 重要度 x 衰减，三个因子缺一个都会坏，")
print("读法：1. lambda=0 不衰减：旧重要记忆凭重要度霸榜，新事实被淹没，top-1 对新查询仅五成；2. lambda=0.3 过衰减：旧重要事实分数归零，检索只认得新琐碎，「学过的东西忘了」；3. 中间存在甜点档（本例 0.05 附近两头全中）——衰减要按记忆重要度分档，不是全局一个 lambda（经验判断）；4. 清理策略应针对「旧且不重要」：重要度x衰减低于阈值的才删，避免误删高价值旧记忆；5. 本示例用词袋向量模拟嵌入，真实检索用向量数据库 + 嵌入模型，但打分公式同构。")
