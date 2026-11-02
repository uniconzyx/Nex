# Git 对象模型与分支实战手记：凯喵用 reflog 救回一次误删分支的十二个现场

> 这一章讲 Git 的对象模型、暂存区/工作区/仓库三区、分支与合并、reset/checkout/reflog。命令谁都会敲，但真出事故时能不能救回来，取决于你是否知道"Git 底层到底存了什么"。这篇手记用十二个现场把这条链路走一遍。

## 开场：Git 只存四种对象，其余都是视图

Git 的底层只有四种对象，全部存在 `.git/objects` 里，用内容的 SHA-1 命名：

```text
blob   文件内容（不含文件名）
tree   目录（记录「文件名 → blob/tree 的映射」）
commit 一次提交（指向一个 tree + 父 commit + 作者 + 消息）
tag    附注标签（指向某个 commit）
```

分支、HEAD、暂存区、remote-tracking 全都是**指针或索引**，不是数据副本。理解这一点，很多"神奇"的操作就变得理所当然：切分支为什么瞬间完成（只改一个指针）、为什么删分支还能救回（对象还在，只是没有指针指向它）。

下面十二个现场，前六个是对象与三区，后六个是分支与救援。

### 现场一：`git branch -d` 删掉分支后以为代码没了

```bash
git branch -D feature/payment     # 强制删除（未合并也能删）
# 后悔了
```

代码**没丢**。删除分支只是删掉 `.git/refs/heads/feature/payment` 这个指针文件，commit 对象们还在对象库里，只是变成了"不可达对象"（没有引用指向）。

救回的方法：

```bash
git reflog                       # 看所有 HEAD 移动记录
# a1b2c3d HEAD@{3}: commit: 完成支付回调
git branch feature/payment a1b2c3d      # 用那个 commit 重建分支
```

`reflog` 默认保留 90 天（`gc.reflogExpire`），所以绝大部分误删都能救。但如果已经跑过 `git gc --prune=now`，不可达对象可能被清掉——**这是唯一真正会丢数据的场景**。

### 现场二：`reflog` 只有 HEAD 的移动，分支的移动看不到

有人 `git reflog` 里找不到某个分支的历史，以为记录丢了。实际上 `reflog` 默认只记 HEAD，每个分支还有自己的 reflog：

```bash
git reflog show feature/payment      # 分支自己的移动记录
ls .git/logs/refs/heads/             # 每个分支一个日志文件
```

三类 reflog 要区分：

```text
.git/logs/HEAD               HEAD 的移动（切分支、commit、reset、merge 都记）
.git/logs/refs/heads/<name>  各本地分支的移动
.git/logs/refs/remotes/<name> 远程跟踪分支的更新（fetch 时）
```

这也是为什么 `reset --hard` 之后还能救：它改了 HEAD 和分支指针，但旧值被记进了 reflog。

### 现场三：`reset --hard` 之后工作区代码没了，对象还在

```bash
git reset --hard HEAD~1          # 丢弃最近一次提交及其所有改动
```

`--hard` 会同时改三处：分支指针回退、暂存区重置、**工作区文件被覆盖**。工作区那部分确实没进 Git，救不回来。

但**提交里的内容是可救的**：

```bash
git reflog                       # 找到 reset 之前的 commit
git reset --hard HEAD@{1}        # 回到 reset 之前的状态
```

三种 reset 模式的差别必须记牢：

```text
--soft    只移动分支指针，暂存区和工作区不动
          → 想「撤销 commit 但保留改动已暂存」
--mixed   移动指针 + 重置暂存区，工作区不动（默认）
          → 想「撤销 commit 和 add，改动还在工作区」
--hard    三处全改
          → 想「彻底丢弃」，也是唯一会丢工作区改动的模式
```

凯喵的习惯：**不确定的时候先用 `--soft`，确认后再决定是否继续回退**。`--hard` 只在"这份改动我确实不要了"时用。

### 现场四：以为 `checkout` 和 `switch` 不一样，其实只是拆分了语义

Git 2.23 把 `checkout` 拆成两个命令，因为它的语义太杂：

```text
git switch <branch>        切分支（专心做一件事）
git restore <file>         恢复文件（专心做一件事）

老写法：
git checkout <branch>      切分支
git checkout -- <file>     恢复文件（危险：会覆盖未提交改动）
```

拆分解决的是"命令同名但语义完全不同"的困惑——`checkout -- file` 覆盖工作区是很多新人丢改动的元凶，而 `checkout branch` 是安全的。现在用 `switch`/`restore` 一眼就能看出意图。

### 现场五：`git restore --source` 找回被删的文件

```bash
rm important.java                # 手滑删了
git status                       # deleted: important.java

git restore important.java       # 从暂存区恢复
# 如果暂存区也没有（没 add 过），从某个 commit 恢复：
git restore --source=HEAD~1 important.java
```

三区的恢复来源不同，必须分清：

```text
git restore <file>                     从「暂存区」恢复到工作区
git restore --staged <file>            用「HEAD」覆盖暂存区（即 unstage）
git restore --source=<commit> <file>   从指定 commit 恢复到工作区
```

`--staged --worktree` 可以同时作用于两区。这个组合在"彻底把文件恢复成某个版本"时最有用。

### 现场六：`git add` 之后改文件，`git diff` 看到的是"没改"

```bash
echo "v1" > a.txt
git add a.txt
echo "v2" > a.txt
git diff                # 空！（因为 diff 默认比较「工作区 vs 暂存区」）
git diff --staged       # 显示 v1（暂存区 vs HEAD）
git diff HEAD           # 显示 v2（工作区 vs HEAD）
```

三个 `diff` 的比较对象完全不同，这是最容易搞混的一组：

```text
git diff            工作区 ↔ 暂存区   （还没 add 的改动）
git diff --staged   暂存区 ↔ HEAD     （已 add、待提交的改动）
git diff HEAD       工作区 ↔ HEAD     （全部未提交的改动）
```

凯喵的习惯是 `git diff HEAD` 做提交前 review——它一次性覆盖"已暂存 + 未暂存"的所有改动，不会漏看。

### 现场七：fast-forward 与三方合并的区别说不清

```bash
# 场景：main 没有新提交，feature 领先 3 个提交
git switch main && git merge feature
# → Fast-forward：main 指针直接前移，不产生合并提交

# 场景：main 和 feature 各有新提交
git merge feature
# → 三方合并：产生一个新的 merge commit，有两个父提交
```

区别的本质是**"能不能只移动指针"**。fast-forward 时历史是一条直线，不需要新提交；分叉后必须生成 merge commit 来"缝合"两条历史。

`--no-ff` 强制生成合并提交，好处是**保留了"这是一个功能分支"的信息**——否则 fast-forward 之后，从历史里完全看不出这些提交曾经属于一个独立分支。团队规范里常见"主干合并必须 `--no-ff`"，就是为了留住这个结构。

`--squash` 则是另一条路：把 feature 的所有提交压成一个改动放进暂存区，不产生合并提交、也不保留原提交历史。适合"功能分支提交很碎（wip、fix typo）"的场景。

### 现场八：rebase 之后别人的分支崩了

`rebase` 会**重写提交**（新的 SHA-1），这是它和 `merge` 最本质的差别：

```text
merge ：保留原有提交，新增一个合并提交 → 历史真实但不线性
rebase：把提交"搬到"新基底上，产生全新提交 → 历史线性但被改写
```

所以有一条铁律：**不要 rebase 已经推送并被别人使用的分支**。因为别人本地的提交还指向旧 SHA-1，rebase 后推到远端会变成两套历史，别人一 pull 就是一堆冲突。

正确的分工：

```text
个人分支（未推送 / 只有自己在用）：可以随意 rebase，保持历史干净
共享分支（main / develop）：只用 merge，绝不 rebase
```

如果确实 rebase 了共享分支，只能用 `git push --force-with-lease`（比 `--force` 安全，会在远端有你不知道的新提交时拒绝），并提前通知所有人。

### 现场九：冲突解决时把别人的改动整段删了

冲突标记的形式：

```text
<<<<<<< HEAD
当前分支的版本
=======
被合并分支的版本
>>>>>>> feature/payment
```

最常见的错误是"选一边、删另一边"——如果两边都有有效改动，这样会静默丢掉功能。正确做法是**理解两边各自想做什么，然后写出第三个版本**：

```java
<<<<<<< HEAD
double fee = amount * 0.006;              // 我们：费率调整
=======
double fee = amount * 0.005 + 1.0;        // 他们：加了保底
>>>>>>> feature/payment
```

正确的解法不是二选一，而是合并意图：

```java
double fee = Math.max(amount * 0.006, amount * 0.005 + 1.0);
```

冲突解决后必须做的三件事：`git add` 标记已解决、跑测试（冲突往往引入逻辑错误而非语法错误）、`git diff --staged` 通读一遍确认没有误删。

### 现场十：`git stash` 之后切分支，忘了 stash 里有重要改动

```bash
git stash                  # 暂存当前改动
git switch hotfix          # 去修紧急 bug
# ……几天后……
git stash list             # 发现有三条记录，不知道哪个是哪个
```

`git stash` 默认不给说明，多条记录后完全无法辨认。正确习惯是**永远带消息**：

```bash
git stash push -m "wip: 支付回调重试逻辑（未完成）"
git stash list
# stash@{0}: On main: wip: 支付回调重试逻辑（未完成）

git stash show -p stash@{0}      # 看具体改动
git stash pop                     # 应用并删除
git stash apply stash@{0}         # 应用但保留（更安全）
```

凯喵的建议：`apply` 而不是 `pop`——`pop` 失败时（有冲突）stash 不会被删除，但容易让人以为已经恢复；`apply` 明确"先应用、确认没问题再 `drop`"。

### 现场十一：`git blame` 找到的作者不对，因为经历了格式化提交

`git blame` 显示某行的最后修改者是"某人"，但那人只是跑了一次 `prettier` 全量格式化。

绕过办法：

```bash
# 1. 忽略纯空白改动
git blame -w file.java

# 2. 忽略某个提交（比如格式化提交）
git blame --ignore-rev a1b2c3d file.java

# 3. 批量忽略（把格式化提交写进文件）
echo "a1b2c3d" >> .git-blame-ignore-revs
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

第三种是团队级的最佳实践：把所有"纯格式化"提交记进 `.git-blame-ignore-revs` 并提交到仓库，所有人的 `git blame` 都会自动跳过它们，追溯"真正改逻辑的人"。

### 现场十二：`git bisect` 手工二分，找了两个小时

线上出现一个 bug，知道"上周还好"，但不知道哪个提交引入的。手工 checkout 各个版本来回试，两小时才定位。

正确姿势是让 Git 自动二分：

```bash
git bisect start
git bisect bad                    # 当前版本是坏的
git bisect good v1.2.0            # 这个 tag 是好的
# Git 自动 checkout 中间版本，你只需要判断好坏
git bisect good    # 或 git bisect bad
# ……重复 log2(N) 次……
git bisect reset                  # 结束，回到原分支
```

1000 个提交只需 10 次判断。更省事的是**自动 bisect**：

```bash
git bisect run ./test.sh          # 脚本返回 0 = good，1 = bad
# Git 全自动跑完，直接告诉你第一个坏提交
```

凯喵的经验：只要有一个能复现问题的脚本（哪怕是 curl + grep），就该用 `bisect run`。它把"两小时手工排查"变成"五分钟机器跑完"，是所有 Git 命令里性价比最高的一个。

## 三视角解析
### 🧑‍💻 程序员视角
`git branch -d` 删掉分支后，提交对象其实还在（只要 reflog 没被清理），`git reflog` 找到那个 SHA 再 `git branch recover <sha>` 就能救回来。但 `reflog` 只记录 HEAD 的移动，分支自己的 reflog 也要看（`git reflog show <branch>`）。`reset --hard` 之后工作区代码没进过暂存区就真的找不回，除非用过 `git add`（那就在对象库里）。`checkout` 与 `switch` 的差别在于前者兼管文件恢复，容易误伤未提交改动。

### 🎓 博士生视角
Git 的核心是「内容寻址的对象库」：blob（文件内容）、tree（目录）、commit（快照 + 父指针）、tag。所有对象以 SHA-1 命名，内容不变则哈希不变，天然去重。分支只是「指向 commit 的可移动指针」，因此创建/切换分支是 O(1)。`reflog` 是「HEAD 与分支引用的本地日志」，是误操作恢复的最后一道保险，但它只在本地、有保留期（默认 90 天），且不会随 `push` 传播。

### 📚 考研者视角
工程岗高频：
1. **三种对象与引用**：blob/tree/commit 的关系，分支与 HEAD 的本质。
2. **`merge` 与 `rebase`**：前者保留分叉历史、后者线性化但改写提交；「不要 rebase 已推送的公共分支」。
3. **`reset` 三种模式**：`--soft`（只移动 HEAD）、`--mixed`（默认，重置暂存区）、`--hard`（连工作区一起重置）。
4. **误操作恢复**：`reflog` + `cherry-pick`/`branch` 找回丢失提交。

## 收尾：凯喵的 Git 急救五招

出事时按顺序想这五件事：

**先别慌，对象都在** —— 只要没跑 `gc --prune=now`，误删的分支/提交都能从 `reflog` 找回。

**reflog 分三种** —— HEAD、本地分支、远程跟踪各有日志，找错地方会以为记录没了。

**reset 三模式分清** —— `--soft` 只动指针、`--mixed` 加动暂存区、`--hard` 连工作区一起，只有 `--hard` 会丢改动。

**rebase 只碰私有分支** —— 已推送共享的分支绝不 rebase；万不得已用 `--force-with-lease` 并提前通知。

**bisect 定位秒杀手工** —— 有复现脚本就 `bisect run`，1000 个提交 10 次判断。

最后说一句观念上的话。Git 的命令多、参数杂，看起来难学，但它的底层模型极其简洁：**四种对象 + 一堆指针**。所有的"神奇操作"都只是移动指针；所有的"不可恢复"都源于"对象被真正清除"。

理解这一点之后，你对 Git 的心态会从"小心翼翼地敲命令、怕搞坏"变成"知道每一步在改哪个指针、出错也知道怎么退回去"。凯喵见过的最熟练的工程师，不是记得命令最多的人，而是**任何时候都能说出"我现在在哪个 commit、哪些改动在哪一区、下一步会改哪个指针"**的人——因为他们操作的从来不是命令，而是那个模型。
