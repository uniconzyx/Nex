# title: 能力矩阵四维自评与雷达图：把「我会什么」画成可对照的缺口
import numpy as np

# 四维自评与目标（目标 = JD 反推的要求等级，concept/02 §2）
DIMS = ["工程", "模型", "产品", "业务"]
SELF = {"工程": 3, "模型": 2, "产品": 3, "业务": 2}
TARGET = {"工程": 4, "模型": 3, "产品": 2, "业务": 2}      # 来自 JD 反推
ARTS = {"工程": 3, "模型": 1, "产品": 2, "业务": 1}        # 可出示产物数
PEER = {"工程": 2, "模型": 2, "产品": 3, "业务": 2}        # mentor 他评


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


R = 10  # 雷达图半径（格子数）


def vertices(levels):
    """四轴（上/右/下/左）多边形的顶点坐标，等级 0-5 映射到半径 0-R。"""
    pts = []
    for i, d in enumerate(DIMS):
        ang = np.pi / 2 - i * np.pi / 2
        r = levels[d] / 5 * R
        pts.append((r * np.cos(ang), r * np.sin(ang)))
    return pts


def inside(poly, x, y):
    """射线法判断点是否在多边形内。"""
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                c = not c
    return c


self_poly, tgt_poly = vertices(SELF), vertices(TARGET)
print("== 1) 能力矩阵雷达图（上=工程 右=模型 下=产品 左=业务，#=自评 +=目标 *=重合）==")
for row in range(R, -R - 1, -1):
    line = []
    for col in range(-R, R + 1):
        s, t = inside(self_poly, col, row), inside(tgt_poly, col, row)
        line.append("*" if s and t else "#" if s else "+" if t else ".")
    print("   " + "".join(line))
print("   图例: '#' 只出自评区, '+' 只出目标区, '*' 重合, '.' 两者都不覆盖")

print("\n== 2) 逐维对照表（差距 = 目标 − 自评，负值=待补）==")
print(f"{pad('维度', 6)}{pad('自评', 5)}{pad('他评', 5)}{pad('目标', 5)}"
      f"{pad('差距', 5)}{pad('产物数', 7)}{'待补级别'}")
for d in DIMS:
    gap = TARGET[d] - SELF[d]
    todo = f"L{SELF[d]}→L{TARGET[d]}" if gap > 0 else ("持平" if gap == 0 else "超标")
    print(f"{pad(d, 6)}{pad(str(SELF[d]), 5)}{pad(str(PEER[d]), 5)}{pad(str(TARGET[d]), 5)}"
          f"{pad(str(gap), 5)}{pad(str(ARTS[d]), 7)}{todo}")

# 3) 路径加权匹配度（concept/02 §1 的权重表）
PATHS = {"应用开发": {"工程": .45, "模型": .20, "产品": .20, "业务": .15},
         "Agent 工程": {"工程": .40, "模型": .30, "产品": .15, "业务": .15},
         "解决方案": {"工程": .30, "模型": .20, "产品": .25, "业务": .25},
         "AI 产品": {"工程": .15, "模型": .25, "产品": .40, "业务": .20}}
print("\n== 3) 同一张矩阵在四条路径下的加权匹配度（等级/5 × 权重）==")
for p, w in PATHS.items():
    fit = sum(SELF[d] * w[d] for d in DIMS) / 5 * 100
    bar = "#" * int(round(fit / 2))
    print(f"   {pad(p, 8)}{fit:5.1f}/100  {bar}")

print("\n结论：矩阵的用法不是「填完打分」，而是生成补证清单——自评与目标的缺口（工程 +1、模型 +1，差距=目标−自评）")
print("读法：1. 雷达图的重合区 '*' 是达标区，只出 '+' 的扇区就是 12 个月计划的任务来源；2. 同一张矩阵换路径权重就得到不同的匹配度，先定路径再配资源；3. 产物数低于自评等级的维度（模型 1 个产物撑 2 级）是下一个被面试官问穿的维度；4. 本示例只用固定数据与几何计算做自评可视化，不调用任何外部服务。")
