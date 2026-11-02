# §4 ai-ch12 实战手记：凯喵带你把 LLM 评测用「虚高」

> 前三节把任务 schema、合成过滤去重、难负例与 Kappa 讲透了。这一节凯喵把评测最容易「刷出假 SOTA」的 12 个现场摆出来——每个都是 benchmark 翻车的前兆。

### 现场一：评测集被训练集污染，分数虚高到离谱

凯喵的模型在某个 QA 集上刷到 95%，一查发现测试题以「同义改写/换数字」形式早就躺在训练集里。整句相等的检测永远 False，污染被完全漏检。正确做法：用 token 级重叠率（Jaccard≥0.5）或 n-gram 子串包含判污染，检测到即剔除，评测集保持「疫苗级」干净。

```python
def contaminated(a: str, b: str, n=5) -> bool:
    def ngrams(s, n): return set(s[i:i+n] for i in range(len(s)-n+1))
    ga, gb = ngrams(a), ngrams(b)
    return len(ga & gb) / max(1, len(ga | gb)) >= 0.5   # Jaccard 阈值
```

### 现场二：只报均值不报方差，结论不可信

凯喵发版说「准确率提升 2%」，结果换批随机种子就掉回去。评测样本只有几百条时，单次均值波动极大。正确做法：跑多次（不同 seed / 不同 split）报均值±标准差，或做显著性检验（如 bootstrap），n 小更要保守。

```python
import numpy as np
scores = [eval_once(seed=s) for s in range(5)]
print(f"acc={np.mean(scores):.1%}±{np.std(scores):.1%}")  # ✅ 带置信区间
```

### 现场三：用准确率评不平衡数据，瞎猜也有 99%

凯喵做风控分类报「准确率 99%」，其实负样本占 1%，全猜正常就 99%。不平衡数据要看 **PR 曲线 / F1 / AUC**，或加权损失。准确率在类别均衡时才直观。

```python
from sklearn.metrics import f1_score, average_precision_score
print("F1=", f1_score(y, pred, average="macro"))
print("AP=", average_precision_score(y, prob))   # PR-AUC，对不平衡友好
```

### 现场四：合成数据不过滤，模型学了一堆重复模板

凯喵用 LLM 批量造训练样本，结果模型只会背模板，泛化崩盘。合成数据必须**去重 + 多样性过滤 + 质量打分**，并和真实数据混合，比例要消融实验定。

```python
# 简单去重：按语义哈希或聚类
seen = set()
for item in synthetic:
    h = hash(embed(item)[:8].tobytes())
    if h not in seen: seen.add(h); keep.append(item)
```

### 现场五：难负例没挖，检索召回全是送分题

凯喵做向量检索评测，召回率虚高，因为负例都是「毫不相干」的随机样本。真实场景负例是**语义相近但错误**的难负例。用难负例挖掘（hard negative mining）才贴近线上。

```python
# 取与 query 最相近但不是正例的样本为难负例
cands = index.search(q_emb, k=50)
hard = [c for c in cands if c not in positives][:5]   # 最易混淆的
```

### 现场六：人工标注一致性（Kappa）太低，标签本身不可信

凯喵的标注两个标注员同意率 60%，看似不低，但随机也能撞 55%，真实一致性极低。用 **Cohen's Kappa** 排除随机吻合：κ<0.6 标签不可信，先统一标注规范再训。

```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(y_a, y_b)
print(kappa)   # <0.6 说明标注协议有问题，先别训
```

### 现场七：测试集泄漏进 few-shot 示例，评测失真

凯喵在 prompt 里塞了几个「示例」，恰好和测试题同分布甚至同款，分数虚高。few-shot 示例必须来自**训练/验证集**，和测试题严格隔离，避免 inadvertently 泄题。

```python
# few-shot 只从 train 取，绝不碰 test
demos = random.sample(train_samples, k=3)
prompt = build_prompt(demos, test_query)   # ✅ 隔离
```

### 现场八：只评最终答案不评过程，错误答案蒙混过关

凯喵评数学题只看最终数字，模型「过程全错、最后瞎蒙对」也拿分。关键任务要评**推理链**（分步打分 / LLM-as-judge 过程分），避免结果偶然正确掩盖能力缺陷。

```python
# 过程 + 结果双评分
score = 0.7 * judge_steps(chain) + 0.3 * (final_correct)
```

### 现场九：LLM-as-judge 自己有偏好，给自家模型放水

凯喵用 GPT-4 当评委，发现自己模型分高、竞品分低，结果评委本身对自家格式有偏好。缓解：盲评（隐去模型名）、多评委交叉、关键项人工复核、用更难的判别任务而非开放式打分。

```python
# 盲评：打乱顺序、隐去来源
pairs = shuffle([("A", ans_a), ("B", ans_b)])
verdict = judge_blind(pairs)   # 不让评委知道谁是谁
```

### 现场十：指标选错，生成质量和「像不像人」混为一谈

凯喵用 BLEU 评开放生成，分数低但人读着挺好——BLEU 偏向 n-gram 重叠，对多样性生成天然不友好。生成质量要组合 **BLEU/ROUGE（重叠）+ BERTScore（语义）+ 人工**，别单靠一个指标拍板。

```python
from bert_score import score
P, R, F1 = score(cands, refs, lang="zh")   # 语义相似度补充 n-gram 指标
```

### 现场十一：样本量太小，误差棒比提升还大

凯喵拿 50 条测试集宣称「超越 SOTA 1 分」，这 1 分完全在噪声里。报告提升必须配样本量和置信区间；差异小就老老实实说「无显著区别」。

```python
import scipy.stats as st
# 两模型配对 t 检验，看差异是否显著
t, p = st.ttest_rel(scores_a, scores_b)
print("p=", p)   # p>0.05 不能声称更好
```

### 现场十二：只跑一个数据集，结论外推过度

凯喵在一个英文集上验证就写「全面领先」，结果中文集上一塌糊涂。评测要覆盖**多数据集、多语言、多领域**，报告分数据集结果，别用单点结论代表全局。

```python
for ds in ["mmlu", "cmmlu", "gsm8k", "bbh"]:
    print(ds, eval_on(ds))   # ✅ 分数据集汇报，不合并成一个虚高均值
```

> 凯喵总结：评测的坑 90% 在「污染」「泄漏」「指标选错」「样本太小」「外推过度」。把这 12 个现场刻进发版流程，少发几次「假 SOTA」。

### 现场之外：凯喵的评测三问
每次要宣布「模型超越 SOTA」之前，凯喵都会先问自己三个问题，能挡掉绝大多数翻车：第一，测试集和训练集真的没有重叠吗？用 n-gram 重叠率查过才敢信。第二，分数提升在统计上显著吗？样本量够不够 bootstrap 出置信区间？第三，结论能跨数据集复现吗？还是只在某一个英文 benchmark 上灵光一现。三问过完再发版，基本不会在同行复审时被一句话问倒。
