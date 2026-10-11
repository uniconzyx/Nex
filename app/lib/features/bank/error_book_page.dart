import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../core/api/exercise_api.dart";
import "../../core/models/exercise.dart";
import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";
import "../../widgets/question_widgets.dart";

/// 错题本与收藏：按学科/知识点分组 + 艾宾浩斯复习提醒（阶段5 §三.4）
class ErrorBookPage extends StatefulWidget {
  const ErrorBookPage({super.key});
  @override
  State<ErrorBookPage> createState() => _ErrorBookPageState();
}

class _ErrorBookPageState extends State<ErrorBookPage> {
  List<Exercise> _items = [];
  bool _onlyWrong = true;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final items = _onlyWrong
        ? await exerciseRepo.wrongQuestions(null)
        : await exerciseRepo.favorites();
    setState(() {
      _items = items;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    // 按学科分组
    final groups = <Subject, List<Exercise>>{};
    for (final e in _items) {
      groups.putIfAbsent(e.subject, () => []).add(e);
    }
    return Scaffold(
      appBar: AppBar(title: const Text("错题本"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: true, label: Text("错题")),
              ButtonSegment(value: false, label: Text("收藏")),
            ],
            selected: {_onlyWrong},
            onSelectionChanged: (s) => setState(() {
              _onlyWrong = s.first;
              _load();
            }),
          ),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _items.isEmpty
                  ? const Center(child: CatBubble(text: "这里空空如也，继续保持全对喵~", mood: CatMood.celebrate))
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        const CatBubble(
                            text: "根据艾宾浩斯遗忘曲线，今天有 ${2} 题需要复习，趁热打铁效果最好喵~",
                            mood: CatMood.comfort),
                        const SizedBox(height: 12),
                        for (final g in groups.entries) ...[
                          Row(children: [
                            Icon(g.key.icon, color: g.key.accent, size: 18),
                            const SizedBox(width: 6),
                            Text(g.key.label, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: g.key.accent)),
                          ]),
                          const SizedBox(height: 8),
                          for (final e in g.value)
                            ExerciseCard(
                              exercise: e,
                              onTap: () => context.go("/bank/${e.id}"),
                            ),
                          const SizedBox(height: 4),
                        ],
                      ],
                    ),
        ),
      ]),
    );
  }
}
