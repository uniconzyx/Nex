# 信号：递送、默认行为与不可捕获信号

> 本节目标：信号是 UNIX 的「异步中断机制」，是进程间（含内核向进程）通知的主要手段。理解信号的默认行为表，是排障与写健壮守护进程的基础。
> 每个主题都按 **🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者** 三视角解析。

---

## 一、信号的递送模型与「默认行为」

信号是内核向进程发送的**软中断**：不携带复杂数据，只表达「某类事件发生」。每个信号有一个**默认处置（disposition）**：

| 默认行为 | 含义 | 代表信号 |
|---|---|---|
| **Term** | 终止进程 | SIGTERM(15)、SIGHUP(1)、SIGINT(2) |
| **Core** | 终止并产生 core dump | SIGSEGV(11)、SIGABRT(6)、SIGQUIT(3) |
| **Ign**  | 忽略 | SIGCHLD(17)、SIGURG、SIGWINCH |
| **Stop** | 暂停（作业控制） | SIGSTOP(19)、SIGTSTP(20) |
| **Cont** | 继续（从 Stop 恢复） | SIGCONT(18) |

进程可以**改变**某个信号的处置：signal()/sigaction() 注册自定义 handler，或 SIG_IGN 显式忽略，或 SIG_DFL 恢复默认。**但有两个信号永远不可被捕获、阻塞或忽略：SIGKILL(9) 与 SIGSTOP(19)。**

```
信号递送（简化）
  事件(内核/其他进程) ──► 置位 pending 位图 ──► 内核在「从内核态返回用户态」的时机检查
    │                                                  │
    │ 若被阻塞(blocked) ──► 保持 pending，解阻塞后再递送
    ▼
  按 disposition 处理：handler / 默认(Term|Core|Ign|Stop|Cont)
```


### 🧑‍💻 程序员视角
- **优雅退出靠 SIGTERM + 自定义 handler**：服务进程应捕获 SIGTERM，先 flush 缓冲区、关连接、删 pidfile，再 _exit()。这样 systemctl stop/docker stop 默认发 SIGTERM，给你清理窗口（默认超时 90s/10s 后转 SIGKILL）。
- **永远不要用 SIGKILL 做常规关停**：它跳过了所有清理，DB 可能留下损坏的 WAL、临时文件泄漏、锁未释放。只在「进程已卡死、SIGTERM 无响应」时用 kill -9。
- **忽略 SIGPIPE**：写管道时读端已关闭会收到 SIGPIPE 默认终止进程——网络服务常 signal(SIGPIPE, SIG_IGN) 改用 write 返回 EPIPE 自行处理，避免被远端断连打死。
- **trap 在脚本里等价于 sigaction**：trap 'cleanup' EXIT TERM INT 让脚本退出/被杀时清理临时文件，是健壮脚本标配。
### 🎓 博士生视角
- **pending + blocked 位图模型**：内核为每个进程维护 pending（待递送）与 blocked（屏蔽）两张位图。信号**不会排队**（标准信号在 pending 里只记「有/无」，同号多次发送合并为一次），实时信号（SIGRTMIN+）才保证排队。
- **为什么 SIGKILL/SIGSTOP 不可捕获**：它们的语义是「内核/管理员的最终控制权」——若允许进程忽略 SIGKILL，一个失控/死锁进程就永远无法被终止，破坏操作系统的基本不变量。这是**安全边界**，不是实现疏漏。
- **递送时机**：信号不会在任意指令中途插入，而是在「内核即将返回用户态」的检查点批量处理 pending 中未被阻塞的信号；因此 handler 不会打断一条不可中断的指令（但可能打断系统调用，使其返回 EINTR）。
- **handler 重入与 sa_mask**：进入 handler 时默认会把该信号加入 blocked 防止重入；复杂 handler 应谨慎访问全局状态，最好只做「写 volatile 标志 / 设 self-pipe」这类异步信号安全操作。
### 📚 考研者视角
- **408 / 操作系统 · 中断与异常**：信号常类比「软中断」，答题要点是「异步、不携带大数据、由内核在返回用户态时递送」。与硬件中断的区别：信号是进程级、软件触发、可屏蔽可捕获（除 SIGKILL/STOP）。
- **必背默认行为表**：Term 组（HUP/INT/TERM/ALRM）、Core 组（SEGV/ABRT/QUIT/ILL/FPE）、Ign 组（CHLD/URG/WINCH）、Stop 组（STOP/TSTP）、Cont（CONT）。面试常直接问「SIGSEGV 默认会怎样」→ Core dump。
- **易错口径**：「kill -9 能杀 D 状态进程吗」→ 不能，D 状态连 SIGKILL 都等底层 IO 返回才生效；「kill 默认信号」→ 15 (SIGTERM) 不是 9。
- **标准问法**：「如何优雅停止一个服务」「为什么 SIGKILL 危险」「SIGCHLD 有什么用」——SIGCHLD 在子进程状态变化时发给父进程，是父进程 wait 回收僵尸的触发信号。
## 二、四个核心信号：SIGTERM / SIGKILL / SIGINT / SIGHUP

面试与排障最高频的四个：

- **SIGINT(2)**：Ctrl-C 产生，发给**当前前台进程组**，默认 Term。用于「用户主动中断」。
- **SIGTERM(15)**：kill 默认，语义是「请优雅退出」，可被捕获/忽略，给人留清理窗口。
- **SIGKILL(9)**：立即终止，不可捕获/阻塞/忽略，最后手段。
- **SIGHUP(1)**：原始语义是「控制终端挂断」；现代复用为「**配置重载**」（daemon 收到后重读配置文件，如 nginx/kill -HUP）。

```
典型递送场景
Ctrl-C         ──► SIGINT  ──► 前台进程组（默认 Term）
kill <pid>     ──► SIGTERM ──► 目标进程（可优雅退出）
kill -9 <pid>  ──► SIGKILL  ──► 内核直接回收（无清理）
终端关闭        ──► SIGHUP   ──► 会话进程组（默认 Term；daemon 复用于 reload）
```


### 🧑‍💻 程序员视角
- **守护进程用 SIGHUP 做热重载**：nginx -s reload 本质发 SIGHUP 让 master 重读配置、平滑起新 worker、停旧 worker，**不丢连接**。比重启进程优雅得多。
- **kill -INT/kill -TERM 在容器停止链里**：docker stop 先 SIGTERM、等待 stopTimeout（默认 10s）再 SIGKILL；应用必须处理 SIGTERM 否则会被强制杀。
- **前台进程组**：一个管道 a | b 里 Ctrl-C 会**同时**发给 a 和 b（同属一个前台进程组），这正是作业控制的设计——你不能只终止一半。
- **nohup 的原理**：把 SIGHUP 置为忽略，使进程在终端关闭（发 SIGHUP）时不被终止，并把 stdout/stderr 重定向到 nohup.out。
### 🎓 博士生视角
- **进程组与会话**：每个进程属一个**进程组（PGID）**，前台作业占一个进程组；Ctrl-C 产生的 SIGINT 发给**整个前台进程组**（kill(-pgid, SIGINT) 负 pid 表示进程组），所以管道两端一起收到。
- **SIGHUP 的语义迁移**：早期 modem 挂断使终端文件描述符失效，内核发 SIGHUP 告诉进程「你的控制终端没了」；daemon 脱离终端后复用它表达「重新初始化」——同一信号承载两种语境，靠进程是否关联终端区分。
- **signal 与 sigaction 的差异**：signal() 在不同 UNIX 上 handler 执行后是否自动恢复默认不一（不可移植）；现代一律用 sigaction() 显式指定 sa_mask/sa_flags（如 SA_RESTART 让被中断的系统调用自动重启）。
- **信号与 wait 的协作**：子进程退出发 SIGCHLD 给父；父在 handler 里 waitpid(-1, ..., WNOHANG) 循环回收，避免僵尸——这是异步安全的回收范式（handler 内只调用 async-signal-safe 函数）。
### 📚 考研者视角
- **易错口径**：「SIGINT 和 SIGTERM 的区别」——前者是用户交互中断（Ctrl-C，发给前台组），后者是管理员/进程的终止请求（可捕获、给清理窗口）；两者都可被捕获，但语义场景不同。
- **「为什么 SIGKILL 不能捕获」是标准追问**：答「它是操作系统的最终控制权，保证任何失控进程都可被终止；若可捕获则系统失去兜底」。
- **SIGHUP 的双重用途**：答题时要能说出「原始=终端挂断、现代守护进程=配置重载（如 nginx/sshd）」两种语义。
- **进程组/会话与 SIGHUP 的关系**：终端关闭时内核向会话首进程的控制进程组发 SIGHUP，这是「关终端后台进程被杀」的根因，也是 nohup/setsid/disown 要解决的问题（见 pitfalls 第 10 条）。
