# title: 岗位匹配度余弦打分：为什么「技能数量」会骗人
# 候选人在 12 个技能维度上自评 0-5；5 条 JD 给出「必须项(权重 3)」和「加分项(权重 1)」。
# 同时算加权余弦与覆盖率，并做「补一项技能」的边际收益分析。
import numpy as np

DIMS = ["Python", "工程化", "LLM 原理", "Prompt", "RAG", "Agent", "评测",
        "部署", "数据", "产品", "业务沟通", "算法"]
CAND = np.array([4, 3, 2, 4, 3, 2, 2, 2, 3, 1, 2, 2], dtype=float)

JDS = {
    "LLM 应用开发": ({"Python": 3, "工程化": 3, "Prompt": 2, "RAG": 2, "部署": 1, "数据": 1}),
    "Agent 工程": ({"Python": 3, "Agent": 3, "Prompt": 2, "评测": 2, "工程化": 2, "部署": 1}),
    "算法工程师": ({"Python": 3, "算法": 3, "LLM 原理": 3, "数据": 1, "工程化": 1}),
    "AI 产品经理": ({"产品": 3, "业务沟通": 3, "数据": 2, "Prompt": 1, "LLM 原理": 1}),
    "解决方案": ({"业务沟通": 3, "部署": 2, "工程化": 2, "产品": 1, "Python": 1, "数据": 1}),
}

def vec(spec):
    v = np.zeros(len(DIMS))
    for k, w in spec.items():
        v[DIMS.index(k)] = w
    return v

print("=" * 68)
print("候选人自评：", dict(zip(DIMS, CAND.astype(int).tolist())))
print("=" * 68)
print(f"{'岗位':<14}{'余弦':>7}{'覆盖率':>8}{'加权缺口':>9}  最该补的一项")
scores = []
for name, spec in JDS.items():
    j = vec(spec)
    cos = float(CAND @ j / (np.linalg.norm(CAND) * np.linalg.norm(j) + 1e-12))
    need = sum(spec.values())
    got = sum(min(CAND[DIMS.index(k)], 5) * w for k, w in spec.items())
    cover = got / (5 * need)
    # 加权缺口：把候选人补到 4 分能补上的缺口
    gains = {k: (min(4, 5) - CAND[DIMS.index(k)]) * w
             for k, w in spec.items() if CAND[DIMS.index(k)] < 4}
    best = max(gains.items(), key=lambda kv: kv[1])[0] if gains else "无"
    gap = sum((4 - CAND[DIMS.index(k)]) * w for k, w in spec.items()
              if CAND[DIMS.index(k)] < 4)
    scores.append((cos, name))
    print(f"{name:<14}{cos:>7.3f}{cover:>8.1%}{gap:>9.1f}  {best}")

scores.sort(reverse=True)
print("\n排序：" + " > ".join(f"{n}({c:.3f})" for c, n in scores))

top = scores[0][1]
print("\n" + "=" * 68)
print(f"边际分析：向「{top}」投递前，补哪一项最划算（每 +1 分带来的余弦增量）")
print("=" * 68)
j = vec(JDS[top])
base = CAND @ j / (np.linalg.norm(CAND) * np.linalg.norm(j))
gains = []
for i, d in enumerate(DIMS):
    if CAND[i] >= 4 or d not in JDS[top]:
        continue
    c2 = CAND.copy()
    c2[i] += 1
    gains.append((c2 @ j / (np.linalg.norm(c2) * np.linalg.norm(j)) - base, d))
for g, d in sorted(gains, reverse=True):
    print(f"  +1 {d:<10} Δcos = {g:+.4f}")

print("\n结论：余弦被「维度数量」稀释——技能写得越全，单项缺失越不敏感；")
print("      覆盖率会高估（自评 3 分也算覆盖），必须同时看加权缺口。")
print("读法：匹配度低时先补 JD 的必须项，不要用「再多学一个工具」掩盖核心维度缺失。")
