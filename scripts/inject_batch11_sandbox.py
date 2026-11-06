# -*- coding: utf-8 -*-
"""批次十一：tooling 五章 + ai 五章 + fundamentals 一章 + ml 一章 sandbox。

为什么是这十二章
---------------
这十二块内容在教材里大多是「最佳实践清单」，但每条实践背后都有一笔能算的账：

  tool-ch01  100 万个 1KB 文件：每个占满 4KB 块（浪费 75%），inode 表还要 244MB
  tool-ch02  Shell 循环里每文件 4 个进程：10 万次循环 = 40 万次 fork，8 分钟
  tool-ch03  100MB 大文件提交 50 次：5GB 仓库，克隆 400 分钟
  tool-ch04  30 天长期分支：6000 行改动在 10 万行库上重叠 360 行，90 小时解冲突
  tool-ch05  COPY . . 写在依赖安装前：40 次构建/天，每次重装 400MB 依赖
  ai-ch05    8K 窗口、20 轮历史、8 个示例：第 6 轮就开始丢对话
  ai-ch06    20 万篇文档 256 token 分块：390 万向量，float32 索引 14.5GB
  ai-ch07    50 个工具的 schema 常驻：每任务 6 万 token，一天 1216 元
  ai-ch09    像素空间扩散 1000 步：每张 200 秒，一千张要 55 小时
  ai-ch11    batch=1 跑 7B：吞吐 32 tok/s，10 万请求/天要 8 张卡
  fund-ch12  150ms RTT + HTTP/1.1 六连接：100 个资源首屏 3.4 秒
  ml-ch07    100 万用户全量相似度矩阵：3.6TB，训练 833 分钟

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限（小规模怎么配都对，没教学意义）。
2. 不锁「正确答案」，让预算判据自己淘汰错方案。
3. 默认值 = 真实事故配置。
4. 场景事实参数用 `==` 或单边界锁死，否则玩家把它拖到极端就能通关。
5. `if(c,a,b)` 急切求值 → 分支内除法保证除数非零常量。
6. fmt 只认 int / fix2 / pct。
7. 判据阈值留 5% 以上余量；被引用的指标必须定义在前面。
8. 除零风险：所有除以参数的地方，分母都取常量或 max(...,1)。

写盘必须 indent=1 + newline="\\n"；只替换本章 sandbox、保留 debug 等其它模块。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# tooling/tool-ch01 · 一百万个 1KB 文件，吃掉 4GB
# ----------------------------------------------------------------------------
# 教学点：ext4 按块分配，1KB 文件也占满 4KB 块（尾部浪费 75%）；
# 每个文件还要一个 256 字节 inode。100 万个小文件 = 3.9GB 数据 + 244MB inode，
# 而 `df -i` 用尽后即使还有空间也创建不了文件。归档成大文件就都消失了。
# ============================================================================
tool_ch01 = {
    "kind": "sandbox",
    "title": "一百万个 1KB 文件，吃掉 4GB",
    "brief": (
        "日志切片、缓存缩略图、模型分片——这类「一堆 1KB 小文件」在 `du` 里"
        "只报 976MB，实际却占掉 3.9GB：块分配的最小单位是 4KB，"
        "1KB 的内容也要占满一整块。外加每个文件 256 字节的 inode，"
        "一百万文件又是 244MB。把文件数、块大小与存放方式拖一拖，"
        "看这 4 倍是怎么凭空多出来的。"
    ),
    "params": [
        # 文件数（万）
        {"key": "filesW", "label": "小文件数量（万）", "min": 10, "max": 200, "step": 10, "value": 100},
        # 每个文件的真实大小（KB）
        {"key": "avgKB", "label": "每个文件大小", "min": 1, "max": 4, "step": 1, "value": 1},
        # 文件系统块大小
        {"key": "blockIdx", "label": "文件系统块大小", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["4KB（ext4 默认）", "16KB", "64KB"]},
        # 存放方式
        {"key": "archive", "label": "存放方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["散落成一堆小文件", "归档成少数大文件（tar/合并段）"]},
    ],
    "metrics": [
        {"key": "fileCount", "label": "文件总数", "expr": "filesW * 10000", "unit": "个", "fmt": "int"},
        {"key": "blockB", "label": "块大小", "expr": "if(blockIdx == 0, 4096, if(blockIdx == 1, 16384, 65536))", "unit": "字节", "fmt": "int"},
        # 数据本身大小
        {"key": "dataMB", "label": "数据本身", "expr": "fileCount * avgKB / 1024", "unit": "MB", "fmt": "int"},
        # 每文件实际占用的字节：归档后连续存放，不浪费；散落时向上取整到整块
        {"key": "perFileB", "label": "每个文件实占", "expr": "if(archive == 1, avgKB * 1024, ceil(avgKB * 1024 / blockB) * blockB)", "unit": "字节", "fmt": "int"},
        {"key": "totalMB", "label": "实际占用磁盘", "expr": "fileCount * perFileB / 1048576", "unit": "MB", "fmt": "int"},
        # 块内尾部浪费比例
        {"key": "wastePct", "label": "块内浪费", "expr": "round((perFileB - avgKB * 1024) * 100 / perFileB)", "unit": "%", "fmt": "int"},
        {"key": "inodeCount", "label": "inode 数量", "expr": "if(archive == 1, 1, fileCount)", "unit": "个", "fmt": "int"},
        # inode 表占用：每个 256 字节
        {"key": "inodeMB", "label": "inode 表占用", "expr": "inodeCount * 256 / 1048576", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：几百个文件谈不上块浪费
        {"expr": "fileCount >= 500000", "label": "文件数 ≥50 万（日志切片/缩略图的真实量级）"},
        # 既定事实：这就是 1KB 的小文件，不许把 size 拖到 4KB 蒙过去
        {"expr": "avgKB == 1", "label": "每个文件就是 1KB（改大小等于换场景）"},
        # 上限：块内浪费
        {"expr": "wastePct <= 10", "label": "块内浪费 ≤10%"},
        # 上限：磁盘占用（数据本身 976MB，留 20% 余量）
        {"expr": "totalMB <= 1200", "label": "实际占用 ≤1.2GB（数据只有 976MB）"},
        # 上限：inode 表
        {"expr": "inodeMB <= 4", "label": "inode 表 ≤4MB（别把 inode 吃光）"},
    ],
    "insight": (
        "`du -sh` 报的是 976MB，`du --apparent-size` 也报 976MB，"
        "但 `df` 显示少了 3.9GB——差额在**块分配**。"
        "文件系统不给「字节」分配空间，给**块**分配：ext4 默认 4KB 一块，"
        "你写 1KB，剩下的 3KB 就是尾部浪费（internal fragmentation），"
        "976MB 的 1KB 文件实际占 `100 万 × 4KB = 3.9GB`，**浪费率 75%**。"
        "更容易被忽略的是 **inode**：每个文件（目录也是文件）都要一个 inode，"
        "ext4 每个 256 字节，`mkfs` 时按卷大小预分配固定数量。"
        "100 万个文件要 244MB 的 inode 表，而且**inode 总数是建卷时定死的**——"
        "`df -h` 还有 50GB 空间、`df -i` 已经 100%，此时 `touch` 报 "
        "`No space left on device`，这是排查小文件问题最容易踩的坑。"
        "三条实操："
        "① **能合并就别散落**：日志按小时切片不如按 128MB 段写，"
        "或者直接进对象存储/时序库；`tar` 归档后连续存放，块浪费归零、inode 只要 1 个；"
        "② **块大小是权衡**：把块调到 64KB 能减少 inode 数量，但只要文件小于 64KB "
        "浪费更严重（1KB 文件变 64 倍），所以「大块 + 大文件」要配套；"
        "③ **监控 `df -i`**：容器镜像层、CI 缓存、邮件队列都是小文件重灾区，"
        "inode 耗尽的表现是「有空间却写不进去」。"
    ),
}


# ============================================================================
# tooling/tool-ch02 · Shell 循环里 fork 了四十万次
# ----------------------------------------------------------------------------
# 教学点：`for f in *.log; do cat $f | grep x >> out; done` 每轮起 3~4 个进程，
# 每次 fork+exec 约 1.2ms；10 万个文件 = 40 万次 fork = 8 分钟。
# 换成单个 awk 一次读全部文件，fork 只要 1 次。
# ============================================================================
tool_ch02 = {
    "kind": "sandbox",
    "title": "Shell 循环里 fork 了四十万次",
    "brief": (
        "`for f in *.log; do cat $f | grep 超时 >> bad.txt; done` 看起来是标准写法，"
        "但每轮循环都要 fork 出 `cat` 和 `grep` 两个进程（管道再加一个子 shell），"
        "一次 fork+exec 约 1.2ms。10 万个文件就是 40 万次 fork，"
        "光进程创建就烧掉 8 分钟——而实际读的数据只有 5GB，2.5 秒就读完了。"
    ),
    "params": [
        {"key": "filesW", "label": "待处理文件数（万）", "min": 5, "max": 40, "step": 5, "value": 10},
        {"key": "dataGB", "label": "数据总量（GB）", "min": 1, "max": 100, "step": 1, "value": 5},
        {"key": "mode", "label": "处理方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["每文件 cat|grep|sed（4 进程）", "每文件单进程（awk 逐文件）", "单进程批量（awk 一次读全部）"]},
    ],
    "metrics": [
        {"key": "fileCount", "label": "文件总数", "expr": "filesW * 10000", "unit": "个", "fmt": "int"},
        # 进程创建次数
        {"key": "forks", "label": "fork+exec 次数", "expr": "if(mode == 0, fileCount * 4, if(mode == 1, fileCount, 1))", "unit": "次", "fmt": "int"},
        # 每次 fork+exec 1.2ms
        {"key": "forkSec", "label": "进程创建耗时", "expr": "forks * 12 / 10000", "unit": "秒", "fmt": "fix2"},
        # 读数据：2GB/s
        {"key": "ioSec", "label": "读数据耗时", "expr": "dataGB * 1024 / 2000", "unit": "秒", "fmt": "fix2"},
        {"key": "totalSec", "label": "总耗时", "expr": "forkSec + ioSec", "unit": "秒", "fmt": "fix2"},
        {"key": "forkPct", "label": "fork 占比", "expr": "round(forkSec * 100 / (forkSec + ioSec))", "unit": "%", "fmt": "int"},
        # 上下文切换次数：每次 fork 至少两次
        {"key": "ctxSwitches", "label": "上下文切换", "expr": "forks * 2", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        {"expr": "fileCount >= 50000", "label": "文件数 ≥5 万（日志切片的真实量级）"},
        # 上限：进程创建总耗时
        {"expr": "forkSec <= 20", "label": "进程创建 ≤20 秒"},
        {"expr": "forkPct <= 10", "label": "fork 占比 ≤10%（别把时间花在创建进程上）"},
        {"expr": "totalSec <= 60", "label": "总耗时 ≤60 秒"},
    ],
    "insight": (
        "Unix 的「组合小工具」哲学在交互式场景很优雅，但放进**循环**里就变成 "
        "fork 炸弹的温和版本：每次 `cat`、每次 `grep`、管道两端的子 shell，"
        "都是一次 `fork()` + `execve()`。fork 要复制页表、exec 要重新加载 ELF、"
        "跑动态链接器，机械盘时代每次 1~3ms，SSD 机上也要 0.5~1.2ms。"
        "10 万个文件 × 4 个进程 = 40 万次，480 秒——**而这些时间没有一秒在干活**。"
        "判断标准很简单：**循环体里有没有 `|`、`$()`、`&&`**。有就至少多 2 个进程。"
        "三条实操："
        "① **用 awk/sed 一次处理多个文件**：`awk 'FNR==1{f=FILENAME} /超时/{print f\":\"$0}' *.log` "
        "只有一个进程，`FNR`/`FILENAME` 自动区分文件边界——这是 shell 里最低成本的替换；"
        "② **`xargs` 批量传参**：`find . -name '*.log' -print0 | xargs -0 -n 500 grep -l 超时` "
        "把 500 个文件塞给一次 grep，fork 次数降到 1/500；"
        "③ **`while read` 循环里的 `ssh`/`curl` 是同一个病**：一万台机器逐个 ssh 要几十分钟，"
        "换成 `pssh`/Ansible 的并发批量、或者 `ssh -O` 复用连接。"
        "顺带一条：循环里 `>>` 追加写每次都要 open/write/close，"
        "`done > out.txt` 在循环外重定向一次能省掉 N 次系统调用。"
    ),
}


# ============================================================================
# tooling/tool-ch03 · 100MB 的模型文件提交 50 次，仓库 5GB
# ----------------------------------------------------------------------------
# 教学点：Git 的 commit 是快照不是差异，每次改动都新增一个完整 blob；
# 二进制文件压不动，gc 后的 delta 也只能省 2%；clone 要把全部历史拉下来。
# ============================================================================
tool_ch03 = {
    "kind": "sandbox",
    "title": "100MB 的模型文件提交 50 次，仓库 5GB",
    "brief": (
        "把 100MB 的模型权重放进 Git，每改一次提交一次——50 个版本之后，"
        "`.git` 里躺着 5GB。原因不是「Git 存了 50 份差量」，而是**每个 commit 都是快照**："
        "内容变一个字节就是一个新 blob，二进制又压不动，`gc --aggressive` 也只能省 2%。"
        "而新人 `clone` 要把全部历史拉下来：5GB 在 12.5MB/s 的网络上要 6.7 小时。"
    ),
    "params": [
        {"key": "fileMB", "label": "单个大文件大小", "min": 10, "max": 500, "step": 10, "value": 100},
        {"key": "versions", "label": "提交了多少个版本", "min": 5, "max": 200, "step": 5, "value": 50},
        {"key": "mode", "label": "存放方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["直接 commit 进 Git", "Git LFS（指针进库）", "不进仓库（构建时下载）"]},
        {"key": "gc", "label": "是否定期 gc", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["从不 gc", "定期 gc --aggressive"]},
    ],
    "metrics": [
        # 未打包：每个版本一个完整 blob
        {"key": "looseMB", "label": "各版本原始体积", "expr": "versions * fileMB", "unit": "MB", "fmt": "int"},
        # gc 后：二进制 delta 几乎无效，总共只省 2%
        {"key": "gcMB", "label": "gc 后仓库体积", "expr": "versions * fileMB * 98 / 100", "unit": "MB", "fmt": "int"},
        # 实际仓库（.git）体积
        {"key": "repoMB", "label": "仓库体积", "expr": "if(mode == 0, if(gc == 1, gcMB, looseMB), if(mode == 1, versions * 13 / 10000, 1 / 1000))", "unit": "MB", "fmt": "int"},
        # LFS 服务端存的完整对象（不随 clone 下载）
        {"key": "lfsMB", "label": "LFS 服务端存储", "expr": "if(mode == 1, versions * fileMB, 0)", "unit": "MB", "fmt": "int"},
        # clone 要拉的东西：LFS 只拉指针，文件按需
        {"key": "cloneMB", "label": "clone 下载量", "expr": "if(mode == 1, 2, repoMB)", "unit": "MB", "fmt": "int"},
        # 12.5MB/s → MB / 12.5 秒
        {"key": "cloneMin", "label": "新人 clone 耗时", "expr": "cloneMB * 8 / 100 / 60", "unit": "分钟", "fmt": "fix2"},
        {"key": "clonePct", "label": "clone 相对未 gc 的比例", "expr": "round(cloneMB * 100 / looseMB)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        {"expr": "fileMB >= 100", "label": "文件 ≥100MB（模型权重的真实体积）"},
        {"expr": "versions >= 50", "label": "至少提交过 50 个版本"},
        # 上限：clone 时间
        {"expr": "cloneMin <= 2", "label": "clone ≤2 分钟"},
        # 上限：仓库体积
        {"expr": "repoMB <= 300", "label": "仓库 ≤300MB（Git 适合放代码，不适合放资产）"},
    ],
    "insight": (
        "「Git 存的是差异」是流传最广的误解。真相是：**commit 是快照**，"
        "每个版本都记录一份完整的 tree，指向当时的全部 blob；"
        "「省空间」发生在 `gc` 时的 **packfile delta** 压缩，而 delta 的前提是**相似文本**。"
        "二进制文件（模型权重、图片、视频、压缩包）改一个字节，整个字节流都变，"
        "delta 找不到匹配窗口——实测 100MB 的权重改 50 次，"
        "`gc --aggressive` 后仍有 200MB（只省了 2%），不 gc 就是 5GB。"
        "更贵的是**每个新人都得 clone 全部历史**：5GB 在 12.5MB/s 上要 6.7 小时，"
        "CI 每次全量 clone 更是持续放血。"
        "三条实操："
        "① **Git LFS**：仓库里只存 130 字节的指针，对象在 LFS 服务端，"
        "clone 默认只拉当前版本，`git lfs fetch --all` 按需取历史——代价是服务端存储照旧、"
        "且 LFS 有自己的配额与「忘记 push LFS」的坑；"
        "② **干脆不进仓库**：构建产物、数据集、模型权重放对象存储/制品库，"
        "仓库里只留下载脚本与校验和（`sha256sum`），CI 层做缓存；"
        "③ **已经进了历史的**：`git filter-repo --path 大文件 --invert-paths` 重写历史，"
        "然后让所有人重新 clone（`filter-branch` 慢且易错，别用）；"
        "改写后旧 blob 仍会留在 reflog 和远端直到 `gc --prune=now`。"
        "判断标准：**文本用 Git，二进制用制品库**。"
    ),
}


# ============================================================================
# tooling/tool-ch04 · 分支活了 30 天，解冲突花了 90 小时
# ----------------------------------------------------------------------------
# 教学点：冲突面积 ≈ 双方改动行数的乘积 / 代码库规模；分支越久双方改得越多，
# 冲突量按天数平方增长。集成延迟（合入前看不到主干变化）是另一半代价。
# ============================================================================
tool_ch04 = {
    "kind": "sandbox",
    "title": "分支活了 30 天，解冲突花了 90 小时",
    "brief": (
        "主干上 200 行/天的改动速度，一个分支活了 30 天——"
        "分支这边改了 6000 行，主干那边也改了 6000 行，"
        "在 10 万行的代码库里期望重叠 360 行。每行冲突平均 15 分钟（读上下文、"
        "判断谁的逻辑对、跑测试），90 小时就没了，而这只是**一次**合并。"
        "冲突量按天数**平方**增长——分支活两倍久，冲突四倍。"
    ),
    "params": [
        {"key": "branchDays", "label": "分支存活天数", "min": 7, "max": 60, "step": 1, "value": 30},
        {"key": "linesPerDay", "label": "每天改动行数", "min": 40, "max": 500, "step": 10, "value": 200},
        {"key": "codeKLines", "label": "代码库规模（千行）", "min": 10, "max": 500, "step": 10, "value": 100},
        {"key": "mode", "label": "协作方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["长期分支，末尾一次性合", "每天 rebase 到主干", "trunk-based 小 PR（每日合并）"]},
    ],
    "metrics": [
        # 分支这边累计改动：rebase / trunk-based 时只算一天的量
        {"key": "effDays", "label": "未同步天数", "expr": "if(mode == 0, branchDays, 1)", "unit": "天", "fmt": "int"},
        {"key": "effLines", "label": "每天改动（小 PR 更碎）", "expr": "if(mode == 2, linesPerDay * 40 / 100, linesPerDay)", "unit": "行", "fmt": "int"},
        {"key": "changedLines", "label": "分支累计改动", "expr": "effDays * effLines", "unit": "行", "fmt": "int"},
        # 冲突期望：双方改动行数的乘积 / 代码库总量
        {"key": "conflictLines", "label": "期望冲突行", "expr": "changedLines * changedLines / (codeKLines * 1000)", "unit": "行", "fmt": "fix2"},
        # 每行冲突 15 分钟
        {"key": "conflictHours", "label": "解冲突耗时", "expr": "conflictLines * 15 / 60", "unit": "小时", "fmt": "fix2"},
        # 集成延迟：改动最久没被主干验证过的天数
        {"key": "delayDays", "label": "集成延迟", "expr": "if(mode == 0, branchDays, 1)", "unit": "天", "fmt": "int"},
        {"key": "mergeCount", "label": "合并次数", "expr": "if(mode == 2, branchDays, 1)", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        {"expr": "branchDays >= 14", "label": "分支至少活 14 天（这就是要治的病）"},
        {"expr": "linesPerDay >= 150", "label": "团队每天改动 ≥150 行（真实节奏）"},
        {"expr": "codeKLines >= 50", "label": "代码库 ≥5 万行（有足够的重叠面积）"},
        # 上限：冲突成本
        {"expr": "conflictHours <= 2", "label": "解冲突 ≤2 小时/次"},
        # 上限：集成延迟，太久就有「合并地狱」风险
        {"expr": "delayDays <= 3", "label": "集成延迟 ≤3 天（问题要尽早暴露）"},
    ],
    "insight": (
        "冲突不是「运气不好撞上了」，而是可以估的：假设双方改动在文件里均匀分布，"
        "分支改了 `a` 行、主干同期改了 `b` 行、代码库 `N` 行，"
        "那么期望重叠行数 ≈ `a × b / N`。"
        "**关键在这个乘积**：分支活 30 天，`a` 和 `b` 都随时间线性增长，"
        "冲突量按**天数平方**涨——活 60 天不是冲突翻倍，是翻四倍。"
        "而且这只是冲突行数，每行还要读上下文、判断谁对、跑测试，15 分钟一行是低估。"
        "第二笔账是**集成延迟**：分支 30 天没合入，意味着这 30 天里主干上的所有改动"
        "（接口变化、依赖升级、别人的 bug 修复）都没和你的代码一起验证过。"
        "**风险在合并那一刻集中兑现**，而不是分摊到每一天。"
        "三条实操："
        "① **trunk-based + 小 PR**：分支活不过 1~2 天，每天改动量也小，`a×b/N` 两头都小；"
        "配合 feature flag 让未完成的代码也能合入主干；"
        "② **每天 rebase 或 merge 主干**：`git rebase origin/main` 把冲突摊到每天几十行，"
        "而不是最后 360 行一次性砸过来——注意 rebase 改写历史，只在**自己的**分支上做；"
        "③ **`rerere` 记住你的解法**：`git config rerere.enabled true`，"
        "同一个冲突第二次出现时自动套用上次的解决方式，长期分支反复 rebase 时省大量手工；"
        "④ **冲突的充要条件是「同一文件同一区域」**——把大文件拆小、"
        "按模块划分所有权，能从结构上降低重叠概率。"
    ),
}


# ============================================================================
# tooling/tool-ch05 · COPY . . 写在装依赖前面，每次构建多花 4 分钟
# ----------------------------------------------------------------------------
# 教学点：Docker 层缓存逐层失效。`COPY . .` 在 `RUN npm ci` 之前，
# 改一行代码就让依赖层失效；单阶段构建把编译器、源码、缓存全留在镜像里。
# ============================================================================
tool_ch05 = {
    "kind": "sandbox",
    "title": "COPY . . 写在装依赖前面，每次构建多花 4 分钟",
    "brief": (
        "Dockerfile 里 `COPY . .` 排在 `RUN npm ci` 之前，看起来只是顺序问题——"
        "实际上每改一行代码，`COPY` 层的哈希就变了，**后面所有层全部失效**，"
        "400MB 依赖每次重装 4 分钟。一天构建 40 次就是 4 小时排队。"
        "另一半代价在镜像体积：单阶段构建把编译器、node_modules 缓存、"
        "源码全留在最终镜像里，1.3GB 每台机器都要拉一遍。"
    ),
    "params": [
        {"key": "depMB", "label": "依赖体积", "min": 100, "max": 1000, "step": 50, "value": 400},
        {"key": "order", "label": "COPY 与装依赖的顺序", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["COPY . . 在前（一行改动全失效）", "先 COPY 依赖清单再装（缓存命中）"]},
        {"key": "multi", "label": "构建阶段", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["单阶段（编译产物与工具链同层）", "多阶段（只拷产物到运行镜像）"]},
        {"key": "buildsPerDay", "label": "每天构建次数", "min": 5, "max": 100, "step": 5, "value": 40},
    ],
    "metrics": [
        # 依赖安装：100MB 约 1 分钟（含解压、链接）
        {"key": "installMin", "label": "装依赖耗时", "expr": "if(order == 1, 0, depMB / 100)", "unit": "分钟", "fmt": "fix2"},
        {"key": "compileMin", "label": "编译打包耗时", "expr": "2", "unit": "分钟", "fmt": "int"},
        {"key": "buildMin", "label": "单次构建", "expr": "installMin + compileMin", "unit": "分钟", "fmt": "fix2"},
        {"key": "dailyHours", "label": "每天排队时间", "expr": "buildMin * buildsPerDay / 60", "unit": "小时", "fmt": "fix2"},
        # 镜像体积：单阶段把工具链/源码/缓存约 900MB 留在里面
        {"key": "imageMB", "label": "镜像体积", "expr": "if(multi == 1, depMB + 60, depMB + 900)", "unit": "MB", "fmt": "int"},
        # 每天要把镜像推到仓库的量
        {"key": "pushGB", "label": "每天推送量", "expr": "imageMB * buildsPerDay / 1024", "unit": "GB", "fmt": "fix2"},
        {"key": "cacheHitPct", "label": "依赖层缓存命中率", "expr": "if(order == 1, 100, 0)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        {"expr": "depMB >= 300", "label": "依赖 ≥300MB（Node/Python 项目的常态）"},
        {"expr": "buildsPerDay >= 20", "label": "每天 ≥20 次构建（团队协作的正常频率）"},
        # 上限：每天的构建排队
        {"expr": "dailyHours <= 1.5", "label": "每天构建排队 ≤1.5 小时"},
        # 上限：镜像体积
        {"expr": "imageMB <= 600", "label": "镜像 ≤600MB（运行镜像不该带编译器）"},
        # 上限：缓存命中
        {"expr": "cacheHitPct >= 90", "label": "依赖层缓存命中率 ≥90%"},
    ],
    "insight": (
        "Docker 的层缓存规则只有一句：**每条指令的输入哈希变了，它和它之后的层全部失效**。"
        "`COPY . .` 的输入是**整个构建上下文**——改一个空格，哈希就变。"
        "所以 `COPY . .` 排在 `RUN npm ci` 前面时，依赖层永远命中不了，"
        "每次构建都从零装一遍；把它挪到后面、先 `COPY package*.json` 再装依赖，"
        "只有 lock 文件变化时才重装。**顺序不是风格问题，是 4 分钟 × 每天 40 次。**"
        "第二笔账是镜像体积。单阶段构建里，`RUN pip install` 拉的编译器、"
        "`node_modules` 里的构建工具、源码、`.npm` 缓存，全都留在最后一层。"
        "多阶段构建（`FROM builder AS build` → `FROM runtime` + `COPY --from=build`）"
        "让运行镜像只带产物和运行时，1.3GB 能砍到 400MB 出头。"
        "体积的代价是复利：每台机器、每次扩容、每次回滚都要拉 1.3GB。"
        "四条实操："
        "① **依赖清单单独 COPY**：`COPY package.json package-lock.json ./` → `RUN npm ci` → "
        "`COPY . .`，最后才是代码；"
        "② **合并 RUN 减少层数**：`apt-get update && apt-get install -y ... && rm -rf /var/lib/apt/lists/*` "
        "必须在**同一条** RUN 里，分开写的话 `rm` 只是在新层里加个白障，前一层的数据还在；"
        "③ **多阶段 + distroless/alpine 运行镜像**：不只有体积，还少了整条 CVE 攻击面；"
        "④ **`.dockerignore` 是免费加速**：`COPY . .` 的上下文包含 `node_modules`、`.git` 时，"
        "光是传输与哈希就要几十秒，别让它们进上下文。"
    ),
}


# ============================================================================
# ai/ai-ch05 · 8K 窗口，第 6 轮就开始丢对话
# ----------------------------------------------------------------------------
# 教学点：上下文 = system + few-shot + 历史 + 当前输入 + 输出预留。
# 20 轮历史 × 300 token = 6000，8K 窗口扣掉 20% 输出预留只剩 6400，
# few-shot 再占 1600 → 溢出，只能丢最早的历史。
# ============================================================================
ai_ch05 = {
    "kind": "sandbox",
    "title": "8K 窗口，第 6 轮就开始丢对话",
    "brief": (
        "8K 上下文的模型，system prompt 占 500 token，塞 8 个 few-shot 示例占 1600，"
        "20 轮对话历史占 6000——再加上 20% 的输出预留，总需求 8100 > 6400 的预算。"
        "结果是**最前面的 6 轮对话被静默截断**，用户问「我刚才说的偏好是什么」时模型一脸茫然。"
        "这不是模型笨，是预算没算。"
    ),
    "params": [
        {"key": "windowK", "label": "上下文窗口（K token）", "min": 4, "max": 128, "step": 4, "value": 8},
        {"key": "shots", "label": "few-shot 示例数", "min": 0, "max": 20, "step": 1, "value": 8},
        {"key": "histTurns", "label": "对话历史轮数", "min": 4, "max": 40, "step": 2, "value": 20},
        {"key": "histMode", "label": "历史处理方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["全量保留", "滑动窗口（只留最近 4 轮）", "摘要压缩（每 5 轮压成 1 条）"]},
    ],
    "metrics": [
        # 扣掉 20% 输出预留
        {"key": "budget", "label": "输入预算", "expr": "windowK * 1000 * 80 / 100", "unit": "token", "fmt": "int"},
        # 历史：每轮 300 token
        {"key": "histTokens", "label": "历史占用", "expr": "if(histMode == 0, histTurns * 300, if(histMode == 1, 1200, ceil(histTurns / 5) * 200))", "unit": "token", "fmt": "int"},
        # system 500 + 每示例 200
        {"key": "promptTokens", "label": "输入总 token", "expr": "500 + shots * 200 + histTokens", "unit": "token", "fmt": "int"},
        {"key": "overflow", "label": "超出预算", "expr": "max(0, promptTokens - budget)", "unit": "token", "fmt": "int"},
        # 溢出时只能丢最早的历史：每轮 300 token
        {"key": "droppedTurns", "label": "被丢掉的历史轮数", "expr": "if(promptTokens - budget <= 0, 0, ceil((promptTokens - budget) / 300))", "unit": "轮", "fmt": "int"},
        {"key": "keepPct", "label": "历史保留率", "expr": "round((histTurns - if(promptTokens - budget <= 0, 0, ceil((promptTokens - budget) / 300))) * 100 / max(histTurns, 1))", "unit": "%", "fmt": "int"},
        # 单次请求成本：输入 2 元/百万 token
        {"key": "costPerK", "label": "千次请求成本", "expr": "promptTokens * 1000 / 1000000 * 2", "unit": "元", "fmt": "fix2"},
    ],
    "checks": [
        # 既定事实：8K 窗口就是这个模型的能力边界，不许换 128K
        {"expr": "windowK == 8", "label": "上下文窗口 8K（换模型等于换场景）"},
        {"expr": "histTurns == 20", "label": "对话 20 轮（一次客服会话的真实长度）"},
        # 下限：few-shot 是输出质量的来源，不能靠删示例过关
        {"expr": "shots >= 3", "label": "至少保留 3 个 few-shot 示例"},
        # 上限：不能溢出
        {"expr": "overflow == 0", "label": "输入不能超出预算（溢出就要丢历史）"},
        # 上限：历史保留
        {"expr": "keepPct >= 100", "label": "历史完整保留（不丢轮次）"},
        # 上限：成本
        {"expr": "costPerK <= 12", "label": "千次请求 ≤12 元"},
    ],
    "insight": (
        "上下文窗口是**硬预算**，不是「大概够」：`system + few-shot + 历史 + 当前输入 + 输出预留` "
        "五项加起来超过窗口，框架的做法通常是**从最早的消息开始丢**——"
        "用户第一轮说的「我是企业版用户、不要提价格」就这么消失了，而且**没有任何报错**。"
        "按 8K 窗口算：留 20% 给输出（1600），输入预算 6400；"
        "system 500 + 8 个示例 1600 + 20 轮历史 6000 = 8100，超 1700 → 丢 6 轮。"
        "三条实操："
        "① **给每一项定额**：比如 system ≤500、few-shot ≤1500、检索片段 ≤2000、"
        "历史 ≤1500、输出预留 20%，加起来必须装得下；配额超了就按优先级砍，"
        "而不是让框架随机截断；"
        "② **历史要主动管理**：滑动窗口（只留最近 N 轮）最简单但会丢早期的关键约束；"
        "**摘要压缩**（把前 N 轮让模型总结成一条 200 token 的「已知信息」）保留语义、"
        "成本可控，是长会话的默认选择；"
        "③ **few-shot 的边际收益递减**：从 0 到 3 个示例提升最大，从 8 到 16 个几乎不涨，"
        "但 token 成本线性增长——**用 3~5 个高质量示例，不是 20 个平庸示例**；"
        "④ **把稳定的部分放前面**：system 与 few-shot 在前、易变的历史在后，"
        "还能吃到 prefix caching 的折扣（缓存命中的输入 token 通常便宜 50%~90%）。"
    ),
}


# ============================================================================
# ai/ai-ch06 · 二十万篇文档建索引，14GB 内存
# ----------------------------------------------------------------------------
# 教学点：向量内存 = 块数 × 维度 × 每维字节。分块越小块越多、内存越大；
# 分块越大，topK 拼进上下文的 token 越多、越容易超预算。
# ============================================================================
ai_ch06 = {
    "kind": "sandbox",
    "title": "二十万篇文档建索引，14GB 内存",
    "brief": (
        "20 万篇文档、平均 5000 token，按 256 token 切块得到 390 万个向量。"
        "768 维 float32 每个 3KB，光向量就 11GB，加上 HNSW 的图结构 14.5GB——"
        "一台 16GB 的机器直接 OOM。切大一点能省内存，但 topK 拼进上下文的 token 也跟着涨。"
        "分块大小是「索引内存 × 上下文预算」的双向取舍。"
    ),
    "params": [
        {"key": "docsW", "label": "文档数量（万篇）", "min": 5, "max": 100, "step": 5, "value": 20},
        {"key": "avgDocK", "label": "每篇平均（K token）", "min": 1, "max": 20, "step": 1, "value": 5},
        {"key": "chunkIdx", "label": "分块大小", "min": 0, "max": 3, "step": 1, "value": 0,
         "labels": ["256 token", "512 token", "1024 token", "2048 token"]},
        {"key": "dtype", "label": "向量精度", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["float32（3KB/条）", "int8 量化（768B/条）"]},
        {"key": "topK", "label": "召回条数 topK", "min": 3, "max": 20, "step": 1, "value": 5},
    ],
    "metrics": [
        {"key": "totalM", "label": "语料总量", "expr": "docsW * 10000 * avgDocK / 1000", "unit": "百万 token", "fmt": "int"},
        {"key": "chunkSize", "label": "每块 token", "expr": "if(chunkIdx == 0, 256, if(chunkIdx == 1, 512, if(chunkIdx == 2, 1024, 2048)))", "unit": "token", "fmt": "int"},
        {"key": "chunks", "label": "向量条数", "expr": "ceil(totalM * 1000000 / chunkSize)", "unit": "条", "fmt": "int"},
        {"key": "bytesPer", "label": "每条向量字节", "expr": "if(dtype == 0, 3072, 768)", "unit": "字节", "fmt": "int"},
        {"key": "vecGB", "label": "向量本体", "expr": "chunks * bytesPer / 1073741824", "unit": "GB", "fmt": "fix2"},
        # HNSW 图结构约 +30%
        {"key": "indexGB", "label": "索引总内存", "expr": "vecGB * 13 / 10", "unit": "GB", "fmt": "fix2"},
        # topK × 块大小 = 塞进上下文的 token
        {"key": "ctxTokens", "label": "拼进上下文的 token", "expr": "topK * chunkSize", "unit": "token", "fmt": "int"},
        # HNSW 查询约 3ms 基础 + 每百万条 2ms
        {"key": "searchMs", "label": "单次检索延迟", "expr": "3 + chunks * 2 / 1000000", "unit": "ms", "fmt": "fix2"},
    ],
    "checks": [
        {"expr": "docsW >= 20", "label": "至少 20 万篇文档（知识库的真实规模）"},
        # 既定事实：真实文档一篇就是几千 token，拖到 1000 等于换场景
        {"expr": "avgDocK == 5", "label": "每篇约 5000 token（真实文档的长度）"},
        # 下限：块太小语义不完整，一段话被切成几截
        {"expr": "chunkSize >= 512", "label": "每块 ≥512 token（装得下一个完整段落）"},
        {"expr": "topK >= 5", "label": "召回至少 5 条（召回率下限）"},
        # 上限：索引内存
        {"expr": "indexGB <= 4", "label": "索引 ≤4GB"},
        # 上限：上下文预算
        {"expr": "ctxTokens <= 6000", "label": "拼进上下文 ≤6000 token"},
        {"expr": "searchMs <= 30", "label": "检索延迟 ≤30ms"},
    ],
    "insight": (
        "RAG 的内存账能精确到字节：`向量数 × 维度 × 每维字节数`。"
        "768 维 float32 = 3072 字节/条；1000 万条就是 30GB，"
        "HNSW 还要存邻居表（M=16 时约 +30%）。"
        "**分块大小是杠杆**：块从 256 调到 1024，向量数降到 1/4，内存直接省 3/4；"
        "但代价在另一头——`topK × 块大小` 就是拼进上下文的 token 数，"
        "topK=5、块 2048 时一次要塞 10240 token，比很多模型的输入预算还大。"
        "所以分块不是「越小越精确」，是**在检索精度、内存、上下文预算之间找交点**。"
        "四条实操："
        "① **512~1024 token 是甜点**：语义完整度够、向量数可控；"
        "加 10%~20% 的 **overlap** 防止一句话被切断（块本身仍按 1024 算）；"
        "② **int8 量化是免费午餐**：768 维 float32 → int8 只损失 1%~2% 召回，"
        "内存降到 1/4，还提升缓存命中率；再狠一点用 PQ/OPQ，能压到 1/32 但有损；"
        "③ **别把整篇文档当一个向量**：语义被平均掉了，长文档检索几乎必失；"
        "也**别把句子当块**：检索命中了但上下文不够，模型答不出来；"
        "④ **混合检索 + rerank**：向量召回 top 50，再用 BM25 与 cross-encoder 重排到 top 5，"
        "比单纯调大 topK 更省 token 也更准——**召回宽、精排窄**是标准姿势。"
    ),
}


# ============================================================================
# ai/ai-ch07 · 五十个工具的 schema，每任务烧六万 token
# ----------------------------------------------------------------------------
# 教学点：function calling 的每个工具 schema 都常驻上下文，每轮都要重发。
# 50 工具 × 120 token = 6000 token/轮，ReAct 10 轮 → 6 万 token/任务，
# 同时工具越多选择准确率越低。意图路由先筛到 8 个，两项一起降。
# ============================================================================
ai_ch07 = {
    "kind": "sandbox",
    "title": "五十个工具的 schema，每任务烧六万 token",
    "brief": (
        "function calling 的工具定义**每次请求都要重发一遍**，不是注册一次就完事。"
        "50 个工具、每个 schema 120 token = 6000 token 常驻，"
        "ReAct 跑 10 轮就是 6 万 token/任务——一天 1 万次任务烧 1216 元，"
        "而且工具越多模型越容易选错（准确率从 95% 掉到 62%）。"
        "先做意图路由把候选筛到 8 个，两项一起降。"
    ),
    "params": [
        {"key": "tools", "label": "注册的工具数", "min": 5, "max": 200, "step": 5, "value": 50},
        {"key": "toolTokens", "label": "每个 schema token", "min": 40, "max": 300, "step": 10, "value": 120},
        {"key": "steps", "label": "每任务 ReAct 轮数上限", "min": 3, "max": 20, "step": 1, "value": 10},
        {"key": "tasksK", "label": "每天任务数（千）", "min": 1, "max": 100, "step": 1, "value": 1},
        {"key": "router", "label": "工具选择方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["全量工具直接塞给模型", "先意图路由，只给 8 个候选"]},
    ],
    "metrics": [
        # 每轮都要重发的工具 schema
        {"key": "schemaTokens", "label": "工具 schema 占用", "expr": "if(router == 1, 8 * toolTokens + 300, tools * toolTokens)", "unit": "token", "fmt": "int"},
        # 每任务：轮数 × schema + 系统/用户/观察
        {"key": "tokensPerTask", "label": "每任务 token", "expr": "schemaTokens * steps + 800", "unit": "token", "fmt": "int"},
        {"key": "dailyMTokens", "label": "每天 token 量", "expr": "tasksK * 10000 * tokensPerTask / 1000000", "unit": "百万 token", "fmt": "fix2"},
        # 输入按 2 元/百万 token
        {"key": "costYuan", "label": "每天 token 成本", "expr": "dailyMTokens * 2", "unit": "元", "fmt": "int"},
        # 每轮一次 LLM 往返 2.5 秒
        {"key": "latencySec", "label": "单任务耗时", "expr": "steps * 25 / 10", "unit": "秒", "fmt": "fix2"},
        # 工具选择准确率：候选越多越容易挑错
        {"key": "toolPickPct", "label": "工具选择准确率", "expr": "if(router == 1, 95, if(tools <= 20, 88, if(tools <= 50, 75, 62)))", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        {"expr": "tasksK >= 1", "label": "每天 ≥1000 次任务（线上 Agent 的真实量级）"},
        {"expr": "tools >= 20", "label": "工具库至少 20 个（真实系统的规模）"},
        # 下限：真实任务需要多轮工具调用，不许把轮数压到 1
        {"expr": "steps >= 4", "label": "至少允许 4 轮（真实任务要多次调用工具）"},
        {"expr": "schemaTokens <= 1500", "label": "工具 schema ≤1500 token"},
        {"expr": "costYuan <= 250", "label": "每天 token 成本 ≤250 元"},
        {"expr": "latencySec <= 20", "label": "单任务 ≤20 秒"},
        {"expr": "toolPickPct >= 90", "label": "工具选择准确率 ≥90%"},
        # 下限：一个带参数说明的 JSON Schema 至少 100 token
        {"expr": "toolTokens >= 100", "label": "每个 schema ≥100 token（再少就丢参数说明了）"},
    ],
    "insight": (
        "Agent 的成本结构和聊天完全不同：**工具定义是常驻开销**。"
        "function calling 的实现是把 JSON Schema 塞进 system 位置，"
        "每次请求都重发——50 个工具、每个 120 token，就是每轮 6000 token 的固定税，"
        "ReAct 跑 10 轮就变成 6 万 token，而其中 98% 的工具跟本次任务毫无关系。"
        "同时「工具越多越选不准」是有实测的：候选从 5 个涨到 50 个，"
        "选择准确率从 95% 掉到 75% 以下（模型要在长列表里做细粒度辨别）。"
        "**token 和准确率是同向恶化的，所以「先路由再调用」是双重收益。**"
        "四条实操："
        "① **意图路由**：先用一次便宜的小模型（或 embedding 分类）把工具集筛到 5~10 个，"
        "再带着这撮候选做正式调用——路由本身只要 300 token，省下几千；"
        "② **限制轮数**：`max_steps` 不只是防死循环，直接决定成本上界；"
        "第 4 轮还没结论的任务，通常缺的是信息而不是更多轮次；"
        "③ **工具粒度要粗**：`get_user` + `get_user_orders` + `get_user_address` 三个工具"
        "不如一个 `query_user(field)`——工具数是成本，参数才是灵活性；"
        "④ **观察结果要截断**：工具返回的 JSON 动辄几千 token，"
        "只把模型需要的字段投影出来（`jq` 式裁剪），比压缩工具描述有用得多。"
    ),
}


# ============================================================================
# ai/ai-ch09 · 一千张图，五天才能生成完
# ----------------------------------------------------------------------------
# 教学点：扩散采样时间 = 步数 × 每步前向。像素空间 512² 每步 200ms，
# 1000 步 = 200 秒/张；潜空间把分辨率降到 64²，每步 15ms。
# 蒸馏（DDIM/一致性模型）把步数降到 20。
# ============================================================================
ai_ch09 = {
    "kind": "sandbox",
    "title": "一千张图，五天才能生成完",
    "brief": (
        "扩散模型的生成时间 = 采样步数 × 每步前向。像素空间 512×512 的 UNet "
        "每步约 200ms，标准 DDPM 要 1000 步 → 200 秒一张，一千张就是 55 小时，"
        "按 3 元/卡时算是 166 元。而潜空间扩散把 512² 压到 64² 再做，"
        "每步只要 15ms；再叠上蒸馏到 20 步，单张 0.3 秒。"
    ),
    "params": [
        {"key": "steps", "label": "采样步数", "min": 20, "max": 1000, "step": 20, "value": 1000},
        {"key": "mode", "label": "生成方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["像素空间 DDPM", "潜空间 LDM（同样步数）", "潜空间 + 蒸馏 20 步"]},
        {"key": "batch", "label": "批大小", "min": 1, "max": 16, "step": 1, "value": 1},
        {"key": "imagesK", "label": "要生成多少（千张）", "min": 1, "max": 20, "step": 1, "value": 1},
    ],
    "metrics": [
        {"key": "stepMs", "label": "每步前向耗时", "expr": "if(mode == 0, 200, 15)", "unit": "ms", "fmt": "int"},
        {"key": "realSteps", "label": "实际采样步数", "expr": "if(mode == 2, 20, steps)", "unit": "步", "fmt": "int"},
        {"key": "perImageS", "label": "单张耗时", "expr": "stepMs * realSteps / 1000", "unit": "秒", "fmt": "fix2"},
        {"key": "totalH", "label": "总耗时", "expr": "imagesK * 1000 * perImageS / 3600 / batch", "unit": "小时", "fmt": "fix2"},
        # 显存：模型 14GB 上下 + 激活随 batch 线性涨
        {"key": "vramGB", "label": "显存占用", "expr": "if(mode == 0, 20 + batch * 6, 6 + batch * 2)", "unit": "GB", "fmt": "int"},
        {"key": "costYuan", "label": "算力成本", "expr": "totalH * 3", "unit": "元", "fmt": "int"},
        {"key": "speedup", "label": "相对像素空间 DDPM 提速", "expr": "200 * steps / (stepMs * realSteps)", "unit": "×", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：步数太少会明显掉质量（DDIM 最少 20 步，采样步数本身要够）
        {"expr": "steps >= 100", "label": "采样步数 ≥100（步数太少画质崩）"},
        {"expr": "imagesK >= 1", "label": "至少生成 1000 张（批量任务才谈得上成本）"},
        # 上限：单张延迟
        {"expr": "perImageS <= 16", "label": "单张 ≤16 秒"},
        {"expr": "totalH <= 6", "label": "总耗时 ≤6 小时（一个晚上跑完）"},
        # 上限：显存（单卡 24GB）
        {"expr": "vramGB <= 23", "label": "显存 ≤23GB（单卡 24GB）"},
    ],
    "insight": (
        "扩散模型的推理成本是**步数 × 单步前向**，两个因子各有各的解法："
        "**减步数**（DDIM 20~50 步、DPM-Solver 10~20 步、一致性模型 1~4 步）"
        "和**减单步开销**（把 512² 的像素空间压到 64² 的潜空间，"
        "前向计算量按面积降 64 倍）。**两者正交，可以叠乘**："
        "像素空间 1000 步 = 200 秒/张；潜空间同步数 15 秒；再蒸馏到 20 步 = 0.3 秒——"
        "**666 倍**，从「一千张要两天」变成「五分钟」。"
        "这条路线的代价要说清："
        "① **潜空间有损**：VAE 编解码会丢掉高频细节，文字和小脸容易糊（所以有 SDXL 的双文本编码器、"
        "以及「潜空间 + 高分辨率精修」两段式）；"
        "② **步数不能无限压**：DDIM 低于 20 步结构开始崩，蒸馏模型（LCM/Turbo）用 4 步的代价是"
        "多样性和细节都变差；"
        "③ **批大小受显存硬限**：batch 翻倍吞吐接近翻倍，但激活显存线性涨，"
        "超了就 OOM——**先算显存再定 batch，比调采样器更立竿见影**；"
        "④ **评估别只看 FID**：FID 对模糊、对模式坍塌都不敏感，"
        "生成任务一定要人眼看 + 任务指标（OCR 准确率、下游分类精度）。"
    ),
}


# ============================================================================
# ai/ai-ch11 · batch=1 跑 7B，十万请求要八张卡
# ----------------------------------------------------------------------------
# 教学点：单请求解码是 memory-bound，batch=1 时 GPU 算力大量空闲；
# 批处理把吞吐抬高十几倍，但 KV cache 显存随 batch 线性增长，有个上限。
# ============================================================================
ai_ch11 = {
    "kind": "sandbox",
    "title": "batch=1 跑 7B，十万请求要八张卡",
    "brief": (
        "自回归解码每生成一个 token 都要把 14GB 的权重从显存读一遍，"
        "batch=1 时 GPU 的算力单元基本在空转：一个 token 31ms，吞吐 32 tok/s。"
        "一天 10 万次请求、每次输出 200 token，需要 231 tok/s——要 8 张卡。"
        "批处理能把吞吐抬到 348 tok/s，但 KV cache 显存随 batch 线性涨，"
        "batch 开到 32 就 OOM 了。"
    ),
    "params": [
        {"key": "batch", "label": "批大小（并发请求）", "min": 1, "max": 32, "step": 1, "value": 1},
        {"key": "promptTokens", "label": "输入长度", "min": 200, "max": 4000, "step": 200, "value": 800},
        {"key": "outTokens", "label": "输出长度", "min": 50, "max": 1000, "step": 50, "value": 200},
        {"key": "reqK", "label": "每天请求数（千）", "min": 10, "max": 1000, "step": 10, "value": 100},
    ],
    "metrics": [
        # 解码一步：权重读取 30ms + 每请求 1ms 的注意力开销
        {"key": "stepMs", "label": "每 token 耗时", "expr": "30 + batch", "unit": "ms", "fmt": "int"},
        {"key": "genS", "label": "单请求生成耗时", "expr": "outTokens * stepMs / 1000", "unit": "秒", "fmt": "fix2"},
        # 吞吐：batch × 输出 token / 生成时间
        {"key": "tps", "label": "单卡吞吐", "expr": "batch * outTokens / (outTokens * stepMs / 1000)", "unit": "token/s", "fmt": "int"},
        {"key": "needTps", "label": "需要的吞吐", "expr": "reqK * 1000 * outTokens / 86400", "unit": "token/s", "fmt": "int"},
        {"key": "gpus", "label": "需要几张卡", "expr": "ceil(needTps / (batch * outTokens / (outTokens * stepMs / 1000)))", "unit": "张", "fmt": "int"},
        # KV cache：7B fp16 约 0.5MB/token
        {"key": "kvGB", "label": "KV cache 占用", "expr": "batch * (promptTokens + outTokens) * 5 / 10000", "unit": "GB", "fmt": "fix2"},
        {"key": "vramGB", "label": "总显存", "expr": "14 + batch * (promptTokens + outTokens) * 5 / 10000", "unit": "GB", "fmt": "fix2"},
        # 首 token 延迟：预填 5000 token/s + 批内排队
        {"key": "ttftMs", "label": "首 token 延迟", "expr": "promptTokens * 5 / 100 + batch * 2", "unit": "ms", "fmt": "int"},
        {"key": "costMonth", "label": "每月卡费", "expr": "ceil(needTps / (batch * outTokens / (outTokens * stepMs / 1000))) * 3000", "unit": "元", "fmt": "int"},
    ],
    "checks": [
        {"expr": "reqK >= 50", "label": "每天 ≥5 万次请求（线上服务的真实量级）"},
        # 既定事实：真实请求的输入输出长度，拖小等于换 workload
        {"expr": "promptTokens >= 500", "label": "输入 ≥500 token（带上下文的真实请求）"},
        {"expr": "outTokens >= 200", "label": "输出 ≥200 token"},
        # 上限：卡数
        {"expr": "gpus <= 2", "label": "最多 2 张卡（预算约束）"},
        # 上限：显存（24GB 单卡）
        {"expr": "vramGB <= 23", "label": "显存 ≤23GB（单卡 24GB）"},
        # 上限：首 token 延迟
        {"expr": "ttftMs <= 800", "label": "首 token ≤800ms（交互体验底线）"},
    ],
    "insight": (
        "自回归解码是**访存瓶颈**，不是算力瓶颈：每生成一个 token，"
        "都要把整个模型的权重从 HBM 读进 SM——7B fp16 是 14GB，"
        "A10 的显存带宽约 600GB/s，理论下限 23ms/token，实测 30ms 上下。"
        "这 30ms 里 GPU 的 FMA 单元几乎全空转，**batch=1 是在给显存带宽交保护费**。"
        "批处理把同一时刻的所有请求拼成一个矩阵乘，权重只读一遍就服务 16 个请求："
        "batch=1 吞吐 32 tok/s，batch=16 吞吐 348 tok/s——**10 倍，卡数从 8 张降到 1 张**。"
        "但 batch 有上限，卡在 **KV cache**：每个请求要缓存 `层数 × 2 × 头数 × 维度 × 序列长度` 的 K/V，"
        "7B fp16 约 0.5MB/token，1000 token 上下文就是 0.5GB/请求；"
        "batch=32 时 16GB 的 KV 加上 14GB 权重，24GB 卡直接 OOM。"
        "**所以真正的容量上限不是「能并行多少请求」，是「显存能装下多少 KV」。**"
        "四条实操："
        "① **continuous batching**：不等整批结束，谁先生成完谁退出、新请求立刻补位，"
        "GPU 利用率从 40% 拉到 85% 以上（vLLM/TensorRT-LLM 默认）；"
        "② **PagedAttention**：把 KV cache 按 16 token 的块分页管理，"
        "消除预分配造成的 60%~80% 内部碎片，等效把可用 batch 抬 2~4 倍；"
        "③ **量化省的是显存不是算力**：INT8/INT4 把权重从 14GB 压到 7GB/3.5GB，"
        "腾出的空间全部给 KV cache，batch 能再翻倍；"
        "④ **首 token 与后续 token 要分开看**：prefill 是算力密集（可并行）、"
        "decode 是访存密集（受带宽限），混在一起调度才能两头都喂饱。"
    ),
}


# ============================================================================
# fundamentals/fund-ch12 · 一百个资源、150ms RTT，首屏 3.4 秒
# ----------------------------------------------------------------------------
# 教学点：首屏 = (握手 RTT + 并发轮次 × RTT) + 传输。
# HTTP/1.1 六连接跑 100 个资源要 17 轮；HTTP/2 多路复用 1 轮；
# TLS 1.3 比 1.2 少一次往返；CDN 把 RTT 从 150ms 压到 20ms。
# 另外 HTTP/1.1 的队头阻塞会把长尾放大 3 倍。
# ============================================================================
fund_ch12 = {
    "kind": "sandbox",
    "title": "一百个资源、150ms RTT，首屏 3.4 秒",
    "brief": (
        "跨区域用户 RTT 150ms。HTTP/1.1 下浏览器对同一域名只开 6 个连接，"
        "100 个资源要排 17 轮：握手 4 个 RTT（DNS + TCP + TLS 1.2 两次）加上 17 轮，"
        "光在等网络上就 3.15 秒，而数据传输只要 240ms。"
        "HTTP/2 多路复用把 17 轮压成 1 轮，TLS 1.3 再省一次往返，CDN 把 RTT 降到 20ms。"
        "另外 HTTP/1.1 的队头阻塞会让长尾放大 3 倍——平均值好看不代表用户不骂。"
    ),
    "params": [
        {"key": "rttMs", "label": "到服务器的 RTT", "min": 20, "max": 300, "step": 10, "value": 150},
        {"key": "assets", "label": "首屏资源数", "min": 10, "max": 300, "step": 10, "value": 100},
        {"key": "proto", "label": "HTTP 版本", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["HTTP/1.1（6 连接）", "HTTP/2（单连接多路复用）", "HTTP/3 over QUIC"]},
        {"key": "tls", "label": "TLS 版本", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["TLS 1.2（2 RTT）", "TLS 1.3（1 RTT）"]},
        {"key": "cdn", "label": "是否用 CDN", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["源站直连", "CDN 边缘节点"]},
    ],
    "metrics": [
        {"key": "effRtt", "label": "实际 RTT", "expr": "if(cdn == 1, 20, rttMs)", "unit": "ms", "fmt": "int"},
        # 握手：DNS 1 + TCP 1 + TLS；QUIC 把 TCP+TLS 合成 1 次
        {"key": "handshakeRtt", "label": "握手往返数", "expr": "if(proto == 2, 2, 1 + 1 + if(tls == 0, 2, 1))", "unit": "RTT", "fmt": "int"},
        # 并发轮次：H1.1 6 连接串行；H2/H3 单连接多路复用
        {"key": "connRtt", "label": "资源并发轮次", "expr": "if(proto == 0, ceil(assets / 6), ceil(assets / 100))", "unit": "RTT", "fmt": "int"},
        # 3MB 资源在 100Mbps 上
        {"key": "payloadMs", "label": "数据传输", "expr": "240", "unit": "ms", "fmt": "int"},
        {"key": "totalMs", "label": "首屏耗时", "expr": "(handshakeRtt + connRtt) * effRtt + payloadMs", "unit": "ms", "fmt": "int"},
        {"key": "ttfbMs", "label": "首字节时间", "expr": "handshakeRtt * effRtt", "unit": "ms", "fmt": "int"},
        # 队头阻塞：H1.1 一条连接上一个慢资源会挡住后面所有请求
        {"key": "p95Ms", "label": "p95 耗时", "expr": "if(proto == 0, totalMs * 3, if(proto == 1, totalMs * 11 / 10, totalMs * 105 / 100))", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        {"expr": "rttMs >= 100", "label": "RTT ≥100ms（跨区域用户的真实网络）"},
        {"expr": "assets >= 50", "label": "首屏至少 50 个资源（现代前端的常态）"},
        # 上限：首屏
        {"expr": "totalMs <= 1000", "label": "首屏 ≤1 秒"},
        # 上限：长尾（H1.1 的队头阻塞会把平均值骗过去）
        {"expr": "p95Ms <= 1200", "label": "p95 ≤1.2 秒"},
    ],
    "insight": (
        "首屏时间能拆成两台加法：**握手 RTT 数 + 资源并发轮次**，各自乘网络往返。"
        "HTTP/1.1 的模型是「6 个连接、连接内串行」：100 个资源要 17 轮，"
        "每轮一个 RTT，150ms 的 RTT 就是 2.55 秒——**这些时间全在等网络，一个字节都还没传**。"
        "握手更贵：DNS 1 次 + TCP 1 次 + TLS 1.2 两次 = 4 个 RTT；"
        "TLS 1.3 把密钥交换压进第一次往返（1-RTT，会话恢复还能 0-RTT），省一半。"
        "HTTP/2 的多路复用把 N 个请求切成帧塞进**一条**连接，17 轮变 1 轮；"
        "HTTP/3 再用 QUIC 把 TCP 与 TLS 握手合并，连队头阻塞（TCP 层的丢包重传）都绕开了。"
        "**为什么还要看 p95**：HTTP/1.1 下一条连接上有个慢资源（大图、慢接口），"
        "它后面的所有请求都得排队——平均耗时可能还行，p95 直接翻三倍。"
        "四条实操："
        "① **先升级协议再优化别的**：H2 + TLS 1.3 是零成本的（服务端配置 + 客户端早就支持），"
        "跨区域用户的收益最大；"
        "② **CDN 治的是 RTT 本身**：150ms → 20ms，所有轮次一起打折，"
        "和协议升级是乘数关系（不是二选一）；"
        "③ **减少资源数是更根本的解**：打包、代码分割、雪碧图、字体子集化，"
        "`assets` 从 100 降到 30，轮次直接砍到 5；"
        "④ **排查链路要分段计时**：`curl -w '@curl-format.txt'` 看 "
        "`time_namelookup`（DNS）/ `time_connect`（TCP）/ `time_appconnect`（TLS）/ "
        "`time_starttransfer`（TTFB）四段，才知道慢在哪一环——"
        "DNS 慢就上 HTTPDNS/预解析，握手慢就上连接复用/QUIC，TTFB 慢就是服务端的事了。"
    ),
}


# ============================================================================
# ml/ml-ch07 · 一百万用户算全量相似度，3.6TB
# ----------------------------------------------------------------------------
# 教学点：user-based CF 的用户相似度矩阵是 U²，100 万用户 = 3.6TB、5×10^11 对；
# item-based 全量也是 I²。工程解法是只保留每个物品的 TopN 相似（截断），
# 或者换矩阵分解（只存 U×K + I×K 的隐向量）。
# ============================================================================
ml_ch07 = {
    "kind": "sandbox",
    "title": "一百万用户算全量相似度，3.6TB",
    "brief": (
        "user-based 协同过滤要给每两个用户算相似度：100 万用户是 5×10^11 个用户对，"
        "相似度矩阵 3.6TB，一天算不完。item-based 换了个方向，但 100 万物品全量"
        "也是同样的量级。工程上的两条出路：每个物品只保留 Top200 相似邻居"
        "（1.5GB），或者直接换矩阵分解，只存用户×隐向量 + 物品×隐向量（0.5GB）。"
    ),
    "params": [
        {"key": "usersW", "label": "用户数（万）", "min": 10, "max": 500, "step": 10, "value": 100},
        {"key": "itemsW", "label": "物品数（万）", "min": 10, "max": 100, "step": 10, "value": 100},
        {"key": "algo", "label": "召回算法", "min": 0, "max": 3, "step": 1, "value": 0,
         "labels": ["user-CF 全量相似度", "item-CF 全量相似度", "item-CF 只留 Top200 邻居", "矩阵分解 ALS"]},
        {"key": "factors", "label": "隐向量维度 K", "min": 16, "max": 256, "step": 16, "value": 64},
    ],
    "metrics": [
        {"key": "users", "label": "用户数", "expr": "usersW * 10000", "unit": "人", "fmt": "int"},
        {"key": "items", "label": "物品数", "expr": "itemsW * 10000", "unit": "个", "fmt": "int"},
        # 要算的相似度对数
        {"key": "pairs", "label": "要算的相似度对", "expr": "if(algo == 0, users * users / 2, if(algo == 1, items * items / 2, if(algo == 2, items * 200, (users + items) * 30)))", "unit": "对", "fmt": "int"},
        # 相似度矩阵体积（T B）
        {"key": "simTB", "label": "相似度矩阵体积", "expr": "if(algo == 0, users * users * 4 / 1099511627776, if(algo == 1, items * items * 4 / 1099511627776, if(algo == 2, items * 200 * 8 / 1073741824 / 1024, 0)))", "unit": "TB", "fmt": "fix2"},
        # 隐向量：U×K + I×K 的 float32
        {"key": "mfGB", "label": "隐向量占用", "expr": "if(algo == 3, (users + items) * factors * 4 / 1073741824, 0)", "unit": "GB", "fmt": "fix2"},
        {"key": "memGB", "label": "总内存", "expr": "simTB * 1024 + mfGB", "unit": "GB", "fmt": "int"},
        # 按 1000 万对/秒
        {"key": "trainMin", "label": "离线计算耗时", "expr": "pairs / 10000000 / 60", "unit": "分钟", "fmt": "fix2"},
        {"key": "diskGB", "label": "落盘体积", "expr": "simTB * 1024 + mfGB", "unit": "GB", "fmt": "int"},
    ],
    "checks": [
        {"expr": "usersW >= 50", "label": "至少 50 万用户（真实平台量级）"},
        {"expr": "itemsW >= 50", "label": "至少 50 万物品"},
        # 上限：内存
        {"expr": "memGB <= 16", "label": "常驻内存 ≤16GB"},
        # 上限：离线计算
        {"expr": "trainMin <= 60", "label": "离线计算 ≤60 分钟（要能每天跑）"},
        # 下限：隐向量维度太低表达不了偏好
        {"expr": "factors >= 32", "label": "隐向量维度 ≥32（再低表达力不够）"},
    ],
    "insight": (
        "协同过滤的第一笔账是**用户对的数量**：`U(U-1)/2`。"
        "1 万用户 5000 万对还能算，100 万用户就是 **5×10^11 对**——"
        "按每秒 1000 万对也要 14 小时，相似度矩阵 3.6TB 根本存不下。"
        "**这不是「优化一下」能解决的，是复杂度不可行**。"
        "三条出路，各有代价："
        "① **item-based + TopN 截断**：物品数通常比用户数小一个量级，"
        "而且「相似物品」是稳定的——离线算好每个物品的 Top200 邻居存下来（1.5GB），"
        "在线查表即可。代价是新品/长尾物品邻居稀疏，冷启动更严重；"
        "② **矩阵分解**：把 U×I 分解成 `U×K` 和 `I×K`（K=32~128），"
        "内存从 TB 降到 GB，还能泛化到没共现过的用户-物品对。"
        "但 ALS/SGD 是**非凸**优化，对隐式反馈和负采样敏感，冷启动仍然要靠内容特征补；"
        "③ **向量召回 + ANN**：把隐向量塞进 Faiss/HNSW，在线 topK 检索 O(log N)，"
        "这是工业界的标准形态（双塔 + ANN）。"
        "还有两条容易被忽略的："
        "④ **均值归一化是必需品**：有人打分永远 4 分、有人永远 3 分，"
        "不减掉用户偏置，相似度会被「打分尺度」而不是「品味」主导；"
        "⑤ **评估别只看 RMSE**：评分预测准不等于排序好，"
        "线上要看 Recall@K / NDCG，还要看**覆盖率与热门偏差**——"
        "推荐系统把 80% 流量给头部 5% 物品，是协同过滤的结构性偏差。"
    ),
}


MODULES = {
    "tooling/tool-ch01": tool_ch01,
    "tooling/tool-ch02": tool_ch02,
    "tooling/tool-ch03": tool_ch03,
    "tooling/tool-ch04": tool_ch04,
    "tooling/tool-ch05": tool_ch05,
    "ai/ai-ch05": ai_ch05,
    "ai/ai-ch06": ai_ch06,
    "ai/ai-ch07": ai_ch07,
    "ai/ai-ch09": ai_ch09,
    "ai/ai-ch11": ai_ch11,
    "fundamentals/fund-ch12": fund_ch12,
    "ml/ml-ch07": ml_ch07,
}


def main() -> int:
    """读取 labs.json → 写入 12 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<24} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
