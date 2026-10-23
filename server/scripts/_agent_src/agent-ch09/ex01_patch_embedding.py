# title: 图像分块：patch 数量、局部性与「小字在入口处就丢了」
import numpy as np

rng = np.random.default_rng(0)


def patchify(img, p=16):
    """(H, W, 3) -> (N, p*p*3)，N = (H//p)*(W//p)。"""
    H, W, _ = img.shape
    H2, W2 = H // p * p, W // p * p
    x = img[:H2, :W2].reshape(H2 // p, p, W2 // p, p, 3)
    return x.transpose(0, 2, 1, 3, 4).reshape(-1, p * p * 3)


# 1) token 数只由 (H//p)*(W//p) 决定，与原图文件大小无关
img = (rng.random((224, 224, 3)) * 255).astype("uint8")
patches = patchify(img, p=16)
print("== 1) 224x224, p=16 的分块 ==")
print(f"原图像素 {img.shape} -> patch 网格 {224 // 16}x{224 // 16} -> {patches.shape[0]} 个 token")
assert patches.shape == (196, 768)

# 2) 局部性：一个 patch 只覆盖 p*p 像素，小于它的细节在入口处被平均掉
# 构造一张「背景 0 + 中央一个 1 像素亮点」的图，看亮点落在哪个 patch、被稀释成多少
tiny = np.zeros((64, 64, 3), dtype="uint8")
tiny[32, 32] = 255  # 单个亮点（模拟小数点/表格细线）
tp = patchify(tiny, p=16).reshape(4, 4, 16, 16, 3)
row, col = 32 // 16, 32 // 16
inside = tp[row, col]
bright = (inside > 0).sum()
print("\n== 2) 局部性：单个亮点进入 patch 后被稀释 ==")
print(f"亮点落在第 ({row},{col}) 个 patch，patch 内亮通道数 = {bright}/{16 * 16 * 3}")
print(f"该细节只占 patch 的 {bright}/{16 * 16 * 3} 个数值 —— 16x16 的格子把它平均成了背景")

# 3) 想要看清小字只有三条路：提高分辨率 / 换更小 patch / 先裁剪放大
print("\n== 3) 同一张 1024x1024 的图在不同 patch 下的 token 数 ==")
for p in (8, 14, 16, 32):
    n = (1024 // p) ** 2
    print(f"p={p:2d}: {1024 // p}x{1024 // p} = {n:5d} token")
print("token 数随 (1/p)^2 增长：patch 减半，token 变 4 倍")

print("\n结论：ViT 类模型把图像当成「打格子的序列」，N=(H//p)*(W//p) 就是视觉 token 数；")
print("读法：1. 一个 patch 只覆盖 p*p 像素，小于该尺寸的细节（小数点、细线、印章小字）在入口处就被平均掉；2. 想看清小字只有提高分辨率、减小 patch 或先裁剪放大三条路，且都直接推高 token 账单；3. 本示例只做分块与计数，不做任何真实模型推理。")
