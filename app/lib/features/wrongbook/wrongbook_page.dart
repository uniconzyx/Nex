import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 错题本：间隔复习（next_review_at），点「重做」进编辑器（PRD §验收 4）
class WrongbookPage extends ConsumerStatefulWidget {
  const WrongbookPage({super.key});

  @override
  ConsumerState<WrongbookPage> createState() => _WrongbookPageState();
}

class _WrongbookPageState extends ConsumerState<WrongbookPage> {
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ref.read(apiClientProvider).get("/wrong-questions");
      final list = (data is Map ? data["items"] : data) as List? ?? [];
      setState(() => _items = list.map((e) => Map<String, dynamic>.from(e as Map)).toList());
    } catch (_) {
      _items = [
        {"id": 1, "title": "返回局部变量引用", "wrong_count": 3, "next_review_at": "今天", "question_type": "exercise"},
        {"id": 2, "title": "忘记 delete 导致内存泄漏", "wrong_count": 2, "next_review_at": "明天", "question_type": "exercise"},
      ];
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("错题本"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(children: [
                      CppCatMascot(mood: CatMood.comfort, size: 48, glow: false),
                      const SizedBox(width: 10),
                      const Expanded(child: Text("这题是「返回局部变量引用」的老坑，重做前先想想：函数结束后栈帧去哪了？", style: TextStyle(fontSize: 12.5))),
                    ]),
                  ),
                ),
              ),
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _items.length,
                  itemBuilder: (_, i) {
                    final w = _items[i];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(children: [
                          const Icon(Icons.error_outline_rounded, color: AppColors.red),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(w["title"]?.toString() ?? "", style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
                              Text("错 ${w["wrong_count"]} 次 · ${w["next_review_at"]}复习",
                                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                            ]),
                          ),
                          FilledButton.tonal(onPressed: () => context.go("/editor?exercise=${w["id"]}"), child: const Text("重做")),
                        ]),
                      ),
                    );
                  },
                ),
              ),
            ]),
    );
  }
}
