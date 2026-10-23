# title: 精读笔记结构化模板校验：八要素、数字指标与差异记录检查
# 工具类：第三遍读法的产出物是一份结构化笔记；本示例是笔记的校验器。
# 内置三份笔记（教学构造），输出缺项清单与汇总。模板字段即校验规则本身。

REQUIRED = ["问题", "方法", "数据集", "指标", "复现要点", "局限", "与我何干", "差异记录"]

NOTES = [
    ("笔记1（合格示例）", {
        "问题": "长上下文下注意力计算量爆炸，能否用稀疏模式把 O(N^2) 降到近线性？",
        "方法": "分块注意力 + 块间共享中心 token；公式见论文第 3 节。",
        "数据集": "合成长度 4k-128k 的文档 + 公开长文基准（论文用两个测试集）",
        "指标": "相同显存下吞吐提升 2.3 倍，长文问答准确率差 0.4 个点以内",
        "复现要点": "跑 scripts/minimal.py，seed=0，先过拟合 100 条样本验证实现",
        "局限": "块大小需手工调；短序列（<2k）无收益；作者未报告多语言结果",
        "与我何干": "我们的检索上下文默认 8k，超过就要分块——正好卡在收益区间上沿",
        "差异记录": "未复现；已记录三个存疑点（块大小 schedule、位置编码、精度设置）",
    }),
    ("笔记2（缺项 + 无数字）", {
        "问题": "提出一个新的训练技巧，据说很有效。",
        "方法": "改动了优化流程，细节见论文。",
        "数据集": "多个基准",
        "指标": "效果显著提升",                       # 无数字 -> 不合格
        "复现要点": "值得一试",                        # 无可执行信息 -> 不合格
        "局限": "无明显局限",                        # 写了「无」-> 不合格
        "差异记录": "",                              # 缺字段
        # 缺「与我何干」
    }),
    ("笔记3（缺差异记录）", {
        "问题": "少样本提示下模型能做组合推理吗？",
        "方法": "chain-of-thought 式中间步骤提示。",
        "数据集": "论文用合成组合任务 + 两个公开基准",
        "指标": "8 个示例时准确率从 21% 升到 63%",
        "复现要点": "跑 scripts/compose.py（seed=0）：合成两属性组合任务，扫示例数曲线",
        "局限": "示例数增加后收益饱和；作者未报告成本",
        "与我何干": "我们的分类 prompt 可以先试加中间步骤，零成本",
        "差异记录": "",                              # 缺字段 -> 不合格
    }),
]

EXEC_WORDS = ["脚本", "命令", "seed", "参数", "python", "运行", "代码"]
USELESS_LIMIT = ["无", "没有", "无明显局限", "无局限"]


def check_note(note):
    """返回缺项/不合格原因列表；空列表 = 通过。"""
    issues = []
    for key in REQUIRED:
        v = (note.get(key) or "").strip()
        if not v:
            issues.append(f"缺字段「{key}」")
    if note.get("指标") and not any(ch.isdigit() for ch in note["指标"]):
        issues.append("「指标」无数字：指标必须可核对，不能写「显著提升」")
    if (note.get("局限") or "").strip() in USELESS_LIMIT:
        issues.append("「局限」写了「无」：每篇都有局限，至少写「作者未报告 X」")
    if (note.get("复现要点") or "").strip() and not any(
            w in note["复现要点"] for w in EXEC_WORDS):
        issues.append("「复现要点」无可执行信息：需含脚本/命令/seed/参数")
    return issues


print("== 精读笔记校验（8 必备字段 + 3 条质量规则）==")
all_pass = 0
missing_counter = {}
for tag, note in NOTES:
    issues = check_note(note)
    if not issues:
        all_pass += 1
        print(f"{tag}: PASS")
    else:
        print(f"{tag}: FAIL")
        for i in issues:
            print(f"    - {i}")
            key = i.split("」")[0].lstrip("缺字段「")
            missing_counter[key] = missing_counter.get(key, 0) + 1

print(f"\n== 汇总：{all_pass}/{len(NOTES)} 通过 ==")
if missing_counter:
    print("缺项频次（按频次降序 = 团队培训的重点）：")
    for k, v in sorted(missing_counter.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v} 次")
else:
    print("无缺项")

print("\n结论：精读笔记的价值在结构不在字数——八个字段强制把「与我何干」和「差异记录」写出来，")
print("读法：1. 「指标」必须含数字，这是防 hype 的第一道闸（无数字的结论不可核对）；2. 「局限」不接受「无」——每篇都有局限，至少写「作者未报告什么」；3. 「复现要点」必须可执行（含脚本/命令/seed/参数），「值得一试」不是要点是感慨；4. 「差异记录」哪怕写「未复现 + 存疑点」也算数——空字段说明第三遍读法没走完；5. 缺项频次统计可以直接当团队周会的培训重点。")
