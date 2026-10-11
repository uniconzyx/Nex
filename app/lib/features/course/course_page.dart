import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 课程详情：卡片式布局 + 代码块高亮 + CppCat 角落提示（PRD §14.3）
class CoursePage extends ConsumerStatefulWidget {
  const CoursePage({super.key, required this.chapterId});
  final int chapterId;

  @override
  ConsumerState<CoursePage> createState() => _CoursePageState();
}

class _CoursePageState extends ConsumerState<CoursePage> {
  String _title = "加载中…";
  List<Map<String, dynamic>> _lessons = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final ch = await ref.read(apiClientProvider).get("/chapters/${widget.chapterId}");
      final ls = await ref.read(apiClientProvider).get("/chapters/${widget.chapterId}/lessons");
      setState(() {
        _title = ch["title"]?.toString() ?? "第 ${widget.chapterId} 章";
        _lessons = (ls as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
      });
    } catch (_) {
      _title = "第 ${widget.chapterId} 章 · 内存与对象模型";
      _lessons = [
        {"id": 1, "type": "concept", "title": "std::move 与右值引用", "content_md": "std::move 只是把左值**转换**为右值引用，本身不移动任何东西。", "code": "int x=5; int&& r=std::move(x);"},
        {"id": 2, "type": "pitfall", "title": "移动后不要再使用原对象", "content_md": "被 move 后的对象处于「有效但未指定」状态，读它结果是未定义的。"},
        {"id": 3, "type": "example", "title": "引用交换两个数", "content_md": "用引用直接改动实参。", "code": "void swap(int& a,int& b){int t=a;a=b;b=t;}"},
      ];
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_title), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Stack(children: [
        ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 90),
          children: [
            if (_loading) const Center(child: CircularProgressIndicator()),
            const CatBubble(text: "注意喵：std::move 本身不移动任何东西，它只是把左值「转换」成右值引用。移动之后别再使用原对象！", mood: CatMood.thinking),
            const SizedBox(height: 12),
            for (final l in _lessons) _LessonCard(l),
          ],
        ),
        Positioned(
          right: 14, bottom: 18,
          child: CppCatMascot(mood: CatMood.happy, size: 56),
        ),
      ]),
    );
  }
}

class _LessonCard extends StatelessWidget {
  const _LessonCard(this.l);
  final Map<String, dynamic> l;
  @override
  Widget build(BuildContext context) {
    final type = l["type"]?.toString() ?? "concept";
    final label = switch (type) {
      "pitfall" => "避坑",
      "example" => "示例",
      _ => "概念",
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Chip(label: Text(label), labelPadding: EdgeInsets.zero),
            const SizedBox(width: 8),
            Expanded(child: Text(l["title"]?.toString() ?? "", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 8),
          Text(l["content_md"]?.toString() ?? "", style: const TextStyle(fontSize: 13, height: 1.6)),
          if (l["code"] != null) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppColors.ice, borderRadius: BorderRadius.circular(12)),
              child: SelectableText(l["code"].toString(), style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12, color: Color(0xFF1E3A8A))),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => context.go("/editor?code=${Uri.encodeComponent(l["code"].toString())}&std=cpp17"),
                icon: const Icon(Icons.play_arrow_rounded, size: 16),
                label: const Text("运行这段代码"),
              ),
            ),
          ],
        ]),
      ),
    );
  }
}
