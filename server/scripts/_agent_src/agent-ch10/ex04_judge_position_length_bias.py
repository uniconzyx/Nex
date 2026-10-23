# title: LLM-as-judge 偏差体检：位置翻转率与长度相关的量化模拟
import numpy as np

rng = np.random.default_rng(0)
# 本地模拟 judge（不是真实模型）：score = 内容质量 + 位置加成 + 长度加成。
# 研究 judge 本身的偏差，正是「judge 也要被评估」的落地方式。
POS_BONUS = 0.30          # 先出现的答案 +0.30
LEN_COEF = 0.50           # 每多 100 字 +0.50（相对 200 字基线）
LEN_CAP = 1.50            # 长度加成封顶
ADMIT = {"flip": 0.10, "rho": 0.30}   # 准入线（经验判断）


def len_bonus(length):
    return min(LEN_CAP, max(0.0, LEN_COEF * (length - 200) / 100))


def compare(sa, sb):
    return "A" if sa > sb else ("B" if sb > sa else "tie")


def judge_pair(qa, qb, la, lb, order):
    """成对比较：order='AB' 表示 A 在 prompt 里先出现。"""
    sa, sb = qa + len_bonus(la), qb + len_bonus(lb)
    sa += POS_BONUS if order == "AB" else 0.0
    sb += POS_BONUS if order == "BA" else 0.0
    return compare(sa, sb)


def judge_score(q, length):
    """单打分口径（无位置变量），用于长度相关分析。"""
    return q + len_bonus(length)


def spearman(x, y):
    rx = np.argsort(np.argsort(np.asarray(x, dtype=float)))
    ry = np.argsort(np.argsort(np.asarray(y, dtype=float)))
    return float(np.corrcoef(rx, ry)[0, 1])


def swap_avg_winner(qa, qb, la, lb):
    """缓解手段：同一对评两次（AB 与 BA），位置加成一正一负被平均抵消。"""
    sa_ab, sb_ab = qa + len_bonus(la) + POS_BONUS, qb + len_bonus(lb)
    sa_ba, sb_ba = qa + len_bonus(la), qb + len_bonus(lb) + POS_BONUS
    return compare((sa_ab + sa_ba) / 2, (sb_ab + sb_ba) / 2)


N = 400
cases = [(float(rng.normal()), float(rng.normal()),
          int(rng.integers(100, 600)), int(rng.integers(100, 600))) for _ in range(N)]

# 1) 位置偏差：交换 A/B 顺序后的翻转率，按质量差分桶
buckets = [("|dq|<0.3", 0, 0), ("0.3<=|dq|<1.0", 0, 0), ("|dq|>=1.0", 0, 0)]
flip_total = 0
for c in cases:
    f = judge_pair(*c, "AB") != judge_pair(*c, "BA")
    flip_total += int(f)
    dq = abs(c[0] - c[1])
    key = 0 if dq < 0.3 else (1 if dq < 1.0 else 2)
    buckets[key] = (buckets[key][0], buckets[key][1] + 1, buckets[key][2] + int(f))
flip_rate = flip_total / N

print("== 1) 位置偏差：交换 A/B 顺序后 judge 结论翻转的比例 ==")
for name, tot, f in buckets:
    print(f"  质量差 {name:<14} 翻转 {f:>3}/{tot:<3} = {f / tot:>5.0%}")
print(f"总体翻转率 = {flip_rate:.0%}（准入线 {ADMIT['flip']:.0%}）-> {'超标' if flip_rate > ADMIT['flip'] else '达标'}")
print("-> 「新版本胜率 78%」这类结论，先扣掉位置偏差再解读；质量越接近，位置越能左右结论")

# 2) 缓解：交换取平均后，位置加成被精确抵消；长度加成与顺序无关，仍然保留
avg_disagree = sum(swap_avg_winner(*c) != judge_pair(*c, "AB") for c in cases) / N
len_driven = sum(swap_avg_winner(*c) != compare(c[0], c[1]) for c in cases) / N
print("\n== 2) 缓解效果：交换位置取平均 ==")
print(f"  单序判定中 {flip_rate:.0%} 的结论由位置决定（交换即翻转）")
print(f"  交换取平均后：判定与顺序完全解耦（顺序敏感性 0%），"
      f"与单序(AB)判定不一致的 {avg_disagree:.0%} 即被位置加成扭曲、经平均后纠正的判定")
print(f"  但仍有 {len_driven:.0%} 的判定由长度加成翻盘（与纯内容判定不一致）——长度偏差未被交换缓解")

# 3) 长度偏差：单打分与长度的 Spearman 相关
lengths = [c[2] for c in cases]
scores = [judge_score(c[0], c[2]) for c in cases]
rho_len = abs(spearman(lengths, scores))
print(f"\n== 3) 长度偏差：judge 分数 vs 答案长度 |Spearman| = {rho_len:.2f}"
      f"（准入线 {ADMIT['rho']:.2f}）-> {'超标' if rho_len > ADMIT['rho'] else '达标'}")

# 4) 具体失效案例：内容更差但更长的答案赢了
qa, la, qb, lb = 0.60, 500, 0.95, 150
print("\n== 4) 失效案例：长而差的答案击败短而好的答案 ==")
print(f"  A: 质量 {qa}, 长度 {la} 字 -> judge 分 {judge_score(qa, la):.2f}")
print(f"  B: 质量 {qb}, 长度 {lb} 字 -> judge 分 {judge_score(qb, lb):.2f}")
print(f"  judge 判定赢家 = {judge_pair(qa, qb, la, lb, 'AB')}"
      f"（内容上 B 更好，长度加成 {len_bonus(la):.2f} 反超）")

# 5) 准入结论
ok = flip_rate <= ADMIT["flip"] and rho_len <= ADMIT["rho"]
print(f"\n== 5) 准入判定：翻转率 {flip_rate:.0%}、长度相关 {rho_len:.2f} -> "
      f"{'可进门禁' if ok else '仅可粗筛/排序参考，正式门禁退回人工或规则判据'} ==")

print("\n结论：该模拟 judge 有明确的位置偏差与长度偏差，直接用于回归门禁会把「位置赢」「长度赢」当成「质量赢」；")
print("读法：1. 位置偏差用交换 A/B 顺序的翻转率量化，交换取平均是模型无关、零成本的缓解；2. 长度偏差用分数-长度 Spearman 相关量化，prompt 去偏与长度归一需重测验证有效性；3. 缓解一项偏差不会自动修复另一项，准入是多项指标的合取；4. 本示例为本地模拟 judge，不调用任何真实 API，偏差参数是构造出来的教学值，真实 judge 还有自我偏好与格式偏好待测。")
