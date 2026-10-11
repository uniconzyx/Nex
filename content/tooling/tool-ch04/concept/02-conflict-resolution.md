# 冲突的本质：三方合并、冲突标记与解决流程
> 本节目标：讲清「冲突什么时候产生、Git 到底怎么合、程序员怎么收尾」。每个主题按三视角解析。

---

## 一、冲突的充要条件与三方合并（three-way merge）

Git 的合并不是「比较两份文件的异同」，而是**三方合并**：给定

- `base` = `merge-base(ours, theirs)`（两个分支的最近公共祖先，**合并基线**），
- `ours` = 当前 HEAD 的版本，
- `theirs` = 被合并进来的版本，

分别计算 `base → ours` 与 `base → theirs` 两串行级改动（hunk），然后逐 hunk 合成。判定规则：

| ours / theirs 在同一区域的情况 | 结果 |
|---|---|
| 只有一侧有改动 | 采用该侧（包括「一侧新增行」「一侧删除行」） |
| 两侧都有改动且结果**完全相同** | 采用一次（不冲突） |
| 两侧都有改动且结果**不同**（含一侧删除、另一侧修改） | **冲突**，写入冲突标记 |

所以冲突的**充要条件**是：相对共同祖先，双方在**同一区域**都做了改动且结果不一致。
「两个人都改了同一个文件」既不充分也不必要。`examples/ex03` 给出自动合并的正例，
`examples/ex04` 给出四组对照（同行异值冲突 / 同行同值自动合并 / 删改冲突 / 不同行自动合并）。

### 🧑‍💻 程序员视角
- **降低冲突成本的办法是缩短分支寿命**：每天 rebase 一次的分支很少出大冲突；攒两周再合，冲突定义就变成「几百行同区域改写」。
- **冲突不要靠猜**：开启 `git config merge.conflictStyle diff3`（或 `zdiff3`），让 Git 把**共同祖先那一行**也写进冲突区，
  你能直接看出「原来是谁在改什么」，而不是在两侧半成品之间做选择。
- **`git checkout --ours/--theirs` 是核按钮**：整段丢弃另一侧，只适用于「我明确知道这一份是对的」（例如合入无关分支时保留自己的配置）。
  真正稳妥的解决通常是打开编辑器手工编辑后再 `git add`。
- **合完必须验证**：冲突解决后，用 `git diff` 复核内容、`git diff --stat` 看改动范围，跑单测再 commit。

### 🎓 博士生视角
- 为什么必须三方：只有 base 才能把「A 新增了这行」和「B 删除了 A 的某行」区分开。这是 Day/1988 三代 diff3 算法的出发点。
- 行配准用的是 **最长公共子序列（LCS）**：Git 的 `xdiff` 实现 Myers O(ND) 与 histogram 两种，
  前者最小编辑脚本更短，后者在「改动含大量重复行（如 `}`）」时更符合人类直觉。
- 多基点的情形：存在多个极大共同祖先（criss-cross 历史，`git merge-base --all` 会列出多个）时，
  **recursive** 策略会先把这些基点合并成一个虚拟 base，再做一次普通三方合并；
  **octopus** 策略则可一次合并多个 head，但一旦有冲突就直接拒绝。
- 复杂性：三方合并是**启发式的**文本合并，不理解语法；因此存在「自动合并成功但语义已坏」的情况
  （典型：两侧各自新增同名函数/变量），这解释了为什么「合并后一定要跑测试」不是官僚而是必要。

### 📚 考研者视角
- 本节机制本身不属 408 纲内；可迁移的考点是 **DAG 上的最近公共祖先（LCA）** 与 **LCS/最长公共子序列**：
  前者是数据结构里二叉树 LCA 的图论推广，后者是动态规划经典题。
- 笔试/面试的标准口径：「Git 什么时候会产生冲突」
  —— 答：**同一文件的同一区域，相对共同祖先两侧改动不一致**；并补齐反例「改成完全一样会自动合并」。
- 易错点辨析：把「冲突」说成「改了同一个文件」；把 `git merge` 说成「拿新文件覆盖老文件」；
  认为 `rebase` 不会产生冲突——rebase 只是把同一套三方合并**逐个提交地做一遍**，冲突次数可能更多。

---

## 二、冲突标记、解决流程与 `rerere`

冲突时 Git 在工作区写入标记：

```
<<<<<<< HEAD            <- ours（当前分支/HEAD 一侧）
这里是我们的版本
=======                 <- 分隔两个版本
这里是对方的版本
>>>>>>> feature/login   <- theirs（被合并的一侧）
```

完整的解决流程：

1. `git status` 看哪些文件 Unmerged；
2. 编辑文件（或 `git checkout --ours/--theirs`），**手工删掉标记**并确定最终语义；
3. `git add <file>` 告诉 Git「这个冲突我解决了」；
4. `git merge --continue`（或 `git rebase --continue` / `git cherry-pick --continue`）；
5. 想反悔：`git merge --abort` / `git rebase --abort`（回到操作前的 refs）；
6. 收尾：`git diff HEAD~1` 复核，跑测试，必要时 `--verify-signatures`。

`rerere`（reuse recorded resolution）会把「这次怎么解决的」记进 `.git/rr-cache/`，
下次遇到同样形状的冲突自动套用——**长期 rebase 的开发分支**特别有用，配 `git config rerere.enabled true` 开启。
`examples/ex05` 实现了标记解析器 + ours/theirs/union 选择语义 + rerere 回放。

### 🧑‍💻 程序员视角
- **union 不是「两边都要」的最简答案**：`git checkout --conflict=union <file>` 会把两侧行都留下，
  很可能产出重复定义 / 重复 switch case，必须人工再看一遍。
- **rebase 的冲突会比 merge 多**：因为 merge 一次解决，rebase 要在**每个被重放的提交**上一次次停下；
  善用 `rerere` 与 `-i` 中途 squash 掉易冲突的中间提交。
- **cherry-pick 的冲突**：`cherry-pick` 用「被摘提交的父」当 base、当前 HEAD 当 ours，
  所以把 commit 搬到差异很大的老分支时，冲突是正常的；解决完记得 `--continue`。
- **Commit 前自检清单**：`grep -rn '^<<<<<<<\|^=======\|^\(<<<<<<<\|>>>>>>>\)' .` — 查出残留标记；
  把它做成 pre-commit hook / CI 检查，能杜绝「标记上线」的经典事故。

### 🎓 博士生视角
- 冲突文件的 index 里有 stage 1/2/3 三个条目（其实是 `git ls-files -u` 可见的 1=base、2=ours、3=theirs），
  `git add` 的语义是把已解决的单一版本写回 stage 0，从而使该路径退出 Unmerged 状态；这是「标记解决完成」的本质。
- `rerere` 的缓存键是**冲突内容的稳定摘要**（不含文件路径与行号），所以同一形状冲突在任何分支重复出现都能命中；
  但 Git 只自动应用，**不会替你 commit**，仍要人工核查。
- `merge.conflictStyle=diff3` 多出的 `|||||||` 段就是 stage 1（base）——把「base / ours / theirs 三份」全部暴露给人类，
  是三十年来 diff3 系合并工具公认更可用的呈现方式。

### 📚 考研者视角
- 本节不是 408 考点；迁移考法是**状态机/阶段迁移**：Unmerged 路径 ⇒ stage{1,2,3} ⇒ `add` 后归一为 stage 0
  （可与操作系统里「文件打开表 / PCB 状态迁移」类比记忆）。
- 易错点辨析：
  - 「`=======` 表示文件结束」——不，它是 ours 与 theirs 的分隔线；
  - 「冲突时 `--theirs` 一定是对方分支的版本」——在 rebase 语境里，**ours/theirs 的语义会颠倒**
    （rebase 时 ours 是正在重放的上游分支，theirs 是你自己的提交），这是高频陷阱；
  - 「标记删掉就算解决」——还必须 `git add`，否则 index 里仍是 Unmerged。
- 标准定义速记：**冲突解决 = edit → add → continue（或 abort 反悔）**。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 决策与收尾质量 | 缩短分支寿命、diff3 风格、ours/theirs 的核按钮风险、标记残留检查清单 |
| 🎓 博士生 | 算法与第一性原理 | LCS 行配准、必须三方的原因、多基点 recursive/octopus 策略、index stage 1/2/3 |
| 📚 考研者 | 易错口径与迁移考点 | 冲突充要条件、rebase 下 ours/theirs 颠倒、add 才算解决、LCA/LCS 迁移 |
