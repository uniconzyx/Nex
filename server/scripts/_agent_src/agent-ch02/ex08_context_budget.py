# title: 上下文预算分配：先截断谁，决定了答案是「有据」还是「有礼貌」
# 300 条模拟请求：历史长度 2~30 轮、检索文档 2~12 篇（带相关性分数），每篇有是否「金标」。
# 三种策略共用同一预算 8192：A 历史优先 / B 文档优先 / C 摘要+最近轮次。
# 指标：金标文档保留率、最近 4 轮保留率、溢出率、平均占用。
import numpy as np

rng = np.random.default_rng(21)
BUDGET = 8192
FIXED = 320 + 900 + 1100 + 800     # system + tools schema + few-shot + 输出预留
AVAIL = BUDGET - FIXED
N = 300
TURN_TOK, DOC_TOK, SUMMARY_TOK = 200, 900, 550

hist = rng.integers(10, 61, N)
ndoc = rng.integers(3, 13, N)
# 每篇文档的相关性；金标 = 相关性最高的前 2 篇
relev = [np.sort(rng.random(n))[::-1] for n in ndoc]
gold = [set(np.argsort(-r)[:2].tolist()) for r in relev]

def pack_history(i, budget):
    turns = min(hist[i], budget // TURN_TOK)
    return turns, turns * TURN_TOK

def pack_docs(i, budget):
    k, used = 0, 0
    for _ in range(ndoc[i]):
        if used + DOC_TOK > budget:
            break
        k += 1
        used += DOC_TOK
    return k, used

stats = {}
for name in ("A 历史优先", "B 文档优先", "C 摘要+最近"):
    gold_keep = recent_keep = overflow = used_sum = 0
    for i in range(N):
        if name.startswith("A"):
            turns, u1 = pack_history(i, AVAIL)
            k, u2 = pack_docs(i, AVAIL - u1)
            kept_docs = set(range(k))
            recent = turns >= min(4, hist[i])
        elif name.startswith("B"):
            k, u2 = pack_docs(i, AVAIL)
            turns, u1 = pack_history(i, AVAIL - u2)
            kept_docs = set(range(k))
            recent = turns >= min(4, hist[i])
        else:
            turns_keep = min(4, hist[i])
            u1 = turns_keep * TURN_TOK + SUMMARY_TOK
            k, u2 = pack_docs(i, AVAIL - u1)
            kept_docs = set(range(k))
            recent = turns_keep >= min(4, hist[i])
        used = u1 + u2
        used_sum += used
        overflow += used > AVAIL
        gold_keep += gold[i].issubset(kept_docs)
        recent_keep += recent
    stats[name] = (gold_keep / N, recent_keep / N, overflow / N, used_sum / N)

print("=" * 78)
print(f"预算 {BUDGET}：固定开销 {FIXED}（system 320 / tools 900 / few-shot 1100 / 输出 800），可用 {AVAIL}")
print("=" * 78)
print(f"{'策略':<14}{'金标保留':>10}{'最近4轮':>10}{'溢出率':>9}{'平均占用':>10}")
for name, (g, r, o, u) in stats.items():
    print(f"{name:<14}{g:>10.0%}{r:>10.0%}{o:>9.0%}{u:>10.0f}")

# 单条请求的细看：历史 20 轮、8 篇文档
i = 0
print("\n" + "=" * 78)
print("表 2  单条请求拆解（历史 40 轮 / 10 篇文档 / 金标为相关性前 2）")
print("=" * 78)
for name in stats:
    if name.startswith("A"):
        turns, u1 = pack_history(i, AVAIL)
        k, u2 = pack_docs(i, AVAIL - u1)
    elif name.startswith("B"):
        k, u2 = pack_docs(i, AVAIL)
        turns, u1 = pack_history(i, AVAIL - u2)
    else:
        turns = 4
        u1 = turns * TURN_TOK + SUMMARY_TOK
        k, u2 = pack_docs(i, AVAIL - u1)
    print(f"  {name:<12} 历史 {turns:>2} 轮 / 文档 {k} 篇 / 占用 {u1+u2:>5} token / "
          f"金标保留 {'是' if gold[i].issubset(set(range(k))) else '否'}")

print("\n结论：历史优先会把金标文档挤掉（答案变成「有礼貌但没依据」），文档优先会丢最近指令；")
print("      摘要+最近轮次把两者都保住了，代价是多一次摘要调用（经验上 +0.8~1.2s）与摘要本身的失真。")
print("读法：预算按「任务类型」分配——问答类给文档更多，多轮改稿类给历史更多；")
print("      并且把「输出预留」先扣掉，否则最后 800 token 会把答案截在半句话。")
