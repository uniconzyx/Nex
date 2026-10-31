# -*- coding: utf-8 -*-
"""
为「更多学科」补详细 ASCII 结构图，并附一句说明（> blockquote），
插入到各章 concept 首文件的 H1 标题之后。

设计要点（对齐前端 markdown.ts 渲染约束）：
  - 图必须放在 ```text 围栏内，前端才会渲染成 <pre class="md-pre">；
  - 说明用 `> ` blockquote 紧跟在图之前，gen_diagrams_data.py 会抽它当 desc；
  - 用 marker（说明首句）做幂等判定，重跑不会重复插入。

覆盖学科：cpp / java / python / database / spring / middleware /
          bigdata / tooling / ml / agent / data
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

# ch -> (subject_dir, marker, caption, art)
# marker 取 caption 首句片段，用于幂等去重
DIAG: dict[str, tuple[str, str, str, str]] = {
    # ---------------- C++ ----------------
    "cpp-ch06": ("cpp", "虚函数表（vtable）是 C++ 多态的运行期核心",
        "虚函数表（vtable）是 C++ 多态的运行期核心：每个含虚函数的类编译期生成一张函数指针表，"
        "对象头部藏一个 vptr 指向它。基类指针调用的虚函数，会在运行期按对象「真实类型」查表分发，"
        "这就是「同一行代码、不同行为」的实现机理。",
        r"""基类 Base { virtual void f(); virtual void g(); }
派生类 Drv  { void f() override;        /* g 沿用 Base */ }

        Base 对象                 Drv 对象
        ┌──────────┐              ┌──────────┐
  vptr─▶│ &Base::f │        vptr─▶│ &Drv::f  │   ← f 被覆盖
        │ &Base::g │              │ &Base::g │   ← g 沿用基类
        └──────────┘              └──────────┘
          vtable(Base)              vtable(Drv)

Base* p = new Drv();
p->f();   // 查 p 的实际 vtable → 调 Drv::f()   （运行期分发）
p->g();   // 查 p 的实际 vtable → 调 Base::g()
代价：一次指针间接寻址 + 缓存不友好；收益：开闭原则、可替换实现。"""),

    "cpp-ch10": ("cpp", "RAII 把「资源生命周期」绑死在「对象作用域」上",
        "RAII 把「资源生命周期」绑死在「对象作用域」上：构造即获取、析构即释放，"
        "离开作用域（无论正常 return 还是抛异常）都会自动回收，是 C++ 防泄漏的基石。三种智能指针"
        "表达三种所有权语义——unique 独占、shared 引用计数、weak 旁观不持有。",
        r"""所有权三态：

  unique_ptr<T>   独占     move 转移，不可拷贝      ── 默认首选
  shared_ptr<T>   共享     引用计数，归零才释放      ── 需共享时
  weak_ptr<T>     旁观     不增计数，lock() 探活     ── 破循环引用

  auto a = make_unique<File>();   // 构造即 open
  { auto b = a; }                // 编译失败：unique 不可拷贝（安全）
  auto s = make_shared<Res>();   // use_count = 1
  weak_ptr<Res> w = s;           // use_count 仍为 1
  if (auto p = w.lock()) { /* 仍活着 */ }   // 防悬垂

RAII 链：锁/文件/连接/内存 全部「栈上对象管堆上资源」，异常安全靠它。"""),

    # ---------------- Java ----------------
    "java-ch08": ("java", "JVM 把内存切成「线程私有」与「线程共享」两大块",
        "JVM 把内存切成「线程私有」与「线程共享」两大块。方法区/元空间存类元信息，堆是对象之家；"
        "GC 主要扫堆，采用分代假设（大部分对象朝生暮死），年轻代用复制算法、老年代用标记-整理。",
        r"""运行时数据区
┌──────────────────────────────────────────────────────┐
│ 线程私有（每线程一份）                                  │
│   程序计数器 │ 虚拟机栈(栈帧/局部变量) │ 本地方法栈     │
├──────────────────────────────────────────────────────┤
│ 线程共享                                              │
│   方法区/元空间（类信息·常量·静态）                     │
│   堆 Heap  ───  GC 主战场                              │
│     ├─ 年轻代 Young: Eden + S0 + S1  (复制算法)        │
│     └─ 老年代 Old:            (标记-整理)              │
└──────────────────────────────────────────────────────┘

对象出生在 Eden → 满触发 Minor GC → 存活进 S0/S1 来回复制
→ 熬过阈值(默认15)进 Old → Old 满触发 Major/Full GC(STW 更久)
GC  Roots: 栈帧局部变量、静态字段、JNI 引用（可达性分析起点）"""),

    "java-ch07": ("java", "线程池用「一个队列 + 一组 worker」解耦任务提交与执行",
        "线程池用「一个阻塞队列 + 一组常驻 worker」解耦「提交任务」与「执行任务」："
        "提交方只丢进队列，worker 循环取任务跑。核心线程保活、队列满再扩容到最大线程、再满则按拒绝策略处理。",
        r"""提交任务 ──▶ [ 队列 BlockingQueue ] ──▶ worker-1 取走执行
                         │                          worker-2 取走执行
                         │                          worker-3 ...
       corePoolSize=2  ↓ maxPoolSize=5
   提交速度 > 消费速度:
     1) 核心线程(2) 全忙 → 2) 任务入队 → 3) 队满 → 4) 扩到最大(5)
     → 仍满 → RejectedExecutionHandler:
        Abort(抛异常) / CallerRuns(调用者自己跑) / Discard / DiscardOldest

   调参口诀：CPU 密集 ≈ 核数；IO 密集 ≈ 核数×(1+等待/计算)"""),

    # ---------------- Python ----------------
    "py-ch07": ("python", "GIL 让 CPython 同一时刻只跑一个字节码线程",
        "GIL（全局解释器锁）让 CPython 同一时刻只在一个线程执行字节码，所以多线程只适合 IO 等待，"
        "真并行要靠多进程；而 asyncio 用「单线程 + 事件循环 + 协程」在 IO 等待时让出控制权，适合高并发 IO。",
        r"""CPU 密集 vs IO 密集 的两条路：

  多线程 threading           asyncio 协程
  ┌─────────────┐           ┌──────────────────────────┐
  │ GIL 串行执行 │           │ 事件循环 event loop        │
  │ T1 ─┐       │           │  await 遇到 IO 就 yield    │
  │ T2 ─┤ 争锁   │           │  coroA ─▶ IO挂起▶ coroB跑  │
  │ T3 ─┘       │           │  单线程切换，零锁开销       │
  └─────────────┘           └──────────────────────────┘
  适合：IO 等待(网络/文件)    适合：海量并发 IO(万级连接)

  多进程 multiprocessing：每进程独立 GIL → 真并行 CPU 密集
  注：GIL 在 IO 阻塞时会释放，故 threading 对 IO 仍有效。"""),

    "py-ch03": ("python", "dict 是「开地址哈希表」，冲突用探测+伪随机再散列",
        "Python dict 是「开地址哈希表」：底层是 entries 数组，每个槽存 hash、key、value。"
        "删除不真删而是打「哑元」标记，插入时复用；负载过高触发扩容并重新散列，查找平均接近 O(1)。",
        r"""dict 内部（简化）
  indices: [None, 0, None, 1, ...]      # 探测链索引
  entries:
    [0] hash=.. key='a' value=1
    [1] hash=.. key='b' value=2
    [2] <dummy>  (被删占位，可被新键覆盖)

  插入 'c': hash(c)%mask 命中槽 → 若 occupied 且 key 不同
          → 按 perturb 伪随机向后探测空/dummy 槽
  查找 'a': 同样探测链，key 相等才命中；遇 dummy 继续；遇空停
  删除 'a': 槽标 dummy（保留探测链不断）

  list/tuple：连续数组，O(1) 索引；set：只存 key 的 hash 表
  copy：浅拷贝共享元素；deepcopy：递归复制嵌套对象"""),

    # ---------------- Database ----------------
    "db-ch03": ("database", "B+树索引把「有序」与「矮树高扇」结合，事务靠 ACID 四性守住正确",
        "B+树索引把「有序性」与「矮树高扇出」结合：所有数据在叶子层串成有序链表，非叶只存路由键，"
        "三层即可索引千万行；事务靠 ACID 四性守住正确，隔离级别用锁/多版本在「并发」与「脏读/幻读」间权衡。",
        r"""B+树（m=3 示意）
        [ 50 ]
       /      \
  [10,30]    [70,90]
   │││        │││
  叶子层有序链表: 10-20-30-40-50-60-70-80-90   ← 真正数据/指针在这
  查找 72：根 50→右 70→叶子 70..90，O(log) 且稳定

  事务 ACID:
   A 原子  全做或全不做（undo log 回滚）
   C 一致  约束不被破坏
   I 隔离  并发互不干扰
   D 持久  commit 后不丢（redo log）

  隔离级别（并发 vs 异常）：
   RU 读未提交 → 脏读     RC 读已提交 → 不可重复读
   RR 可重复读 → 防幻读    Serializable 全串行（最安全最慢）"""),

    "db-ch02": ("database", "三类 Join 的本质是「如何为两边每一行找匹配」",
        "三类 Join 的本质是「如何为左右两边每一行找匹配」。Nested Loop 朴素双循环（小表驱动）；"
        "Hash Join 建哈希表（适合大数据、等值）；Merge Join 先排序再指针合并（已排序时最优）。",
        r"""1) Nested Loop（小表驱动）
   for r in R(out):            # R 小
     for s in S: if r.k==s.k: emit(r,s)
   代价 O(|R|·|S|)；建索引后内表可索引查找

2) Hash Join（大数据·等值）
   build: 对 S 建哈希表 H( key )
   probe: 逐行 r∈R，算 h(r.k) 进 H 找匹配
   代价 O(|R|+|S|)；不适合非等值

3) Merge Join（两边已按连接键排序）
   i=j=0
   while i<|R| and j<|S|:
     if R[i].k==S[j].k: emit; 推进较小的指针
     elif R[i].k < S[j].k: i++
     else: j++
   代价 O(|R|+|S|)，省去排序时最优"""),

    # ---------------- Spring ----------------
    "spring-ch01": ("spring", "IoC 把「对象怎么造、依赖谁」交给容器，而非写死在代码里",
        "IoC（控制反转）把「对象怎么造、依赖谁」交给容器，而非在代码里 new。DI（依赖注入）是落地手段："
        "容器读配置/注解，按类型或名字把依赖「塞进」对象。结果是类之间解耦、可单测、可替换实现。",
        r"""传统： class A { B b = new B(); }   ← A 自己负责 B 的创建（紧耦合）

IoC/DI：
   @Component class B {}
   @Component class A { @Autowired B b; }   ← 容器注入，A 不 new B

容器启动：
   1) 扫描 @Component/@Bean → 建 BeanDefinition 注册表
   2) 按依赖图实例化（先 B 后 A）
   3) 注入：构造器 / 字段(@Autowired) / Setter
   4) 放入单例池，按需取用

好处：A 只声明「我需要 B 的能力」，B 的实现可随时替换/打桩测试。"""),

    "spring-ch03": ("spring", "AOP 用「代理」在目标方法周围织入横切逻辑，业务代码零侵入",
        "AOP 用「代理」在目标方法周围织入横切逻辑（日志、事务、鉴权），业务代码零侵入。"
        "有接口走 JDK 动态代理（实现同一接口），无接口走 CGLIB 子类代理；调用经代理先跑通知再转目标。",
        r"""目标 Bean 被包一层代理：

   调用方 ─▶ [ Proxy 代理 ]
                 │  @Before   (前置：记日志/开事务)
                 │  @Around   (环绕：计时/鉴权，可改参/拦返回)
                 ▼
              [ Target 真实方法 ]
                 │  @AfterReturning / @AfterThrowing
                 ▼
               返回调用方

  代理选型：
   目标实现接口 → JDK 动态代理（同接口）
   目标无接口   → CGLIB 生成子类代理
  执行顺序：环绕前 → 前置 → 目标 → 后置/异常 → 环绕后

  横切关注点（日志/事务/安全）与业务解耦，集中维护。"""),

    # ---------------- Middleware ----------------
    "mw-ch05": ("middleware", "Kafka 用「Topic 分多个 Partition + 多 Replica」同时换来了并发与容错",
        "Kafka 用「一个 Topic 切成多个 Partition（并行单位）+ 每个 Partition 多 Replica（容错单位）」"
        "同时拿到吞吐与高可用：Producer 按 key 哈希落 Partition 保顺序，Consumer Group 每组每 Partition 至多一个消费者。",
        r"""Topic = orders
  Partition-0  [replica: L P F]      ← Leader(L) 在 broker2
  Partition-1  [replica: P F L]      ← Leader 在 broker0
  Partition-2  [replica: F L P]      ← Leader 在 broker1

  Producer: key=user_id → hash → 固定 Partition（同用户有序）
  Consumer Group G:
     C1 消费 P0, P1
     C2 消费 P2          （每 Partition 同组仅 1 消费者）
  再起 C3 → 自动 rebalance 重新分配
  某 broker 挂 → Partition 的 Follower 之一升 Leader，服务不中断

  ISR = 与 Leader 同步的副本集；ack=all 才算写入成功。"""),

    "mw-ch04": ("middleware", "缓存三大经典问题本质是「查不到时往哪去、什么时候失效」",
        "缓存三大经典问题本质是「查不到时往哪去、什么时候失效」：穿透是查不存在的 key 直击库，"
        "击穿是热点 key 突失效瞬间被打穿，雪崩是大量 key 同时过期把库冲垮。解法分别是空值/布隆、单飞/逻辑过期、错峰 TTL。",
        r"""① 缓存穿透：查 db 也没有的 key → 每次都打到库
   解：缓存空值(null,短时TTL) + 布隆过滤器挡非法 key

② 缓存击穿：某个热点 key 突然过期 → 瞬间大量请求穿透过载
   解：互斥单飞(只放1个去查库) + 逻辑过期(异步重建不阻塞)

③ 缓存雪崩：大量 key 同一时刻过期 / Redis 宕机 → 库被冲垮
   解：TTL 加随机抖动错峰 + 多级缓存 + 高可用(集群)

读路径： 请求 → Cache 命中? 返回 : 查 DB → 写回 Cache → 返回
写路径： 更新 DB → 删 Cache(或双删) → 防脏读"""),

    # ---------------- BigData ----------------
    "bd-ch02": ("bigdata", "MapReduce 把「计算」搬近「数据」，靠 Shuffle 归并同 key",
        "MapReduce 把「计算」搬近「数据」，避免搬大盘：Map 在本地切片并行处理，Shuffle 按 key 归并到同 reducer，"
        "Reduce 聚合输出。YARN 负责把任务调度到数据所在的节点，做到「数据不动、计算动」。",
        r"""input 分片 ──▶ Map(本地,并行) ──▶ [ Shuffle: 按 key 分组 ] ──▶ Reduce ──▶ 输出
                 (k1,v1)          partition+sort       (k2, [v2..])
                 (k1,v2)   ─────────────┐
                 (k3,v1)   ───┐         │
                               ▼         ▼
                            reduce0    reduce1
                            k1→聚合    k3→聚合

  Map:  逐行转 (key, value)       例: (word,1)
  Shuffle: 同 key 进同 reducer（网络传输，最贵一步）
  Reduce: 同 key 的 values 聚合    例: word→count

  YARN: ResourceManager 调度，NodeManager 在 DataNode 本地起 Container 跑任务。"""),

    # ---------------- Tooling ----------------
    "tool-ch03": ("tooling", "Git 把版本存成「blob/tree/commit 三类对象」的有向图",
        "Git 把版本存成「blob(文件内容)/tree(目录结构)/commit(快照指针)」三类对象的有向图，"
        "内容寻址（SHA-1 去重）；工作区、暂存区、版本库「三区」是改动流动的三个站点。",
        r"""对象模型（内容寻址）：
  blob   文件内容（与名字无关，同内容同 hash）
  tree   目录：文件名 → blob/tree 的指针
  commit 指向一个 tree + 父 commit + 作者/信息

  三区流动：
   工作区(编辑) ──git add──▶ 暂存区(index) ──git commit──▶ 版本库(.git)
        ▲                                            │
        └──────────── git checkout ──────────────────┘

  分支只是指向 commit 的轻量指针：
    main ─▶ C3 ← C2 ← C1
    feat ─▶ C4 (从 C3 分出)
  merge: 建新 commit 把两历史汇合；rebase: 把提交重放到目标之后（线性）。"""),

    # ---------------- ML ----------------
    "ml-ch03": ("ml", "神经网络训练 = 前向算输出、反向传梯度、优化器更新权重",
        "神经网络训练由三步循环构成：前向（输入经层层加权求和+激活得到预测）、反向（链式法则从损失算每层权重梯度）、"
        "更新（优化器沿负梯度调权）。梯度消失/爆炸、学习率大小是训练稳定性的关键旋钮。",
        r"""前向 (forward):
   z = W·x + b ;  a = σ(z)        逐层传播
   ŷ = softmax(z_last)            多分类输出概率

损失 L = CrossEntropy(ŷ, y_true)

反向 (backward) — 链式法则:
   ∂L/∂W = ∂L/∂a · ∂a/∂z · ∂z/∂W
   从输出层往回，把梯度「分摊」给每层权重

更新 (SGD / Adam):
   W ← W − η · ∂L/∂W             η=学习率

  多分类: 输出层 softmax + 交叉熵；二分类: sigmoid + BCE
  梯度消失: 深层 + sigmoid → 梯度趋零 → 用 ReLU/BatchNorm
  学习率太大震荡、太小慢 → 用自适应(Adam)或 warmup+衰减"""),

    # ---------------- Agent ----------------
    "agent-ch05": ("agent", "RAG 让模型「先查资料再回答」，检索质量决定回答上限",
        "RAG（检索增强生成）让模型「先查资料再回答」：把知识切块向量化建库，提问时先检索最相关片段，"
        "拼接进 prompt 再生成。它把「参数记忆」变成「可更新的外部知识」，幻觉与时效问题大幅缓解——但上限由检索质量决定。",
        r"""知识入库（离线）:
   文档 → 切片 chunk → Embedding 模型 → 向量库(如 Milvus)

在线问答（实时）:
   用户问题 → Embedding → 向量检索 Top-K 片段
        │
        ▼
   拼装 Prompt: [系统: 只依据下列资料] + [资料:K个片段] + [问题]
        │
        ▼
   LLM 生成（带引用来源）

  质量杠杆：
   切片粒度 / 检索召回率 / 重排(Rerank) / 来源可信度
  常见坑：检索不到→答非所问；片段太长→淹没重点"""),

    "agent-ch11": ("agent", "一个能干活 Agent = 规划 + 工具 + 记忆，多智能体再分角色协作",
        "一个能真正干活的 Agent 由三件套组成：规划（把目标拆成步骤）、工具（调用搜索/代码/API）、"
        "记忆（短期上下文 + 长期存储）。多智能体则是把「规划/执行/评审」分给不同角色，靠消息协作，适合复杂任务。",
        r"""单 Agent 闭环:
   目标 → [Planner 规划] → 步骤1 → [Tool 调搜索/代码/API]
                               │ 结果
                               ▼
                          [Memory 记忆] ← 短期(上下文)+长期(向量库)
                               │
                               ▼
                          完成? → 是: 交付 / 否: 回到 Planner

多智能体（分角色）:
   UserRequest → Orchestrator(路由)
        ├─ Planner  Agent  拆解任务
        ├─ Worker   Agent  调工具执行
        └─ Critic   Agent  评审/纠错
   角色间经消息总线协作，各自持独立上下文

  稳定性关键：工具调用结果要校验、步骤要可回滚、错误要进记忆。"""),

    # ---------------- Data (NumPy/Pandas) ----------------
    "data-ch01": ("data", "ndarray 是「一块连续同质内存 + 形状/步长视图」，广播让不同形也能运算",
        "ndarray 本质是「一块连续同质内存」加「shape/strides 视图」：逻辑维度由 strides 决定，"
        "很多操作（转置、reshape）只改视图不复制数据；广播（broadcasting）按尾部对齐、长度为1的轴复制，"
        "让不同形状数组也能逐元素运算，是 NumPy 向量化提速的核心。",
        r"""内存布局（一维视角）:
   [ a0 ][ a1 ][ a2 ][ a3 ][ a4 ][ a5 ]  连续字节
   shape=(2,3)  strides=(3*8, 1*8) 字节

  视图 vs 复制:
   a.T       只换 shape/strides，不搬数据（视图）
   a.reshape  → 连续则视图，否则复制
   a.copy()  强制复制

  广播 Broadcasting（从尾部对齐）:
   (3,1) 与 (3,) → 对齐为 (3,3) 逐元素
   (2,3) 与 (3,)  → (2,3) 行复制 (3,) 成 (2,3)
   规则：维度相等 或 其一为 1，否则报错

  向量化：用数组运算替代 Python for 循环 → 接近 C 速度"""),
}


def insert(ch: str, subject: str, marker: str, caption: str, art: str) -> str:
    d = CONTENT / subject / ch / "concept"
    files = sorted(d.glob("*.md")) if d.exists() else []
    if not files:
        return f"[skip] {ch} 无 concept 目录"
    f = files[0]
    text = f.read_text(encoding="utf-8")
    if marker in text:
        return f"[skip] {ch} 已含图（幂等）"
    # 找第一个 H1 标题行，插在其后
    idx = text.find("\n# ")
    if idx == -1:
        idx = text.find("# ")
        if idx != 0:
            return f"[skip] {ch} 找不到 H1 标题"
        h1_end = text.find("\n", idx)
    else:
        h1_end = idx + 1 + text[idx + 1:].find("\n") + 1
    block = f"\n> {caption}\n\n```text\n{art}\n```\n"
    new = text[:h1_end] + block + text[h1_end:]
    f.write_text(new, encoding="utf-8")
    return f"[ok] {ch} -> {f.name}"


def main() -> int:
    ok = skip = miss = 0
    for ch, (subject, marker, caption, art) in DIAG.items():
        res = insert(ch, subject, marker, caption, art)
        print(res)
        if res.startswith("[ok]"):
            ok += 1
        elif res.startswith("[skip]") and "已含" in res:
            skip += 1
        else:
            miss += 1
    print(f"\n合计: 新增 {ok} / 跳过(已存在) {skip} / 失败 {miss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
