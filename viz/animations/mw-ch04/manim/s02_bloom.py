"""S02 · 概念：布隆过滤器的「单向」性质

深度落点：
  1. 无假阴性可证：写入时那 k 位一定被置 1，标准布隆没有清零操作，之后查询必全 1；
  2. 误判率 p ≈ (1 − e^(−kn/m))^k；n=1000、m=10000、k=7 时理论 0.82%，实测 1.10%（ex02）；
  3. k 不是越大越好：m/n=10 时 k=1→0.0952、k=2→0.0329、k=7 触底 0.0082，再加 k 反而升高；
  4. 位共享 → 标准布隆不能删元素，删除要换 Counting Bloom。

14s / 30fps。数字来自 examples/ex02-bloom-false-positive-rate.json；k 曲线用公式现算。
"""

from __future__ import annotations

import math
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
    Square,
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

M_BITS, K = 512, 3
COLS, ROWS = 16, 8          # 画 128 格代表 512 位：画满 512 格每格会糊成一片
HIT_BITS = [21, 68, 105]    # user:42 命中的 3 格
FP_BITS = [21, 68, 105]     # user:999 的 3 次哈希恰好全落在已置位处 → 假阳性


class S02Bloom(Scene):
    def construct(self):
        self.camera.background_color = "#F7FAFD"
        self.add(background())

        head = title("布隆过滤器：只会误报「有」", "mw-ch04 · 概念 02")
        self.play(FadeIn(head, shift=DOWN * 0.1), run_time=0.6)

        # ── 位数组（左半屏）────────────────────────────────────────
        cell, gap = 0.20, 0.058
        step = cell + gap
        gx0, gy0 = -5.42, 1.72
        grid = VGroup()
        for r in range(ROWS):
            for c in range(COLS):
                sq = Square(side_length=cell, stroke_width=0, fill_color="#D9E5EF", fill_opacity=1)
                sq.move_to([gx0 + c * step, gy0 - r * step, 0])
                grid.add(sq)

        grid_lbl = mix(f"m = {M_BITS} bit    k = {K}    只画前 128 位", 12, SLATE_MUTE)
        grid_lbl.next_to(grid, UP, buff=0.14).align_to(grid, LEFT)

        self.play(LaggedStart(*[FadeIn(s, scale=0.55) for s in grid], lag_ratio=0.005), run_time=0.9)
        self.play(FadeIn(grid_lbl), run_time=0.3)

        # ── 写入 user:42 ────────────────────────────────────────────
        key1 = chip("user:42", ICE, "#FFFFFF", 13)
        key1.move_to([-6.62, 1.02, 0], aligned_edge=LEFT)
        self.play(FadeIn(key1, shift=RIGHT * 0.1), run_time=0.3)

        for bi in HIT_BITS:
            sq = grid[bi]
            a = Arrow(key1.get_right(), sq.get_left(), buff=0.08, stroke_width=2.2, color=ICE,
                      max_tip_length_to_length_ratio=0.18)
            self.play(Create(a), sq.animate.set_fill(ICE, 1), run_time=0.28)

        set_note = mix(f"写入 1 个元素 → 置 {K} 位（k 次哈希）", 12.5, ICE)
        set_note.next_to(grid, DOWN, buff=0.24).align_to(grid, LEFT)
        self.play(FadeIn(set_note), run_time=0.3)

        # ── 查询 user:999：三位全 1 → 假阳性 ───────────────────────
        key2 = chip("user:999", CORAL, "#FFFFFF", 13)
        key2.move_to([-6.62, 0.30, 0], aligned_edge=LEFT)
        self.play(FadeIn(key2, shift=RIGHT * 0.1), run_time=0.3)

        for bi in FP_BITS:
            sq = grid[bi]
            ring = RoundedRectangle(corner_radius=0.05, width=cell + 0.09, height=cell + 0.09,
                                    stroke_color=CORAL, stroke_width=2.2, fill_opacity=0).move_to(sq.get_center())
            a = Arrow(key2.get_right(), sq.get_left(), buff=0.08, stroke_width=1.9, color=CORAL,
                      max_tip_length_to_length_ratio=0.16)
            self.play(Create(a), Create(ring), run_time=0.22)

        fp = chip("假阳性", CORAL, "#FFFFFF", 12)
        fp.next_to(set_note, DOWN, buff=0.30).align_to(set_note, LEFT)
        fp_desc = cn("三位恰好都是 1 → 判「可能存在」，可库里根本没这个 key", 12, SLATE_MUTE)
        fp_desc.next_to(fp, RIGHT, buff=0.16)
        self.play(FadeIn(fp, shift=UP * 0.06), FadeIn(fp_desc), run_time=0.45)
        self.wait(1.2)

        never = VGroup(
            cn("反过来永不成立：", 12, SLATE_MUTE),
            cn("插入过的 key 必然全 1（只置位、不清零）", 12, MINT),
        ).arrange(RIGHT, buff=0.08)
        never.next_to(fp_desc, DOWN, buff=0.26).align_to(fp, LEFT)
        self.play(FadeIn(never), run_time=0.4)

        # ── 右半屏：公式 / 实测 / k 曲线 ────────────────────────────
        fbody = glass(5.5, 1.12, r=0.14).move_to([3.75, 2.55, 0])
        fcard = VGroup(
            cn("误判率", 12, SLATE_MUTE),
            mix("p ≈ (1 − e^(−kn/m))^k", 20, SLATE),
        ).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        fcard.move_to(fbody[1].get_center()).align_to(fbody[1], LEFT).shift(RIGHT * 0.30)
        self.play(FadeIn(fbody), FadeIn(fcard), run_time=0.45)

        nbody = glass(5.5, 1.32, r=0.14).move_to([3.75, 1.16, 0])
        nums = VGroup(
            mix("m = 10000   n = 1000   k = 7", 12.5, SLATE_MUTE),
            VGroup(mix("理论 0.82%", 19, MINT), mix("实测 1.10%", 19, CORAL)).arrange(RIGHT, buff=0.40),
        ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        nums.move_to(nbody[1].get_center()).align_to(nbody[1], LEFT).shift(RIGHT * 0.28)
        self.play(FadeIn(nbody), FadeIn(nums), run_time=0.45)

        ratio = 10.0
        ks = list(range(1, 9))
        ps = [(1 - math.exp(-k / ratio)) ** k for k in ks]
        best = min(range(len(ps)), key=lambda i: ps[i])

        base_y, max_h, step_x = -0.42, 1.05, 0.56
        bars = VGroup()
        for i, (k, p) in enumerate(zip(ks, ps)):
            h = max_h * (p / max(ps))
            bar = RoundedRectangle(corner_radius=0.04, width=0.32, height=h, stroke_width=0,
                                  fill_color=MINT if i == best else ICE, fill_opacity=1 if i == best else 0.55)
            bar.move_to([1.02 + i * step_x, base_y + h / 2, 0])
            klbl = mono(str(k), 10, SLATE_MUTE).next_to(bar, DOWN, buff=0.05)
            bars.add(VGroup(bar, klbl))

        chart_title = mix("k 从 1 到 8，m/n = 10", 11.5, SLATE_MUTE)
        chart_title.next_to(bars, UP, buff=0.16).align_to(bars, LEFT)

        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.08) for b in bars], lag_ratio=0.09), run_time=0.8)
        self.play(FadeIn(chart_title), run_time=0.3)

        best_lbl = mix(f"k=7 触底 {ps[best]*100:.2f}%，再大反而回升", 11.5, MINT)
        best_lbl.next_to(bars, DOWN, buff=0.30).align_to(bars, LEFT)
        self.play(FadeIn(best_lbl), run_time=0.35)

        km = kaimao("k 不是越大越好：位被填满得越快，误判反而升高喵。", at=(-3.45, -2.95), width=4.9)
        self.play(FadeIn(km, shift=UP * 0.1), run_time=0.6)

        self.wait(2.9)
