# title: 简历 STAR-R 完整性与空话检测：把「不可信」变成可定位的问题
# 本地模拟：内置 6 条 bullet 的规则化审计，不调用任何外部服务。
# 目的：交简历前的固定动作——先过空话扫描，再过 STAR-R 五段覆盖，最后按优先级重写。
import re

BULLETS = [
    # --- 三条空话反例 ---
    "参与公司知识库问答项目，负责检索模块",
    "熟悉 LangChain 与向量数据库，深入掌握 RAG 技术",
    "系统性能获得显著提升，用户体验大大改善",
    # --- 三条合格范例 ---
    "独立重写召回层：300 条标注查询上召回率 71%→89%，高于开源默认配置 6 个点；复盘发现 b=0.75 对短文档过惩罚，后续应按文档长度分桶标定",
    "针对短文档被长度惩罚的问题，引入文档长度分桶（b 参数按桶分别标定）：top-3 命中率 84%→87%",
    "A/B 同流量两周：检索 P99 从 850ms 降到 210ms，瓶颈定位为同步 OCR 调用，改异步队列后恢复",
]

EMPTY_RULES = [
    (r"(负责|参与|协助)[^，。]{0,12}$", "动词空话"),
    (r"(深入|熟练|扎实)掌握", "程度形容词"),
    (r"(显著|大幅|极大|大大)地?(提升|改善|优化)", "不可证伪成果"),
]

# STAR-R 五段的关键词近似（规则初筛，最终判断在人）
STAR_R = {
    "S 背景": r"(万|千|\d+\s?%|QPS|文档|员工|团队|公司|季度|月)",
    "T 任务": r"(独立|主导|承担)[^，。]{4,}|负责[^，。]{4,}",
    "A 动作": r"(实现|重写|设计|引入|替换|搭建|部署|上线|迁移|改)",
    "R 结果": r"(\d+\s?%|→|\d+\s?倍|从.{1,12}到)",
    "R 反思": r"(复盘|教训|边界|局限|不足|如果重来|改进|问题)",
}


def audit(b):
    empty = [name for pat, name in EMPTY_RULES if re.search(pat, b)]
    missing = [seg for seg, pat in STAR_R.items() if not re.search(pat, b)]
    return empty, missing


print("== 逐条审计 ==")
print(f"{'#':<3}{'空话命中':<16}{'缺失段':<26}{'优先级分':>6}")
scored = []
for i, b in enumerate(BULLETS, 1):
    empty, missing = audit(b)
    priority = len(empty) * 2 + len(missing)
    scored.append((priority, i, b, empty, missing))
    print(f"{i:<3}{('、'.join(empty) or '无'):<16}{('、'.join(missing) or '无'):<26}{priority:>6}")

scored.sort(key=lambda t: (-t[0], t[1]))
worst = scored[0]
print(f"\n重写优先级最高：第 {worst[1]} 条「{worst[2]}」")
print(f"  命中空话 {worst[3]}，缺失 {worst[4]} —— 空话 bullet 整条信息量为零，先于任何补要素动作")

# 改写示范：同一条信息的 STAR-R 五段齐 + 带数字
REWRITE = ("背景：2000 人企业的知识库问答，人工客服 30% 工单是重复问题（S）；"
           "独立负责检索层重写（T）：用 BM25 替换关键词匹配，300 条标注查询上标定 k1=1.2/b=0.75（A）："
           "召回率 71%→89%，top-3 命中率 62%→84%，高于开源默认配置 6 个点（R）；"
           "复盘发现剩余失败集中在同义词查询，是下一版引入查询扩展的方向（R）")
print("\n== 改写示范（五段齐 + 数字） ==")
print("  " + REWRITE)
empty_r, missing_r = audit(REWRITE)
assert not empty_r and not missing_r, f"改写后仍有问题: {empty_r} {missing_r}"
print(f"  复检：空话 {empty_r or '无'}，缺失段 {missing_r or '无'}")

# 反例自毁：确认规则确实能抓住空话（不是永远返回空的「温柔」扫描器）
for b in BULLETS[:3]:
    e, _ = audit(b)
    assert e, f"空话规则漏报了: {b}"
for b in BULLETS[3:]:
    e, _ = audit(b)
    assert not e, f"范例被误伤: {b}"
assert not audit(BULLETS[3])[1], "范例 4 应五段全覆盖"
print("  自毁测试通过：3 条反例全部命中空话规则，3 条范例空话零命中，范例 4 五段全覆盖")

print("\n结论：空话检测管「信息量为零」，STAR-R 覆盖管「扛不住追问」，两者都过才是可交付的 bullet；")
print("读法：1. 规则必然误伤（「独立负责」也含「负责」），所以输出规则名供人工复核，工具是初筛不是终审；2. 重写优先级 = 空话数×2 + 缺失段数——空话 bullet 修了才轮到补要素；3. 五段里最后的 R（反思）最常缺，也最值钱：它给面试官追问留锚点；4. 真实投递前把终稿全文过一遍本审计器，目标零命中（对应 project.json 任务一的验收口径）。")
