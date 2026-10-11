# 管道、重定向与文件描述符表

> 本节目标：把「|、>、2>&1、tee、xargs」全部还原成「对 fd 表的一组合法操作」。一旦用 fd 视角看，所有「顺序陷阱」都自然消失。
> 每个主题都按 **🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者** 三视角解析。

---

## 一、管道与重定向的本质：fd 表的复制与重定向

一切从「进程的 fd 表」出发。fd 表是内核里「小整数 → 打开文件描述」（file description）的数组；0=stdin、1=stdout、2=stderr。

- **重定向 > file**：open(file, O_WRONLY|O_CREAT|O_TRUNC) 拿到一个新 fd，然后 dup2(newfd, 1) 把 fd 1 **指向**这个新 file description，关闭原来的 fd 1 目标。
- **管道 a | b**：内核建一对 pipe fd（读端 r、写端 w，共享一块环形缓冲）；a 的 fd 1 被 dup2 到 w，b 的 fd 0 被 dup2 到 r；于是 a 写 stdout 实际写入管道、b 读 stdin 实际从管道读。

```
ls | wc -l 的 fd 表（简化）
  ls : fd0=终端  fd1 ──┐      wc : fd0 ──┐  fd1=终端
                       │pipe 写端        │pipe 读端
  （ls 的 stdout 重定向到 pipe 写端，wc 的 stdin 重定向到 pipe 读端）
```

**关键结论：管道 ≈ 临时文件 + 自动 fd 重定向**，但管道是内存环形缓冲、无磁盘 IO、且读端关闭时写端收 SIGPIPE。


### 🧑‍💻 程序员视角
- **2>&1 是「复制」不是「移动」**：2>&1 让 fd 2 **指向 fd 1 当前指向的那个目标**（不是字面指向 fd 1）。所以顺序决定一切：>file 2>&1 正确（先让 1 指向 file，2 跟着指向 file）；2>&1 >file 错误（2 先指向终端，1 才转向 file）。
- **诊断 Permission denied 写到了哪**：把 cmd >out 2>err 分开重定向，stdout 与 stderr 进不同文件，过滤错误只看 err；不要用 2>&1 混在一起再 grep。
- **tee 的用法**：cmd | tee log.txt 把 stdin 同时写 stdout 与文件——本质是 tee 持有两个写目标（管道读端 + 文件 fd）。
- **管道满会阻塞写端**：管道缓冲 64KB 满时，a 的 write 会**阻塞**直到 b 读走（这就是「慢消费者背压」），也是为什么 yes | head 不会无限写爆内存。
### 🎓 博士生视角
- **dup2 的原子语义**：dup2(new, old) 等价于「关闭 old（若已开）+ 让 old 指向 new 的目标」一步完成，避免了「先 close 再 dup」之间的竞态（fd 可能被别的线程抢占到 old 号）。
- **file description vs fd**：dup2 复制的是「指向同一 file description 的引用」，二者**共享文件偏移量与打开模式**（故管道两端看到同一缓冲）；而两次 open 同一文件得到**两个独立** file description（各自偏移）。这是 O_APPEND 并发安全的基础。
- **管道的内核实现**：pipe 是一对「伪 inode」+ 一块**有限环形缓冲**（Linux pipe(7) 默认 64KB，fcntl(F_SETPIPE_SZ) 可改）；读空/写满时按读写语义阻塞或返回 EAGAIN（非阻塞模式）。
- **重定向发生在 exec 之前**：shell 在 fork 子进程后、exec 目标程序前完成所有 dup2，目标程序**永远看到已布置好的 fd 表**，它对「我从管道读还是从文件读」毫不知情——这正是「一切皆 fd」的优雅之处。
### 📚 考研者视角
- **408 / 操作系统 · 文件系统**：fd 表、打开文件表、inode 的三级结构是常考模型（fd → file description → inode）。重定向的 dup2 改的是第一级（fd 表项指向），不改后两级。
- **易错口径**：「> 与 >> 的区别」→ > 是 O_TRUNC（清空后写）、>> 是 O_APPEND（追加且原子定位到末尾）；「2>&1 的顺序」是 output 题高频陷阱（见 pitfalls 第 5 条）。
- **标准问法**：「a | b 时如果 b 提前退出，a 会怎样」→ a 的写端收 SIGPIPE 默认终止（或 write 得 EPIPE）；「为什么 cat file | grep x > file 会清空 file」→ 重定向 > 在管道建立前已 truncate 文件。
- **/dev/null 的角色**：2>/dev/null 把 stderr 丢弃——/dev/null 是「写即丢弃、读即 EOF」的特殊文件，是丢弃输出的标准做法。
## 二、xargs/find -exec/tee：批量与组合的工程取舍

find 与 xargs 都能「找到文件并对每个执行命令」，差异在**进程创建次数**与**分隔符安全性**：

| 写法 | 进程创建 | 文件名安全 | 说明 |
|---|---|---|---|
| find ... -exec cmd {} \; | 每文件 1 次 | 安全（逐文件传参） | 最慢，N 文件 = N 进程 |
| find ... -exec cmd {} + | 批量（约 N/每批） | 安全 | 同 xargs 默认，推荐 |
| find ... -print0 \| xargs -0 cmd | 批量 | **安全（NUL 分隔）** | 处理含空格/换行文件名 |
| find ... \| xargs cmd | 批量 | **不安全**（空白拆分） | 含空格文件名被破坏 |

**为什么 -0 是必须的**：POSIX 文件名可含除 / 与 NUL 之外的任意字节，空格与换行都会让 xargs 的默认空白分隔出错；NUL 是唯一文件名中不会出现的字节，因此 -print0 | xargs -0 是 100% 安全的组合。


### 🧑‍💻 程序员视角
- **批量才是性能关键**：处理 10 万个文件，-exec \; 起 10 万次进程，-exec +/xargs 只起几十次——差距是「进程创建开销 × N」，实测见 examples/ex10（量化对比）。
- **xargs -P 并行**：find ... -print0 | xargs -0 -P 8 cmd 一次跑 8 个 worker，充分利用多核做独立任务（压缩、转码）。
- **tee -a 追加、tee 默认覆盖**；cmd 2>&1 | tee log 把 stderr 也并进日志。
- **xargs 读 stdin 来源要纯净**：不要把 ls 输出喂给 xargs（含空格就错），老实用 find -print0。
### 🎓 博士生视角
- **-exec + 的批大小**：find 会把尽量多的参数塞进一次 cmd 调用，受 ARG_MAX（命令行长度上限，约 2MB）约束，达到上限就再起一批，故进程数 ≈ ⌈N / 每批上限⌉，是最优的「少进程 + 不超 ARG_MAX」平衡。
- **NUL 分隔的不可伪造性**：内核禁止文件名含 \0，所以以 NUL 作记录分隔符能 100% 还原边界，而换行/空格都可能是合法文件名内容——这是「-print0/xargs -0 无可替代」的形式化理由。
- **xargs 默认分隔的退化**：默认按 \n、空格、tab 拆分且会做引号/反斜杠解释（GNU xargs），与 shell 词法耦合，进一步放大不确定性；显式 -d '\n' 或 -0 才能消除。
- **tee 的 fan-out**：tee 内部维护「读一端、写多端」的 fd 集合，是 shell 里少见的「一对多写」原语，等价于把 stdout 同时 dup2 到终端与文件两个 file description。
### 📚 考研者视角
- **易错口径**：「xargs 不写 -0 的隐患」是 output/排障题高频点，标准答法必须点名「空格/换行文件名 + NUL 分隔」。
- **find -delete 的安全性**：-delete 在 find 内部删除，不经 shell 词拆分，比 | xargs rm 更安全；但 -delete 隐含 -depth（自底向上），与 -prune 冲突，易踩坑。
- **标准问法**：「find -exec cmd {} + 和 xargs 区别」→ 都是批量、都安全，区别在是否依赖管道与分隔符；「为什么不用 for f in $(find)」→ 词拆分 + globbing 破坏文件名。
- **ARG_MAX 限制**：批量传参受命令行长度上限约束，这是 -exec + 必须分批的形式化原因，答「为什么不能一次传完所有文件」时要提到它。
