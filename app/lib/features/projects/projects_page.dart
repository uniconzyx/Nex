import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 项目实战：基础 / 系统 / 深度学习三类（PRD §四 项目实战）
class ProjectsPage extends ConsumerStatefulWidget {
  const ProjectsPage({super.key});

  @override
  ConsumerState<ProjectsPage> createState() => _ProjectsPageState();
}

class _ProjectsPageState extends ConsumerState<ProjectsPage> {
  List<Map<String, dynamic>> _items = const [];
  String _cat = "basic";
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ref.read(apiClientProvider).get("/projects?category=$_cat");
      final list = (data is Map ? data["items"] : data) as List? ?? [];
      setState(() => _items = list.map((e) => Map<String, dynamic>.from(e as Map)).toList());
    } catch (_) {
      _items = {
        "basic": [
          {"id": 1, "title": "学生管理系统", "category": "basic", "summary": "链表 + 文件持久化", "difficulty": "mid", "done_tasks": 3, "total_tasks": 5},
          {"id": 2, "title": "迷你 STL vector", "category": "basic", "summary": "手写动态数组", "difficulty": "hard", "done_tasks": 1, "total_tasks": 6},
        ],
        "system": [
          {"id": 3, "title": "线程池", "category": "system", "summary": "生产者消费者模型", "difficulty": "hard", "done_tasks": 2, "total_tasks": 5},
          {"id": 4, "title": "HTTP 服务器", "category": "system", "summary": "epoll + 协程", "difficulty": "hard", "done_tasks": 0, "total_tasks": 7},
        ],
        "dl": [
          {"id": 5, "title": "MNIST C++ 推理", "category": "dl", "summary": "ONNX Runtime", "difficulty": "hard", "done_tasks": 0, "total_tasks": 6},
          {"id": 6, "title": "YOLO 部署", "category": "dl", "summary": "TensorRT", "difficulty": "hard", "done_tasks": 0, "total_tasks": 8},
        ],
      }[_cat]!;
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("项目实战"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: "basic", label: Text("基础")),
              ButtonSegment(value: "system", label: Text("系统")),
              ButtonSegment(value: "dl", label: Text("深度学习")),
            ],
            selected: {_cat},
            onSelectionChanged: (s) => setState(() {
              _cat = s.first;
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
                    final p = _items[i];
                    final done = p["done_tasks"] as int? ?? 0;
                    final total = p["total_tasks"] as int? ?? 1;
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            CppCatMascot(mood: CatMood.cheer, size: 36, glow: false),
                            const SizedBox(width: 8),
                            Expanded(child: Text(p["title"]?.toString() ?? "", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700))),
                            Chip(label: Text(p["difficulty"]?.toString() ?? "mid"), labelPadding: EdgeInsets.zero),
                          ]),
                          const SizedBox(height: 6),
                          Text(p["summary"]?.toString() ?? "", style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                          const SizedBox(height: 10),
                          LinearProgressIndicator(value: total == 0 ? 0 : done / total, backgroundColor: AppColors.ice, color: AppColors.blue, minHeight: 5),
                          const SizedBox(height: 4),
                          Text("$done / $total 任务", style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
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
