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
