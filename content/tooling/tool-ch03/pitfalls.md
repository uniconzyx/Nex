# 常见陷阱：Git 对象模型与分支

> 每条都是「执行能通过、但结果或安全性是错的」类型。按「现象 → 根因 → 正确做法」组织。

1. **把 `git commit` 当成「提交工作区所有改动」** —— 现象：改了文件直接 commit，发现改动没进历史。根因：`commit` 只固化**暂存区（index）**，未 `git add` 的改动不会进提交。正确做法：提交前用 `git status` 确认待提交项；需要全部提交用 `git add -A` 再 `commit`，或用 `git commit -a`（仅已 tracked 文件）。

2. **`git reset --hard` 把未提交的改动全抹掉** —— 现象：reset 后发现半天的工作没了。根因：`--hard` 会同时重置 **HEAD、暂存区、工作区**，工作区未提交的修改被直接丢弃且（若无 reflog 指向）难找回。正确做法：不确定时用 `--soft`/`--mixed`；确需 `--hard` 前先 `git stash` 或确认改动已提交。

3. **对已经 push 的分支做 `reset --hard` + 强推** —— 现象：你「整理」了历史，队友 `pull` 后冲突满天飞甚至丢失提交。根因：`reset` 改写提交 SHA，强推（`git push --force`）把共享历史推翻，他人基于旧 SHA 的工作变成孤儿。正确做法：共享分支永远用 `git revert` 做可协作回滚；必须强推时用 `--force-with-lease` 且先沟通。

4. **在 detached HEAD 下提交后切走「提交丢了」** —— 现象：checkout 一个老提交做了实验性提交，切回 main 后找不到它。根因：detached 下的提交不属任何分支，离开后无引用指向，最终被 GC。正确做法：提交后立即 `git branch rescue <sha>` 或 `git checkout -b rescue` 收编；若已切走，用 `git reflog` 找到旧 SHA 再建分支。

5. **以为 `git checkout -- <file>` 会动 HEAD** —— 现象：想恢复某个文件却担心「切了分支」。根因：`checkout -- file` 与 `git restore` 只动**文件内容**，不切换分支、不动 HEAD。正确做法：恢复工作区用 `git restore --source=HEAD --worktree <file>`；切换分支用 `git switch <branch>`（这才是动 HEAD 的）。

6. **冲突时直接提交含 `<<<<<<<` 标记的文件** —— 现象：合并冲突后没仔细看就 add+commit，代码里残留冲突标记上线。根因：冲突标记是 Git 的占位符，不是合法代码/数据。正确做法：编辑文件手工消除 `<<<<<<<`/`=======`/`>>>>>>>`，确认语义后再 `git add`+`git commit`；用 `git diff` 复核。

7. **`git merge` 默认快进导致历史「看起来没合并过」** —— 现象：feature 合进 main 后 `git log` 是一条直线，看不出曾合并。根因：目标分支是源的祖先时 merge 默认**快进**（只移指针），不产生 merge commit。正确做法：想保留「合并痕迹」用 `git merge --no-ff`；CI/发布分支通常强制 `--no-ff`。

8. **对已共享的分支做 rebase 再强推** —— 现象：rebase 自己的提交后 push 被拒，强推后队友历史错乱。根因：rebase **改写提交 SHA**（旧提交被新提交取代），已共享的旧提交仍被他人引用，造成分叉。正确做法：只对**本地、未 push** 的提交 rebase 整理；共享分支用 merge 而非 rebase。

9. **以为 `git rm` 只删工作区** —— 现象：`git rm` 后发现「已暂存的删除」也一起进了下次提交。根因：`git rm` 同时删除工作区文件**并**从 index 移除；若只想停止跟踪、保留工作区文件，要用 `git rm --cached`。正确做法：删文件并入库用 `git rm`；仅取消跟踪保留文件用 `git rm --cached <file>`。

10. **`.gitignore` 对已 tracked 文件无效** —— 现象：把 `config.local` 加进 `.gitignore` 后它仍被提交。根因：`.gitignore` 只对**未跟踪**文件生效；一旦文件已被 track，忽略规则不再管它。正确做法：先 `git rm --cached <file>` 取消跟踪，再靠 `.gitignore` 防止重新误加。

11. **大文件提交进历史后用 `git rm` 删不掉体积** —— 现象：误提交一个 500MB 文件，`git rm` 后仓库 clone 依旧巨大。根因：旧 blob 仍留在历史对象里，`git rm` 只让当前提交不含它，历史提交仍引用它。正确做法：用 `git filter-repo` 或 BFG 重写历史清除大对象，并改用 Git LFS 管理大文件。

12. **没搞清 `git pull` 是 fetch+merge 还是 fetch+rebase** —— 现象：`pull` 后多出意料之外的合并提交，或本地提交被重排。根因：`pull` = `fetch` +（默认 `merge`，或配置了 `rebase`）。两者的历史形态完全不同。正确做法：明确团队约定；想要线性历史配置 `pull.rebase=true` 或显式 `git pull --rebase`；想看清动作先 `git fetch` 再手动 `merge`/`rebase`。

13. **在错误分支上提交，没有及时迁移** —— 现象：把功能提交到了 main，feature 分支没有这些改动。根因：提交落到当前 HEAD 指向的分支，切到正确分支不会自动带过去。正确做法：未 push 时 `git reset --soft` 退回改动到工作区，切分支后重新提交；已提交则用 `git cherry-pick <sha>` 把该提交摘到正确分支。

14. **把密码/token 提交进历史，`--amend` 删不掉** —— 现象：提交后发现含密钥，`git commit --amend` 改了最新提交，但旧提交（含密钥）仍在历史里。根因：`amend` 只是用新提交替换，旧对象仍在对象库中，且可能已被 push。正确做法：立即轮换泄露的密钥；用 `git filter-repo`/`BFG` 从整个历史清除，并加 `.gitignore` 与预提交钩子（如 gitleaks）防再犯。
