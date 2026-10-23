# title: POC 验收指标可测性检查：四要素缺一即「不可验收」
# 失效边界（教学示例）：把「效果显著提升」式虚指标挡在合同之外。

NEED = ["dataset", "metric_rule", "threshold", "retest_cycle"]

# 内置清单：前 3 条可验收，后 3 条为典型虚指标（缺要素已标出）
ITEMS = [
    {"name": "自动解决率", "dataset": "500条月度冻结集（双方共同标注）",
     "metric_rule": "无需人工即关闭且72h无重复进线", "threshold": ">=60%",
     "retest_cycle": "月度复测"},
    {"name": "误答率", "dataset": "同一冻结集", "metric_rule": "业务方双人抽检全等判定",
     "threshold": "<=5%", "retest_cycle": "周抽检100条"},
    {"name": "首token延迟P95", "dataset": "压测流量回放", "metric_rule": "服务端计时",
     "threshold": "<3s", "retest_cycle": "月度压测"},
    {"name": "响应体验", "dataset": "", "metric_rule": "业务方主观评价", "threshold": "",
     "retest_cycle": ""},
    {"name": "准确率提升", "dataset": "历史数据", "metric_rule": "与上线前对比",
     "threshold": "显著", "retest_cycle": ""},
    {"name": "知识覆盖", "dataset": "知识库导出", "metric_rule": "覆盖率",
     "threshold": "", "retest_cycle": "季度"},
]

SUGGEST = {
    "dataset": "补：冻结集规模、来源、标注方（建议双方共同标注并签字口径）",
    "metric_rule": "补：判定口径（全等/归一化/容差），边界案例裁剪规则",
    "threshold": "补：可判定数值（>=x 或 <=x），删掉「显著」「良好」等主观词",
    "retest_cycle": "补：复测频率与未达标后果（整改或退出）",
}


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def poc_check(items):
    bad = []
    for it in items:
        missing = [k for k in NEED if not str(it.get(k, "")).strip()]
        if missing:
            bad.append((it["name"], missing))
    return bad


bad = poc_check(ITEMS)
print("== POC 验收指标可测性检查（四要素：数据集/口径/阈值/复测频率） ==")
print(f"共 {len(ITEMS)} 条指标：可验收 {len(ITEMS)-len(bad)} 条，不可验收 {len(bad)} 条\n")
for name, missing in bad:
    print(f"[不可验收] {name}")
    print(f"  缺失要素: {', '.join(missing)}")
    for k in missing:
        print(f"  - {SUGGEST[k]}")
    print()

ok_names = [it["name"] for it in ITEMS if all(str(it.get(k, '')).strip() for k in NEED)]
print(f"[可验收] {', '.join(ok_names)}")

print("\n结论：验收口径写不清，Demo 再漂亮也会在验收会上变成扯皮会——四要素缺一即不可验收，")
print("读法：1. 数据集要冻结并版本化，双方共同标注 50~500 条并签字口径，它是所有验收的唯一基准；2. 阈值必须是可判定数值，「显著」「良好」这类词在合同里等于没有标准，解释权归付款方；3. 复测频率防推广期退化（模型静默升级/知识库膨胀/流量变难三因叠加，经验判断主流 API 商均发生过不影响版本号的调优）；4. 判定口径要预先定义：全等还是归一化、数值容差、大小写与单位换算，写进 schema 附件。")
