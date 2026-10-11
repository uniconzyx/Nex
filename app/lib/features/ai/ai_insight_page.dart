import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 学习诊断页（Phase 6）：调 /ai/insight，聚合错题本+进度，排名弱章节并给建议。
class AiInsightPage extends ConsumerStatefulWidget {
  const AiInsightPage({super.key});

  @override
  ConsumerState<AiInsightPage> createState() => _AiInsightPageState();
}

class _AiInsightPageState extends ConsumerState<AiInsightPage> {
  bool _loading = false;
  Map<String, dynamic>? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await ref.read(apiClientProvider).get("/ai/insight");
      setState(() => _data = data as Map<String, dynamic>?);
    } catch (e) {
      setState(() => _error = "诊断失败，请登录后重试：$e");
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text("📊 学习诊断"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _loading
          ? const Center(child: CatLoader(size: 48))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CppCatMascot(mood: CatMood.comfort, size: 56),
                        const SizedBox(height: 12),
                        Text(_error!, textAlign: TextAlign.center),
                      ],
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(14),
                  children: [
                    const CppCatMascot(mood: CatMood.happy, size: 56),
                    const SizedBox(height: 8),
                    Text("累计错误 ${_data?["total_wrong"] ?? 0} 次",
                        style: const TextStyle(fontSize: 13, color: Colors.grey)),
                    const SizedBox(height: 16),
                    const Text("薄弱章节", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 8),
                    ..._weakChapters(),
                    const SizedBox(height: 16),
                    const Text("薄弱题型", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 8),
                    ..._weakTypes(scheme),
                    const SizedBox(height: 16),
                    const Text("CppCat 的建议", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 8),
                    ..._recommendations(scheme),
                  ],
                ),
    );
  }

  List<Widget> _weakChapters() {
    final list = (_data?["weak_chapters"] as List? ?? []);
    if (list.isEmpty) return [const Text("暂无数据，继续保持~", style: TextStyle(color: Colors.grey))];
    return [
      for (final c in list)
        ListTile(
          leading: const Icon(Icons.book_outlined, color: AppColors.blue),
          title: Text("第 ${c["chapter_id"]} 章"),
          subtitle: Text("错误 ${c["wrong"]} · 正确 ${c["right"]}"),
          trailing: Text("权重 ${c["score"]}", style: const TextStyle(color: Colors.redAccent, fontSize: 12)),
          contentPadding: EdgeInsets.zero,
        ),
    ];
  }

  List<Widget> _weakTypes(ColorScheme scheme) {
    final list = (_data?["weak_types"] as List? ?? []);
    if (list.isEmpty) return [const Text("暂无数据", style: TextStyle(color: Colors.grey))];
    return [
      for (final t in list)
        Chip(
          label: Text("${t["label"]} · ${t["wrong"]} 次"),
          backgroundColor: scheme.surfaceContainerHighest,
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
    ];
  }

  List<Widget> _recommendations(ColorScheme scheme) {
    final list = (_data?["recommendations"] as List? ?? []);
    return [
      for (final r in list)
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.blue.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("🐱 ", style: TextStyle(fontSize: 13)),
              Expanded(child: Text(r.toString(), style: const TextStyle(fontSize: 13, height: 1.5))),
            ],
          ),
        ),
    ];
  }
}
