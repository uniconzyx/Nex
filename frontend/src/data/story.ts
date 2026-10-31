/* 由 scripts/gen_story_data.py 从 content/_story/acts.json 生成，请勿手改。
   164 条台词 / 41 幕 / 13 个学科。
   可见性规则：pitfall 与 scene 未完成也能看（悬念即钩子）；archive 已说半个答案，必须完成后才显示。 */
/* eslint-disable */

export type StoryTone = 'pitfall' | 'scene' | 'field' | 'archive';

export interface StoryLine {
  chapterId: string;
  title: string;
  tone: StoryTone;
  line: string;
  anchor: string;
}

export interface StoryAct {
  id: string;
  group: string;
  title: string;
  chapters: StoryLine[];
}

export interface StorySubject {
  key: string;
  label: string;
  acts: StoryAct[];
}

export const STORY: StorySubject[] = [
  { key: "ai", label: "AI · Agent 开发", acts: [
    { id: "ai-a1", group: "Agent 开发", title: "从岗位到接口：把「会用」变成「能交付」", chapters: [
      { chapterId: "agent-ch01", title: "AI 行业认知与岗位地图：从「会用」到「知道为什么值钱」", tone: "pitfall", line: "我背了一堆模型名，JD 上问的是「你做过哪一层的成本账」。", anchor: "goals-1 产业链四层与毛利" },
      { chapterId: "agent-ch02", title: "Prompt 工程与结构化输出：把自然语言当接口设计", tone: "archive", line: "四段式模板之所以有效，是因为角色、任务、约束、示例各自消掉一种不确定性。少哪段，输出就在哪里漂。", anchor: "goals-1 四段式模板" },
      { chapterId: "agent-ch03", title: "模型接入与 DeepSeek 实操：第一次让程序真的说话", tone: "pitfall", line: "我第一次接模型只写了 model 和 messages。上生产那天，超时、限流、跨包 SSE 一起来了。", anchor: "goals-1/2 客户端与流式解析" },
      { chapterId: "agent-ch04", title: "需求洞察：用户故事与 AI 产品画布", tone: "archive", line: "「让 AI 更智能」不是需求。需求是那句能写进验收条件的话——否则做完了也没人判定它算不算完成。", anchor: "goals-1 可验收用户故事" },
    ] },
    { id: "ai-a2", group: "Agent 开发", title: "瓶颈不在模型：检索、显存、数据与那条前向链路", chapters: [
      { chapterId: "agent-ch05", title: "RAG 技术精讲：检索质量决定回答上限", tone: "pitfall", line: "召回率 90%，答案还是错的。我一直在调提示词，没人告诉我错在上游。", anchor: "goals-1 检索决定上限" },
      { chapterId: "agent-ch06", title: "私有化部署与推理服务：把模型放进自己的机房", tone: "archive", line: "24G 单卡能不能跑 14B？我拍脑袋说能，然后被 KV Cache 的账打了脸。", anchor: "goals-1 显存四拆" },
      { chapterId: "agent-ch07", title: "轻量化微调：LoRA / QLoRA 与数据工程", tone: "pitfall", line: "我先上了微调，后来才发现我要的只是更新知识——那本该交给 RAG。", anchor: "goals-1 该不该微调决策表" },
      { chapterId: "agent-ch08", title: "Transformer 核心机理：能白板推一遍才算懂", tone: "archive", line: "背得出注意力公式，和能从 token 一路画到 logits，中间隔着一整条链路。这条链路上每一步都可验证。", anchor: "goals-1 完整前向链路" },
    ] },
    { id: "ai-a3", group: "Agent 开发", title: "从感觉到数字：多模态的成本、评估的口径、Agent 的边界", chapters: [
      { chapterId: "agent-ch09", title: "多模态应用开发：图像、文档与语音的工程接口", tone: "pitfall", line: "一张发票我先想的是「喂给模型」，没想到先算它会占多少 token。", anchor: "goals-1 视觉 token 账本" },
      { chapterId: "agent-ch10", title: "AI 产品设计与评估方法论：把「感觉不错」变成分数", tone: "archive", line: "上线前说的是「效果不错」，上线后没人能证明它比上周好。黄金集和三档指标，就是为了堵这句话。", anchor: "goals-1 黄金集与三层指标" },
      { chapterId: "agent-ch11", title: "Agent 系统开发：工具、记忆、规划与多智能体", tone: "pitfall", line: "循环跑飞了三次。我以为是模型笨，其实是我没给它一个能判定的终止条件。", anchor: "goals-1 三要素" },
      { chapterId: "agent-ch12", title: "商业化与行业解决方案：从 demo 到能签单", tone: "archive", line: "按席位收费很爽，直到少数重度用户的推理成本吃掉了他们全年订阅费。计费模式的选择，本质是风险转移。", anchor: "goals-1 三种计费的毛利" },
    ] },
    { id: "ai-a4", group: "Agent 开发", title: "把做过的事，讲成别人愿意付钱的证据", chapters: [
      { chapterId: "agent-ch13", title: "前沿技术追踪：建立自己的信息过滤系统", tone: "pitfall", line: "我一年读了 200 篇论文，一篇都没跑过。收藏夹不算知识。", anchor: "goals-4 复现最小闭环" },
      { chapterId: "agent-ch14", title: "职业发展框架：把能力翻译成岗位语言", tone: "archive", line: "简历上写「熟悉大模型」等于没写。面试官要的是：哪个模型、熟到什么程度、有没有一件能验证的事。", anchor: "goals-1 四维五级能力矩阵" },
      { chapterId: "agent-ch15", title: "项目实操：端到端交付一个可演示的 Agent 产品", tone: "pitfall", line: "我把最难的部分先做了。三周后 demo 能跑，但没人愿意点第二次。", anchor: "goals-2 先跑通最简方案" },
      { chapterId: "agent-ch16", title: "简历、模拟面试与入职答辩：把项目讲成录用理由", tone: "archive", line: "项目讲十分钟不难，难的是讲到「你做的哪个决定，导致了什么数字变化」。前者是经历，后者才是证据。", anchor: "goals-1 STAR-R 证据清单" },
    ] },
    { id: "ai-a5", group: "大模型原理", title: "从梯度到接口：原理被压缩成一行 API 之前的样子", chapters: [
      { chapterId: "ai-ch01", title: "深度学习基础：张量、前向与反向传播", tone: "pitfall", line: "我以为反向传播就是链式法则。直到有人问：为什么它只要一次前向的代价。", anchor: "goals-1 反向模式自动微分" },
      { chapterId: "ai-ch02", title: "视觉与序列建模：CNN、RNN 到注意力机制", tone: "archive", line: "算不出 3×3 卷积、64 通道的参数量，面试第一问就卡住。这个数字不靠背，靠 out 和 Params 两个公式推。", anchor: "goals-2 参数量与感受野" },
      { chapterId: "ai-ch03", title: "Transformer 与大语言模型原理", tone: "pitfall", line: "我能默写 QKV，却说不出为什么除以根号 d_k。后来发现，那是个方差问题。", anchor: "goals-1 缩放的必要性" },
      { chapterId: "ai-ch04", title: "高效微调与对齐：LoRA、RLHF 与 DPO", tone: "pitfall", line: "rank 从 8 调到 64，效果没动。我调的不是容量，是我不理解的旋钮。", anchor: "goals-2 LoRA 的 rank 与 alpha" },
      { chapterId: "ai-ch05", title: "提示工程与上下文工程", tone: "pitfall", line: "提示词不是咒语。措辞、示例、结构、上下文这四件事各有各的价钱，混在一起调就是在瞎调。", anchor: "goals-1 可度量的四件事" },
    ] },
    { id: "ai-a6", group: "大模型原理", title: "把模型装进系统：检索、循环、延迟、显存", chapters: [
      { chapterId: "ai-ch06", title: "RAG：向量检索与知识增强", tone: "pitfall", line: "余弦和内积，我当成两个指标比了一下午。归一化之后它们是同一个。", anchor: "goals-2 相似度等价" },
      { chapterId: "ai-ch07", title: "Agent 开发：工具调用、记忆与多智能体", tone: "archive", line: "能用确定性 DAG 写完的流程，硬上 Agent，它每次跑的结果都不一样。Agent 只该留给真的需要自主决策的地方。", anchor: "goals-3 架构判据" },
      { chapterId: "ai-ch08", title: "LLM 应用工程：推理优化、评测、可观测性与安全", tone: "pitfall", line: "用户说卡，我去优化模型。其实 TTFT 卡在 prefill，那是算力不是模型。", anchor: "goals-1 两阶段延迟" },
      { chapterId: "ai-ch09", title: "生成模型：从自编码器到扩散", tone: "pitfall", line: "我调了一周 GAN，loss 在抖，样本在崩。没人告诉我这是纳什均衡，不是梯度下降。", anchor: "goals-3 最优判别器" },
      { chapterId: "ai-ch10", title: "训练工程与规模化：从「能跑通」到「能训起来」", tone: "archive", line: "7B 模型要几张卡不是玄学：十六字节一个参数，权重、梯度、优化器状态、激活四部分加起来，就是答案。", anchor: "goals-4 训练显存口算" },
    ] },
    { id: "ai-a7", group: "机器学习", title: "几何、代数、统计：同一件事的三种说法", chapters: [
      { chapterId: "ml-ch01", title: "机器学习导论：范式、代价函数与梯度下降", tone: "pitfall", line: "训练高、验证也高，我以为是过拟合，去加了正则。方向正好反了。", anchor: "goals-3 曲线诊断" },
      { chapterId: "ml-ch02", title: "线性回归与逻辑回归：从最小二乘到正则化", tone: "archive", line: "L1 稀疏、L2 平滑，我背了三年。有人问我 L1 的等值线为什么是菱形，我愣住了。", anchor: "goals-3 几何视角" },
      { chapterId: "ml-ch03", title: "神经网络：推理、训练与多分类（衔接 ai 学科）", tone: "pitfall", line: "多分类我用了 MSE。梯度照样能算，只是它不再指向我要的方向。", anchor: "goals-2 损失与激活配对" },
      { chapterId: "ml-ch04", title: "应用机器学习：评估、偏差方差与误差分析", tone: "pitfall", line: "准确率 98%，上线一塌糊涂。因为那 2% 里全是我想抓的人。", anchor: "goals-4 业务代价选指标" },
      { chapterId: "ml-ch05", title: "决策树与集成学习：从信息增益到 XGBoost", tone: "archive", line: "树自己找分裂点，森林用方差公式投票。集成为什么有用，写成了 ρσ²+(1−ρ)σ²/B。", anchor: "goals-4 Bagging 方差缩减" },
    ] },
    { id: "ai-a8", group: "机器学习", title: "没有标签的时候，怎么知道学对了", chapters: [
      { chapterId: "ml-ch06", title: "无监督学习：K-means、异常检测与 GMM", tone: "pitfall", line: "K-means 把数据分成两簇：一簇是金额，一簇是时间。因为量纲差了一千倍。", anchor: "goals-2 对尺度敏感" },
      { chapterId: "ml-ch07", title: "推荐系统：协同过滤与矩阵分解", tone: "archive", line: "把「没点过」当成 0 喂进回归，模型学会的是一套不存在的偏好。隐式反馈要换损失，不是换模型。", anchor: "goals-4 隐式反馈换损失" },
      { chapterId: "ml-ch08", title: "强化学习：马尔可夫决策过程与 Q-learning", tone: "pitfall", line: "Q-learning 的 target 里有一个 max。它让我高估了从没试过的动作。", anchor: "goals-4 target 差异" },
      { chapterId: "ml-ch09", title: "支持向量机与核方法：最大间隔、对偶与核技巧", tone: "archive", line: "最大间隔不是几何直觉，是一次尺度规范化；核技巧不是魔法，是对偶里只剩内积。", anchor: "goals-1/4 规范化与核技巧" },
    ] },
    { id: "ai-a9", group: "大模型原理", title: "大模型工程：批处理、schema、注意力、多模态", chapters: [
      { chapterId: "ai-ch11", title: "模型服务化落地：从 train() 跑到线上不崩", tone: "archive", line: "动态批处理省下的不是算力，是等待——先凑满一批再统一算，尾延迟才降得下来。", anchor: "goals-1 动态批处理与输入契约" },
      { chapterId: "ai-ch12", title: "SFT 数据工程：任务 schema、合成数据过滤、去重与污染、难例挖掘、标注一致性 Kappa", tone: "pitfall", line: "我堆了十万条数据训出来还是胡说——因为没 schema，格式漂了整轮训练白干。", anchor: "goals-1 任务 schema 与指令设计" },
      { chapterId: "ai-ch13", title: "推理引擎与量化部署：KV Cache 分页、continuous batching、GPTQ/AWQ/GGUF", tone: "archive", line: "KV Cache 用 PagedAttention 像管理内存一样分页，显存碎片没了，并发才上得去。", anchor: "goals-1 PagedAttention 分页注意力" },
      { chapterId: "ai-ch14", title: "多模态落地：图文对齐、OCR→VLM 流水线、多模态 RAG、成本与延迟", tone: "scene", line: "OCR 先把版面拆开、文字认出来，再交给 VLM 问答——链路在哪一步崩决定你看到的是答案还是幻觉。", anchor: "goals-1 图文对齐与表征" },
    ] },
  ] },
  { key: "cpp", label: "C / C++", acts: [
    { id: "cpp-a1", group: "C++", title: "从语法到内存：语言开始有重量", chapters: [
      { chapterId: "cpp-ch01", title: "C++ 基础语法：类型、变量与引用", tone: "pitfall", line: "我以为引用是语法糖里的指针。可它不能为空、不能重绑，也不能挪位置。", anchor: "goals-2 引用与指针的区别" },
      { chapterId: "cpp-ch02", title: "函数：声明/定义、重载、默认参数与 lambda", tone: "archive", line: "重载决议只看参数列表，返回类型根本不参与。所以两个只差返回类型的函数，编译器会直接报重定义。", anchor: "goals-3 重载决议规则" },
      { chapterId: "cpp-ch03", title: "数组与字符串：C 数组、std::string 与字符串视图", tone: "pitfall", line: "sizeof(arr) 在 main 里是 40，在函数里变成 8。数组名一传参就退化了。", anchor: "goals-1 数组退化" },
      { chapterId: "cpp-ch04", title: "指针与内存管理：指针运算、new/delete 与悬垂", tone: "pitfall", line: "delete 完还能读出原来的值，我就以为那块内存还归我。", anchor: "goals-4 悬垂指针" },
      { chapterId: "cpp-ch05", title: "类与对象：封装、构造/析构、拷贝与运算符重载", tone: "archive", line: "对象的一生只有两个确定时刻：构造开始，析构结束。中间那些拷贝，才是 bug 的入口。", anchor: "goals-3 三/五法则" },
    ] },
    { id: "cpp-a2", group: "C++", title: "抽象、容器与所有权：让别人能读懂", chapters: [
      { chapterId: "cpp-ch06", title: "继承与多态：虚函数、抽象类与 RTTI", tone: "pitfall", line: "基类构造函数里调虚函数，调到的还是基类版本。对象那时还没长成子类。", anchor: "goals-2 构造/析构中不触发多态" },
      { chapterId: "cpp-ch07", title: "模板与泛型：函数模板、类模板与特化", tone: "archive", line: "模板报错两百行，真正那句错在第一行。后面全是实例化的回溯链——读的时候要从最深的那层往外剥。", anchor: "goals-3 两阶段查找" },
      { chapterId: "cpp-ch08", title: "STL 容器：vector/list/map/set/unordered", tone: "pitfall", line: "我在循环里 push_back 一个指向 vector 元素的指针。扩容那次，它们一起悬空。", anchor: "goals-1 扩容与迭代器失效" },
      { chapterId: "cpp-ch09", title: "STL 算法与迭代器：sort/find/lambda/范围", tone: "pitfall", line: "比较器写成 <=，std::sort 在某些输入上读到了数组外面。它没崩，这才可怕。", anchor: "goals-4 严格弱序" },
      { chapterId: "cpp-ch10", title: "智能指针与 RAII：unique_ptr/shared_ptr/weak_ptr", tone: "archive", line: "C++ 没有 GC，但它有析构函数。这一章把「谁负责释放」钉进了一个花括号里。", anchor: "goals-1 RAII 第一性" },
    ] },
    { id: "cpp-a3", group: "C++", title: "从能跑到能改：工程的基本礼貌", chapters: [
      { chapterId: "cpp-ch11", title: "异常处理与断言：try/catch、noexcept 与契约", tone: "pitfall", line: "noexcept 我是随手加的。后来发现它决定了 vector 扩容时移动还是拷贝。", anchor: "goals-4 noexcept 的影响" },
      { chapterId: "cpp-ch12", title: "现代 C++ 特性：auto/移动语义/范围 for/emplace", tone: "archive", line: "std::move 之后对象并没有空，它只是被转成了右值。究竟搬没搬，取决于那个类型有没有移动构造函数。", anchor: "goals-2 移动语义本质" },
      { chapterId: "cpp-ch13", title: "输入/输出与文件：iostream、fstream 与格式化", tone: "pitfall", line: "cin 慢，我关了同步。它快了，但和 printf 混用就开始乱序。", anchor: "goals-2 sync_with_stdio" },
      { chapterId: "cpp-ch14", title: "预处理与宏：include/define/条件编译/头文件守卫", tone: "pitfall", line: "#define SQUARE(x) x*x，SQUARE(1+2) 得 5。它是文本替换，不是函数调用。", anchor: "goals-3 宏的卫生问题" },
      { chapterId: "cpp-ch15", title: "命名空间与模块化：namespace/inline namespace/C++20 模块", tone: "archive", line: "同一个名字，在两个文件里可能指两个东西。作用域管查找在哪找，链接属性管它归谁——两套规则，别混着理解。", anchor: "goals-2 ADL" },
    ] },
    { id: "cpp-a4", group: "C++", title: "并发、极限与交付：让它在真实负载下不死", chapters: [
      { chapterId: "cpp-ch16", title: "并发与多线程：thread/mutex/atomic/async", tone: "pitfall", line: "i++ 在多线程里丢了数。它明明是一行，编译出来是三条指令。", anchor: "goals-2 数据竞争" },
      { chapterId: "cpp-ch17", title: "元编程与类型萃取：type_traits/constexpr/SFINAE/concept", tone: "archive", line: "SFINAE 我抄了三年。直到写出一个替换失败却报错的版本，才懂它只是「不报错」。", anchor: "goals-3 SFINAE" },
      { chapterId: "cpp-ch18", title: "性能与底层：内存对齐、缓存友好与内联", tone: "pitfall", line: "sizeof 出来 24，我写的是 20。那 4 个字节，编译器替我做了决定。", anchor: "goals-2 对齐与 padding" },
      { chapterId: "cpp-ch19", title: "工程化与测试：CMake、单元测试与 CI", tone: "pitfall", line: "target_link_libraries 写成 PUBLIC，一个依赖泄漏到所有下游。编得过，只是没人能单独用它。", anchor: "goals-2 usage requirements" },
      { chapterId: "cpp-ch20", title: "综合项目与面试冲刺：系统设计、代码规范与复盘", tone: "archive", line: "自己写一遍 vector 的扩容，才会明白前面十九章讲的其实是同一件事：谁持有、谁释放、什么时候失效。", anchor: "goals-1 造一遍 STL" },
    ] },
  ] },
  { key: "fundamentals", label: "计算机基础（408）", acts: [
    { id: "fund-a1", group: "数据结构", title: "连续、受限、分层、成环：四种底座", chapters: [
      { chapterId: "fund-ch01", title: "数据结构：线性表与链表", tone: "pitfall", line: "数组和链表都写 O(N)，实测差五倍。复杂度只算次数，不算缓存。", anchor: "goals-3 渐进≠实测" },
      { chapterId: "fund-ch02", title: "栈、队列与串", tone: "archive", line: "函数能返回，是因为有人替你把返回地址压进了栈。栈不是数据结构，是硬件约定。", anchor: "goals-4 栈帧" },
      { chapterId: "fund-ch03", title: "树与二叉树", tone: "pitfall", line: "前中后序我背了三套模板。其实只有一件事在变：根什么时候被访问。", anchor: "goals-4 访问根的时机" },
      { chapterId: "fund-ch04", title: "图", tone: "archive", line: "图和树只差一个字：环。所有图算法本质上都在处理那条多余的边——要么绕开它，要么利用它。", anchor: "goals-2 DFS/BFS 是搜索序" },
    ] },
    { id: "fund-a2", group: "数据结构 + 计组", title: "算法之下的硬件：为什么「一样快」的两种写法差五倍", chapters: [
      { chapterId: "fund-ch05", title: "查找与哈希", tone: "pitfall", line: "ASL 我算了个平均值。成功和失败要分开算，权重也不一样。", anchor: "goals-1 ASL 定义" },
      { chapterId: "fund-ch06", title: "排序算法与复杂度分析", tone: "archive", line: "快排最坏 O(n²)，我知道。可我的数据是预排序的，每次都挑到端点做枢轴。", anchor: "goals-2 最坏情况与优化" },
      { chapterId: "fund-ch07", title: "计算机组成原理：数据表示与运算", tone: "pitfall", line: "0.1 + 0.2 != 0.3，我以为是语言的问题。它是 IEEE 754 的正确行为。", anchor: "goals-3 浮点表示" },
      { chapterId: "fund-ch08", title: "计组：存储系统与 CPU", tone: "archive", line: "CPU 一次搬 64 字节，你只要了 4 个。剩下 60 个，是缓存替你赌的下一步。", anchor: "goals-1 局部性" },
    ] },
    { id: "fund-a3", group: "操作系统 + 网络", title: "从上到下：一台机器怎么同时做很多事、怎么把字节送到对面", chapters: [
      { chapterId: "fund-ch09", title: "操作系统：进程、线程与调度", tone: "pitfall", line: "运行到阻塞是自己要的，阻塞到就绪是别人通知的，运行到就绪是被抢走的。", anchor: "goals-2 状态转换判据" },
      { chapterId: "fund-ch10", title: "操作系统：内存管理、文件与 IO", tone: "archive", line: "页表本身就存在内存里，取一次数据要访两次存。所以 CPU 里还得再放一个 TLB，把常用映射缓存起来。", anchor: "goals-4 TLB 与 EAT" },
      { chapterId: "fund-ch11", title: "计算机网络：分层模型与 TCP/IP", tone: "pitfall", line: "每层都加一个头。我一直以为那是开销，其实那是让下层不必知道上层在干什么。", anchor: "goals-2 封装与分用" },
      { chapterId: "fund-ch12", title: "计算机网络：应用层与链路排查", tone: "archive", line: "地址栏敲下回车到页面亮起来，中间排着 DNS、三次握手、TLS、一次请求往返和一遍渲染。哪一步慢，得逐段量。", anchor: "goals-2 一次请求全链路" },
    ] },
    { id: "fund-a4", group: "计算机组成原理", title: "从五大部件到一根总线：冯·诺依曼之后机器怎么跑起来", chapters: [
      { chapterId: "fund-ch13", title: "计算机组成原理：计算机系统概述", tone: "pitfall", line: "主频翻倍，程序不一定快一倍——Amdahl 说加速比被那块串行代码死死卡住。", anchor: "goals-5 性能指标与Amdahl" },
      { chapterId: "fund-ch14", title: "计算机组成原理：指令系统", tone: "pitfall", line: "十种寻址方式我都背了，真写有效地址 EA 时却数不清到底要访存几次。", anchor: "goals-3 寻址方式与有效地址" },
      { chapterId: "fund-ch15", title: "计算机组成原理：中央处理器（CPU）", tone: "pitfall", line: "时空图我画得挺漂亮，算吞吐率时却把结构冒险那几个 stall 悄悄漏掉了。", anchor: "goals-4 五级流水线冒险与转发" },
      { chapterId: "fund-ch16", title: "计算机组成原理：总线", tone: "pitfall", line: "总线带宽我总算错——把时钟频率直接当传输率，忘了乘宽度、忘了复用占掉的相位。", anchor: "goals-3 总线特性与带宽" },
    ] },
    { id: "fund-a5", group: "数据结构 + 操作系统", title: "等价类、特权级、inode：软件怎么在硬件上安家", chapters: [
      { chapterId: "fund-ch17", title: "计算机组成原理：I/O 系统", tone: "pitfall", line: "中断和 DMA 我都背了，真说清『CPU 和 DMA 抢访存时谁让谁』却卡了壳。", anchor: "goals-5 DMA与CPU争访存" },
      { chapterId: "fund-ch18", title: "数据结构：并查集与字符串高级", tone: "pitfall", line: "并查集我写了路径压缩，却讲不清为什么能当 O(1) 用——那只反阿克曼 α(n) 一直没懂。", anchor: "goals-2 并查集均摊复杂度" },
      { chapterId: "fund-ch19", title: "操作系统：操作系统概述与运行机制", tone: "pitfall", line: "用户态内核态我分得清，却讲不出『一条 int 0x80 怎么就掉进内核了』——模式位在那儿管着。", anchor: "goals-6 系统调用与陷入指令" },
      { chapterId: "fund-ch20", title: "操作系统：文件管理", tone: "archive", line: "混合索引最大文件 = 10 个直接块 + 一/二/三级间接各自块数 × 块大小，偏移落在哪一级看临界。", anchor: "goals-4 混合索引最大文件大小" },
    ] },
    { id: "fund-a6", group: "操作系统 + 计算机网络", title: "把字节送到对面：I/O、磁盘与比特流", chapters: [
      { chapterId: "fund-ch21", title: "操作系统：I/O 管理与磁盘", tone: "pitfall", line: "单缓冲双缓冲我分清了，算平均用时却忘了生产者和消费者在抢同一个缓冲队列。", anchor: "goals-6 缓冲与SPOOLing" },
      { chapterId: "fund-ch22", title: "计算机网络：物理层", tone: "archive", line: "算信道容量别乱套：奈奎斯特给 2W·log2V（无噪声），香农给 W·log2(1+S/N)，dB 先换倍数。", anchor: "goals-4 香农定理与dB换算" },
      { chapterId: "fund-ch23", title: "计算机网络：数据链路层", tone: "pitfall", line: "GBN 和 SR 的窗口上限我背了，算信道利用率却把 ACK 那点传输时间给丢了。", anchor: "goals-4 可靠传输三协议窗口" },
    ] },
  ] },
  { key: "java", label: "Java", acts: [
    { id: "java-a1", group: "语言", title: "语法、对象、类型：Java 的三层地基", chapters: [
      { chapterId: "java-ch01", title: "环境与基础语法：JDK、变量、八种基本类型、运算符、流程控制、数组", tone: "pitfall", line: "public static void main 我敲了几百遍。没人告诉我四个词各在约束什么。", anchor: "goals-2 固定签名约定" },
      { chapterId: "java-ch02", title: "类与对象：封装、构造器、this", tone: "archive", line: "Java 只有值传递。可我把对象传进去改了字段，它确实变了——变的是同一个堆对象。", anchor: "goals-2 引用的副本" },
      { chapterId: "java-ch03", title: "继承与多态：extends、方法重写、抽象类与接口", tone: "pitfall", line: "父类引用指向子类对象：方法变了，字段没变。多态只在方法上。", anchor: "goals-3 字段隐藏" },
      { chapterId: "java-ch04", title: "集合框架：List、Set、Map、Queue 与泛型集合", tone: "pitfall", line: "我把对象塞进 HashSet，再改它的字段，然后就再也 remove 不掉了。", anchor: "goals-4 equals/hashCode 契约" },
      { chapterId: "java-ch05", title: "异常体系与泛型进阶", tone: "archive", line: "异常不是用来打印栈的，是为了把「这一步可能失败」写进类型系统，让调用方在编译期就被迫面对它。", anchor: "goals-1 受检异常契约" },
    ] },
    { id: "java-a2", group: "运行时", title: "运行时：字节怎么流、线程怎么排、对象怎么活、依赖怎么来", chapters: [
      { chapterId: "java-ch06", title: "IO 与 NIO", tone: "pitfall", line: "FileInputStream 读中文乱码。因为我把字节当成了字符。", anchor: "goals-1 字节流/字符流边界" },
      { chapterId: "java-ch07", title: "并发：Thread、线程池与 JUC 并发容器", tone: "archive", line: "volatile 只保证可见性和禁止重排序，不保证复合操作原子。所以两个线程同时 i++ ，照样会丢数。", anchor: "goals-4 volatile 边界" },
      { chapterId: "java-ch08", title: "JVM 与内存模型、GC、类加载", tone: "pitfall", line: "堆切成 Region，对象拆成对象头。「泄漏」= 还有一条 GC Root 指着它。", anchor: "goals-3/5 布局与可达性" },
      { chapterId: "java-ch09", title: "工程与框架：Maven 与 Spring Boot 入门", tone: "archive", line: "一串 groupId:artifactId:version 背后是一次依赖调解。构建工具真正管的是版本冲突，不是编译命令。", anchor: "goals-3 依赖调解" },
    ] },
  ] },
  { key: "database", label: "数据库", acts: [
    { id: "db-a1", group: "SQL 与索引", title: "从「我要什么」到「它怎么取」", chapters: [
      { chapterId: "db-ch01", title: "关系模型与 SQL 基础（DDL/DML/SELECT/JOIN/聚合/分组）", tone: "pitfall", line: "NULL 不等于任何值，包括它自己。所以 WHERE x != 1 会漏掉 x 为空的那些行。", anchor: "goals-1 关系完整性与 NULL" },
      { chapterId: "db-ch02", title: "表连接与子查询：JOIN、子查询、集合操作", tone: "archive", line: "LEFT JOIN 之后行数变多，不是去重失效，是右表有两行同时匹配。连接先做笛卡尔积再过滤，行数就是这么来的。", anchor: "goals-2 JOIN 语义" },
      { chapterId: "db-ch03", title: "索引与事务：B+树索引、ACID、隔离级别", tone: "pitfall", line: "三层 B+ 树，四次 I/O，一亿行。这一章让「为什么快」有了次数。", anchor: "goals-1 树高估算" },
      { chapterId: "db-ch04", title: "查询优化与执行计划（EXPLAIN）", tone: "archive", line: "索引建好不代表被用上。EXPLAIN 是数据库唯一愿意跟你说实话的地方——type 那一列，就是它给不给面子的答案。", anchor: "goals-3 EXPLAIN 逐列" },
    ] },
    { id: "db-a2", group: "工程与运维", title: "一个库的四件麻烦事：过程、规范、灾备、拆表", chapters: [
      { chapterId: "db-ch05", title: "存储过程 / 触发器 / 自定义函数", tone: "pitfall", line: "函数能出现在 WHERE 里，过程不能。它们不是一个东西的两个名字。", anchor: "goals-3 过程与函数四条差异" },
      { chapterId: "db-ch06", title: "范式与数据库建模", tone: "archive", line: "表拆到 3NF 之后，一次查询要 join 五张表。范式保证不冗余，不保证快；反范式是拿冗余换读性能的自觉交易。", anchor: "goals-2 ER 与反范式权衡" },
      { chapterId: "db-ch07", title: "备份恢复与权限安全", tone: "pitfall", line: "DELETE 没加 WHERE。备份能恢复，但恢复点是昨晚两点，中间六小时订单没了。", anchor: "goals-2 PITR" },
      { chapterId: "db-ch08", title: "高可用 / 主从复制 / 分库分表", tone: "archive", line: "机器一定会坏，数据一定会装不下。所以只有两问：坏了怎么不停，满了怎么拆。", anchor: "goals-1 可用性与扩展性" },
    ] },
  ] },
  { key: "fullstack", label: "全栈开发", acts: [
    { id: "fs-a1", group: "Web 与前端", title: "一个请求的旅程：从地址栏到事件循环", chapters: [
      { chapterId: "fs-ch01", title: "Web 工作原理：HTTP 协议与浏览器-服务器交互", tone: "pitfall", line: "PUT 和 PATCH 我随手用。重试一次，PUT 没事，PATCH 把值加了两遍。", anchor: "goals-3 幂等性" },
      { chapterId: "fs-ch02", title: "前端基础：HTML 语义化与 CSS 盒模型/布局", tone: "archive", line: "width: 100% 加 padding 之后撑破了容器。100% 算的是 content，不是 border。", anchor: "goals-3 盒模型" },
      { chapterId: "fs-ch03", title: "JavaScript 核心：类型、原型链、DOM 与事件、异步(Promise/async)", tone: "pitfall", line: "typeof null 是 object。这个 1995 年的 bug，我第一场面试就栽在它上面。", anchor: "goals-1 typeof 坑" },
      { chapterId: "fs-ch04", title: "Node.js 与后端 API", tone: "archive", line: "Node 只有一个线程，却能同时挂着一万个请求。因为「等 I/O」这件事被排进了队列，而不是占着线程空转。", anchor: "goals-1 事件循环六阶段" },
    ] },
    { id: "fs-a2", group: "后端与上线", title: "让它上线：契约、凭证、状态、机器", chapters: [
      { chapterId: "fs-ch05", title: "数据库与 REST API 设计", tone: "pitfall", line: "我加了联合索引 (a,b)，查询只带 b，索引一点没用上。最左前缀不是建议，是规则。", anchor: "goals-2 最左前缀" },
      { chapterId: "fs-ch06", title: "用户认证 / JWT / 鉴权", tone: "archive", line: "JWT 里塞了角色，改权限就得等它过期。它没有撤销接口，只有到期时间——这是无状态换来的代价，不是 bug。", anchor: "goals-2 能否主动撤销" },
      { chapterId: "fs-ch07", title: "全栈项目实战（GitHub 资源驱动）", tone: "pitfall", line: "所有状态都塞进全局 store。后来每次请求失败，我都要手动回滚五个地方。", anchor: "goals-3 服务端/客户端状态" },
      { chapterId: "fs-ch08", title: "部署 / CI-CD / Docker", tone: "archive", line: "部署不是把代码拷上去，是让一台机器在没人看着的时候，自己回到该有的样子。", anchor: "goals-2 systemd 与日志" },
    ] },
    { id: "fs-a3", group: "工程化与框架", title: "工程化：类型、前端框架与微服务骨架", chapters: [
      { chapterId: "fs-ch09", title: "TypeScript：结构化类型、泛型与类型收窄", tone: "pitfall", line: "我写了 let，收窄就丢了——其实丢的是重新赋值，不是 let。绑定一动，类型就回不去。", anchor: "goals-1 结构类型与收窄" },
      { chapterId: "fs-ch10", title: "Vue 3 + TypeScript + Pinia：响应式原理与 ref/reactive 边界", tone: "archive", line: "ref 必须写 .value，是因为响应式靠 Proxy 拦截；不写 .value 就绕过了依赖收集。", anchor: "goals-1 响应式依赖收集" },
      { chapterId: "fs-ch11", title: "Spring Boot 3 工程骨架：分层边界、异常与校验收口", tone: "pitfall", line: "我把堆栈返给前端调试，结果用户看见了我们的包结构——异常该统一收口，别裸奔。", anchor: "goals-1 统一异常处理" },
      { chapterId: "fs-ch12", title: "服务拆分与网关：拆分判断、网关职责、配置中心", tone: "scene", line: "拆服务前先问：团队结构允许吗？康威定律说系统会复制团队的形状。", anchor: "goals-1 何时该拆" },
    ] },
    { id: "fs-a4", group: "质量与多语言", title: "质量门禁与多语言后端", chapters: [
      { chapterId: "fs-ch13", title: "前端测试与质量门禁：测试金字塔、E2E、契约测试", tone: "archive", line: "测试金字塔不是铁律，但倒金字塔真会拖垮交付——E2E 一跑半小时，没人愿意跑。", anchor: "goals-1 测试金字塔" },
      { chapterId: "fs-ch14", title: "Agent × 全栈工程接缝：流式、长任务、幂等与成本", tone: "field", line: "流式穿过网关断线了怎么续？一个 last-event-id，让长任务从断点接着跑。", anchor: "goals-1 流式透传与长任务" },
      { chapterId: "fs-ch15", title: "Go + Gin 后端：并发模型、接口契约与 Java 路线对照", tone: "pitfall", line: "我用共享内存数请求结果错得离谱——Go 的哲学是别通过共享内存通信，用 channel。", anchor: "goals-1 goroutine 并发模型" },
    ] },
  ] },
  { key: "middleware", label: "中间件", acts: [
    { id: "mw-a1", group: "Redis 与缓存", title: "缓存的四道坎：编码、落盘、故障、被冲垮", chapters: [
      { chapterId: "mw-ch01", title: "Redis 数据结构与底层编码", tone: "pitfall", line: "一次 HSET 卡了 200ms。不是网络，是那张哈希表正在 rehash。", anchor: "goals-3 渐进式 rehash" },
      { chapterId: "mw-ch02", title: "Redis 持久化与内存管理", tone: "archive", line: "开了 RDB 不等于数据安全，最后一次快照之后写进去的东西全没了。耐久性靠 AOF 的 fsync 策略兜，不靠快照频率。", anchor: "goals-2 AOF 三档 fsync" },
      { chapterId: "mw-ch03", title: "Redis 高可用：主从、哨兵与 Cluster", tone: "pitfall", line: "主库挂了，哨兵切了，客户端还连着旧主。切换不是原子的，客户端得会重连。", anchor: "goals-2 ODOWN 与选举" },
      { chapterId: "mw-ch04", title: "缓存设计与三大经典问题", tone: "archive", line: "缓存不是加速器，是数据库前面的一道闸。闸会漏（穿透）、会被单点撞穿（击穿）、也会被同时冲垮（雪崩）。", anchor: "goals-1/2/3 穿透击穿雪崩" },
    ] },
    { id: "mw-a2", group: "消息队列", title: "消息的四次交付：分区、位移、幂等、积压", chapters: [
      { chapterId: "mw-ch05", title: "Kafka 架构：Topic、Partition 与 Replica", tone: "pitfall", line: "acks=1 我以为写成功了。leader 挂了，那条消息跟着它一起没了。", anchor: "goals-3 ISR 与 acks" },
      { chapterId: "mw-ch06", title: "Kafka 生产者与消费者机制", tone: "archive", line: "自动提交位移很方便，但它在处理完成之前就提交了。于是崩一次，就静默丢一批——不报错，这才是最难查的。", anchor: "goals-4 位移提交时机" },
      { chapterId: "mw-ch07", title: "消息可靠性：不丢、不重、有序", tone: "pitfall", line: "我追求 exactly-once，调了两周。最后落地的是：至少一次，加一张去重表。", anchor: "goals-2 至少一次+幂等" },
      { chapterId: "mw-ch08", title: "消息队列选型与工程实践", tone: "archive", line: "MQ 把同步变异步，同时也把「立刻知道失败」变成了「以后才知道」。这笔延迟账要在设计阶段就认下来。", anchor: "goals-1 三大价值与代价" },
    ] },
  ] },
  { key: "python", label: "Python", acts: [
    { id: "py-a1", group: "语言核心", title: "名字、对象、容器：Python 的三件事", chapters: [
      { chapterId: "py-ch01", title: "语法与数据类型：变量/流程控制/字符串/列表/字典/元组/集合/推导式", tone: "pitfall", line: "a = b 之后我改了 a，b 也变了。名字不是盒子，是贴在对象上的标签。", anchor: "goals-1 名字绑定" },
      { chapterId: "py-ch02", title: "函数与作用域：def、参数解包、lambda、闭包、命名空间", tone: "archive", line: "在函数里给全局变量赋值，它就变成了局部变量。global 不是装饰也不是提醒，是让它别把名字建成新的。", anchor: "goals-3 LEGB" },
      { chapterId: "py-ch03", title: "内置数据结构：list/tuple/dict/set 与推导式、深浅拷贝", tone: "pitfall", line: "元组不可变。但元组里的那个列表，一直都能改。", anchor: "goals-4 引用不可变" },
      { chapterId: "py-ch04", title: "标准库：os/sys/re/datetime/json", tone: "archive", line: "带时区和不带时区的时间能直接相减，结果是一个没人想要的数。先立坐标系，再谈比较和运算。", anchor: "goals-3 时区处理" },
    ] },
    { id: "py-a2", group: "IO、并发与数据", title: "把数据搬进来：文件、文本、线程、数组", chapters: [
      { chapterId: "py-ch05", title: "文件与 IO：读写/上下文管理器/序列化", tone: "pitfall", line: "with open 写完我就走了。断电后文件是空的——flush 不等于 fsync。", anchor: "goals-3 缓冲与落盘" },
      { chapterId: "py-ch06", title: "正则与文本处理：re/分组/替换", tone: "archive", line: "一条正则跑了 40 秒。(a+)+b 这种写法在长串上不是慢，是指数级回溯——它是把正则当成了搜索树在走。", anchor: "goals-4 回溯爆炸" },
      { chapterId: "py-ch07", title: "并发：threading/asyncio", tone: "pitfall", line: "十个线程跑 CPU 密集任务，耗时和一个线程一样。我看了半小时监控才想起 GIL。", anchor: "goals-1 GIL" },
      { chapterId: "py-ch08", title: "数据分析：numpy/pandas 入门", tone: "archive", line: "一次调用算完整张表，靠的不是 Python 快，是它把循环交给了 C 和 SIMD。向量化的收益来自少做解释器层面的往返。", anchor: "goals-1 ndarray 与 list" },
      { chapterId: "py-ch09", title: "面向对象：类、继承与魔术方法", tone: "archive", line: "__new__ 先于 __init__ 跑，不可变类型的子类要改构造语义，只能动 __new__。", anchor: "goals-1 对象模型与查找" },
    ] },
  ] },
  { key: "spring", label: "Spring", acts: [
    { id: "spring-a1", group: "容器", title: "容器怎么把对象造出来，又在什么时候插一手", chapters: [
      { chapterId: "spring-ch01", title: "Spring 核心：IoC 容器与依赖注入", tone: "pitfall", line: "new 出来的对象不归容器管。所以它的 @Autowired 字段一直是 null。", anchor: "goals-1 IoC 与 DI" },
      { chapterId: "spring-ch02", title: "Bean 生命周期与作用域", tone: "archive", line: "在构造函数里用注入字段会拿到 null，因为那会儿属性还没填充。Bean 的生命周期有明确顺序，急不得。", anchor: "goals-1 生命周期顺序" },
      { chapterId: "spring-ch03", title: "AOP 与代理机制", tone: "pitfall", line: "注解加了，日志没打。那个类是 final 的，CGLIB 生不出子类。", anchor: "goals-3 final 不可代理" },
      { chapterId: "spring-ch04", title: "SpringBoot 自动配置与起步依赖", tone: "archive", line: "自动配置不是魔法，是一堆「有就用、没有就跳过」的条件装配。读懂了条件，就知道为什么某个 Bean 没生效。", anchor: "goals-3 条件装配" },
    ] },
    { id: "spring-a2", group: "Web 与持久层", title: "一次请求穿过四层：控制器、SQL、缓存、事务", chapters: [
      { chapterId: "spring-ch05", title: "Web 层：REST 控制器与参数校验", tone: "pitfall", line: "参数校验注解加了没生效。类上少了 @Valid，它只是注释，不是开关。", anchor: "goals-2 参数校验" },
      { chapterId: "spring-ch06", title: "MyBatis 基础：映射与 CRUD", tone: "archive", line: "${} 拼出来的 SQL 能被注入。#{} 是占位符，${} 是字符串替换，一字之差。", anchor: "goals-2 预编译与拼接" },
      { chapterId: "spring-ch07", title: "MyBatis 进阶：动态 SQL、缓存与插件", tone: "pitfall", line: "二级缓存开了，两个服务读到不一样的数据。它跨了 SqlSession，也跨了我以为的边界。", anchor: "goals-2 两级缓存失效条件" },
      { chapterId: "spring-ch08", title: "事务管理与工程实践", tone: "archive", line: "Transactional 失效的四个常见原因，都指向同一件事：它作用在代理对象上，而你调用的是对象自己。", anchor: "goals-2 事务失效场景" },
    ] },
  ] },
  { key: "clang", label: "C 语言（clang 单元）", acts: [
    { id: "clang-a1", group: "C 语言", title: "地址、堆、布局、文件：C 眼里的内存", chapters: [
      { chapterId: "clang-u01", title: "指针与地址运算", tone: "pitfall", line: "p + 1 前进几个字节？取决于 p 指向什么。指针的类型决定步长。", anchor: "goals-2 指针运算" },
      { chapterId: "clang-u02", title: "内存与动态分配（malloc/free）", tone: "archive", line: "p = realloc(p, n) 失败时返回 NULL，而 p 已经被覆盖，原来那块再也找不回来。标准写法是用一个临时指针接。", anchor: "goals-3 realloc 搬迁" },
      { chapterId: "clang-u03", title: "结构体与联合体", tone: "pitfall", line: "sizeof 出来 24，我写的是 20。那 4 个字节不是浪费，是对齐的过路费。", anchor: "goals-2 内存对齐" },
      { chapterId: "clang-u04", title: "文件 IO 与二进制", tone: "archive", line: "fread 返回的数字比你要的少，它不是在报错，是在告诉你读到了哪里。返回值必须查，否则部分读会被当成成功。", anchor: "goals-3 返回值与 EOF" },
    ] },
    { id: "clang-a2", group: "C 语言", title: "从文本到可执行：宏、目标文件、符号", chapters: [
      { chapterId: "clang-u05", title: "预处理与宏", tone: "pitfall", line: "宏不是函数，是翻译阶段 4 的一次纯文本替换。它连括号都不替你加。", anchor: "goals-2 括号卫生与多重求值" },
      { chapterId: "clang-u06", title: "Makefile 与构建", tone: "archive", line: "改了个头文件，make 什么都没做。它只看 .c 的时间戳，不知道头文件也进来了。", anchor: "goals-4 mtime 驱动的增量" },
      { chapterId: "clang-u07", title: "多文件编译与链接", tone: "archive", line: "编译通过、链接失败，是两个世界的事。名字要在第二个世界被认领一次——认领不到，就是 undefined reference。", anchor: "goals-2 声明/定义与链接属性" },
    ] },
  ] },
  { key: "bigdata", label: "大数据", acts: [
    { id: "bd-a1", group: "离线计算", title: "把一台机器撑不住的事，摊到一千台上", chapters: [
      { chapterId: "bd-ch01", title: "Hadoop 生态与 HDFS 架构", tone: "pitfall", line: "Secondary NameNode 不是备胎。它只帮忙合并日志，主节点挂了它接不上。", anchor: "goals-4 checkpoint 误区" },
      { chapterId: "bd-ch02", title: "MapReduce 原理与 YARN 调度", tone: "archive", line: "Combiner 只该做「可结合且可交换」的聚合。拿它做求和之外的运算，等于在中间环节悄悄改了语义。", anchor: "goals-3 Combiner 边界" },
      { chapterId: "bd-ch03", title: "Hive：数据仓库与 HQL", tone: "archive", line: "一条 HQL 变成分布式作业，路上会丢掉一些东西。丢掉的，就是你调不动的部分。", anchor: "goals-3 编译执行" },
    ] },
    { id: "bd-a2", group: "Spark 与数仓", title: "内存、DAG、口径：快的原因和算错的原因", chapters: [
      { chapterId: "bd-ch04", title: "Spark 核心：RDD 与惰性求值", tone: "pitfall", line: "Spark 快不是因为「在内存」，是它只在宽依赖那条线上付 Shuffle 的钱。", anchor: "goals-3 窄/宽依赖" },
      { chapterId: "bd-ch05", title: "Spark SQL、DataFrame 与 Catalyst", tone: "archive", line: "同样一个聚合，用 RDD 写比 DataFrame 慢八倍。因为优化器看不见 lambda 里面发生了什么，谓词下推也就无从下手。", anchor: "goals-1 结构化信息=优化空间" },
      { chapterId: "bd-ch06", title: "离线数仓实战：分层建模与调度", tone: "archive", line: "同一个指标在两张表里算出两个数，问题不在 SQL，在这个口径从来没被定义过。度量、聚合、限定、时间，四样缺一不可。", anchor: "goals-4 指标四要素" },
    ] },
  ] },
  { key: "data", label: "数据分析", acts: [
    { id: "data-a1", group: "NumPy 与 Pandas", title: "数组与表：把循环交给 C", chapters: [
      { chapterId: "data-ch01", title: "NumPy 基础：ndarray 与向量化", tone: "pitfall", line: "b = a[::2] 之后我改了 b，a 也变了。切片给的是视图，不是副本。", anchor: "goals-2 视图与拷贝" },
      { chapterId: "data-ch02", title: "NumPy 进阶：广播、随机与性能", tone: "archive", line: "广播不复制数据，它把该维的 stride 改成 0，于是零内存零拷贝。但一旦物化成真实数组，内存就按广播后的形状爆开。", anchor: "goals-1 stride 置 0" },
      { chapterId: "data-ch03", title: "Pandas 基础：Series 与 DataFrame", tone: "archive", line: "两个 Series 相加，索引对不上就补 NaN。Pandas 是先对齐、再运算——这条规则解释了它大部分的「意外结果」。", anchor: "goals-1 自动对齐" },
    ] },
    { id: "data-a2", group: "分析实战", title: "从分组到结论：聚合、抓取、证伪", chapters: [
      { chapterId: "data-ch04", title: "Pandas 进阶：分组聚合、合并与时间序列", tone: "pitfall", line: "merge 之后行数翻了三倍。右表的键不唯一，它做了笛卡尔积。", anchor: "goals-2 merge 语义" },
      { chapterId: "data-ch05", title: "数据采集：requests 与解析（含合规边界）", tone: "archive", line: "爬虫跑了一整晚，第二天 IP 被封。看的是页面内容，却没人看 robots.txt——合规边界在动手之前就该读。", anchor: "goals-4 合规边界" },
      { chapterId: "data-ch06", title: "数据分析与数学建模实战", tone: "archive", line: "结论能不能复现，取决于有没有先问那句：这个特征是怎么来的。泄漏和偏差，通常就藏在这个问题的答案里。", anchor: "goals-1/2/3/4 四问" },
    ] },
  ] },
  { key: "tooling", label: "工程工具", acts: [
    { id: "tool-a1", group: "Linux 与 Git", title: "文件、进程、对象：机器怎么记住东西", chapters: [
      { chapterId: "tool-ch01", title: "Linux 基础：文件系统与权限", tone: "pitfall", line: "rm 删了文件，磁盘没释放。因为还有个进程开着它，inode 引用数没归零。", anchor: "goals-4 inode 与链接" },
      { chapterId: "tool-ch02", title: "Linux 进程、管道与 Shell 脚本", tone: "archive", line: "子进程结束了，父进程没有 wait，它就成了僵尸，占着一个 PID 不放。回收动作不能省，省了就是泄漏。", anchor: "goals-4 僵尸进程" },
      { chapterId: "tool-ch03", title: "Git 核心：对象模型与分支", tone: "archive", line: "Git 不是存差异的数据库，是内容寻址的对象库。想通这一点，所有命令都只是增删查改。", anchor: "本章定位 内容寻址" },
    ] },
    { id: "tool-a2", group: "协作与容器", title: "和别人一起干：分支、镜像、编排", chapters: [
      { chapterId: "tool-ch04", title: "Git 协作：分支策略与冲突处理", tone: "pitfall", line: "git pull 我以为只是下载。它先 fetch 再 merge，我本地一堆提交被合了进来。", anchor: "goals-1 三类引用与 pull 语义" },
      { chapterId: "tool-ch05", title: "Docker 基础：镜像、容器与 Dockerfile", tone: "archive", line: "镜像是摞只读层，容器是顶上那层可写的。所以重启容器数据会没——要留下来，得挂在数据卷上，不是放在容器里。", anchor: "goals-1 分层与写时复制" },
      { chapterId: "tool-ch06", title: "Docker Compose 与部署实践", tone: "archive", line: "depends_on 只保证启动顺序，不保证依赖能用了。中间那段空窗，得靠健康检查和就绪门控自己填。", anchor: "goals-1 健康检查与就绪门控" },
    ] },
  ] },
];

/** 章节 id → 台词，剧情页逐个查，O(1)。 */
export const STORY_BY_CHAPTER: Record<string, StoryLine> = (() => {
  const m: Record<string, StoryLine> = {};
  for (const s of STORY) for (const a of s.acts) for (const c of a.chapters) m[c.chapterId] = c;
  return m;
})();

/** 台词是否可以在「未完成」时显示：archive 不行，它已经说了半个答案。 */
export function isTeaser(tone: StoryTone): boolean {
  return tone !== 'archive';
}
