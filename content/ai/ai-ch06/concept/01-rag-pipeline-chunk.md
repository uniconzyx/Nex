# RAG 全流程与分块策略

## 主题一：RAG 的两条链路——索引与查询

RAG（Retrieval-Augmented Generation）把「参数记忆」改成「上下文证据」：先检索再生成。
索引链路（离线）：文档解析 → 分块（chunk） → 向量化（embedding） → 写入向量库。
查询链路（在线）：用户 query → 向量化 → 检索 top-k → （可选重排 rerank） → 拼接进 prompt → LLM 生成。
检索质量决定回答上限，生成质量决定下限；二者解耦，可独立优化。

### 🧑‍💻 程序员视角
工程决策清单：
- **chunk 策略与重叠**：固定长度 + 10%~20% 重叠最常用；重叠是为了不把一句话劈成两半，但重叠过大会引入重复 token、抬高成本。
- **embedding 维度选择**：维度直接决定存储与检索成本（见 ex09），优先选支持 Matryoshka 表示的模型，按需截断。
- **top-k 与重排**：先召回 top-50~100 粗排，再用交叉编码器重排到 top-5~10 喂给 LLM；top-k 太小漏召回、太大稀释 prompt。
- **向量库选型与成本**：百万级文档用 HNSW（内存换延迟），亿级用 IVF+PQ（压缩换内存）；上线前务必做「有无检索」的对照实验。

### 🎓 博士生视角
第一性原理：检索之所以能减幻觉，是因为把生成的条件分布从 p(y|x) 改写为
p(y|x,q,D) = Σ_{d∈D} p(d|q) · p(y|d,x)，把「凭记忆猜」改成「凭检索到的证据推」。
早期 DPR/RAG 把检索器与生成器联合训练，本质是让检索分布对齐生成所需证据；现代做法多用冻结的强 embedding + 轻量重排。

### 📚 考研者视角
笔面标准口径：
- **RAG 定义**：检索增强生成，先从不限来源的语料中检索相关证据，再交给 LLM 生成，缓解知识过时与幻觉。
- **与微调的区别**：RAG 注「知识」（私有/实时），微调改「行为」（语气/格式/决策偏好）；口诀「注知识用 RAG、改行为用微调」。
- **全流程步骤**：离线建库（解析→分块→向量化→入库）、在线检索（query 向量化→召回→重排→拼接→生成）。
- **易错点**：把「检索」和「生成」混为一谈，以为 RAG 就是「把文档丢给大模型」。

## 主题二：分块（chunk）策略与粒度

chunk 是把长文档切成可检索片段的基本单元。常见四类：固定长度（按 token/字符）、结构感知（按标题/段落/Markdown 节点）、
语义分块（按 embedding 相似度断点）、父子块（parent-child：小块用于精准召回、大块用于完整喂入）。
块太大→噪声多、top-k 精度下降；块太小→语义碎片化、丢失长程依赖。

### 🧑‍💻 程序员视角
工程惯例：
- 重叠 10%~20%，且按「句子/段落边界」回退，避免硬切切断语义。
- chunk 大小常用 200~512 token，长文档配父子块（小块检索、大块喂入）。
- 元数据（来源、时间戳、章节）必须跟着 chunk 走，检索后可做过滤与溯源。
- 高频坑：用固定 token 数硬切却忽略句子边界，把一句话劈成两半。

### 🎓 博士生视角
信息论视角：分块是「检索粒度」与「上下文完整性」的权衡。块太小，条件熵 H(y|d,x) 偏高（证据不足）；
块太大，检索信号被稀释、信噪比下降。最优块长取决于文档自相关尺度与模型上下文预算。

### 📚 考研者视角
笔面口径：
- **chunk 大小的影响**：过大→召回噪声大、单块 token 成本高；过小→上下文割裂、语义不完整。
- **重叠（overlap）的作用**：减少边界切断造成的语义丢失，但会增加存储与重复计算。
- **易错点**：认为「越细的块召回越准」——过细会把实体关系拆散，反而损害多跳问答。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 相似度度量对比：余弦 / 内积 / L2 的等价关系

```python
import numpy as np
rng = np.random.default_rng(42)
D = 8
docs = rng.standard_normal((5, D))
q = rng.standard_normal(D)

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

cos_scores = [cosine(q, d) for d in docs]
ip_scores = [float(np.dot(q, d)) for d in docs]
l2_scores = [float(np.linalg.norm(q - d)) for d in docs]

rank_cos = [i for i, _ in sorted(enumerate(cos_scores), key=lambda x: -x[1])]
rank_ip = [i for i, _ in sorted(enumerate(ip_scores), key=lambda x: -x[1])]
rank_l2 = [i for i, _ in sorted(enumerate(l2_scores), key=lambda x: x[1])]

qn = q / np.linalg.norm(q)
dn = docs / np.linalg.norm(docs, axis=1, keepdims=True)
ip_norm = [float(np.dot(qn, d)) for d in dn]
rank_ipn = [i for i, _ in sorted(enumerate(ip_norm), key=lambda x: -x[1])]

print('文档数 = %d  维度 = %d' % (len(docs), D))
print('余弦相似度 =', [round(x, 4) for x in cos_scores])
print('内积 =', [round(x, 4) for x in ip_scores])
print('L2 距离 =', [round(x, 4) for x in l2_scores])
print('余弦排名(降序) =', rank_cos)
print('内积排名(降序) =', rank_ip)
print('L2排名(升序) =', rank_l2)
print('归一化后 余弦排名 == 内积排名 =', rank_cos == rank_ipn)
print('L2排名(升序) 与 余弦排名(降序) 一致 =', rank_l2 == rank_cos)
```

实际输出：

```text
文档数 = 5  维度 = 8
余弦相似度 = [-0.2554, -0.1326, 0.006, 0.3168, -0.5575]
内积 = [-1.0912, -0.411, 0.0174, 1.1388, -1.7406]
L2 距离 = [3.555, 2.7158, 2.4548, 2.402, 3.1775]
余弦排名(降序) = [3, 2, 1, 0, 4]
内积排名(降序) = [3, 2, 1, 0, 4]
L2排名(升序) = [3, 2, 1, 4, 0]
归一化后 余弦排名 == 内积排名 = True
L2排名(升序) 与 余弦排名(降序) 一致 = False
```

> 出处：`examples/ex01-similarity-metrics.json`。改一处再看输出变没变，比读三遍解释有用。

### 余弦相似度手算：点积、模长与余弦值

```python
import numpy as np
q = np.array([1.0, 2.0, 3.0, 4.0])
d = np.array([2.0, 0.0, 1.0, 3.0])
dot = float(np.dot(q, d))
nq = float(np.linalg.norm(q))
nd = float(np.linalg.norm(d))
cos = dot / (nq * nd)
print('q =', q.tolist())
print('d =', d.tolist())
print('点积 q·d = %.4f' % dot)
print('|q| = %.4f  |d| = %.4f' % (nq, nd))
print('cos(q,d) = %.4f / (%.4f * %.4f) = %.4f' % (dot, nq, nd, cos))
```

实际输出：

```text
q = [1.0, 2.0, 3.0, 4.0]
d = [2.0, 0.0, 1.0, 3.0]
点积 q·d = 17.0000
|q| = 5.4772  |d| = 3.7417
cos(q,d) = 17.0000 / (5.4772 * 3.7417) = 0.8295
```

> 出处：`examples/ex02-cosine-manual.json`。改一处再看输出变没变，比读三遍解释有用。

