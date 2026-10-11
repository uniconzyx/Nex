"""CppCat AI 助手音效资源生成器（纯标准库，无第三方依赖）。

生成 7 个短音效 WAV 到 app/assets/audio/，供 Flutter 侧 audioplayers 播放。
Web 预览版（web-preview/index.html）用 Web Audio API 合成**同一套参数**，
两端音色保持一致 —— 改这里就必须同步改 index.html 里的 SOUND 常量表。

设计原则：
  * 相位累加合成（频率变化时不产生相位跳变，避免爆音）
  * 5ms attack + 指数衰减包络（短促不刺耳，无 click）
  * 振幅上限 0.35（多音叠加留 headroom，不削波）
  * CppCat 是「电子喵」风格：轻、短、上扬为主，失败音也必须柔和（不打击用户）

用法：
    python app/tool/gen_audio_assets.py
"""

from __future__ import annotations

import math
import pathlib
import struct
import wave

SR = 44100          # 采样率
AMP = 0.35          # 全局振幅上限
ATTACK_MS = 5.0     # 起音时间，防爆音


# ---------------------------------------------------------------- 基础合成

def _sweep(f0: float, f1: float, dur_ms: float, amp: float = AMP,
           curve: str = "exp", vibrato_hz: float = 0.0, vibrato_depth: float = 0.0,
           decay: float = 3.2) -> list[float]:
    """频率滑音。f0→f1 按指数/线性变化，相位累加保证连续。

    decay 越大衰减越快（决定听感长短）。
    """
    n = int(SR * dur_ms / 1000.0)
    attack = max(1, int(SR * ATTACK_MS / 1000.0))
    out: list[float] = []
    phase = 0.0
    for i in range(n):
        r = i / n
        f = f0 * (f1 / f0) ** r if curve == "exp" else f0 + (f1 - f0) * r
        if vibrato_hz:
            f *= 1.0 + vibrato_depth * math.sin(2 * math.pi * vibrato_hz * i / SR)
        phase += 2 * math.pi * f / SR
        s = math.sin(phase)
        env = (i / attack) if i < attack else math.exp(-decay * (i - attack) / n)
        out.append(s * env * amp)
    return out


def _silence(dur_ms: float) -> list[float]:
    return [0.0] * int(SR * dur_ms / 1000.0)


def _mix(*tracks: list[float]) -> list[float]:
    """把多轨等长混音（短轨按 0 补齐）。"""
    length = max(len(t) for t in tracks)
    acc = [0.0] * length
    for t in tracks:
        for i, v in enumerate(t):
            acc[i] += v
    return acc


def _seq(*parts: list[float]) -> list[float]:
    """顺序拼接。"""
    out: list[float] = []
    for p in parts:
        out.extend(p)
    return out


def _normalize(buf: list[float], peak: float = 0.85) -> list[float]:
    m = max((abs(v) for v in buf), default=0.0)
    if m == 0:
        return buf
    k = peak / m
    return [v * k for v in buf]


def _write_wav(path: pathlib.Path, buf: list[float]) -> None:
    buf = _normalize(buf)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)          # 16-bit PCM
        w.setframerate(SR)
        frames = bytearray()
        for v in buf:
            s = max(-1.0, min(1.0, v))
            frames += struct.pack("<h", int(s * 32767))
        w.writeframes(bytes(frames))


# ---------------------------------------------------------------- 音效定义

# 频率取自 C 大调五度内音程，听感「明亮、友好」；失败音用下行小三度，柔和

def snd_send() -> list[float]:
    """发送消息：短促上扬滑音（像猫咪应了一声「喵?」）。"""
    return _seq(
        _sweep(620, 1040, 110, amp=0.30, vibrato_hz=22, vibrato_depth=0.012),
        _silence(10),
    )


def snd_receive() -> list[float]:
    """收到回复：双音上行，柔和收尾。"""
    return _seq(
        _sweep(880, 880, 70, amp=0.26, decay=4.0),
        _silence(18),
        _sweep(1170, 1170, 130, amp=0.28, decay=2.6),
    )


def snd_thinking() -> list[float]:
    """思考/编译中：三连轻 ping（提示「我在处理」）。"""
    return _seq(
        _sweep(1318, 1318, 45, amp=0.20, decay=5.5), _silence(70),
        _sweep(1318, 1318, 45, amp=0.20, decay=5.5), _silence(70),
        _sweep(1568, 1568, 55, amp=0.22, decay=4.5),
    )


def snd_success() -> list[float]:
    """编译通过 / 答对：C-E-G 上行琶音。"""
    return _seq(
        _sweep(523.25, 523.25, 80, amp=0.24, decay=4.0),
        _sweep(659.25, 659.25, 80, amp=0.24, decay=4.0),
        _sweep(783.99, 783.99, 170, amp=0.26, decay=2.4),
    )


def snd_celebrate() -> list[float]:
    """AC / 庆祝：琶音上扬到高音 + 尾部双音闪光。"""
    return _seq(
        _sweep(523.25, 523.25, 70, amp=0.22, decay=4.5),
        _sweep(659.25, 659.25, 70, amp=0.22, decay=4.5),
        _sweep(783.99, 783.99, 70, amp=0.22, decay=4.5),
        _mix(
            _sweep(1046.50, 1046.50, 200, amp=0.22, decay=2.2),
            _seq(_silence(60), _sweep(1318.51, 1318.51, 140, amp=0.16, decay=3.0)),
        ),
    )


def snd_fail() -> list[float]:
    """编译失败 / 答错：下行小三度，柔和安慰（绝不能刺耳）。"""
    return _seq(
        _sweep(466.16, 466.16, 130, amp=0.20, decay=3.0),
        _sweep(392.00, 349.23, 220, amp=0.18, decay=2.4),
    )


def snd_tap() -> list[float]:
    """点击猫咪：极短 blip。"""
    return _sweep(1568, 1568, 35, amp=0.16, decay=7.0)


SOUNDS = {
    "send": snd_send,
    "receive": snd_receive,
    "thinking": snd_thinking,
    "success": snd_success,
    "celebrate": snd_celebrate,
    "fail": snd_fail,
    "tap": snd_tap,
}


def main() -> None:
    out_dir = pathlib.Path(__file__).resolve().parents[1] / "assets" / "audio"
    total = 0
    for name, fn in SOUNDS.items():
        buf = fn()
        path = out_dir / f"{name}.wav"
        _write_wav(path, buf)
        size_kb = path.stat().st_size / 1024
        ms = len(buf) / SR * 1000
        total += path.stat().st_size
        print(f"  {name+'.wav':16s} {ms:6.0f} ms  {size_kb:6.1f} KB")
    print(f"共 {len(SOUNDS)} 个音效，合计 {total/1024:.1f} KB -> {out_dir}")


if __name__ == "__main__":
    main()
