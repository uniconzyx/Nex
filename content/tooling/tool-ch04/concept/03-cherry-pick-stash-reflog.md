# 提交搬运与误操作救援：cherry-pick / stash / reflog
> 本节目标：把「把一个改动搬到另一条线」和「误操作之后怎么救」讲透。每个主题按三视角解析。

---

## 一、cherry-pick / revert / rebase：三种「复制/抵消」语义

三者都会对**已有的改动**做文章，但语义完全不同：

| 命令 | 输入 | 作用 | 是否改写历史 | 典型用途 |
|---|---|---|---|---|
| `git cherry-pick <sha>` | 单个提交 | 把该提交相对其父的**差异**应用到当前 HEAD，生成**新 SHA** 的提交 | 否（只新增） | 把一个 hotfix 复制到多条发布分支 |
| `git revert <sha>` | 单个/区间提交 | 生成一个**反向提交**来抵消它 | 否（只新增） | 回滚已发布的提交（对协作者最友好） |
| `git rebase <upstream>` | 一段提交序列 | 把这段序列在新基点上**逐个重放**，原提交作废 | **是** | 整理本地未推送的提交、保持历史线性 |

`cherry-pick` 内部做的事就是一次三方合并：**base = 被摘提交的父，ours = 当前 HEAD，theirs = 被摘提交**。
所以它可能冲突，解决完要 `git cherry-pick --continue`。
`examples/ex07` 模拟了这个过程：遗留侧看到的是等价的改动，但因为 parent 与 tree 不同，**新提交的 SHA 必然变化**。

### 🧑‍💻 程序员视角
- **决策树（回滚已上线的提交）**：共享分支 → `revert`；自己的尚未推送的开发分支 → `reset --hard` / `rebase -i` 都可以；
  只想把某个修复搬到别的分支 → `cherry-pick -x`（`-x` 会在提交信息里注明来源 SHA，便于溯源，强烈推荐）。
- **cherry-pick 的坑**：它只搬 **这一个提交的内容**，不会带上它的祖先。如果 hotfix 依赖同分支更早的重构提交，
  直接 cherry-pick 会得到「编译不过」；正确顺序是先摘先序依赖，或干脆把那一段整体 rebase 过去。
- **回滚 merge commit 要小心**：需要 `-m 1` 指定以第几条主线为准；
  而 revert 之后再次 merge 同一分支，Git 会认为「那些提交已经在历史里」而跳过它们——
  需要 `revert the revert` 才能重新引入这部分改动（经典事故场景）。
- **事故案例**：用 `revert` 回滚 A 之后再 cherry-pick A，Git 可能报 nothing to commit（因为改动已在历史中），
  正确做法是 revert 掉那次 revert。

### 🎓 博士生视角
- 形式化地看：`cherry-pick(C)` = `three_way_merge(base=parent(C), ours=HEAD, theirs=C)` 的结果作为一个新提交，
  其 parent 为 HEAD、message 复用 `C.message`（`-x` 会追加 `(cherry picked from commit <sha>)`）。
- 为什么 SHA 一定变：commit 对象的键由 `sha1(tree, parents, author, committer, message)` 决定，
  parents 变了 ⇒ tree 或 parents 至少一项变化 ⇒ 键必然不同。这是「commit id 是内容的完整指纹」的直接推论。
- rebase 就是循环 cherry-pick（实现上略有优化，如 `merge --onto`），所以 rebase 的冲突次数 = 每个被重放提交各自的三方合并结果之和；
  这也是为什么 `--onto` 能精确控制「从哪儿搬、搬到哪儿」。
- 幂等性：`cherry-pick` 一个已经在祖先链里的提交通常是空操作（或报 `The previous cherry-pick is now empty`），
  因为三方合并结果等同于 ours——这正是「Git 用差分而非累积」的体现。

### 📚 考研者视角
- 本节不在 408 纲内；笔试/面试标准问法是 `revert` 与 `reset` 的区别：**revert 追加历史（安全、可协作），reset 改写历史（可能让别人 orphan）**。
- 易错点辨析：
  - 「cherry-pick 是移动提交」——错，是**复制**，原提交仍在原分支；
  - 「cherry-pick 后 id 应该不变」——错，parent 变了 id 必变；
  - 「revert 一个 merge 不需要参数」——错，必须 `-m <parent-number>` 指定主线。
- 可能与错题结合的口径：「把某次修复从 feature 搬到 master 且要保留溯源」→ 答 `git cherry-pick -x <sha>`。

---

## 二、stash 栈与 reflog 救援网

`git stash` 把「工作区 + 暂存区」的改动打成一个**快照**压栈，然后把已跟踪文件还原到 HEAD。
它是一个 **LIFO 栈**：`stash@{0}` 永远是最近压入的一条。

```bash
git stash push -m "wip: 表单校验"   # 压栈（-u 才会包含未跟踪文件）
git stash list                       # stash@{0} ... 从新到旧
git stash pop                        # 取出栈顶并删除该记录
git stash apply stash@{1}            # 取出指定条目但**保留**记录
git stash drop stash@{1}             # 删除指定条目
```

`reflog` 则是另一个维度的安全网：`.git/logs/HEAD` 记录了每次 HEAD 的移动（commit / checkout / reset / merge / rebase / pull），
每条包含「移动前后的 SHA」。只要你误操作的那些提交还被 reflog 的某条记录指向，它们就**还在对象库**，可以从打捞。
`examples/ex08` 演示了完整的 push/pop/apply/drop 顺序与「脏工作区拒绝 pop」的反例；
`examples/ex09` 演示 `reset --hard` 之后用 reflog 找回 c2/c3、并抢救被 `-D` 删除的分支。

### 🧑‍💻 程序员视角
- **stash 只适合临时跳转**（几分钟到几小时的半成品）。跨天/跨机器的半成品应该 commit 到自己的临时分支
  —— stash 没有 ref namespace，容易混成一锅粥，且**不在任何分支上、没法被别人看到**。
- 记住 `-u`：未跟踪文件默认不进 stash，切分支后又会被带着走，常被误 commit；用 `git stash -u` 或 `.gitignore` 处理。
- **救援顺序**：`git reflog` → 找到误操作前的位置（形如 `HEAD@{3}` 或某个 SHA）→
  `git reset --hard <sha>` 或 `git checkout -b rescue <sha>`；若涉及被 `.git gc` 清理，**时间窗默认 90 天**（`gc.reflogExpire`）。
- **`--amend` 丢的提交**、`rebase` 前的旧 tip、`reset --hard` 前的 tip，全都能用同一套路找回；前提是**没换机器、没手动删 .git**。

### 🎓 博士生视角
- stash 的实现其实是一个**特殊形状的 commit 对象**：它把 index 状态和工作区状态分别记为两棵树（有时还有第三棵树存未跟踪文件），
  并有至少两个 parent（HEAD 与 index commit），然后用 `refs/stash` 这个引用串成链表——所以从对象模型看它就是提交图的一部分。
- reflog 是 **append-only log（WAL）** 思想的典型实例：引用本身可变，但「引用的每一次变化」被持久化为只增不改的日志，
  于是所有历史状态都可通过重放日志抵达。这与数据库的 redo log、文件系统的 journal 是同一类设计。
- reflog **不入 push 协议、不进 bundle**；它的存在范围严格等于「这一个本地仓库」。克隆一份新仓库时，别人的 reflog 不会跟着来——
  因此它是「个人后悔药」而不是「团队容灾手段」（团队容灾靠远端备份与 PR 历史）。
- 可达性与 GC：Git 的 GC 只回收「**从所有 ref + reflog + index 出发都不可达**」的对象；reflog 因此在 GC 语义上也是一种根引用。

### 📚 考研者视角
- 本节不属 408 纲内；迁移考点是 **栈（LIFO）** 与 **WAL/日志结构的追加写**。
  前者对应数据结构章节「出栈序列合法性判定」的经典题，后者可与操作系统/数据库的日志恢复做类比记忆。
- 易错点辨析：
  - 「stash 是队列」——错，是栈，多次 stash 后 `pop` 取的是**最近一次**；
  - 「reflog 能找回远端丢失的提交」——不能，它只在本地；
  - 「`git stash` 后 checkout 到别的分支再回来，`git stash apply` 一定成功」——不成立，
    目标文件若已有改动会被拒绝（这就是 examples/ex08 的反例）。
- 标准口径速记：**复制用 cherry-pick，回滚共享用 revert，救急本地用 reflog，暂存半成品用 stash。**

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 决策树与救援顺序 | revert vs reset vs cherry-pick 选型、`cherry-pick -x` 溯源、stash 只做临时跳转、reflog 打捞四步法 |
| 🎓 博士生 | 对象模型与日志原理 | cherry-pick = 三方合并特例、SHA 必变的原因、stash 是特殊形状 commit、reflog 是 WAL |
| 📚 考研者 | 易混辨析与迁移考点 | revert/reset 区别、LIFO 栈、WAL 类比、reflog 只本地不共享 |
