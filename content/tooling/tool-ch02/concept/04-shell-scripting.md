# Shell 脚本工程化：变量、退出码与守护

> 本节目标：把前几节的进程/信号/fd 原语，编排成**可维护、可排障、可上线**的 Shell 脚本。重点在「为什么 set -euo pipefail 是底线」「$? 何时取值」「cron/systemd/SSH 的工程取舍」。
> 每个主题都按 **🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者** 三视角解析。

---

## 一、变量、条件、循环、$? 与 set -euo pipefail

Shell 是**解释执行的命令语言**，不是通用编程语言。几个最容易翻车的点：

1. **变量展开与引号**：$VAR 未加引号会经历词拆分与 globbing；"$VAR" 才是「一个整体」。 "$@" 保留每个参数边界（与 "$*" 拼成单串不同）。
2. **$? 的取值时机**：它保存**上一条命令**的退出码，任何命令（哪怕是 echo $? 本身）都会覆盖它——要保存须 rc=$? 紧接在目标命令后。
3. **set -e 的例外**：条件（if/while）、&&/|| 链中非末位命令失败**不触发退出**。
4. **set -o pipefail**：让管道整体退出码 = 第一个非零退出码（而非末位命令）。

```
健壮脚本头（行业底线）
#!/usr/bin/env bash
set -euo pipefail        # e:出错即停  u:未定义变量即错  o pipefail:管道任一段失败则失败
IFS=$'\n\t'            # 收紧词拆分分隔符（仅换行/tab）
```


### 🧑‍💻 程序员视角
- **set -u 防未定义变量**：rm -rf "$DIR/" 若 DIR 未设，会退化成 rm -rf /——set -u 让这类错在赋空前就崩溃，而不是酿成删根事故（配合 set -e 立刻停）。
- **$? 必须立刻存**：somecmd; echo "rc=$?" 之后 $? 已变成 echo 的码；正确是 somecmd; rc=$?; echo "rc=$rc"。
- **${PIPESTATUS[@]} 看清管道每段**：cmd1 | cmd2; echo ${PIPESTATUS[*]} 打印每段退出码，调试管道必备。
- **函数返回用 return N、脚本退出用 exit N**；退出码 0=成功，非 0 表失败（惯例：1=通用错，2=用法错，>128 表被信号杀）。
- **[[ ]] 比 [ 更安全**：[[ -f "$f" ]] 内部不做词拆分、支持 &&/||/正则 =~，是 Bash 的推荐条件写法。
### 🎓 博士生视角
- **set -e 的语义边界（形式化）**：shell 规范规定「命令的退出导致脚本退出」只在命令处于「被等待且其状态未被显式测试」时成立；出现在 if/while/until 条件、&&/|| 中（除最右）、! 之后的命令，其失败是被「预期用于决策」的，不触发退出。这正是 set -e 看似「失灵」的精确边界。
- **$? 为何只存一个码**：shell 每次执行一条流水线后把其退出状态写入一个**单槽变量** $?，下一条命令执行即覆盖——所以它本质是个「最近状态寄存器」，天然只保留最后一条；管道则是把多段状态汇成单一值（默认取末段，pipefail 取首失败）。
- **变量展开的两阶段**：$VAR 展开发生在「参数展开」阶段，之后才做词拆分与路径展开——加双引号等于「跳过词拆分与 globbing 这两步」。这是「引号改变语义」的底层原因。
- **"$@" vs "$*"**：$@ 展开为 N 个独立词（保留原参数边界，是转发参数的正确写法），$* 展开为单个串——前者在参数含空格时不会碎裂。
### 📚 考研者视角
- **易错口径**：「set -e 为什么拦不住 a | b 里 a 失败」→ 默认 $? 取管道末段，需 pipefail；「$? 取的是哪条命令」→ 紧邻的上一条。
- **标准问法**：「写一个安全删除目录的脚本头」→ set -euo pipefail + 检查变量已定义 + rm -rf "$DIR" 加引号；「[ 与 [[ 区别」→ [ 是外部/内建命令、受词拆分影响，[[ 是 bash 关键字、更安全。
- **退出码约定（常识）**：0 成功、1 通用错误、2 用法/语法错、126 不可执行、127 命令未找到、128+N 被信号 N 杀——排障时 echo $? 的返回值能直接定位原因。
## 二、环境变量/PATH、cron、systemd 与 SSH 密钥登录

脚本要「上线」就离不开这三组工程原语：

- **环境变量与 PATH**：子进程 fork 继承父的环境副本；export 仅影响之后的子进程，不回传父 shell。命令查找沿 PATH 从左到右第一个匹配。
- **cron**：环境变量极简（PATH 常为 /usr/bin:/bin，无交互 shell 的 PATH/HOME/LANG），且**非交互、非登录**。脚本在 cron 里找不到命令是头号坑。
- **systemd**：以 unit 托管服务，提供 Restart=/After=/WantedBy= 依赖、journald 日志、KillSignal= 控制终止信号（默认 SIGTERM）。
- **SSH 密钥登录**：公钥放 ~/.ssh/authorized_keys，私钥本地 chmod 600；登录时服务端发 challenge、客户端用私钥签名、服务端用公钥验签（challenge-response），全程私钥不出本机。

```
SSH 公钥登录挑战-响应（简化）
  Client                               Server
    │                                    │ 持有 authorized_keys 里的公钥
    │  ←── 发送随机 challenge ────       │
    │  用私钥对 challenge 签名           │
    │  ──── 发送签名 ──►                 │ 用公钥验证签名
    │                                    │ 验证通过 → 允许登录（私钥从未离开客户端）
```


### 🧑‍💻 程序员视角
- **cron 脚本开头补 PATH**：export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin，或命令一律写绝对路径；不要依赖 ~/.bashrc（cron 不加载）。
- **systemd 优雅停止**：写 unit 时设 KillSignal=SIGTERM + TimeoutStopSec=30，让应用有清理窗口；别用 SIGKILL 粗暴停止 DB。
- **SSH 私钥权限 600 是硬约束**：权限太宽 ssh 直接拒 UNPROTECTED PRIVATE KEY FILE；服务端关 PasswordAuthentication 防暴力。
- **环境变量别塞密码**：敏感配置用文件 + chmod 600 或密钥管理（Vault/KMS），不要 export DB_PASS=xxx 留在进程环境里被 ps/coredump 泄露。
- **ssh -o StrictHostKeyChecking**：首次连接把主机指纹写 known_hosts 防中间人；自动化场景用 UserKnownHostsFile 托管指纹。
### 🎓 博士生视角
- **环境继承的单向性（形式化）**：fork 复制环境块（environ），exec 保留之；export 仅修改当前进程的 environ，新 fork 的子进程才看得到——这是「变量不回传父 shell」的精确原因（进程树有向、单向向下）。
- **cron 的 session 缺失**：cron 启动的任务是「无控制终端、无登录 shell」的会话，不读取 .bashrc/.profile，因此交互环境里的别名、函数、扩展 PATH 全部缺席——这是「手动能跑、cron 跑不了」的系统性根因。
- **systemd 的依赖图**：After=/Requires=/Wants= 表达启动顺序与强弱依赖，由 systemd 拓扑排序后并行启动可达依赖集，比「rc 脚本顺序写死」更鲁棒；Restart= 实现进程级自愈。
- **SSH 签名验证的不对称性**：服务端只持公钥、私钥只留客户端，验证用公钥即可——非对称密码学使「证明拥有私钥」无需泄露私钥，这是公钥认证安全性的根基（区别于密码「双方都知明文」）。
### 📚 考研者视角
- **易错口径**：「为什么 crontab 里 */5 * * * * backup.sh 报错 command not found」→ cron 的 PATH 极简，命令要用绝对路径或在脚本里 export PATH。
- **标准问法**：「进程环境变量从哪来、能回传吗」→ 从父 fork 继承、只能向下、export 不回传父；「SSH 密码登录 vs 密钥登录」→ 密钥免明文传输、防中间人、可禁用密码暴力。
- **systemd vs cron 取舍**：cron 适合「简单周期性单命令」、无日志聚合、无依赖；systemd 适合「需守护、需重启、需依赖顺序、需日志」的服务进程。
- **StrictHostKeyChecking 的语义**：首次连接若不做指纹校验，攻击者可在中间冒充服务端——known_hosts 是「首次信任 + 后续比对」的 TOFU 模型，面试常问其安全前提。
