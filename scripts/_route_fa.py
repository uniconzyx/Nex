# -*- coding: utf-8 -*-
"""来源颗粒度 · fundamentals 12 章 + ai 10 章（收尾批次 A）。

fundamentals 三个仓库的分工：
  CyC2018/CS-Notes                   —— 中文 408 笔记，按「算法/操作系统/网络/计组」分目录
  jwasham/coding-interview-university —— 英文清单式学习计划，用来「校准覆盖范围」
  donnemartin/system-design-primer    —— 系统设计，用来「看这些基础怎么用在设计题里」

ai 六个仓库的分工（ch01~ch08）：
  tensorflow/transformers —— 机制的真实实现
  langchain/dify          —— 应用层怎么把这些机制串起来
  AutoGPT/firecrawl       —— Agent 与抓取的真实工程形态
"""
import sys

from _route_granularity import apply

CSN = 'CyC2018/CS-Notes'
CIU = 'jwasham/coding-interview-university'
SDP = 'donnemartin/system-design-primer'

FUND = {
    'fund-ch01': {
        CSN: ('§1.2', '讲「顺序表与链表的取舍」时读 `docs/算法/` 下的线性表篇：它用「随机访问 vs 插入删除」两列对比，重点看它对「链表每结点多一个指针域」的空间代价的量化'),
        CIU: ('§2.1', '讲「双指针与链表操作」时读 README 里 Data Structures 的 Linked Lists 一节：给的练习题（逆置、找环、合并有序链表）与本章「一写就错」的清单高度重合'),
        SDP: ('§3.1', '讲「为什么基础结构影响系统设计」时读 `solutions/` 里的缓存设计题：LRU 用哈希表 + 双向链表实现，本章的「已知位置才能 O(1) 删除」正是它成立的前提'),
    },
    'fund-ch02': {
        CSN: ('§2.1', '讲「循环队列」时读 `docs/算法/` 的栈与队列篇：牺牲一个单元判满、`(rear+1)%MaxSize==front` 的写法与本章一致，配了元素个数公式的推导'),
        CIU: ('§1.3', '讲「栈与队列的适用场景」时读 README 里 Stack/Queue 的练习清单：括号匹配用栈、BFS 用队列，两条对应关系在清单里被反复强调'),
        SDP: ('§4.2', '讲「消息队列为什么需要缓冲区」时读 `solutions/` 的队列相关设计：队列把「生产速率」与「消费速率」解耦，这与本章「先进先出保证公平」是同一件事的两个层面'),
    },
    'fund-ch03': {
        CSN: ('§1.1', '讲「遍历序列互推」时读 `docs/算法/` 的二叉树篇：前序 + 中序能唯一确定、前序 + 后序不能——文档给了两组对照例子，把「为什么不能」演示清楚'),
        CIU: ('§2.2', '讲「BST 与堆的区别」时读 README 的 Trees 一节：BST 保证「中序有序」、堆只保证「父大于子」，两者的不变量不同，适用的题也不同'),
        SDP: ('§3.2', '讲「树在系统设计里的位置」时读 `solutions/` 的索引设计：B 树/B+ 树把「有序 + 多叉」结合，是「树的高度决定磁盘 IO 次数」的工业应用'),
    },
    'fund-ch04': {
        CSN: ('§2.3', '讲「图的两种存储」时读 `docs/算法/` 的图篇：邻接矩阵 O(V²) 空间换 O(1) 判边、邻接表相反，选择依据写作「稠密还是稀疏」'),
        CIU: ('§3.1', '讲「DFS 与 BFS 的模板」时读 README 的 Graphs 一节：递归 DFS 与队列 BFS 两份模板，配「什么时候该用哪个」的判断（最短路 / 连通性 / 拓扑）'),
        SDP: ('§4.1', '讲「图算法在系统设计中的应用」时读 `solutions/` 的社交网络设计：好友推荐本质是「图的邻居扩展」，与本章 BFS 分层是同一套思路'),
    },
    'fund-ch05': {
        CSN: ('§1.2', '讲「哈希冲突的处理」时读 `docs/算法/` 的查找篇：链地址法 vs 开放寻址的取舍，重点看「负载因子超过阈值就扩容」这条工程约定'),
        CIU: ('§2.1', '讲「二分的边界」时读 README 的 Binary Search 一节：`left <= right` 还是 `left < right`、`mid` 要不要 +1，这些「差一」错误在练习题里被逐个覆盖'),
        SDP: ('§3.3', '讲「哈希在缓存里的作用」时读 `solutions/` 的 key-value 存储设计：哈希把 O(n) 查找变 O(1)，但代价是「不支持范围查询」——这正是要加有序索引的原因'),
    },
    'fund-ch06': {
        CSN: ('§2.1', '讲「八种排序的复杂度表」时读 `docs/算法/` 的排序篇：时间/空间/稳定性三列齐全，重点看它对「快排最坏 O(n²) 与不稳定」的标注'),
        CIU: ('§3.2', '讲「排序算法的选择」时读 README 的 Sorting 一节：小数据用插入、大数据用快排/归并、要求稳定用归并——选择依据与本章一致'),
        SDP: ('§4.3', '讲「外部排序的动机」时读 `solutions/` 的大数据处理题：内存装不下时先分块排序再归并，是「排序不止在内存里做」的直接案例'),
    },
    'fund-ch07': {
        CSN: ('§1.1', '讲「补码为什么统一加减法」时读 `docs/计算机组成原理/` 的数据表示篇：模 2^n 剩余类的角度解释了「取反加一」，比「记住规则」更能推导出范围'),
        CIU: ('§2.3', '讲「位运算技巧」时读 README 的 Bit Manipulation 一节：`x & (x-1)` 清最低位 1、`x & -x` 取最低位 1，两道练习把这两个技巧练熟'),
        SDP: ('§3.1', '讲「浮点精度对业务的影响」时读 `solutions/` 里涉及计数的设计：金额必须用整数或定点数，浮点的非结合性会让「累加顺序不同结果不同」'),
    },
    'fund-ch08': {
        CSN: ('§2.1', '讲「地址字段划分」时读 `docs/计算机组成原理/` 的存储系统篇：标记/组索引/块内偏移的切分算法配了例题，重点是「组数 = 容量 /(块大小 × 路数)」'),
        CIU: ('§3.1', '讲「缓存局部性」时读 README 的 Cache 部分：时间局部性与空间局部性的定义、以及「按行遍历比按列快」的解释，与本章的实测结论一致'),
        SDP: ('§4.2', '讲「多级缓存的设计」时读 `solutions/` 的缓存层设计：L1/L2/CDN 各挡一层，与 CPU 的 L1/L2/L3 是同一套「用容量换延迟」的思路'),
    },
    'fund-ch09': {
        CSN: ('§1.3', '讲「调度算法的周转时间」时读 `docs/计算机操作系统/` 的进程管理篇：FCFS/SJF/SRTN/时间片轮转的甘特图画法，配「平均周转时间」的计算示例'),
        CIU: ('§2.1', '讲「进程与线程的区别」时读 README 的 Operating Systems 清单：地址空间、切换代价、通信方式三条，是面试追问的固定落点'),
        SDP: ('§3.2', '讲「并发在系统设计里的位置」时读 `solutions/` 的限流与线程池设计：线程数、队列、拒绝策略三者的取舍，与本章「时间片与上下文切换」同源'),
    },
    'fund-ch10': {
        CSN: ('§2.2', '讲「页面置换」时读 `docs/计算机操作系统/` 的内存管理篇：OPT/FIFO/LRU 的缺页次数逐个手算，Belady 异常只在 FIFO 出现这一点被单独标注'),
        CIU: ('§3.3', '讲「虚拟内存的意义」时读 README 的 Virtual Memory 一节：隔离、超额分配、按需调页三个目标，与本章「页表是间接层」的表述对应'),
        SDP: ('§4.1', '讲「文件系统在存储设计里的取舍」时读 `solutions/` 的对象存储设计：元数据与数据分离、块大小影响寻址开销，与本章 inode 的设计动机一致'),
    },
    'fund-ch11': {
        CSN: ('§1.2', '讲「TCP 三次握手」时读 `docs/计算机网络/` 的传输层篇：SYN/ACK 的序号变化配了状态迁移图，重点是「为什么是三次而不是两次」'),
        CIU: ('§2.3', '讲「分层模型」时读 README 的 Networking 清单：每层的职责与典型协议，用来校准「哪个问题该在哪一层解决」'),
        SDP: ('§3.1', '讲「TCP 与 UDP 的选择」时读 `solutions/` 的实时通信设计：可靠 vs 低延迟的取舍，与本章「拥塞控制的代价」是同一权衡'),
    },
    'fund-ch12': {
        CSN: ('§2.1', '讲「HTTP 与 DNS」时读 `docs/计算机网络/` 的应用层篇：DNS 递归/迭代查询的差别、HTTP 缓存头的组合，配了抓包示例'),
        CIU: ('§3.2', '讲「链路层排障」时读 README 的 Networking 练习：`ping`/`traceroute`/`curl -v` 各自回答什么问题，与本篇「分层排查」的顺序一致'),
        SDP: ('§4.2', '讲「CDN 与边缘节点」时读 `solutions/` 的 CDN 设计：把内容推到离用户最近的节点，本质是「用空间换 RTT」，与本章「时延带宽积」的量化视角互补'),
    },
}

TF = 'tensorflow/tensorflow'
FC = 'firecrawl/firecrawl'
AGPT = 'Significant-Gravitas/AutoGPT'
HF = 'huggingface/transformers'
DIFY = 'langgenius/dify'
LC = 'langchain-ai/langchain'
DS = 'huggingface/datasets'
VLLM = 'vllm-project/vllm'
LCPP = 'ggml-org/llama.cpp'
MLC = 'mlc-ai/mlc-llm'
LLAMA = 'facebookresearch/llama'

AI = {
    'ai-ch01': {
        TF: ('§1.2', '讲「反向传播」时读 `tensorflow/python/eager/backprop.py`：`GradientTape` 记录前向的每个算子、反向按链式法则逐层求导，本章公式里的「链式相乘」就是这里的 `gradient` 调用链'),
        HF: ('§2.1', '讲「张量的形状语义」时读 `src/transformers/models/` 下任一模型的 `forward`：`(batch, seq, hidden)` 这条约定贯穿所有模型，形状对不上时第一眼看的就是这里'),
        LC: ('§3.1', '讲「训练循环的骨架」时读 `libs/core/langchain_core/` 的 Runnable 接口：`invoke`/`batch`/`stream` 三件套是「推理调用」的抽象，对照本章的训练循环能看清「训练与推理的差异在哪一层'),
        DIFY: ('§4.1', '讲「模型接入的工程形态」时读 `api/core/model_runtime/`：把不同厂商的 API 统一成 `invoke` 接口，本章讲的「张量在前向里流动」到了应用层就变成「消息在 provider 之间转换」'),
        AGPT: ('§4.3', '讲「端到端的 AI 应用长什么样」时看仓库里的 agent 主循环：它把「LLM 调用 + 工具执行 + 结果回填」串成 while 循环，是本章「前向一次」在应用层的放大版'),
        FC: ('§3.3', '讲「训练数据的来源」时读 `apps/api/src/` 的抓取与转换逻辑：网页 → markdown → 文本块，这条链路就是「原始数据变成可训练文本」的最小实现'),
    },
    'ai-ch02': {
        TF: ('§1.1', '讲「卷积的计算量」时读 `tensorflow/python/keras/layers/convolutional/`：`Conv2D` 的 `call` 里就是「滑窗 + 乘加」，参数量 `k²·C_in·C_out` 与计算量 `k²·C_in·C_out·H·W` 的差别在这里能直接看出来'),
        HF: ('§2.2', '讲「从 RNN 到注意力」时读 `src/transformers/models/bert/` 与任一 RNN 模型的实现对比：注意力没有递归、整段并行，这是「训练能规模化」的根本原因'),
        LC: ('§3.2', '讲「序列建模的输入表示」时读 `libs/core/langchain_core/messages/`：把对话压成 token 序列时「角色 + 内容」的拼接方式，决定了模型看到的是什么'),
        DIFY: ('§4.1', '讲「视觉模型在应用里的位置」时读 `api/core/model_runtime/model_providers/`：多模态 provider 把图片转成 base64 或 URL 再送模型，本章「视觉 token 数决定成本」在这里变成计费口径'),
        AGPT: ('§4.2', '讲「序列决策」时看 agent 的「观察 → 思考 → 行动」循环：与 RNN 的「隐状态随步更新」结构同构，区别是隐状态换成了上下文窗口'),
        FC: ('§2.3', '讲「图文数据的采集」时读 `apps/api/src/` 的抓取输出：markdown 里保留图片链接，是「图文对」最廉价的来源，也解释了为什么多模态数据质量参差'),
    },
    'ai-ch03': {
        HF: ('§1.1', '讲「自注意力的实现」时读 `src/transformers/models/bert/modeling_bert.py` 的 `BertSelfAttention`：`query/key/value` 三个线性层 + `softmax(QKᵀ/√d)V`，与本章公式逐行对应'),
        TF: ('§2.2', '讲「缩放点积的数值行为」时读 `tensorflow/python/ops/nn_ops.py` 的 `softmax`：数值稳定实现会先减去最大值，这解释了「不缩放时 softmax 饱和」为什么会让梯度消失'),
        LC: ('§3.1', '讲「上下文窗口的代价」时读 `libs/core/langchain_core/` 的消息裁剪逻辑：超长上下文要做截断或摘要，本质是「注意力 O(n²) 的成本」在应用层的体现'),
        DIFY: ('§4.3', '讲「Transformer 在 RAG 里的位置」时读 `api/core/rag/`：检索出的片段被拼进 prompt，模型用注意力在这些片段上做「软对齐」——RAG 的效果上限由这一步决定'),
        AGPT: ('§4.1', '讲「长上下文的工程约束」时看 agent 的记忆管理：历史太长就摘要、关键信息单独存，与本章「KV Cache 随序列线性增长」是同一个约束的两种应对'),
        FC: ('§2.1', '讲「预处理对模型输入的影响」时读 `apps/api/src/` 的 markdown 清洗：去掉导航与广告后，进入上下文的 token 才是「有效信息」，这直接影响注意力的信噪比'),
    },
    'ai-ch04': {
        HF: ('§1.2', '讲「LoRA 的低秩分解」时读 `src/peft/`（PEFT 已并入 transformers 生态）的 `LoraLayer`：`A` 随机初始化、`B` 零初始化让「训练开始时等价于原模型」，这是 LoRA 能即插即用的关键'),
        TF: ('§2.3', '讲「RLHF 的奖励建模」时读 `tensorflow/python/keras/` 的自定义 loss 写法：奖励模型的训练目标是「偏好对排序」，loss 形式与本章的 Bradley-Terry 一致'),
        LC: ('§3.2', '讲「DPO 与 RLHF 的差别」时读 `libs/langchain/langchain/chains/` 里的偏好优化封装：DPO 直接用偏好对做监督式优化，省掉「训练奖励模型 + PPO」两步'),
        VLLM: ('§4.2', '讲「微调后的部署」时读 `vllm/lora/`：多 LoRA 适配器挂在同一基座上按请求切换，本章「合并导出 vs 分离挂载」的取舍在这里有工程实现'),
        LCPP: ('§4.3', '讲「量化微调的显存账本」时读 `src/llama.cpp` 的量化加载路径：4-bit 基座 + fp16 LoRA 是 QLoRA 的常见组合，显存占用可以直接对照本章公式'),
        LLAMA: ('§2.1', '讲「基座模型的训练流程」时读仓库里的模型并行实现：预训练 → SFT → 对齐三段式，本章讲的对齐只占最后一段'),
    },
    'ai-ch05': {
        LC: ('§1.1', '讲「提示模板的工程化」时读 `libs/core/langchain_core/prompts/`：`PromptTemplate` 把变量槽位与格式约束分开，避免「字符串拼接到处飞」'),
        DIFY: ('§2.2', '讲「少样本示例的组织」时读 `api/core/` 下的 prompt 编排模块：示例与指令分段存放、按场景组装，本章「例子要覆盖边界」在这里变成「示例集合的维护」'),
        AGPT: ('§3.1', '讲「CoT 与自洽性」时看 agent 的思考链：它把「先计划再执行」写进提示，与 CoT 的「显式中间步骤」是同一机制在不同尺度上的应用'),
        HF: ('§4.1', '讲「结构化输出的可靠性」时读 `src/transformers/generation/` 的约束解码相关实现：用语法约束 token 采样，比「请在 JSON 里回答」可靠得多'),
        TF: ('§2.3', '讲「温度与采样的影响」时读 `tensorflow/python/ops/` 的 `top_k`/`top_p` 实现：它们改的是分布形状，不是「准确性」——低温更确定但不一定更对'),
        FC: ('§4.2', '讲「提示注入的防护」时读 `apps/api/src/` 的内容清洗：抓来的网页文本可能含指令，必须与系统提示隔离，否则「数据」会被当成「命令」'),
    },
    'ai-ch06': {
        DIFY: ('§1.1', '讲「RAG 的四段流程」时读 `api/core/rag/`：`indexing`（分块+嵌入）、`retrieval`（向量+关键词）、`rerank`、`generate` 四个子目录就是本章流程的代码化'),
        LC: ('§2.2', '讲「分块策略」时读 `libs/langchain/langchain/text_splitter.py`：按字符/递归/按 token 三种切法各有实现，`chunk_overlap` 的作用在源码注释里写得很清楚'),
        HF: ('§3.1', '讲「向量检索的近似算法」时读 `src/transformers/` 与 `datasets` 的 FAISS 集成：HNSW/IVF 用「近似」换速度，召回率与延迟的权衡在这里可调'),
        AGPT: ('§4.1', '讲「检索结果怎么进 prompt」时看 agent 的记忆检索：Top-K 片段拼接、带来源标注，与本章「检索不到必然答错」的判断一致'),
        FC: ('§1.3', '讲「文档解析的质量」时读 `apps/api/src/` 的 HTML → markdown：解析质量直接决定「切出来的块是否有语义完整性」，这是 RAG 效果的第一道闸'),
        TF: ('§3.3', '讲「嵌入模型的训练」时读 `tensorflow/python/keras/` 的对比学习示例：双塔 + 对比损失，与本章「余弦相似度排序」的用法对应'),
    },
    'ai-ch07': {
        LC: ('§1.1', '讲「工具调用的抽象」时读 `libs/core/langchain_core/tools/`：工具 = 名称 + 描述 + 参数 schema + 执行函数，模型只负责「选哪个、传什么」，执行永远在服务端'),
        AGPT: ('§2.2', '讲「Agent 主循环」时看仓库里的 `run` 循环：规划 → 调工具 → 观察 → 再规划，直到「无需再调用工具」为止，本章的「状态机」就是它的形式化'),
        DIFY: ('§3.1', '讲「工作流编排」时读 `api/core/workflow/`：节点 + 边 + 变量传递，把「多步 Agent」画成图，比纯 prompt 更可控'),
        HF: ('§4.2', '讲「函数调用的模型侧支持」时读 `src/transformers/` 的 chat template：`tools` 字段被渲染成模型认识的格式，各家模板不同，这是「同一个工具定义换个模型就不work」的原因'),
        TF: ('§3.3', '讲「记忆的向量化存储」时读 `tensorflow/python/ops/` 的嵌入运算：短期记忆放上下文、长期记忆进向量库，与本章「两层记忆」的分工一致'),
        FC: ('§2.3', '讲「工具的实际形态」时读 `apps/api/src/` 的抓取接口：输入 URL、输出 markdown，是 Agent 最常用的工具之一，也最容易「超时/被墙」'),
    },
    'ai-ch08': {
        VLLM: ('§1.1', '讲「连续批处理」时读 `vllm/core/scheduler.py`：新请求随时插入、已完成的立即释放，与静态批处理相比吞吐能高数倍——本章的调度策略在这里有实现'),
        LCPP: ('§2.3', '讲「量化部署」时读 `src/llama.cpp` 的量化 kernel：Q4_K_M 之类的命名对应不同的分组尺度，精度损失与体积的权衡在 README 的表格里可查'),
        HF: ('§3.2', '讲「评测与可观测」时读 `src/transformers/trainer.py` 的 `evaluate`：指标计算与日志记录绑在训练循环上，推理侧要自己搭一套对应的观测'),
        LC: ('§4.1', '讲「LLM 应用的安全边界」时读 `libs/langchain/langchain/` 的 output parser 与 guard：解析失败要兜底、输出要过滤，不能假设模型一定守规矩'),
        DIFY: ('§4.2', '讲「提示缓存与成本」时读 `api/core/model_runtime/` 的调用封装：同样的系统提示重复发送可以命中上游缓存，这是「成本控制」最直接的一条'),
        TF: ('§2.1', '讲「推理与训练的资源差异」时读 `tensorflow/python/eager/` 的执行模式：推理不需要保留中间激活，显存占用远小于训练——本章的显存账本要分开算'),
    },
    'ai-ch12': {
        HF: ('§1.2', '讲「对话模板与 loss mask」时读 `src/transformers/models/*/tokenizer` 的 `apply_chat_template`：它按角色拼 token，非 assistant 部分要置 -100 不参与损失，本章的「移位一位」在这里落地'),
        DS: ('§2.1', '讲「数据集的组织」时读 `src/datasets/` 的 `map`/`filter`：合成数据要先去重、再按长度/质量过滤，`filter` 的批处理模式能把这步跑得很快'),
        VLLM: ('§3.2', '讲「合成数据的验证」时读 `vllm/` 的批量推理入口：用强模型生成、用规则或弱模型打分，是「合成数据规模化」的常见流水线'),
        LLAMA: ('§4.1', '讲「SFT 的数据格式」时读仓库里的训练脚本：`(prompt, response)` 对的组织方式决定了模型学到的是「补全」还是「对话」'),
    },
    'ai-ch13': {
        VLLM: ('§1.1', '讲「PagedAttention」时读 `vllm/attention/ops/paged_attn.py`：KV Cache 按固定大小块分配、用块表映射逻辑位置，消除「预留最大长度」造成的碎片——这是吞吐高的关键'),
        LCPP: ('§2.2', '讲「GGUF 与端侧部署」时读 `ggml/src/`：内存映射加载、按层量化，让 7B 模型能在消费级硬件上跑，本章的显存公式在端侧要换成「内存 + 带宽」'),
        MLC: ('§3.1', '讲「编译式推理」时读仓库里的 TVM 编译流程：把模型编译成目标硬件上的 kernel，与「通用 runtime 解释执行」是两条路线'),
        HF: ('§4.2', '讲「推理引擎的接口统一」时读 `src/transformers/generation/` 的 `generate`：参数的语义（`max_new_tokens`/`temperature`/`top_p`）在各引擎间要对齐，否则「换个引擎效果就变」'),
    },
}

if __name__ == '__main__':
    apply('fundamentals', FUND)
    apply('ai', AI)
    sys.exit(0)
