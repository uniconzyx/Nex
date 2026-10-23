# title: 技术雷达四象限分类器：Adopt / Trial / Assess / Hold 的规则与不稳定边界
# 四个可观测指标：成熟度、岗位需求、变更速度（越高越不稳）、与当前项目匹配度。
# 规则先给出象限，再做阈值 ±0.05 的敏感性测试——雷达的价值在于「边界上的项」被显式讨论。
ITEMS = [
    # 名称, 成熟度, 岗位需求, 变更速度, 项目匹配
    ("Python 异步/HTTP", 0.97, 0.95, 0.10, 0.90),
    ("Prompt 四段式", 0.92, 0.93, 0.25, 0.95),
    ("JSON Schema 严格模式", 0.88, 0.82, 0.30, 0.90),
    ("RAG（混合检索+重排）", 0.86, 0.90, 0.45, 0.92),
    ("LangGraph 状态机", 0.78, 0.72, 0.55, 0.80),
    ("MCP 工具协议", 0.62, 0.58, 0.80, 0.70),
    ("vLLM 推理服务", 0.84, 0.66, 0.40, 0.55),
    ("LoRA 微调", 0.90, 0.60, 0.25, 0.35),
    ("多智能体框架", 0.45, 0.40, 0.85, 0.30),
    ("端侧小模型", 0.52, 0.35, 0.70, 0.20),
    ("Agent 自进化/记忆", 0.30, 0.30, 0.90, 0.25),
    ("提示词自动优化（APE）", 0.38, 0.18, 0.60, 0.15),
]

def quadrant(m, d, c, f):
    # 先判 Hold：不稳且不匹配；再判 Adopt/Trial/Assess
    if c >= 0.75 and f < 0.5:
        return "Hold"
    if m >= 0.85 and d >= 0.75 and c <= 0.45:
        return "Adopt"
    if m >= 0.70 and d >= 0.55 and c <= 0.65:
        return "Trial"
    if m >= 0.35:
        return "Assess"
    return "Hold"

def ttl(m, c):
    # 预计「可以进生产」的月数（经验公式）
    return max(1, round((1 - m) * 12 + c * 6))

print("=" * 82)
print("表 1  技术雷达（阈值：Adopt m≥.85 d≥.75 c≤.45；Hold c≥.75 且 fit<.5）")
print("=" * 82)
print(f"{'技术':<24}{'成熟':>6}{'需求':>6}{'变更':>6}{'匹配':>6}{'象限':>8}{'TTL(月)':>9}")
buckets = {"Adopt": [], "Trial": [], "Assess": [], "Hold": []}
for name, m, d, c, f in ITEMS:
    q = quadrant(m, d, c, f)
    buckets[q].append(name)
    print(f"{name:<24}{m:>6.2f}{d:>6.2f}{c:>6.2f}{f:>6.2f}{q:>8}{ttl(m, c):>9}")

print("\n" + "=" * 82)
print("表 2  四象限清单（Adopt 可直接用；Trial 限一个项目；Assess 只做 spike；Hold 不投入）")
print("=" * 82)
for q in ("Adopt", "Trial", "Assess", "Hold"):
    print(f"  {q:<7}({len(buckets[q])})：{'、'.join(buckets[q]) if buckets[q] else '—'}")

print("\n" + "=" * 82)
print("表 3  阈值 ±0.05 的敏感性：哪些项在边界上摇摆")
print("=" * 82)
base = {name: quadrant(m, d, c, f) for name, m, d, c, f in ITEMS}
moved = 0
for name, m, d, c, f in ITEMS:
    variants = {
        quadrant(m + 0.05, d, c, f), quadrant(m - 0.05, d, c, f),
        quadrant(m, d + 0.05, c, f), quadrant(m, d - 0.05, c, f),
        quadrant(m, d, c + 0.05, f), quadrant(m, d, c - 0.05, f),
    }
    if len(variants) > 1 or base[name] not in variants:
        moved += 1
        print(f"  {name:<24} 基准 {base[name]:<7} 可能变成 {'/'.join(sorted(variants))}")
print(f"\n{len(ITEMS)} 项中有 {moved} 项对阈值敏感（{moved/len(ITEMS):.0%}）。")

print("\n结论：真正稳定的只有 Python 异步、Prompt 四段式、Schema 严格模式这类「接口级」技术；")
print("      带「多智能体/自进化」的项成熟度低、变更快，只能 Assess，不能写进交付承诺。")
print("读法：雷达每季度重跑一次，重点看边界项而不是象限数量；")
print("      面试里说「我们在 Trial 阶段用它，并设了回退方案」比说「它是最新技术」可信得多。")
