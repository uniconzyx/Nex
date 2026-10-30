# Git 协作：分支策略与冲突处理 — 学习目标

## 一、本章定位

本章是「工程工具」学科 Git 线的第四章，承接 tool-ch03（Git 核心：对象模型与分支）。第三章你已经知道
Git 是一个**内容寻址的对象库**、分支只是指向 commit 的指针、merge/rebase 会把提交图拼出不同形状。
本章回答的是下一个问题：**当这些操作发生在「多人 + 远端」的环境下，会发生什么、怎么不出事。**

- **先修**：`tool-ch03`（对象模型、三区、merge-base、reset/rebase 语义）。
- **衔接**：本章内容是 Docker/CI 章节（tool-ch05/06）的前置——CI 流水线的每一步都建立在
  「每次 push 都能被安全地集成」这一假设上；也是团队 Code Review 文化的操作基础。
- **面试权重**：★★★★★ —— pull 的真实语义、push 被拒与 `--force-with-lease`、冲突解决流程、
  rebase 黄金法则、stash/reflog 救援、分支策略选型，是后端 / SRE / 客户端高频面试题。

## 二、学习目标

学完本章，你应当能够：

1. **分清三类引用**：本地分支 `refs/heads/*`、远端跟踪引用 `refs/remotes/origin/*`、远端真实引用。
   能解释为什么 `git fetch` 安全到「随时可以执行」，而 `git pull` 需要谨慎。
2. **说清 pull = fetch + merge / rebase**：能画出三种历史形态（快进 / merge commit / 线性重放），
   并说明 `pull.rebase=true` 与 `--rebase-preserve-merges`（新版 `--rebase=merges`）的作用差异。
3. **定位 push 被拒绝的根因**：non-fast-forward（本地不是远端祖先）；能用
   `git fetch` + `git log --left-right` 判断落后了几个提交，并给出 rebase / merge 两条修复路径。
4. **论证为什么 `--force-with-lease` 比 `--force` 安全**：lease 是一条「我上次看到的远端位置」的断言，
   远端位置变了就拒绝；并知道共享分支的**正确回滚手段是 `revert`**。
5. **掌握冲突的完整解决流程**：冲突的充要条件（相对共同祖先，两侧改了同一区域且结果不同）；
   三方合并的基线是 merge-base；冲突标记三段含义；`--ours/--theirs`、`diff3` 风格、`rerere` 的用法与风险。
6. **熟练使用搬运与救急命令**：`cherry-pick`（复制单个提交）、`stash`（半成品栈）、`reflog`（本地后悔药）；
   知道 `reset --hard` 之后如何找回、`--amend` 丢的提交去哪儿了。
7. **按场景选型分支策略**：能在 Git Flow / GitHub Flow / Trunk Based 之间做决策并给出理由，
   要点出各自的发布单元、长期分支数与失败模式。
8. **写出可协作的提交与仓库配置**：Conventional Commits 格式与语义化版本推导；
   `.gitignore` / `.gitattributes` / Git LFS 各自解决什么问题，以及 `--force-with-lease` 之外的仓库卫生项。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写三类引用与 pull 的真实分解式 | 习题 choice |
| 理解 | 给定操作序列推断 a head/behind 与历史形态 | 习题 output |
| 应用 | 用代码复刻 merge-base、三方合并、stash 栈、ignore 匹配 | examples 实跑 |
| 分析 | 能判断「一次丢失提交的事故」到底走了哪一步 | pitfalls 第 3/9/10 条 |
| 评价 | 能论证「为什么共享分支不能强推 / 不能 rebase」 | interview 第 1/3 题 |

## 四、常见认知误区（先破后立）

1. **「pull = 拉取」是一个动作** —— 错，`pull` = `fetch`（更新远端跟踪引用）+ `merge` 或 `rebase`；
   它**会改动你的本地分支和工作区**，而 `fetch` 不会。
2. **「push 被拒就直接 `--force`」** —— 错，被拒说明远端已有你没看过的新提交；`--force` 会让它们消失。
   至少使用 `--force-with-lease`，更推荐先 `fetch` 再整合。
3. **「冲突 = 两个人都改了同一个文件」** —— 错，必须**同一区域且结果不同**；改同一处但改成一模一样会自动合并。
4. **「reflog 会跟着 push 传上去」** —— 错，reflog 是**纯本地**的安全网，换机器即失效。
5. **「stash 队列是 FIFO」** —— 错，它是**栈（LIFO）**，`stash@{0}` 是最近压入的那条。
6. **「`.gitignore` 能忽略任何文件」** —— 错，对**已跟踪**文件无效；且被排除的**目录**内部不能再用 `!` 救回子文件。

## 五、学习路径建议

1. 先读 concept/01（fetch/pull/push），配合 examples/ex01、ex10 建立三类引用与 push 安全的心智模型。
2. 读 concept/02（冲突），用 examples/ex02~ex05 实测 merge-base、三方合并自动通过与冲突两组对照、
   冲突标记解析与 rerere。
3. 读 concept/03（搬运与救援），用 examples/ex06~ex09 看 rebase 拓扑、cherry-pick 复制、stash 栈、reflog 救援。
4. 读 concept/04（策略与规范），用 examples/ex11~ex14 跑提交信息校验器、.gitignore 匹配器、策略决策器、bisect。
5. 做 exercises.json（8 题：6 基础 + 2 算法），自测 interview.json，再用 project.json 交付一个协作工具箱。

## 六、与 GitHub 顶级资源的对接

- bregman-arie/devops-exercises（84k★）—— Git / CI 练习题集，含分支策略与冲突场景
- jlevy/the-art-of-command-line（162k★）—— 命令行体系化进阶，含 Git 别名与日常流水线
- trimstray/the-book-of-secret-knowledge（248k★）—— 运维与安全知识合集
- 推荐读物：《Pro Git》第 3、5、6 章（分支、分布式 Git、GitHub）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 248,407 | 全章 | 运维与工程工具知识合集：Linux、网络、排障命令速查；本章先读与「`pull` 不是「拉取」」「push 为什么被拒绝，以…」相关的部分 |
| 2 | [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,209 | 全章 | Shell 生产力框架（工程效率的入门必装）；本章先读与「`pull` 不是「拉取」」「push 为什么被拒绝，以…」相关的部分 |
| 3 | [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162,576 | 全章 | 命令行艺术：Linux 命令的体系化进阶指南；本章先读与「`pull` 不是「拉取」」「push 为什么被拒绝，以…」相关的部分 |
| 4 | [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 85,071 | 全章 | DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖；本章先读与「`pull` 不是「拉取」」「push 为什么被拒绝，以…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Docker 实战（入门到大神）<br><sub>尚硅谷</sub> | [BV1gr4y1U7CY](https://www.bilibili.com/video/BV1gr4y1U7CY/) | 全章 | 主线：镜像分层 → 容器生命周期 → Dockerfile 与多阶段构建 → 数据卷与网络 → Compose；看完回 `ex01`（fetch 与 pull 的真实语义（p）核对 |
| 2 | 黑马程序员 · Git 全套教程<br><sub>黑马程序员</sub> | [BV1MU4y1Y7h5](https://www.bilibili.com/video/BV1MU4y1Y7h5/) | §4.1 分支策略选型 | 对象模型 → 分支本质 → merge/rebase → 冲突与 reflog 救援；配真实协作场景演示；看完回 `ex02`（提交 DAG 的 merge-base（）核对 |
| 3 | GeekHour · 一小时 Git 教程<br><sub>GeekHour</sub> | [BV1HM411377j](https://www.bilibili.com/video/BV1HM411377j/) | §4.1 分支策略选型 | 一小时建立全局图：三区、HEAD、常用命令的对应关系，适合先看这个再进细节；看完回 `ex03`（三方合并）核对 |
| 4 | 于仕琪 · Linux 常用命令与 Shell<br><sub>于仕琪</sub> | [BV1Uv4y127tU](https://www.bilibili.com/video/BV1Uv4y127tU/) | 全章 | 25 分钟过一遍 13 个基本命令与 Shell 脚本骨架，南方科大老师讲得干净；看完回 `ex04`（三方合并）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《鸟哥的 Linux 私房菜（第 4 版）》 |
| 2 | 《Pro Git（第 2 版）》Chacon & Straub |
| 3 | 《Docker 技术入门与实战（第 3 版）》杨保华 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
