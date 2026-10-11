import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/settings/settings.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 个人中心：成就徽章 + 学习数据可视化 + CppCat 陪伴 + 设置（PRD §14.4）
class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(settingsProvider);
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Row(children: [
              CppCatMascot(mood: CatMood.celebrate, size: 64),
              const SizedBox(width: 14),
              const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text("主人", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                Text("连续学习 12 天 · 掌握 42%", style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
              ]),
            ]),
            const SizedBox(height: 16),
            // 双轨数据统计：考研倒计时 + 编程刷题量（需求 §二.6）
            Row(children: [
              Expanded(
                child: _StatCard(
                  icon: Icons.event_rounded,
                  color: AppColors.red,
                  title: "考研倒计时",
                  value: "92 天",
                  sub: "距 2027 考研",
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _StatCard(
                  icon: Icons.code_rounded,
                  color: AppColors.blue,
                  title: "编程刷题量",
                  value: "236 题",
                  sub: "本月新增 48 题",
                ),
              ),
            ]),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(children: [
                  const Text("本周学习时长", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 90,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [for (final v in [20, 35, 15, 50, 40, 60, 30])
                        Expanded(
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            height: v.toDouble(),
                            decoration: const BoxDecoration(gradient: AppColors.gradientBlue, borderRadius: BorderRadius.vertical(top: Radius.circular(6))),
                          ),
                        )],
                    ),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 12),
            const Text("成就徽章", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 10, runSpacing: 10, children: [
              _Badge(Icons.emoji_events_rounded, "首题 AC", AppColors.amber),
              _Badge(Icons.thread_rounded, "并发入门", AppColors.blue),
              _Badge(Icons.pets_rounded, "猫之友", AppColors.cyan),
              _Badge(Icons.local_fire_department_rounded, "连续 7 天", AppColors.red),
            ]),
            const SizedBox(height: 16),
            Card(
              child: Column(children: [
                SwitchListTile(
                  title: const Text("深色模式"),
                  secondary: const Icon(Icons.dark_mode_rounded, color: AppColors.blue),
                  value: s.themeMode == ThemeMode.dark,
                  onChanged: (v) => ref.read(settingsProvider.notifier).setThemeMode(v ? ThemeMode.dark : ThemeMode.light),
                ),
                SwitchListTile(
                  title: const Text("减少动效"),
                  secondary: const Icon(Icons.reduced_motion_rounded, color: AppColors.blue),
                  subtitle: const Text("关闭猫咪动画与转场"),
                  value: s.reduceMotion,
                  onChanged: (v) => ref.read(settingsProvider.notifier).setReduceMotion(v),
                ),
                SwitchListTile(
                  title: const Text("音效"),
                  secondary: const Icon(Icons.volume_up_rounded, color: AppColors.blue),
                  subtitle: const Text("CppCat 发送 / 回复 / 编译结果提示音"),
                  value: s.soundEnabled,
                  onChanged: (v) => ref.read(settingsProvider.notifier).setSoundEnabled(v),
                ),
                ListTile(
                  leading: const Icon(Icons.text_fields_rounded, color: AppColors.blue),
                  title: const Text("字号缩放"),
                  trailing: SizedBox(
                    width: 150,
                    child: Slider(
                      value: s.fontScale,
                      min: 0.85,
                      max: 1.3,
                      divisions: 9,
                      label: "${(s.fontScale * 100).toInt()}%",
                      onChanged: (v) => ref.read(settingsProvider.notifier).setFontScale(v),
                    ),
                  ),
                ),
                ListTile(
                  leading: const Icon(Icons.login_rounded, color: AppColors.blue),
                  title: const Text("登录 / 注册"),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14),
                  onTap: () => context.go("/login"),
                ),
              ]),
            ),
            if (dark) const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge(this.icon, this.label, this.color);
  final IconData icon;
  final String label;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(14)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 6),
        Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
      ]),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.icon, required this.color, required this.title, required this.value, required this.sub});
  final IconData icon;
  final Color color;
  final String title;
  final String value;
  final String sub;
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(width: 6),
            Text(title, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
          ]),
          const SizedBox(height: 8),
          Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: color)),
          Text(sub, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
        ]),
      ),
    );
  }
}
