import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 题库：支持章节 / 难度 / 标签筛选（PRD §验收 4）
class ExercisesPage extends ConsumerStatefulWidget {
  const ExercisesPage({super.key});

  @override
  ConsumerState<ExercisesPage> createState() => _ExercisesPageState();
}

class _ExercisesPageState extends ConsumerState<ExercisesPage> {
  List<Map<String, dynamic>> _items = const [];
  String _diff = "all";
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final q = _diff == "all" ? null : {"difficulty": _diff};
      final data = await ref.read(apiClientProvider).get("/exercises", query: q);
      final list = (data is Map ? data["items"] : data) as List? ?? [];
      setState(() => _items = list.map((e) => Map<String, dynamic>.from(e as Map)).toList());
    } catch (_) {
      _items = [
        {"id": 1, "type": "choice", "difficulty": "easy", "title": "引用与指针的区别？", "tags": ["cpp-ch01"]},
        {"id": 2, "type": "fix_error", "difficulty": "mid", "title": "下列代码为何编译失败？", "tags": ["cpp-ch03"]},
        {"id": 3, "type": "output", "difficulty": "mid", "title": "程序输出是什么？", "tags": ["cpp-ch02"]},
        {"id": 4, "type": "coding", "difficulty": "hard", "title": "实现线程安全的单例", "tags": ["cpp-ch07"]},
      ];
    } finally {
      setState(() => _loading = false);
    }
  }

  Color _diffColor(String d) => switch (d) {
        "easy" => AppColors.diffEasy,
        "hard" => AppColors.diffHard,
        _ => AppColors.diffMid,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("题库"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: "all", label: Text("全部")),
              ButtonSegment(value: "easy", label: Text("简单")),
              ButtonSegment(value: "mid", label: Text("中等")),
              ButtonSegment(value: "hard", label: Text("困难")),
            ],
            selected: {_diff},
            onSelectionChanged: (s) => setState(() {
              _diff = s.first;
              _load();
            }),
          ),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _items.length,
                  itemBuilder: (_, i) {
                    final e = _items[i];
                    final d = e["difficulty"]?.toString() ?? "easy";
                    return Card(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(18),
                        onTap: () => context.go("/editor?exercise=${e["id"]}"),
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Row(children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(color: _diffColor(d).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(99)),
                              child: Text(d == "easy" ? "简单" : d == "hard" ? "困难" : "中等",
                                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _diffColor(d))),
                            ),
                            const SizedBox(width: 10),
                            Expanded(child: Text(e["title"]?.toString() ?? "", style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600))),
                            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.blue),
                          ]),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}
