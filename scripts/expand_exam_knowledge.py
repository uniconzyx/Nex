"""补齐考研数学 / 英语 / 政治的概念学习内容（knowledge）。

原则：
  1. 只在原 items[].knowledge 上「追加」，不改动既有概念的 id / 标题，避免破坏
     前端已记录的进度与 patterns 映射；
  2. 新增概念一律挂在所属章的既有 pattern 上（后端不校验，但这样保持语义一致）；
  3. 幂等：按 id 去重，重复执行不会重复插入。

用法：python3 scripts/expand_exam_knowledge.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOW = ROOT / "content" / "_exam" / "knowledge"


def load(name: str) -> dict:
    return json.loads((KNOW / f"{name}.json").read_text(encoding="utf-8"))


def save(name: str, doc: dict) -> None:
    (KNOW / f"{name}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def add(doc: dict, topic: str, items: list[dict]) -> int:
    """把 items 追加到 topic 对应的 knowledge 列表；按 id 去重。返回新增条数。"""
    block = next((b for b in doc["items"] if b["topic"] == topic), None)
    if block is None:
        raise SystemExit(f"topic 不存在：{topic}")
    have = {k["id"] for k in block["knowledge"]}
    added = 0
    for it in items:
        if it["id"] in have:
            continue
        block["knowledge"].append(it)
        have.add(it["id"])
        added += 1
    return added


# ─────────────────────────────── 数学（一） ───────────────────────────────

M1 = {
    "m1-limits": [
        {
            "id": "m1-limits-k4",
            "title": "数列极限与夹逼准则",
            "chapter": "1.2 数列极限",
            "patterns": ["m1-limits-p1"],
            "core": "数列极限看得是「n → ∞ 的走向」，不是某一项的值。夹逼准则要求上界与下界收敛到同一个数；单调有界准则要求先证单调、再证有界。",
            "tip": "n 项和的极限几乎都是夹逼：把每项放成最大项与最小项，两边夹到同一个值。",
        },
        {
            "id": "m1-limits-k5",
            "title": "无穷小的阶与等价替换",
            "chapter": "1.3 无穷小比较",
            "patterns": ["m1-limits-p2"],
            "core": "等价无穷小替换只在乘除因子中可整体替换，加减中替换会丢高阶项、结论失真。x→0 时 sin x ~ tan x ~ arcsin x ~ arctan x ~ ln(1+x) ~ e^x−1 ~ x；1−cos x ~ x²/2。",
            "tip": "加减式想用等价替换，先把式子拆成「一个主项 + 无穷小余项」，对余项单独判阶。",
        },
        {
            "id": "m1-limits-k6",
            "title": "连续与间断点的分类",
            "chapter": "1.5 连续性与间断点",
            "patterns": ["m1-limits-p2"],
            "core": "连续 ⇔ 左极限 = 右极限 = 函数值。间断点按左右极限是否存在分：可去（都存在且相等）、跳跃（都存在但不等）、无穷、振荡（不存在且非无穷）。",
            "tip": "判间断点先求两侧极限，别一上来就套「无定义即间断」——定义域外点不叫间断点。",
        },
        {
            "id": "m1-limits-k7",
            "title": "闭区间上连续函数的四大定理",
            "chapter": "1.5 连续性的应用",
            "patterns": ["m1-limits-p1"],
            "core": "有界性、最值性、介值性、零点定理。前提都是「闭区间 + 连续」，缺一不可；开区间上这四条都可能失效。",
            "tip": "证明方程有根用零点定理：先造 F(x)，再找两点异号；证明存在 ξ 使某式成立，多半也是这套。",
        },
    ],
    "m1-derivative": [
        {
            "id": "m1-derivative-k4",
            "title": "导数定义与可导性判定",
            "chapter": "2.1 导数概念",
            "patterns": ["m1-derivative-p1"],
            "core": "可导 ⇒ 连续，反之不成立（如 y=|x| 在 0 点）。分段函数在分界点必须用定义式求左右导数，两者相等才可导。",
            "tip": "看到「f(x) 在 x0 处可导」的条件题，先写出定义式，把待求极限凑成 (f(x)−f(x0))/(x−x0) 的形状。",
        },
        {
            "id": "m1-derivative-k5",
            "title": "微分中值定理的选择",
            "chapter": "2.3 微分中值定理",
            "patterns": ["m1-derivative-p2"],
            "core": "罗尔要三点（闭连续、开可导、两端相等）；拉格朗日去掉两端相等；柯西是两个函数之比；泰勒是带余项的高阶版本。",
            "tip": "题干出现「存在 ξ 使 f'(ξ)=…」时，先把要证的式子改写成 f'(ξ) − k = 0，再反推辅助函数 F。",
        },
        {
            "id": "m1-derivative-k6",
            "title": "单调性、极值与凹凸拐点",
            "chapter": "2.4 导数的应用",
            "patterns": ["m1-derivative-p2"],
            "core": "f' 定单调，f'' 定凹凸：f''>0 为凹（下凸），f''<0 为凸。极值看 f' 变号，拐点看 f'' 变号——两者都不是「导数为 0/不存在」的充分条件。",
            "tip": "求极值一定要列表标出 f' 的符号变化；只在驻点上判断会漏掉导数不存在的极值点。",
        },
        {
            "id": "m1-derivative-k7",
            "title": "渐近线的三类求法",
            "chapter": "2.5 函数作图",
            "patterns": ["m1-derivative-p1"],
            "core": "铅直：x→a 时 f→∞；水平：x→∞ 时 f→b；斜：k=lim f(x)/x，b=lim(f(x)−kx)，两者都有限才存在。",
            "tip": "同一侧 x→+∞ 与 x→−∞ 要分开求，斜渐近线在一侧存在不代表另一侧也有。",
        },
    ],
    "m1-integral": [
        {
            "id": "m1-integral-k3",
            "title": "不定积分的换元与分部",
            "chapter": "3.1 不定积分",
            "patterns": ["m1-integral-p1"],
            "core": "第一换元（凑微分）处理「内层导数在外层」；第二换元（三角/根式代换）处理含 √(a²−x²)、√(x²±a²) 的形状。分部积分按「反对幂指三」选 u。",
            "tip": "分部积分记住 ∫u dv = uv − ∫v du，选 u 的优先级：反三角 > 对数 > 幂 > 指数 > 三角。",
        },
        {
            "id": "m1-integral-k4",
            "title": "定积分的性质与对称性",
            "chapter": "3.2 定积分",
            "patterns": ["m1-integral-p2"],
            "core": "对称区间上：奇函数积分为 0，偶函数为 2 倍半区间。周期函数在任一整周期上积分相同。比较大小先看被积函数差的符号。",
            "tip": "看到对称区间先判奇偶，这一步常能直接把复杂积分化为 0 或减半。",
        },
        {
            "id": "m1-integral-k5",
            "title": "变上限积分与求导",
            "chapter": "3.2 变上限积分",
            "patterns": ["m1-integral-p2"],
            "core": "d/dx ∫(a→φ(x)) f(t)dt = f(φ(x))·φ'(x)。上下限都是函数时两者相减；被积函数含 x 时必须先把 x 提到积分号外或换元。",
            "tip": "被积函数里混着 x 和 t 是最高频陷阱——x 不能直接当常数求导，先换元把 x 分离出去。",
        },
        {
            "id": "m1-integral-k6",
            "title": "反常积分的敛散判定",
            "chapter": "3.3 反常积分",
            "patterns": ["m1-integral-p1"],
            "core": "无穷区间与无界函数两类。p 积分：∫(1→∞) 1/x^p 在 p>1 收敛；∫(0→1) 1/x^p 在 p<1 收敛。判敛用比较判别法，找同阶参考函数。",
            "tip": "两个「p 积分」的收敛条件方向相反，最容易记混——记「远处要大指数，近处要小指数」。",
        },
    ],
    "m1-multivar": [
        {
            "id": "m1-multivar-k3",
            "title": "偏导数与全微分",
            "chapter": "4.1 多元函数微分",
            "patterns": ["m1-multivar-p1"],
            "core": "偏导存在不保证连续，更不保证可微。可微的充分条件是偏导数连续。全微分 dz = f_x dx + f_y dy。",
            "tip": "判可微必须验证 lim(Δz − f_xΔx − f_yΔy)/ρ = 0，只算两个偏导就下结论是典型错误。",
        },
        {
            "id": "m1-multivar-k4",
            "title": "复合函数与隐函数求导",
            "chapter": "4.2 多元复合求导",
            "patterns": ["m1-multivar-p1"],
            "core": "链式法则按「中间变量个数」逐层展开，别漏乘。隐函数 F(x,y,z)=0 时 z_x = −F_x/F_z，z_y = −F_y/F_z。",
            "tip": "画变量依赖树再写式子，能避免把 z 当常数或漏乘内层导数。",
        },
        {
            "id": "m1-multivar-k5",
            "title": "无条件极值与条件极值",
            "chapter": "4.3 多元函数极值",
            "patterns": ["m1-multivar-p2"],
            "core": "无条件极值：先求驻点，再用 AC−B² 判（>0 有极值，A>0 极小、A<0 极大；<0 无极值；=0 需另判）。条件极值用拉格朗日乘数法。",
            "tip": "AC−B²=0 时二阶判别失效，得回到定义或沿特殊路径考察，不能直接说「无极值」。",
        },
        {
            "id": "m1-multivar-k6",
            "title": "二重积分的坐标变换",
            "chapter": "4.4 二重积分",
            "patterns": ["m1-multivar-p2"],
            "core": "直角坐标按「先积后画」定序；极坐标适用于圆/环/扇形区域，面积元换成 r dr dθ，别漏这个 r。",
            "tip": "被积函数含 x²+y² 或区域是圆的一部分，几乎一定要转极坐标；转换后先对 θ 定范围再对 r 积分。",
        },
    ],
    "m1-ode": [
        {
            "id": "m1-ode-k3",
            "title": "可分离变量与齐次方程",
            "chapter": "5.1 一阶微分方程",
            "patterns": ["m1-ode-p1"],
            "core": "可分离：把 y 的都挪到一边、x 的都挪到另一边再积分。齐次方程令 u=y/x，化为可分离。",
            "tip": "分离变量时除以含 y 的因子，要单独检查「被除掉的因子 = 0」是否是丢掉的解。",
        },
        {
            "id": "m1-ode-k4",
            "title": "一阶线性方程与常数变易",
            "chapter": "5.2 一阶线性方程",
            "patterns": ["m1-ode-p2"],
            "core": "标准形 y' + P(x)y = Q(x)，通解 y = e^{−∫P}(∫Q·e^{∫P}dx + C)。先化成标准形再套公式，P、Q 的符号最容易错。",
            "tip": "套公式前务必把 y' 的系数除成 1；Q(x)=0 时退化为可分离变量，可用作自检。",
        },
        {
            "id": "m1-ode-k5",
            "title": "二阶常系数非齐次方程",
            "chapter": "5.3 二阶线性方程",
            "patterns": ["m1-ode-p3"],
            "core": "先解齐次得通解，再按右端项形状设特解：e^{λx}P_n(x) 型按 λ 是否为特征根决定乘 x^k（k=0,1,2）。",
            "tip": "λ 是单根乘 x、是重根乘 x²，这是最常见的失分点——先算特征根再设特解形式。",
        },
    ],
    "m1-linear": [
        {
            "id": "m1-linear-k3",
            "title": "行列式的性质与展开",
            "chapter": "6.1 行列式",
            "patterns": ["m1-linear-p1"],
            "core": "行列式对某行可加性、换行变号、某行乘 k 则行列式乘 k。按行（列）展开前先做行变换把某行化出尽量多的 0。",
            "tip": "数字行列式优先「化三角」：目标是把主对角线下方全化成 0，再连乘对角元。",
        },
        {
            "id": "m1-linear-k4",
            "title": "矩阵的秩与初等变换",
            "chapter": "6.2 矩阵",
            "patterns": ["m1-linear-p2"],
            "core": "秩 = 非零子式的最高阶数 = 行阶梯形中非零行的个数。初等变换不改变秩，但改变行列式的值。",
            "tip": "求秩统一用行变换化阶梯形，别用列变换——列变换会改变线性方程组解的结构语义。",
        },
        {
            "id": "m1-linear-k5",
            "title": "向量组的线性相关与极大无关组",
            "chapter": "6.3 向量组",
            "patterns": ["m1-linear-p2"],
            "core": "向量组线性相关 ⇔ 秩 < 向量个数。极大无关组所含向量个数即秩；其余向量可由它线性表示，表示系数在化简后的矩阵里直接读。",
            "tip": "求极大无关组时把向量按列拼成矩阵做行变换，主元所在的列就是极大无关组的成员。",
        },
    ],
    "m1-equation": [
        {
            "id": "m1-equation-k4",
            "title": "线性方程组解的判定",
            "chapter": "7.1 线性方程组",
            "patterns": ["m1-equation-p1"],
            "core": "r(A) ≠ r(A|b) 无解；r(A) = r(A|b) = n 唯一解；= r < n 无穷多解，基础解系含 n−r 个向量。",
            "tip": "含参数的方程组题，先把增广矩阵化阶梯形，再按参数取值讨论秩——不要按参数分支硬解方程。",
        },
        {
            "id": "m1-equation-k5",
            "title": "特征值与特征向量",
            "chapter": "7.2 特征值",
            "patterns": ["m1-equation-p2"],
            "core": "由 |λE − A| = 0 求特征值，再解 (λE−A)x = 0 求特征向量。迹 = 特征值之和，行列式 = 特征值之积（两条都能用来验算）。",
            "tip": "算完特征值一定用「和 = 迹、积 = 行列式」验一遍，能马上抓出计算错误。",
        },
        {
            "id": "m1-equation-k6",
            "title": "相似对角化",
            "chapter": "7.3 相似矩阵",
            "patterns": ["m1-equation-p3"],
            "core": "A 可对角化 ⇔ 有 n 个线性无关的特征向量 ⇔ 每个特征值的几何重数 = 代数重数。实对称矩阵必可正交对角化。",
            "tip": "重根特征值一定要检查它能否凑出足够多的线性无关特征向量，这是可对角化的判据。",
        },
    ],
    "m1-quadratic": [
        {
            "id": "m1-quadratic-k3",
            "title": "化二次型为标准形",
            "chapter": "8.2 二次型的标准形",
            "patterns": ["m1-quadratic-p1"],
            "core": "正交变换法：求 A 的特征值 → 单位正交特征向量 → 拼成正交矩阵 Q → x=Qy 化标准形，系数即特征值。配方法不唯一，正交变换法唯一到次序。",
            "tip": "正交变换法得到的标准形系数必然是特征值；若算出的系数不等于特征值，说明 Q 没单位正交化。",
        },
        {
            "id": "m1-quadratic-k4",
            "title": "正定二次型的判定",
            "chapter": "8.3 正定性",
            "patterns": ["m1-quadratic-p2"],
            "core": "正定 ⇔ 所有特征值 > 0 ⇔ 所有顺序主子式 > 0 ⇔ 正惯性指数 = n。必要条件：对角元全为正。",
            "tip": "判正定优先用顺序主子式（算 n 个行列式），比求全部特征值快得多。",
        },
    ],
    "m1-prob": [
        {
            "id": "m1-prob-k5",
            "title": "常见分布的识别",
            "chapter": "10.2 常见分布",
            "patterns": ["m1-prob-p2"],
            "core": "二项 B(n,p)：n 次独立重复的成功次数；泊松 P(λ)：单位时间稀有事件数，λ=np 近似二项；均匀 U(a,b)；指数 E(λ) 无记忆性；正态 N(μ,σ²)。",
            "tip": "「n 大 p 小」近似泊松，「大量独立同分布之和」近似正态——这两句能覆盖大部分分布判断题。",
        },
        {
            "id": "m1-prob-k6",
            "title": "随机变量函数的分布",
            "chapter": "10.3 函数的分布",
            "patterns": ["m1-prob-p3"],
            "core": "分布函数法最稳：先写 F_Y(y)=P(g(X)≤y)，再解不等式化成 X 的区间，求导得密度。单调 g 可用公式法 f_Y(y)=f_X(g⁻¹(y))·|d/dy g⁻¹(y)|。",
            "tip": "非单调的 g（如 X²）一定要分段，直接套公式法会漏掉另一半区间。",
        },
    ],
    "m1-stat": [
        {
            "id": "m1-stat-k3",
            "title": "三大抽样分布",
            "chapter": "11.1 抽样分布",
            "patterns": ["m1-stat-p1"],
            "core": "χ²(n)：n 个标准正态的平方和；t(n)：标准正态 ÷ √(χ²(n)/n)；F(m,n)：两个独立 χ² 各除自由度之比。",
            "tip": "看到「样本均值 − μ」配合样本方差，几乎必是 t 分布——注意分母是 S/√n。",
        },
        {
            "id": "m1-stat-k4",
            "title": "矩估计与最大似然估计",
            "chapter": "11.2 参数估计",
            "patterns": ["m1-stat-p2"],
            "core": "矩估计：让样本矩等于总体矩解出参数。最大似然：写 L(θ)=∏f(x_i;θ)，取对数求导令为 0；边界型参数直接看 L 的单调性取端点。",
            "tip": "似然函数含指数时务必先取 ln 再求导；参数在取值范围的端点上时，求导法失效，要看单调性。",
        },
    ],
}

# ─────────────────────────────── 数学（二） ───────────────────────────────

M2 = {
    "m2-limits": [
        {
            "id": "m2-limits-k4",
            "title": "无穷小的阶与等价替换",
            "chapter": "1.2 无穷小比较",
            "patterns": ["m2-limits-p1"],
            "core": "等价无穷小只可在乘除因子中整体替换；加减中替换会丢高阶项。常用：sin x ~ tan x ~ arcsin x ~ ln(1+x) ~ e^x−1 ~ x，1−cos x ~ x²/2。",
            "tip": "加减式先用泰勒展开到足够阶，比等价替换更安全。",
        },
        {
            "id": "m2-limits-k5",
            "title": "连续与间断点分类",
            "chapter": "1.3 连续性",
            "patterns": ["m2-limits-p2"],
            "core": "连续 ⇔ 左极限 = 右极限 = 函数值。间断点分可去、跳跃、无穷、振荡四类，判据是两侧极限的存在性与相等性。",
            "tip": "分段函数的分界点必须分别算左右极限，直接代入会漏判。",
        },
        {
            "id": "m2-limits-k6",
            "title": "闭区间连续函数四大定理",
            "chapter": "1.3 连续性的应用",
            "patterns": ["m2-limits-p1"],
            "core": "有界性、最值性、介值性、零点定理，前提都是闭区间连续。证明方程有根的标准套路是零点定理。",
            "tip": "证「存在 ξ 使 F(ξ)=0」，先验证 F 在两端异号，再补一句「F 在闭区间连续」。",
        },
    ],
    "m2-derivative": [
        {
            "id": "m2-derivative-k4",
            "title": "导数定义与分段点可导性",
            "chapter": "2.1 导数概念",
            "patterns": ["m2-derivative-p1"],
            "core": "可导 ⇒ 连续，反之不然。分段点可导必须用定义求左右导数并令其相等，不能直接对两段分别求导后代入。",
            "tip": "题干给「可导」条件时，优先把待求极限凑成导数定义式，比洛必达更可靠。",
        },
        {
            "id": "m2-derivative-k5",
            "title": "中值定理的选择",
            "chapter": "2.3 中值定理",
            "patterns": ["m2-derivative-p2"],
            "core": "罗尔（两端相等）、拉格朗日（一般情形）、柯西（两函数之比）。要证的式子含 ξ 与 f'(ξ) 的特定组合时，反推辅助函数是关键。",
            "tip": "把结论改写为「某函数在 ξ 处导数为 0」的形式，那个函数就是辅助函数。",
        },
        {
            "id": "m2-derivative-k6",
            "title": "单调性、极值与最值",
            "chapter": "2.4 导数的应用",
            "patterns": ["m2-derivative-p2"],
            "core": "f' 定单调；极值看 f' 变号；闭区间最值要把驻点值与端点值一起比较。",
            "tip": "求最值列三个候选：驻点、导数不存在的点、区间端点，缺一不可。",
        },
        {
            "id": "m2-derivative-k7",
            "title": "曲率与渐近线",
            "chapter": "2.5 函数作图",
            "patterns": ["m2-derivative-p1"],
            "core": "曲率 K = |y''| / (1+y'²)^{3/2}。渐近线三类：铅直、水平、斜，斜渐近线的 k、b 必须分别求极限。",
            "tip": "数二考曲率的频次不低，记公式时别漏分母的 3/2 次方。",
        },
    ],
    "m2-integral": [
        {
            "id": "m2-integral-k3",
            "title": "换元与分部积分",
            "chapter": "3.1 不定积分",
            "patterns": ["m2-integral-p1"],
            "core": "凑微分处理内层导数在外层的形状；三角代换处理含根号的形状。分部积分按「反对幂指三」定 u。",
            "tip": "含 √(a²−x²) 令 x=a sin t，含 √(x²+a²) 令 x=a tan t，含 √(x²−a²) 令 x=a sec t。",
        },
        {
            "id": "m2-integral-k4",
            "title": "定积分的对称性与周期性",
            "chapter": "3.2 定积分",
            "patterns": ["m2-integral-p2"],
            "core": "对称区间奇函数为 0、偶函数为半区间两倍；周期函数在任一整周期上积分相等。",
            "tip": "先判奇偶再看被积函数，往往能把整道积分题化简成一句话。",
        },
        {
            "id": "m2-integral-k5",
            "title": "变上限积分求导",
            "chapter": "3.2 变上限积分",
            "patterns": ["m2-integral-p2"],
            "core": "d/dx∫(a→φ(x))f(t)dt = f(φ(x))φ'(x)。被积函数含 x 时必须先换元或把 x 提出积分号。",
            "tip": "「x 与 t 混在一起」是这类题唯一的高频陷阱，先分离再求导。",
        },
        {
            "id": "m2-integral-k6",
            "title": "定积分的几何应用",
            "chapter": "3.3 应用",
            "patterns": ["m2-integral-p1"],
            "core": "面积 ∫|f−g|dx；旋转体体积绕 x 轴 π∫f²dx，绕 y 轴 2π∫x·f dx（柱壳法）；弧长 ∫√(1+y'²)dx。",
            "tip": "算面积一定要先求交点定上下限，再判哪条曲线在上——符号错了整题归零。",
        },
    ],
    "m2-ode": [
        {
            "id": "m2-ode-k3",
            "title": "可分离变量与齐次方程",
            "chapter": "4.1 一阶微分方程",
            "patterns": ["m2-ode-p1"],
            "core": "可分离直接两边积分；齐次令 u=y/x 化为可分离。注意检查被除掉的因子为零时是否丢掉解。",
            "tip": "最后一步别忘了把 u 换回 y/x，直接以 u 交卷等于没做完。",
        },
        {
            "id": "m2-ode-k4",
            "title": "一阶线性方程",
            "chapter": "4.2 一阶线性方程",
            "patterns": ["m2-ode-p2"],
            "core": "标准形 y'+P(x)y=Q(x)，通解 y=e^{−∫P}(∫Q e^{∫P}dx + C)。",
            "tip": "套公式前先把 y' 系数化为 1，P、Q 的符号是最常见的失分点。",
        },
        {
            "id": "m2-ode-k5",
            "title": "二阶常系数方程",
            "chapter": "4.3 二阶线性方程",
            "patterns": ["m2-ode-p3"],
            "core": "齐次解看特征根（两不同实根/重根/共轭复根）；非齐次特解按右端项设形式，λ 为单根乘 x、重根乘 x²。",
            "tip": "先算特征根再设特解形式，跳过这步是设错特解的头号原因。",
        },
    ],
    "m2-linear": [
        {
            "id": "m2-linear-k3",
            "title": "行列式与矩阵运算",
            "chapter": "5.1 行列式与矩阵",
            "patterns": ["m2-linear-p1"],
            "core": "行列式的可加性、换行变号、数乘某行；矩阵乘法不满足交换律，但满足结合律。",
            "tip": "数字行列式优先化三角，目标是把主对角线下方全化为 0。",
        },
        {
            "id": "m2-linear-k4",
            "title": "秩与向量组相关性",
            "chapter": "5.2 向量组",
            "patterns": ["m2-linear-p2"],
            "core": "秩 = 阶梯形非零行数；线性相关 ⇔ 秩 < 向量个数。极大无关组的主元列在化简矩阵里直接可读。",
            "tip": "一律用行变换化阶梯形求秩，列变换会改变解的结构语义。",
        },
        {
            "id": "m2-linear-k5",
            "title": "线性方程组解的判定",
            "chapter": "5.3 线性方程组",
            "patterns": ["m2-linear-p2"],
            "core": "r(A)≠r(A|b) 无解；相等且 =n 唯一解；=r<n 无穷多解，基础解系 n−r 个向量。",
            "tip": "含参数题先化阶梯形，再按秩讨论，不要按参数分支硬解。",
        },
    ],
    "m2-equation": [
        {
            "id": "m2-equation-k4",
            "title": "特征值与特征向量",
            "chapter": "6.1 特征值",
            "patterns": ["m2-equation-p1"],
            "core": "由 |λE−A|=0 求特征值，再解 (λE−A)x=0。迹 = 特征值和，行列式 = 特征值积，可用于验算。",
            "tip": "每次算完都用迹与行列式验一遍，错误率能降一大半。",
        },
        {
            "id": "m2-equation-k5",
            "title": "相似对角化",
            "chapter": "6.2 相似矩阵",
            "patterns": ["m2-equation-p2"],
            "core": "可对角化 ⇔ n 个线性无关特征向量 ⇔ 每个特征值几何重数 = 代数重数。实对称矩阵必可正交对角化。",
            "tip": "重根特征值务必检查特征向量个数是否够，这是可对角化的唯一实质判据。",
        },
        {
            "id": "m2-equation-k6",
            "title": "二次型与正定性",
            "chapter": "6.3 二次型",
            "patterns": ["m2-equation-p3"],
            "core": "正交变换化标准形，系数即特征值；正定 ⇔ 顺序主子式全 > 0 ⇔ 特征值全 > 0。",
            "tip": "判正定用顺序主子式最快，不必求全部特征值。",
        },
    ],
}

# ─────────────────────────────── 英语（一/二） ───────────────────────────────

EN_COMMON = {
    "cloze": [
        {
            "id": "k4",
            "title": "固定搭配与短语动词",
            "chapter": "完形填空",
            "core": "完形 20 题里约 1/3 考搭配而非词义：动词+介词、形容词+介词、名词+介词。选项中出现两个近义动词时，差异几乎总在搭配上。",
            "tip": "先把四个选项各自能接的介词写出来，与题干已给的介词比对，能直接排除一半。",
        },
        {
            "id": "k5",
            "title": "上下文语义场",
            "chapter": "完形填空",
            "core": "一篇完形的主题词会反复以同义/反义/上下义形式出现。空格所在句往往能被前后 1~2 句的语义场锁定，不要孤立看单句。",
            "tip": "读第一遍不看选项通读全文，先建立主题与褒贬倾向，第二遍再填。",
        },
    ],
    "reading": [
        {
            "id": "k5",
            "title": "题干定位与干扰项设计",
            "chapter": "阅读理解 A 节",
            "core": "四类干扰项：偷换主体、扩大/缩小范围、绝对化（all/never/must）、无中生有（原文没提）。正确答案几乎都是原文的合理同义改写。",
            "tip": "选项里出现 all/only/never/must 先标红，除非原文明确写了绝对表述，否则基本是错的。",
        },
        {
            "id": "k6",
            "title": "例证题与段落功能",
            "chapter": "阅读理解 A 节",
            "core": "问「作者举某例子是为了说明什么」，答案在例子**之前**的主题句或之后一句，而不是例子里本身。",
            "tip": "例证题永远向上（或向下）找论点句，紧扣例子细节的选项都是陷阱。",
        },
        {
            "id": "k7",
            "title": "态度题与语气判断",
            "chapter": "阅读理解 A 节",
            "core": "态度词分三类：正向（approval, support）、负向（critical, skeptical）、中立（objective, neutral）。「indifferent（漠不关心）」几乎从不作正确答案。",
            "tip": "找形容词/副词与转折词后的评价，作者真实态度通常藏在 however/but 之后。",
        },
    ],
    "newtype": [
        {
            "id": "k3",
            "title": "七选五的衔接判定",
            "chapter": "新题型",
            "core": "三个抓手：代词指代（this/these/it 必指前文）、逻辑连接词（however/moreover 定方向）、复现词（同词或同义重复）。",
            "tip": "先做含明显代词或连接词的题，用求解出的位置排除其他选项，比顺序硬做快得多。",
        },
        {
            "id": "k4",
            "title": "排序题的逻辑链",
            "chapter": "新题型",
            "core": "先定首段（通常给引言或背景，无代词指前文），再按时间/因果/递进关系串。每段首句的衔接词是主要线索。",
            "tip": "先锁定首段与末段，中间两段靠「代词指代 + 连接词」双向验证。",
        },
    ],
    "translation": [
        {
            "id": "k4",
            "title": "被动语态与无灵主语",
            "chapter": "翻译",
            "core": "英语被动句常含无灵主语（it is said that / it is believed that），中文宜转为主动或加泛指主语（人们认为 / 据说），直译会生硬。",
            "tip": "遇到「It is + 过去分词 + that」，先判断能否译成「据……」「人们……」再动笔。",
        },
        {
            "id": "k5",
            "title": "定语从句的拆分与前置",
            "chapter": "翻译",
            "core": "短定语从句前置译为「……的」；长定语从句（尤其非限定）拆分独立成句，用「这/它/该」承接，避免一句套一句。",
            "tip": "从句超过 8 个词就别硬塞前置，拆句比长句更符合中文习惯。",
        },
    ],
    "writing": [
        {
            "id": "k4",
            "title": "大小作文模板骨架",
            "chapter": "写作",
            "core": "小作文（应用文）三段：写信目的 → 具体内容 → 期待回复。大作文（图画/图表）三段：描述图 → 分析原因 → 总结建议。",
            "tip": "大作文第一段只描述不评论，把「描述 + 分析」搅在一起是最大的结构失分。",
        },
        {
            "id": "k5",
            "title": "高分句式与连接",
            "chapter": "写作",
            "core": "递进（moreover, what's more）、转折（however, nevertheless）、因果（consequently, hence）、举例（for instance）。每段 2~3 个连接词足够，堆砌反而扣分。",
            "tip": "背 5 个万能句式（非谓语开头、强调句、倒装、同位语、数据描述）比背整篇模板更抗查重。",
        },
    ],
    "listening": [
        {
            "id": "k4",
            "title": "听力长对话的信号词",
            "chapter": "听力",
            "core": "转折（but, however）、因果（because, so, therefore）、建议（why not, you'd better）、数字与时间（half past, quarter to）是考点密集区。",
            "tip": "听到 but/however 立刻提高警觉，其后一句八成是答案所在。",
        },
        {
            "id": "k5",
            "title": "听力做题节奏控制",
            "chapter": "听力",
            "core": "预读选项（利用读题间隙）→ 抓听到的关键词定位 → 边听边记缩写。错过一题立即放手，追题会连丢三题。",
            "tip": "预读时圈出选项中「互不相同」的那个词，那就是要靠听辨确认的信息点。",
        },
        {
            "id": "k6",
            "title": "复试口语与听力应对",
            "chapter": "听力（复试）",
            "core": "复试常见：英文自我介绍（1~2 分钟）、专业问题英文作答、听一段材料复述。评分看流利度与信息完整度，不苛求口音。",
            "tip": "自我介绍备「学业背景 → 项目/科研经历 → 报考动机」三段式，每段留一句可展开的钩子。",
        },
    ],
}

POL = {
    "pol-ma": [
        {
            "id": "pol-ma-k4",
            "title": "唯物辩证法三大规律",
            "chapter": "辩证法",
            "core": "对立统一（根本规律，揭示发展的源泉与动力）、质量互变（形式与状态）、否定之否定（方向与道路）。三者共同回答「事物为什么发展、怎样发展」。",
            "tip": "材料题里出现「既……又……」「在……中把握……」的描述，多半在考对立统一；出现「量变到质变」「曲折前进」则对应另两条。",
        },
        {
            "id": "pol-ma-k5",
            "title": "实践与认识的辩证关系",
            "chapter": "认识论",
            "patterns": ["pol-ma-p1"],
            "core": "实践是认识的来源、动力、检验标准和目的；认识对实践有能动反作用。认识的两次飞跃：感性→理性（第一次）、理性→实践（第二次）。",
            "tip": "「来源」回答从哪来，「目的」回答为什么——这两个词互换是选择题最常见陷阱。",
        },
        {
            "id": "pol-ma-k6",
            "title": "社会存在与社会意识",
            "chapter": "唯物史观",
            "core": "社会存在决定社会意识，社会意识具有相对独立性（可能超前或滞后于社会存在）。生产力与生产关系、经济基础与上层建筑的矛盾是社会发展的基本动力。",
            "tip": "看到「社会意识具有相对独立性」这一表述是对的；说「社会意识决定社会存在」则必错。",
        },
    ],
    "pol-mzt": [
        {
            "id": "pol-mzt-k4",
            "title": "新民主主义革命理论",
            "chapter": "毛泽东思想",
            "core": "总路线：无产阶级领导的、人民大众的、反对帝国主义封建主义官僚资本主义的革命。三大法宝：统一战线、武装斗争、党的建设。",
            "tip": "「领导权」是新民主主义革命的核心问题，凡淡化无产阶级领导地位的表述都错。",
        },
        {
            "id": "pol-mzt-k5",
            "title": "社会主义改造与过渡时期",
            "chapter": "社会主义改造",
            "core": "过渡时期总路线「一化三改」：逐步实现国家社会主义工业化，逐步实现对农业、手工业、资本主义工商业的社会主义改造。",
            "tip": "「一化」是主体、「三改」是两翼，说「三改是主体」即错。",
        },
        {
            "id": "pol-mzt-k6",
            "title": "中国特色社会主义理论体系",
            "chapter": "中特理论",
            "core": "邓小平理论、三个代表重要思想、科学发展观、习近平新时代中国特色社会主义思想，一脉相承又与时俱进，共同构成中特理论体系。",
            "tip": "「一脉相承」指坚持马克思主义立场观点方法，「与时俱进」指回答新的时代课题，两者不可混用。",
        },
    ],
    "pol-history": [
        {
            "id": "pol-history-k4",
            "title": "近代中国的两大历史任务",
            "chapter": "近代史纲要",
            "core": "一是争取民族独立、人民解放；二是实现国家富强、人民幸福。前者是前提，后者是目的，两者相互区别又相互联系。",
            "tip": "顺序不能颠倒：先独立解放，才能谈富强幸福。",
        },
        {
            "id": "pol-history-k5",
            "title": "三次历史性巨变",
            "chapter": "现代史纲要",
            "core": "辛亥革命（推翻帝制）、新中国成立与社会主义制度建立（站起来）、改革开放（富起来）与新时代（强起来）。",
            "tip": "「三次巨变」的经典表述对应孙中山、毛泽东、邓小平三位代表人物，答题时可作结构骨架。",
        },
        {
            "id": "pol-history-k6",
            "title": "史纲材料题的答法",
            "chapter": "史纲答题",
            "core": "三步：先定性（事件性质与历史地位）→ 再讲史实（时间、内容、意义）→ 最后升华（对当代的启示）。只罗列史实不升华，得分不超过一半。",
            "tip": "材料题结尾务必写一句「这启示我们……」，这是史纲主观题的固定得分点。",
        },
    ],
    "pol-ethics": [
        {
            "id": "pol-ethics-k4",
            "title": "社会主义核心价值观",
            "chapter": "思想道德",
            "core": "国家层面：富强、民主、文明、和谐；社会层面：自由、平等、公正、法治；个人层面：爱国、敬业、诚信、友善。",
            "tip": "三个层面各四个词共 12 个，顺序固定，选择题常考「某词属于哪个层面」。",
        },
        {
            "id": "pol-ethics-k5",
            "title": "法治思维的基本内容",
            "chapter": "法治",
            "core": "法律至上、权力制约、公平正义、权利保障、正当程序。全面依法治国要求科学立法、严格执法、公正司法、全民守法。",
            "tip": "「十六字方针」四句分别对应立法、执法、司法、守法四个环节，错位是最常见的选项陷阱。",
        },
        {
            "id": "pol-ethics-k6",
            "title": "道德与法律的关系",
            "chapter": "道德与法律",
            "core": "道德与法律相辅相成：道德是法律的基础与补充，法律是道德的底线与保障。二者调整范围、实现方式、约束力不同，不可互相替代。",
            "tip": "说「法律可以解决一切道德问题」或「道德比法律更重要」都是错的——两者是并重关系。",
        },
    ],
    "pol-current": [
        {
            "id": "pol-current-k3",
            "title": "中国式现代化的五个特征",
            "chapter": "时政",
            "core": "人口规模巨大、全体人民共同富裕、物质文明与精神文明相协调、人与自然和谐共生、走和平发展道路。",
            "tip": "五个特征要能按顺序说出来，材料题问「中国式现代化与西方现代化的区别」，答案就是逐条对照这五点。",
        },
        {
            "id": "pol-current-k4",
            "title": "人类命运共同体",
            "chapter": "时政",
            "core": "核心是建设持久和平、普遍安全、共同繁荣、开放包容、清洁美丽的世界。主张共商共建共享的全球治理观。",
            "tip": "「五个世界」是固定表述，与「五个特征」不是一回事，答题时别混。",
        },
        {
            "id": "pol-current-k5",
            "title": "主观题答题模板（肖四肖八方向）",
            "chapter": "主观题",
            "core": "四步：原理定位（点明考的是哪一原理/哪一思想）→ 材料对应（引材料中的具体表述）→ 原理展开（把该原理的完整表述写出来）→ 结合升华（联系现实意义）。",
            "tip": "肖四肖八的价值在「预测方向 + 提供答题话术」，背答案要拆成四步结构记，而不是整段死记。",
        },
    ],
}


def main() -> int:
    total = 0

    for name, spec in (("math-m1", M1), ("math-m2", M2)):
        doc = load(name)
        n = sum(add(doc, topic, items) for topic, items in spec.items())
        save(name, doc)
        print(f"{name}: +{n} 概念")
        total += n

    for name, prefix in (("english-e1", "e1"), ("english-e2", "e2")):
        doc = load(name)
        n = 0
        for topic_short, items in EN_COMMON.items():
            topic = f"{prefix}-{topic_short}"
            if not any(b["topic"] == topic for b in doc["items"]):
                continue
            payload = []
            for it in items:
                payload.append({
                    "id": f"{topic}-{it['id']}",
                    "title": it["title"],
                    "chapter": it["chapter"],
                    "patterns": [],
                    "core": it["core"],
                    "tip": it["tip"],
                })
            n += add(doc, topic, payload)
        save(name, doc)
        print(f"{name}: +{n} 概念")
        total += n

    doc = load("politics-pol")
    n = 0
    for topic, items in POL.items():
        payload = []
        for it in items:
            payload.append({
                "id": it["id"],
                "title": it["title"],
                "chapter": it["chapter"],
                "patterns": it.get("patterns", []),
                "core": it["core"],
                "tip": it["tip"],
            })
        n += add(doc, topic, payload)
    save(doc and "politics-pol", doc)
    print(f"politics-pol: +{n} 概念")
    total += n

    print(f"\n合计新增 {total} 个概念")
    return 0


if __name__ == "__main__":
    sys.exit(main())
