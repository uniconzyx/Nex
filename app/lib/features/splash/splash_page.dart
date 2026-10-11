import "dart:async";
import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../widgets/cpp_cat.dart";

/// 启动页：3D 缅因猫头像居中 + 「CppCat 正在唤醒…」（PRD §14 缅因猫版）
class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  @override
  void initState() {
    super.initState();
    Timer(const Duration(seconds: 2), () {
      if (mounted) context.go("/home");
    });
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: dark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CppCatMascot(mood: CatMood.happy, size: 132),
            const SizedBox(height: 18),
            Text(
              "Nex",
              style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.w800,
                color: Theme.of(context).colorScheme.primary,
                letterSpacing: 1,
              ),
            ),
            const SizedBox(height: 8),
            const Text("小蓝猫 CppCat 正在唤醒…",
                style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
            const SizedBox(height: 22),
            const SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
          ],
        ),
      ),
    );
  }
}
