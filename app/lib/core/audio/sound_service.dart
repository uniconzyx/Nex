import "dart:async";

import "package:audioplayers/audioplayers.dart";
import "package:flutter/foundation.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../settings/settings.dart";

/// CppCat 音效事件。
///
/// 每个枚举项对应 `app/assets/audio/<asset>.wav`，资产由
/// `app/tool/gen_audio_assets.py` 纯标准库合成（无外部素材依赖）。
///
/// **三处同源**：改音色时必须同步修改
///   1. `app/tool/gen_audio_assets.py`（Flutter 资源）
///   2. `web-preview/index.html` 的 `SOUND` 参数表（Web Audio 实时合成）
///   3. 本枚举（Dart 侧事件名）
enum CppSound {
  /// 用户发送消息
  send("send", volume: 0.85),

  /// AI 回复完成
  receive("receive", volume: 0.85),

  /// 请求已发出、等待首 token（「我在处理」）
  thinking("thinking", volume: 0.55),

  /// 编译通过 / 答对
  success("success", volume: 0.85),

  /// AC / 庆祝
  celebrate("celebrate", volume: 0.9),

  /// 编译失败 / 答错（音色柔和，不打击学习积极性）
  fail("fail", volume: 0.7),

  /// 点击猫咪
  tap("tap", volume: 0.5);

  const CppSound(this.asset, {required this.volume});

  final String asset;
  final double volume;

  /// audioplayers 的 AssetSource 前缀默认是 `assets/`，
  /// 因此这里只需给出 `assets/` 之后的相对路径。
  String get path => "audio/$asset.wav";
}

/// 音效播放服务。
///
/// 设计取舍：
/// * **每个音效一个 AudioPlayer**（7 个常驻实例）—— 短音效之间互不打断；
///   若共用一个实例，连续触发会把前一声掐断，听感像「卡顿」。
/// * **fire-and-forget**：`play()` 同步返回，播放失败绝不影响 UI 与业务流程。
/// * **连续失败自动静音**：桌面/Web 等平台若缺少音频后端，避免每帧刷日志
///   （Web 的自动播放策略也会导致首帧前失败，属预期）。
/// * **开关独立于「减少动效」**：动效与声音是两种不同的无障碍偏好，
///   合并成一个开关会让「想安静但要看动画」的用户无法表达。
class SoundService {
  SoundService(this._ref);

  final Ref _ref;

  final Map<CppSound, AudioPlayer> _pool = {};
  int _failCount = 0;
  bool _mutedByError = false;

  /// 尝试把音频文件读入缓存，降低首次播放延迟。
  /// 失败静默忽略（不影响后续正常播放）。
  Future<void> warmUp() async {
    try {
      // 注意：AudioCache 的签名是 (String fileName)，不是 Source；
      // 文件名相对 AudioCache.prefix（默认 "assets/"）。
      await AudioCache.instance.loadAll(
        CppSound.values.map((s) => s.path).toList(),
      );
    } catch (e) {
      debugPrint("[SoundService] 预热失败（不影响播放）：$e");
    }
  }

  /// 播放音效。同步返回，异常内部消化。
  void play(CppSound sound) {
    if (_mutedByError) return;
    if (!_ref.read(settingsProvider).soundEnabled) return;
    unawaited(_play(sound));
  }

  Future<void> _play(CppSound sound) async {
    try {
      final player = _pool.putIfAbsent(sound, () {
        final p = AudioPlayer();
        // 短音效走低延迟模式；播完停在结尾，下次 play 从 0 重放。
        unawaited(p.setPlayerMode(PlayerMode.lowLatency));
        unawaited(p.setReleaseMode(ReleaseMode.stop));
        return p;
      });
      await player.stop();
      await player.play(AssetSource(sound.path), volume: sound.volume);
    } catch (e) {
      _failCount++;
      // 连续 3 次失败说明该平台没有可用音频后端，整体静音并只报一次。
      if (_failCount >= 3 && !_mutedByError) {
        _mutedByError = true;
        debugPrint("[SoundService] 音频后端不可用，本次会话已静音：$e");
      }
    }
  }

  Future<void> dispose() async {
    for (final p in _pool.values) {
      await p.dispose();
    }
    _pool.clear();
  }
}

final soundServiceProvider = Provider<SoundService>((ref) {
  final service = SoundService(ref);
  // 首帧后预热，避免阻塞启动。
  Future.microtask(service.warmUp);
  ref.onDispose(service.dispose);
  return service;
});
