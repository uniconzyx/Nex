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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 248,407 | 全章 | 运维与工程工具知识合集：Linux、网络、排障命令速查；本章先读与「第1节 一、三类核心对象」「第2节 二、tree 与…」相关的部分 |
| 2 | [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,274 | 全章 | Shell 生产力框架（工程效率的入门必装）；本章先读与「第1节 一、三类核心对象」「第2节 二、tree 与…」相关的部分 |
| 3 | [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162,646 | 全章 | 命令行艺术：Linux 命令的体系化进阶指南；本章先读与「第1节 一、三类核心对象」「第2节 二、tree 与…」相关的部分 |
| 4 | [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 86,127 | 全章 | DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖；本章先读与「第1节 一、三类核心对象」「第2节 二、tree 与…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Docker 实战（入门到大神）<br><sub>尚硅谷</sub> | [BV1gr4y1U7CY](https://www.bilibili.com/video/BV1gr4y1U7CY/) | 全章 | 主线：镜像分层 → 容器生命周期 → Dockerfile 与多阶段构建 → 数据卷与网络 → Compose；看完回 `ex01`（blob 对象与内容寻址（SHA-1 复）核对 |
| 2 | 黑马程序员 · Git 全套教程<br><sub>黑马程序员</sub> | [BV1MU4y1Y7h5](https://www.bilibili.com/video/BV1MU4y1Y7h5/) | §1.1 第1节 一、三类核心对象 | 对象模型 → 分支本质 → merge/rebase → 冲突与 reflog 救援；配真实协作场景演示；看完回 `ex02`（内容寻址去重）核对 |
| 3 | GeekHour · 一小时 Git 教程<br><sub>GeekHour</sub> | [BV1HM411377j](https://www.bilibili.com/video/BV1HM411377j/) | §1.1 第1节 一、三类核心对象 | 一小时建立全局图：三区、HEAD、常用命令的对应关系，适合先看这个再进细节；看完回 `ex03`（commit / tree 对象结构）核对 |
| 4 | 于仕琪 · Linux 常用命令与 Shell<br><sub>于仕琪</sub> | [BV1Uv4y127tU](https://www.bilibili.com/video/BV1Uv4y127tU/) | 全章 | 25 分钟过一遍 13 个基本命令与 Shell 脚本骨架，南方科大老师讲得干净；看完回 `ex04`（分支是指向 commit 的指针）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《鸟哥的 Linux 私房菜（第 4 版）》 |
| 2 | 《Pro Git（第 2 版）》Chacon & Straub |
| 3 | 《Docker 技术入门与实战（第 3 版）》杨保华 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
