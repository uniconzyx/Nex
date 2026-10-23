# title: Loss Mask 构造：只让 assistant 段产生梯度
# 把一条对话拆成 token，验证三件事：标签如何移位、哪些位置置 -100、错一位会怎样。
import numpy as np

# 词表（字符级，只为可读）
VOCAB = list("系统用户助手：请帮我查订单A123退款进度好的已受理")
stoi = {ch: i for i, ch in enumerate(VOCAB)}
V = len(VOCAB)

segments = [("system", "系统：请帮我"), ("user", "用户：查订单A123"), ("assistant", "助手：已受理退款")]
ids, seg_of = [], []
for name, text in segments:
    for ch in text:
        ids.append(stoi[ch])
        seg_of.append(name)
pad = [stoi["的"]] * 3
ids += pad
seg_of += ["pad"] * 3
ids = np.array(ids)
T = len(ids)

# 模拟 logits：prompt 段几乎能照抄（高置信），assistant 段才是真正要学的
rng = np.random.default_rng(5)
logits = rng.normal(0, 0.3, size=(T, V))
for t in range(T):
    target = ids[(t + 1) % T]           # 下一个 token 是标签
    logits[t, target] += 8.0 if seg_of[t] != "assistant" else 0.0

def ce_row(t, target):
    z = logits[t] - logits[t].max()
    logp = z - np.log(np.exp(z).sum())
    return -logp[target]

# 标准做法：输入 x[0..T-2]，标签 y = x[1..T-1]，非 assistant 置 -100
labels = np.full(T - 1, -100, dtype=int)
for t in range(T - 1):
    if seg_of[t + 1] == "assistant":
        labels[t] = ids[t + 1]

print(f"序列长 {T}（含 3 个 pad），shift 后预测 {T-1} 个位置")
print(f"{'位置':>4} {'当前段':<10}{'预测下一 token':<14}{'是否计 loss':>10}{'单 token loss':>13}")
for t in range(T - 1):
    nxt = VOCAB[ids[t + 1]]
    counted = labels[t] != -100
    loss_t = ce_row(t, ids[t + 1])
    print(f"{t:>4} {seg_of[t]:<10}{nxt:<14}{'是' if counted else '否(-100)':>10}{loss_t:>13.4f}")

mask = labels != -100
loss_mask = np.array([ce_row(t, labels[t]) if mask[t] else 0.0 for t in range(T - 1)])
loss_assistant = loss_mask[mask].mean()
all_tokens = np.array([ce_row(t, ids[t + 1]) for t in range(T - 1)]).mean()
print(f"\n只算 assistant（{mask.sum()} 个 token）：loss = {loss_assistant:.4f}")
print(f"算全部 token（{T-1} 个，含 prompt 与 pad）：loss = {all_tokens:.4f}"
      f"（是全量的 {all_tokens/loss_assistant:.0%}）")
print(f"assistant 每个 token 的梯度权重被稀释到 {mask.sum()/(T-1):.0%}")
print("看起来「训练得很好」，其实大部分 loss 来自背 prompt")

# 常见 bug：忘了 shift，直接拿 labels=ids 且 mask 覆盖 assistant 本身
bad = np.zeros(T, dtype=bool)
for t in range(T):
    if seg_of[t] == "assistant":
        bad[t] = True
bad_loss = np.mean([ce_row(t, ids[t]) for t in range(T) if bad[t]])
print(f"\n错位写法（不 shift，用当前 token 当标签）loss = {bad_loss:.4f}，"
      f"模型学到的是「复制输入」而不是「预测下一个」")
print("另一种错位：mask 从 assistant 的第一个 token 开始，会漏掉它的首个预测位，")
print("  正确做法是 mask 作用在 **标签侧**（t+1），即 assistant 段整体右移一位。")
print("\n结论：loss mask 必须作用在移位后的标签上，且 pad 也要置 -100。")
print("读法：prompt 的 loss 再低也不代表模型学会了回答——它只是在背输入。")
