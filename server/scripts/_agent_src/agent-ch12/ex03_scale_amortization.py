# title: 规模效应与反规模效应：固定成本摊薄遇上上下文膨胀
# 数值实验（示例测算）：观察单任务成本随用量的递减与知识库膨胀带来的反弹。

C_FIX = 20000.0      # 月固定成本 ¥（示例测算）
CTX_BASE = 3000      # 基线上下文 token（示例测算）
CTX_GROWTH = 0.35    # 知识库每翻一倍，上下文 token 的增幅（经验判断）
P_IN = 0.008 / 1000
P_OUT = 0.024 / 1000
GPU_UNIT = 0.012     # 满负荷时的卡时分摊 ¥/任务（示例测算）
UTIL_MAX = 0.85      # 卡的最大可持续利用率（经验判断）
VEC = 0.004          # 向量库 ¥/任务（示例测算）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def unit_cost(q, doublings=0):
    """单任务成本：固定摊薄 + token（随 doublings 膨胀）+ 卡时（随利用率改善）+ 向量库"""
    tok_in = CTX_BASE * (1 + CTX_GROWTH) ** doublings
    tok = tok_in * P_IN + 400 * P_OUT
    util = min(UTIL_MAX, 0.30 + 0.55 * (1 - 1 / (1 + q / 20000)))  # 利用率爬坡后饱和
    gpu = GPU_UNIT * (0.30 / max(util, 1e-9))
    return C_FIX / q + tok + gpu + VEC


print("== 单任务成本 vs 用量 Q（同一知识库规模，示例测算） ==")
print(f"{pad('用量Q', 8)}{'固定摊薄':>10}{'token':>9}{'卡时':>9}{'向量库':>8}{'单任务合计':>11}")
QS = [10000, 20000, 40000, 80000, 160000]
for q in QS:
    c = unit_cost(q)
    print(f"{pad(f'{q//10000:.0f}万', 8)}{C_FIX/q:>10.3f}"
          f"{CTX_BASE*P_IN+400*P_OUT:>9.3f}"
          f"{c-CTX_BASE*P_IN-400*P_OUT-C_FIX/q-VEC:>9.3f}{VEC:>8.3f}{c:>11.3f}")

print("\n== 边际改善：用量每翻倍，单任务成本再降多少 ==")
prev = None
for q in QS:
    if prev is not None:
        print(f"  {prev//10000:.0f}万→{q//10000:.0f}万：省 ¥{unit_cost(prev)-unit_cost(q):.3f}"
              f"（固定摊薄 {C_FIX/prev:.2f}→{C_FIX/q:.2f}）")
    prev = q
print("固定摊薄按 1/Q 递减，每翻倍收益减半；16万 时该项（¥0.125）仍是卡时+向量库合计的十余倍，")
print("但绝对量已很小——继续扩量的单位经济意义让位于产能调度与下面的反规模效应。")

print("\n== 反规模效应：知识库翻倍的代价（固定 Q=8万，示例测算） ==")
print(f"{pad('知识库', 8)}{'上下文tok':>11}{'token费':>9}{'单任务合计':>11}")
for d in (0, 1, 2, 3):
    c = unit_cost(80000, doublings=d)
    tok_in = CTX_BASE * (1 + CTX_GROWTH) ** d
    print(f"{pad(f'{2**d}x', 8)}{tok_in:>11,.0f}{tok_in*P_IN+400*P_OUT:>9.3f}{c:>11.3f}")
print(f"知识库翻 8 倍：token 费 +{(CTX_BASE*(1+CTX_GROWTH)**3)/(CTX_BASE)-1:.0%}，"
      f"单任务成本 +{unit_cost(80000,3)/unit_cost(80000)-1:.0%}")

print("\n结论：规模效应让单任务成本递减（固定摊薄 + GPU 利用率爬坡至 0.85 饱和），但知识库膨胀带来反规模——上下文 token 持续上涨，")
print("读法：1. 规模效应两来源：固定成本摊薄（1/Q，边际收益每翻倍减半）、推理利用率上升（0.3→0.85 饱和后不再改善）；2. 反规模效应：用得越深上下文越长，token 成本占比不降反升，裁剪/缓存/小模型分流是对冲手段；3. 看板必须同时监控「用量 / 单任务成本 / 四元占比」三个序列，只盯总账单会在成本结构反转后才发现；4. 参数为教学假设（示例测算），曲线形状比绝对数字重要。")
