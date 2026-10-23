# title: 作品集 STAR-R 完整性校验：五个项目的抗追问评级
import numpy as np

# 五个原创教学用项目描述（结构化字段，非自由文本）
PROJECTS = [
    {
        "name": "工单自动问答", "real_users": "是（1.2 万条工单，反馈=已解决按钮）",
        "S": "售后 40% 工单是重复问题，人工日均 80 条",
        "T": "上线自动问答，自动处理率做到 50%",
        "A": "RAG 检索 + 规则兜底 + 低置信度转人工",
        "R": {"指标": ["自动处理率 12%→50%", "Recall@5 0.71→0.86"],
              "基线": "上线前 4 周均值", "口径": "工单全量/200 条标注样本",
              "归因": "混合召回替代纯向量；自动回复被点已解决"},
        "取舍": ["不用微调选 RAG：知识周更，微调追不上；代价是检索质量决定上限"],
        "教训": ["第一版没做兜底，客诉 +18%——先加路由再谈效果"],
        "Reflection": "重来先建 200 条评估集再动工，灰度分开检索与生成",
    },
    {
        "name": "课程知识库问答", "real_users": "否（仅课程演示）",
        "S": "课程作业：给教材做问答",
        "T": "实现一个能回答课程问题的 Demo",
        "A": "文档切分 + 向量检索 + 生成",
        "R": {"指标": ["回答覆盖率 80%"], "口径": "自测 30 个问题",
              "基线": None, "归因": None},
        "取舍": [], "教训": [],
        "Reflection": "检索切分策略还能优化",
    },
    {
        "name": "论文摘要小工具", "real_users": "是（3 位同实验室同学）",
        "S": "组会前读论文来不及，需要摘要+要点",
        "T": "做一个输入 arXiv 链接输出结构化摘要的脚本",
        "A": "规则解析 + 分段摘要 + 模板化输出",
        "R": {"指标": ["单篇摘要耗时 40s→12s"], "基线": "人工阅读均时 25 分钟",
              "口径": "20 篇论文计时", "归因": "缓存 + 分段并行"},
        "取舍": [],
        "教训": ["第一次没做异常处理，遇到扫描版 PDF 直接崩——边界输入要先测"],
        "Reflection": "应该先做失败样本集再优化速度",
    },
    {
        "name": "领域微调实验", "real_users": "否（实验报告）",
        "S": "想知道微调能不能提升领域问答效果",
        "T": "完成一组对比实验",
        "A": "LoRA 微调 + 评测脚本",
        "R": {"指标": ["效果更好"], "基线": None, "口径": None, "归因": None},
        "取舍": [], "教训": [],
        "Reflection": None,
    },
    {
        "name": "博客评论机器人", "real_users": "否（自用）",
        "S": "博客垃圾评论变多",
        "T": "自动过滤垃圾评论",
        "A": "规则 + 关键词过滤",
        "R": None,
        "取舍": [], "教训": [],
        "Reflection": None,
    },
]


def star_r_check(proj):
    """返回 (缺失段列表, Result 三要素清单, 可追问点数)。"""
    need = ["S", "T", "A", "R", "Reflection"]
    missing = [k for k in need if not proj.get(k)]
    r = proj.get("R") or {}
    metric_ok = [k for k in ("基线", "口径", "归因") if r.get(k)]
    probes = len(r.get("指标", [])) + len(proj.get("取舍", [])) + len(proj.get("教训", []))
    return missing, metric_ok, probes


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


print("== 1) 五项目逐个体检 ==")
print(f"{pad('项目', 14)}{'五段':>4}{'三要素':>5}{'追问点':>5}  {'评级':<6} {'用户':>2}  缺失")
scores = []
for p in PROJECTS:
    missing, metric, probes = star_r_check(p)
    parts = 5 - len(missing)
    ok = parts == 5 and len(metric) == 3 and probes >= 3
    scores.append((p["name"], parts, len(metric), probes, ok))
    miss_txt = ",".join(missing) if missing else "无"
    print(f"{pad(p['name'], 14)}{parts:>4}{len(metric):>5}{probes:>5}  "
          f"{'抗追问' if ok else '需补结构':<6} {p['real_users'][:1]:>2}  {miss_txt}")

arr = np.array([[s[1], s[2], s[3]] for s in scores], dtype=float)
n_ok = sum(1 for s in scores if s[4])
print("\n== 2) 作品集整体体检 ==")
print(f"   抗追问项目 {n_ok}/{len(PROJECTS)}（要求：至少 1 个，且至少 1 个有真实用户）")
print(f"   平均五段完整度 {arr[:, 0].mean():.1f}/5，平均三要素 {arr[:, 1].mean():.1f}/3，"
      f"平均追问点 {arr[:, 2].mean():.1f}")
print(f"   有真实用户的项目: {sum(1 for p in PROJECTS if p['real_users'].startswith('是'))}"
      f"/{len(PROJECTS)}")

# 3) 修复优先级：先补出现频次最高的缺失项（一个周末能补完的那种）
from collections import Counter
miss_c = Counter()
for p in PROJECTS:
    for m in star_r_check(p)[0]:
        miss_c[m] += 1
print("\n== 3) 修复优先级（按缺失频次降序）==")
for k, v in miss_c.most_common():
    print(f"   {k}: 缺 {v} 个项目")
best = max(scores, key=lambda s: (s[4], s[3]))
worst = min(scores, key=lambda s: (s[1], s[2], s[3]))
print(f"   最强项: {best[0]}（追问点 {best[3]}）——面试主讲这个")
print(f"   最弱项: {worst[0]}（五段 {worst[1]}/5）——只配一句带过或撤下")

print("\n结论：五个项目里只有 1 个抗追问、2 个有真实用户——作品集的质量由结构决定，不由技术栈决定")
print("读法：1. 评级规则 = 五段齐全 + 三要素齐全 + 追问点≥3，三条全过才敢放简历首页；2. 伪量化的典型是「效果更好」这种 Result——有指标字段但三要素全空，比没有更危险；3. 修复顺序：先补 Reflection 与三要素（回忆成本，一个周末），再补取舍记录（决策现场），数字最后校准；4. 5 个项目里 ≥1 个有真实用户是硬要求——面试官问「谁在用」答不上来，整个作品集的可信度同步打折。")
