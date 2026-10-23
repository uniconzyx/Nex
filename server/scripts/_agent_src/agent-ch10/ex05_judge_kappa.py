# title: judge 校准实验：raw agreement 93.3% 为什么 kappa 只有 0.30
import numpy as np

rng = np.random.default_rng(1)
N = 60   # 校准集规模：50~100 条人工双标样本


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def cohens_kappa(a, b):
    """两份类别标注（0/1 序列）的 Cohen's kappa：扣除随机一致后的净一致。"""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    a1, b1 = sum(a) / n, sum(b) / n
    pe = a1 * b1 + (1 - a1) * (1 - b1)
    return po, pe, (po - pe) / (1 - pe)


def spearman(x, y):
    rx = np.argsort(np.argsort(np.asarray(x, dtype=float)))
    ry = np.argsort(np.argsort(np.asarray(y, dtype=float)))
    return float(np.corrcoef(rx, ry)[0, 1])


# ---- 1) 60 条校准样本：真值质量 q，人工终判（含标注噪声），judge 分数（含打分噪声）
q = rng.normal(size=N)                       # 真实质量（不可见，仅用于生成标注）
human_score = q + rng.normal(scale=0.30, size=N)     # 人工 1-5 分量表的连续代理
judge_score = q + rng.normal(scale=0.55, size=N)     # judge 分数噪声更大
human_bin = [1 if h > 0 else 0 for h in human_score]
judge_bin = [1 if j > 0.40 else 0 for j in judge_score]   # judge 阈值偏严（未校准）

po, pe, kappa = cohens_kappa(human_bin, judge_bin)
rho = spearman(human_score, judge_score)

print("== 1) 60 条校准样本上 judge vs 人工 ==")
print(f"  人工判「好」{sum(human_bin)}/{N}，judge 判「好」{sum(judge_bin)}/{N}")
print(f"  raw agreement（观测一致率） = {po:.1%}")
print(f"  p_e（随机一致率，由边际分布决定） = {pe:.1%}")
print(f"  Cohen's kappa = ({po:.3f} - {pe:.3f}) / (1 - {pe:.3f}) = {kappa:.2f}")
print(f"  Spearman rho（judge 分数 vs 人工均分） = {rho:.2f}")
print(f"  准入线：kappa >= 0.60 且 rho >= 0.70 -> "
      f"{'可进门禁' if kappa >= 0.60 and rho >= 0.70 else '仅可粗筛，不进门禁'}")

# ---- 2) 极偏边际下的陷阱：raw agreement 很高，kappa 很低（可手算复核）
print("\n== 2) 极偏边际案例：为什么 raw agreement 会骗人 ==")
# 构造 2x2：人工 57 好/3 坏，judge 57 好/3 坏，其中 2 条判反
tp, fp, fn, tn = 55, 2, 2, 1
n = tp + fp + fn + tn
po2 = (tp + tn) / n
pe2 = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
k2 = (po2 - pe2) / (1 - pe2)
print(f"  人工好 {tp + fp} / 坏 {fn + tn}；judge 好 {tp + fn} / 坏 {fp + tn}")
print(f"  raw agreement = {po2:.1%}，但 kappa = ({po2:.3f}-{pe2:.3f})/(1-{pe2:.3f}) = {k2:.2f}")
print("  类别越不均衡，随手标都能有很高的 raw agreement——验收必须看 kappa，不能看一致率")

# ---- 3) judge 版本漂移：v2 = v1 + 0.5，排序不变但绝对门禁失真
print("\n== 3) judge 静默升级：尺子整体缩了/涨了 0.5 分 ==")
judge_v2 = [j + 0.5 for j in judge_score]
rho2 = spearman(human_score, judge_v2)
gate_v1 = sum(1 for j in judge_score if j > 0.40) / N
gate_v2 = sum(1 for j in judge_v2 if j > 0.40) / N
print(f"  升级后 Spearman = {rho2:.2f}（与升级前 {rho:.2f} 几乎相同——秩相关对平移不敏感）")
print(f"  但「judge 分 > 0.40 即通过」的通过率从 {gate_v1:.0%} 涨到 {gate_v2:.0%}")
print("  -> 绝对门禁阈值失真：历史版本对比全部作废，必须重跑校准集并迁移基线")
print("  -> 对策：judge 三要素（模型版本+prompt hash+温度）进报告页眉；主门禁用成对比较口径")

# ---- 4) 共同偏差提醒
print("\n== 4) 一致 != 正确：共同偏差检查 ==")
agree = sum(a == b for a, b in zip(human_bin, judge_bin))
wrong_together = sum(1 for a, b, qq in zip(human_bin, judge_bin, q)
                     if a == b and a != (1 if qq > 0 else 0))
print(f"  一致 {agree} 条，其中与真值质量符号不符的 {wrong_together} 条")
print("  judge 与人工标注可能一起错（同类幻觉、同类偏好）——校准集必须独立于被测系统训练数据")

print("\n结论：该 judge 的 kappa 与 rho 均低于准入线，只能用于粗筛；升级造成的分数平移还会 silently 破坏绝对门禁；")
print("读法：1. kappa 扣除随机一致，类别极偏时 raw agreement 虚高，必须以 kappa 为准；2. Spearman 对分数平移不敏感，版本迁移要同时看绝对分差；3. 一致不等于正确，需抽查共同偏差；4. 本示例用程序化生成的 60 条模拟标注，人工标注流程（双标+仲裁）在真实项目中不可省略。")
