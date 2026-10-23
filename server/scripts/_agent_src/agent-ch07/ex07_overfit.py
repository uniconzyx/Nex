# title: 过拟合识别：训练/验证间距与早停点
# 用一条可控的合成曲线复现「训练 loss 一直降、验证 loss 先降后升」，
# 并给出三个可自动化的判据：最小验证点、patience、间距比。
import numpy as np

EPOCHS = 90
t = np.arange(EPOCHS)
rng = np.random.default_rng(3)

train = 2.20 * np.exp(-t / 25.0) + 0.35 + rng.normal(0, 0.008, EPOCHS)
val = 2.60 * np.exp(-t / 22.0) + 0.50 + 0.0025 * np.maximum(0, t - 35) ** 1.7
val = val + rng.normal(0, 0.012, EPOCHS)

best_epoch = int(np.argmin(val))
best_val = val[best_epoch]
patience, wait = 8, 0
stop_epoch = EPOCHS - 1
for e in range(best_epoch + 1, EPOCHS):
    if val[e] < best_val - 1e-4:
        best_val, best_epoch, wait = val[e], e, 0
    else:
        wait += 1
        if wait >= patience:
            stop_epoch = e
            break

print(f"{'epoch':>5}{'train':>9}{'val':>9}{'gap':>8}{'val/train':>10}  状态")
for e in range(0, EPOCHS, 5):
    gap = val[e] - train[e]
    state = ""
    if e == best_epoch:
        state = "验证最低 → 保存"
    elif e > best_epoch and gap > 2.0 * (val[best_epoch] - train[best_epoch]):
        state = "过拟合区间"
    print(f"{e:>5}{train[e]:>9.4f}{val[e]:>9.4f}{gap:>8.4f}{val[e]/train[e]:>10.2f}  {state}")

print(f"\n验证集最低：epoch {best_epoch}，val={val[best_epoch]:.4f}，此时 train={train[best_epoch]:.4f}")
print(f"patience={patience} → 应在 epoch {stop_epoch} 停止（val 已连续 {patience} 轮不降）")
print(f"若硬训到 {EPOCHS-1}：train={train[-1]:.4f}（还在降），val={val[-1]:.4f}"
      f"（比最优点高 {val[-1]/val[best_epoch]-1:.0%}），gap={val[-1]-train[-1]:.4f}")
print(f"间距比 val/train 从 {val[best_epoch]/train[best_epoch]:.2f} 涨到 {val[-1]/train[-1]:.2f}")

print("\n三个可写进训练脚本的判据：")
print("1. 绝对判据：val 连续 N 轮不降（N=3~8，按数据量定）→ 回滚到最佳 checkpoint；")
print("2. 相对判据：val/train > 1.5 且持续 5 轮 → 过拟合，降 rank / 加 dropout / 减 epoch；")
print("3. 数据判据：val 曲线抖动的方差突然变大 → 验证集太小，先扩验证集再谈调参。")
print("\n结论：训练 loss 单调下降毫无信息量，早停依据只能是验证曲线。")
print("读法：小数据（500~2000 条）微调常见 2~4 个 epoch 就到最优点，10 epoch 基本都在背答案。")
