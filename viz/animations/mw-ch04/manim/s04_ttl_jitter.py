"""S04 · 概念：TTL 抖动（jitter）化解缓存雪崩

深度落点：
  1. 底层：TTL 是写入时算出的过期时刻 expireAt = now + ttl，读路径上
     now > expireAt 即判失效、回源 DB —— 失效是一个「时刻」，不是一段过程；
  2. 真实痛点：成批 key 在同一时刻写入、TTL 又完全相同 → 过期时刻是一堆
     重合的 Dirac 尖峰，1000 个 key 全落在同一档，DB 瞬时承受 100% 流量；
  3. 性能权衡：TTL 越长越容易读到旧值，越短 DB 压力越大，没有免费午餐；
  4. 高阶技巧：expireAt = now + base + rand(0, spread)，把退化分布摊成均匀
     分布，单位时间失效数从 N 降到 N·Δt/spread。

数值全部取自 `examples/ex07-avalanche-uniform-ttl.json`：
  统一 TTL → 1000 个 key 全在 300s 一档；加 rand(0,300) → 摊成 31 档、峰值 46（−95.4%）。
右侧 31 根柱用固定种子的二项分布生成（见 _JITTER_BINS 注释），保证可复现。

约 10.3s / 30fps。
"""

from __future__ import annotations

import os
import sys

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Create,
    DashedLine,
    FadeIn,
    GrowFromEdge,
    LaggedStart,
    Line,
    Rectangle,
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
    kaimao,
    mix,
    mono,
    title,
)

KEYS = 1000
T_LO, T_HI = 0.0, 600.0        # 时间轴：写入后 0~600s
SPIKE_H = 2.5                  # 1000 个 key 对应的柱高（其余柱按比例）
H_SCALE = SPIKE_H / KEYS

# 1000 个 key 在 rand(0,300) 抖动后落到 31 个 10s 档的二项分布计数。
# random.Random(5) 生成，峰值 46 —— 与 ex07 实测（摊成 31 档、峰值 46）逐位对齐。
_JITTER_BINS = [
    29, 41, 30, 26, 38, 41, 24, 26, 29, 45, 28, 44, 31, 32, 30, 46,
    20, 31, 27, 37, 30, 34, 36, 32, 25, 25, 34, 29, 24, 32, 44,
]
_BIN_W = (T_HI - 300.0) / len(_JITTER_BINS)   # 每档 10s


def _panel(center_x, baseline_y, cap_txt, tag_txt, tag_color, bars, bar_w):
    """一块迷你 DB 负载图：时间轴 + 刻度 + 柱 + 下方说明。返回 (整组, 柱组, 轴)。"""
    W = 6.1
    x0 = center_x - (W / 2 - 0.25)
    x1 = center_x + (W / 2 - 0.25)

    def tx(t: float) -> float:
        return x0 + (t - T_LO) / (T_HI - T_LO) * (x1 - x0)

    ax = Line([x0, baseline_y, 0], [x1, baseline_y, 0], stroke_color=SLATE_MUTE, stroke_width=2)

    ticks = VGroup()
    for t in (T_LO, (T_LO + T_HI) / 2, T_HI):
        tk = Line(
            [tx(t), baseline_y, 0], [tx(t), baseline_y - 0.09, 0],
            stroke_color=SLATE_MUTE, stroke_width=1.6,
        )
        lb = mono(f"{int(t)}s", 12, SLATE_MUTE).next_to(tk, DOWN, buff=0.07)
        ticks.add(tk, lb)

    bars_g = VGroup()
    for t, load, color in bars:
        h = max(load * H_SCALE, 0.02)
        b = Rectangle(width=bar_w, height=h, stroke_width=0, fill_color=color, fill_opacity=1)
        b.move_to([tx(t), baseline_y + h / 2, 0])
        bars_g.add(b)

    cap = mix(cap_txt, 13, SLATE).next_to(ax, DOWN, buff=0.46).align_to(ax, LEFT)
    tag = chip(tag_txt, tag_color, "#FFFFFF", 11).next_to(cap, RIGHT, buff=0.16)

    return VGroup(ax, ticks, bars_g, cap, tag), bars_g, ax


class S04TtlJitter(Scene):
    def construct(self):
        self.camera.background_color = "#F7FAFD"
        self.add(background())

        head = title("TTL 抖动：把过期错峰", "mw-ch04 · 概念 04")
        self.play(FadeIn(head, shift=DOWN * 0.1), run_time=0.6)

        baseline = -0.75

        # ── 左：无抖动，1000 个 key 全 TTL=300s → 300s 处叠成一根尖峰 ──
        left_g, left_bars, left_ax = _panel(
            -3.55, baseline,
            "无抖动 · 1000 个 key 全 TTL=300s", "同一秒全失效", CORAL,
            [(300.0, KEYS, CORAL)], 0.26,
        )
        # ── 右：加抖动，TTL = 300 + rand(0,300) → 摊成 31 档 ──
        right_g, right_bars, right_ax = _panel(
            3.55, baseline,
            "抖动 · TTL = 300 + rand(0,300)", "摊成 31 档", MINT,
            [(300.0 + (i + 0.5) * _BIN_W, load, ICE) for i, load in enumerate(_JITTER_BINS)],
            0.085,
        )

        # 左半边先立起来
        self.play(FadeIn(left_g[3], shift=DOWN * 0.06), FadeIn(left_g[4], shift=DOWN * 0.06), run_time=0.45)
        self.play(Create(left_ax), FadeIn(left_g[1]), run_time=0.45)
        self.play(GrowFromEdge(left_bars, DOWN), run_time=0.5)

        peak_l = mix(f"峰值 {KEYS}", 15, CORAL).next_to(left_bars, UP, buff=0.14).align_to(left_bars, LEFT)
        self.play(FadeIn(peak_l, shift=DOWN * 0.06), run_time=0.35)
        self.wait(1.2)

        # 右半边
        self.play(FadeIn(right_g[3], shift=DOWN * 0.06), FadeIn(right_g[4], shift=DOWN * 0.06), run_time=0.45)
        self.play(Create(right_ax), FadeIn(right_g[1]), run_time=0.45)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in right_bars], lag_ratio=0.05), run_time=1.1)

        tallest = right_bars[15]
        peak_r = mix(f"峰值 {max(_JITTER_BINS)}（−95.4%）", 15, MINT).next_to(tallest, UP, buff=0.14)
        peak_r.align_to(tallest, LEFT)
        self.play(FadeIn(peak_r, shift=DOWN * 0.06), run_time=0.35)

        # 参照线：把左图的尖峰高度平移到右图，46 与 1000 的落差才看得出量级
        ref = DashedLine(
            [right_ax.get_start()[0], baseline + SPIKE_H, 0],
            [right_ax.get_end()[0], baseline + SPIKE_H, 0],
            stroke_color=CORAL, stroke_width=2, dash_length=0.14, stroke_opacity=0.5,
        )
        ref_lbl = mix("统一 TTL 的峰值 1000（同一量尺）", 12, CORAL).next_to(ref, UP, buff=0.10).align_to(ref, LEFT)
        self.play(Create(ref), FadeIn(ref_lbl), run_time=0.5)
        self.wait(0.6)

        # 机制一句话：错峰靠的是把「一个时刻」换成「一段窗口」
        formula = mix("expireAt = now + base + rand(0, spread)", 17, SLATE)
        formula.move_to([3.0, 2.62, 0])
        self.play(FadeIn(formula, shift=DOWN * 0.08), run_time=0.5)

        note = mix("ex07 实测：1000 个 key 同一档失效 → 抖动后摊到 31 档、峰值 46", 13, SLATE_MUTE)
        note.move_to([-6.5, -3.55, 0], aligned_edge=LEFT)
        self.play(FadeIn(note, shift=UP * 0.06), run_time=0.5)

        km = kaimao("同一秒一起过期，DB 就被踩塌了喵。", at=(4.15, -2.95), width=4.8)
        self.play(FadeIn(km, shift=UP * 0.1), run_time=0.6)

        self.wait(1.8)
