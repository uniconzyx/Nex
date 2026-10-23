# title: 论文价值评分卡：四维加权、三档处置与权重敏感性
# 维度与权重（经验判断）：可复现性 0.30 / 影响面 0.25 / 相关度 0.30 / 时效 0.15。
# 论文均为真实存在的著名工作；评分为教学用主观值（经验判断），仅演示评分卡结构。

WEIGHTS = {"repro": 0.30, "impact": 0.25, "rel": 0.30, "rec": 0.15}

PAPERS = [
    # (论文, 可复现性, 影响面, 相关度, 时效)
    ("Attention Is All You Need (2017)",            3, 5, 4, 5),
    ("Adam: A Method for Stochastic Optimization",  4, 5, 3, 4),
    ("LoRA: Low-Rank Adaptation of LLMs",           5, 5, 4, 4),
    ("Language Models are Few-Shot Learners",       2, 5, 3, 3),
    ("Chain-of-Thought Prompting Elicits Reasoning", 4, 4, 3, 4),
    ("某顶会新架构（教学构造，无代码释出）",          1, 3, 2, 2),
]


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def scorecard(repro, impact, rel, rec):
    total = (WEIGHTS["repro"] * repro + WEIGHTS["impact"] * impact
             + WEIGHTS["rel"] * rel + WEIGHTS["rec"] * rec)
    if total >= 3.5:
        return total, "复现候选"
    if total >= 2.5:
        return total, "精读不復现"
    return total, "只记卡片"


print("== 1) 评分卡（每维 0-5 分）==")
print(f"{pad('论文', 40)}{'复现':>4}{'影响':>4}{'相关':>4}{'时效':>4}{'总分':>7}  处置")
rows = []
for name, a, b, c, d in PAPERS:
    t, action = scorecard(a, b, c, d)
    rows.append((name, t, action))
    print(f"{pad(name, 40)}{a:>4}{b:>4}{c:>4}{d:>4}{t:>7.2f}  {action}")

print("\n== 2) 权重敏感性：四个权重各 ±0.05 后，处置档位是否翻转 ==")
base_w = dict(WEIGHTS)
flips = 0
for key in base_w:
    for delta in (+0.05, -0.05):
        w = dict(base_w)
        w[key] += delta
        for name, a, b, c, d in PAPERS:
            t = w["repro"] * a + w["impact"] * b + w["rel"] * c + w["rec"] * d
            t2, action2 = scorecard(a, b, c, d)
            # 直接用扰动权重重算，与原档位比较
            if (t >= 3.5) != (t2 >= 3.5) or (t >= 2.5) != (t2 >= 2.5):
                flips += 1
                print(f"  权重 {key} {delta:+.2f} 时，「{name}」档位翻转")
print(f"翻转次数 = {flips}（越小说明档位对权重越稳健）")

print("\n== 3) 边界用例：总分恰好压在阈值上 ==")
for case, (a, b, c, d) in {
    "恰好 3.50": (3, 5, 3, 3), "恰好 2.50": (2, 4, 2, 2), "差一点 2.45": (1, 5, 2, 2),
}.items():
    t, action = scorecard(a, b, c, d)
    print(f"  {case}: 总分 {t:.2f} -> {action}")
print("阈值是闭区间（>= 才算上一档）：3.50 与 2.50 判上一档，2.45 判「只记卡片」")

print("\n结论：评分卡把「值不值得复现」变成可复盘的数字，三档处置直接决定投入多少时间，")
print("读法：1. 可复现性权重最高档同相关度（各 0.30）——无代码的论文复现成本高三到五倍，默认降档；2. 处置语义：>=3.5 复现候选（进 project 的复现清单）、2.5-3.5 精读不復现（只做笔记）、<2.5 只记卡片；3. 权重与阈值是经验判断，应按自己的时间成本标定，但「必须有阈值」比「阈值是多少」重要；4. 敏感性分析用来看哪些条目卡在档位边界上——边界条目复查优先级最高。")
