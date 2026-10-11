import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../core/api/exercise_api.dart";
import "../../core/models/exercise.dart";
import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";
import "../../widgets/question_widgets.dart";

/// 题库大厅：学科/题型/难度/来源筛选 + 搜索 + 状态标签 + ExerciseCard（阶段5 §三.1）
class BankPage extends StatefulWidget {
  const BankPage({super.key, this.subject});
  final Subject? subject;

  @override
  State<BankPage> createState() => _BankPageState();
}

class _BankPageState extends State<BankPage> {
  Subject? _subject;
  ExerciseType? _type;
  Difficulty? _difficulty;
  QuestionSource? _source;
  QuestionStatus? _status;
  final _search = TextEditingController();
  List<Exercise> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _subject = widget.subject;
    _reload();
  }

  Future<void> _reload() async {
    setState(() => _loading = true);
    final items = await exerciseRepo.list(ExerciseFilter(
      subject: _subject,
      type: _type,
      difficulty: _difficulty,
      source: _source,
      status: _status,
      keyword: _search.text,
    ));
    setState(() {
      _items = items;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("题库大厅"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        _searchBar(),
        _filterChips(),
        Expanded(
          child: _loading
              ? const Center(child: CatLoader(size: 72))
              : _items.isEmpty
                  ? const Center(
                      child: CatBubble(text: "没有找到符合条件的题，换个筛选试试喵~", mood: CatMood.confused))
                  : ListView.builder(
                      padding: const EdgeInsets.all(14),
                      itemCount: _items.length,
                      itemBuilder: (_, i) => ExerciseCard(
                        exercise: _items[i],
                        onTap: () => context.go("/bank/${_items[i].id}"),
                      ),
                    ),
        ),
      ]),
    );
  }

  Widget _searchBar() => Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _search,
              decoration: const InputDecoration(hintText: "搜索题目 / 知识点…", prefixIcon: Icon(Icons.search_rounded), contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8)),
              onSubmitted: (_) => _reload(),
            ),
          ),
          const SizedBox(width: 8),
          CppCatMascot(mood: CatMood.thinking, size: 36, glow: false),
        ]),
      );

  Widget _filterChips() => SizedBox(
        height: 40,
        child: ListView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          children: [
            _chip<Subject>("学科", _subject, Subject.values, (v) => v.label, (v) => _subject = v),
            const SizedBox(width: 8),
            _chip<ExerciseType>("题型", _type, ExerciseType.values, (v) => v.label, (v) => _type = v),
            const SizedBox(width: 8),
            _chip<Difficulty>("难度", _difficulty, Difficulty.values, (v) => v.label, (v) => _difficulty = v),
            const SizedBox(width: 8),
            _chip<QuestionSource>("来源", _source, QuestionSource.values, (v) => v.label, (v) => _source = v),
            const SizedBox(width: 8),
            _chip<QuestionStatus>("状态", _status, QuestionStatus.values, (v) => v.label, (v) => _status = v),
          ],
        ),
      );

  Widget _chip<T>(String label, T? current, List<T> values, String Function(T) text, void Function(T?) set) {
    return PopupMenuButton<T?>(
      initialValue: current,
      onSelected: (v) {
        set(v);
        _reload();
      },
      itemBuilder: (_) => [
        PopupMenuItem<T?>(value: null, child: Text("全部$label")),
        for (final v in values) PopupMenuItem<T?>(value: v, child: Text(text(v))),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: current != null ? AppColors.ice : Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(99),
          border: Border.all(color: AppColors.ice),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(_chipLabel(current, label, values, text),
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: current != null ? AppColors.blue : const Color(0xFF64748B))),
          const Icon(Icons.arrow_drop_down_rounded, size: 16, color: Color(0xFF64748B)),
        ]),
      ),
    );
  }

  String _chipLabel<T>(T? current, String label, List<T> values, String Function(T) text) {
    if (current == null) return label;
    for (final v in values) {
      if (v == current) return text(v);
    }
    return label;
  }
}
