# 零样本、少样本与示例选择

## 一、零样本 / 单样本 / 少样本：边界与代价

| 形式 | 做法 | 什么时候用 | 主要代价 |
|---|---|---|---|
| 零样本（zero-shot） | 只给指令 | 任务常见、模型已充分训练 | 格式与边界不稳 |
| 单样本（one-shot） | 1 个示例 | 需要固定输出格式 | 示例稍有偏差就被放大 |
| 少样本（few-shot） | 2~8 个示例 | 任务冷门、需要划定决策边界 | 占上下文预算；示例集本身有偏 |

**关键点**：少样本不是「教模型新知识」的手段，而是「用最小代价表达一个难以用自然语言说清的映射」。一个经典例子是「把客服工单分成 5 类」——你很难把 5 类的判定标准写成无歧义的规则，但给出每类 2 个例子就非常有效。

## 二、示例的顺序与标签分布偏差

示例集不是无序集合，它会被模型当成**隐式的分布先验**：

- **近因偏差（recency bias）**：靠近待处理输入的示例权重更高。当示例标签分布均匀、而场景本身有偏时，把「正确答案所在类」的示例放在末尾会显著改变输出分布。
- **多数标签偏差（majority label bias）**：若 6 个示例里有 4 个是 A 类，模型会倾向于把模糊输入判成 A，哪怕你的指令写的是「请客观判断」。**示例的标签分布本身就是一条被隐式学习的规则**。
- **示例数量收益递减**：从 1 到 4 个示例的收益通常最显著，4 到 16 个的边际收益快速下降，而 token 成本线性上升。**先算预算，再定数量**。

一个可操作的工程习惯：把示例集当成**数据集**来管——写清来源、标注规则、覆盖矩阵，并且**做顺序敏感性测试**（把示例随机重排若干次，看输出分布是否稳定；不稳定就说明模型在依赖顺序而非规则）。

## 三、指令与示例的关系

- 指令说「做什么」，示例说「长什么样、边界在哪」。**两者冲突时，模型通常跟示例走**——因为示例是更高带宽的信号。
- 因此「指令改了但输出没变」的常见原因不是模型不听话，而是**示例里还残留着旧行为的示范**。改行为要先查示例。
- 当任务可以完全用规则说清时，**零样本 + 明确规则**往往优于少样本，因为少样本会引入不必要的分布先验。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### token 计数估算器：按字符类别的近似规则

```python
CHINESE_FACTOR = 1.0     # 一个汉字约 1 token（经验值，随 tokenizer 不同而波动）
ASCII_WORD = 1.3         # 一个英文单词约 1.3 token
PUNCT = 1.0              # 每个标点/空白约 1 token


def estimate(text):
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    # 英文单词：连续的字母/数字（按空白切分后过滤）
    words = [w for w in text.replace(',', ' ').replace('.', ' ').split()
             if any(c.isalnum() and ord(c) < 128 for c in w)]
    other = len(text) - cjk
    return int(round(cjk * CHINESE_FACTOR + len(words) * ASCII_WORD))


SAMPLES = [
    ("纯中文", "上下文工程是把有限的窗口预算分配给最重要的信息。"),
    ("纯英文", "Prompt engineering is the practice of designing inputs."),
    ("中英混合", "请用 JSON 格式输出 result 字段，不要包含 explanation。"),
    ("长中文", "在检索增强生成中，chunk 的大小直接影响召回质量与上下文利用率。" * 3),
]


def rough_chars(text):
    return len(text)


print("规则: 汉字 x%.1f + 英文词 x%.1f" % (CHINESE_FACTOR, ASCII_WORD))
print("%-10s %8s %10s %10s" % ("类型", "字符数", "估算token", "字符/token"))
rows = []
for name, text in SAMPLES:
    tok = estimate(text)
    ratio = rough_chars(text) / tok if tok else 0.0
    rows.append((name, rough_chars(text), tok, ratio))
    print("%-10s %8d %10d %10.2f" % (name, rough_chars(text), tok, ratio))

heaviest = min(rows, key=lambda r: r[3])
print()
print("字符/token 最低（最吃窗口）的是: %s (%.2f)" % (heaviest[0], heaviest[3]))
print("原因: 中文单字占 token，同等字符数下比英文更耗预算")
```

实际输出：

```text
规则: 汉字 x1.0 + 英文词 x1.3
类型              字符数    估算token   字符/token
纯中文              24         23       1.04
纯英文              55         10       5.50
中英混合             40         16       2.50
长中文             102         82       1.24

字符/token 最低（最吃窗口）的是: 纯中文 (1.04)
原因: 中文单字占 token，同等字符数下比英文更耗预算
```

> 出处：`examples/ex01-token-count-estimator.json`。改一处再看输出变没变，比读三遍解释有用。

### 上下文窗口预算分配与溢出判定

```python
WINDOW = 8192


def allocate(blocks, reserve_output=1024):
    usable = WINDOW - reserve_output
    total = sum(t for _, t in blocks)
    print("窗口 %d | 预留输出 %d | 可用输入 %d" % (WINDOW, reserve_output, usable))
    print("%-16s %8s %8s %8s" % ("区块", "token", "占比", "状态"))
    acc = 0
    for name, t in blocks:
        share = t / usable * 100
        acc += t
        state = "OK" if acc <= usable else "OVERFLOW"
        print("%-16s %8d %7.1f%% %8s" % (name, t, share, state))
    print()
    print("输入合计 %d / 可用 %d" % (total, usable))
    print("是否溢出: %s" % (total > usable))
    print("溢出量: %d token" % max(0, total - usable))
    return total, usable


print("=== 场景 A: 预算充裕 ===")
allocate([("system", 320), ("few-shot x3", 900), ("retrieved x5", 3200),
          ("history x6", 1800), ("user query", 60)])

print()
print("=== 场景 B: 预算超支（检索片段过多）===")
allocate([("system", 320), ("few-shot x8", 2400), ("retrieved x20", 12800),
          ("history x6", 1800), ("user query", 60)])
```

实际输出：

```text
=== 场景 A: 预算充裕 ===
窗口 8192 | 预留输出 1024 | 可用输入 7168
区块                  token       占比       状态
system                320     4.5%       OK
few-shot x3           900    12.6%       OK
retrieved x5         3200    44.6%       OK
history x6           1800    25.1%       OK
user query             60     0.8%       OK

输入合计 6280 / 可用 7168
是否溢出: False
溢出量: 0 token

=== 场景 B: 预算超支（检索片段过多）===
窗口 8192 | 预留输出 1024 | 可用输入 7168
区块                  token       占比       状态
system                320     4.5%       OK
few-shot x8          2400    33.5%       OK
retrieved x20       12800   178.6% OVERFLOW
history x6           1800    25.1% OVERFLOW
user query             60     0.8% OVERFLOW

输入合计 17380 / 可用 7168
是否溢出: True
溢出量: 10212 token
```

> 出处：`examples/ex02-context-budget-allocation.json`。改一处再看输出变没变，比读三遍解释有用。

## 三视角解析

### 🧑‍💻 程序员视角

**工程决策上，少样本示例集要当数据集维护。** 一个可落地的最小流程是：① 给每个示例标注来源与覆盖的边界情形（覆盖矩阵）；② 固定随机种子做 5 次顺序重排，统计输出的标签分布方差，方差大的场景说明模型在「抄最后一个示例」而不是「学规则」；③ 把示例数量作为超参在固定测试集上扫一遍，通常 4 个左右就进入平台期。排查顺序推荐：先查「指令与示例是否自相矛盾」，再查「顺序敏感性」，最后才动指令措辞。

**踩坑提醒**：把示例里出现的输入文本和待处理输入写得「太像」（比如同一个模板只换了实体名），模型会直接做字符串替换式回答，看起来在 few-shot 学习，实际在抄格式。

### 🎓 博士生视角

**少样本的机制解释可归到「隐式梯度下降」假设**：前向传播中，注意力层会把示例构造成一个「输入→输出」的映射，而 Transformer 的权重更新近似与这个前向的隐式梯度方向一致。这解释了两个可检验的推论：① 示例的**顺序**会改变隐式梯度的累积顺序，从而影响输出（recency bias 的由来）；② 示例的**标签分布**会被当成先验编码进上下文表示（majority label bias 的由来）。

从信息论角度，上下文中的每个 token 都在改变条件分布的「支撑集」。少样本的收益上界受限于**上下文信道的有效容量**：指令 + 示例必须与目标映射的「描述复杂度」匹配；超过某个点，新增示例带来的先验噪声超过了它提供的信息量，这就是收益递减与「加示例反而更差」同时存在的根本原因。

### 📚 考研者视角

**面试常考口径**：

1. **零样本 / 少样本 / 微调三者的定位**：prompt 是「不改变参数，只改变条件」；微调是「改变参数」。因此 prompt 适合快速迭代与冷启动，微调适合稳定行为与大幅降本（可用更小模型）。
2. **few-shot 为什么能起作用**（高频追问）：标准答法是「模型在预训练中习得了上下文学习（in-context learning）能力，示例在上下文中隐含地指定了任务与输出格式」，**不要**答成「模型从示例里学到了新知识」——它没有更新参数。
3. **示例顺序会影响结果吗**：会。这是偏差来源，不是随机噪声；面试里若能答出「近因偏差 / 多数标签偏差」并给出缓解手段（打乱顺序做一致性测试），是加分项。
4. **易错口径**：把 few-shot 与「微调」混为一谈；或认为「示例越多越好」。

