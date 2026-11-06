# -*- coding: utf-8 -*-
"""批次十二：fullstack 十五章 sandbox。

为什么是这十五章
---------------
fullstack 多章在教材里偏「视角 / 最佳实践清单」，但每章都能提炼出一笔可算的账：

  fs-ch01    100KB 响应 × 1000 QPS：明文 97MB/s 带宽，gzip 后 14MB/s
  fs-ch02    1000 个节点循环里读写交替：1000 次强制同步重排，2000ms 卡死
  fs-ch03    100ms 轮询：每秒 10 次空转请求，推送后 0 次
  fs-ch04    500MB 文件 fs.readFile：内存峰值 500MB，流式 64KB
  fs-ch05    第 1000 页 OFFSET 深翻页：扫描 10000 行，游标只扫 10 行
  fs-ch06    8 位密码：明文/快哈希瞬间破，bcrypt 每秒 10 次要几百年
  fs-ch07    1000 节点状态放顶层：任意子更新整树 diff，下沉后只 20 节点
  fs-ch08    单阶段镜像含 JDK：720MB，多阶段 distroless 7MB
  fs-ch09    TS 泛型擦除：20 种类型 0 额外体积，C++ 模板每类型 3KB
  fs-ch10    500 次渲染直接调 heavyCalc：重算 500 次，computed 只 5 次
  fs-ch11    事务包住 5 次 RPC：持锁 505ms 占用连接，短事务 5ms
  fs-ch12    3 跳微服务：本次请求多 8.4ms 网络开销，单体 0
  fs-ch13    倒金字塔 300 e2e：一次回归 25 分钟，金字塔 5.5 分钟
  fs-ch14    逐 token flush：1000 个网络小包，按 8 批量 125 包
  fs-ch15    100 协程各 +1000 无锁：丢 40% 更新，atomic 后 0 丢失

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限（小规模怎么配都对，没教学意义）。
2. 默认值 = 真实事故配置。
3. 场景事实参数用 `==` / 单边界锁死，否则拖到极端就能通关。
4. `if(c,a,b)` 急切求值 → 分支内除法保证除数非零常量。
5. fmt 只认 int / fix2 / pct。
6. 判据阈值留 5% 以上余量；被引用的指标必须定义在前面。
7. 除零风险：所有除以参数的地方，分母都取常量或 max(...,1)。

写盘必须 indent=1 + newline="\\n"；只替换本章 sandbox、保留 debug 等其它模块。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# fullstack/fs-ch01 · 100KB 响应不压缩，带宽打满
# ----------------------------------------------------------------------------
# 教学点：HTTP 响应体（JSON/HTML）常常 100KB 上下，明文发送时
# 1000 QPS = 97MB/s 出带宽，单台机器网卡就打满；gzip 后约 15KB，省 85%。
# ============================================================================
fs_ch01 = {
    "kind": "sandbox",
    "title": "100KB 响应不压缩，带宽打满",
    "brief": (
        "一个列表接口返回 100KB 的 JSON，线上 1000 QPS。明文发出去就是 97MB/s 的出带宽，"
        "单机千兆网卡直接打满、P99 抖动。把响应体大小、QPS 和是否压缩拖一拖，"
        "看 gzip 把带宽压到什么程度。"
    ),
    "params": [
        {"key": "payloadKB", "label": "单响应体大小", "min": 80, "max": 512, "step": 10, "value": 100},
        {"key": "qps", "label": "请求速率", "min": 500, "max": 5000, "step": 50, "value": 1000},
        {"key": "gzip", "label": "是否压缩", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["明文发送（无 Content-Encoding）", "gzip 压缩后"]},
    ],
    "metrics": [
        {"key": "ratio", "label": "压缩比", "expr": "if(gzip == 1, 0.15, 1)", "unit": "×", "fmt": "fix2"},
        {"key": "rawMB", "label": "每秒原始带宽", "expr": "payloadKB * qps / 1024", "unit": "MB/s", "fmt": "int"},
        {"key": "perReqMB", "label": "单响应实际传输", "expr": "payloadKB * ratio / 1024", "unit": "MB", "fmt": "fix2"},
        {"key": "outMB", "label": "每秒实际带宽", "expr": "rawMB * ratio", "unit": "MB/s", "fmt": "int"},
    ],
    "checks": [
        {"expr": "payloadKB >= 80", "label": "响应体就是 100KB 上下（列表/详情页的真实体量）"},
        {"expr": "qps >= 500", "label": "至少 500 QPS（线上接口的常态）"},
        {"expr": "outMB <= 30", "label": "实际带宽 ≤30MB/s（千兆网卡要留余量）"},
        {"expr": "perReqMB <= 0.05", "label": "单响应 ≤50KB（与大小无关的单位量判据）"},
    ],
    "insight": (
        "HTTP 的 `Content-Encoding: gzip`（或 br/zstd）是性价比最高的优化之一："
        "JSON/HTML 这类文本压缩比常常 5~8×，上面的 100KB 响应 gzip 后约 15KB。"
        "97MB/s 的明文带宽降到 14MB/s，单机直接多出 6 倍余量。"
        "注意三件事：① **反向代理（Nginx）统一开启**最省心，应用层不必每个接口自己压；"
        "② **已经压缩过的内容别再压**（图片、视频 gzip 反而变大），按 Content-Type 白名单；"
        "③ 压缩有 CPU 成本，极高 QPS 下可以 `gzip_static` 预压缩或交给 CDN 边缘做。"
    ),
}


# ============================================================================
# fullstack/fs-ch02 · 循环里读写交替，强制同步重排
# ----------------------------------------------------------------------------
# 教学点：JS 里读 offsetHeight 会强制浏览器立即 flush 之前的写并做一次布局（reflow）。
# 循环里「写样式→读 offsetHeight→写→读」交替，每轮都触发一次同步重排。
# ============================================================================
fs_ch02 = {
    "kind": "sandbox",
    "title": "循环里读写交替，强制同步重排",
    "brief": (
        "要批量更新 1000 个节点的样式并读取它们的位置。如果循环里「写一行样式、读一次 offsetHeight」交替，"
        "浏览器每次读都会强制先做一遍布局（reflow），1000 个节点就是 1000 次重排。"
        "把节点数和处理模式拖一拖，看卡顿是怎么来的。"
    ),
    "params": [
        {"key": "nodes", "label": "节点数", "min": 100, "max": 5000, "step": 100, "value": 1000},
        {"key": "pattern", "label": "读写模式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["循环里读写交替（每次读 offsetHeight 都强制重排）",
                    "先批量读、再批量写（只 1 次重排）"]},
    ],
    "metrics": [
        {"key": "reflows", "label": "重排次数", "expr": "if(pattern == 0, nodes, 1)", "unit": "次", "fmt": "int"},
        {"key": "costMs", "label": "布局耗时", "expr": "reflows * 2", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        {"expr": "nodes >= 500", "label": "至少 500 个节点（列表 / 表格的真实规模）"},
        {"expr": "reflows <= 5", "label": "重排 ≤5 次（读写分离的硬判据）"},
        {"expr": "costMs <= 50", "label": "布局耗时 ≤50ms（16ms 一帧，50ms 已掉 3 帧但可接受）"},
    ],
    "insight": (
        "浏览器的渲染是「JS 执行 → 样式计算 → 布局 → 绘制 → 合成」的流水线，"
        "**读几何属性（offsetHeight / offsetTop / getBoundingClientRect / 某些 getComputedStyle）"
        "会强制浏览器先 flush 掉之前积攒的写、立即跑一遍布局**——这就是 layout thrashing。"
        "循环里「写→读→写→读」等于每轮都重排一次。三条解法："
        "① **读写分离**：先把所有要读的值一次性读出来，再统一写；"
        "② **用 DocumentFragment / 脱离文档的节点**做批量改动，只触发一次回流；"
        "③ **fast path**：改 class 而不是逐条改 style，交给 CSS 引擎批量处理。"
        "现代框架（React/Vue）的虚拟 DOM diff 也是在 commit 阶段统一写，本质就是避免读写交替。"
    ),
}


# ============================================================================
# fullstack/fs-ch03 · 100ms 轮询，空转请求
# ----------------------------------------------------------------------------
# 教学点：用 setInterval 每 100ms 去问「有新数据吗」，绝大多数时候答案是没有，
# 等于每秒 10 次空转请求；用 SSE/WebSocket 服务端主动推送后归零。
# ============================================================================
fs_ch03 = {
    "kind": "sandbox",
    "title": "100ms 轮询，空转请求",
    "brief": (
        "前端想实时看订单状态，用 setInterval 每 100ms 打一次接口问「变了吗」。绝大多数请求答案都是「没变」，"
        "等于每秒 10 次空转请求打到后端。把轮询间隔和是否用推送拖一拖，看空转量。"
    ),
    "params": [
        {"key": "pollMs", "label": "轮询间隔", "min": 100, "max": 5000, "step": 100, "value": 100},
        {"key": "usePush", "label": "数据获取方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["客户端定时轮询", "服务端事件推送（SSE / WebSocket）"]},
    ],
    "metrics": [
        {"key": "pollsPerSec", "label": "每秒请求数", "expr": "if(usePush == 1, 0, 1000 / pollMs)", "unit": "次/s", "fmt": "int"},
        {"key": "wastedPerMin", "label": "每分钟空转请求", "expr": "pollsPerSec * 60", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        {"expr": "pollMs <= 1000", "label": "轮询间隔不会太长（默认 100ms 很频繁）"},
        {"expr": "pollsPerSec <= 0.2", "label": "每秒请求 ≤0.2（推送后归零的硬判据）"},
        {"expr": "wastedPerMin <= 12", "label": "每分钟空转 ≤12 次"},
    ],
    "insight": (
        "轮询（polling）是最容易写的实时方案，但代价是**「询问」和「变化」解耦后的空转**："
        "间隔短了空转多、间隔长了延迟高，永远在两难之间。三种更优的替代："
        "① **长轮询（long-polling）**：请求挂起直到有变化才返回，把空转合并掉；"
        "② **SSE（Server-Sent Events）**：服务端单向推送，一条长连接复用；"
        "③ **WebSocket**：双向全双工，适合聊天 / 协同编辑。"
        "取舍点：读多写少、延迟敏感 → SSE；需要客户端主动发 → WebSocket；"
        "纯粹为了「知道变了」却用高频轮询，是典型的资源浪费。"
    ),
}


# ============================================================================
# fullstack/fs-ch04 · Node 一次性 readFile 大文件
# ----------------------------------------------------------------------------
# 教学点：fs.readFile 把整个文件读进内存，500MB 文件 = 500MB 内存峰值（OOM 风险）；
# createReadStream 分块（64KB）峰值只有 64KB，还能配合背压（backpressure）。
# ============================================================================
fs_ch04 = {
    "kind": "sandbox",
    "title": "Node 一次性 readFile 大文件",
    "brief": (
        "要处理一个 500MB 的导出文件。fs.readFile 会把它整个读进内存再回调，"
        "内存峰值就是 500MB——容器内存限制 256MB 时直接 OOM 被 kill。换成流分块读，峰值只有 64KB。"
        "把文件大小和读取方式拖一拖，看内存峰值。"
    ),
    "params": [
        {"key": "fileMB", "label": "文件大小", "min": 100, "max": 2000, "step": 50, "value": 500},
        {"key": "streaming", "label": "读取方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["fs.readFile 一次性读进内存", "fs.createReadStream 分块（64KB）"]},
    ],
    "metrics": [
        {"key": "peakMB", "label": "内存峰值", "expr": "if(streaming == 1, 64, fileMB)", "unit": "MB", "fmt": "int"},
        {"key": "chunks", "label": "数据块数", "expr": "if(streaming == 1, fileMB * 1024 / 64, 1)", "unit": "块", "fmt": "int"},
    ],
    "checks": [
        {"expr": "fileMB >= 200", "label": "至少 200MB（日志 / 导出文件的真实体量）"},
        {"expr": "peakMB <= 128", "label": "内存峰值 ≤128MB（容器常见限制）"},
    ],
    "insight": (
        "Node 是单进程，**一次性把大文件读进内存既撑爆 V8 堆又加长 GC 停顿**。"
        "Stream 的核心价值是**边读边处理 + 背压**：下游消费慢时，上游自动暂停推数据，"
        "内存峰值恒定在「一个 chunk」大小（默认 64KB）。两个要点："
        "① 用 `stream.pipe(dest)` 或 `for await (const chunk of readable)` 而不是 readFile；"
        "② 网络 / 磁盘 / 压缩（zlib）之间用 pipe 串联，Node 会自动在两端速率不匹配时做背压，"
        "不会堆积。需要随机访问大文件时再考虑 mmap（Node 用 `fs.open` + `read` 按 offset 读）。"
    ),
}


# ============================================================================
# fullstack/fs-ch05 · 深度分页 OFFSET 深翻页
# ----------------------------------------------------------------------------
# 教学点：LIMIT 10 OFFSET 100000，数据库仍要从头扫描并丢弃前 100000 行。
# 游标分页（WHERE id > lastId LIMIT 10）无论翻多深都只扫 10 行。
# ============================================================================
fs_ch05 = {
    "kind": "sandbox",
    "title": "深度分页 OFFSET 深翻页",
    "brief": (
        "一个千万行的订单表，前端「下一页」翻到第 1000 页。LIMIT 10 OFFSET 100000 看起来只取 10 行，"
        "但数据库得先扫出前 100000 行再丢弃，越翻越慢。把总行数、页码和分页方式拖一拖，看扫描行数。"
    ),
    "params": [
        {"key": "totalRows", "label": "表总行数", "min": 100000, "max": 10000000, "step": 500000, "value": 5000000},
        {"key": "page", "label": "翻到第几页", "min": 1, "max": 1000, "step": 20, "value": 1000},
        {"key": "perPage", "label": "每页条数", "min": 10, "max": 100, "step": 10, "value": 10},
        {"key": "cursor", "label": "分页方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["OFFSET 深翻页", "游标分页（WHERE id > lastId）"]},
    ],
    "metrics": [
        {"key": "offset", "label": "OFFSET 值", "expr": "page * perPage", "unit": "行", "fmt": "int"},
        {"key": "scanned", "label": "本次扫描行数", "expr": "if(cursor == 1, perPage, offset + perPage)", "unit": "行", "fmt": "int"},
        {"key": "scanMB", "label": "本次扫描数据量", "expr": "scanned * 200 / 1048576", "unit": "MB", "fmt": "fix2"},
    ],
    "checks": [
        {"expr": "totalRows >= 1000000", "label": "至少千万级大表（深翻页才会痛）"},
        {"expr": "page >= 100", "label": "确实翻到了很深的页"},
        {"expr": "scanned <= 100", "label": "本次扫描 ≤100 行（游标分页的硬判据）"},
        {"expr": "scanMB <= 0.05", "label": "扫描数据 ≤50KB（与页码无关的单位量）"},
    ],
    "insight": (
        "`OFFSET` 是「跳过前 N 行」，数据库**没有捷径**，必须真的先把前 N 行从存储读出来（即使丢弃）。"
        "翻到第 1000 页就是扫 10000 行，深翻页随着页码线性变慢，还会因 MVCC 反复读旧版本。"
        "游标分页（keyset pagination）用索引列做范围：`WHERE id > :lastId ORDER BY id LIMIT 10`，"
        "无论翻多深都只扫一页，**前提是排序列有索引且稳定**（所以别用 `ORDER BY rand()`）。"
        "限制：游标分页不支持「跳到第 N 页」的随机跳转，UI 上用「无限滚动 / 上一页下一页」替代页码输入即可。"
    ),
}


# ============================================================================
# fullstack/fs-ch06 · 密码存储：明文 vs bcrypt
# ----------------------------------------------------------------------------
# 教学点：明文/快哈希（MD5/SHA）每秒可算十亿次，8 位密码瞬间枚举完；
# bcrypt 故意慢（每秒约 10 次），同样密码要几百年。
# ============================================================================
fs_ch06 = {
    "kind": "sandbox",
    "title": "密码存储：明文 vs bcrypt",
    "brief": (
        "用户密码只有 8 位（大小写+数字）。如果数据库明文存、或只存一个 MD5，"
        "泄露后被 GPU 每秒枚举十亿次，几秒就全破。换成 bcrypt（故意慢哈希）后，"
        "同样一个密码要算几百年。把存储方案和密码长度拖一拖，看破解时间。"
    ),
    "params": [
        {"key": "scheme", "label": "存储方案", "min": 0, "max": 3, "step": 1, "value": 0,
         "labels": ["明文", "快哈希（MD5 / SHA-1）", "加盐快哈希", "bcrypt 慢哈希"]},
        {"key": "pwdLen", "label": "密码长度", "min": 6, "max": 16, "step": 1, "value": 8},
    ],
    "metrics": [
        {"key": "guessesPerSec", "label": "每秒可试密码数",
         "expr": "if(scheme == 0, 1000000000000, if(scheme == 1, 1000000000, if(scheme == 2, 1000000000, 10)))",
         "unit": "次/s", "fmt": "int"},
        {"key": "keyspace", "label": "密码空间", "expr": "pow(62, pwdLen)", "unit": "种", "fmt": "int"},
        {"key": "crackSec", "label": "破解耗时（平均）", "expr": "keyspace / guessesPerSec / 2", "unit": "秒", "fmt": "int"},
        {"key": "crackYears", "label": "破解耗时（年）", "expr": "crackSec / 31536000", "unit": "年", "fmt": "int"},
    ],
    "checks": [
        {"expr": "pwdLen <= 10", "label": "用户就是弱密码（≤10 位才是真实风险）"},
        {"expr": "crackYears >= 1000", "label": "破解 ≥1000 年（bcrypt 的硬判据）"},
    ],
    "insight": (
        "密码存储的第一原则：**永远别存明文，也别用快哈希（MD5/SHA-1/SHA-256）**。 "
        "快哈希的设计目标是「快」，正好让攻击者的 GPU 农场每秒枚举几十亿个候选。"
        "正确做法是**慢哈希 + 每用户盐**：bcrypt / scrypt / Argon2 故意把单次计算做慢"
        "（bcrypt 默认约 100ms/次，且可随硬件升级调 cost），并给每个用户随机盐，"
        "让「彩虹表」失效、相同密码也存出不同摘要。"
        "现代框架（Django/Spring Security/Passlib）默认就走这套；"
        "如果还在手写 `md5(password)`，这是最需要优先修的安全债。"
    ),
}


# ============================================================================
# fullstack/fs-ch07 · 状态放顶层，整树重渲染
# ----------------------------------------------------------------------------
# 教学点：把共享 state 放在组件树顶层，任意一个子组件更新 state，
# 整棵子树都会被标记为「需要 diff」，1000 节点全量比对；状态下沉到最小公共祖先后只有 20 节点参与。
# ============================================================================
fs_ch07 = {
    "kind": "sandbox",
    "title": "状态放顶层，整树重渲染",
    "brief": (
        "一个 1000 节点的后台页面，把共享状态放在最顶层。任意子组件更新这个状态，"
        "整棵组件树都会被标记为需要重新渲染（diff），1000 个节点全量比对。"
        "把状态下沉到最小公共祖先、或用 store 的局部订阅后，每次更新只波及 20 个节点。"
        "把节点数和状态位置拖一拖，看单次更新参与渲染的节点数。"
    ),
    "params": [
        {"key": "nodes", "label": "组件节点数", "min": 100, "max": 5000, "step": 100, "value": 1000},
        {"key": "localState", "label": "状态位置", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["状态放顶层（任意子更新触发整树 diff）",
                    "状态下沉到最小公共祖先 / store 局部订阅"]},
    ],
    "metrics": [
        {"key": "renderNodes", "label": "每次更新参与渲染节点", "expr": "if(localState == 1, 20, nodes)", "unit": "个", "fmt": "int"},
        {"key": "renderMs", "label": "单次更新耗时", "expr": "renderNodes * 0.05", "unit": "ms", "fmt": "fix2"},
    ],
    "checks": [
        {"expr": "nodes >= 500", "label": "至少 500 个节点（真实页面组件树体量）"},
        {"expr": "renderNodes <= 100", "label": "每次更新 ≤100 节点（状态下沉的硬判据）"},
        {"expr": "renderMs <= 10", "label": "单次更新 ≤10ms"},
    ],
    "insight": (
        "「状态放得越高，重渲染范围越大」是 UI 性能的第一性原理（React/Vue 都适用）。"
        "顶层 state 一旦变化，其所有后代默认都会进入 reconcile/diff 队列——即使它们的 props 没变，"
        "纯函数 diff 本身也要花时间。三条解法："
        "① **状态下沉**：把 state 移到「真正用到它的最小公共祖先」，父组件不持有它就不会被牵连；"
        "② **记忆化**：React.memo / Vue 的静态提升 + v-memo，让 props 未变的子节点跳过 diff；"
        "③ **细粒度订阅**：状态库（Redux/Zustand/Pinia）按 selector 订阅，只有用到该字段的组件才更新。"
        "经验法则：**状态离使用它的组件越近越好**。"
    ),
}


# ============================================================================
# fullstack/fs-ch08 · Docker 单阶段镜像含构建工具
# ----------------------------------------------------------------------------
# 教学点：单阶段 Dockerfile 把 JDK/gcc/node 全打进最终镜像，体积 720MB；
# 多阶段只 COPY 运行时产物 + distroless 基础镜像，7MB。
# ============================================================================
fs_ch08 = {
    "kind": "sandbox",
    "title": "Docker 单阶段镜像含构建工具",
    "brief": (
        "一个 Java 服务，单阶段 Dockerfile 直接在最终镜像里 `apt install openjdk`，"
        "再 COPY 源码编译。最终镜像既含 JDK（~600MB）又含 ubuntu 基础（~70MB），"
        "体积 720MB，传输和启动都慢。多阶段只把 jar 拷进 distroless，7MB。"
        "把是否含构建工具链和基础镜像拖一拖，看最终体积。"
    ),
    "params": [
        {"key": "buildTool", "label": "最终镜像是否含构建工具", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["最终镜像含构建工具（gcc / JDK / node）", "多阶段只 COPY 运行时产物"]},
        {"key": "baseImg", "label": "基础镜像", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["ubuntu（~70MB）", "debian-slim（~30MB）", "distroless / alpine（~5MB）"]},
    ],
    "metrics": [
        {"key": "baseMB", "label": "基础镜像体积", "expr": "if(baseImg == 0, 70, if(baseImg == 1, 30, 5))", "unit": "MB", "fmt": "int"},
        {"key": "toolchainMB", "label": "构建工具链体积", "expr": "if(buildTool == 1, 600, 0)", "unit": "MB", "fmt": "int"},
        {"key": "depsMB", "label": "运行时依赖体积", "expr": "if(baseImg == 2, 2, 50)", "unit": "MB", "fmt": "int"},
        {"key": "imageMB", "label": "最终镜像体积", "expr": "baseMB + toolchainMB + depsMB", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        {"expr": "imageMB <= 100", "label": "最终镜像 ≤100MB（单阶段 ubuntu 720MB 会爆）"},
        {"expr": "toolchainMB == 0", "label": "运行时镜像不含构建工具（多阶段的硬判据）"},
    ],
    "insight": (
        "Docker 镜像分层的妙处不止缓存，**多阶段构建（multi-stage）还能让「构建环境」和「运行环境」彻底分离**："
        "第一阶段用完整的 SDK 镜像编译，第二阶段从一个极小的运行时镜像（distroless / alpine）"
        "只 `COPY` 编译产物。收益有三：① 体积从几百 MB 降到几 MB，拉取和冷启动都快；"
        "② 攻击面骤减（运行镜像里没有 shell / 包管理器 / 编译器）；"
        "③ 构建工具链的 CVE 不会带进生产镜像。"
        "另外 `COPY . .` 要写在 `RUN npm install` **之后**、依赖文件单独 COPY 在前，才能命中 layer 缓存——"
        "这条和镜像体积同样重要。"
    ),
}


# ============================================================================
# fullstack/fs-ch09 · TS 泛型擦除 vs C++ 模板膨胀
# ----------------------------------------------------------------------------
# 教学点：TypeScript 泛型在编译后完全擦除（0 额外产物），C++ 模板每用一种类型就实例化一份代码。
# 20 种类型的容器，TS 产物不变，C++ 多 60KB。
# ============================================================================
fs_ch09 = {
    "kind": "sandbox",
    "title": "TS 泛型擦除 vs C++ 模板膨胀",
    "brief": (
        "一个泛型容器 `Box<T>` 被 20 种类型实例化。很多人以为「泛型会像 C++ 模板那样每种类型生成一份代码」，"
        "其实 TypeScript 的泛型在编译成 JS 后**完全擦除**——`Box<number>` 和 `Box<string>` 是同一份 JS。"
        "把类型数量和语言拖一拖，看额外产物体积。"
    ),
    "params": [
        {"key": "types", "label": "泛型实例化类型数", "min": 2, "max": 50, "step": 1, "value": 20},
        {"key": "lang", "label": "语言", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["TypeScript（泛型擦除）", "C++（模板每类型实例化一份）"]},
    ],
    "metrics": [
        {"key": "perTypeKB", "label": "每类型额外体积", "expr": "if(lang == 0, 0, 3)", "unit": "KB", "fmt": "int"},
        {"key": "extraKB", "label": "额外产物", "expr": "types * perTypeKB", "unit": "KB", "fmt": "int"},
        {"key": "extraMB", "label": "额外产物（MB）", "expr": "extraKB / 1024", "unit": "MB", "fmt": "fix2"},
    ],
    "checks": [
        {"expr": "types >= 10", "label": "至少被 10 种类型使用（泛型容器的真实处境）"},
        {"expr": "extraMB == 0", "label": "TS 编译后泛型 0 额外体积（擦除的硬判据）"},
    ],
    "insight": (
        "这是 TS 和 C++ 泛型**最本质的区别**：C++ 模板是图灵完备的「代码生成器」，**每用一种类型就真编译出一份机器码**"
        "（所以 `std::vector<int>` 和 `std::vector<double>` 是两份代码，模板元编程能跑会显著增加二进制体积）；"
        "而 TypeScript 的类型系统**只在编译期存在**，类型信息（包括泛型参数）在 emit 成 JS 时被整体擦除，"
        "运行时只有一份无类型的 JS——所以「泛型会膨胀产物」在 TS 里是**误解**。"
        "代价是：TS 无法在运行时做基于类型的分发（需要 `typeof` / `instanceof` / 自定义 type guard 来窄化），"
        "也不能像 Java 那样 `T.class`。理解擦除才能正确设计运行时行为。"
    ),
}


# ============================================================================
# fullstack/fs-ch10 · 模板里直接调重函数 vs computed
# ----------------------------------------------------------------------------
# 教学点：模板里写 `{{ heavyCalc() }}` 会在每次组件重新渲染时都重算（500 次）；
# 用 computed 后只在依赖变化时重算（依赖只变了 5 次）。
# ============================================================================
fs_ch10 = {
    "kind": "sandbox",
    "title": "模板里直接调重函数 vs computed",
    "brief": (
        "一个组件的模板里写 `{{ heavyCalc() }}`，父组件因为别的状态频繁重渲染，"
        "这个函数就被跟着调了 500 次（每次 3ms = 1.5 秒纯浪费）。"
        "改成 computed 后，它只在自己依赖的数据变化时重算——而依赖其实很少变（5 次）。"
        "把渲染次数、依赖变化次数和计算方式拖一拖，看重算次数。"
    ),
    "params": [
        {"key": "renders", "label": "组件渲染次数", "min": 10, "max": 1000, "step": 10, "value": 500},
        {"key": "depsChange", "label": "依赖变化次数", "min": 1, "max": 50, "step": 1, "value": 5},
        {"key": "useComputed", "label": "计算方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["模板里直接调 heavyCalc()（每次渲染都重算）", "用 computed（依赖不变不重算）"]},
    ],
    "metrics": [
        {"key": "calcRuns", "label": "重算次数", "expr": "if(useComputed == 1, depsChange, renders)", "unit": "次", "fmt": "int"},
        {"key": "calcMs", "label": "计算总耗时", "expr": "calcRuns * 3", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        {"expr": "renders >= 200", "label": "至少 200 次渲染（列表频繁重渲染的真实场景）"},
        {"expr": "depsChange <= 10", "label": "依赖很少变（只变了 5 次）"},
        {"expr": "calcRuns <= 20", "label": "重算 ≤20 次（computed 缓存的硬判据）"},
        {"expr": "calcMs <= 60", "label": "计算总耗时 ≤60ms"},
    ],
    "insight": (
        "响应式框架里「在模板 / 渲染函数里直接调用重计算」是典型的性能反模式："
        "渲染是**高频且常常被迫触发**的（父组件更新、兄弟状态变化都可能让本组件重渲染），"
        "而重计算本可以**只在它真正依赖的数据变化时**跑一次。"
        "computed（Vue）/ useMemo（React）/ memoized selector（状态库）做的就是这件事："
        "① 记录依赖 → ② 依赖不变时返回缓存值、跳过计算 → ③ 只在依赖变时重算。"
        "注意 computed 不是万能药：**依赖要选得准**，把不相关的变量塞进依赖数组会让缓存频繁失效，"
        "等于又退化成每次重算。原则是「依赖 = 函数真正读到的响应式变量」。"
    ),
}


# ============================================================================
# fullstack/fs-ch11 · 事务边界放在 Controller
# ----------------------------------------------------------------------------
# 教学点：把事务开在 Controller 层、包住整个 HTTP 处理（含 5 次 RPC/IO），
# 事务持锁时间 = 5×100ms = 505ms，连接长时间被占用；短事务只在 Service 内部 = 5ms。
# ============================================================================
fs_ch11 = {
    "kind": "sandbox",
    "title": "事务边界放在 Controller",
    "brief": (
        "一个下单接口，把数据库事务开在 Controller，包住了整个 HTTP 处理流程——"
        "其中还嵌着 5 次对其它微服务的 RPC 调用（每次 100ms）。事务一直持着数据库连接和行锁，"
        "505ms 里连接池被占着，并发一高就耗尽。把事务范围、RPC 次数和耗时拖一拖，看持锁时间。"
    ),
    "params": [
        {"key": "inTxnCalls", "label": "事务内的远程调用数", "min": 0, "max": 10, "step": 1, "value": 5},
        {"key": "txnScope", "label": "事务范围", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["事务包住整个 HTTP 处理（含 RPC / IO）", "事务只在 Service 内部（短事务）"]},
        {"key": "rpcMs", "label": "单次 RPC 耗时", "min": 10, "max": 500, "step": 10, "value": 100},
    ],
    "metrics": [
        {"key": "holdingMs", "label": "事务持锁时间", "expr": "if(txnScope == 1, 5, inTxnCalls * rpcMs + 5)", "unit": "ms", "fmt": "int"},
        {"key": "connHeld", "label": "连接被占用", "expr": "holdingMs", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        {"expr": "inTxnCalls >= 3", "label": "业务确实跨多个服务（≥3 次远程调用）"},
        {"expr": "rpcMs >= 50", "label": "单次 RPC 至少 50ms（网络调用真实耗时）"},
        {"expr": "holdingMs <= 50", "label": "事务持锁 ≤50ms（短事务的硬判据）"},
    ],
    "insight": (
        "事务边界是后端最容易被放错的地方。**事务应该尽可能短、只包住真正的写操作**，"
        "决不该把 RPC / HTTP 调用 / 耗时计算裹在里面——这些都在占用数据库连接（连接池是稀缺资源）"
        "和数据库锁，并发稍高连接池就耗尽、请求开始排队。"
        "正确的分层是：Controller 负责协议转换与编排，**事务开在 Service 方法内部**，"
        "进入 Service 前先完成所有远程调用拿到数据，Service 里只做「读-算-写」的短事务。"
        "跨服务的「分布式事务」更不该用长事务硬撑，而是用 Saga / 本地消息表 / 最终一致。"
    ),
}


# ============================================================================
# fullstack/fs-ch12 · 微服务跨服务调用开销
# ----------------------------------------------------------------------------
# 教学点：一次业务请求跨 3 个微服务，每跳一次 RPC 都多 1ms 网络 + 序列化成本；
# 单体进程内方法调用是 0 额外延迟。承认这笔开销、按需拆分，而不是无脑微服务化。
# ============================================================================
fs_ch12 = {
    "kind": "sandbox",
    "title": "微服务跨服务调用开销",
    "brief": (
        "一个「下单」请求在微服务架构里要依次穿过 3 个服务（用户→库存→订单），"
        "每跳一次 RPC 都多约 2ms（1ms 网络往返 + 序列化/反序列化）。本次请求凭空多 8.4ms 延迟。"
        "单体架构里这只是一次进程内方法调用，延迟为 0。把跨服务跳数、架构和序列化体量拖一拖，看额外延迟。"
    ),
    "params": [
        {"key": "svcHops", "label": "本次请求跨服务跳数", "min": 1, "max": 10, "step": 1, "value": 3},
        {"key": "arch", "label": "架构", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["单体（进程内方法调用）", "微服务（每跳一次 RPC）"]},
        {"key": "serializeKB", "label": "每次 RPC 序列化数据", "min": 1, "max": 64, "step": 1, "value": 8},
    ],
    "metrics": [
        {"key": "perHopMs", "label": "每跳额外延迟", "expr": "if(arch == 0, 0, 2 + serializeKB * 0.1)", "unit": "ms", "fmt": "fix2"},
        {"key": "extraLatency", "label": "本次请求额外延迟", "expr": "svcHops * perHopMs", "unit": "ms", "fmt": "fix2"},
    ],
    "checks": [
        {"expr": "svcHops >= 2", "label": "业务确实跨多个服务"},
        {"expr": "extraLatency <= 5", "label": "额外延迟 ≤5ms（默认微服务 8.4ms 过不了，需减少跨服务跳数 / 合并调用）"},
    ],
    "insight": (
        "「微服务」不是免费的：**每一次跨进程调用都比进程内方法调用多出网络往返 + 序列化/反序列化 + 重试/超时治理的成本**。"
        "翻过几道服务边界后，原本 1ms 的调用可能变成 5~10ms，且任何一跳抖动都会放大成端到端延迟。"
        "这章的核心不是「微服务好 / 单体好」，而是**何时拆**："
        "当团队结构（康威定律）、独立部署粒度、技术异构需求真的出现时，付出的延迟与运维代价才值回票价；"
        "否则「为了微服务而微服务」只会在延迟和排障复杂度上双倍买单。"
        "降低开销的工程手段：合并相邻的同步 RPC、对非实时结果用异步事件、用 gRPC/protobuf 压缩序列化。"
    ),
}


# ============================================================================
# fullstack/fs-ch13 · 测试金字塔倒挂
# ----------------------------------------------------------------------------
# 教学点：倒金字塔（300 个 e2e 测试，每个 5s）一次回归 25 分钟；
# 金字塔（大量单测 + 少量 e2e）5.5 分钟，且单测稳定可并行。
# ============================================================================
fs_ch13 = {
    "kind": "sandbox",
    "title": "测试金字塔倒挂",
    "brief": (
        "一个项目写了 300 个端到端（e2e）测试、每个跑 5 秒，单元测试却只有 1000 个。"
        "一次完整回归要把浏览器拉起来跑 25 分钟，开发等得抓狂，还动不动 flaky。"
        "把 e2e 数量、单测数量以及各自的耗时拖一拖，看一次回归总时长。"
    ),
    "params": [
        {"key": "e2eCount", "label": "e2e 测试数", "min": 0, "max": 500, "step": 10, "value": 300},
        {"key": "unitCount", "label": "单元测试数", "min": 0, "max": 10000, "step": 100, "value": 1000},
    ],
    "metrics": [
        # e2e 每个 5s、单测每个 10ms（常量，不放参数以免组合爆炸）
        {"key": "e2eTotalS", "label": "e2e 总耗时", "expr": "e2eCount * 5", "unit": "秒", "fmt": "int"},
        {"key": "unitTotalS", "label": "单测总耗时", "expr": "unitCount * 10 / 1000", "unit": "秒", "fmt": "int"},
        {"key": "totalMin", "label": "一次回归总时长", "expr": "(e2eTotalS + unitTotalS) / 60", "unit": "分钟", "fmt": "fix2"},
        {"key": "e2eRatio", "label": "e2e 占比", "expr": "if(e2eCount + unitCount > 0, e2eCount * 100 / max(e2eCount + unitCount, 1), 0)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        {"expr": "e2eCount >= 50", "label": "确实堆了大量 e2e（这是要改的现状）"},
        {"expr": "e2eRatio <= 10", "label": "e2e 占比 ≤10%（金字塔的硬判据）"},
        {"expr": "totalMin <= 15", "label": "一次回归 ≤15 分钟"},
    ],
    "insight": (
        "经典的**测试金字塔**：底层大量快、稳、便宜的单元测试，中层少量集成测试，顶层极少脆弱又慢的 e2e。"
        "倒挂（e2e 一大堆、单测寥寥）会同时踩三个坑：① e2e 慢（拉浏览器/建库/走网络），"
        "回归时间随用例数线性膨胀；② e2e 易 flaky（环境/时序任一抖动就红），降低团队对测试红绿的信任；"
        "③ 失败时定位难——e2e 只告诉你「端到端挂了」，得自己往下挖。"
        "纠偏：把能落单测的逻辑（算法、校验、状态机）下沉到底层，e2e 只覆盖「关键用户旅程的冒烟」；"
        "单测用真实实现而非满屏 mock，才能既快又真。"
    ),
}


# ============================================================================
# fullstack/fs-ch14 · 流式响应逐 token 推送
# ----------------------------------------------------------------------------
# 教学点：LLM 流式输出如果每生成一个 token 就立即 flush，1000 个 token = 1000 个网络小包；
# 按 ~8 token 批量缓冲再发，125 个包，网络小包开销降 8 倍。
# ============================================================================
fs_ch14 = {
    "kind": "sandbox",
    "title": "流式响应逐 token 推送",
    "brief": (
        "一个 LLM 网关要把生成的回复流式推给客户端。如果每产出一个 token 就立即 flush 一次 HTTP chunk，"
        "1000 个 token 就是 1000 个极小的网络包（每包几字节），TCP/HTTP 头部开销被放大。"
        "改成每攒够约 8 个 token 再发一次，包数降 8 倍。把 token 数、每包 flush 间隔和是否缓冲拖一拖，看网络包数。"
    ),
    "params": [
        {"key": "tokens", "label": "本次响应 token 数", "min": 100, "max": 4000, "step": 100, "value": 1000},
        {"key": "flushEvery", "label": "每多少 token flush 一次", "min": 1, "max": 64, "step": 1, "value": 1},
        {"key": "buffered", "label": "缓冲策略", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["每生成 1 个 token 立即 flush", "按 ~8 token 批量缓冲再发"]},
    ],
    "metrics": [
        {"key": "packets", "label": "网络包数", "expr": "if(buffered == 1, tokens / 8, tokens / flushEvery)", "unit": "个", "fmt": "int"},
        {"key": "perPacketTokens", "label": "每包 token 数", "expr": "if(buffered == 1, 8, flushEvery)", "unit": "个", "fmt": "int"},
    ],
    "checks": [
        {"expr": "tokens >= 500", "label": "至少 500 个 token（长回复的真实体量）"},
        {"expr": "packets <= 200", "label": "网络包 ≤200 个（批量缓冲的硬判据）"},
        {"expr": "perPacketTokens >= 4", "label": "每包 ≥4 个 token（别发极小的包）"},
    ],
    "insight": (
        "流式（streaming）把「等全部生成完再返回」变成「边生成边推」，首字延迟（TTFT）大幅下降、体验更好；"
        "但**推送的粒度**有讲究：每产出 1 个 token 就 flush 一次，等于把 TCP 包和 HTTP chunk 头部的开销放大了几百倍，"
        "在网关 / CDN / 客户端还会触发过多的小包调度。"
        "工程上普遍做法是**攒一小批（~8 个 token，或按 ~50ms 时间窗）再 flush 一次**，"
        "既保持「打字机」体感，又把包数降一个数量级。"
        "另一个关联坑是**背压**：客户端消费慢时网关要停推，否则缓冲堆积把内存吃掉；"
        "以及 `Content-Type: text/event-stream` 下有些代理会缓冲，需要 `X-Accel-Buffering: no` 关掉。"
    ),
}


# ============================================================================
# fullstack/fs-ch15 · 无锁并发计数丢更新
# ----------------------------------------------------------------------------
# 教学点：100 个 goroutine 各对共享变量 +1000，无锁时 `counter++` 不是原子的（读-改-写竞争），
# 最终值远小于期望；用 atomic / mutex 保护后精确等于期望。
# ============================================================================
fs_ch15 = {
    "kind": "sandbox",
    "title": "无锁并发计数丢更新",
    "brief": (
        "用 Go 起 100 个 goroutine，每个对同一个共享计数器自增 1000 次。"
        "如果直接 `counter++`（没有锁、没有 atomic），自增在 CPU 上是「读-改-写」三步，"
        "多个 goroutine 会读到同一个旧值一起写回，互相覆盖——最终计数远小于 100×1000。"
        "把协程数、每协程次数和保护方式拖一拖，看最终值是否精确。"
    ),
    "params": [
        {"key": "goroutines", "label": "并发 goroutine 数", "min": 10, "max": 1000, "step": 10, "value": 100},
        {"key": "perG", "label": "每协程自增次数", "min": 100, "max": 10000, "step": 100, "value": 1000},
        {"key": "useMutex", "label": "保护方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["共享变量直接 counter++（无锁）", "用 atomic / mutex 保护"]},
    ],
    "metrics": [
        {"key": "expected", "label": "期望最终值", "expr": "goroutines * perG", "unit": "次", "fmt": "int"},
        {"key": "lost", "label": "丢失的更新", "expr": "if(useMutex == 1, 0, round(expected * 0.4))", "unit": "次", "fmt": "int"},
        {"key": "final", "label": "实际最终值", "expr": "expected - lost", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        {"expr": "goroutines >= 50", "label": "至少 50 个并发协程（真实并发场景）"},
        {"expr": "perG >= 500", "label": "每协程至少自增 500 次"},
        {"expr": "final == expected", "label": "最终值 == 期望值（加锁的硬判据）"},
    ],
    "insight": (
        "`counter++` 看起来是一行，在机器码里是「从内存读 → 寄存器 +1 → 写回内存」三步，"
        "**根本不是原子的**。两个 goroutine 同时读到 42、都算成 43、都写回 43——一次自增就这么丢了。"
        "高并发下丢失比例可观（上面默认丢 40%）。四种修法按场景选："
        "① **sync/atomic**（整数/指针计数器最轻量，无锁但用 CPU 原子指令）；"
        "② **mutex**（保护任意临界区，代价是串行化）；"
        "③ **channel** 把计数收拢到一个 owner goroutine（「不要通过共享内存来通信」的 Go 哲学）；"
        "④ 如果每个协程只管自己的局部计数，最后再汇总（避免共享），最优雅。"
        "写完记得 `go run -race` 跑一遍，race detector 能直接揪出这类数据竞争。"
    ),
}


MODULES = {
    "fullstack/fs-ch01": fs_ch01,
    "fullstack/fs-ch02": fs_ch02,
    "fullstack/fs-ch03": fs_ch03,
    "fullstack/fs-ch04": fs_ch04,
    "fullstack/fs-ch05": fs_ch05,
    "fullstack/fs-ch06": fs_ch06,
    "fullstack/fs-ch07": fs_ch07,
    "fullstack/fs-ch08": fs_ch08,
    "fullstack/fs-ch09": fs_ch09,
    "fullstack/fs-ch10": fs_ch10,
    "fullstack/fs-ch11": fs_ch11,
    "fullstack/fs-ch12": fs_ch12,
    "fullstack/fs-ch13": fs_ch13,
    "fullstack/fs-ch14": fs_ch14,
    "fullstack/fs-ch15": fs_ch15,
}


def main() -> int:
    """读取 labs.json → 写入 15 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<22} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
