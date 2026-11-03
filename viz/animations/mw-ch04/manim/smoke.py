"""阶段二前置冒烟：确认 Manim 能在无 LaTeX 的机器上渲染中文 + Unicode 公式 + 等宽字体。

待验证的三件事：
  1. Text(font="Microsoft YaHei") 能出中文；
  2. Unicode 的 ≈ → × ≤ 与手工上下标能正常显示（不依赖 MathTex）；
  3. register_font 注册的 JetBrains Mono 能被 Pango 认出来。

    manim -ql -s smoke.py SmokeFont
"""

from __future__ import annotations

import os
import sys

from manim import DOWN, LEFT, RIGHT, Scene, VGroup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from style import CN, MONO, SLATE, background, cn, mono, sup  # noqa: E402


class SmokeFont(Scene):
    def construct(self):
        self.camera.background_color = "#F7FAFD"
        self.add(background())

        line1 = cn("凯喵：中文正文，圆润无衬线。", 30, SLATE)
        line2 = mono("mono 0123456789 := func() <-\"ok\"", 22)
        line3 = VGroup(
            mono("p ", 24),
            mono("≈", 24),
            sup("(1 − e", "−kn/m", 24),
            sup(")", "k", 24),
            mono("  →  0.82%", 24),
        ).arrange(RIGHT, buff=0.04)
        line4 = mono("m = 10000, k = 7 → 理论 0.82% / 实测 1.10%", 18)

        g = VGroup(line1, line2, line3, line4).arrange(DOWN, buff=0.45, aligned_edge=LEFT)
        g.move_to([-1.2, 0.4, 0])
        self.add(g)

        # 字体是否真的被解析成 JetBrains Mono（Pango 找不到会静默回退，必须自己查）
        probe = mono("iiilll 000 WWW", 20)
        self.add(probe.next_to(g, DOWN, buff=0.6))
