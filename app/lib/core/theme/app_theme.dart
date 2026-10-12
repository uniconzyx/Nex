import "package:flutter/material.dart";

import "app_colors.dart";

/// 亮/暗双主题：卡片 18px 圆角、按钮 14px、输入框 12px、柔和蓝色微光阴影（PRD §14.1）
class AppTheme {
  AppTheme._();

  static ThemeData light() => _base(
        brightness: Brightness.light,
        scaffold: AppColors.bgLight,
        card: AppColors.cardLight,
        ink: AppColors.inkLight,
        sub: AppColors.subLight,
      );

  static ThemeData dark() => _base(
        brightness: Brightness.dark,
        scaffold: AppColors.bgDark,
        card: AppColors.cardDark,
        ink: AppColors.inkDark,
        sub: AppColors.subDark,
      );

  static ThemeData _base({
    required Brightness brightness,
    required Color scaffold,
    required Color card,
    required Color ink,
    required Color sub,
  }) {
    final scheme = ColorScheme(
      brightness: brightness,
      primary: AppColors.blue,
      onPrimary: Colors.white,
      secondary: AppColors.cyan,
      onSecondary: Colors.white,
      error: AppColors.red,
      onError: Colors.white,
      surface: card,
      onSurface: ink,
      surfaceContainerHighest: AppColors.ice,
      outline: brightness == Brightness.light
          ? const Color(0xFFE2E8F0)
          : const Color(0xFF334155),
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scaffold,
      fontFamily: "PingFang SC",
      textTheme: TextTheme(
        titleLarge: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: ink),
        titleMedium: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: ink),
        bodyMedium: TextStyle(fontSize: 13, height: 1.65, color: ink),
        bodySmall: TextStyle(fontSize: 11, height: 1.5, color: sub),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        margin: const EdgeInsets.only(bottom: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: scheme.outline),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.blue,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: card,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        hintStyle: TextStyle(fontSize: 12, color: sub),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: scheme.outline, width: 1.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: scheme.outline, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.blue, width: 1.5),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.ice,
        labelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.blue),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(99)),
        side: BorderSide.none,
      ),
      dividerTheme: DividerThemeData(color: scheme.outline, thickness: 1, space: 1),
    );
  }
}
