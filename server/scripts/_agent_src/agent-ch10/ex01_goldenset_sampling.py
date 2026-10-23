# title: 黄金集分层抽样与覆盖度：为什么 demo 通过率不能当验收指标
import numpy as np

rng = np.random.default_rng(7)

# 线上流量占比（用于回加权），与分层配额相互独立
TRAFFIC_W = {"查询": 0.50, "计算": 0.20, "创作": 0.15, "拒答": 0.10, "多轮": 0.05}
QUOTA = {  # (意图, 难度): 样本配额，难例集中往高难度层倾斜
    ("查询", "易"): 8, ("查询", "难"): 5,
    ("计算", "易"): 5, ("计算", "难"): 6,
    ("创作", "易"): 5, ("创作", "难"): 5,
    ("拒答", "易"): 4, ("拒答", "难"): 4,
    ("多轮", "易"): 4, ("多轮", "难"): 4,
}


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def gen_goldenset():
    """按配额程序化生成 50 条黄金样本（固定种子，可复现）。"""
    samples = []
    i = 0
    for (intent, diff), n in QUOTA.items():
        for _ in range(n):
            is_hard = diff == "难" or rng.random() < 0.15  # 难例：高难度层 + 15% 简单层
            # 知识依赖第三维：独立知识 / 依赖文档 / 依赖工具
            know = ["独立", "文档", "工具"][rng.integers(0, 3)]
            # 模拟系统在该层的通过概率：高难度与难例显著更低
            p = 0.86 if diff == "易" else 0.55
            if is_hard:
                p -= 0.18
            correct = int(rng.random() < p)
            samples.append(dict(id=f"g{i:03d}", intent=intent, diff=diff,
                                know=know, hard=is_hard, correct=correct))
            i += 1
    return samples


def coverage_table(samples):
    rows = {}
    for s in samples:
        key = (s["intent"], s["diff"])
        n, h, hit = rows.get(key, (0, 0, 0))
        rows[key] = (n + 1, h + int(s["hard"]), hit + s["correct"])
    return rows


def weighted_acc(samples):
    """按线上流量占比回加权：先按 (意图,难度) 算层内准确率，再加权求和。"""
    rows = coverage_table(samples)
    num = den = 0.0
    for (intent, _), (n, _, hit) in rows.items():
        w = TRAFFIC_W[intent] / sum(1 for (i2, _) in QUOTA if i2 == intent)
        num += w * hit / n
        den += w
    return num / den


samples = gen_goldenset()
rows = coverage_table(samples)
total = len(samples)
hard_n = sum(s["hard"] for s in samples)
raw = sum(s["correct"] for s in samples) / total
w_acc = weighted_acc(samples)

print("== 1) 分层覆盖度表（50 条黄金集） ==")
print(f"{pad('意图x难度', 14)}{'样本数':>6}{'难例数':>6}{'难例占比':>8}{'层内准确率':>10}")
for (intent, diff), (n, h, hit) in rows.items():
    print(f"{pad(intent + 'x' + diff, 14)}{n:>6}{h:>6}{h / n:>8.0%}{hit / n:>10.1%}")
print(f"合计 {total} 条，难例 {hard_n} 条（占比 {hard_n / total:.0%}，要求 >=30%）")

print("\n== 2) 知识依赖第三维的覆盖 ==")
for know in ("独立", "文档", "工具"):
    k = [s for s in samples if s["know"] == know]
    print(f"  {know}: {len(k)} 条，正确 {sum(s['correct'] for s in k)} 条")

print("\n== 3) 原始准确率 vs 回加权准确率 ==")
print(f"原始（难例被 oversampling，有偏）= {raw:.1%}")
print(f"回加权（按线上流量占比）       = {w_acc:.1%}")
print(f"两者差 {abs(raw - w_acc) * 100:.1f} 个百分点 —— 难例占比越高，不回加权的报告越偏保守/偏激")

print("\n== 4) 反面对照：若按 demo 方便采样（只留各意图的简单层） ==")
demo = [s for s in samples if s["diff"] == "易"]
demo_raw = sum(s["correct"] for s in demo) / len(demo)
missing = sorted({k for k in QUOTA if k[1] == "难"})
print(f"demo 集 {len(demo)} 条，原始准确率 {demo_raw:.1%}（比全集 {raw:.1%} 高 {(demo_raw - raw) * 100:.1f} 个百分点）")
print(f"但丢掉了这些层的覆盖: {['x'.join(k) for k in missing]}")
print("丢层 = 盲区：五个高难度层整体不可见，拒答/多轮的难例全军覆没也被平均掉")

print("\n结论：黄金集的合格线先是覆盖度（每格有样本、难例 >=30%、含拒答层），其次才是准确率数字；")
print("读法：1. 分层配额按「线上流量 + 难例加权」设计，报告准确率必须回加权，否则 oversampling 会让指标有偏；2. 反面对照显示方便采样会把分数抬高、同时制造指标盲区；3. 本示例用程序化生成的 50 条模拟样本，真实黄金集还应带判定口径与版本号，样本增删必须可追溯。")
