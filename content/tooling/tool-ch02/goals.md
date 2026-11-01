# Linux 进程、管道与 Shell 脚本 — 学习目标

## 一、本章定位

本章是「工程工具」学科第二章，承接 tool-ch01（文件系统与权限）。第一章你理解了「一切皆文件」与
fd（文件描述符）是访问资源的统一句柄；本章把这条主线推进到**进程与进程间通信**：管道、重定向本质上
都是对 fd 表的重新排列；Shell 脚本则是把这些原语编排成可复用的工程资产。

- **先修**：tool-ch01（fd、权限、路径解析）—— 管道的读/写端、重定向的目标，本质都是 fd。
- **衔接**：tool-ch03（Git 对象模型）的「内容寻址」与本章「进程树」是两种不同层级的抽象；
  tool-ch05（Docker）的 namespace/cgroup 是对本章进程模型的再封装。
- **面试权重**：★★★★★ —— 进程（僵尸/孤儿）、信号（SIGTERM vs SIGKILL）、2>&1、管道、
  set -e 几乎是后端/SRE 面试的必考题，且极易追问到底层。

## 二、学习目标

学完本章，你应当能够：

1. **讲清 fork/exec 语义**：fork() 复制地址空间、exec() 替换映像；由此解释「为什么子进程改了
   变量不影响父进程」「bash script.sh 与 source script.sh 的区别」。
2. **画出并解释进程状态机**：R（运行）/S（可中断睡眠）/D（不可中断睡眠）/Z（僵尸）/T（停止），
   以及它们之间的转移条件。
3. **区分僵尸进程与孤儿进程**：谁产生、谁回收、不回收的后果（僵尸占 pid、孤儿被 init 收养）。
4. **列出常见信号的默认行为**：SIGTERM（可捕获、优雅终止）、SIGKILL（不可捕获、立即杀）、
   SIGINT（Ctrl-C）、SIGHUP（终端关闭/配置重载），并说明 SIGKILL/SIGSTOP 为何「不能被捕获」。
5. **把管道与重定向还原成 fd 表操作**：| 是创建一对 pipe fd 并重定向；2>&1 是「把 fd 2 复制
   到 fd 1 当前指向的目标」；顺序敏感（2>&1 >file 与 >file 2>&1 结果不同）。
6. **写出健壮的 Shell 脚本**：set -euo pipefail、$? 的取值时机、变量加引号、循环里的
   词拆分陷阱；理解 set -e 的例外（条件表达式内、命令列表里的非末位命令）。
7. **解释 xargs 与 find -exec 的差异**：\; 每文件一进程、+ 与 xargs 批量传参；
   含空格文件名必须用 -0/find -print0。
8. **讲清 cron 与 systemd 的取舍**：cron 环境极简（PATH 几乎为空），systemd 提供依赖、日志、
   重启策略；SSH 密钥登录的 challenge-response 流程与私钥权限 600 的硬约束。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写 5 个状态字母与 4 个核心信号的默认行为 | 习题 choice |
| 理解 | 能给一段脚本推断 2>&1 后的 fd 表 | 习题 output |
| 应用 | 能用 Python 模拟进程树/状态机/僵尸回收 | examples 实跑 |
| 分析 | 能定位「脚本手动能跑、cron 跑不了」的根因 | pitfalls 第 12~16 条 |
| 评价 | 能论证「为什么不该把 SIGKILL 当首选」 | interview 第 2 题 |

## 四、常见认知误区（先破后立）

1. **「kill PID 是杀进程」** —— kill 默认发 **SIGTERM（15）**，是「请优雅退出」的礼貌请求；
   真正「立即杀、不可拒绝」的是 SIGKILL（9），要 kill -9。把 SIGTERM 当成 SIGKILL 是新手最大误区。
2. **「僵尸进程很可怕」** —— 单个僵尸不占内存、不占 CPU，只**占一个 pid 槽**；只有父进程长期不
   wait 导致大量僵尸堆积（耗尽 pid 上限）才是事故。僵尸本身无法被 kill -9（它已经死了）。
3. **「管道是文件」** —— 管道是内核里一块**有限环形缓冲区**（Linux 默认 64KB），不是磁盘文件；
   它的两端是两个 fd，读端关闭时写端会收到 SIGPIPE。
4. **「set -e 能让脚本绝对安全」** —— set -e 有很多例外：条件里（if cmd）、&&/|| 链里、
   while 条件里的命令失败都不会触发退出。要管住管道必须用 set -o pipefail。

## 五、学习路径建议

1. 先读 concept/01-process-model.md，用 examples/ex01（进程树）与 ex03（僵尸孤儿）把
   fork/exec 与 wait 变成直觉。
2. 再读 concept/02-signals.md，结合 ex04（信号语义）理解「为什么 SIGKILL 不能捕获」。
3. 读 concept/03-pipe-redirection.md，用 ex05（fd 表）和 ex10（xargs vs find）把管道重定向
   还原成「fd 的复制与重定向」。
4. 最后读 concept/04-shell-scripting.md，把 ex07/ex08（$? 与 set -e）当检查表。
5. 做 exercises.json 的 coding 题（fork 模拟），自测 interview.json，再用 project.json 交付
   一个真实可用的守护脚本。

## 六、与 GitHub 顶级资源的对接

- jlevy/the-art-of-command-line（162k★）—— 命令行体系化进阶，与 concept/04 互补
- bregman-arie/devops-exercises（84k★）—— Linux/Shell 练习题集，覆盖进程与信号
- ohmyzsh/ohmyzsh（190k★）—— Shell 生产力框架（下一章工具链会用到）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 254,934 | 全章 | 运维与工程工具知识合集：Linux、网络、排障命令速查；本章先读与「进程是什么」「进程状态机」相关的部分 |
| 2 | [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190,274 | 全章 | Shell 生产力框架（工程效率的入门必装）；本章先读与「进程是什么」「进程状态机」相关的部分 |
| 3 | [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162,646 | 全章 | 命令行艺术：Linux 命令的体系化进阶指南；本章先读与「进程是什么」「进程状态机」相关的部分 |
| 4 | [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 86,127 | 全章 | DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖；本章先读与「进程是什么」「进程状态机」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Docker 实战（入门到大神）<br><sub>尚硅谷</sub> | [BV1gr4y1U7CY](https://www.bilibili.com/video/BV1gr4y1U7CY/) | 全章 | 主线：镜像分层 → 容器生命周期 → Dockerfile 与多阶段构建 → 数据卷与网络 → Compose；看完回 `ex01`（进程树）核对 |
| 2 | 于仕琪 · Linux 常用命令与 Shell<br><sub>于仕琪</sub> | [BV1Uv4y127tU](https://www.bilibili.com/video/BV1Uv4y127tU/) | 全章 | 25 分钟过一遍 13 个基本命令与 Shell 脚本骨架，南方科大老师讲得干净；看完回 `ex02`（进程状态机）核对 |
| 3 | 黑马测试 · Linux 课程（2 天）<br><sub>黑马测试</sub> | [BV1vk4y1r7cW](https://www.bilibili.com/video/BV1vk4y1r7cW/) | 全章 | 环境配置与 vim、进程与权限、常见运维操作；装环境卡住时看它；看完回 `ex03`（僵尸进程与孤儿进程的成因与回收）核对 |
| 4 | 黑马程序员 · Git 全套教程<br><sub>黑马程序员</sub> | [BV1MU4y1Y7h5](https://www.bilibili.com/video/BV1MU4y1Y7h5/) | 全章 | 对象模型 → 分支本质 → merge/rebase → 冲突与 reflog 救援；配真实协作场景演示；看完回 `ex04`（信号默认行为表与递送顺序）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《鸟哥的 Linux 私房菜（第 4 版）》 |
| 2 | 《Pro Git（第 2 版）》Chacon & Straub |
| 3 | 《Docker 技术入门与实战（第 3 版）》杨保华 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
