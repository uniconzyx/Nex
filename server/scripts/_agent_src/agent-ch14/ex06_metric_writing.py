# title: 量化指标写法打分：基线、口径、归因、可复现四要素体检
import re

import numpy as np

# 教学用简历 bullet（原创）：前三条是常见坏写法，后三条是好写法
BULLETS = [
    "优化了系统性能，效果明显提升",
    "准确率提升到 92%",
    "把 P99 延迟从 850ms 降到 210ms",
    "通过引入缓存与批处理，在 QPS 1.2k 不变的条件下把 P99 延迟从 850ms 降到 210ms"
    "（200 条压测样本）",
    "用户体验有了显著改善，投诉少了很多",
    "自动处理率 12%→50%，基线为上线前 4 周工单全量均值，归因于混合召回替代纯向量召回",
]

VAGUE = ["明显", "大大", "显著", "很多", "一些", "优化了", "提升了", "改善"]
KOU_WORDS = ["口径", "样本", "全量", "均值", "P99", "QPS", "定义"]
GUI_WORDS = ["因为", "通过", "引入", "改用", "换成", "归因", "手段是"]
UNITS = ["ms", "%", "条", "分钟", "小时", "人时", "QPS", "万"]


def has_digit(s):
    return any(c.isdigit() for c in s)


def check_baseline(s):
    """基线：有对比对象（改前/对照组/基线值）。"""
    if "→" in s:
        head, tail = s.split("→", 1)
        return has_digit(head) and has_digit(tail)
    if re.search(r"从\s*[\d.]+\s*\S*\s*(降到|降低到|提升到|提高到)\s*[\d.]+", s):
        return True
    return ("相比" in s or "基线" in s) and has_digit(s)


def check_koujing(s):
    return any(k in s for k in KOU_WORDS)


def check_guiyin(s):
    return any(k in s for k in GUI_WORDS)


def check_repro(s):
    """可复现：有数字且有单位/条件，读者能照着复现测量。"""
    return has_digit(s) and (any(u in s for u in UNITS) or "条件下" in s)


def score_bullet(s):
    b, k, g, r = (check_baseline(s), check_koujing(s),
                  check_guiyin(s), check_repro(s))
    vague = sum(1 for v in VAGUE if v in s)
    total = max(0.0, min(10.0, 2.5 * (b + k + g + r) - vague))
    missing = [n for n, ok in [("基线", b), ("口径", k), ("归因", g), ("可复现", r)] if not ok]
    return (b, k, g, r), vague, total, missing


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


print("== 1) 六条 bullet 的四要素体检（每要素 2.5 分，空话每个扣 1 分）==")
print(f"{pad('bullet', 46)}{'基线':>3}{'口径':>3}{'归因':>3}{'复现':>3}"
      f"{'扣分':>4}{'总分':>5}  缺失")
rows = []
for s in BULLETS:
    (b, k, g, r), vague, total, missing = score_bullet(s)
    rows.append(total)
    mark = lambda x: "√" if x else "×"
    print(f"{pad(s[:44], 46)}{mark(b):>3}{mark(k):>3}{mark(g):>3}{mark(r):>3}"
          f"{vague:>4}{total:>5.1f}  {','.join(missing) if missing else '无'}")

print(f"\n   平均分 {np.mean(rows):.1f}/10；不及格（<6）的 {sum(1 for x in rows if x < 6)}/{len(rows)} 条")

print("\n== 2) 有数字 ≠ 有指标：第二条的反例 ==")
b2 = BULLETS[1]
(fl, _, total2, miss2) = score_bullet(b2)
print(f"   「{b2}」有数字，但缺 {','.join(miss2)} —— 没有基线的数字只是状态描述，")
print("   面试官无法判断 92% 是好了还是坏了；没有口径的 92% 也无法复现测量")

print("\n== 3) 改写演示：把最差的一条改成满分 ==")
worst_idx = int(np.argmin(rows))
print(f"   原文（{rows[worst_idx]:.1f} 分）: {BULLETS[worst_idx]}")
rewritten = ("通过给检索结果加缓存，在 QPS 不变的条件下把 P99 延迟从 850ms 降到 "
             "210ms（200 条压测样本，口径为服务端全量日志）")
_, _, total3, miss3 = score_bullet(rewritten)
print(f"   改写（{total3:.1f} 分）: {rewritten}")
print(f"   改写后缺失项: {miss3 if miss3 else '无'}")

print(f"\n结论：六条平均 {np.mean(rows):.1f} 分——「有数字」只值 2.5 分，四要素齐全才构成可追问的指标")
print("读法：1. 伪量化三种形态：只有数字没基线（第二条）、有数字有基线没归因（第三条，说不清谁带来的）、全是形容词没数字（第一/五条）；2. 空话词（明显/显著/很多）每个扣 1 分——它们是指标缺失的补偿性修辞；3. 改写模板：通过{手段}，在{条件}下把{指标}从{基线}到{新值}（{口径}），四要素一次到位；4. 本打分器是规则法，只看措辞不看事实——数字的真实性靠评估报告背书（示例 ex05 的产物校验）。")
