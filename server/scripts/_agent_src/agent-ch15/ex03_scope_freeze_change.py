# title: MVP 范围冻结与变更影响评估：关键路径增量、冻结接口与变更日志
# 纯标准库实现：范围说明书（做什么/不做什么）、变更请求的三级决策与日志。


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


class ScopeStatement:
    """范围说明书：in_scope 每条需求可判定完成与否；not_in_scope 具体到能反驳。"""

    def __init__(self, in_scope, not_in_scope, frozen_interfaces):
        self.in_scope = in_scope            # [(需求, 验收口径)]
        self.not_in_scope = not_in_scope    # [(不做项, 理由)]
        self.frozen = set(frozen_interfaces)  # 冻结接口：动它 = 高风险

    def verifiable(self):
        bad = [n for n, crit in self.in_scope if not crit or len(crit) < 8]
        return bad


SCOPE = ScopeStatement(
    in_scope=[
        ("上传一周散乱记录（文本粘贴）", "≥2000 字文本可提交并返回任务 id"),
        ("自动归类为 4 类（进展/风险/数据/计划）", "50 条黄金集上归类准确率 ≥ 70%"),
        ("按模板生成周报初稿", "输出含 4 个固定小节，可一键复制"),
        ("存疑句标注", "每条存疑标注带原文片段，可点击定位"),
        ("容器一键启动", "陌生人按 README 10 分钟内跑起来"),
    ],
    not_in_scope=[
        ("多语言", "目标用户单一语种，差异化收益低"),
        ("移动端适配", "演示场景为桌面端"),
        ("微信/OAuth 登录", "demo 阶段不需要账号体系"),
        ("个性化推荐", "无历史数据，冷启动无意义"),
        ("知识库 > 100 篇", "超上限需重做索引，延期 > 2 天"),
    ],
    frozen_interfaces={"周报模板 schema", "归类枚举 4 类", "评测程序入口"},
)


def assess_change(scope, name, cp_delta, touches_frozen, touches_evaluated, alternative):
    """变更影响评估：工期增量 + 是否动冻结接口 + 是否动已评测模块 -> 三级决策。"""
    risks = []
    if touches_frozen:
        risks.append("动冻结接口")
    if touches_evaluated:
        risks.append("动已评测模块")
    if cp_delta <= 1 and not risks:
        decision = "接纳"
    elif cp_delta <= 1 and risks:
        decision = "推迟(风险)"
    else:
        decision = "拒绝"
    return {"name": name, "cp_delta": cp_delta, "risks": risks,
            "decision": decision, "alternative": alternative}


REQUESTS = [
    ("加一个导出 PDF", 0.5, False, False, "W3 后 backlog 优先"),
    ("归类改成 6 类（更细）", 5, True, True, "先跑一轮黄金集看 4 类瓶颈再议"),
    ("加一个暗黑模式", 1, False, False, ""),
    ("周报模板加一节「风险」", 2, True, False, "在「风险」内容并入计划节，不动 schema"),
]

print("== 1) 范围说明书：做什么（可判定）与不做什么（可反驳） ==")
print(f"  in_scope {len(SCOPE.in_scope)} 条，not_in_scope {len(SCOPE.not_in_scope)} 条，"
      f"冻结接口 {len(SCOPE.frozen)} 个")
bad = SCOPE.verifiable()
print(f"  验收口径可判定性自检：{'全部可判定' if not bad else '不可判定: ' + str(bad)}")
for item, why in SCOPE.not_in_scope[:3]:
    print(f"    不做「{item}」：{why}")

print("\n== 2) 变更影响评估（口径：+N 天且不动冻结接口/已评测模块才可接纳） ==")
print("  " + pad("变更请求", 26) + pad("工期增量", 10) + pad("风险", 22) + "决策")
log = []
for name, delta, frozen, evaluated, alt in REQUESTS:
    r = assess_change(SCOPE, name, delta, frozen, evaluated, alt)
    log.append(r)
    risk = ",".join(r["risks"]) if r["risks"] else "-"
    print("  " + pad(name, 26) + pad(f"+{delta} 天", 10) + pad(risk, 22) + r["decision"])

print("\n== 3) 变更日志（日期/请求/评估/决策 四字段，答辩时证明交付受控） ==")
for i, r in enumerate(log, 1):
    line = (f"  2026-10-2{i} | {r['name']} | +{r['cp_delta']}天 "
            f"风险:{','.join(r['risks']) or '无'} | {r['decision']}")
    if r["alternative"]:
        line += f" | 替代:{r['alternative']}"
    print(line)

accepted = [r for r in log if r["decision"] == "接纳"]
print(f"\n  接纳 {len(accepted)}/{len(log)} 个；关键路径净增量 = "
      f"{sum(r['cp_delta'] for r in accepted)} 天（单请求 <=1 天才够格；累计增量超过浮动时间就要重新排期）")
print("  「暗黑模式」+1 天不动接口被接纳；「6 分类」+5 天且动冻结接口被拒绝——")
print("  拒绝不等于不做，是带着替代方案进 backlog，等第 2 轮错误分析说话")

print("\n结论：范围冻结把「加个小功能」从人情题变成计算题——先算关键路径增量与冻结面，再决策；")
print("读法：1. 冻结单要同时写「做什么（可判定）+ 不做什么（可反驳）」，后者是拒绝时的依据；2. 接纳线画在「+1 天且不动冻结接口/已评测模块」，其余一律推迟或拒绝；3. 变更日志四字段（日期/请求/评估/决策）同时是答辩材料；4. 本示例为本地模拟，真实评估还应叠加人力与成本两项。")
