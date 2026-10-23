# title: 方案书数字一致性自检：成本、报价、毛利与竞品结论四处引用必须相等
# 工程账本（示例测算）：方案书被 CTO 挑战最多的是「第 8 页的成本和第 12 页对不上」。

COST = 2.05        # 单任务四元成本合计 ¥（concept/02 口径，示例测算）
MRR = 45000.0      # 月收入 ¥（示例测算）
PRICE = 6.83       # 报价 ¥/任务（示例测算，= 成本/(1-0.70)，保留两位小数）

# 方案书四页对同一组数字的引用（正常应一致）
PAGES = {
    "P3_成本测算表": {"单任务成本": 2.05, "月收入": 45000.0, "毛利率": 0.70},
    "P7_报价页":     {"单任务成本": 2.05, "报价下限": 6.83},
    "P10_毛利对比":  {"单任务成本": 2.05, "月收入": 45000.0, "月毛利": 31493.41},
    "P12_竞品结论":  {"报价下限": 6.83, "月毛利": 31493.41},
}

# 派生公式（交叉验证用：只查「相等」查不出「一起错」）
DERIVED = {
    "报价下限": COST / (1 - 0.70),                    # = 6.8333…，呈现为 6.83
    "月毛利": MRR - COST * (MRR / PRICE),             # = 45000 − 2.05×6588.58 = 31493.41
}


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def check_consistency(pages, derived):
    """同一 key 多页出现必须相等；派生值与公式值按两位小数口径吻合"""
    issues = []
    seen = {}
    for page, kv in pages.items():
        for k, v in kv.items():
            if k in seen and abs(seen[k][1] - v) > 1e-9:
                issues.append((page, k, f"{seen[k][0]} 页", seen[k][1], v))
            seen[k] = (page, v)
    for k, v in derived.items():
        if k in seen and round(seen[k][1], 2) != round(v, 2):
            issues.append((seen[k][0], k, "派生公式", v, seen[k][1]))
    return issues


print("== 方案书一致性自检（四处引用 vs 派生公式；示例测算） ==")
issues = check_consistency(PAGES, DERIVED)
if issues:
    for page, k, src, ref_v, got in issues:
        print(f"[不一致] {page} 的「{k}」={got}，与 {src} 的 {ref_v} 冲突")
else:
    print("跨页引用一致，派生公式吻合 —— 可发布")

# 交叉验证明细
tasks = MRR / PRICE
print(f"\n交叉验证：月任务量 = 月收入/报价 = {tasks:,.0f}，"
      f"月毛利 = {MRR:,.0f} − {COST}×{tasks:,.0f} = ¥{MRR - COST*tasks:,.2f}")

# 注入一处典型错误：报价页手改成本数字（模拟「改了一个忘改其余」）
PAGES_BAD = {k: dict(v) for k, v in PAGES.items()}
PAGES_BAD["P7_报价页"]["单任务成本"] = 1.80   # 手改
print("\n== 注入错误后重跑（模拟改了一处忘改其余） ==")
issues2 = check_consistency(PAGES_BAD, DERIVED)
for page, k, src, ref_v, got in issues2:
    print(f"[不一致] {page} 的「{k}」={got}，与 {src} 的 {ref_v} 冲突")
print(f"定位到 {len(issues2)} 处不一致 —— 修复后重跑至 0 处方可发布")

print("\n结论：方案书的可信度死在数字自洽上，一致性自检应成为发布前的固定动作，")
print("读法：1. 同一语义数字（单任务成本/报价下限/月毛利）多处引用必须相等，用 key 归并全页扫描，容差 1e-9；2. 派生值要用公式反算交叉验证（报价下限=c/(1−g)，月毛利=月收入−月收入/报价×单任务成本），只查「相等」查不出「一起错」；派生比较按两位小数口径，容忍呈现层的四舍五入；3. 典型事故路径：为了凑某个结论手改一页数字，忘了联动其余页——自检脚本要在每次导出后自动跑；4. 数字为教学假设（示例测算）。")
