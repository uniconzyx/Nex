# 对象模型：blob/tree/commit 与内容寻址存储
> 本节目标：把 Git 从「黑盒命令」还原成「内容寻址的对象数据库」。每个主题按 🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者 三视角解析。

---

## 第1节 一、三类核心对象（blob/tree/commit）与内容寻址（CAS）

Git 内核本质是一个**内容寻址的文件系统（content-addressable storage）**：所有数据都以「对象」形式存入 `.git/objects`，用其内容的 SHA-1 作为唯一键（文件名即哈希）。对象分四类——`blob`（文件内容）、`tree`（目录快照）、`commit`（提交）、`tag`（标签）。其中 **blob 只存内容、不含文件名**，文件名由 tree 记录。
### 🧑‍💻 程序员视角
- 内容寻址的现实收益：相同内容全局只存一份，天然去重；`git gc` 进一步用 packfile 把相似对象做 delta 压缩。
- 大文件是历史炸弹：一旦 `git commit` 进对象库，即便之后 `git rm`，旧 blob 仍在历史里，仓库体积不会降——必须用 `git filter-repo` / BFG 或 Git LFS 清理。
- 工程习惯：`.gitignore` 在提交前过滤；二进制/大文件交给 LFS，避免污染对象库。

### 🎓 博士生视角
- 对象键的精确算法：`SHA-1 = sha1('blob ' + len(content) + '\0' + content)`，tree/commit/tag 同理用各自类型名作前缀；内容定，哈希定，因此对象不可变、可校验。
- 这构成 **Merkle DAG**：commit 指向 tree，tree 指向 blob/子树，commit 间用 parent 指针连成有向无环图；任一底层字节变化都会沿 DAG 向上改变根 commit 的 SHA，形成「防篡改」的可验证结构。
- 形式化：commit 对象序列化为 `tree + parents + author + committer + message`，其 SHA 是整棵子树的根摘要。

### 📚 考研者视角
- 408/软工常考「Git 与 SVN 的区别」：**SVN 集中式、存差异（delta）**；**Git 分布式、存快照 + 内容寻址（SHA-1）**，每个克隆都是完整仓库。
- 易错口径：**blob 不含文件名，文件名在 tree 里**；「相同内容不同文件名」在 Git 里是同一个 blob 对象。
- 标准表述：Git 的对象数据库以「内容哈希」为索引，这是它与基于文件名/版本号寻址的 VCS 的根本区别。

---

## 第2节 二、tree 与 commit 的结构：快照而非差异

一个 `commit` 对象记录：指向顶层 `tree` 的指针、零或多个 `parent`（首提交无 parent，合并提交 ≥2 个）、author/committer 与时间、提交说明。一个 `tree` 对象记录该目录下每条目：文件模式（如 100644）、类型（blob/tree）、子对象 SHA、名字。
### 🧑‍💻 程序员视角
- 「提交是快照不是差异」的工程含义：`git checkout <任意版本>` 直接定位那一棵 tree，复杂度与历史长度无关（O(1) 取快照），不必像 SVN 那样逐版本回放差异。
- 分支、标签都只是「指向某个 commit 的轻量引用」；删分支只是删一个 41 字节的引用文件，对象本身还在（直到 GC 且无人引用）。

### 🎓 博士生视角
- commit 与 tree 解耦：commit 是「时间点 + 元数据」，tree 是「目录结构的不可变描述」；同一 tree 可被多个 commit 共享（如仅改一个文件，其余子树 tree 对象复用）。
- 父指针使 commit 构成 DAG 而非链：线性历史是 DAG 退化为链的特殊情况；合并提交的「两个 parent」正是 DAG 分叉/汇合的数学表达。

### 📚 考研者视角
- 常考：commit 对象里**包含哪些字段**（tree 指针、parent、author、committer、message）；tree 对象**描述目录结构**而非文件内容本身。
- 易错：「为什么 Git 切换/比较版本快」——直接取快照对象，不依赖逐版本 diff；「为什么分支轻量」——分支只是指向 commit 的指针。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 工程决策与踩坑 | reset 三模式对照、reflog 救援、rebase/merge 取舍、大文件清理 |
| 🎓 博士生 | 第一性原理与底层机制 | 内容寻址 SHA-1、Merkle DAG、三路合并基线算法、packfile delta |
| 📚 考研者 | 标准考法与易错口径 | Git vs SVN、三区模型、detached HEAD、reset 三模式差异 |
