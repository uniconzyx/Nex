# Linux 基础：文件系统与权限 — 学习目标

## 一、本章定位

本章是「工程工具」学科的第一章，也是整个后端/运维能力的地基。Linux 不是一门"要背命令"的课，而是一套**设计哲学 + 抽象的元模型**：理解「一切皆文件」「目录是名称到 inode 的映射」「权限是对 inode 的操作许可」这三条，命令只是表层语法。

- **先修**：无（本章是工具链起点）。若已具备 C 语言指针与内存概念（`content/clang/clang-u01`），对 inode/链接的理解会顺畅很多。
- **衔接**：`tool-ch02`（进程、管道与 Shell 脚本）会大量使用本章的文件描述符与权限概念；`tool-ch03`（Git 对象模型）中「内容寻址」与本章的「inode 编号」是同一种思想。
- **面试权重**：★★★★☆ —— 出现频次极高（"软链接和硬链接区别""`chmod 777` 有什么风险""`rm` 删除的文件能恢复吗"），且是**区分"用过 Linux"和"懂 Linux"的分水岭**。

## 二、学习目标

学完本章，你应当能够：

1. **说出 FHS 各目录的职责边界**，并解释为什么 `/bin` 与 `/usr/bin`、`/lib` 与 `/usr/lib` 在现代发行版里被合并（`/usr` merge，一个真实的工程演进）。
2. **解释 inode 的本质**：它存什么（元数据 + 数据块指针）、不存什么（文件名），以及为什么**文件名不属于 inode**——由此自然推出硬链接、`rm` 的语义、目录项与 `..` 的实现。
3. **在 rwx 两种语义间自由切换**：对普通文件，`r/w/x` 是"读/写/执行"；对目录，`r` 是"可列名"、`w` 是"可增删目录项"、`x` 是"可穿越 / 可访问其中的 inode"。→ 能解释「有读权限但没执行权限，为什么 `ls` 目录能列名却 `cat` 不进去」。
4. **掌握权限的计算体系**：八进制表示、`umask` 掩码运算（默认文件 `666 & ~umask`、目录 `777 & ~umask`）、`chmod` 的符号法与数字法、`chown/chgrp` 与权限的配合。
5. **讲清三个特殊权限的用途与风险**：setuid（`passwd` 为什么能改 `/etc/shadow`）、setgid（目录下新建文件继承组）、sticky（`/tmp` 为什么别人删不掉你的文件）。
6. **区分硬链接与软链接的本质**：目录项 vs 独立 inode；链接计数；能否跨文件系统；能否指向目录；悬垂链接如何产生与如何排查。
7. **用文本三剑客解决真实问题**：`grep` 的模式与 `-E/-v/-c/-n/-r` 组合、`sed` 的模式空间与地址定址、`awk` 的「记录—字段」模型与 `BEGIN/END`，并能用管道把它们串起来。
8. **理解「为什么不解析 `ls` 输出」**：`ls` 是给人看的，解析应使用 `find -print0` + `xargs -0` 或 `stat`，因为文件名可含空格与换行。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写 FHS 主要目录职责与权限八进制对照表 | 习题中的 choice 题 |
| 理解 | 能解释「目录的 x 权限」与「硬链接计数」 | 习题中的 output 题（给权限位推断行为） |
| 应用 | 能用 `find` + `xargs` 批量处理文件；能用 `awk` 做字段统计 | examples 中的 grep/sed/awk/find 示例、coding 题 |
| 分析 | 能诊断「Permission denied」属于哪一类权限缺失；能判断某一链接是硬链接还是软链接 | 习题中的 fix_error 题、pitfalls 第 7~10 条 |
| 评价 | 能说明 `chmod 777` 与 `chmod -R 777 /` 的危害链条；能论证为什么 `umask 022` 是合理的默认值 | interview 第 3、4 题 |

## 四、常见认知误区（先破后立）

1. **「Linux 的文件没有扩展名」** —— 准确说法是**内核不依赖扩展名判断类型**，`file` 命令读的是**魔数（magic number）**。但用户态的很多工具（编译器、解释器）仍按约定后缀工作。
2. **「`rm` 把文件删了」** —— `rm` 只是删掉**目录项**（把名字与 inode 解绑）并把 inode 的链接计数减一；计数归零且无进程打开时才真正释放。所以「误删后进程还在读」是能救回数据的真实场景。
3. **「软链接比硬链接高级」** —— 两者服务于不同目的。硬链接是"同一个文件的多个名字"，软链接是"一个存着路径的小文件"。**软链接可指向目录与跨文件系统，但会悬垂**；硬链接反之。
4. **「`777` 就是全部权限、最省事」** —— `777` 对目录意味着任何人都能删你的文件（除非 sticky 位），对可执行文件意味着任何人都能替换它。这是**提权链条的第一环**。

## 五、学习路径建议

1. 先读 `concept/01-fhs-and-inode.md`，建立「inode 才是文件本体」的心智模型。
2. 再读 `concept/02-permissions.md`，**动手把每个权限位都改一遍并观察 `ls -l` / `stat` 的变化**（本章 examples 已提供可运行脚本）。
3. 读 `concept/03-hardlink-symlink.md`，用 `stat` 对比 `Inode` 与 `Links` 两个字段，这是理解两者差异最快的方式。
4. 最后读 `concept/04-text-toolchain.md`，把 `pitfalls.md` 当检查表，用 `examples/` 里的脚本改写练习。
5. 做 `exercises.json` 的 coding 题（实践导向），再自测 `interview.json`。

## 六、与 GitHub 顶级资源的对接

按项目约定，本章学习资源取自 GitHub star 最高的相关仓库（实时抓取，见 `_manifest.json` 的 `github_resources`）：

- `trimstray/the-book-of-secret-knowledge`（248k★）—— 运维与排障命令合集，本章的 `find/xargs` 实战可在此深挖
- `jlevy/the-art-of-command-line`（162k★）—— 命令行体系化进阶，与 `concept/04` 高度互补
- `ohmyzsh/ohmyzsh`（190k★）—— Shell 生产力框架（下一章 tool-ch02 会用到）

> 建议先在本地把本章 examples 全部跑一遍（每个脚本都会真实创建文件、改权限、建硬链接），再去看这些仓库，体感会完全不同。


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
