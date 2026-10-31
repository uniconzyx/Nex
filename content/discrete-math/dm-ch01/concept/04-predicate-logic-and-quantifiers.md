# 谓词逻辑与量词：把"所有人"写成公式

## 1. 背景/动机

命题逻辑的最小单位是"整句话"，无法表达"所有人""存在一个"。
谓词逻辑引入个体、谓词与量词，才有了"∀x(Student(x)→Pass(x))"这种表达力。
代价是：可满足性从"可判定但指数"变成"半可判定"（一阶逻辑没有通用判定算法）。

对工程师来说，谓词逻辑的实用形态是 **Datalog / Prolog / 规则引擎**：
它们限制在一阶逻辑的一个可判定子集（Horn 子句），换来"一定能算完"。

## 2. 定义/要点

```text
∀x P(x)      所有个体都满足 P
∃x P(x)      至少有一个个体满足 P
∀x(P(x)→Q(x))   所有 P 都是 Q（注意用 -> 而不是 ^）
∃x(P(x)∧Q(x))   存在同时满足 P 与 Q 的个体（注意用 ^ 而不是 ->）
```

量词否定律（考试必考，也最容易错）：

```text
~∀x P(x)        ≡ ∃x ~P(x)
~∃x P(x)        ≡ ∀x ~P(x)
~∀x (P(x)->Q(x)) ≡ ∃x (P(x) ^ ~Q(x))     <- 不是 ∃x(P(x)->~Q(x))
```

辖域与变元：

```text
∀x ( P(x) ^ ∃y R(x,y) )      x 的辖域是整个括号；y 只在内层被约束
∀x P(x) ^ ∃x Q(x)            两个 x 互不相干（同名但辖域不同，可改名）
```

量词顺序（本章 `c04` 用两张 3×3 关系表证明）：

```text
∃y∀x L(x,y)  =>  ∀x∃y L(x,y)        成立
∀x∃y L(x,y)  =/=>  ∃y∀x L(x,y)      不成立（各人有各自的选择）
```

Skolem 化：消去 `∃` 时用 Skolem 常量/函数替代，例如 `∀x∃y L(x,y)` 变成 `∀x L(x, f(x))`。
这是把一阶公式喂给归结求解器的标准预处理。

## 3. 可运行代码

两张关系表：表 1「每人喜欢不同的人」使 `∀∃` 真而 `∃∀` 假；表 2「某人被所有人喜欢」使两者都真。

```c
#include <stdio.h>
/*
 * c04：量词的顺序不能交换
 * L(x,y) 表示「x 喜欢 y」。在同一张 3x3 关系表上比较：
 *   A: forall x exists y L(x,y)   —— 每个人都能找到自己喜欢的人（可以各不相同）
 *   B: exists y forall x L(x,y)   —— 存在一个人被所有人喜欢（同一个人）
 * B 成立一定 A 成立，反之不然。
 */
#define N 3
static const char *who[N] = {"ann", "bob", "cat"};
static int L1[N][N] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};  /* 各喜欢各的：A 真 B 假 */
static int L2[N][N] = {{1, 0, 0}, {1, 1, 0}, {1, 0, 0}};  /* ann 被所有人喜欢：A 真 B 真 */

static void show_table(const char *name, int L[N][N]) {
    printf("\n%s\n      ", name);
    for (int y = 0; y < N; y++) printf("%-6s", who[y]);
    printf("\n");
    for (int x = 0; x < N; x++) {
        printf("%-6s", who[x]);
        for (int y = 0; y < N; y++) printf("%-6d", L[x][y]);
        printf("\n");
    }
}

static int forall_exists(int L[N][N]) {
    for (int x = 0; x < N; x++) {
        int found = 0;
        for (int y = 0; y < N; y++) if (L[x][y]) found = 1;
        if (!found) return 0;
    }
    return 1;
}

static int exists_forall(int L[N][N], int *wit) {
    for (int y = 0; y < N; y++) {
        int all = 1;
        for (int x = 0; x < N; x++) if (!L[x][y]) all = 0;
        if (all) { if (wit) *wit = y; return 1; }
    }
    return 0;
}

int main(void) {
    int w1 = -1, w2 = -1;
    int a1 = forall_exists(L1), b1 = exists_forall(L1, &w1);
    int a2 = forall_exists(L2), b2 = exists_forall(L2, &w2);

    printf("L(x,y): 1 = x likes y;  A = forall x exists y L;  B = exists y forall x L\n");
    show_table("table 1: everyone likes a different person", L1);
    printf("A=%d  B=%d  -> B=>A holds (trivially), A=>B FAILS\n", a1, b1);
    show_table("table 2: ann is liked by everyone", L2);
    printf("A=%d  B=%d  (witness for B: %s)\n", a2, b2, w2 >= 0 ? who[w2] : "none");

    printf("\nA => B ? %s\n", (a1 && !b1) ? "NO -- see table 1: each x picks its own y, no single y works for all"
                                          : "no in general (table 1 is the counterexample)");
    printf("B => A ? %s\n", (!b2 || a2) ? "yes -- if one fixed y works for every x, it surely works for each x" : "NO");
    printf("\nso quantifier ORDER matters: exists-forall is strictly stronger than forall-exists.\n");
    printf("engineering echo: 'there is a config that works for all tenants' vs\n");
    printf("                  'every tenant has some config that works' -- the first is far stronger.\n");
    return 0;
}
```

真实运行输出：

```text
L(x,y): 1 = x likes y;  A = forall x exists y L;  B = exists y forall x L

table 1: everyone likes a different person
      ann   bob   cat   
ann   1     0     0     
bob   0     1     0     
cat   0     0     1     
A=1  B=0  -> B=>A holds (trivially), A=>B FAILS

table 2: ann is liked by everyone
      ann   bob   cat   
ann   1     0     0     
bob   1     1     0     
cat   1     0     0     
A=1  B=1  (witness for B: ann)

A => B ? NO -- see table 1: each x picks its own y, no single y works for all
B => A ? yes -- if one fixed y works for every x, it surely works for each x

so quantifier ORDER matters: exists-forall is strictly stronger than forall-exists.
engineering echo: 'there is a config that works for all tenants' vs
                  'every tenant has some config that works' -- the first is far stronger.
```

表 1 是"`∀∃` 不蕴含 `∃∀`"的反例。这条差别在多租户系统里非常真实：
"每个租户都有某份可用配置"和"存在一份配置对所有租户可用"，后者的 SLA 强得多。

## 三视角解析

### 🧑‍💻 程序员视角
SLA 文档里写过一句"所有租户都能找到可用区域"，被实现成
`∃region ∀tenant available(region, tenant)`——即"存在一个区域对所有租户都可用"。
这句话比原意强得多，上线后单区域故障就把全部租户打挂了。
正确形式是 `∀tenant ∃region available(region, tenant)`（每个租户各自有可用区域，可不同）。
两者的差别正是 `∀∃` 与 `∃∀` 的差别；写需求时把量词顺序写清楚，
比事后补容灾演练便宜得多。

### 🎓 博士生视角
一阶逻辑的表达力与代价是一体两面：它能刻画"所有/存在/关系"，
但 Church-Turing 结论表明其有效性问题是不可判定的（半可判定）。
可行的工程子集是 Horn 子句（至多一个正文字）：其可满足性等价于"最小模型存在"，
可用不动点迭代在多项式时间内求出——这正是 Datalog 与 Prolog 的理论边界。
Skolem 化把 `∃` 变成函数项，保持**可满足性**等价（但不保持逻辑等价），
这是把所有一阶公式送进归结引擎的标准手段，也是类型论里"存在消去"的直观来源。

### 📚 考研者视角
谓词符号化是送分题也是失分题，两条铁律：
① "所有 A 都是 B" → `∀x(A(x)→B(x))`（用 `→`）；
② "有的 A 是 B" → `∃x(A(x)∧B(x))`（用 `∧`）。
量词否定按"否定往里推，量词翻转"操作，复合式 `¬∀x(P→Q)` 要先用蕴涵等值式化开再否定，
结果是 `∃x(P∧¬Q)`。量词顺序题常见问法："说明 `∀x∃y` 与 `∃y∀x` 的关系并举例"——
答：后者蕴含前者，反之不然，举"每人有各自母亲" vs "存在一个人是所有人的母亲"。
