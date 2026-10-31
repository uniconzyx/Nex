# 推理与归结：机器怎么"证明"一件事

## 1. 背景/动机

"这个推理有效吗"在教材里靠真值表，但真值表是 `2^n`，`n=40` 就跑不动了。
真正被机器使用的方法是**归结**：把公式拆成小句（子句），两两消去互补文字，
如果最终推出空子句 `□`，就证明原式不可满足。SAT 求解器、SMT、Prolog、Datalog
全部建立在这个思路上。

## 2. 定义/要点

**推理有效的定义**：`P1, P2, …, Pk ⊨ Q` 当且仅当 `(P1∧…∧Pk) → Q` 是永真式。
等价说法：`P1∧…∧Pk∧¬Q` **不可满足**。后者才是可机械执行的形式——这就是反驳法。

归结规则（唯一一条）：

```text
        C1 v l        C2 v ~l
        ----------------------   (归结)
              C1 v C2
```

工程化步骤：

```text
1) 把 前提 ^ ~结论 化成 CNF（子句集，每个子句是一堆文字的析取）
2) 反复对含互补文字的子句对做归结，把归结式加入集合
3) 若出现空子句 []  ->  不可满足  ->  原推理有效
   若再也加不出新子句 ->  可满足    ->  推理无效（可读出反例模型）
```

三个实现细节（本章 `ex04`/`c03` 都踩过）：

- 归结式里若出现互补文字（如 `[p, ~p]`），它是永真的，**必须丢弃**。
- 消去必须**双向跳过**：`[~p,q]` 与 `[~q,r]` 只能得到 `[~p,r]`。
- 子句数会爆炸，所以工业实现（CDCL）会做单元传播 + 学习子句 + 非时序回溯。

Horn 子句是另一个极端好用的子集：每条子句**至多一个正文字**，形如 `body ⇒ head`。
它的可满足性可以线性判定，且前向链天然对应"事实不断增长直到不动点"。

## 3. 可运行代码

程序用反驳法证明假言三段论 `(p→q)∧(q→r) → (p→r)`：先把前提与结论的否定化成 4 条子句，再逐步归结。

```c
#include <stdio.h>
/*
 * c03：用归结法证明假言三段论
 * 待证：(p->q) ^ (q->r) -> (p->r)
 * 反驳法：把「前提 + 结论的否定」化成子句：
 *   ~p v q,  ~q v r,  p,  ~r
 * 然后两两归结，直到推出空子句。
 */
#define NV 3
static int comp(int l) { return l ^ 1; }
static void show(int c) {
    if (!c) { printf("[]"); return; }
    printf("[");
    int first = 1;
    for (int l = 0; l < 2 * NV; l++)
        if ((c >> l) & 1) {
            if (!first) printf(", ");
            printf("%s%d", (l & 1) ? "~" : "", l / 2 + 1);
            first = 0;
        }
    printf("]");
}
static int resolve(int a, int b, int *out) {
    int res = 0, elim = 0;
    for (int l = 0; l < 2 * NV; l++) {
        int ina = (a >> l) & 1, inb = (b >> l) & 1;
        if (ina && ((b >> comp(l)) & 1)) { elim = 1; continue; }
        if (inb && ((a >> comp(l)) & 1)) { elim = 1; continue; }
        if (ina || inb) {
            if ((res >> comp(l)) & 1) return -1;
            res |= (1 << l);
        }
    }
    if (!elim) return -1;
    *out = res;
    return 0;
}
int main(void) {
    /* 文字编号：0=p 1=~p 2=q 3=~q 4=r 5=~r */
    int cls[12] = {(1 << 1) | (1 << 2), (1 << 3) | (1 << 4), (1 << 0), (1 << 5)};
    int n = 4, step = 0, proved = 0;
    printf("clauses from  premises ^ ~conclusion:\n");
    for (int i = 0; i < n; i++) { printf("  "); show(cls[i]); printf("\n"); }
    while (!proved && n < 12) {
        int added = 0;
        for (int i = 0; i < n && !proved; i++)
            for (int j = i + 1; j < n && !proved; j++) {
                int r;
                if (resolve(cls[i], cls[j], &r) != 0) continue;
                int dup = 0;
                for (int k = 0; k < n; k++) if (cls[k] == r) dup = 1;
                if (dup) continue;
                step++;
                printf("step %d: ", step); show(cls[i]); printf(" + "); show(cls[j]);
                printf(" => "); show(r); printf("\n");
                cls[n++] = r;
                added = 1;
                if (r == 0) proved = 1;
            }
        if (!added) break;
    }
    printf("\n%s\n", proved ? "empty clause derived -> the negation is unsatisfiable -> QED"
                            : "not proved in the given budget");
    printf("cost: %d resolution steps for a 3-variable formula.\n", step);
    return 0;
}
```

真实运行输出：

```text
clauses from  premises ^ ~conclusion:
  [~1, 2]
  [~2, 3]
  [1]
  [~3]
step 1: [~1, 2] + [~2, 3] => [~1, 3]
step 2: [~1, 2] + [1] => [2]
step 3: [~2, 3] + [~3] => [~2]
step 4: [~2, 3] + [2] => [3]
step 5: [~3] + [~1, 3] => [~1]
step 6: [~3] + [3] => []

empty clause derived -> the negation is unsatisfiable -> QED
cost: 6 resolution steps for a 3-variable formula.
```

6 步推出空子句。注意 `step 1` 得到的是 `[~1, 3]` 而不是 `[~1, ~2, 3]`——
后者正是"漏掉 b 侧跳过"写出来的错误子句，用它永远推不出 `□`。

## 三视角解析

### 🧑‍💻 程序员视角
权限系统用 Datalog 描述：`can_write(u,db) :- role(u,admin)`、
`role(u,admin) :- in_group(u, dba)`。每周新增规则后跑一次前向链，
把"谁能写生产库"全量物化出来做审计。
某次新增 `in_group(u,temp) :- intern(u)` 后，审计发现 3 个实习生路径可达生产库写权限——
这在规则文本里要跨 4 条规则才看得出来，而前向链一轮就把它摊平了。
这就是为什么权限审计工具（如 Soufflé、Open Policy Agent 的 partial eval）
宁可用"物化全部推导结果"的笨办法：**只要不动点是有限的，穷举推导就是最可靠的证明**。

### 🎓 博士生视角
归结的完备性定理（Robinson, 1965）：一阶子句集不可满足 ⟺ 存在从它出发的归结反驳。
这条定理把"语义上的不可满足"与"语法上的有限推导"接了起来，
是自动定理证明的第一块基石。它的证明依赖 Herbrand 定理（1950）：
不可满足的一阶子句集必存在有限的 Herbrand 基上的命题不可满足实例。
工程上纯归结的子句爆炸无法接受，于是有了 DPLL（1962，回溯 + 单元传播）
和 CDCL（1996 起，冲突驱动子句学习 + 非时序回溯），后者是现代 SAT 求解器的主流。

### 📚 考研者视角
自命题离散的证明题常给 4–5 条子句让你"用归结法证明"。
标准步骤：① 写出子句集（务必含结论的否定）；② 每次只对一对含互补文字的子句归结；
③ 在边上标出消去的是哪个文字；④ 得到 `□` 后写"与假设矛盾，故原命题成立"。
扣分点：忘了对结论取反；归结式保留了互补文字对；把 `[p,¬p]` 这种永真子句当结果写下去。
