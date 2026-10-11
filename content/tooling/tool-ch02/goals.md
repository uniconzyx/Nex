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
