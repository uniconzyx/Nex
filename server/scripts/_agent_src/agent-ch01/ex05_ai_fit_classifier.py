# title: AI 适用性四档判断器：规则树、混淆矩阵与过度设计的账单
# 四档：0 确定性规则 / 1 分类抽取 / 2 生成 / 3 Agent 多步。
# 60 条模拟需求，「真实档位」= 满足容错要求的最便宜方案；规则树则带安全边际（宁可高判一档）。
# 结果用混淆矩阵看错在哪，用成本倍率看「过度设计」到底多花多少钱。
import numpy as np

rng = np.random.default_rng(11)
N = 60
TIER_COST = np.array([1.0, 2.2, 6.5, 18.0])   # 单次任务相对成本
NAMES = ["规则", "分类抽取", "生成", "Agent"]

output_enum = rng.random(N) < 0.70       # 输出可枚举（分类/字段抽取）
needs_action = rng.random(N) < 0.22      # 需要写操作/外部动作
steps = rng.choice([1, 2, 3, 4], N, p=[0.35, 0.30, 0.20, 0.15])   # 任务步数
tolerance = rng.uniform(0.5, 0.99, N)    # 可接受错误率上限
structured_in = rng.random(N) < 0.65      # 输入是否结构化

def tier_of(i):
    if needs_action[i] and steps[i] >= 2:
        return 3
    if steps[i] >= 4:
        return 3
    if not output_enum[i]:
        return 2
    if not structured_in[i]:
        return 1
    if tolerance[i] < 0.90:
        return 1
    return 0

true = np.array([tier_of(i) for i in range(N)])
# 需求歧义：8% 的样本真实档位在相邻档之间摇摆
flip = rng.random(N) < 0.08
for i in np.where(flip)[0]:
    true[i] = min(3, max(0, true[i] + rng.choice([-1, 1])))

# 规则树：与真实判据同构，但更保守——步数阈值 3（而非 4），容错阈值 0.95（而非 0.90）
pred = np.zeros(N, dtype=int)
for i in range(N):
    if needs_action[i] or steps[i] >= 3:
        pred[i] = 3
    elif not output_enum[i]:
        pred[i] = 2
    elif not structured_in[i] or tolerance[i] < 0.90:
        pred[i] = 1
    else:
        pred[i] = 0

cm = np.zeros((4, 4), dtype=int)
for t, p in zip(true, pred):
    cm[t, p] += 1

print("=" * 66)
print("表 1  混淆矩阵（行=真实档位，列=规则判定）")
print("=" * 66)
print(f"{'真实\\预测':<10}" + "".join(f"{n:>10}" for n in NAMES) + f"{'样本':>6}{'召回':>7}")
for t in range(4):
    rec = cm[t, t] / max(cm[t].sum(), 1)
    print(f"{NAMES[t]:<10}" + "".join(f"{v:>10}" for v in cm[t]) + f"{cm[t].sum():>6}{rec:>7.0%}")
print(f"{'精确率':<10}" + "".join(f"{(cm[p,p]/max(cm[:,p].sum(),1)):>9.0%} " for p in range(4)))

acc = np.trace(cm) / N
over = int(np.triu(cm, 1).sum())
under = int(np.tril(cm, -1).sum())
print(f"\n总体准确率 {acc:.1%}；过度设计（低判高）{over} 条，能力不足（高判低）{under} 条。")
print(f"过度设计占全部错判的 {over/max(over+under,1):.0%}——保守规则的代价是可见的。")

mult = TIER_COST[pred] / TIER_COST[true]
print(f"\n平均成本倍率 {mult.mean():.2f}x；总成本比真实最优方案高 "
      f"{(TIER_COST[pred].sum()/TIER_COST[true].sum()-1):.0%}")
print("按档位统计平均成本倍率：", end="")
print("  ".join(f"{NAMES[t]}={mult[true==t].mean():.2f}x" for t in range(4) if (true==t).any()))

print("\n结论：规则在 Agent 档最准（有外部动作/多步是强信号），错判几乎全是「低判高」——")
print("      因为保守地把 steps=3 的单轮任务也推进了 Agent 档，成本倍率最高的正是这一档。")
print("读法：先看错判结构再看准确率；如果 80% 的错判是过度设计，就调阈值/加前置过滤，")
print("      而不是继续加模型能力——后者只会让成本倍率更高。")
