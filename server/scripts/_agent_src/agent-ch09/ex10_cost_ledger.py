# title: 多模态单次请求成本账本：文本、图像、多图与生成四类请求对比
# 计费口径：视觉 token 按 (H//p)*(W//p) 计，文本按词近似，生成按输出 token 计。
# 单价为教学用假设值，仅用于展示账本结构。

PRICE_IN = 0.008 / 1000   # 输入 ¥/token
PRICE_OUT = 0.024 / 1000  # 输出 ¥/token
P = 14
CTX = 8192


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def vision_tokens(h, w):
    return (h // P) * (w // P)


def text_tokens(s):
    return max(1, len(s) // 2)  # 中文按约 2 字符 1 token 近似


def cost(in_tok, out_tok):
    return in_tok * PRICE_IN + out_tok * PRICE_OUT


print("== 四类请求的单次成本账本（单价为教学假设） ==")
print(f"{'请求类型':<22}{'输入token':>10}{'输出token':>10}{'成本(¥)':>10}{'占ctx':>8}")
rows = []
# 1) 纯文本问答
t_in = text_tokens("帮我把这段工单分类并提取优先级，输出 JSON：" + "x" * 200)
rows.append(("纯文本（约350字）", t_in, 128, ""))

# 2) 单图理解：448x448 票据
v1 = vision_tokens(448, 448)
rows.append(("单图理解 448x448", v1 + text_tokens("抽取发票字段"), 256, ""))

# 3) 多图：4 张 448x448 产品图
v4 = 4 * vision_tokens(448, 448)
rows.append(("多图 4x448x448", v4 + text_tokens("对比四张图的差异"), 512, ""))

# 4) 文生图：按 latent 预算 x 步数折算（等价 token 口径，仅用于账本对比）
gen_equiv = 1024 * 25  # 1024 token 级 latent 预算 x 25 步（教学折算）
rows.append(("文生图 1024x1024x25步", text_tokens("a cat"), gen_equiv, "n/a"))

total_cost = 0.0
for name, i_t, o_t, ctx_str in rows:
    c = cost(i_t, o_t)
    total_cost += c
    share = f"{(i_t + o_t) / CTX:.0%}" if ctx_str == "" else ctx_str
    print(f"{pad(name, 22)}{i_t:>10}{o_t:>10}{c:>10.4f}{share:>8}")

print(f"\n四类合计 = ¥{total_cost:.4f}/次")

print("\n== 同一会话内的复购：6 图咨询的累计成本 ==")
per_msg = v1 + text_tokens("继续问") + 100
cum = 0.0
for turn in range(1, 7):
    cum += cost(per_msg, 100)
    print(f"  第 {turn} 轮后累计 = ¥{cum:.4f}（每轮视觉 token {per_msg}，其中图 {v1}）")
print(f"6 轮约为首轮的 {cum / cost(per_msg, 100):.0f} 倍 —— 多图会话的视觉 token 按轮累加")

print("\n== 缓存命中后：同一张图重复出现 ==")
cached = text_tokens("还是看刚才那张图") + 100
print(f"命中缓存后每轮输入 token 从 {per_msg} 降到 {cached}，成本 {(1 - cost(cached, 100) / cost(per_msg, 100)):.0%} ↓")

print("\n结论：多模态成本的大头是视觉 token 且按张/按轮累加，缓存与限张数是两个最有效的降本杠杆，")
print("读法：1. 账本结构 = 视觉 token（按切图策略）+ 文本 token + 输出 token，三项分开记才好归因；2. 分辨率翻倍，视觉成本 x4——和 token 数同步；3. 会话内重复图必须走编码缓存，这是零质量损失的降本；4. 单价为教学假设值，真实计价以各服务商为准，但账本结构一致。")
