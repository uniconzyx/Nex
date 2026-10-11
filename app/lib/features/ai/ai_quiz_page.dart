import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 自适应测验页（Phase 6）：调 /ai/generate-quiz，基于错题本弱章节/弱题型抽真题依据题目。
class AiQuizPage extends ConsumerStatefulWidget {
  const AiQuizPage({super.key});

  @override
  ConsumerState<AiQuizPage> createState() => _AiQuizPageState();
}

class _AiQuizPageState extends ConsumerState<AiQuizPage> {
  bool _loading = false;
  List<dynamic> _questions = [];
  bool _basedOnWeak = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _generate();
  }

  Future<void> _generate() async {
    setState(() => _loading = true);
    try {
      final data = await ref.read(apiClientProvider).post("/ai/generate-quiz", data: {"n": 5});
      setState(() {
        _questions = (data["questions"] as List? ?? []);
        _basedOnWeak = data["based_on_weak"] as bool? ?? false;
        _error = null;
      });
    } catch (e) {
      setState(() => _error = "生成失败，请登录后重试：$e");
    } finally {
      setState(() => _loading = false);
    }
  }

  Color _diffColor(String d) => switch (d) {
        "easy" => Colors.green,
        "hard" => Colors.redAccent,
        _ => AppColors.blue,
      };

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text("📝 自适应测验"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loading ? null : _generate),
        ],
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
              : ListView.separated(
                  padding: const EdgeInsets.all(14),
                  itemCount: _questions.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, i) {
                    final q = _questions[i] as Map<String, dynamic>;
                    return Card(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Chip(
                                  label: Text(q["difficulty"]?.toString() ?? "mid"),
                                  backgroundColor: _diffColor(q["difficulty"]?.toString() ?? "mid").withValues(alpha: 0.15),
                                  labelStyle: TextStyle(
                                    color: _diffColor(q["difficulty"]?.toString() ?? "mid"),
                                    fontSize: 11,
                                  ),
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                const SizedBox(width: 8),
                                Chip(
                                  label: Text(q["type"]?.toString() ?? "choice"),
                                  backgroundColor: scheme.surfaceContainerHighest,
                                  labelStyle: const TextStyle(fontSize: 11),
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                const Spacer(),
                                Text("第 ${q["chapter_id"] ?? "?"} 章",
                                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(q["title"]?.toString() ?? "题目",
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                            const SizedBox(height: 6),
                            Text((q["prompt"]?.toString() ?? "").replaceAll(RegExp(r"\s+"), " "),
                                maxLines: 4, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: AppColors.blue.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.verified, size: 14, color: AppColors.blue),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text("真题依据：${q["source_ref"] ?? "Nex 自编"}",
                                        style: const TextStyle(fontSize: 11, color: AppColors.blue)),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
      bottomNavigationBar: _questions.isEmpty
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: FilledButton.icon(
                  onPressed: () => context.pop(),
                  icon: const Icon(Icons.chat_bubble_outline),
                  label: Text(_basedOnWeak ? "已按你的薄弱点生成 · 回到 CppCat 答疑" : "回到 CppCat 答疑"),
                ),
              ),
            ),
    );
  }
}
