# title: 简历一页纸信息密度：逐行打分、空话行清单与改写演示
import re

import numpy as np

TECH = ["Python", "SQL", "NumPy", "Pandas", "LangChain", "LlamaIndex", "Redis",
        "Docker", "Kubernetes", "FAISS", "LoRA", "GitHub", "RAG", "vLLM"]
ACTION = ["主导", "设计", "实现", "上线", "优化", "搭建", "交付", "推动", "定位",
          "复现", "建设", "重构", "降低", "提升", "引入", "降到", "降至", "完成", "验证"]
FILLER = ["等等", "之类", "良好", "认真", "丰富", "较强", "一定", "各种"]
LINE_BUDGET = 45          # 一页纸的经验行数上限（经验判断）
DENSE_BAR = 4.0           # 内容行平均密度的达标线（经验判断）

# (分区, 行文本, 是否结构行——标题/联系信息不参与打分)
RESUME = [
    ("基本信息", "姓名 | 电话 | 邮箱 | GitHub", True),
    ("教育", "XX 大学 计算机科学与技术 本科 2022.09-2026.06", True),
    ("技能", "熟练掌握 Python、SQL，熟悉 NumPy/Pandas 数据分析", False),
    ("技能", "熟悉 LangChain、LlamaIndex 等编排框架，了解主流大模型 API", False),
    ("技能", "具备良好的团队协作与沟通能力，工作认真负责", False),
    ("实习", "A 公司 · 后端开发实习生 2025.06-2025.12", True),
    ("实习", "参与用户中心模块开发，负责订单查询接口实现与联调", False),
    ("实习", "通过引入 Redis 缓存，把订单查询 P99 延迟从 320ms 降到 90ms"
             "（日均 50 万次调用）", False),
    ("实习", "B 公司 · AI 应用实习生 2025.12-2026.06", True),
    ("实习", "独立负责工单自动问答从 0 到 1 上线，累计服务 1.2 万条工单", False),
    ("实习", "搭建 200 条工单评估集与周回归流程，Recall@5 从 0.71 提升到 0.86", False),
    ("实习", "C 公司 · 数据分析实习生 2024.09-2025.03", True),
    ("实习", "负责数据报表日常维护，使用 SQL 与 Python 完成 30 余张报表自动化", False),
    ("项目", "课程知识库问答（Python / LangChain / FAISS）", True),
    ("项目", "基于 LangChain 实现文档切分、向量检索与答案生成，"
             "自测 30 个问题覆盖率 80%", False),
    ("项目", "论文摘要工具（arXiv 爬虫 + LLM 摘要）", True),
    ("项目", "单篇摘要耗时从 40s 降到 12s，被 3 位同实验室同学持续使用", False),
    ("项目", "领域微调实验（LoRA，3 组对比）", True),
    ("项目", "完成 3 组对比实验，验证微调在领域问答上的效果提升", False),
    ("其他", "获校级奖学金两次，通过英语六级", False),
    ("其他", "GitHub 持续更新，维护技术博客", False),
]


def line_score(s):
    """密度分 = 2×数字组 + 技术词 + 强动词 − 2×空话词，封顶 10，下限 0。"""
    digits = len(re.findall(r"\d+(?:\.\d+)?", s))
    tech = sum(1 for t in TECH if t in s)
    act = sum(1 for v in ACTION if v in s)
    fill = sum(1 for f in FILLER if f in s)
    return digits, tech, act, fill, max(0, min(10, 2 * digits + tech + act - 2 * fill))


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


print("== 1) 逐行密度体检（结构行不打分）==")
print(f"{pad('分区', 6)}{pad('行内容', 44)}{'数字':>3}{'技术':>3}{'动词':>3}"
      f"{'空话':>3}{'密度':>4}  判定")
content_scores, empty_lines, total_digits = [], [], 0
for sec, text, struct in RESUME:
    if struct:
        print(f"{pad(sec, 6)}{pad(text[:42], 44)}{'-':>3}{'-':>3}{'-':>3}{'-':>3}"
              f"{'-':>4}  结构行")
        continue
    d, t, a, f, sc = line_score(text)
    content_scores.append(sc)
    total_digits += d
    verdict = "空话行" if sc == 0 else ("弱行" if sc <= 2 else "")
    if sc == 0:
        empty_lines.append(text)
    print(f"{pad(sec, 6)}{pad(text[:42], 44)}{d:>3}{t:>3}{a:>3}{f:>3}{sc:>4}  {verdict}")

arr = np.array(content_scores, dtype=float)
print("\n== 2) 汇总 ==")
print(f"   总行数 {len(RESUME)}/{LINE_BUDGET}（一页纸预算），"
      f"剩余 {LINE_BUDGET - len(RESUME)} 行——建议再补 2 个项目（每个约 3 行）")
print(f"   内容行 {len(content_scores)} 条，平均密度 {arr.mean():.1f}"
      f"（达标线 {DENSE_BAR:.0f}），中位数 {np.median(arr):.0f}")
print(f"   空话行 {len(empty_lines)} 条，弱行（≤2 分，含空话行）{(arr <= 2).sum()} 条")
print(f"   可追问点（数字组总数）= {total_digits} 个——面试官能沿着挖的抓手")

print("\n== 3) 改写演示（空话行 → 带数字行）==")
rewrites = [
    ("获校级奖学金两次，通过英语六级",
     "获校级一等奖学金 2 次（专业前 5%），英语六级 560 分"),
    ("具备良好的团队协作与沟通能力，工作认真负责",
     "主导 3 次跨模块联调，推动 2 个阻塞问题当周解决"),
]
for old, new in rewrites:
    o = line_score(old)[-1]
    n = line_score(new)[-1]
    print(f"   {o:.0f} 分 → {n:.0f} 分 | {old}")
    print(f"           | {new}")

print(f"\n结论：平均密度 {arr.mean():.1f} 分踩线达标，但 {len(empty_lines)} 条空话行和"
      f"{LINE_BUDGET - len(RESUME)} 行空余暴露了同一问题——有经历没写成证据")
print("读法：1. 密度分只衡量「可追问性」不衡量真实性：数字多的行经得起挖，形容词多的行一挖就穿；2. 空话行的共同特征是零数字（多半还配空话词：等等/良好/认真），改写的唯一公式是「谁 + 做了什么 + 数字结果」；3. 一页纸没用满是风险信号：21/45 行意味着作品集项目少于 5 个或 STAR-R 没展开，补 2 个项目比删行更重要；4. 本打分器是规则法，同义词与行业黑话需按目标岗位补充词表（见示例 ex04 的 JD 反推）。")
