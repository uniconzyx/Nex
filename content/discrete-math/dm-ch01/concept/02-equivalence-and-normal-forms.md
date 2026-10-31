# 等值演算与范式：为什么"写法不同"能被机器判成同一个公式

## 1. 背景/动机

规则系统里最常见的故障不是规则写错，而是**同一条规则被写了两遍、写法还不一样**。
`p→q` 和 `¬p∨q` 在文本上毫无相似度，但它们是同一个函数。要在工程上自动去重，
就必须有一个"标准形"：把公式化成唯一形态，再比较字符串。

这个标准形就是**主析取范式**（Σm）与**主合取范式**（ΠM）。它们是本章唯一需要"手算到不出错"的技能，
也是考研离散的第一道大题。

## 2. 定义/要点

常用等值式（全部可用真值表验证，本章 `ex03` 就是干这件事）：

```text
蕴涵等值式   p->q      ≡ ~p v q
假言易位     p->q      ≡ ~q -> ~p          （逆否等价）
德摩根       ~(p^q)    ≡ ~p v ~q
             ~(p v q)  ≡ ~p ^ ~q
分配律       p^(q v r) ≡ (p^q) v (p^r)
             p v (q^r) ≡ (p v q)^(p v r)
吸收律       p v (p^q) ≡ p
双重否定     ~~p       ≡ p
```

极小项与极大项的写法（`n=3`，变量顺序固定 `p,q,r`）：

```text
赋值 pqr   极小项 m_i（该项仅在此赋值下为真）   极大项 M_i（该项仅在此赋值下为假）
000        ~p ^ ~q ^ ~r   = m0                  p v q v r      = M0
011        ~p ^  q ^  r   = m3                  p v ~q v ~r    = M3
110         p ^  q ^ ~r   = m6                  ~p v ~q v r    = M6
```

- **主析取范式**：把所有**成真**赋值对应的小项取析取，记作 `Σm{...}`。
- **主合取范式**：把所有**成假**赋值对应的极大项取合取，记作 `ΠM{...}`。
- 自检：`Σm` 的下标集合与 `ΠM` 的下标集合**互补**，并起来恰好 `2^n` 个。

## 3. 可运行代码

程序对 `f1 = p→q` 与 `f2 = ¬p∨q` 分别求 Σm：两组下标完全相同，于是判等。

```c
#include <stdio.h>
/*
 * c02：范式为什么唯一 —— 两个不同写法的公式，同一个 Σm
 * f1 = p -> q
 * f2 = ~p v q
 * 语法完全不同，但真值表相同，于是主析取范式完全相同：Σm{0,1,3}。
 * 这正是「机器判等」的做法：化成范式，比较集合。
 */
static int imp(int a, int b) { return (!a) || b; }
int main(void) {
    printf("p q | f1=p->q | f2=~p v q | same?\n");
    printf("----+---------+-----------+------\n");
    int m1[4], m2[4], n1 = 0, n2 = 0;
    for (int v = 0; v < 4; v++) {
        int p = (v >> 1) & 1, q = v & 1;
        int a = imp(p, q), b = (!p) || q;
        printf("%d %d |    %d    |     %d     |  %s\n", p, q, a, b, a == b ? "yes" : "no");
        if (a) m1[n1++] = v;
        if (b) m2[n2++] = v;
    }
    printf("\nSDNF(f1) = Sm{");
    for (int i = 0; i < n1; i++) printf("%s%d", i ? "," : "", m1[i]);
    printf("}\nSDNF(f2) = Sm{");
    for (int i = 0; i < n2; i++) printf("%s%d", i ? "," : "", m2[i]);
    printf("}\n");
    int same = (n1 == n2);
    for (int i = 0; i < n1 && same; i++) if (m1[i] != m2[i]) same = 0;
    printf("\nthe two sets are %s -> the formulas are logically equivalent.\n", same ? "identical" : "different");
    printf("so: equivalent formulas <=> identical principal normal form.\n");
    printf("practical use: cache key / rule dedup can hash the SDNF set.\n");
    return 0;
}
```

真实运行输出：

```text
p q | f1=p->q | f2=~p v q | same?
----+---------+-----------+------
0 0 |    1    |     1     |  yes
0 1 |    1    |     1     |  yes
1 0 |    0    |     0     |  yes
1 1 |    1    |     1     |  yes

SDNF(f1) = Sm{0,1,3}
SDNF(f2) = Sm{0,1,3}

the two sets are identical -> the formulas are logically equivalent.
so: equivalent formulas <=> identical principal normal form.
practical use: cache key / rule dedup can hash the SDNF set.
```

`SDNF(f1)` 与 `SDNF(f2)` 都是 `Sm{0,1,3}` —— 这就是"机器判等"的全部秘密：
**化到范式，比集合**。工程上可以直接把 Σm 集合哈希成规则指纹做去重。

## 三视角解析

### 🧑‍💻 程序员视角
风控平台曾把 37 条规则写进同一张表，其中 5 组是同一条规则的变体
（`amount>1000 → manual` 与 `¬(amount≤1000) ∨ manual`）。
线上每次请求要顺序求值 37 条，P99 是 11ms。做法是：把每条规则化成 `Σm` 集合当指纹，
去重后剩 29 条，再把剩余的用奎因-麦克拉斯基化简到 18 条，P99 降到 5.2ms。
关键是**判等必须用范式**：字符串比较会把 `p→q` 和 `¬p∨q` 当成两条规则，
而人工 review 也看不出来——这正是"范式唯一性"的工程价值。

### 🎓 博士生视角
范式唯一性来自"每个布尔函数 `{0,1}^n → {0,1}` 与它的真值向量一一对应"。
主析取范式就是真值向量的"标准基"展开，所以同一函数必得同一下标集合，反之亦然。
极小项的个数等于函数的 **0-1 谱**中 1 的个数，因此 `|Σm| + |ΠM| = 2^n` 是恒等式而非巧合。
更深的联系：布尔函数的代数正规形（ANF，Zhegalkin 多项式）是同一个函数在 `GF(2)` 上的另一种标准形，
两条路线分别对应"析取范式"与"异或/与"两种电路实现，芯片综合时会在两者间选代价更低的。

### 📚 考研者视角
答题时最容易丢分的是**下标算错**。固定规则：变量顺序 `p,q,r`，赋值读作二进制 `pqr`。
`p=0,q=1,r=1` → `011` → 3，写 `m3 = ¬p∧q∧r`。
主合取范式用**成假**赋值，极大项写法与极小项相反（取 0 写本身、取 1 写否定），最后整体取合取。
自检口诀：`Σm` 与 `ΠM` 的下标集合并起来必须正好是 `0..2^n-1`，缺一个就是算错了。
