# title: hype 检测器：标题词频与实质信号的比值，决定一条信息降不降层
# 规则版 anti-hype：hype 词密度（每百字命中数） vs 实质信号数（0-4）。
# 内置摘要为教学构造文本，不指向任何真实论文；规则本身可直接搬到 RSS 过滤器里。
import re

HYPE_ZH = ["首个", "首次", "碾压", "秒杀", "革命性", "突破性", "史上", "彻底改变",
           "吊打", "完美", "颠覆", "遥遥领先"]
HYPE_EN = ["sota", "state-of-the-art", "outperforms all", "revolutionary",
           "breakthrough", "unprecedented", "dominates"]

SUBSTANCE_SIGNALS = [
    ("有 baseline 对比", lambda t: any(w in t for w in ["baseline", "对比", "compared"])),
    ("有具体数字指标", lambda t: bool(re.search(r"\d+(?:\.\d+)?\s*(?:个点|%|％|倍)", t))),
    ("讨论失败/局限", lambda t: any(w in t for w in ["局限", "失败", "限制", "limitation", "fails"])),
    ("有代码/数据链接", lambda t: any(w in t for w in ["github", "code", "代码", "开源", "dataset"])),
]

# (标签, 标题, 摘要) —— 教学构造
ENTRIES = [
    ("条目1", "首个碾压全部基线的方法",
     "我们提出首个碾压全部 baseline 的方法，革命性突破，彻底改变领域，遥遥领先。"),
    ("条目2", "某检索框架的延迟优化复盘",
     "上线三个月复盘：p99 延迟从 820ms 降到 310ms（-62%），但冷启动场景失败率上升 2.1 个点，"
     "根因是缓存预热策略；代码已开源 github.com/example/repo。"),
    ("条目3", "一种新的注意力变体",
     "提出注意力变体 X。在三个基准上与 6 个 baseline 对比，平均提升 1.8 个点；"
     "局限：长序列下不稳定，超过 8k 后失败。"),
    ("条目4", "史上最强模型诞生",
     "史上最强、完美、颠覆性的模型诞生，秒杀一切， outperforms all existing methods。"),
    ("条目5", "小数据场景下的正则化研究",
     "研究正则化对 1k 样本以下任务的影响：相比 baseline 提升 0.6 个点，"
     "但在 10k 以上样本时优势消失（limitation：结论仅适用小数据）。"),
    ("条目6", "社区热帖：某框架使用体验",
     "体验不错，推荐大家试试，感觉比以前的方案快了不少，谁用谁知道。"),
]


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def analyze(title, abstract):
    text = (title + " " + abstract).lower()
    n_chars = len(abstract) + len(title)
    hype_hits = sum(text.count(w.lower()) for w in HYPE_ZH + HYPE_EN)
    density = hype_hits / n_chars * 100          # 每百字 hype 词数
    signals = [name for name, fn in SUBSTANCE_SIGNALS if fn(text)]
    return density, signals


print("== hype 检测：密度阈值 2.0/百字，实质信号 >=3 为高 ==")
print(f"{pad('条目', 6)}{'hype密度':>9}{'实质信号':>9}  象限 -> 处置")
for tag, title, abstract in ENTRIES:
    density, signals = analyze(title, abstract)
    high_hype = density >= 2.0
    high_sub = len(signals) >= 3
    if high_hype and not high_sub:
        quad, action = "高 hype 低实质", "降层到 L3/L4：提高举证要求，不进复现候选"
    elif high_hype and high_sub:
        quad, action = "高 hype 高实质", "正常对待：按评分卡走，hype 不减分"
    elif not high_hype and high_sub:
        quad, action = "低 hype 高实质", "优先读：工程复盘类，信息密度最高"
    else:
        quad, action = "低 hype 低实质", "信息量不足：只记卡片"
    sig_txt = f"{len(signals)}/4"
    print(f"{pad(tag, 6)}{density:>9.2f}{sig_txt:>9}  {quad} -> {action}")

print("\n== 实质信号明细 ==")
for tag, title, abstract in ENTRIES:
    density, signals = analyze(title, abstract)
    print(f"  {tag}: {signals if signals else '无'}")

print("\n结论：hype 的本质是「强断言 / 弱证据」的比值失衡，规则版检测把降层决策变成可复现的计算，")
print("读法：1. hype 词密度按每百字命中数算，标题权重天然更高（标题短、断言密）；2. 实质信号四个可检查项：baseline 对比、具体数字、失败/局限讨论、代码数据链接——注意条目3 有局限讨论仍算高实质，「承认失败」是加分项不是减分项；3. 高 hype 低实质 -> 降层处理（不是不信，是提高举证要求）；低 hype 高实质 -> 优先读，工程复盘通常落在这格；4. 词表与阈值是经验判断，应按你的信息源分布校准；5. 本示例摘要为教学构造，规则可直接搬进 RSS 过滤器。")
