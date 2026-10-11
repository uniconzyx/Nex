import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 多学科首页仪表盘：顶部横向学科切换 Tab + 猫咪问候 + 进度环 + 跨学科推荐 + 混合继续学习
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  Subject _subject = Subject.cpp;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          _subjectTabs(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              children: [
                _greetingCard(),
                const SizedBox(height: 14),
                _progressRow(),
                const SizedBox(height: 14),
                _crossRecommend(),
                const SizedBox(height: 14),
                const Text("继续学习", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                _continueCard(),
              ],
            ),
          ),
        ]),
      ),
    );
  }

  // 顶部横向学科切换 Tab（需求 §二.1）
  Widget _subjectTabs() => Container(
        height: 44,
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          itemCount: Subject.values.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final s = Subject.values[i];
            final sel = s == _subject;
            return GestureDetector(
              onTap: () => setState(() => _subject = s),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: sel ? AppColors.blue : Colors.transparent,
                  borderRadius: BorderRadius.circular(99),
                ),
                child: Row(children: [
                  Icon(s.icon, size: 16, color: sel ? Colors.white : const Color(0xFF64748B)),
                  const SizedBox(width: 4),
                  Text(s.shortLabel,
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: sel ? Colors.white : const Color(0xFF64748B))),
                ]),
              ),
            );
          },
        ),
      );

  Widget _greetingCard() => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(gradient: AppColors.gradientHeader, borderRadius: BorderRadius.circular(20)),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text("主人，下午好 🐱", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.white)),
              const SizedBox(height: 4),
              Text("今天主攻「${_subject.label}」，继续冲喵~",
                  style: const TextStyle(fontSize: 12.5, color: Colors.white70)),
            ]),
          ),
          CppCatMascot(mood: CatMood.cheer, size: 56),
        ]),
      );

  Widget _progressRow() => Row(children: [
        SizedBox(
          width: 92,
          height: 92,
          child: Stack(alignment: Alignment.center, children: [
            const CircularProgressIndicator(value: 0.42, strokeWidth: 9, backgroundColor: AppColors.ice, color: AppColors.blue),
            const Column(mainAxisSize: MainAxisSize.min, children: [
              Text("42%", style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.blue)),
              Text("总掌握度", style: TextStyle(fontSize: 10, color: Color(0xFF64748B))),
            ]),
          ]),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text("${_subject.label} · 进度", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                LinearProgressIndicator(value: 0.6, backgroundColor: AppColors.ice, color: _subject.accent, minHeight: 6),
                const SizedBox(height: 4),
                const Text("第 3 章 · 已学 12/20 节", style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ]),
            ),
          ),
        ),
      ]);

  // 跨学科推荐（需求 §二.1 新增）
  Widget _crossRecommend() => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(children: [
            const Icon(Icons.tips_and_updates_rounded, color: AppColors.amber),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text("跨学科推荐", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text("今天学完 C++ 后，再刷 2 道考研数学极限题，劳逸结合~",
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
              ]),
            ),
            TextButton(onPressed: () => context.go("/bank"), child: const Text("去刷题")),
          ]),
        ),
      );

  // 混合继续学习（按最近学习学科）
  Widget _continueCard() => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => context.go("/bank"),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              CppCatMascot(mood: CatMood.thinking, size: 44, glow: false),
              const SizedBox(width: 10),
              const Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text("最近学习：C++ 内存模型", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                  SizedBox(height: 4),
                  Text("上次学到：std::move 与右值引用", style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                ]),
              ),
              const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: AppColors.blue),
            ]),
          ),
        ),
      );
}
