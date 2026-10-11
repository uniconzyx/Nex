# 三区模型与分支指针：工作区/暂存区/版本库
> 本节目标：把「改了文件为什么没进提交」「分支为什么这么轻」讲清楚。每个主题按三视角解析。

---

## 第1节 一、工作区 / 暂存区 / 版本库（三区模型）

Git 把文件状态分散在三个区域：**工作区（working tree）**是你直接编辑的目录；**暂存区（index / stage）**是「下一次 commit 的候选清单」，本质是待序列化成 tree 的草稿；**版本库（repository）**= 对象数据库（`.git/objects`）+ 引用（`.git/refs`、HEAD），即已固化的历史。
### 🧑‍💻 程序员视角
- `git add` 把工作区改动搬进 index；`git commit` 把 index 固化为一个 commit；三者关系用三件套看清：`git status`（工作区 vs index）、`git diff`（工作区 vs index）、`git diff --cached`（index vs HEAD）。
- 新手最大坑：改了文件没 `git add` 就 `git commit`，发现改动没进去——`commit` 只提交 index，不提交工作区未暂存的改动。
- 部分暂存技巧：`git add -p` 只把某文件的部分 hunk 放入暂存区，便于把一个文件里的多个逻辑改动拆成多个提交。

### 🎓 博士生视角
- index 是「工作树到对象库之间的缓冲层」：它是一个有序的（path → blob SHA）映射，commit 时整个 index 被一次性序列化成 tree 对象，因此 index 即「下个 tree 的蓝本」。
- 三区对应三种状态：工作区=已修改未记录；index=已记录待提交（staged）；版本库=已提交（committed）。`git status` 本质在报告「工作区与 index 的差异」「index 与 HEAD 的差异」。

### 📚 考研者视角
- 标准三区定义与转换命令是高频考点：工作区↔暂存区用 `add`/`restore --staged`；暂存区↔版本库用 `commit`/`reset`；工作区↔版本库用 `checkout`/`restore`。
- 易错口径：「`git commit` 提交的是 index 而非工作区」；「`git diff` 看工作区相对 index，`git diff --cached` 看 index 相对 HEAD」。

---

## 第2节 二、分支是指向 commit 的指针；HEAD 是「当前位置」

在 Git 里**分支只是 `.git/refs/heads/<name>` 里存的一行 commit SHA**（41 字节：40 位十六进制 + 换行）。`HEAD` 是「当前所在位置」的符号引用：正常时指向某个分支（`ref: refs/heads/main`），detached 时直接存一个 commit SHA。
### 🧑‍💻 程序员视角
- 创建/切换分支极快：只是写一个或改一个 41 字节文件，与仓库大小无关——这也是 Git 鼓励「大量短命分支」做实验的原因。
- 现代命令：`git switch -c <name>` 新建并切换；旧式 `git checkout -b` 仍可用但语义重载。切换分支实质是「把 HEAD 指向新分支，并把工作树更新成该分支指向的 tree」。

### 🎓 博士生视角
- 分支与 commit 完全解耦：N 个分支 = N 个指针指向 DAG 中某个节点；「分支合并」往往是**移动指针**（快进）而非拷贝数据。
- HEAD 作为符号引用的精确定义：`HEAD` 的值是「引用的引用」；读取当前 commit 时需做一次解引用（`HEAD -> refs/heads/main -> <sha>`）。

### 📚 考研者视角
- 常考「为什么 Git 分支比 SVN 轻量」：**SVN 分支是目录拷贝（O(文件数)）**，Git 分支只是指针（O(1)）。
- 易错：「HEAD 与分支的关系」——HEAD 指向当前分支，分支指向 commit；切分支=改 HEAD；`git branch` 列出的名字都是「指向 commit 的引用」。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 工程决策与踩坑 | reset 三模式对照、reflog 救援、rebase/merge 取舍、大文件清理 |
| 🎓 博士生 | 第一性原理与底层机制 | 内容寻址 SHA-1、Merkle DAG、三路合并基线算法、packfile delta |
| 📚 考研者 | 标准考法与易错口径 | Git vs SVN、三区模型、detached HEAD、reset 三模式差异 |
