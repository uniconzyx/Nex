#!/usr/bin/env python
"""生成数学一、数学二的题库（阶段16）。

做法：每类题写一个「模板函数」，给定参数返回题干/选项/答案/推导。
数值全部用 Fraction 精确计算，答案由程序算出而不是手写，避免出现「解析对、答案错」。
数二 = 8 个专题；数一 = 数二全部 + 级数 + 概率 + 统计，由 M1_EXTRA 追加。

每题的四层结构里，framework 直接取自 frameworks/*.json 的同 id 题型，
保证「题目讲解」与「题型框架」永远一致，不会各写一套。
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"


def fs(x) -> str:
    """分数转字符串：整数不带分母，负数带负号。"""
    f = Fraction(x)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


NL = chr(92) + "n"  # 生成文本里的换行，避免源码转义踩坑


def cf(k) -> str:
    """系数：1 省略，其余照写。"""
    return "" if k == 1 else str(k)


def xp(e: int) -> str:
    """x 的 e 次方：1 次省略指数，0 次写成 1。"""
    if e == 0:
        return "1"
    return "x" if e == 1 else f"x^{e}"


def load_patterns(exam: str, subj: str) -> dict[str, dict]:
    # 408 的框架文件叫 408-ds.json；数学/英语/政治叫 m2.json / e1.json / pol.json（与 _meta 的 subject key 一致）
    name = f"{exam}-{subj}.json" if exam == "408" else f"{subj}.json"
    data = json.loads((EXAM / "frameworks" / name).read_text(encoding="utf-8"))
    out = {}
    for t in data["topics"]:
        for p in t["patterns"]:
            out[p["id"]] = p
    return out


def q(qid, topic, kid, pattern, typ, stem, approach, note, solution,
      options=None, correct=None, text=None, diff=3) -> dict:
    item = {
        "id": qid,
        "topic": topic,
        "knowledge": kid,
        "type": typ,
        "diff": diff,
        "stem": stem,
        "answer": {"correct": correct} if typ == "choice" else {"text": text},
        "explain": {
            "right": approach,
            "wrong": "常见错误：" + note,
            "link": kid,
        },
        "walkthrough": {
            "framework": {"pattern": pattern},
            "approach": approach,
            "points": [{"id": kid, "note": note}],
            "solution": solution,
        },
    }
    if options:
        item["options"] = options
    return item


# ====================================================================== 数二模板
def c1(a, b):
    """lim (sin ax − ax)/(b x³)。"""
    ans = Fraction(-a ** 3, 6 * b)
    opts = [fs(ans), fs(Fraction(a ** 3, 6 * b)), fs(Fraction(-a ** 3, 3 * b)),
            fs(Fraction(a ** 3, 3 * b))]
    order = [0, 1, 2, 3]
    k = (a + b) % 4
    opts = opts[k:] + opts[:k]
    u = "x" if a == 1 else f"{a}x"
    return dict(
        stem=f"极限 lim(x→0) [sin({u}) − {u}] / ({b}x³) 等于（　）",
        options=opts, correct=opts.index(fs(ans)),
        approach=f"分子在 0 附近是「正弦减去线性项」，本质是 sin({u}) 的泰勒展开缺了三次项，"
                 f"展开到 x³ 就能看出主部，再除以 {b}x³。",
        note="把 sin u 直接换成 u 得到 0，或展开只到一次项，都会丢掉唯一非零的主部。",
        solution=(f"由 sin u = u − u³/6 + o(u³)，令 u = {u}：\n"
                  f"sin({u}) = {u} − {a ** 3}x³/6 + o(x³)。\n"
                  f"所以分子 = −{a ** 3}x³/6 + o(x³)，除以 {b}x³ 后极限为 "
                  f"−{a ** 3}/(6×{b}) = {fs(ans)}。\n"
                  f"要点：分子最低次项是三次，这不是 0/0 型洛必达能一眼看出的结构，"
                  f"但用一次洛必达再展开同样得到该值。"),
    )


def c2(a, b):
    """lim (1 + a/x)^(bx) = e^{ab}。"""
    ans = f"e^({a * b})"
    opts = [ans, f"e^({a}/{b})", f"e^({a * b * b})", "1"]
    return dict(
        stem=f"极限 lim(x→∞) (1 + {a}/x)^({b}x) 等于（　）",
        options=opts, correct=0,
        approach=f"这是 1^∞ 型，先取对数把指数 {b}x 拿下来，再用 ln(1+t) ~ t 求极限，"
                 f"最后还原成 e 的指数。",
        note="直接把 (1+a/x) 当成 1，得到 1；或把指数上的 b 漏掉，写成 e^a。",
        solution=(f"设 y = (1 + {a}/x)^({b}x)，取对数：\n"
                  f"ln y = {b}x·ln(1 + {a}/x)。\n"
                  f"当 x→∞ 时 ln(1 + {a}/x) ~ {a}/x，故 ln y → {b}x·{a}/x = {a * b}。\n"
                  f"因此原极限 = e^({a * b})。\n"
                  f"通法：1^∞ 型统一写成 e^(lim (底−1)×指数)，这里 (底−1) = {a}/x。"),
    )


def c3(a, b):
    """y = x³ − 3a x² + b 的拐点。"""
    y = b - 2 * a ** 3
    ans = f"({a}, {y})"
    opts = [ans, f"({a}, {b})", f"(0, {b})", f"({a}, {b + 2 * a ** 3})"]
    return dict(
        stem=f"曲线 y = x³ − {3 * a}x² + {b} 的拐点是（　）",
        options=opts, correct=0,
        approach="拐点看二阶导变号：先求 y″，令其为零得候选横坐标，再验证两侧凹凸性相反。",
        note="把一阶导为零的驻点当拐点；或只算出 x 就停手，忘了代回原方程求纵坐标。",
        solution=(f"y′ = 3x² − {6 * a}x，y″ = 6x − {6 * a}。\n"
                  f"令 y″ = 0 得 x = {a}；当 x < {a} 时 y″ < 0（凸），x > {a} 时 y″ > 0（凹），"
                  f"凹凸性确实改变，故为拐点。\n"
                  f"代回：y = {a ** 3} − {3 * a}·{a ** 2} + {b} = {y}。\n"
                  f"拐点为 ({a}, {y})。注意拐点是曲线上的点，必须写成坐标。"),
    )


def c4(a):
    """f(x) = x³ − 3a²x 的极大值点。"""
    ans = f"x = −{a}"
    opts = [ans, f"x = {a}", "x = 0", f"x = ±{a}"]
    return dict(
        stem=f"设 a > 0，函数 f(x) = x³ − {3 * a * a}x 的极大值点是（　）",
        options=opts, correct=0,
        approach="先求 f′ 定驻点，再用二阶导或一阶导的符号变化判断哪一个是极大。",
        note="只解出驻点 ±a 就选「±a」，没有区分极大与极小。",
        solution=(f"f′(x) = 3x² − {3 * a * a} = 3(x − {a})(x + {a})，驻点 x = ±{a}。\n"
                  f"f″(x) = 6x：f″(−{a}) = −{6 * a} < 0，故 x = −{a} 为极大值点；\n"
                  f"f″({a}) = {6 * a} > 0，故 x = {a} 为极小值点。\n"
                  f"所以极大值点是 x = −{a}。三次函数的两个驻点一极大一极小，符号看二阶导最稳。"),
    )


def c5(m):
    """∫₀^{π/2} sin^m x cos x dx = 1/(m+1)。"""
    ans = Fraction(1, m + 1)
    opts = [fs(ans), fs(Fraction(1, m)), fs(Fraction(1, m + 2)), "1"]
    return dict(
        stem=f"定积分 ∫(0→π/2) sin^{{{m}}}x·cos x dx 等于（　）",
        options=opts, correct=0,
        approach="被积函数里 sin 的幂次乘着 cos，正好是 sin x 的导数，直接令 t = sin x 换元。",
        note="把 cos x 当成常数提到积分号外；换元后忘记把上下限从 x 换成 t。",
        solution=(f"令 t = sin x，则 dt = cos x dx。\n"
                  f"x = 0 时 t = 0，x = π/2 时 t = 1，故\n"
                  f"原式 = ∫(0→1) t^{{{m}}} dt = 1/({m} + 1) = {fs(ans)}。\n"
                  f"这类「sin 的幂 × cos」的定积分一律换元，不要试图用分部积分展开。"),
    )


def c6(a):
    """y = x² 与 y = ax 围成的面积 = a³/6。"""
    ans = Fraction(a ** 3, 6)
    opts = [fs(ans), fs(Fraction(a ** 3, 3)), fs(Fraction(a ** 2, 2)), fs(Fraction(a ** 3, 2))]
    return dict(
        stem=f"曲线 y = x² 与直线 y = {a}x 所围图形的面积为（　）",
        options=opts, correct=0,
        approach="先求交点定积分区间，再判断哪条曲线在上方，用「上减下」列面积积分。",
        note="不判断上下位置，直接 ∫(x² − ax) 得到负值；或交点只取 x = 0 一个。",
        solution=(f"联立 x² = {a}x 得 x = 0 与 x = {a}，积分区间为 [0, {a}]。\n"
                  f"在该区间内 {a}x ≥ x²，故\n"
                  f"S = ∫(0→{a}) ({a}x − x²) dx = {a}·{a}²/2 − {a}³/3 = {fs(ans)}。\n"
                  f"答案 {fs(ans)}。面积必须为正，若算出负数说明上下位置判断反了。"),
    )


def c7(a, b):
    """z = x²y + xy² 在 (a,b) 的全微分。"""
    fx = 2 * a * b + b ** 2
    fy = a ** 2 + 2 * a * b
    ans = f"{fx}dx + {fy}dy"
    opts = [ans, f"{fy}dx + {fx}dy", f"{2 * a * b}dx + {2 * a * b}dy",
            f"{a ** 2 + b ** 2}dx + {a ** 2 + b ** 2}dy"]
    return dict(
        stem=f"函数 z = x²y + xy² 在点 ({a}, {b}) 处的全微分为（　）",
        options=opts, correct=0,
        approach="全微分 dz = z_x dx + z_y dy，分别对 x、y 求偏导后代入具体点。",
        note="把两个偏导数写反（dx 配 z_y），或求偏导时把另一变量也一起求了。",
        solution=(f"z_x = 2xy + y²，在 ({a}, {b}) 处为 2×{a}×{b} + {b}² = {fx}；\n"
                  f"z_y = x² + 2xy，在 ({a}, {b}) 处为 {a}² + 2×{a}×{b} = {fy}。\n"
                  f"故 dz = {fx}dx + {fy}dy。\n"
                  f"注意 dx 配的是对 x 的偏导，次序写反是最常见的手误。"),
    )


def c8(a, b):
    """A = [[a,b],[b,a]] 的特征值。"""
    ans = f"{a + b} 和 {a - b}"
    opts = [ans, f"{a} 和 {b}", f"{a + b} 和 {a + b}", f"{a - b} 和 {a - b}"]
    return dict(
        stem=f"矩阵 A = [[{a}, {b}], [{b}, {a}]] 的两个特征值是（　）",
        options=opts, correct=0,
        approach="用 |λE − A| = 0 展开，或直接套 2×2 对称矩阵 [[a,b],[b,a]] 的结论 λ = a ± b。",
        note="把对角元当成特征值，直接选 a 和 b。",
        solution=(f"|λE − A| = (λ − {a})² − {b}² = 0，\n"
                  f"故 λ − {a} = ±{b}，λ₁ = {a + b}，λ₂ = {a - b}。\n"
                  f"验算：λ₁ + λ₂ = {2 * a} = 迹，λ₁λ₂ = {a * a - b * b} = 行列式，均吻合。\n"
                  f"结论：形如 [[a,b],[b,a]] 的矩阵，特征值必为 a ± b。"),
    )


def c9(a):
    """det [[a,1,0],[1,a,1],[0,1,a]] = a³ − 2a。"""
    ans = a ** 3 - 2 * a
    opts = [f"{ans}", f"{a ** 3}", f"{a ** 3 - a}", f"{a ** 3 + 2 * a}"]
    return dict(
        stem=f"三阶行列式 |{a} 1 0; 1 {a} 1; 0 1 {a}| 的值为（　）",
        options=opts, correct=0,
        approach="按第一行展开，或先化上三角；三对角行列式也可直接用递推式 D_n = aD_{n−1} − D_{n−2}。",
        note="展开时符号写错（余子式前漏掉 (−1)^{i+j}）。",
        solution=(f"按第一行展开：\n"
                  f"D = {a}·|{a} 1; 1 {a}| − 1·|1 1; 0 {a}| + 0\n"
                  f"  = {a}({a}² − 1) − 1·({a} − 0)\n"
                  f"  = {a}³ − {a} − {a} = {ans}。\n"
                  f"用递推式验算：D₃ = {a}D₂ − D₁ = {a}({a}² − 1) − {a} = {ans}，一致。"),
    )


def c10(a):
    """[[a,1],[1,a]] 正定 ⇔ a > 1。"""
    opts = ["a > 1", "a > 0", "a > −1", "a ≠ 1"]
    return dict(
        stem=f"二次型 f = {a}x₁² + 2x₁x₂ + {a}x₂² 正定的充要条件是（　）",
        options=opts, correct=0,
        approach="写出二次型矩阵，用顺序主子式全大于零列不等式。",
        note="只看 a > 0 就下结论，漏掉二阶顺序主子式。",
        solution=(f"二次型矩阵 A = [[{a}, 1], [1, {a}]]。\n"
                  f"一阶顺序主子式 {a} > 0；二阶顺序主子式 {a}² − 1 > 0。\n"
                  f"由 {a} > 0 且 ({a} − 1)({a} + 1) > 0 得 a > 1（a 为参数时还需 a > 0 前提）。\n"
                  f"故充要条件是 a > 1。也可用特征值：{a} ± 1 全正 ⇔ {a} > 1。"),
    )


def c11(a, c):
    """y' + ay = 0, y(0)=c → y = c e^{-ax}。"""
    ans = f"{c}e^(−{a}x)"
    opts = [ans, f"{c}e^({a}x)", f"{c}e^(−x)", f"−{c}e^(−{a}x)"]
    return dict(
        stem=f"微分方程 y′ + {a}y = 0 满足 y(0) = {c} 的特解是（　）",
        options=opts, correct=0,
        approach="一阶齐次线性方程，分离变量或直接套 y = Ce^(−∫P dx)。",
        note="指数符号写反；或把初值代进通解后忘记回代常数。",
        solution=(f"分离变量：dy/y = −{a}dx，积分得 ln|y| = −{a}x + C₁，\n"
                  f"即 y = Ce^(−{a}x)。代入 y(0) = {c} 得 C = {c}。\n"
                  f"故特解 y = {c}e^(−{a}x)。\n"
                  f"验证：y′ = −{a}·{c}e^(−{a}x)，代回方程得 0，且 y(0) = {c}。"),
    )


def c12(a):
    """∬_{x²+y²≤a²} (x²+y²) dσ = π a⁴/2。"""
    ans = f"{fs(Fraction(a ** 4, 2))}π"
    opts = [ans, f"{a ** 4}π", f"{fs(Fraction(a ** 2, 2))}π", f"{2 * a ** 4}π"]
    return dict(
        stem=f"二重积分 ∬(D) (x² + y²) dσ，其中 D 为圆域 x² + y² ≤ {a * a}，其值为（　）",
        options=opts, correct=0,
        approach="圆域 + 被积函数含 x²+y²，直接上极坐标，dσ = r dr dθ。",
        note="极坐标漏掉雅可比因子 r，算成 ∫∫r² dr dθ 少一个量级。",
        solution=(f"令 x = r cosθ，y = r sinθ，则 x² + y² = r²，dσ = r dr dθ，\n"
                  f"区域为 0 ≤ θ ≤ 2π，0 ≤ r ≤ {a}。\n"
                  f"原式 = ∫(0→2π)dθ ∫(0→{a}) r²·r dr = 2π·{a}⁴/4 = π{a}⁴/2。\n"
                  f"答案 {ans}。判断依据：被积函数是 r²，乘雅可比 r 后是 r³，积分得 a⁴/4。"),
    )


def b1(a):
    """y = x^a ln x 的极小值 = −1/(a e)。"""
    return dict(
        stem=f"函数 y = x^{a}·ln x（x > 0）的极小值为 ______。",
        text=f"−1/({a}e)",
        approach="对数与幂函数相乘，求导后用「驻点 + 单调性」定极小，再代回求值。",
        note="只写驻点 x = e^(−1/a) 不代回求函数值；或把极小值写成极小值点。",
        solution=(f"y′ = {a}{xp(a - 1)}·ln x + {xp(a - 1)} = {xp(a - 1)}({a}ln x + 1)。\n"
                  f"令 y′ = 0，因 x > 0 故 {a}ln x + 1 = 0，ln x = −1/{a}，x = e^(−1/{a})。\n"
                  f"当 0 < x < e^(−1/{a}) 时 y′ < 0，当 x > e^(−1/{a}) 时 y′ > 0，故该点为极小值点。\n"
                  f"代回：y = e^(−1/{a})·(−1/{a}) = −1/({a}e)。\n"
                  f"注意题目问的是极小值（函数值），不是极小值点。"),
    )


def b2(a):
    """y = x² 与 y = a² 围成区域面积 = 4a³/3。"""
    return dict(
        stem=f"由曲线 y = x² 与直线 y = {a * a} 所围图形的面积为 ______。",
        text=fs(Fraction(4 * a ** 3, 3)),
        approach="先求交点定区间，再按「上减下」积分；图形关于 y 轴对称，可算一半乘 2。",
        note="交点只取正的一侧，面积算成一半；或把 y = a² 当成 x = a²。",
        solution=(f"联立 x² = {a * a} 得 x = ±{a}，区间 [−{a}, {a}]，上方是 y = {a * a}。\n"
                  f"S = ∫(−{a}→{a}) ({a * a} − x²) dx = 2∫(0→{a}) ({a * a} − x²) dx\n"
                  f"  = 2({a * a}·{a} − {a}³/3) = 2·(2{a}³/3) = {fs(Fraction(4 * a ** 3, 3))}。\n"
                  f"利用对称性可少算一半，但别忘乘 2。"),
    )


def b3(a):
    """det [[a,1,1],[1,a,1],[1,1,a]] = (a−1)²(a+2)。"""
    val = (a - 1) ** 2 * (a + 2)
    return dict(
        stem=f"行列式 |{a} 1 1; 1 {a} 1; 1 1 {a}| 的值为 ______。",
        text=str(val),
        approach="各行加到第一行提出公因子，再化上三角——这是「对角元相同、其余全 1」型行列式的固定套路。",
        note="直接按定义展开六项，符号容易错；或提公因子时把 (a+2) 写成 (a−2)。",
        solution=(f"三行都加到第一行：第一行变为 ({a} + 2, {a} + 2, {a} + 2)，提出 ({a} + 2)：\n"
                  f"D = ({a} + 2)·|1 1 1; 1 {a} 1; 1 1 {a}|。\n"
                  f"再用第一行乘 −1 加到其余两行，得\n"
                  f"D = ({a} + 2)·|1 1 1; 0 {a}−1 0; 0 0 {a}−1| = ({a} + 2)({a} − 1)² = {val}。\n"
                  f"结论可记：对角 a、其余 1 的 n 阶行列式 = (a − 1)^(n−1)·(a + n − 1)。"),
    )


def b4(a, b):
    """A = [[a,1],[0,b]]，|A| = ab，特征值 a,b。"""
    return dict(
        stem=f"矩阵 A = [[{a}, 1], [0, {b}]] 的特征值为 ______。",
        text=f"{a} 和 {b}",
        approach="上三角矩阵的特征值就是对角元，不必解特征方程。",
        note="把副对角元的 1 也算进特征值；或误以为特征值是 a+1 与 b。",
        solution=(f"A 是上三角矩阵，|λE − A| = (λ − {a})(λ − {b}) = 0，\n"
                  f"故 λ₁ = {a}，λ₂ = {b}。\n"
                  f"验证：迹 = {a + b} = λ₁ + λ₂，行列式 = {a * b} = λ₁λ₂，均吻合。\n"
                  f"记住结论：三角矩阵的特征值就是主对角线元素，副对角元不影响。"),
    )


def ex(r: int) -> str:
    """指数写法：1 → e^x，−1 → e^(−x)，其余 e^(rx)。"""
    if r == 1:
        return "e^x"
    if r == -1:
        return "e^(−x)"
    return f"e^({r}x)"


def k1(a):
    """∫ x^a ln x dx = x^(a+1)/(a+1)·ln x − x^(a+1)/(a+1)² + C。"""
    n = a + 1
    ans = ("x^" + str(n) + "/" + str(n) + "·ln x − x^" + str(n) + "/" + str(n) + "² + C")
    return dict(
        stem="求不定积分 ∫ x^" + str(a) + "·ln x dx。",
        text=ans,
        approach=("幂函数乘对数，按「反对幂指三」令 u=ln x、dv=x^" + str(a) +
                  "dx，分部积分一次即可；积分后幂次升到 " + str(n) + "，注意分母同步变成 " +
                  str(n) + " 与 " + str(n) + "²。"),
        note="选错 u 与 dv（令 u=x^a），越积越复杂；或漏掉积分常数 C。",
        solution=("令 u = ln x，dv = x^" + str(a) + "dx，则 du = dx/x，v = x^" + str(n) + "/" + str(n) + "。" + NL +
                  "∫x^" + str(a) + "ln x dx = (x^" + str(n) + "/" + str(n) + ")ln x − ∫(x^" + str(n) + "/" + str(n) + ")(1/x)dx" + NL +
                  "= (x^" + str(n) + "/" + str(n) + ")ln x − (1/" + str(n) + ")∫x^" + str(a) + "dx" + NL +
                  "= " + ans + "。" + NL +
                  "求导验算：d/dx[x^" + str(n) + "/" + str(n) + "·ln x] = x^" + str(a) + "ln x + x^" + str(a) + "/" + str(n) +
                  "，减去 x^" + str(a) + "/" + str(n) + " 后正好只剩 x^" + str(a) + "ln x，正确。"),
    )


def k2(r1, r2):
    """y″ − (r1+r2)y′ + r1r2 y = 0 的通解。"""
    s = r1 + r2
    p = r1 * r2
    ans = "y = C₁" + ex(r1) + " + C₂" + ex(r2)
    sgn = "−" if s >= 0 else "+"
    psgn = "+" if p >= 0 else "−"
    return dict(
        stem=("求微分方程 y″ " + sgn + " " + str(abs(s)) + "y′ " + psgn + " " + str(abs(p)) +
              "y = 0 的通解。"),
        text=ans,
        approach=("这是二阶常系数齐次线性方程：先写特征方程 r² " + sgn + " " + str(abs(s)) +
                  "r " + psgn + " " + str(abs(p)) + " = 0，它能分解成 (r−" + str(r1) + ")(r−" + str(r2) +
                  ") = 0，两个相异实根，直接写两个指数项相加。"),
        note="特征方程符号抄错；两个不同实根却写成 (C₁+C₂x)e^(rx)（那是重根的形式）。",
        solution=("特征方程 r² " + sgn + " " + str(abs(s)) + "r " + psgn + " " + str(abs(p)) + " = 0，" + NL +
                  "因式分解得 (r − " + str(r1) + ")(r − " + str(r2) + ") = 0，故 r₁ = " + str(r1) +
                  "，r₂ = " + str(r2) + "。" + NL +
                  "相异实根的通解形式为 y = C₁e^(r₁x) + C₂e^(r₂x)，" + NL +
                  "代入得 " + ans + "，C₁、C₂ 为任意常数。" + NL +
                  "三种情形要分清：相异实根 → 两个指数项；重根 → (C₁+C₂x)e^(rx)；共轭复根 α±βi → e^(αx)(C₁cosβx+C₂sinβx)。"),
    )


def k3(a):
    """∬_D x dσ，D 由 y=x² 与 y=ax 围成，值为 a⁴/12。"""
    from fractions import Fraction as F
    val = F(a ** 4, 12)
    return dict(
        stem=("计算二重积分 ∬(D) x dσ，其中 D 由 y = x² 与 y = " + str(a) + "x 围成。"),
        text=fs(val),
        approach=("先联立求交点：x² = " + str(a) + "x 得 x = 0 与 x = " + str(a) +
                  "；在 0 ≤ x ≤ " + str(a) + " 上 " + str(a) + "x ≥ x²，按 X 型区域先对 y 积分，内层上限 " +
                  str(a) + "x、下限 x²。"),
        note="积分次序选错导致上下限难写；或把两条曲线的上下关系弄反，结果变负。",
        solution=("联立 y = x² 与 y = " + str(a) + "x 得交点 (0,0) 与 (" + str(a) + "," + str(a * a) + ")。" + NL +
                  "在 0 ≤ x ≤ " + str(a) + " 上 " + str(a) + "x ≥ x²，故 D = {(x,y) | 0 ≤ x ≤ " + str(a) +
                  ", x² ≤ y ≤ " + str(a) + "x}。" + NL +
                  "原式 = ∫(0→" + str(a) + ") x dx ∫(x²→" + str(a) + "x) dy = ∫(0→" + str(a) +
                  ") x(" + str(a) + "x − x²) dx" + NL +
                  "= ∫(0→" + str(a) + ")(" + str(a) + "x² − x³)dx = " + str(a) + "·" + str(a ** 3) + "/3 − " +
                  str(a ** 4) + "/4 = " + fs(val) + "。" + NL +
                  "答案 " + fs(val) + "。先对 y 积分时，内层上下限是函数、外层是常数，这是 X 型区域的标准写法。"),
    )


def k4(a, b):
    """A = [[a,b],[b,a]] 的特征值与特征向量。"""
    l1, l2 = a + b, a - b
    return dict(
        stem=("求矩阵 A = [[" + str(a) + ", " + str(b) + "], [" + str(b) + ", " + str(a) +
              "]] 的特征值与对应的特征向量。"),
        text=("λ₁ = " + str(l1) + "，特征向量 k(1,1)ᵀ；λ₂ = " + str(l2) + "，特征向量 k(1,−1)ᵀ（k ≠ 0）"),
        approach=("先用 |λE−A| = (λ−" + str(a) + ")² − " + str(b) + "² = 0 得 λ = " + str(a) + " ± " +
                  str(b) + "；再对每个特征值解 (λE−A)x = 0，得到两个正交的特征向量。"),
        note="求出特征值就结束，没求特征向量；或特征向量漏写 k≠0。",
        solution=("|λE − A| = (λ−" + str(a) + ")² − " + str(b) + "² = 0，" + NL +
                  "故 λ₁ = " + str(l1) + "，λ₂ = " + str(l2) + "。" + NL +
                  "λ = " + str(l1) + " 时，(λE−A)x = 0 化为 x₁ = x₂，特征向量 k(1,1)ᵀ，k ≠ 0。" + NL +
                  "λ = " + str(l2) + " 时，(λE−A)x = 0 化为 x₁ = −x₂，特征向量 k(1,−1)ᵀ，k ≠ 0。" + NL +
                  "两个特征向量正交，符合实对称矩阵不同特征值的特征向量必正交的结论。" + NL +
                  "验算：λ₁+λ₂ = " + str(2 * a) + " = 迹，λ₁λ₂ = " + str(a * a - b * b) + " = 行列式。"),
    )


def s1():
    return dict(
        stem="级数 Σ(n=1→∞) 1/[n(n+1)] 的和为（　）",
        options=["1", "1/2", "2", "发散"], correct=0,
        approach="裂项相消：1/[n(n+1)] = 1/n − 1/(n+1)，前 n 项和只剩首尾两项。",
        note="看到分母是 n² 量级就判发散；或裂项后忘记取极限。",
        solution=("部分和 S_n = Σ(k=1..n)[1/k − 1/(k+1)] = 1 − 1/(n+1)。\n"
                  "令 n→∞，S_n → 1，故级数收敛且和为 1。\n"
                  "这里通项是 1/n² 量级，p = 2 > 1，本来就可判收敛；裂项只是顺便求出和。\n"
                  "注意：收敛 ≠ 和为 1，只有能求出部分和闭式时才谈具体和。"),
    )


def s2():
    return dict(
        stem="幂级数 Σ(n=1→∞) xⁿ/n 的收敛半径 R 为（　）",
        options=["1", "2", "1/2", "∞"], correct=0,
        approach="用比值法求半径：R = lim|a_n/a_{n+1}|，再单独判两个端点。",
        note="只算半径不判端点，把收敛域写成 [−1,1]；或在 x = −1 处误判发散。",
        solution=("a_n = 1/n，R = lim(n→∞) |a_n/a_{n+1}| = lim n/(n+1) · ... = 1。\n"
                  "端点 x = 1：Σ1/n 为调和级数，发散；\n"
                  "端点 x = −1：Σ(−1)ⁿ/n 为交错级数，通项单调趋于 0，收敛（条件收敛）。\n"
                  "故收敛域为 [−1, 1)，收敛半径 R = 1。\n"
                  "记住：半径只有一个数，端点必须代回原级数单独判断。"),
    )


def p1():
    return dict(
        stem="甲乙两箱各有 3 个球，甲箱 2 红 1 白，乙箱 1 红 2 白。任取一箱再取一球，取到红球的概率为（　）",
        options=["1/2", "2/3", "1/3", "5/6"], correct=0,
        approach="「任取一箱」构成完备事件组，用全概率公式按箱分情况加权。",
        note="直接算 (2+1)/(3+3) = 1/2 碰巧对，但换成箱子球数不等就会错；应写全概率式。",
        solution=("设 A₁ = 取甲箱，A₂ = 取乙箱，B = 取到红球。\n"
                  "P(A₁) = P(A₂) = 1/2，P(B|A₁) = 2/3，P(B|A₂) = 1/3。\n"
                  "由全概率公式：P(B) = (1/2)(2/3) + (1/2)(1/3) = 1/3 + 1/6 = 1/2。\n"
                  "答案 1/2。若两箱球数不同，必须先加权再相加，不能把红球数直接除以总球数。"),
    )


def p2():
    return dict(
        stem="设 X ~ U(0, 2)，则 E(X²) = （　）",
        options=["4/3", "2/3", "1", "2"], correct=0,
        approach="均匀分布密度为 1/2，按定义算 E(X²) = ∫x²f(x)dx，再用 D(X) 验算。",
        note="把 E(X²) 与 [E(X)]² 混为一谈，得到 1。",
        solution=("X 的密度 f(x) = 1/2（0 ≤ x ≤ 2）。\n"
                  "E(X²) = ∫(0→2) x²·(1/2)dx = (1/2)·(8/3) = 4/3。\n"
                  "验算：E(X) = 1，D(X) = (2−0)²/12 = 1/3，\n"
                  "由 D(X) = E(X²) − [E(X)]² 得 E(X²) = 1/3 + 1 = 4/3，一致。\n"
                  "注意 E(X²) ≠ [E(X)]²，两者相差一个方差。"),
    )


def p3():
    return dict(
        stem="设总体 X 服从参数为 λ 的指数分布，密度 f(x) = λe^(−λx)（x > 0），x₁,…,x_n 为样本，则 λ 的最大似然估计量为（　）",
        options=["1/x̄", "x̄", "1/x̄²", "n/x̄"], correct=0,
        approach="写似然函数 → 取对数 → 对 λ 求导令零 → 解出估计量。",
        note="不取对数直接对乘积求导；或把估计量写成 λ 的矩估计以外形式。",
        solution=("似然函数 L(λ) = Π λe^(−λx_i) = λⁿ·e^(−λΣx_i)。\n"
                  "取对数：ln L = n ln λ − λΣx_i。\n"
                  "求导：d(ln L)/dλ = n/λ − Σx_i = 0，解得 λ̂ = n/Σx_i = 1/x̄。\n"
                  "二阶导 −n/λ² < 0，确为极大值点。\n"
                  "结论：指数分布参数的最大似然估计是样本均值的倒数。"),
    )


def s3():
    return dict(
        stem="幂级数 Σ(n=1→∞) xⁿ/n² 的收敛域是（　）",
        options=["[−1, 1]", "(−1, 1)", "[−1, 1)", "(−1, 1]"], correct=0,
        approach="先求半径 R = 1，再分别把 x = ±1 代入原级数判敛散。",
        note="只写开区间 (−1,1)，漏判端点。",
        solution=("a_n = 1/n²，R = lim |a_n/a_{n+1}| = lim (n+1)²/n² = 1。\n"
                  "x = 1：Σ1/n² 是 p = 2 的 p 级数，收敛；\n"
                  "x = −1：Σ(−1)ⁿ/n² 绝对收敛（因为 Σ1/n² 收敛）。\n"
                  "故收敛域为 [−1, 1]，两个端点都要。\n"
                  "对比 Σxⁿ/n 的收敛域 [−1,1)：端点是否收敛取决于通项里 n 的幂次。"),
    )


def p4():
    return dict(
        stem="设 X ~ N(0,1)，Y = X²，则当 y > 0 时 Y 的密度 f_Y(y) 为（　）",
        options=["(1/√(2πy))·e^(−y/2)", "(1/√(2π))·e^(−y/2)",
                 "(1/2)e^(−y/2)", "(1/√(2πy))·e^(−y)"], correct=0,
        approach="Y = X² 非单调，必须用分布函数法：F_Y(y) = P(−√y ≤ X ≤ √y)，再求导。",
        note="直接用公式法只取一支，得到一半的结果（漏掉负根那一支）。",
        solution=("当 y > 0 时，F_Y(y) = P(X² ≤ y) = P(−√y ≤ X ≤ √y) = Φ(√y) − Φ(−√y)。\n"
                  "求导：f_Y(y) = φ(√y)·(1/(2√y)) + φ(−√y)·(1/(2√y)) = φ(√y)/√y。\n"
                  "代入标准正态密度 φ(u) = (1/√(2π))e^(−u²/2)，得\n"
                  "f_Y(y) = (1/√(2πy))·e^(−y/2)，y > 0。\n"
                  "这正是自由度为 1 的 χ² 分布密度，可作为结论记住。"),
    )


M2_CHOICE = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12]
M2_BLANK = [b1, b2, b3, b4]
M2_CALC = [k1, k2, k3, k4]

M1_EXTRA_CHOICE = [s1, s2, p1, p2, p3, s3, p4]


def build_questions(exam: str, subj: str, extra_choice) -> dict:
    pats = load_patterns(exam, subj)
    # 模板与知识点/题型的绑定：每个模板固定挂一个知识点，避免「题目与考点两张皮」
    bind = {
        "c1": (f"{subj}-limits", f"{subj}-limits-k2", f"{subj}-limits-p1"),
        "c2": (f"{subj}-limits", f"{subj}-limits-k1", f"{subj}-limits-p1"),
        "c3": (f"{subj}-derivative", f"{subj}-derivative-k3", f"{subj}-derivative-p2"),
        "c4": (f"{subj}-derivative", f"{subj}-derivative-k3", f"{subj}-derivative-p2"),
        "c5": (f"{subj}-integral", f"{subj}-integral-k1", f"{subj}-integral-p1"),
        "c6": (f"{subj}-integral", f"{subj}-integral-k3", f"{subj}-integral-p2"),
        "c7": (f"{subj}-multivar", f"{subj}-multivar-k1", f"{subj}-multivar-p1"),
        "c8": (f"{subj}-equation", f"{subj}-equation-k2", f"{subj}-equation-p1"),
        "c9": (f"{subj}-linear", f"{subj}-linear-k1", f"{subj}-linear-p1"),
        "c10": (f"{subj}-quadratic", f"{subj}-quadratic-k2", f"{subj}-quadratic-p2"),
        "c11": (f"{subj}-ode", f"{subj}-ode-k1", f"{subj}-ode-p1"),
        "c12": (f"{subj}-multivar", f"{subj}-multivar-k3", f"{subj}-multivar-p2"),
        "b1": (f"{subj}-derivative", f"{subj}-derivative-k3", f"{subj}-derivative-p2"),
        "b2": (f"{subj}-integral", f"{subj}-integral-k3", f"{subj}-integral-p2"),
        "b3": (f"{subj}-linear", f"{subj}-linear-k1", f"{subj}-linear-p1"),
        "b4": (f"{subj}-equation", f"{subj}-equation-k2", f"{subj}-equation-p1"),
        "k1": (f"{subj}-integral", f"{subj}-integral-k1", f"{subj}-integral-p1"),
        "k2": (f"{subj}-ode", f"{subj}-ode-k2", f"{subj}-ode-p3"),
        "k3": (f"{subj}-multivar", f"{subj}-multivar-k3", f"{subj}-multivar-p2"),
        "k4": (f"{subj}-equation", f"{subj}-equation-k2", f"{subj}-equation-p3"),
        "s1": (f"{subj}-series", f"{subj}-series-k1", f"{subj}-series-p1"),
        "s2": (f"{subj}-series", f"{subj}-series-k3", f"{subj}-series-p2"),
        "s3": (f"{subj}-series", f"{subj}-series-k3", f"{subj}-series-p2"),
        "p1": (f"{subj}-prob", f"{subj}-prob-k1", f"{subj}-prob-p1"),
        "p2": (f"{subj}-prob", f"{subj}-prob-k4", f"{subj}-prob-p3"),
        "p3": (f"{subj}-stat", f"{subj}-stat-k2", f"{subj}-stat-p1"),
        "p4": (f"{subj}-prob", f"{subj}-prob-k3", f"{subj}-prob-p2"),
    }
    items, used = [], set()

    def emit(key, fn, args, typ):
        topic, kid, pid = bind[key]
        d = fn(*args)
        n = len(items) + 1
        qid = f"q-{subj}-{key}-{n:02d}"
        assert qid not in used, qid
        used.add(qid)
        item = q(qid, topic, kid, pid, typ, d["stem"], d["approach"], d["note"], d["solution"],
                 options=d.get("options"), correct=d.get("correct"), text=d.get("text"))
        # framework 从框架文件回填，保证与题型定义完全一致
        p = pats[pid]
        item["walkthrough"]["framework"].update({
            "title": p["title"],
            "steps": p["steps"],
            "trap": p["traps"][0],
        })
        items.append(item)

    # 选择题：每模板 2 个变体，凑 24 题（8 套 × 3）
    variants = {
        "c1": [(2, 3), (3, 2)], "c2": [(1, 2), (3, 2)], "c3": [(1, 1), (2, 1)],
        "c4": [(1,), (2,)], "c5": [(2,), (4,)], "c6": [(1,), (2,)],
        "c7": [(1, 1), (2, 3)], "c8": [(1, 2), (2, 1)], "c9": [(1,), (2,)],
        "c10": [(2,), (3,)], "c11": [(1, 2), (2, 3)], "c12": [(2,), (3,)],
        "s1": [()], "s2": [()], "s3": [()], "p1": [()], "p2": [()], "p3": [()], "p4": [()],
    }
    order = [f"c{i}" for i in range(1, 13)] + extra_choice
    for key in order:
        fn = {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5, "c6": c6, "c7": c7,
              "c8": c8, "c9": c9, "c10": c10, "c11": c11, "c12": c12,
              "s1": s1, "s2": s2, "s3": s3, "p1": p1, "p2": p2, "p3": p3, "p4": p4}[key]
        for args in variants[key]:
            emit(key, fn, args, "choice")

    # 填空：4 模板 × 2 变体 = 8（8 套 × 1）
    for key, fn, args in [("b1", b1, (2,)), ("b2", b2, (1,)), ("b3", b3, (2,)), ("b4", b4, (1, 2)),
                          ("b1", b1, (3,)), ("b2", b2, (2,)), ("b3", b3, (3,)), ("b4", b4, (2, 3))]:
        emit(key, fn, args, "blank")

    # 解答：4 模板 × 2 变体 = 8（8 套 × 1）
    # 4 个模板 × 2 组参数 = 8 道，保证两套卷之间不出现同一道题
    for key, args in [("k1", (1,)), ("k2", (1, 2)), ("k3", (1,)), ("k4", (2, 1)),
                      ("k1", (2,)), ("k2", (2, 3)), ("k3", (2,)), ("k4", (3, 1))]:
        emit(key, {"k1": k1, "k2": k2, "k3": k3, "k4": k4}[key], args, "calc")

    # 按专题轮转重排：组卷时每套连取 3 题，轮转序能保证这 3 题来自不同专题。
    # 否则「数一补充的级数/概率题」全排在尾部，8 套卷一道都轮不到。
    def rr(lst):
        groups: dict[str, list] = {}
        for x in lst:
            groups.setdefault(x["topic"], []).append(x)
        out, i = [], 0
        while len(out) < len(lst):
            for g in groups.values():
                if i < len(g):
                    out.append(g[i])
            i += 1
        return out

    items = (rr([x for x in items if x["type"] == "choice"])
             + [x for x in items if x["type"] == "blank"]
             + [x for x in items if x["type"] == "calc"])
    return {"subject": subj, "exam": exam, "items": items}


def write(exam: str, subj: str, data: dict) -> None:
    p = EXAM / "questions" / f"{exam}-{subj}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    print(f"{exam}-{subj}: {len(data['items'])} 题 {dict(Counter(x['type'] for x in data['items']))}")


if __name__ == "__main__":
    write("math", "m2", build_questions("math", "m2", []))
    write("math", "m1", build_questions("math", "m1", ["s1", "s2", "s3", "p1", "p2", "p3", "p4"]))
