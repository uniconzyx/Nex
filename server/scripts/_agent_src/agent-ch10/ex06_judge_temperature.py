# title: judge 温度实验：同一批评测重复跑三次，结论会变吗
import numpy as np

rng = np.random.default_rng(2)
# judge 是测量仪器，不是创意生成器。本示例量化「judge 自身的随机性」：
# 成对比较中，judge 以 sigmoid(质量差/T) 的概率抽样判定赢家，T=0 时退化为确定性判定。
M = 200      # 案例数（一次回归的成对比较量）
REPS = 50    # 重复实验次数


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def judge_decide(dq, temp, r):
    """dq = 新版本质量 - 旧版本质量；temp=0 时确定性判强的一方。"""
    if temp == 0.0:
        return 1.0 if dq > 0 else 0.0
    p = sigmoid(dq / temp)
    return float(r.random() < p)


def repeat_agreement(dq, temp, r, k=100):
    """同一条案例评 k 次：两次独立评估结论一致的概率（可复现性）。"""
    draws = [judge_decide(dq, temp, r) for _ in range(k)]
    p = float(np.mean(draws))
    return p * p + (1 - p) * (1 - p)


print("== 1) 同一条案例（质量差 0.2）重复评 100 次：可复现性 ==")
print(f"{'温度 T':>8}{'P(判新版本赢)':>14}{'两次独立评估一致率':>20}")
for T in (0.0, 0.5, 1.0):
    p_new = 1.0 if T == 0 else float(sigmoid(0.2 / T))
    agree = repeat_agreement(0.2, T, np.random.default_rng(100 + int(T * 10)))
    print(f"{T:>8.1f}{p_new:>14.2f}{agree:>20.2f}")
print("T=0：judge 输出完全确定，回归可复现；T>0：同一版本两次回归的结论差是 judge 自己的噪声")

# 200 个案例，真实平均提升 3 个百分点（dq ~ N(0.03, 0.5)）
dq = rng.normal(loc=0.03, scale=0.5, size=M)
print("\n== 2) 「新版本胜率」估计：同一批案例重复 50 次实验 ==")
print(f"{'温度 T':>8}{'胜率均值':>10}{'胜率 std':>10}{'95% 波动范围':>18}")
for T in (0.0, 0.5, 1.0):
    rates = []
    for rep in range(REPS):
        r = np.random.default_rng(1000 + rep)   # 每次重复只换 judge 的抽样种子
        rates.append(float(np.mean([judge_decide(d, T, r) for d in dq])))
    rates = np.array(rates)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    print(f"{T:>8.1f}{rates.mean():>10.3f}{rates.std():>10.3f}   [{lo:.3f}, {hi:.3f}]")
print("T=0：50 次重复胜率完全相同（std=0）；T=0.5：std 与真实效应（+3pp）同量级，信号被噪声淹没")
print(f"注：本批案例 T=0 的确定性胜率 {np.mean([d > 0 for d in dq]):.3f} 是样本实现值；"
      f"若案例无限多，总体期望胜率 = Phi(0.03/0.5) = {float(sigmoid(0.03 / 0.5 / np.sqrt(1))):.3f}")

print("\n== 3) 门禁翻转：阈值「胜率 > 0.55 才允许发布」 ==")
for T in (0.0, 0.5, 1.0):
    decisions = []
    for rep in range(REPS):
        r = np.random.default_rng(2000 + rep)
        rate = float(np.mean([judge_decide(d, T, r) for d in dq]))
        decisions.append(rate > 0.55)
    flips = sum(decisions) != len(decisions) and (min(decisions) != max(decisions))
    print(f"  T={T}: 50 次重复中「通过」{sum(decisions)} 次 -> "
          f"{'判定不稳定（同数据结论翻转）' if flips else '判定稳定'}")
print("T>0 时同一批数据能跑出相反的发布结论——这不是系统在波动，是尺子在自己抖")

print("\n== 4) 工程结论 ==")
print("judge 温度固定为 0：测量仪器要求可复现，回归脚本两次跑必须给出同一结论")
print("确需 judge 采样时（如用多次投票估不确定性）：报告 std 与置信区间，且门禁判定用中位数/众数而非单次抽样")

print("\n结论：judge 的随机性是回归流程里最隐蔽的噪声源——T=0 完全可复现，T=0.5 的波动就与 3pp 的真实效应同量级；")
print("读法：1. 可复现性用「同案例两次独立评估的一致率」量化，T=0 时为 1.0；2. 胜率估计的 std 随 T 增大，且高 T 下胜率向 50% 回归，真实提升被稀释；3. 门禁在 T>0 时会对同一批数据给出翻转结论，这是流程缺陷不是模型缺陷；4. 本示例为本地模拟 judge（sigmoid 抽样），不调用任何真实 API。")
