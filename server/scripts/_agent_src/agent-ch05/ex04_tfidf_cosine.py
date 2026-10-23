# title: 手写 TF-IDF 向量与余弦：不去掉高频词，营销长文会排到显存文档前面
# 同一个分词（字符二元组）、同一个余弦公式，只切换词权重：原始词频 vs TF-IDF。
# 语料是 5 篇自造文档，其中 D5 是一篇反复出现「模型」但没讲显存算法的产品介绍。
import math
import re

DOCS = [
    ("D1", "7B 模型以 FP16 加载时权重约 14GB，4090 的 24GB 显存里权重占大头，激活与 KV Cache 再占一部分。"),
    ("D2", "14B 模型权重约 28GB，单卡 24GB 显存放不下，必须量化到 INT4 或者上双卡。"),
    ("D3", "显存占用要拆成权重、KV Cache、激活三块分别计算，再乘并发数看峰值。"),
    ("D4", "推理服务的显存监控要看分配器的预留量，不能只看 nvidia-smi 显示的数字。"),
    ("D5", "我们的模型平台提供模型训练、模型压缩、模型部署、模型评测、模型监控、模型版本管理、模型灰度、模型回滚，模型能力覆盖全流程。平台也支持显存查看，欢迎试用我们的模型产品。"),
]

QUERY = "模型显存占用怎么算"


def tokenize(text):
    toks = []
    for m in re.finditer(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        s = m.group(0)
        if re.match(r"[a-z0-9_]", s):
            toks.append(s)
        else:
            toks.extend(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else toks.append(s)
    return toks


TOK = [tokenize(t) for _, t in DOCS]
VOCAB = {}
for ts in TOK:
    for w in set(ts):
        VOCAB.setdefault(w, len(VOCAB))
N, V = len(DOCS), len(VOCAB)

DF = {w: 0 for w in VOCAB}
for ts in TOK:
    for w in set(ts):
        DF[w] += 1

# 这里用 log(N/df)+1：df=N 时权重为 1（不是 0），保留词但压低它的区分度
IDF = {w: math.log(N / DF[w]) + 1.0 for w in VOCAB}


def vec(tokens, use_idf):
    v = [0.0] * V
    for w in tokens:
        if w not in VOCAB:      # 查询里的跨词二元组（如「型显」）在语料中不存在，直接丢弃
            continue
        v[VOCAB[w]] += 1.0
    if use_idf:
        for w, i in VOCAB.items():
            v[i] *= IDF[w]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def ranking(use_idf):
    q = vec(tokenize(QUERY), use_idf)
    scores = [(did, cosine(vec(ts, use_idf), q)) for (did, _), ts in zip(DOCS, TOK)]
    return sorted(scores, key=lambda x: -x[1])


print(f"词表 {V} 维（字符二元组），文档 {N} 篇，查询：{QUERY}")
print(f"「模型」出现于 {DF['模型']}/{N} 篇，idf={IDF['模型']:.2f}；"
      f"「显存」出现于 {DF['显存']}/{N} 篇，idf={IDF['显存']:.2f}")
print(f"「占用」出现于 {DF['占用']}/{N} 篇，idf={IDF['占用']:.2f}")

for label, use_idf in (("原始词频 TF", False), ("TF-IDF", True)):
    print(f"\n{label} 的余弦排序：")
    for i, (did, sc) in enumerate(ranking(use_idf), 1):
        print(f"  {i}. {did}  cos={sc:.3f}")

tf = ranking(False)
tfidf = ranking(True)
print(f"\nD5 在原始词频下排第 {[d for d, _ in tf].index('D5') + 1}，"
      f"在 TF-IDF 下排第 {[d for d, _ in tfidf].index('D5') + 1}。")
print(f"D5 的「模型」词频是 D1 的 8 倍，长度也是 3 倍；不做 IDF，长文只靠重复一个词就能赢。")
print("\n读法：IDF 的作用不是『降权所有常见词』，而是把『在每篇里都有』的词压到接近常数——")
print("它们不携带区分信息，却会因为长度和重复次数主导余弦。")
print("注意：TF-IDF 仍然是词袋，无法处理『权重占大头』和『放不下』这种语义；")
print("它适合做第一路召回，不适合单独决定最终排序。")
print("\n结论：手写 TF-IDF 只要 30 行，但两个坑必须踩过——词表要按语料建（线上查询的未登录词会被丢掉），")
print("以及归一化要放在加权之后，否则长文档的范数会把相似度整体压低。")
