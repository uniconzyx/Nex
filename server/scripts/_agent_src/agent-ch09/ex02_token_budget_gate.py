# title: 视觉 token 预算门：1024x1024 直喂超不超窗？降本方案怎么选
import numpy as np


def dw(s):
    """终端显示宽度：中文等宽字符按 2 列计。"""
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


def token_ledger(h, w, p=14):
    """视觉 token 数与注意力矩阵显存（单头 fp32，N^2 项，单位 MB）。"""
    n = (h // p) * (w // p)
    return n, n * n * 4 / 1e6


def budget_gate(h, w, p, ctx, text_tokens, out_tokens):
    """总 token = 视觉 + 文本 + 输出预算，返回 (N, 总量, 是否可行)。"""
    n, _ = token_ledger(h, w, p)
    total = n + text_tokens + out_tokens
    return n, total, total <= ctx


CTX = 4096
TEXT, OUT = 200, 512
print("== 原图直喂：1024x1024, p=14, ctx=4096 ==")
n0, mem0 = token_ledger(1024, 1024)
n, total, ok = budget_gate(1024, 1024, 14, CTX, TEXT, OUT)
print(f"N = {n0} token，注意力矩阵 ≈ {mem0:.0f} MB")
print(f"总 token = {n0} + {TEXT} + {OUT} = {total}，可行 = {ok}（超窗 {total - CTX}）")
assert not ok and total == 6041

print("\n== 降本方案对比表 ==")
print(f"{'方案':<20}{'视觉token':>10}{'总token':>9}{'可行':>6}{'文字区保真':>10}")
rows = []
# 方案 1：整体降采样到 768x768
n1, m1 = token_ledger(768, 768)
rows.append(("整体降采样 768x768", n1, n1 + TEXT + OUT, "压缩"))
# 方案 2：降采样到 512x512
n2, m2 = token_ledger(512, 512)
rows.append(("整体降采样 512x512", n2, n2 + TEXT + OUT, "压缩"))
# 方案 3：anyres 切 4 个 512x512 子图 + 1 张全局缩略图
sub, _ = token_ledger(512, 512)
n3 = 4 * sub + 1
rows.append(("anyres 4x512² + 1 全局", n3, n3 + TEXT + OUT, "局部保真"))
# 方案 4：先检测后裁剪，只留文字区（约整图 35% 面积，等效 608x608）
n4, m4 = token_ledger(608, 608)
rows.append(("检测后裁剪文字区 608²", n4, n4 + TEXT + OUT, "文字区保真"))
for name, nn, tt, keep in rows:
    print(f"{pad(name, 20)}{nn:>10}{tt:>9}{str(tt <= CTX):>6}{keep:>10}")

print("\n== 结论 ==")
print("原图直喂超窗 1945 token，必须降级；整体降采样与检测后裁剪都可行，")
print("anyres 4x512²+1 在 4k 窗口仍超 1617 token——切图不是万能，子图大小要跟着窗口走。")
print("结论：token 预算门要在第一行推理代码之前计算——N=(H//p)*(W//p)，总预算 = 视觉 + 文本 + 输出，")
print("读法：1. 超窗时多数服务端静默截断尾部而非报错，症状是「后半张图抽不出字段」；2. 降本手段按代价从小到大：限张数 → 非关键图降采样 → anyres 切图 → 检测后裁剪；3. 票据场景优先「先版面检测再裁剪放大」，token 降一半且小字更准；4. anyres 的子图数与单图 token 要重新过一遍预算门，切更小或换更大窗口；5. 本账本只算数与判定，不调用任何模型。")
