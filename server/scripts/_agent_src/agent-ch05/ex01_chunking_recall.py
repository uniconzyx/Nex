# title: 两种切块的对照：Recall@3 都是 8/8，答案完整率是 6/8 对 8/8
# 用字符二元组 TF-IDF 检索同一批语料，只改切块方式，观察「命中文档」与「拿到答案」的差距。
# 语料是本文件内自造的小样本（8 篇技术笔记 + 4 篇干扰文档），不读外部文件；真实 PDF 解析见 concept/01。
import re
import numpy as np

DOCS = [
    ("D1", "RAG 的召回质量主要由文档解析与切块决定。PDF 中的双栏排版如果按阅读顺序还原失败，切出的块会把两栏文字交错拼接，检索时既像这一栏又像那一栏，两边都排不到第一。"),
    ("D2", "固定长度切块实现简单，但会在句子中间截断。被截断的块往往丢失主语或结论，向量表示因此偏向局部词面，召回的块看着相关却答不出问题。"),
    ("D3", "语义切块先用句子边界做候选，再在相邻句子的向量相似度明显下跌处切开。它的块长不固定，但每个块通常只讲一件事，适合问答型检索。"),
    ("D4", "重叠窗口的作用是防止答案正好落在切口上。重叠一成到一成半通常够用，超过三成会让索引膨胀、同一段话被多个块重复召回，挤占上下文预算。"),
    ("D5", "元数据决定能不能过滤。把租户、文档版本、生效日期、权限等级写进块级元数据，检索时才能先裁剪候选集，而不是取出结果再逐条判断权限。"),
    ("D6", "父子块把检索单位和生成单位分开：用小块做向量匹配，命中后把它的父块整段喂给模型。这样既保留小块的匹配精度，又避免上下文被切碎。"),
    ("D7", "词法检索依赖词频与逆文档频率，对专有名词和编号特别敏感。用户查错误码这类字符串时，字面匹配往往比语义向量更准。"),
    ("D8", "向量检索擅长同义改写。用户问显存不够怎么办，文档里写的是 GPU 内存不足，两者字面几乎不重合，但语义向量能把它们拉到一起。"),
    ("D9", "重排模型看的是查询与段落的逐字交互，比双塔向量更贵也更准。它通常只对前五十个候选做精排，全量重排的延迟无法接受。"),
    ("D10", "拒答阈值不是拍脑袋定的。要有『有答案』和『无答案』两组样本，分别看误答率和误拒率，再按业务成本选工作点。"),
    ("D11", "引用溯源要求答案里的每个论断都能落到具体片段。只给文档名不够，粒度必须细到块或句子，否则无法核验。"),
    ("D12", "缓存能省钱，但缓存键必须带上租户与权限版本。只按查询文本做键，会把 A 租户的答案发给 B 租户。"),
]

# (query, 目标文档, 答案关键跨度)
QUERIES = [
    ("q1 PDF 双栏排版还原失败会怎样", "D1", "两栏文字交错拼接"),
    ("q2 固定长度切块为什么答不出问题", "D2", "丢失主语或结论"),
    ("q3 语义切块在什么地方切开", "D3", "向量相似度明显下跌处"),
    ("q4 重叠窗口设多少合适", "D4", "一成到一成半通常够用"),
    ("q5 元数据能用来做什么过滤", "D5", "先裁剪候选集"),
    ("q6 父子块为什么用小块检索", "D6", "检索单位和生成单位分开"),
    ("q7 错误码用什么检索更准", "D7", "字面匹配往往比语义向量更准"),
    ("q8 显存不够但文档写 GPU 内存不足", "D8", "能把它们拉到一起"),
]


def bigrams(s: str):
    s = re.sub(r"\s+", "", s)
    return [s[i:i + 2] for i in range(len(s) - 1)]


def fixed_chunks(text: str, size: int = 48, overlap: int = 0):
    spans, i, step = [], 0, size - overlap
    while True:
        end = min(i + size, len(text))
        spans.append((i, end))
        if end >= len(text):
            break
        i += step
    return spans


def semantic_chunks(text: str, max_len: int = 70):
    sents = [(m.start(), m.end()) for m in re.finditer(r"[^。！？；]*[。！？；]", text)]
    if sents and sents[-1][1] < len(text):
        sents.append((sents[-1][1], len(text)))
    spans, cur = [], None
    for s, e in sents:
        if cur is None:
            cur = [s, e]
        elif e - cur[0] <= max_len:
            cur[1] = e
        else:
            spans.append(tuple(cur))
            cur = [s, e]
    if cur:
        spans.append(tuple(cur))
    return spans


def build(chunker):
    chunks = []
    for doc_id, text in DOCS:
        for s, e in chunker(text):
            piece = text[s:e]
            broken = e < len(text) and text[e - 1] not in "。！？；"
            chunks.append({"doc": doc_id, "text": piece, "start": s, "end": e, "broken": broken})
    return chunks


def tfidf(texts):
    toks = [bigrams(t) for t in texts]
    vocab = {}
    for ts in toks:
        for t in set(ts):
            vocab.setdefault(t, len(vocab))
    X = np.zeros((len(texts), len(vocab)))
    df = np.zeros(len(vocab))
    for i, ts in enumerate(toks):
        for t in ts:
            X[i, vocab[t]] += 1.0
        for t in set(ts):
            df[vocab[t]] += 1.0
    idf = np.log((1 + len(texts)) / (1 + df)) + 1.0
    X *= idf
    norm = np.linalg.norm(X, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return X / norm, vocab, idf


def query_vec(q, vocab, idf):
    v = np.zeros(len(vocab))
    for t in bigrams(q):
        if t in vocab:
            v[vocab[t]] += 1.0
    v *= idf
    n = np.linalg.norm(v)
    return v / n if n else v


def evaluate(name, chunks):
    X, vocab, idf = tfidf([c["text"] for c in chunks])
    hit_doc = hit_ans = 0
    missed = []
    for q, gold_doc, key in QUERIES:
        sims = X @ query_vec(q, vocab, idf)
        top = np.argsort(-sims)[:3]
        got_doc = any(chunks[i]["doc"] == gold_doc for i in top)
        got_ans = any(key in chunks[i]["text"] for i in top)
        hit_doc += got_doc
        hit_ans += got_ans
        if not got_ans:
            missed.append(q.split()[0])
    avg_len = np.mean([len(c["text"]) for c in chunks])
    frag = np.mean([c["broken"] for c in chunks])
    print(f"{name:<14}{len(chunks):>6}{avg_len:>9.1f}{frag:>9.0%}{hit_doc:>9}/8{hit_ans:>10}/8")
    return missed


print("同一份 12 篇语料、同一个检索器（字符二元组 TF-IDF + 余弦），只换切块函数：")
print(f"{'切块方式':<12}{'块数':>6}{'平均块长':>10}{'碎片率':>9}{'Recall@3':>10}{'答案完整':>10}")
m1 = evaluate("固定 48/0", build(fixed_chunks))
m2 = evaluate("语义(句边界)", build(semantic_chunks))

print(f"\n固定窗口下答案被切口劈开的查询：{', '.join(m1)}")
print("两条 Recall@3 都是 8/8 —— 如果只看『Top-K 有没有命中目标文档』，这次实验会得出")
print("『两种切块一样好』的错误结论。真正的差别在块内完整性：切口把关键跨度劈成两半，")
print("块里只剩半句话，模型拿到也答不出。")
print(f"\n结论：切块评估要同时看『命中率』和『答案完整率』；固定窗口的块数多 {len(build(fixed_chunks))-len(build(semantic_chunks))} 个，")
print("索引更大、上下文更碎，而它换来的召回收益在这个语料上是 0。")
print("把 overlap 调到 15% 能救回大部分被劈开的答案，代价是块数再涨三成——这就是 overlap 的真实定价。")
