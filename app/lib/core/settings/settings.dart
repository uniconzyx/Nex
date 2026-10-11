import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:shared_preferences/shared_preferences.dart";

/// 全局设置：主题模式 / 减少动效 / 字号缩放 / 音效（PRD §14.5/14.6 可访问性）
class SettingsState {
  const SettingsState({
    this.themeMode = ThemeMode.system,
    this.reduceMotion = false,
    this.fontScale = 1.0,
    this.soundEnabled = true,
  });

  final ThemeMode themeMode;
  final bool reduceMotion;
  final double fontScale;

  /// CppCat AI 助手音效开关（见 core/audio/sound_service.dart）。
  /// 独立于 reduceMotion：动效与声音是两种不同的无障碍偏好。
  final bool soundEnabled;

  SettingsState copyWith({
    ThemeMode? themeMode,
    bool? reduceMotion,
    double? fontScale,
    bool? soundEnabled,
  }) =>
      SettingsState(
        themeMode: themeMode ?? this.themeMode,
        reduceMotion: reduceMotion ?? this.reduceMotion,
        fontScale: fontScale ?? this.fontScale,
        soundEnabled: soundEnabled ?? this.soundEnabled,
      );
}

class SettingsNotifier extends Notifier<SettingsState> {
  static const _kTheme = "settings.theme";
  static const _kMotion = "settings.reduceMotion";
  static const _kFont = "settings.fontScale";
  static const _kSound = "settings.soundEnabled";

  @override
  SettingsState build() {
    _load();
    return const SettingsState();
  }

  Future<void> _load() async {
    final sp = await SharedPreferences.getInstance();
    state = SettingsState(
      themeMode: ThemeMode.values[sp.getInt(_kTheme) ?? 0],
      reduceMotion: sp.getBool(_kMotion) ?? false,
      fontScale: sp.getDouble(_kFont) ?? 1.0,
      soundEnabled: sp.getBool(_kSound) ?? true,
    );
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    state = state.copyWith(themeMode: mode);
    (await SharedPreferences.getInstance()).setInt(_kTheme, mode.index);
  }

  Future<void> setReduceMotion(bool v) async {
    state = state.copyWith(reduceMotion: v);
    (await SharedPreferences.getInstance()).setBool(_kMotion, v);
  }

  Future<void> setFontScale(double v) async {
    state = state.copyWith(fontScale: v.clamp(0.85, 1.3));
    (await SharedPreferences.getInstance()).setDouble(_kFont, state.fontScale);
  }
}

final settingsProvider = NotifierProvider<SettingsNotifier, SettingsState>(SettingsNotifier.new);
