"""S01 · 概念：三种失效其实是一张二维表

深度落点（对应分镜表「深度知识点」栏）：
  1. 三者不是并列的三种 bug，而是「key 是否存在 × 失效是一个还是一批」二维里被占的对角；
  2. 读路径恒定（Cache 命中→返回 / 未命中→查 DB→回填），三种问题全发生在「未命中」；
  3. 布隆与空值缓存只堵「不存在」这一整行——对击穿、雪崩完全无效。

12s / 30fps。
"""

from __future__ import annotations

import os
import sys

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Create,
    FadeIn,
    LaggedStart,
    RoundedRectangle,
    Scene,
    VGroup,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from style import (  # noqa: E402
    CORAL,
    ICE,
    MINT,
    SLATE,
    SLATE_MUTE,
    background,
    chip,
    cn,
    glass,
    kaimao,
    mix,
    mono,
    title,
)

AMBER = "#E8A33D"


class S01Taxonomy(Scene):
    def construct(self):
        self.camera.background_color = "#F7FAFD"
        self.add(background())

        # ── 标题（占 y 2.95 ~ 3.75，下面所有内容都压在 2.75 以下）────────
        head = title("缓存的三种失效：其实是一张二维表", "mw-ch04 · 概念 01")
        self.play(FadeIn(head, shift=DOWN * 0.1), run_time=0.7)

        # ── 读路径 ──────────────────────────────────────────────────
        def node(label: str, sub: str, w: float) -> VGroup:
            g = glass(w, 0.94, r=0.13)
            inner = VGroup(cn(label, 20, SLATE, "MEDIUM"), mono(sub, 13, SLATE_MUTE)).arrange(DOWN, buff=0.05)
            inner.move_to(g[1].get_center())
            return VGroup(g, inner)

        n_req = node("请求", "GET /user/42", 1.72)
        n_cache = node("缓存", "Redis", 1.42)
        n_db = node("数据库", "MySQL", 1.62)
        flow = VGroup(n_req, n_cache, n_db).arrange(RIGHT, buff=0.86)
        flow.move_to(LEFT * 3.52 + UP * 1.66)

        a1 = Arrow(n_req.get_right(), n_cache.get_left(), buff=0.10, stroke_width=3, color=ICE,
                   max_tip_length_to_length_ratio=0.24)
        a2 = Arrow(n_cache.get_right(), n_db.get_left(), buff=0.10, stroke_width=3, color=ICE,
                   max_tip_length_to_length_ratio=0.24)

        self.play(
            LaggedStart(*[FadeIn(n, shift=UP * 0.08) for n in (n_req, n_cache, n_db)], lag_ratio=0.2),
            run_time=0.9,
        )
        self.play(Create(a1), Create(a2), run_time=0.45)

        legend = VGroup(
            VGroup(mix("HIT", 12.5, MINT), cn("直接返回，不过库", 12.5, SLATE_MUTE)).arrange(RIGHT, buff=0.12),
            VGroup(mix("MISS", 12.5, CORAL), cn("查库并回填，三种问题都发生在这里", 12.5, SLATE_MUTE)).arrange(RIGHT, buff=0.12),
        ).arrange(RIGHT, buff=0.55)
        legend.next_to(flow, DOWN, buff=0.40)
        self.play(FadeIn(legend), run_time=0.45)

        # ── 三条失效（全部挂在 MISS 之后）────────────────────────────
        rows = VGroup()
        for i, (name, desc, col) in enumerate([
            ("穿透", "查的 key 库里也没有 → 每次都打到库", CORAL),
            ("击穿", "单个热点 key 过期 → 并发全回源", ICE),
            ("雪崩", "一批 key 同时过期 → 库被冲垮", AMBER),
        ]):
            r = VGroup(chip(name, col, "#FFFFFF", 15), cn(desc, 15.5, SLATE_MUTE)).arrange(RIGHT, buff=0.14)
            r.move_to([-6.05, 0.34 - i * 0.58, 0], aligned_edge=LEFT)
            rows.add(r)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.14) for r in rows], lag_ratio=0.25), run_time=1.4)

        # ── 二维表 ──────────────────────────────────────────────────
        # 左边留 0.8 宽的行标签槽，两列格子各 2.0 宽
        gx = 1.22          # 行标签槽左边界
        cx = 2.32          # 第一列左边界（槽宽 1.05，放得下「key 不存在」）
        cw, ch, gap = 2.08, 1.02, 0.10
        top = 2.36         # 表头基线

        h1 = cn("失效：一个 key", 13, SLATE_MUTE).move_to([cx + cw / 2, top, 0])
        h2 = cn("失效：一批 key", 13, SLATE_MUTE).move_to([cx + cw + gap + cw / 2, top, 0])
        self.play(FadeIn(h1), FadeIn(h2), run_time=0.35)

        def cell(w: float, color: str, op: float = 0.15) -> RoundedRectangle:
            return RoundedRectangle(corner_radius=0.11, width=w, height=ch,
                                    stroke_color=color, stroke_width=1.5,
                                    fill_color=color, fill_opacity=op)

        r1y = top - 0.32 - ch / 2          # 存在 行中线
        r2y = r1y - ch - 0.14             # 不存在 行中线

        lbl_a = cn("key 存在", 13, SLATE, "MEDIUM").move_to([gx + 0.52, r1y, 0])
        lbl_b = cn("key 不存在", 13, SLATE, "MEDIUM").move_to([gx + 0.52, r2y, 0])

        c_hit = cell(cw, ICE).move_to([cx + cw / 2, r1y, 0])
        t_hit = VGroup(cn("击穿", 17, SLATE, "BOLD"), mono("1 key", 12, SLATE_MUTE)).arrange(DOWN, buff=0.03)
        t_hit.move_to(c_hit.get_center())

        c_ava = cell(cw, AMBER).move_to([cx + cw + gap + cw / 2, r1y, 0])
        t_ava = VGroup(cn("雪崩", 17, SLATE, "BOLD"), mono("N key", 12, SLATE_MUTE)).arrange(DOWN, buff=0.03)
        t_ava.move_to(c_ava.get_center())

        merged_w = cw * 2 + gap
        c_pen = cell(merged_w, CORAL, 0.20).move_to([cx + merged_w / 2, r2y, 0])
        t_pen = VGroup(
            cn("穿透", 17, SLATE, "BOLD"),
            cn("单个、批量都落在这一行", 12, SLATE_MUTE),
        ).arrange(DOWN, buff=0.03)
        t_pen.move_to(c_pen.get_center())

        self.play(FadeIn(lbl_a, shift=RIGHT * 0.08), FadeIn(lbl_b, shift=RIGHT * 0.08), run_time=0.4)
        self.play(FadeIn(c_hit), FadeIn(c_ava), run_time=0.45)
        self.play(FadeIn(c_pen), run_time=0.4)
        self.play(LaggedStart(FadeIn(t_hit), FadeIn(t_ava), FadeIn(t_pen), lag_ratio=0.2), run_time=0.75)

        # 四格填满后停一拍：这里是全章的坐标系，读表比看动画重要
        self.wait(1.9)

        # 维度说明：贴在表格正下方，避免和左侧三条失效混在一起
        # ── 结论：布隆/空值只堵「不存在」这一行 ─────────────────────
        guard = VGroup(cn("布隆 / 空值缓存", 15, SLATE, "MEDIUM"), cn("只作用在这一行", 13, CORAL)).arrange(
            DOWN, buff=0.04, aligned_edge=LEFT
        )
        guard.move_to([cx + 0.95, r2y - ch / 2 - 0.92, 0], aligned_edge=LEFT)

        up = Arrow(guard.get_top() + RIGHT * 1.05, c_pen.get_bottom() + DOWN * 0.02 + RIGHT * 0.95,
                   buff=0.04, stroke_width=2.6, color=CORAL, max_tip_length_to_length_ratio=0.30)
        self.play(FadeIn(guard, shift=UP * 0.08), Create(up), run_time=0.65)

        km = kaimao("击穿和雪崩都在「存在」那行，布隆一个都挡不住喵。", at=(-2.42, -2.72), width=4.6)
        self.play(FadeIn(km, shift=UP * 0.1), run_time=0.7)

        self.wait(1.4)
