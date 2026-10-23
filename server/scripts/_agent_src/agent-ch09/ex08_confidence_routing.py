# title: 低置信度路由：阈值扫描下的漏过率与兜底率权衡
import numpy as np

rng = np.random.default_rng(0)
FIELDS = ["发票号", "金额", "税率", "开票日期", "销方名称"]
N = 500


def make_batch(n):
    """构造 (置信度, 是否正确) 的字段级样本：正确的普遍高置信，错误的普遍低置信但有重叠。"""
    conf_correct = np.clip(rng.normal(0.88, 0.08, int(n * 0.9)), 0.3, 1.0)
    conf_wrong = np.clip(rng.normal(0.55, 0.18, n - int(n * 0.9)), 0.05, 1.0)
    conf = np.concatenate([conf_correct, conf_wrong])
    correct = np.concatenate([np.ones(int(n * 0.9), bool), np.zeros(n - int(n * 0.9), bool)])
    order = rng.permutation(n)
    return conf[order], correct[order]


conf, correct = make_batch(N)

print("== 阈值扫描：置信度 < tau 进人工，其余自动通过 ==")
print(f"{'阈值tau':>8}{'自动通过率':>10}{'漏过率':>8}{'兜底率':>8}{'兜底中真错占比':>14}")
best = None
for tau in (0.30, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80):
    auto = conf >= tau
    missed = (~auto) & correct          # 被送人工但其实是对的（浪费）
    leaked = auto & (~correct)          # 自动通过但实际错了（事故）
    review = ~auto
    caught = review & (~correct)        # 兜底里真正拦下的错误
    row = (1 - auto.mean(), leaked.sum() / (~correct).sum(), review.mean(),
           caught.sum() / max(review.sum(), 1))
    print(f"{tau:>8.2f}{row[0]:>10.1%}{row[1]:>8.1%}{row[2]:>8.1%}{row[3]:>14.1%}")
    # 业务目标：漏过率（事故）优先压低，同时兜底率（成本）可控
    score = row[1] * 10 + row[2]
    if best is None or score < best[0]:
        best = (score, tau, row)

print(f"\n推荐阈值 tau={best[1]:.2f}：漏过率 {best[2][1]:.1%}、兜底率 {best[2][2]:.1%}")
print("（评分 = 漏过率x10 + 兜底率：错误成本按人工 10 倍计价，权重应按业务重标定）")

# 极限验证：tau=1.0 全兜底（零事故、成本最高）；tau=0 全自动（事故最多）
for tau, tag in ((1.0, "全兜底"), (0.0, "全自动")):
    auto = conf >= tau
    leaked = (auto & (~correct)).sum() / (~correct).sum()
    print(f"{tag}: 漏过率 = {leaked:.1%}")

print("\n结论：阈值不是拍脑袋——它由「自动错误成本 vs 人工成本」的比值决定，且漏过率优先于兜底率，")
print("读法：1. 漏过率 = 自动通过但实际错的比例，是事故指标，要优先压低；2. 兜底率 = 送人工的比例，是成本指标；3. 两率随阈值反向移动，权衡曲线就是选阈值的依据；4. 兜底样本回流成新测试集，防止「修一个坏三个」；5. 本示例用程序化模拟置信度，未调用任何模型。")
