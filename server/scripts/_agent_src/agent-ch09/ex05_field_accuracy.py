# title: 字段级准确率与混淆对：字符对不等于字段对
from collections import Counter

import numpy as np

rng = np.random.default_rng(0)
FIELDS = ["发票号", "金额", "税率", "开票日期", "销方名称", "购方名称"]
COMPANIES = ["甲公司", "乙科技", "丙集团"]


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def gen_samples(n=50):
    """生成 n 条「真值 + 抽取结果」，注入四类系统性错误。"""
    gts, preds = [], []
    for i in range(n):
        seller, buyer = rng.choice(len(COMPANIES), size=2, replace=False)
        g = {
            "发票号": f"INV-{i:04d}",
            "金额": f"{rng.integers(100, 99999)}.{rng.integers(0, 100):02d}",
            "税率": "13%",
            "开票日期": "2026-09-19",
            "销方名称": COMPANIES[seller],
            "购方名称": COMPANIES[buyer],
        }
        p = dict(g)
        r = rng.random()
        if r < 0.20:   # 千分位口径错误（模型其实抽对了，判等口径判错）
            p["金额"] = f"{int(g['金额'].split('.')[0]):,}.{g['金额'].split('.')[1]}"
        elif r < 0.32:  # 销方/购方互串：两个字段的值整体互换位置
            p["销方名称"], p["购方名称"] = g["购方名称"], g["销方名称"]
        elif r < 0.40:  # 日期格式漂移
            p["开票日期"] = "2026/09/19"
        elif r < 0.46:  # 整字段漏抽（键缺失）
            p.pop("开票日期")
        gts.append(g)
        preds.append(p)
    return gts, preds


def levenshtein(a, b):
    """标准 DP 编辑距离（纯标准库）。"""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def field_accuracy(preds, gts):
    total = hit = 0
    for p, g in zip(preds, gts):
        for k in g:
            total += 1
            hit += (p.get(k) == g[k])
    return hit, total


def per_field(preds, gts):
    hit = {k: 0 for k in FIELDS}
    tot = {k: 0 for k in FIELDS}
    for p, g in zip(preds, gts):
        for k in g:
            tot[k] += 1
            hit[k] += (p.get(k) == g[k])
    return {k: hit[k] / tot[k] for k in FIELDS}


def confusion_pairs(preds, gts, topn=3):
    """A 的真值出现在 B 的预测位置上 = A 被错抽成 B。"""
    c = Counter()
    for p, g in zip(preds, gts):
        for a in g:
            if p.get(a) == g[a]:
                continue
            for b in FIELDS:
                if b != a and p.get(b) == g[a]:
                    c[(a, b)] += 1
                    break
    return c.most_common(topn)


gts, preds = gen_samples()
hit, total = field_accuracy(preds, gts)
pf = per_field(preds, gts)
cp = confusion_pairs(preds, gts)

print("== 50 条样本、6 字段的字段级评估报告 ==")
print(f"总体字段级准确率 = {hit}/{total} = {hit / total:.2%}\n")
print(f"{pad('字段', 10)}{'准确率':>8}")
for k in FIELDS:
    print(f"{pad(k, 10)}{pf[k]:>8.1%}")
print("\nTop 混淆对（真值字段 -> 被错抽到的字段）:")
for (a, b), n in cp:
    print(f"  {a} -> {b}: {n} 次")

char_hit = char_tot = 0
for p, g in zip(preds, gts):
    for k in g:
        a, b = str(p.get(k, "")), str(g[k])
        char_tot += max(len(a), len(b))
        char_hit += max(len(a), len(b)) - levenshtein(a, b)
print(f"\n字符级准确率（编辑距离口径）= {char_hit / char_tot:.2%}")
print(f"字段级准确率（全等口径）    = {hit / total:.2%}  <- 业务验收用这个")

print("\n结论：同一份数据字符级明显高于字段级，差异来自全等判定与系统性错位，")
print("读法：1. 字段级 = 全等字段占比，千分位、大小写、单位漂移都会判错，口径要在 schema 里预先定义；2. Top 混淆对按频次排序就是下一步优化清单（本例是销方名称互串 → 交换两栏的数据增强）；3. 漏抽（键缺失）比串位更严重，应配低置信度路由兜底；4. 本示例用程序化生成的 50 条模拟样本，不读取任何外部文件。")
