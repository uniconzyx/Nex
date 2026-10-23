# title: 20 条模拟 JD 的技能频率与共现：岗位要求不是一维清单
# 内置 20 条模拟 JD（结构参考真实招聘描述的写法，内容为教学构造）。
# 统计技能频率 Top-N、两两共现的 lift，以及每个岗位最「有区分度」的技能。
from collections import Counter, defaultdict
from itertools import combinations

JDS = [
    ("算法", "大模型算法工程师", ["Python", "PyTorch", "LLM", "微调", "分布式训练", "论文复现"]),
    ("算法", "NLP 算法工程师", ["Python", "PyTorch", "Transformer", "微调", "评测", "数据处理"]),
    ("算法", "多模态算法工程师", ["Python", "PyTorch", "多模态", "CLIP", "分布式训练", "论文复现"]),
    ("算法", "推理优化工程师", ["C++", "CUDA", "推理优化", "量化", "PyTorch", "性能分析"]),
    ("应用开发", "LLM 应用开发", ["Python", "API 接入", "Prompt", "RAG", "向量库", "部署"]),
    ("应用开发", "AI 后端工程师", ["Python", "Java", "微服务", "API 接入", "部署", "SQL"]),
    ("应用开发", "全栈 AI 工程师", ["TypeScript", "Python", "API 接入", "前端", "部署", "向量库"]),
    ("应用开发", "AI 平台工程师", ["Python", "K8s", "部署", "监控", "推理优化", "SQL"]),
    ("Agent 工程", "Agent 开发工程师", ["Python", "Prompt", "工具调用", "LangGraph", "评测", "状态机"]),
    ("Agent 工程", "Agent 平台工程师", ["Python", "MCP", "工具调用", "沙箱", "部署", "监控"]),
    ("Agent 工程", "RAG 工程师", ["Python", "RAG", "向量库", "检索", "评测", "数据处理"]),
    ("Agent 工程", "AI 工程效率", ["Python", "评测", "CI/CD", "监控", "Prompt", "数据分析"]),
    ("AI 产品", "AI 产品经理", ["产品设计", "用户研究", "数据分析", "Prompt", "项目管理", "商业化"]),
    ("AI 产品", "Agent 产品经理", ["产品设计", "工具调用", "用户研究", "评测", "项目管理", "商业化"]),
    ("AI 产品", "AI 解决方案产品", ["产品设计", "客户沟通", "方案撰写", "商业化", "项目管理", "数据分析"]),
    ("AI 产品", "AI 增长产品", ["产品设计", "数据分析", "A/B 实验", "商业化", "SQL", "用户研究"]),
    ("解决方案", "AI 解决方案架构师", ["客户沟通", "方案撰写", "部署", "API 接入", "RAG", "项目管理"]),
    ("解决方案", "售前工程师", ["客户沟通", "方案撰写", "产品演示", "Prompt", "商业化", "项目管理"]),
    ("解决方案", "交付工程师", ["部署", "K8s", "客户沟通", "监控", "SQL", "项目管理"]),
    ("解决方案", "行业顾问", ["客户沟通", "行业知识", "方案撰写", "数据分析", "商业化", "项目管理"]),
]

docs = [(role, title, set(sk)) for role, title, sk in JDS]
freq = Counter()
for _, _, s in docs:
    freq.update(s)

print("=" * 60)
print("表 1  技能出现频率 Top-12（20 条 JD，每条 6 个要求）")
print("=" * 60)
for i, (skill, n) in enumerate(freq.most_common(12), 1):
    bar = "#" * round(n / 20 * 30)
    print(f"{i:>2}. {skill:<10}{n:>3}/20  {bar}")

pair = Counter()
for _, _, s in docs:
    pair.update(combinations(sorted(s), 2))
N = len(docs)
print("\n" + "=" * 60)
print("表 2  共现强度：lift = P(a,b) / (P(a)P(b))，只显示共现 >= 3 的对")
print("=" * 60)
ranked = []
for (a, b), c in pair.items():
    if c < 3:
        continue
    lift = (c / N) / ((freq[a] / N) * (freq[b] / N))
    ranked.append((lift, c, a, b))
for lift, c, a, b in sorted(ranked, reverse=True)[:8]:
    print(f"{a:<8}+ {b:<10} 共现{c:>2}  lift={lift:>4.2f}")

print("\n" + "=" * 60)
print("表 3  各岗位的区分度技能（该类占比 - 全体占比，取前 2）")
print("=" * 60)
roles = sorted({r for r, _, _ in docs})
for role in roles:
    sub = [s for r, _, s in docs if r == role]
    cnt = Counter()
    for s in sub:
        cnt.update(s)
    scored = sorted(((cnt[k] / len(sub) - freq[k] / N, k) for k in cnt), reverse=True)
    picks = [f"{k}({v:+.2f})" for v, k in scored[:2]]
    print(f"{role:<8} {'  '.join(picks)}")

print("\n结论：Python/Prompt/部署 是通用底座，真正区分岗位的是「共现块」——")
print("      Agent 岗 = Prompt + 工具调用 + 评测；解决方案岗 = 客户沟通 + 方案撰写 + 部署。")
print("读法：对照 JD 时不要逐条打勾，先看它属于哪个共现块；块不匹配，单项会得再多也难命中。")
