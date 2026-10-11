import "package:flutter/material.dart";

import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/question_widgets.dart";

/// 模拟考试：答题卡 + 交卷成绩报告（阶段5 §三.3）
class ExamPage extends StatefulWidget {
  const ExamPage({super.key, this.subject = Subject.math});
  final Subject subject;

  @override
  State<ExamPage> createState() => _ExamPageState();
}

class _ExamPageState extends State<ExamPage> {
  final Set<int> _answered = {1, 2, 4};
  final Set<int> _marked = {5};
  bool _submitted = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("${widget.subject.label} · 模拟考试"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 计时器 + 交卷
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(children: [
                const Icon(Icons.timer_rounded, color: AppColors.blue),
                const SizedBox(width: 8),
                const Text("剩余时间 42:18", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                const Spacer(),
                FilledButton(
                  onPressed: () => setState(() => _submitted = true),
                  child: const Text("交卷"),
                ),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          const Text("答题卡", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                AnswerCard(total: 12, answered: _answered, marked: _marked),
                const SizedBox(height: 12),
                Wrap(spacing: 16, children: [
                  _legend(AppColors.blue, "已答"),
                  _legend(const Color(0xFFCBD5E1), "未答"),
                  _legend(AppColors.amber, "标记"),
                ]),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          if (_submitted) ResultReport(score: 86, correct: 10, total: 12, usedSeconds: 1078),
        ],
      ),
    );
  }

  Widget _legend(Color c, String label) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 12, height: 12, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
      ]);
}
