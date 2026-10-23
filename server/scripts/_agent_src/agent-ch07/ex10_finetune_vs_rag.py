# title: 微调 vs RAG 的成本/收益决策表
# 把「该微调还是该 RAG」变成可算的账：prompt 长度差、训练一次性成本、知识更新频率。
import numpy as np

# 价格假设（每百万 token，美元；仅用于演示口径，接入前按当期价目替换）
PRICE_IN, PRICE_OUT = 0.50, 1.50
Q_MONTH = [10_000, 50_000, 200_000, 1_000_000]

def monthly(q, prompt_tokens, out_tokens=300, extra=0.0):
    return q * (prompt_tokens * PRICE_IN + out_tokens * PRICE_OUT) / 1e6 + extra

FT_TRAIN_ONCE = 80.0          # 8 卡时 × $10，500 条数据一次 LoRA
FT_DATA = 2400.0              # 标注/清洗/留出集建设的人力折价
FT_MONTHLY_MAINT = 60.0       # 评测回归与重训流水线维护
RAG_INFRA = 70.0              # 向量库/检索服务月费

print("假设：RAG prompt 3000 token（检索片段），微调后 prompt 300 token，输出均 300 token")
print(f"微调一次性：训练 ${FT_TRAIN_ONCE:.0f} + 数据 ${FT_DATA:.0f}，每月维护 ${FT_MONTHLY_MAINT:.0f}\n")
print(f"{'月请求量':>10}{'RAG 月成本':>12}{'FT 月成本':>11}{'FT 摊销(12月)':>15}{'更便宜':>8}")
for q in Q_MONTH:
    rag = monthly(q, 3000, extra=RAG_INFRA)
    ft = monthly(q, 300, extra=FT_MONTHLY_MAINT)
    ft_amort = ft + (FT_TRAIN_ONCE + FT_DATA) / 12
    print(f"{q:>10,}{rag:>12,.0f}{ft:>11,.0f}{ft_amort:>15,.0f}"
          f"{'FT' if ft_amort < rag else 'RAG':>8}")

q_be = ((FT_TRAIN_ONCE + FT_DATA) / 12 + FT_MONTHLY_MAINT - RAG_INFRA) / ((3000 - 300) * PRICE_IN / 1e6)
print(f"\n静态盈亏平衡点 ≈ 每月 {q_be:,.0f} 次请求（只算 token 差、维护费与训练摊销）")

print("\n知识更新频率的影响（每月重训一次）：")
print(f"{'月请求':>8}{'RAG':>9}{'FT 重训':>10}{'差额':>9}")
for q in (50_000, 200_000):
    rag = monthly(q, 3000, extra=RAG_INFRA)
    ft = monthly(q, 300, extra=FT_TRAIN_ONCE + 200)    # 重训 + 重新标注增量
    print(f"{q:>8,}{rag:>9,.0f}{ft:>10,.0f}{ft-rag:>+9,.0f}")

print("\n决策表（除成本外的四个维度）：")
rows = [
    ("知识每天变", "RAG", "重新索引分钟级；微调追不上"),
    ("知识季度级稳定 + 固定话术", "微调", "短 prompt 省钱，风格稳定"),
    ("需要引用出处/可审计", "RAG", "检索片段可回溯，微调不能"),
    ("输出格式/语气/工具调用协议", "微调", "这是行为，不是知识"),
    ("长尾事实问答、实体多", "RAG", "微调记不牢，且容易幻觉"),
    ("低延迟、无检索服务", "微调", "省掉一次检索往返"),
]
for scene, choice, why in rows:
    print(f"  {scene:<24}{choice:<6}{why}")

print("\n结论：决策顺序是「先问知识是否高频变化、是否需要溯源，再算请求量」。")
print("读法：本假设下月请求低于 10 万的内部工具，微调的数据与维护成本摊不回来，RAG 更快上线；")
print("      高频 + 知识稳定 + 要短 prompt 的场景，微调才在 6~12 个月内回本；")
print("      知识每天变时，重训成本会把微调的节省吃掉 —— 先看更新频率，再算钱。")
print("      两者不互斥：微调学行为，RAG 供知识，组合常是最优解。")
