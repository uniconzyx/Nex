# Git 核心：对象模型与分支 — 学习目标

## 一、本章定位

本章是「工程工具」学科第三章，进入 Git 这条线（tool-ch04 继续讲协作与冲突处理）。第一章/第二章你掌握了
Linux 文件系统与进程模型；本章把版本控制的「底层模型」讲透：Git 不是「存差异的数据库」，而是一个
**内容寻址的对象库**（blob/tree/commit/tag），配合「工作区/暂存区/版本库」三区与「分支只是指针」的抽象。
理解了模型，所有命令（`add`/`commit`/`reset`/`merge`/`rebase`）都只是对这个模型的增删查改。

- **先修**：无硬前置（本线首章）；但 tool-ch01/02 的「文件系统/进程」直觉有助于理解 `.git` 目录结构。
- **衔接**：tool-ch04（Git 协作）建立在本章对象模型之上；理解 DAG 后才能讲清 push/fetch/冲突救援。
- **面试权重**：★★★★★ —— 对象模型、三区、reset 三模式、detached HEAD/reflog、rebase vs merge 是后端/SRE/客户端面试必考题。

## 二、学习目标

学完本章，你应当能够：

1. **讲清四类对象与内容寻址**：blob/tree/commit/tag 各自存什么；SHA-1 如何由「类型+长度+内容」算出；
   为什么说「相同内容永远同一 SHA」「blob 不含文件名」。
2. **画出三区模型并说清命令归属**：工作区/暂存区/版本库各自职责；`add`/`commit`/`reset`/`checkout`/`restore`
   分别在这三区之间如何搬运数据。
3. **解释分支为何轻量**：分支只是 `.git/refs/heads/<name>` 里一个 41 字节的 commit SHA；HEAD 是「当前位置」的符号引用。
4. **区分快进合并与三方合并**：判定条件（目标是否为源的祖先）；merge commit 为何有两个 parent；
   说清 rebase 与 merge 的团队取舍（线性历史 vs 真实拓扑、改写历史 vs 不改写）。
5. **讲清冲突的充要条件**：不是「都改了就冲突」，而是「相对共同祖先 ours 与 theirs 都改了同一区域且结果不同」；
   能描述 `<<<<<<<` 标记与解决流程；理解 `merge-base` 作为三方合并基线的角色。
6. **熟用 reset 三模式与安全回退**：`--soft`/`--mixed`/`--hard` 对三区的影响范围递增；
   区分 `checkout`/`restore`/`revert`；已知 `reset --hard` 后能用 `reflog` 救援。
7. **理解 detached HEAD 与救援网**：detached 的含义与离开方式；reflog 是本地 append-only 安全网、不随 push 共享；
   会用 `git branch rescue <sha>` 收编游离提交。
8. **认识 tag/stash/cherry-pick**：轻量标签 vs 附注标签；stash 暂存半成品；cherry-pick 摘取单个提交。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写四类对象与 reset 三模式差异 | 习题 choice |
| 理解 | 给一段操作推断三区状态 | 习题 output |
| 应用 | 用 Python 复算 blob SHA、模拟 Merkle DAG | examples 实跑 |
| 分析 | 能定位「reset --hard 误删后用 reflog 找回」 | pitfalls 第 4/14 条 |
| 评价 | 能论证「为什么不对共享分支 rebase/reset」 | interview 第 4 题 |

## 四、常见认知误区（先破后立）

1. **「`git commit` 提交的是工作区所有改动」** —— 错，`commit` 只提交**暂存区（index）**；未 `add` 的改动不会进提交。
2. **「分支是目录拷贝，很重」** —— 错，Git 分支只是指向 commit 的 41 字节指针，创建/切换 O(1)。
3. **「冲突就是双方都改了同一文件」** —— 错，必须「相对共同祖先，两边改了同一区域且结果不一致」才冲突；改在同一处但改成一模一样会自动合并。
4. **「detached HEAD 下的提交会立即被 GC 删掉」** —— 错，提交仍在对象库，只是无分支引用；用 `git reflog` 可找回。
5. **「`reset --hard` 只是回退提交」** —— 它会连工作区未提交改动一起抹掉，对共享分支还会改写他人历史。

## 五、学习路径建议

1. 先读 concept/01（对象模型），用 examples/ex01~ex04 把「blob/tree/commit、内容寻址、分支指针」变成直觉。
2. 读 concept/02（三区与分支），结合 examples/ex10（reset 三模式）理解三区搬运。
3. 读 concept/03（合并与冲突），用 examples/ex05~ex09 看线性/分叉/快进/三方/冲突的真实输出。
4. 读 concept/04（reset/reflog/tag），用 examples/ex11~ex12 验证 detached HEAD 救援与 stash/cherry-pick/tag。
5. 做 exercises.json 的 coding 题（SHA 复算、Merkle DAG、merge-base LCA），自测 interview.json，再用 project.json 交付一个迷你 Git 分析器。

## 六、与 GitHub 顶级资源的对接

- bregman-arie/devops-exercises（84k★）—— Git 练习题集，覆盖对象模型与合并
- jlevy/the-art-of-command-line（162k★）—— 命令行体系化进阶
- 推荐读物：《Pro Git》第 1–3 章（对象模型与分支）、官方 `git-scm.com/docs`


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 248407 | 运维与工程工具知识合集：Linux、网络、排障命令速查 |
| [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190209 | Shell 生产力框架（工程效率的入门必装） |
| [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162576 | 命令行艺术：Linux 命令的体系化进阶指南 |
| [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 84793 | DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 韩顺平 · 一周学会 Linux | [视频](https://www.bilibili.com/video/BV1Sv411r7vd/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Linux 教程（千万级学习人次） | [视频](https://www.bilibili.com/video/BV1dW411M7xL/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · 5h 打通 Git 全套教程 | [视频](https://www.bilibili.com/video/BV1vy4y1s7k6/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 狂神说 · Docker 教程 | [视频](https://www.bilibili.com/video/BV1og4y1q7M4/) | 本学科配套视频，建议结合本章示例与习题观看 |
