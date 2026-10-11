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
