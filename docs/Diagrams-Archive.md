# 图表归档 · 按逻辑学习链条

> 本档案汇集 CppMind 各章 concept 中用 ```` ```text ```` 围栏绘制的 ASCII/Unicode 图表，用于复习时按「由浅入深、由基础到工程」的顺序串成一条学习链。
> 顺序遵循：① 基础学科（DS/计组/计网/OS）② 全栈工程 ③ AI 工程。


## 一、基础学科（数据结构 / 计组 / 计网 / 操作系统）

### fund-ch01 · 顺序表与链表：内存布局决定的性能差异

**来源**：`fund-ch01/concept/01-array-vs-list.md`

```text
数组:    [ 0 ][ 1 ][ 2 ][ 3 ][ 4 ]   连续内存，随机访问 O(1)，插入/删除 O(n)
链表:    ●─▶●─▶●─▶●─▶∅            节点分散存 data+next，访问 O(n)，头插/头删 O(1)
双链表:  ◀─●─▶◀─●─▶◀─●─▶          每个节点多一个 prev，删除已知节点 O(1)
```

### fund-ch02 · 栈：LIFO 与函数调用栈的硬件支撑

**来源**：`fund-ch02/concept/01-stack-and-call-frame.md`

```text
栈(Stack, LIFO):   push▶[ A ][ B ][ C ]◀pop     后进先出，用数组/链表尾作栈顶
队列(Queue, FIFO): enq▶[ A ][ B ][ C ]◀deq     先进先出，需头指针+尾指针
循环队列:  尾到头绕回，用 (rear+1)%cap==front 判满
串匹配:  KMP 靠失配函数 next[] 跳过已匹配前缀，避免主串指针回退
```

### fund-ch03 · 树的遍历：三种序的本质与递归的非递归改写

**来源**：`fund-ch03/concept/01-tree-traversal.md`

```text
          [ 1 ]
         /     \
      [ 2 ]   [ 3 ]
     /   \       \
  [ 4 ] [ 5 ]   [ 6 ]
先序(根左右): 1 2 4 5 3 6
中序(左根右): 4 2 5 1 3 6
后序(左右根): 4 5 2 6 3 1
层序(BFS)   : 1 2 3 4 5 6     二叉搜索树靠「中序有序」支撑查找 O(log n)
```

### fund-ch04 · 图的存储结构：邻接矩阵、邻接表与十字链表

**来源**：`fund-ch04/concept/01-graph-storage.md`

```text
邻接表(稀疏图省空间):   0 → [1, 2]   1 → [2]   2 → []
邻接矩阵(稠密图查边快): 2D 布尔表，查边 O(1)，空间 O(V²)
遍历:  BFS 用队列(按层)   DFS 用栈或递归(一条路走到底)
最短路径: Dijkstra(非负权) / Floyd(全源)   最小生成树: Prim / Kruskal
```

### fund-ch05 · 线性表上的查找：顺序、折半与分块

**来源**：`fund-ch05/concept/01-linear-search.md`

```text
key ──hash()──▶ 槽位 h
冲突解决:
  链地址法:  槽 h ─▶ [node]─▶[node]─▶∅      (Java HashMap 做法)
  开放寻址:  h, h+1, h+2 ... 线性探测       (探测序列填满整个表)
负载因子 α = 元素数 / 槽数；α↑ → 冲突↑ → 查找从 O(1) 退化到 O(n)
```

### fund-ch06 · 排序总览：内部排序分类与复杂度/稳定性对照表

**来源**：`fund-ch06/concept/01-sort-taxonomy.md`

```text
        最好      平均      最坏     稳定   核心思想
插入排序  O(n)     O(n²)    O(n²)    稳    边扫描边把元素插到已排序区
快速排序  O(nlogn) O(nlogn) O(n²)   不稳  分治+基准，最左/右作枢轴
归并排序  O(nlogn) O(nlogn) O(nlogn) 稳   分治+合并，额外 O(n) 空间
堆排序    O(nlogn) O(nlogn) O(nlogn) 不稳  建堆后反复取堆顶
计数/桶/基: 非比较排序，可突破 O(nlogn) 下界
```

### fund-ch07 · 四种机器数：原码、反码、补码、移码

**来源**：`fund-ch07/concept/01-four-machine-number-representations.md`

```text
原码:   [符号][数值]          0 和 -0 两种表示，加减要判符号，麻烦
补码:   负数 = 取反 + 1       统一用加法器做减法，只有一种 0，溢出可检
浮点 IEEE754(32位): [1位S][8位阶E][23位尾M]  值 = (-1)^S × 1.M × 2^(E-127)
  阶码全0/全1 用作 0 / 非规 / ±∞ / NaN
```

### fund-ch08 · 存储层次与局部性原理

**来源**：`fund-ch08/concept/01-memory-hierarchy-and-locality.md`

```text
存储层次(越往外越慢越大):
  CPU寄存器 ─ L1 ─ L2 ─ L3 ─ 内存 ─ SSD ─ HDD
CPU 五级流水: 取指 → 译码 → 执行 → 访存 → 写回  (理想吞吐≈单级延迟)
Cache 映射: 直接映射 / 组相联 / 全相联   命中率取决于时间+空间局部性
```

### fund-ch09 · 进程与线程：状态机、PCB 与上下文切换

**来源**：`fund-ch09/concept/01-process-and-thread.md`

```text
进程 = 资源容器(地址空间/文件句柄)   线程 = 进程内的执行流
PCB ──拥有──▶ 若干 TCB
状态机:  就绪 ─▶(调度) 运行 ─▶(时间片到) 就绪
                    │
                    └─▶(等IO) 阻塞 ─▶(IO完成) 就绪
调度: FCFS / 时间片轮转 / 优先级 / 多级反馈队列
```

### fund-ch10 · 连续分配与碎片：首次/最佳/最坏适应到底差在哪

**来源**：`fund-ch10/concept/01-contiguous-allocation-and-fragmentation.md`

```text
虚拟地址 ─MMU─▶ 页表 ─▶ 物理页帧       分页让进程以为独占内存
页面置换: FIFO / LRU / Clock   缺页率高 → 频繁换入换出(颠簸)
文件: inode ─▶ 数据块链表            IO 缓冲/缓存减少 syscall 与磁盘次数
```

### fund-ch11 · 分层模型与封装：每一层到底加了什么

**来源**：`fund-ch11/concept/01-layer-models-and-encapsulation.md`

```text
应用层  HTTP / DNS / FTP
传输层  TCP(可靠,三次握手)  UDP(不可靠,低延迟)
网络层  IP(路由,无连接)     ICMP
链路层  帧 / MAC / ARP / 交换机
TCP 三次握手建连:  SYN → SYN+ACK → ACK
TCP 四次挥手断连:  FIN → ACK → FIN → ACK
```

### fund-ch12 · HTTP 的演进：1.1 → 2 → 3

**来源**：`fund-ch12/concept/01-http-evolution.md`

```text
浏览器 ─DNS解析─▶ IP ─TCP握手─▶ TLS ─HTTP请求─▶ 服务器 ─响应─▶ 渲染
排错自底向上:
  ping       (网络层连通)
  traceroute (路径哪跳丢包)
  curl -v    (应用层请求/响应头)
  RTT / 丢包率 / 重传 定位瓶颈
```


## 二、全栈工程（前端 → 后端 → 工程化 → Agent 接缝）

### fs-ch10 · 响应式原理与依赖追踪

**来源**：`fs-ch10/concept/01-reactivity-and-dependency-tracking.md`

```text
   reactive(obj.x)          effect(fn)
        │                        │
        ▼                        ▼
   ┌─────────┐   track()   ┌──────────┐
   │  dep: x  │◀───────────│  active   │  读 obj.x 时把 effect 登记为依赖
   └─────────┘             │  effect   │
        ▲                   └──────────┘
        │   trigger()               │
        └────── obj.x = new ────────┘  写时反向通知 effect 重跑
```

### fs-ch11 · 分层边界与依赖方向

**来源**：`fs-ch11/concept/01-layered-boundaries.md`

```text
   请求 ─▶ Controller ── 只做收口(参数/DTO) ─▶ Service ── 业务 & 事务 ─▶ Repository ──▶ DB
             │                                      │                     │
             └──── DTO ⇄ Entity 转换边界 ────────────┘                Entity/Model
   禁止：Controller 直连 DB / Repository 反向调 Service / 跨层穿透
```

### fs-ch12 · 什么时候该拆：单体到微服务的触发条件与代价

**来源**：`fs-ch12/concept/02-gateway-boundary.md`

```text
   client ─▶ Gateway ──┬─ 路由     ─▶ service A
                       ├─ 鉴权     ─▶ service B
                       ├─ 限流     ─▶ (超阈值则拒绝 429)
                       └─ 聚合(BFF)─▶ 多服务扇出后合并
   网关不管：具体业务校验、DB 连接、领域计算（那是服务的事）
```

### fs-ch13 · 测试金字塔：分层策略与测试替身

**来源**：`fs-ch13/concept/01-test-pyramid.md`

```text
        /\
       /E2E\        ← 少而慢：验端到端关键路径
      /----\
     / 集成 \       ← 中：模块协作、外部依赖
    /------\
   / 单元   \      ← 多而快：基底，占绝大多数
  /----------\
  倒金字塔(反例)：E2E 一堆、单测没几个 → 一改就红、定位慢
```

### fs-ch14 · 流式响应穿过网关：透传、背压与取消

**图 1**（来源：`fs-ch14/concept/01-streaming-through-gateway.md`）

```text
   Agent ──SSE 分块──▶ Gateway ──SSE 分块──▶ 浏览器
     ▲   (cancel)         ▲   (cancel)
     └─────────────────────┘   断线重连用 last-event-id 续传
   网关只透传流，不缓冲整段；背压从下游往上游反压
```

**图 2**（来源：`fs-ch14/concept/03-tool-call-idempotency-and-audit.md`）

```text
   tool call ──callId=abc──▶ 去重表 ──首次──▶ 真正执行 → 结果
      (重试)   callId=abc ──▶ 去重表 ──命中──▶ 直接返回已存结果
   审计日志：callId + 输入哈希 + 输出哈希 → 哈希链，篡改即可检出
```

### fs-ch15 · Goroutine 与 Channel：轻量并发与「不要通过共享内存通信」

**来源**：`fs-ch15/concept/01-goroutine-and-channel.md`

```text
   G(goroutine) ─▶ P(逻辑处理器, 数量≈CPU) ─▶ M(系统线程) ─▶ 核
        │                │
        └──── channel 通信 ──── 代替「共享内存 + 锁」
   「不要通过共享内存来通信，而要通过通信来共享内存」
```


## 三、AI 工程（数据 → 推理部署 → 多模态）

### ai-ch12 · 任务 schema 与指令设计：从一句话需求到可训练样本

**来源**：`ai-ch12/concept/02-synthetic-filter-dedup-contamination.md`

```text
   原始语料 → 规则过滤 → 语义去重 → 训练集污染检测 → 留验隔离 → SFT 训练
                │           │            │              │
              去脏/短/重    SimHash    与评测集      train / valid
                          near-dup     重叠率         / test 分开
```

### ai-ch13 · KV Cache 与分页注意力：显存账、碎片与复用

**来源**：`ai-ch13/concept/01-kv-cache-paged-attention.md`

```text
   请求A: [block0][block1][block2]     物理块池 (PagedAttention)
   请求B: [block0][block3]             block1/2/3 可跨请求复用，不再连续占满
   传统: 每请求预分配最大长度 → 碎片多；分页: 按需取块 → 碎片≈0
```

### ai-ch14 · 图文对齐与表征：CLIP 式对比学习、投影层、跨模态检索

**来源**：`ai-ch14/concept/02-ocr-vlm-pipeline.md`

```text
   图像 → 版面检测(版心/表格) → 文本识别(OCR) → VLM 问答
            │                      │
            └── 失败模式：漏检/错认 ─┘ → 答案幻觉的来源
   成本：识别 + VLM 各算一次；延迟预算要拆成「预处理 / 推理 / 回传」
```


---

> 共归档 **22** 张图表，覆盖 21 章。
