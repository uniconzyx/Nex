/// 题库通用组件库（阶段5 需求 §三.6）
library;

import "package:flutter/material.dart";

import "../core/models/exercise.dart";
import "../core/models/subject.dart";
import "../core/theme/app_colors.dart";
import "../widgets/cpp_cat.dart";

/// 难度颜色
Color diffColor(Difficulty d) => switch (d) {
      Difficulty.easy => AppColors.diffEasy,
      Difficulty.medium => AppColors.diffMid,
      Difficulty.hard => AppColors.diffHard,
    };

/// 题目状态颜色
Color statusColor(QuestionStatus s) => switch (s) {
      QuestionStatus.done => AppColors.green,
      QuestionStatus.wrong => AppColors.red,
      QuestionStatus.favorite => AppColors.amber,
      QuestionStatus.untouched => const Color(0xFF94A3B8),
    };

/// 通用题目卡片 ExerciseCard
class ExerciseCard extends StatelessWidget {
  const ExerciseCard({super.key, required this.exercise, this.onTap});

  final Exercise exercise;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              _tag(exercise.difficulty.label, diffColor(exercise.difficulty)),
              const SizedBox(width: 6),
              _tag(exercise.subject.shortLabel, exercise.subject.accent),
              const SizedBox(width: 6),
              _tag(exercise.type.label, dark ? const Color(0xFF94A3B8) : AppColors.blue),
              const Spacer(),
              _statusDot(exercise.status),
            ]),
            const SizedBox(height: 10),
            Text(exercise.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, height: 1.4)),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: Wrap(spacing: 6, children: [
                  for (final t in exercise.tags.take(3))
                    Text("#$t", style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                ]),
              ),
              Text("正确率 ${(exercise.correctRate * 100).round()}%",
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
            ]),
            if (exercise.sourceRef.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(children: [
                Icon(Icons.verified_rounded, size: 12, color: AppColors.blue),
                const SizedBox(width: 4),
                Expanded(
                  child: Text("依据：${exercise.sourceRef}",
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10.5, height: 1.5, color: AppColors.blue)),
                ),
              ]),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _tag(String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)),
        child: Text(label, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: c)),
      );

  Widget _statusDot(QuestionStatus s) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 7, height: 7, decoration: BoxDecoration(color: statusColor(s), shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(s.label, style: TextStyle(fontSize: 11, color: statusColor(s), fontWeight: FontWeight.w600)),
      ]);
}

/// 选择题选项 OptionSelector（支持单选/多选）
class OptionSelector extends StatefulWidget {
  const OptionSelector({super.key, required this.options, required this.multi, this.onChanged});

  final List<QuestionOption> options;
  final bool multi;
  final ValueChanged<Set<String>>? onChanged;

  @override
  State<OptionSelector> createState() => _OptionSelectorState();
}

class _OptionSelectorState extends State<OptionSelector> {
  final Set<String> _selected = {};

  void _toggle(String key) {
    setState(() {
      if (widget.multi) {
        _selected.contains(key) ? _selected.remove(key) : _selected.add(key);
      } else {
        _selected
          ..clear()
          ..add(key);
      }
    });
    widget.onChanged?.call(_selected);
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      for (final o in widget.options)
        GestureDetector(
          onTap: () => _toggle(o.key),
          child: Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: _selected.contains(o.key) ? AppColors.ice : Theme.of(context).colorScheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _selected.contains(o.key) ? AppColors.blue : Theme.of(context).colorScheme.outline,
                width: 1.5,
              ),
            ),
            child: Row(children: [
              Container(
                width: 24,
                height: 24,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: _selected.contains(o.key) ? AppColors.blue : Colors.transparent,
                  shape: BoxShape.circle,
                  border: Border.all(color: _selected.contains(o.key) ? AppColors.blue : const Color(0xFF94A3B8)),
                ),
                child: Text(o.key,
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: _selected.contains(o.key) ? Colors.white : const Color(0xFF64748B))),
              ),
              const SizedBox(width: 12),
              Expanded(child: Text(o.text, style: const TextStyle(fontSize: 13.5))),
            ]),
          ),
        ),
    ]);
  }
}

/// LaTeX 公式渲染 LatexRenderer（无依赖兜底：原样展示公式文本，标注 LaTeX）
class LatexRenderer extends StatelessWidget {
  const LatexRenderer({super.key, required this.latex, this.fontSize = 15});
  final String latex;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    if (latex.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: AppColors.ice.withValues(alpha: 0.6), borderRadius: BorderRadius.circular(12)),
      child: SelectableText(
        latex,
        style: TextStyle(fontFamily: "JetBrains Mono", fontSize: fontSize, color: const Color(0xFF1E3A8A), height: 1.5),
      ),
    );
  }
}

/// 测试用例面板 TestCasePanel
class TestCasePanel extends StatelessWidget {
  const TestCasePanel({super.key, required this.cases});
  final List<TestCase> cases;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("测试用例（${cases.length}）", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        for (final c in cases)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: dark ? const Color(0xFF0B1220) : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.ice),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(c.hidden ? Icons.lock_rounded : Icons.visibility_rounded, size: 14, color: const Color(0xFF64748B)),
                const SizedBox(width: 6),
                Text(c.hidden ? "隐藏用例" : "公开用例", style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ]),
              if (!c.hidden) ...[
                const SizedBox(height: 8),
                Text("输入: ${c.input.isEmpty ? "(空)" : c.input}",
                    style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12)),
                const SizedBox(height: 4),
                Text("输出: ${c.output.isEmpty ? "(空)" : c.output}",
                    style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12, color: AppColors.green)),
              ],
            ]),
          ),
      ],
    );
  }
}

/// 答题卡 AnswerCard（已答/未答/标记）
class AnswerCard extends StatelessWidget {
  const AnswerCard({super.key, required this.total, required this.answered, required this.marked, this.onTap});

  final int total;
  final Set<int> answered;
  final Set<int> marked;
  final ValueChanged<int>? onTap;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (var i = 1; i <= total; i++)
          GestureDetector(
            onTap: () => onTap?.call(i),
            child: Container(
              width: 34,
              height: 34,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: answered.contains(i) ? AppColors.blue : const Color(0xFFCBD5E1),
                borderRadius: BorderRadius.circular(8),
                border: marked.contains(i) ? Border.all(color: AppColors.amber, width: 2) : null,
              ),
              child: Text("$i", style: TextStyle(fontSize: 12, color: answered.contains(i) ? Colors.white : const Color(0xFF64748B), fontWeight: FontWeight.w700)),
            ),
          ),
      ],
    );
  }
}

/// 交卷成绩报告 ResultReport
class ResultReport extends StatelessWidget {
  const ResultReport({super.key, required this.score, required this.correct, required this.total, required this.usedSeconds});

  final int score;
  final int correct;
  final int total;
  final int usedSeconds;

  @override
  Widget build(BuildContext context) {
    final rate = total == 0 ? 0.0 : correct / total;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          const MaineCoonAssistant(status: AssistantStatus.celebrate, tip: "本次模考完成！猫咪给你生成了成绩报告~"),
          const SizedBox(height: 16),
          Text("$score 分", style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w800, color: AppColors.blue)),
          const SizedBox(height: 8),
          Text("正确 $correct / $total 题 · 正确率 ${(rate * 100).round()}% · 用时 ${usedSeconds ~/ 60} 分 ${usedSeconds % 60} 秒",
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B))),
          const SizedBox(height: 12),
          Text("击败了全国 ${(60 + rate * 38).round()}% 的考生 🎉", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.amber)),
        ]),
      ),
    );
  }
}

