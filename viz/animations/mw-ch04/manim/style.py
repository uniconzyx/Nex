"""《凯喵Code试炼录》mw-ch04 动画公共样式。

视觉契约（与 API 端 viz/index.html 同一套色）：
    背景 #EBF4FA → #F9FBFD 竖向渐变
    冰蓝 #5DB4E5 / 深灰蓝 #2B3E50 / 青绿 #31D0AA / 柔红 #F87171
    正文圆润无衬线（微软雅黑），代码与数值 JetBrains Mono
    「液态玻璃」= 半透明白卡 + 偏移的柔和投影副本 + 极细描边
注意：Manim 没有真正的高斯模糊，玻璃感靠「白卡 + 低透明度投影 + 细边」模拟；
      公式一律用 Text 拼（无 LaTeX），上下标用 sup() 手工排版。
"""

from __future__ import annotations

import os

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Dot,
    FadeIn,
    Line,
    RoundedRectangle,
    Text,
    VGroup,
    config,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "fonts")

# ── 色板 ───────────────────────────────────────────────────────────────
BG_TOP = "#EBF4FA"
BG_BOTTOM = "#F9FBFD"
ICE = "#5DB4E5"        # 冰蓝：主结构、连线、高亮
ICE_SOFT = "#BFE1F3"   # 冰蓝淡：已发生但非焦点
SLATE = "#2B3E50"      # 深灰蓝：标题与正文
SLATE_MUTE = "#5D7183" # 次级文字
MINT = "#31D0AA"       # 正确 / 通过
CORAL = "#F87171"      # 错误 / 失败
GLASS = "#FFFFFF"

CN = "Microsoft YaHei"   # Pango 家族名（msyh.ttc）
MONO = "JetBrains Mono"  # register_font 注册后的家族名

_FONT_READY = False


def ensure_fonts() -> None:
    """注册 JetBrains Mono（随仓库带 ttf，不依赖系统安装）。

    坑：manim.register_font 是 contextmanager，直接调用不会注册任何东西，
    只会静默回退到 Sans。这里改用 manimpango.register_font()，它走系统原生 API
    做永久注册，进程内一直有效。
    """
    global _FONT_READY
    if _FONT_READY:
        return
    from manimpango import list_fonts, register_font

    for f in ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf", "JetBrainsMono-Medium.ttf"):
        p = os.path.abspath(os.path.join(FONT_DIR, f))
        if os.path.exists(p):
            try:
                register_font(p)
            except Exception as exc:  # 注册失败不致命，但要让调用方看见
                print("[font] register failed:", f, exc)
    from manim import Text as _Text

    # Text.font_list 是 @functools.cache：任何一个 Text 先被创建，列表就固化了，
    # 之后注册的字体在 Manim 眼里"不存在"。注册完必须清一次缓存。
    try:
        _Text.font_list.cache_clear()
    except AttributeError:
        pass
    if "JetBrains Mono" not in list_fonts():
        print("[font] WARNING: JetBrains Mono 未进 Pango 列表，将回退到 Sans")
    _FONT_READY = True


def cn(text: str, size: float = 26, color: str = SLATE, weight: str = "NORMAL") -> Text:
    """中文正文。"""
    return Text(text, font=CN, font_size=size, color=color, weight=weight)


def mono(text: str, size: float = 22, color: str = SLATE, weight: str = "NORMAL") -> Text:
    """代码 / 数值 / 键名。"""
    ensure_fonts()
    return Text(text, font=MONO, font_size=size, color=color, weight=weight)


def mix(text: str, size: float = 22, color: str = SLATE, weight: str = "NORMAL") -> Text:
    """中英混排：ASCII 走 JetBrains Mono，CJK 走微软雅黑。

    两个坑：
      1. JetBrains Mono 没有中文字形，硬用它渲染中文会得到「方框 + 码点十六进制」；
      2. 不能拼两个 Text 再 align_to(DOWN) —— 两种字体的下缘不在同一基线上，中文会浮起来。
    正解是让 Pango 在同一段排版里换字体：Manim 的 t2f 参数就是干这个的，
    基线由排版引擎统一处理。
    """
    ascii_runs = set()
    buf = ""
    for ch in text:
        if 0x20 <= ord(ch) <= 0x7E:
            buf += ch
        else:
            if buf.strip():
                ascii_runs.add(buf)
            buf = ""
    if buf.strip():
        ascii_runs.add(buf)
    t2f = {run: MONO for run in ascii_runs}
    return Text(text, font=CN, font_size=size, color=color, weight=weight, t2f=t2f or None)


def sup(base: str, exp: str, size: float = 22, color: str = SLATE) -> VGroup:
    """手工上标：Manim 的 Text 在 Windows 上不保证 <sup> 标记，改用两个 Text 拼。

    指数缩到 60%，right 对齐底数右上角后只留 0.02 的缝——留太多会看起来像两个词。
    """
    e = mono(exp, size * 0.60, color)
    if not base:
        return VGroup(e)
    b = mono(base, size, color)
    e.next_to(b, RIGHT, buff=0.015)
    e.align_to(b, UP)
    e.shift(DOWN * b.height * 0.06)
    return VGroup(b, e)


def background() -> VGroup:
    """整幅背景：上浅冰蓝、下奶白。Manim 无原生渐变填充，用 24 条窄带近似。"""
    from manim import Rectangle

    w, h = config.frame_width + 0.2, config.frame_height + 0.2
    bands = VGroup()
    n = 24
    band_h = h / n
    for i in range(n):
        t = i / (n - 1)
        c = _mix(BG_TOP, BG_BOTTOM, t)
        b = Rectangle(width=w, height=band_h + 0.02, stroke_width=0, fill_color=c, fill_opacity=1)
        b.move_to(UP * (h / 2) - DOWN * (band_h * (i + 0.5)))
        bands.add(b)
    return bands.set_z_index(-10)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    return "#%02X%02X%02X" % (
        round(ar + (br - ar) * t),
        round(ag + (bg - ag) * t),
        round(ab + (bb - ab) * t),
    )


def glass(w: float, h: float, r: float = 0.16, opacity: float = 0.86, shadow: bool = True) -> VGroup:
    """液态玻璃卡片：白色半透主体 + 右下偏移的柔和投影副本。

    返回的 VGroup[0] 是投影、[1] 是卡片本体，调用方 `.move_to` 即可整体移动。
    """
    sh = RoundedRectangle(
        corner_radius=r, width=w, height=h, stroke_width=0,
        fill_color=SLATE, fill_opacity=0.07 if shadow else 0,
    ).shift(DOWN * 0.07 + RIGHT * 0.04)
    card = RoundedRectangle(
        corner_radius=r, width=w, height=h,
        stroke_color="#FFFFFF", stroke_width=1.4,
        fill_color=GLASS, fill_opacity=opacity,
    )
    return VGroup(sh, card)


def chip(text: str, color: str = ICE, fg: str = "#FFFFFF", size: float = 18) -> VGroup:
    """小胶囊标签（场景名、判定结果）。"""
    t = cn(text, size, fg, "MEDIUM")
    body = RoundedRectangle(
        corner_radius=t.height * 0.55,
        width=t.width + 0.34, height=t.height + 0.20,
        stroke_width=0, fill_color=color, fill_opacity=1,
    )
    t.move_to(body.get_center())
    return VGroup(body, t)


def kaimao(quote: str, at=(5.1, -3.0), width: float = 4.2) -> VGroup:
    """凯喵：右下角 Q 版头像 + 台词气泡。头像用几何图形拼（不引入位图）。"""
    # 气泡
    txt = Text(quote, font=CN, font_size=19, color=SLATE, line_spacing=1.2)
    if txt.width > width - 0.6:
        # 注意：set_max_width 是**整体缩放**，不是自动换行。缩到 0.7 以下字就糊了，
        # 所以宁可把 width 传大一点、台词写短一点，这里只做兜底。
        txt = Text(quote, font=CN, font_size=19, color=SLATE, line_spacing=1.2).set_max_width(width - 0.6)
    bub_body = RoundedRectangle(
        corner_radius=0.18,
        width=txt.width + 0.55, height=txt.height + 0.42,
        stroke_color=ICE, stroke_width=2, fill_color=GLASS, fill_opacity=0.95,
    )
    txt.move_to(bub_body.get_center())
    tail = Line(
        bub_body.get_corner(DOWN + RIGHT), bub_body.get_corner(DOWN + RIGHT) + DOWN * 0.16 + LEFT * 0.10,
        stroke_color=GLASS, stroke_width=6,
    )
    # 头像：圆形脸 + 两只三角耳 + 两点眼
    face = Circle(radius=0.30, stroke_width=0, fill_color=ICE, fill_opacity=1)
    from manim import Polygon, Triangle

    ear_l = Triangle(stroke_width=0, fill_color=ICE, fill_opacity=1).scale(0.16)
    ear_r = ear_l.copy()
    ear_l.move_to(face.get_center() + UP * 0.28 + LEFT * 0.17)
    ear_r.move_to(face.get_center() + UP * 0.28 + RIGHT * 0.17)
    eye_l = Dot(radius=0.035, color=SLATE).move_to(face.get_center() + UP * 0.03 + LEFT * 0.10)
    eye_r = eye_l.copy().shift(RIGHT * 0.20)
    head = VGroup(ear_l, ear_r, face, eye_l, eye_r)
    bubble = VGroup(bub_body, tail, txt)
    bubble.next_to(head, LEFT, buff=0.14)
    g = VGroup(head, bubble).move_to([at[0], at[1], 0])
    # 防越界：at 是**整组中心**，长台词 + 偏左的 at 会把气泡推出画框（S04 首版就把
    # 气泡左缘裁掉了半句）。这里统一按画框钳制，调用方不必自己算宽度。
    hw = config.frame_width / 2 - 0.30
    hh = config.frame_height / 2 - 0.22
    if g.get_left()[0] < -hw:
        g.shift(RIGHT * (-hw - g.get_left()[0]))
    if g.get_right()[0] > hw:
        g.shift(LEFT * (g.get_right()[0] - hw))
    if g.get_bottom()[1] < -hh:
        g.shift(UP * (-hh - g.get_bottom()[1]))
    if g.get_top()[1] > hh:
        g.shift(DOWN * (g.get_top()[1] - hh))
    g.set_z_index(6)
    return g


def title(text: str, kicker: str = "") -> VGroup:
    """左上角标题：小号 kicker + 大标题，不居中对齐，避免模板感。"""
    t = cn(text, 34, SLATE, "BOLD")
    g = VGroup()
    if kicker:
        k = mix(kicker, 13, ICE, "MEDIUM")
        g.add(k)
        t.next_to(k, DOWN, buff=0.34, aligned_edge=LEFT)
    g.add(t)
    g.to_corner(UP + LEFT, buff=0.55)
    return g


def footnote(text: str, size: float = 18, color: str = SLATE_MUTE) -> Text:
    t = cn(text, size, color)
    t.to_edge(DOWN, buff=0.42)
    return t


# 模块导入即注册：必须早于任何 Text 实例，否则缓存里没有新字体（见 ensure_fonts 注释）
ensure_fonts()
