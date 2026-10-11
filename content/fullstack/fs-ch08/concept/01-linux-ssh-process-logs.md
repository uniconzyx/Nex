# fs-ch08 · 一、Linux 服务器：SSH、进程管理与日志

## 一、SSH 与免密登录（含端口转发）

SSH（Secure Shell，IANA 分配的默认端口 22）在不可信网络上提供加密的远程登录与文件传输。认证方式有密码与公钥两类；**免密登录**指的是公钥（publickey）认证：客户端持有私钥，服务端在 `~/.ssh/authorized_keys` 里持有对应公钥。基本流程：

```
ssh-keygen -t ed25519 -C "deploy@ci"        # 生成密钥对（私钥留在本机，永不外传）
ssh-copy-id -i ~/.ssh/id_ed25519.pub deploy@10.0.0.11
```

`~/.ssh/config` 把连接参数固化下来，供 `ssh/scp/rsync/git` 共用：

```
Host prod-web
  HostName 10.0.0.11
  User deploy
  IdentityFile ~/.ssh/id_ed25519_prod
  ServerAliveInterval 30
  LocalForward 5433 db.internal:5432      # 本地端口转发：本机 5433 -> 跳板机可达的 db
```

三类端口转发：`-L`（本地转发，把本地端口映射到远端网络）、`-R`（远程转发，把远端端口映射回本地）、`-D`（动态转发，起一个 SOCKS5 代理）。本章 ex12 用 Node 解析 SSH 配置并审计四件事：是否有 `IdentityFile`（免密）、是否 `User root`、是否 `PasswordAuthentication yes`、是否有端口转发。

### 🧑‍💻 程序员视角
- 落地清单：① 用 `ed25519`（比 RSA 短且快），② `ssh-agent` 缓存私钥口令，③ `ControlMaster auto` + `ControlPersist` 复用一条 TCP 连接，让 `scp`/`git` 等连续操作不再重复握手，④ CI 里私钥放 `secrets` 并以 `600` 权限落盘。
- 事故画像：为了让脚本不报 `Host key verification failed`，把 `StrictHostKeyChecking no` 写进生产配置——这等于关掉中间人防护，攻击者可任意伪装目标主机。正确做法是把目标主机公钥预置进 `known_hosts`，而不是关闭校验。
- 排查顺序：连不上先 `ssh -vvv`，按输出定位到「DNS → TCP 22 可达 → 密钥交换 → 认证 → 授权」哪一段；`Permission denied (publickey)` 通常是服务端 `authorized_keys` 权限过松（须 600）或属主不对。
- 安全基线：禁止 root 直连（`PermitRootLogin no`）、禁密码认证（`PasswordAuthentication no`）、改默认端口只是降低扫描噪音而非安全措施，真正的边界是密钥与最小权限。

### 🎓 博士生视角
- 公钥认证不是「用公钥解密」，而是**挑战-响应签名**：客户端证明自己持有私钥，服务端用公钥验签；私钥永不存在于网络上。这与「对称加密传密码」有本质区别，也解释了为什么服务端泄露 `authorized_keys` 不会导致私钥泄露。
- 会话密钥由密钥交换协议（如 curve25519-sha256 或 ecdh-sha2-nistp256）协商，具备**前向保密**：即使长期私钥日后泄露，也无法解密历史会话流量。这是 KEX 与认证分离（先协商会话密钥、再用长期密钥认证）带来的性质。
- 端口转发复用的是同一条 SSH 通道内的多路复用连接（channel），因此「隧道」的带宽与延迟都受 SSH 通道限制；`-D` 建立的 SOCKS 代理是应用层转发，与四层隧道在语义上不同层。
- 交互式登录分配 PTY，非交互式 `ssh host cmd` 不分配 PTY；后者退出时若仍有后台子进程，父 shell 收 SIGHUP 会让子进程被挂断——这就是远程跑长任务必须用 `nohup/setsid/systemd-run` 的机制来源。

### 📚 考研者视角
- **408 网络层考点**：SSH 属**应用层**协议、基于 **TCP**、默认端口 **22**；与 telnet（明文）、FTPS 的关系与替代动机（机密性与完整性）。选择题常把 SSH 塞进「传输层协议」作为干扰项。
- **加密与认证口径**：对称加密（AES）用于数据保密，非对称加密/签名用于身份认证与密钥交换，哈希（HMAC/SHA）用于完整性。答题时不要写成「SSH 用非对称加密传输数据」。
- **易混点**：`ssh-keygen` 生成的是密钥对（`id_ed25519` 私钥 + `id_ed25519.pub` 公钥），公钥进服务端 `authorized_keys`，私钥留在客户端；拷贝方向写反是高频失分点。

## 二、进程管理：systemd / pm2 / supervisor

三个常见选择的定位：

| 方案 | 层级 | 适用场景 | 关键能力 |
|---|---|---|---|
| **systemd** | 操作系统 init（PID 1） | 裸机/虚机上的长期服务 | unit 依赖与启动顺序、`Restart` 策略、cgroup 资源限制、journald 日志集成、开机自启 |
| **pm2** | Node 生态进程管理器 | 裸机上的 Node 应用（多实例） | cluster 模式利用多核、`ecosystem.config.js`、`pm2 startup/save`、内置日志轮转 |
| **supervisor** | 通用进程管理器 | 需要统一托管多个异构小进程 | 纯 Python、配置简单、`autorestart`、`supervisorctl` 管理 |

本章 ex13 用一个真实 unit 做静态审计与重启退避模拟：`Restart=on-failure` + `RestartSec=2` + `StartLimitBurst=3` 时，进程每 10s 崩一次，systemd 依次在 t=0/12/24 启动成功，第 4 次启动被 `start-limit-hit` 拒绝并进入 `failed` 状态。

```
[Unit]
Description=orders-api
After=network-online.target

[Service]
User=app
ExecStart=/usr/bin/node /srv/orders/dist/server.js
Restart=on-failure
RestartSec=2
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
```

### 🧑‍💻 程序员视角
- 选择判据：裸机上的单进程服务优先 **systemd**（它已经在系统里，且能顺手拿到 cgroup 限额与 journald 日志）；裸机上要跑多核 Node 集群再考虑 **pm2**（它的 cluster 模式替你 fork 多份）；**容器内一律不要套进程管理器**，直接前台运行单进程，重启交给编排层。
- 为什么容器内套 pm2 会出事：pm2 会成为 PID 1 并 fork 出真正的 node 进程，`docker stop` 发的 SIGTERM 到达 pm2 而非工作进程；pm2 若未正确转发，优雅停机失效，10 秒后被 SIGKILL。信号链多一层，故障面就多一层。
- 排查顺序：`systemctl status <unit>` 看 `Active` 与 `Main PID` 与最近一行日志 → `journalctl -u <unit> -n 200` 看详情 → 看退出码（`137` = 128+9 被 SIGKILL，常为 OOM；`143` = 128+15 收到 SIGTERM）→ `systemctl show <unit> -p Restart,RestartUSec` 确认策略生效。
- 事故画像：把 `Restart=always` 用在「启动即崩」的服务上，systemd 会疯狂重启并写满日志；正确做法是 `Restart=on-failure` 配 `RestartSec` 退避 + `StartLimitBurst`/`StartLimitIntervalSec` 熔断（ex13 的模拟正是这条熔断线）。

### 🎓 博士生视角
- 进程语义层面：systemd 作为 PID 1 兼「孤儿进程收养者」，是所有被 `daemonize` 掉双 fork 的守护进程的最终父进程；`Restart` 的本质是「主进程退出 → 拉起一个新的」这一状态机，而 `RestartSec` 是这个状态机的保持时间。
- 容器与 init 的根本差异在于 **PID 1 的信号语义**：Linux 对 PID 1 忽略未注册 handler 的信号（这是为了保护 init 不被误杀），且 PID 1 必须负责 `wait()` 回收僵尸。应用进程通常两条都不满足，于是需要 `tini`/`dumb-init` 这类极简 init 作为 PID 1 转发信号与回收子进程。
- 资源限制落在 cgroup 上：内存上限被触及时由内核 OOM killer 杀进程，表现为主进程收到 SIGKILL（退出码 137），应用自身的错误处理完全无机会执行——所以「服务莫名被杀」要先看 cgroup 内存而不是代码。
- systemd 的 `After=` 只描述**启动顺序**，`Requires=`/`Wants=` 描述**依赖强度**，两者正交；把两者混为一谈，会写出「有顺序但没依赖」或「有依赖却没顺序」的配置。

### 📚 考研者视角
- **408 操作系统考点**：进程状态转换（就绪/运行/阻塞/创建/终止）、PCB 的组成、`fork`/`exec` 的区别、父进程与子进程关系、**僵尸进程**（已终止但 PCB 未回收）与**孤儿进程**（父先终止，被 init 收养）、信号机制与进程调度。
- **口径**：`SIGKILL`（9）不可捕获、不可忽略、不可阻塞；`SIGTERM`（15）可以被捕获或忽略，因此「优雅停机」在 SIGTERM 上做、SIGKILL 是最后手段。答题时把「退出码 137」换算成 `128+9` 是加分的推导。
- **易混点**：僵尸进程不占 CPU 但占 PID 与 PCB；大量僵尸会耗尽 PID 表。父进程调用 `wait()/waitpid()` 才是回收动作，只 `kill` 子进程不会消除僵尸。
- **面试考点**：为什么容器里需要 init 进程（信号转发 + 僵尸回收）；`systemd` 与 `supervisord` 的区别（init 层级与 POSIX init 语义 vs 普通用户态进程管理器）。

## 三、日志：journalctl 与 logrotate

Linux 上的日志有两条主线：**systemd 的 journald** 把各服务日志统一收进二进制 journal，用 `journalctl` 查询；**logrotate** 则负责把已有的文本日志按大小/时间轮转、压缩与清理。两者配合的典型形态是：应用写文本日志 → logrotate 轮转 → 需要集中检索时再走日志采集器送到聚合后端。

```
journalctl -u orders-api --since "30 min ago" -p err --no-pager
journalctl -b -1 -p warning            # 上一次启动
journalctl --disk-usage                # 当前占用
journalctl --vacuum-size=500M          # 只保留 500M
```

```
/var/log/orders/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 app app
    sharedscripts
    postrotate
        systemctl kill -s USR1 orders-api     # 通知进程重开日志文件
    endscript
}
```

### 🧑‍💻 程序员视角
- 排查顺序：① `journalctl -u <unit> --since "10 min ago" -p err` 拿到错误窗口；② 用 `--no-pager` 便于管道给 `grep`；③ 结构化日志（JSON 单行）比多行堆栈更利于聚合检索；④ 生产上把日志送 stdout，由运行时/采集器决定落盘与转发，容器内不要自建日志文件（容器可写层随容器销毁）。
- 事故画像：磁盘被日志打满导致服务写失败（`No space left on device`），`df -h` 显示 `/var` 100%。先 `du -sh /var/log/*` 定位，再 `journalctl --vacuum-size=500M` 与修 logrotate 策略；**不要**直接 `rm` 正在写的日志——进程仍持有该 inode，空间不会释放（`lsof +L1` 可见 `(deleted)`）。
- logrotate 的两个坑：一是 `create` 模式（mv 旧文件 + 新建同名文件）后进程仍写旧 inode，必须配 `postrotate` 发信号让进程重开文件（如 nginx 的 `USR1`）；二是 `copytruncate` 不需要信号，但拷贝与截断之间存在窗口，高写入量下会丢日志，且对大文件代价高。
- 级别与采样：日志级别（emerg/alert/crit/err/warning/notice/info/debug）要与告警策略对齐；高频路径打 `debug` 会让磁盘与采集成本翻倍，应改成结构化指标（计数器）而不是日志。

### 🎓 博士生视角
- 二进制 journal 的设计动机是**可索引 + 完整性**：字段化条目（unit、pid、优先级、boot id）可以按维度检索而不必正则扫文本，代价是不能再直接 `grep` 文件，必须经由 journalctl 这一查询层。这是「结构化 vs 可移植」的经典取舍。
- logrotate 的根本困难是 **文件描述符与 inode 的解耦**：进程持有的是打开的 fd（指向 inode），`mv` 只改目录项；因此 `create` 模式必然要求「通知进程重新 open」，否则新文件空、旧文件持续增长。这与文件系统章节里「目录项 → inode → 数据块」的三层结构完全同源，也是「删除文件而磁盘不释放」的同一机制。
- 日志系统的容量规划是一个**写入速率 × 保留窗口**的估算问题：保留 14 天、每天 2GB，就需要 ≥28GB 可用空间再加上压缩率折扣；未做这个估算的系统在业务放量时必然撞上磁盘上限。
- 可观测性三支柱的分工：metrics 便宜且可聚合（适合告警），logs 信息密度高但成本随量线性增长（适合定位），traces 建立跨服务因果（适合分布式延迟归因）。把「统计需求」错误地压在日志上，是成本失控的常见根因。

### 📚 考研者视角
- **日志管理本身不在 408 考纲内**，但相关考纲概念非常密集：**文件物理结构**（索引节点 inode、目录项、硬链接与打开计数）、**文件系统空间管理**（空闲块管理、磁盘容量）、**缓冲与 I/O**（页缓存、延迟写）。本章的 logrotate 讨论正好可以反向印证这些考点。
- **常考口径**：一个文件被进程打开后即使 `unlink`，只要仍有打开的 fd，数据块就不释放（`i_nlink=0` 但打开计数 > 0）；`i_nlink` 管删除、打开计数管释放，这是两个不同字段——错误合并是高频失分点。
- **易混点**：`df` 与 `du` 结果不一致，典型原因就是「已删除但仍被占用的文件」；这也解释了为什么「删除大日志」后磁盘没变化。
- **面试考点**：日志轮转为什么需要信号（回答要点：fd 指向 inode，重命名不改变 fd，因此必须让进程重新打开文件）；容器为什么推荐把日志写 stdout（回答要点：由运行时统一收集，避免容器可写层膨胀与随容器销毁丢日志）。
