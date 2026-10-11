# reset/checkout/reflog 与标签：安全回退与救援
> 本节目标：把「怎么安全回退、误操作怎么救」讲透。每个主题按三视角解析。

---

## 第1节 一、reset 三模式 + checkout/restore/revert 的区别

`git reset` 移动 HEAD（并可顺带重置 index、工作树）；`git checkout`/`git switch` 切换分支或恢复文件；`git restore` 是更聚焦的文件级恢复（可指定 source 与 destination）；`git revert` **生成一个新的反向提交**来抵消某次提交，不改写历史。
### 🧑‍💻 程序员视角
- reset 三模式对照：`--soft` 只动 HEAD（index/工作区不动）；`--mixed`（默认）动 HEAD + 重置 index（改动退回工作区）；`--hard` 三者全动（工作区改动**直接丢弃，危险**）。
- `git checkout -- <file>` / `git restore --source=HEAD --staged --worktree <file>` 用 HEAD 版本覆盖文件，是「放弃工作区改动」；它们**只动文件，不动 HEAD**。
- 回滚已 push 的提交：**用 `revert` 而非 `reset --hard` + 强推**——reset 改写共享历史会连累队友；revert 是安全的可协作回滚。

### 🎓 博士生视角
- reset 三类影响的精确定义：`--soft` 仅写 HEAD 引用；`--mixed` 再重置 index（使其等于目标 commit 的 tree）；`--hard` 再 `checkout` 目标 tree 到工作区，故会抹掉未提交改动。
- revert 不删对象：它构造一个「把目标提交的所有改动取反」的新 commit 接到 HEAD，旧提交仍在历史里——这是它与 reset（可能让旧提交变为不可达）的根本区别。

### 📚 考研者视角
- 常考「`reset --soft/--mixed/--hard` 的差异」——**哪个动工作区、哪个动暂存区、哪个动 HEAD**：soft(只HEAD)/mixed(HEAD+暂存区)/hard(全部)。
- 易错：「`checkout -- file` 会动 HEAD 吗」——不会，它只恢复文件；「`reset --hard` 后用 reflog 还能找回丢失的 commit」。

---

## 第2节 二、detached HEAD、reflog 救援与 tag/stash/cherry-pick

`git checkout <commit-sha>` 会进入 **detached HEAD**：HEAD 直接存一个 commit SHA 而非分支引用。此时新提交「不属于任何分支」，切走后若未被引用似乎「丢失」——但 **reflog**（`.git/logs/HEAD` 的流水）记录每次 HEAD 移动，是本地救援网。此外 `stash` 暂存半成品、`cherry-pick` 摘取单个提交、`tag` 标记里程碑。
### 🧑‍💻 程序员视角
- detached 下提交后想保留：立刻 `git branch rescue <sha>` 或 `git checkout -b rescue` 把它收编成分支；否则切回分支后该提交无引用，最终被 GC。
- stash：`git stash` 把工作区+暂存区压栈并还原干净，`git stash pop` 取回；适合「临时切分支又不想提交半成品」。
- cherry-pick：`git cherry-pick <sha>` 把某个提交的差异应用到当前分支，常用于「把修复从一条线搬到另一条线」。
- tag 两种：轻量标签（就是个指向 commit 的引用，无额外对象）vs 附注标签（`git tag -a`，是带信息/可签名的独立 tag 对象）。发布版本用附注标签。

### 🎓 博士生视角
- reflog 是 append-only 的本地 HEAD 流水，记录 `commit/checkout/reset/merge` 等每一次移动及其前后 SHA；它**只存本地、不被 push**，因此是对「误操作」的最后安全网，但换机器/克隆拿不到。
- 附注标签本质是一个 `tag` 对象（有自己的 SHA、可含 message 与 GPG 签名），再被 `refs/tags/vX` 引用；轻量标签则 `refs/tags/vX` 直接指向 commit——这就是为什么 `cat-file -t v1` 可能是 commit、`cat-file -t v2` 是 tag。

### 📚 考研者视角
- 常考「detached HEAD 是什么、如何离开」——HEAD 直接指向 commit；离开用 `git checkout <branch>` 或 `git switch -c <newbranch>` 收编。
- 易错：「reflog 会不会随 push 共享」——**不会**，它是纯本地安全网；「`reset --hard` 误删提交后如何找回」——用 `git reflog` 找到旧 SHA 再 `git reset --hard <sha>`。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 工程决策与踩坑 | reset 三模式对照、reflog 救援、rebase/merge 取舍、大文件清理 |
| 🎓 博士生 | 第一性原理与底层机制 | 内容寻址 SHA-1、Merkle DAG、三路合并基线算法、packfile delta |
| 📚 考研者 | 标准考法与易错口径 | Git vs SVN、三区模型、detached HEAD、reset 三模式差异 |
