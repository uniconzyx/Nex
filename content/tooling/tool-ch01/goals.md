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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 254,934 | §3.1 | 讲「排障入口」时看分类里的「Sysadmin」一节：`df`/`du`/`lsof`/`ss` 这几个命令的定位分工，正好对应本章「先看哪一层」的顺序 |
| 2 | [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,274 | §4.1 | 讲「Shell 环境」时读 `lib/` 下的主题与补全脚本：`PATH`、别名、补全函数的加载顺序，决定了「为什么我的命令找不到」 |
| 3 | [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162,646 | §1.2 | 讲「文件与目录操作」时读 `README.md` 的「文件及数据处理」一节：`find`/`xargs`/`grep` 的组合用法给了可直接抄的一行命令，比 man 手册好上手 |
| 4 | [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 86,127 | §2.1 | 讲「权限位」时看 `topics/linux/` 的权限练习：`chmod 755` 与 `chmod u+x` 的等价关系、`umask` 如何影响新建文件，题后有答案可自测 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Docker 实战（入门到大神）<br><sub>尚硅谷</sub> | [BV1gr4y1U7CY](https://www.bilibili.com/video/BV1gr4y1U7CY/) | 全章 | 主线：镜像分层 → 容器生命周期 → Dockerfile 与多阶段构建 → 数据卷与网络 → Compose；看完回 `ex01`（逐字段拆解 `ls -l` 的一行）核对 |
| 2 | 于仕琪 · Linux 常用命令与 Shell<br><sub>于仕琪</sub> | [BV1Uv4y127tU](https://www.bilibili.com/video/BV1Uv4y127tU/) | 全章 | 25 分钟过一遍 13 个基本命令与 Shell 脚本骨架，南方科大老师讲得干净；看完回 `ex02`（rwx 符号串与八进制互转（含 setu）核对 |
| 3 | 黑马测试 · Linux 课程（2 天）<br><sub>黑马测试</sub> | [BV1vk4y1r7cW](https://www.bilibili.com/video/BV1vk4y1r7cW/) | 全章 | 环境配置与 vim、进程与权限、常见运维操作；装环境卡住时看它；看完回 `ex03`（umask 掩码运算）核对 |
| 4 | 黑马程序员 · Git 全套教程<br><sub>黑马程序员</sub> | [BV1MU4y1Y7h5](https://www.bilibili.com/video/BV1MU4y1Y7h5/) | 全章 | 对象模型 → 分支本质 → merge/rebase → 冲突与 reflog 救援；配真实协作场景演示；看完回 `ex04`（硬链接本质验证）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《鸟哥的 Linux 私房菜（第 4 版）》 |
| 2 | 《Pro Git（第 2 版）》Chacon & Straub |
| 3 | 《Docker 技术入门与实战（第 3 版）》杨保华 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
