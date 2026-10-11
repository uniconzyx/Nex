# 常见陷阱：Git 协作、冲突处理与分支策略

> 每条都是「命令能跑通、但结果或安全性是错的」类型。按「现象 → 根因 → 正确做法」组织。

1. **把 `git pull` 当成「只是把远端拉取下来」** —— 现象：习惯性 `git pull`，结果本地被自动合并/重放，冲突在你没预料的时候出现，甚至多出一个 merge commit。根因：`pull` = `fetch` +（`merge` 或 `rebase`），它会**移动你的本地分支并改写工作区**。正确做法：先 `git fetch`，用 `git log --oneline main..origin/main` 看清差异，再自己决定 merge 还是 rebase；个人分支可配 `pull.rebase=true`。

2. **push 被拒就加 `--force`** —— 现象：推上去之后队友当天的工作从远端消失。根因：push 被拒 = non-fast-forward = 远端有你没整合的提交，`--force` 是无校验的直接覆盖。正确做法：`git fetch` → `git rebase origin/main`（或 merge）→ 解决冲突 → 再 push；确需强推时用 `--force-with-lease`，且仅限已沟通的个人分支。

3. **以为 `--force-with-lease` 是「安全的强推」，于是放心地改写共享分支** —— 现象：lease 校验通过了，历史照样被改写，队友 pull 后一堆冲突。根因：lease 只保证「不覆盖我没看过的提交」——如果你刚 fetch 过，租约天然一致，保护退化为允许覆盖。正确做法：共享分支回滚一律用 `git revert`（追加历史）；把 main/release 设为保护分支，从平台层面禁止强推。

4. **对已经 push 的分支做 rebase 再推** —— 现象：本地历史干净了，队友的提交变成孤儿，`push` 被拒后你强推，团队历史分裂。根因：rebase 改写 SHA，别人基于旧 SHA 的工作失去根基。正确做法：**黄金法则**——只对本地尚未推送的提交 rebase；已共享就用 merge。确需整理时全组沟通，重排后所有人 `git reset --hard origin/<branch>` 对齐。

5. **特性分支长期不与主干同步** —— 现象：两周后一次性合并，几百行冲突、合并花一整天还容易合错。根因：冲突概率与合并成本随「分支寿命 × 并行改动量」增长，集成得越晚代价越大。正确做法：每天 `git fetch` + `rebase`（或 merge）主干；分支寿命控制在 3 天以内，配合 feature flag 做未完成功能隔离。

6. **冲突解决直接用 `git checkout --ours/--theirs` 挑一边** —— 现象：「解决」完上线，发现对方的修复没了。根因：这两个选项是**整段丢弃另一侧**，不是合并；而且 union 也可能产出重复定义。正确做法：打开编辑器手工合并两侧语义（可开 `merge.conflictStyle diff3` 看到共同祖先那一行）；`--ours/--theirs` 只用于明确知道单边正确的情况。

7. **删掉冲突标记就以为解决了，忘了 `git add`** —— 现象：`git commit` 报 Committing is not possible because you have unmerged files。根因：Unmerged 路径在 index 里有 stage 1/2/3 三个版本，只有 `git add` 才会把它归一到 stage 0。正确做法：编辑 → `git add <file>` → `git merge --continue`（rebase 场景为 `--continue`，反悔用 `--abort`）。

8. **把含 `<<<<<<<` 标记的文件提交上线** —— 现象：构建失败或线上配置文件出现乱码般的标记。根因：冲突标记是 Git 的占位符，不是合法代码/配置。正确做法：提交前用 `grep -rn '^<<<<<<<\|^>>>>>>>' .` 自检，并把该检查做成 pre-commit 钩子或 CI 步骤。

9. **rebase 时搞反 ours / theirs** —— 现象：`git checkout --ours <file>` 结果拿到的却是「别人的」版本，一脸困惑。根因：rebase 是把你的提交重放到上游之上，此刻 **ours = 上游（正在写的基准），theirs = 你自己的提交**，与 merge 语义相反。正确做法：别背 ours/theirs，直接看冲突区内容或用 diff3 风格（`git checkout --conflict=diff3 <file>`）按 base 判断。

10. **把 `cherry-pick` 当成「移动提交」，忽略它的依赖集成** —— 现象：把一个 hotfix 摘到发布分支后编译不过。根因：cherry-pick 只复制**该提交相对其父的差异**，不带祖先；若它依赖更早的重构提交就缺上下文。正确做法：按依赖顺序逐个 cherry-pick（或整段 rebase --onto）；用 `-x` 让提交信息记录来源 SHA；注意新提交的 SHA 必然与原提交不同。

11. **回滚 merge commit 忘了 `-m`，或 revert 后再 merge 同一分支发现改动没回来** —— 现象：`git revert <merge-sha>` 报 error: commit is a merge；或者 revert 之后重新 merge，Git 说 Already up to date。根因：merge commit 有多个 parent，必须 `-m 1` 指定主线；而 revert 后 Git 认为那些提交已在历史里，再次 merge 会被跳过。正确做法：`git revert -m 1 <merge-sha>`；要重新引入被回滚的改动，需 `git revert <刚才那个 revert 提交>`。

12. **把 stash 当长期/跨分支存储** —— 现象：stash 里堆了十几条，几个月后 `stash@{7}` 到底是啥完全说不清。根因：stash 是**LIFO 栈**且没有命名空间，混入多人/多分支的半成品后极难辨识；未跟踪文件还**默认不入库**。正确做法：临时跳转（几分钟~几小时）才用 stash 并带 `-m` 说明；超过一天就 commit 到临时分支或用 `git worktree`；注意未跟踪文件要 `git stash -u`。

13. **误以为 pop/apply 一定能成功** —— 现象：`git stash pop` 报 Your local changes would be overwritten。根因：pop/apply 其实是一次合并，目标文件有本地改动时会拒绝覆盖。正确做法：先 `git status` 确认干净、必要时 `git restore` 目标文件；需要仔细保留时用 `git stash apply`（保留记录）+ `git stash drop`（确认后再删），而不是一步到位的 pop。

14. **把 reflog 当团队容灾手段** —— 现象：同事误删远端分支后问「你的 reflog 能恢复吗」，答案是不能。根因：reflog 是**纯本地**的 `.git/logs/HEAD` 流水，不随 push/bundle 传播，换机即无。正确做法：本地救援（`git reset --hard <sha>` / `git checkout -b rescue <sha>`）靠 reflog；团队级依赖远端备份、保护分支与 PR 记录；注意 reflog 保留期默认 90 天。

15. **`reset --hard` 前不确认有没有未提交改动** —— 现象：回退一个提交，结果连半天没提交的改动一起没了。根因：`--hard` 同时重置 HEAD、暂存区与工作区，未提交内容既不进对象库也无指针指向。正确做法：先 `git stash`（或临时 commit）；损失后立刻查 `git reflog`，未 commit 的内容还需在工作区不动的前提下抢救。

16. **`.gitignore` 写错位置或指望它忽略已跟踪文件** —— 现象：加了规则文件照样被提交；或 `build/` + `!build/keep.txt` 完全无效。根因：ignore 只对**未跟踪**文件生效；且一旦某目录被排除，Git 不再递归，`!` 救不回它的子文件。正确做法：已跟踪文件先 `git rm --cached <file>`；放行目录内个别文件要写成 `build/*` + `!build/keep.txt`（而不是 `build/`）。

17. **大文件进历史后才想起来清理** —— 现象：几百 MB 的日志/压缩包 commit 后 `git rm`，仓库仍然巨大，clone 要几分钟。根因：旧 blob 仍被历史提交引用，`git rm` 只让当前 tree 不含它。正确做法：新增用 `git lfs track`，历史用 `git filter-repo`（或 BFG）重写再 `git gc --prune=now`，通知全体重新克隆。

18. **忽视 `.gitattributes` 与换行一致性** —— 现象：Windows 同事提交后 CI 报一堆「整个文件被改动」，diff 满屏红绿。根因：CRLF/LF 不一致导致同一逻辑内容算出不同 blob。正确做法：仓库根加 `.gitattributes`（`* text=auto eol=lf`，Shell 脚本显式 `eol=lf`，二进制显式 `binary`），并设置 `core.autocrlf=false`。

19. **提交信息随手写，导致自动化发布失效** —— 现象：CI 生成的 CHANGELOG 缺项、版本号没升级。根因：`版本号/CHANGELOG` 是从 Conventional Commits 的 type 与 BREAKING 标记机器推导的，`update code` 这类信息无法解析。正确做法：统一 `feat|fix|...`(<scope>)「!」: <desc> 格式，本地用 commitlint + CI 复核，破坏性变更必须标 `!` 或写 BREAKING CHANGE footer。

20. **分支策略照抄，不考虑团队现实** —— 现象：小团队上了 Git Flow，develop 三个月没合回 main，两个「真相」各走各的。根因：策略取舍的核心是**集成频率 vs 质量门成熟度**，与团队规模、发布节奏、是否多版本维护强相关。正确做法：单一可部署主干 + 短命分支 + PR + CI 是通用底座；需要多版本并行维护才加 release/hotfix；每日多次发布且 CI 完善才上 Trunk Based + feature flag。
