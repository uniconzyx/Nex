import "package:flutter/material.dart";

/// Nex 设计系统 · 色彩 tokens（PRD §14 蓝白猫咪版，与 web-preview / Tailwind 配置同源）
class AppColors {
  AppColors._();

  static const blue = Color(0xFF3B82F6);   // 主蓝
  static const blueLight = Color(0xFF60A5FA); // 浅蓝
  static const ice = Color(0xFFDBEAFE);    // 冰蓝
  static const cyan = Color(0xFF22D3EE);   // 强调青

  static const green = Color(0xFF22C55E);  // 成功绿 / 简单
  static const amber = Color(0xFFF59E0B);  // 警告黄 / 中等 / 薄弱
  static const red = Color(0xFFEF4444);    // 错误红 / 困难

  // 亮色
  static const bgLight = Color(0xFFF8FAFC);
  static const cardLight = Color(0xFFFFFFFF);
  static const inkLight = Color(0xFF0F172A);
  static const subLight = Color(0xFF64748B);

  // 暗色
  static const bgDark = Color(0xFF0F172A);
  static const cardDark = Color(0xFF1E293B);
  static const inkDark = Color(0xFFE2E8F0);
  static const subDark = Color(0xFF94A3B8);

  /// 思维导图节点四态（PRD §14.3）
  static const nodeMastered = blue;
  static const nodeLearning = blueLight;
  static const nodeTodo = Color(0xFFCBD5E1);
  static const nodeWeak = amber;

  /// 难度标签
  static const diffEasy = green;
  static const diffMid = amber;
  static const diffHard = red;

  static const gradientBlue = LinearGradient(
    begin: Alignment.topLeft, end: Alignment.bottomRight,
    colors: [blue, blueLight],
  );
  static const gradientHeader = LinearGradient(
    begin: Alignment.topLeft, end: Alignment.bottomRight,
    colors: [blue, blueLight, Color(0xFF93C5FD)],
  );
}
