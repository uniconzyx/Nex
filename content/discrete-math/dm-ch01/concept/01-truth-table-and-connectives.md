# 真值表与联结词：蕴含为什么会"假前提为真"

## 1. 背景/动机

自然语言里的"如果……那么……"带着因果和假设的意味，但逻辑里的 `→` 只承诺一件事：
**不允许出现"前件真、后件假"**。这不是教材的怪癖，而是整个自动推理系统的地基——
如果允许从真前提推出假结论，任何定理都能被"证明"出来。

工程上踩过的坑几乎都源于此：把"只有付费用户才能进新流程"写成 `付费→进流程`，
免费用户就顺着 `p=0` 的"空真"被放进去了。真值表是唯一能一眼看出这类错的工具。

## 2. 定义/要点

五个联结词的真值表（`1` 真 / `0` 假）：

```text
 p  q | ~p | p^q | p v q | p->q | p<->q
------+----+-----+-------+------+-------
 0  0 |  1 |  0  |   0   |  1   |   1
 0  1 |  1 |  0  |   1   |  1   |   0
 1  0 |  0 |  0  |   1   |  0   |   0     <- p->q 唯一为假的一行
 1  1 |  0 |  1  |   1   |  1   |   1
```

三条必须刻进肌肉记忆的结论：

1. `p→q` 只在 `1→0` 时为假；`p=0` 时整句为真，称为**空真**（vacuous truth）。
2. `p→q ≡ ¬p∨q`。把蕴含化成"非或"，是等值演算的第一步。
3. `p↔q ≡ (p→q)∧(q→p)`。等价不是"差不多"，是双向蕴含。

自然语言到符号的固定译法：

```text
如果 P 那么 Q        ->  P -> Q
只有 P 才 Q          ->  Q -> P        （P 是必要条件，落在后件）
除非 P 否则 Q        ->  ~P -> Q  ≡ P v Q
P 当且仅当 Q         ->  P <-> Q
```

## 3. 可运行代码

下面的程序把两条"看起来都对"的推理各跑一遍 4 行真值表：肯定前件有效，肯定后件无效。

```c
#include <stdio.h>
/* 蕴含：只在 1 -> 0 时为假 */
static int imp(int a, int b) { return (!a) || b; }
/* 等价：同真同假 */
static int iff(int a, int b) { return a == b; }

/*
 * c01：两个「看起来都对」的推理，只有一个有效
 * 肯定前件 (modus ponens):  p->q, p  ==>  q     有效
 * 肯定后件 (affirming consequent): p->q, q ==> p 无效
 * 打印两张真值表，并指出无效式的反例行。
 */
int main(void) {
    printf("A) modus ponens: p->q, p |- q\n");
    printf("p q | p->q | (p->q)^p | q\n");
    printf("----+------+----------+--\n");
    int bad = 0;
    for (int p = 0; p < 2; p++)
        for (int q = 0; q < 2; q++) {
            int i = imp(p, q), prem = i && p;
            printf("%d %d |  %d   |    %d     | %d%s\n", p, q, i, prem, q,
                   (prem && !q) ? "  <-- would break validity" : "");
            if (prem && !q) bad = 1;
        }
    printf("=> %s\n\n", bad ? "INVALID" : "VALID: no row makes premises true and conclusion false");

    printf("B) affirming the consequent: p->q, q |- p\n");
    printf("p q | p->q | (p->q)^q | p\n");
    printf("----+------+----------+--\n");
    int ce = 0;
    for (int p = 0; p < 2; p++)
        for (int q = 0; q < 2; q++) {
            int i = imp(p, q), prem = i && q;
            printf("%d %d |  %d   |    %d     | %d%s\n", p, q, i, prem, p,
                   (prem && !p) ? "  <-- counterexample: q=1,p=0" : "");
            if (prem && !p) ce++;
        }
    printf("=> %s (%d counterexample row)\n", ce ? "INVALID" : "VALID", ce);
    printf("\nlesson: validity = 'premises true, conclusion must be true',\n");
    printf("        not 'conclusion sounds plausible'.\n");
    return 0;
}
```

真实运行输出：

```text
A) modus ponens: p->q, p |- q
p q | p->q | (p->q)^p | q
----+------+----------+--
0 0 |  1   |    0     | 0
0 1 |  1   |    0     | 1
1 0 |  0   |    0     | 0
1 1 |  1   |    1     | 1
=> VALID: no row makes premises true and conclusion false

B) affirming the consequent: p->q, q |- p
p q | p->q | (p->q)^q | p
----+------+----------+--
0 0 |  1   |    0     | 0
0 1 |  1   |    1     | 0  <-- counterexample: q=1,p=0
1 0 |  0   |    0     | 1
1 1 |  1   |    1     | 1
=> INVALID (1 counterexample row)

lesson: validity = 'premises true, conclusion must be true',
        not 'conclusion sounds plausible'.
```

`B` 表第 2 行（`p=0,q=1`）就是反例：前提 `(p→q)∧q` 为真，结论 `p` 为假。
一行反例就足以否掉一个推理形式——这比背十条规定有用。

## 三视角解析

### 🧑‍💻 程序员视角
业务里有个真实事故：灰度平台把「只有付费用户才进新流程」实现成 `paid → gray`，
结果免费用户（`paid=0`）因为 `0→?` 恒真，全被放进了灰度。上线 20 分钟才发现。
用真值表一扫就清楚：`paid=0` 的两行在两种写法下真值不同，而代码里只测了 `paid=1` 的路径。
正确写法是 `gray → paid`（进灰度必须付费），或者直接用白名单而不是蕴含。
这也解释了为什么很多团队宁可写 `if (paid) gray()` 而不用规则表达式——
**蕴含的方向一旦写反，静态检查很难发现**，只有把真值表摊开或写单测覆盖 `paid=0` 才看得见。

### 🎓 博士生视角
经典命题逻辑的语义是"赋值函数 `v: Var → {0,1}` 的全体"。
`→` 的定义不是"因果"，而是为了让**演绎定理**成立：`Γ, p ⊢ q` 当且仅当 `Γ ⊢ p→q`。
如果 `0→0` 定义为假，演绎定理立刻破裂，整个希尔伯特系统不再健全。
从代数角度看，`({0,1}, ∧, ∨, ¬)` 是布尔代数，`→` 只是 `¬p∨q` 的语法糖；
而 `p→q` 恰好是偏序 `p ≤ q` 的另一种写法——这也解释了为什么"真值表法"本质是在枚举格上的点。

### 📚 考研者视角
408 不考离散，但**自命题院校的离散数学**几乎每年一道真值表/范式题。
标准答题模板：① 列 `2^n` 行真值表；② 标出成真行；③ 写 `Σm{...}`（成真）与 `ΠM{...}`（成假）；
④ 若要写公式，小项"取 1 写本身、取 0 写否定"。
高频陷阱：`p→q` 的假值行是 `1→0`（第 3 行），不是第 2 行；"只有 P 才 Q"写作 `Q→P`。
