# 检索侧：混合检索、融合与重排，把对的内容捞上来

检索侧回答一个问题：给定一个查询，如何从百万级块里找出「最可能对」的 Top-K。
单一检索器都有盲区——BM25 强在精确词面匹配但不懂语义，向量检索懂语义但漏精确词面，
所以工程上几乎都用**混合检索 + 融合 + 重排**三段式。

```
query
  ├─ BM25 召回 ──────┐
  └─ 向量召回 ───────┤
                     ▼
               RRF 融合（无分值、只看排名）
                     ▼
          cross-encoder 重排（Top-N 精读）
                     ▼
                  Top-K 喂给 LLM
```

## 主题一：BM25 与向量检索，为什么必须混合

**中立陈述。** BM25 是一种基于词频-逆文档频率的排序函数，对「精确词面 + 稀有词」极其敏感：
查「GB/T 28181 协议」，BM25 能精准命中含该字符串的块，而向量检索可能因该术语在语料里稀少、
表征模糊而漏掉。向量检索（双塔 / bi-encoder）把 query 和 doc 各自编码成向量，用余弦相似度召回，
擅长「同义改写、跨表述」：查「怎么重置密码」能命中「找回登录口令的方法」。

BM25 得分（简化，含词频饱和与文档长度归一）：

```
score(D, Q) = Σ_{t∈Q} IDF(t) · (f(t,D)·(k1+1)) / (f(t,D) + k1·(1 - b + b·|D|/avgdl))
IDF(t) = ln( (N - n(t) + 0.5) / (n(t) + 0.5) + 1 )
```

其中 `k1`（通常 1.2~2.0）控制词频饱和，`b`（通常 0.75）控制长度惩罚。
向量检索则用余弦相似度 `sim = (q·d) / (|q||d|)`，相似度越高越相关。

中文 BM25 的关键前置是**分词**：英文天然按空格，中文需要二元组（bigram）或分词器。
经验判断：对专业术语密集的语料，二元组分词比通用分词器的 BM25 召回更稳，因为它不依赖词典对新术语的覆盖。

```python
import math
def bm25(query_terms, tf, df, N, doc_len, avgdl, k1=1.5, b=0.75):
    score = 0.0
    for t in query_terms:
        if t not in df:
            continue
        idf = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
        f = tf.get(t, 0)
        denom = f + k1 * (1 - b + b * doc_len / avgdl)
        score += idf * (f * (k1 + 1)) / denom
    return score

def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
```

| 检索器 | 擅长 | 短板 | 成本 |
|---|---|---|---|
| BM25 | 精确词面、稀有术语、编号/公式 | 不懂同义改写 | 极低（可 CPU） |
| 向量（bi-encoder） | 语义同义、跨表述 | 漏精确词面、稀有词表征弱 | 中（需 embedding） |
| 混合 | 覆盖两者盲区 | 需融合与去重 | 两者之和 |

### 🧑‍💻 程序员视角

真实系统里，纯向量检索最大的坑是「召回率天生低于 BM25 精确匹配」：
产品文档里满屏的「错误码 E1234」「配置项 max_connections」，向量检索经常把它当成普通词糊掉，
而 BM25 一击命中。所以别迷信「全向量」，先把 BM25 加上，混合召回率通常能再涨 5~10 个点。
另一个性能账：BM25 可以纯内存跑（倒排索引），向量检索要么上向量库（HNSW/IVF）要么暴力算，
百万级以下暴力余弦在 numpy 上也够快，别一上来就引重型依赖。注意中文一定要先分词再进 BM25，
否则按字符粒度算，词频信号全失真。

### 🎓 博士生视角

双塔（bi-encoder）与交叉编码器（cross-encoder）的根本区别在**交互时机**。
双塔在编码阶段就让 query 与 doc 分离，相似度只是两个独立向量的点积，无法建模细粒度词对齐，
故召回快但精度有限；cross-encoder 把 query+doc 拼在一起过一次 Transformer，
能捕捉「这个词对那个词」的交互，精度高但无法预计算 doc 向量，只能对少量候选重排。
这正是「双塔做粗排召回、cross-encoder 做精排」的理论依据。向量召回率上限还受 embedding 对比学习
负样本策略影响——难负例不足时，模型对细差异不敏感，正是 BM25 能补的盲区。

### 📚 考研者视角

常考 BM25 公式里的 `k1` 与 `b` 各自管什么：`k1` 管词频饱和（词出现越多得分越高但有上限），
`b` 管长度归一（长文档不因词多而虚高）。计算题会给 tf、df、N、doc_len、avgdl 让你手算某一词的贡献，
记得先算 IDF 再看饱和项。易混点：BM25 的「逆文档频率」与 TF-IDF 的 IDF 形式不同（加了平滑 +1），
别直接套 TF-IDF 公式。向量检索部分考余弦定义与「为什么归一化后点积=余弦」，这是基础送分题。

## 主题二：RRF 融合与 cross-encoder 重排的性价比

**中立陈述。** 混合检索得到两个排名列表，需要合成一个。
**RRF（Reciprocal Rank Fusion）** 是最稳的工程选择：它不依赖各检索器的分值量纲，只看排名：

```
RRF_score(d) = Σ_{r ∈ 检索器} 1 / (k + rank_r(d))
```

默认 `k = 60`。一个在 BM25 排第 1、向量排第 50 的文档，RRF 得分仍由 BM25 的高排名主导，
避免了「向量分值普遍比 BM25 大十倍」导致的量纲碾压。

RRF 之后接**重排（rerank）**：取融合后的 Top-N（通常 20~50），用 cross-encoder 对
「query, doc」逐对打分，按精排分取最终 Top-K。重排的性价比账在于——
cross-encoder 延迟约为双塔的十倍，但只对 Top-N 跑，绝对耗时可控；
把 N 卡在 20 以内，精排带来的精度收益远大于那点延迟。

```python
def rrf(rank_lists, k=60):
    score = {}
    for ranks in rank_lists:          # ranks: 文档id按排名顺序的列表
        for rank, doc_id in enumerate(ranks, 1):
            score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(score, key=score.get, reverse=True)

def rerank_cross_encoder(query, docs, top_n=20):
    # 本地模拟：用 query-doc 词重叠度近似 cross-encoder 相关性
    def score(q, d):
        qs = set(q); return sum(1 for w in d if w in qs) / max(1, len(d))
    ranked = sorted(docs, key=lambda d: score(query, d), reverse=True)
    return ranked[:top_n]
```

| 环节 | 输入规模 | 延迟量级 | 作用 |
|---|---|---|---|
| 向量召回 | 全库 | 低 | 粗筛语义相关 |
| BM25 召回 | 全库 | 极低 | 粗筛词面相关 |
| RRF 融合 | 两路 Top-K | 极低 | 统一排名、去量纲 |
| cross-encoder 重排 | 融合 Top-N | 高（×10） | 精排、提精度 |

### 🧑‍💻 程序员视角

RRF 的 `k=60` 不是玄学，是经验默认；如果你的两路检索分值量级差特别大，
直接按分值加权相加会被一路碾压，RRF 只认排名反而更稳——这也是它受欢迎的原因。
重排最容易写错的是「对全库跑 cross-encoder」：线上一旦忘了截断 Top-N，延迟直接炸。
我的做法是融合后硬截断 20，再重排，P95 稳定。还有个坑：重排模型输出的是相对分，
不要拿它和 BM25 的原始分混在一起再排序，两段必须各算各的、各管各的阶段。

### 🎓 博士生视角

RRF 属于「无监督融合」，不需要训练，对检索器误差有鲁棒性；
更优但有成本的方案是学习排序（learning-to-rank）融合，需要标注数据且易过拟合某一检索器分布。
cross-encoder 的精度优势来自深层交互，但它是非对称、不可预计算的，
因此天然适合放在召回-重排两阶段管线的末端。值得注意：重排的上限受限于召回阶段有没有把正确答案放进 Top-N，
若正确答案根本没进 Top-N，重排再强也救不回——这再次印证「检索是天花板，重排是放大器」。

### 📚 考研者视角

RRF 公式必须会默写：`1/(k+rank)` 累加，`k` 默认 60。
辨析题常考「为什么不用分值加权平均而用 RRF」——答「不同检索器分值量纲/分布不同，直接相加会被一路主导，
RRF 只看排名、免归一化」。重排部分考「为什么 cross-encoder 不能替代双塔做全库检索」：
答「双塔可预计算 doc 向量、支持近似最近邻；cross-encoder 需 query-doc 同框编码、不可预计算、延迟高，
只能精排少量候选」。这组对比是面试/笔试高频。

## 主题三：查询改写与多跳，补召回的最后一公里

**中立陈述。** 用户问句常与文档表述不一致：「这玩意儿怎么连不上网」vs 文档里的「无线网卡驱动异常排查」。
**查询改写（query rewriting）** 用同义词表、拼写纠正或 LLM 把原始 query 扩写成若干检索友好的变体，
再分别检索后合并。对「跨文档才能答」的问题，需要**多跳（multi-hop）** 检索：
先检索出第一跳证据，从中抽取子问题，再检索第二跳，直到能合成答案。
多跳的代价是指数级候选与误差累积，工程上常用「限定跳数 + 每跳只取 Top-K + 早停」来控制。

```python
SYNONYMS = {"连不上网": "无线网卡 驱动 异常", "登不进": "登录 失败 密码 重置"}

def rewrite(query):
    out = [query]
    for k, v in SYNONYMS.items():
        if k in query:
            out.append(query.replace(k, v))
    return out

def multi_hop(query, retriever, max_hop=2, top_k=3):
    evidences = []
    for _ in range(max_hop):
        hits = retriever(query)[:top_k]
        if not hits:
            break
        evidences.extend(hits)
        query = extract_subquery(hits)   # 从证据里抽下一跳问题（本地模拟）
    return evidences
```

### 🧑‍💻 程序员视角

查询改写最便宜的版本是同义词表，别一上来就调 LLM 改写——同义词表零延迟、可审计、可控。
真正要小心的是「改写后召回爆炸」：一个 query 扩成 8 个变体，每个检索 Top-20，合并去重前就是 160 条，
重排窗口被撑爆。我的经验是改写变体控制在 2~3 个、合并后统一截断。
多跳更危险的是误差累积：第一跳错了，后面全歪。所以多跳要有「置信度阈值」，
低置信就早停并触发拒答，而不是硬编一个答案。

### 🎓 博士生视角

查询改写可视为检索侧的「query 端数据增强」，与训练时的难负例挖掘思路相通：
它弥补了用户表述与文档表述之间的词汇鸿沟（vocabulary mismatch）。
多跳检索与「推理检索（reasoning over passages）」相关，其理论瓶颈是
「每跳只取 Top-K 带来的信息损失随跳数指数放大」，所以前沿工作多在解决
「何时该跳、何时该停」的决策问题，而非无脑加深跳数。

### 📚 考研者视角

简答题框架：「查询改写解决词汇鸿沟，多跳解决跨文档推理」。
计算/设计题可能让你给同义词表写改写并算合并后候选数（变体数 × Top-K，再去重），
注意「去重」这步常被漏掉而多算。易混：查询改写≠重排，前者在检索前扩 query，后者在检索后对候选精排，
阶段完全不同，别在名词对应上丢分。

## 小结

检索侧的三段式——混合召回补盲区、RRF 融合去量纲、cross-encoder 重排提精度——
是当下最稳的工业配方。再往前一步是查询改写与多跳，补「表述不一致」和「跨文档」两类召回缺口。
但记住：所有这些都只在「正确答案进了融合 Top-N」的前提下有效，检索召回的上限仍是数据侧定的。
