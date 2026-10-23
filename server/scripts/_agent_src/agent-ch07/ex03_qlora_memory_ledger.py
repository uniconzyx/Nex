# title: QLoRA 显存账本：4bit 基座 + 适配器 + 优化器状态
# 逐项拆开 7B 模型微调的显存：权重、量化常数、LoRA 参数、Adam 状态、激活。
# 所有数字都可按公式复算，不是拍脑袋的「大约 24G」。
import numpy as np

P = 6.74e9          # 基座参数量
L, D, SEQ, BATCH = 32, 4096, 1024, 4
GB = 1024 ** 3

def gb(x):
    return x / GB

# ① 权重
w_fp16 = P * 2
w_nf4 = P * 0.5
absmax_single = P / 64 * 4                        # 每 64 权重一个 fp32 absmax
# 双重量化：每 256 个 absmax 再压成 int8（+1 个 fp32 尺度）
absmax_double = (P / 64) * (1 + 4 / 256)

print("① 基座权重")
print(f"  FP16           {gb(w_fp16):7.2f} GB  (2.00 byte/param)")
print(f"  NF4 单重量化   {gb(w_nf4 + absmax_single):7.2f} GB  "
      f"(0.50 + {absmax_single/P:.4f} byte/param)")
print(f"  NF4 双重量化   {gb(w_nf4 + absmax_double):7.2f} GB  "
      f"(0.50 + {absmax_double/P:.4f} byte/param，省 "
      f"{gb(absmax_single-absmax_double):.2f} GB)")

# ② LoRA 适配器（r=16，q/k/v/o）
r = 16
adapter = L * 4 * r * (D + D)
print(f"\n② LoRA 适配器 r={r}，挂 q/k/v/o：{adapter/1e6:.2f}M 参数")
print(f"  推理（fp16）   {gb(adapter*2):7.3f} GB")
print(f"  训练（fp32 参数+梯度+Adam m,v = 16 byte/param） {gb(adapter*16):7.3f} GB")

# ③ 激活（按「每层存一份 batch×seq×d 的 fp16 张量」粗算）
act_ckpt = L * BATCH * SEQ * D * 2
act_full = act_ckpt * 8
print(f"\n③ 激活 batch={BATCH}, seq={SEQ}")
print(f"  不开梯度检查点 {gb(act_full):7.2f} GB")
print(f"  开梯度检查点   {gb(act_ckpt):7.2f} GB（重算换显存，速度约降 20%~30%）")

rows = [
    ("全参微调 FP16", w_fp16 + P * 2 + P * 8 + P * 4, 0.0, act_full),
    ("LoRA FP16",     w_fp16,                          adapter * 16, act_ckpt),
    ("QLoRA 单重量化", w_nf4 + absmax_single,           adapter * 16, act_ckpt),
    ("QLoRA 双重量化", w_nf4 + absmax_double,           adapter * 16, act_ckpt),
]
print(f"\n{'方案':<16}{'权重':>8}{'适配器/优化器':>14}{'激活':>8}{'合计':>9}  24GB 单卡")
for name, w, opt, act in rows:
    total = gb(w + opt + act)
    verdict = "可训练" if total < 22 else ("临界" if total < 24 else "OOM")
    print(f"{name:<16}{gb(w):>8.2f}{gb(opt):>14.2f}{gb(act):>8.2f}{total:>9.2f}  {verdict}")

q_total = gb(w_nf4 + absmax_double + adapter * 16 + act_ckpt)
print(f"\n峰值场景：seq 突增到 2048，激活 ×2 → {q_total + gb(act_ckpt):.2f} GB")
print("paged optimizer：把 Adam 状态分页到 CPU，显存峰值只保留当前页，")
print("  代价是每步多一次 H2D/D2H 拷贝；这是 24GB 卡跑 7B QLoRA 的最后一道保险。")
print("\n结论：QLoRA 把 7B 的权重从 13.5GB 压到 3.6GB，省下的空间全给了激活与 batch。")
print("读法：账本里最先爆的通常不是权重而是激活——先开梯度检查点，再降 seq，最后才降 rank。")
