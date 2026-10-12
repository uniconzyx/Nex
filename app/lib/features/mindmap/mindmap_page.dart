import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 学习地图 / 思维导图：节点蓝白配色，四态着色（PRD §14.3）
/// 已掌握=主蓝 / 学习中=浅蓝 / 未学习=灰 / 薄弱=橙；点击节点有 CppCat 提示。
class MindmapPage extends ConsumerStatefulWidget {
  const MindmapPage({super.key});

  @override
  ConsumerState<MindmapPage> createState() => _MindmapPageState();
}

class _MindmapPageState extends ConsumerState<MindmapPage> {
  List<_Node> _nodes = const [];
  int? _tapped;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ref.read(apiClientProvider).get("/mindmap?chapter_id=1");
      final items = (data is Map ? data["nodes"] : data) as List? ?? [];
      setState(() => _nodes = items.map((e) => _Node.fromJson(e as Map<String, dynamic>)).toList());
    } catch (_) {
      // 占位：第 1 章知识树
      _nodes = [
        _Node(1, 0, "C++ 基础语法", 180, 70, "mastered"),
        _Node(2, 1, "变量与类型", 90, 170, "mastered"),
        _Node(3, 1, "引用", 180, 170, "learning"),
        _Node(4, 1, "const", 270, 170, "todo"),
        _Node(5, 2, "整型/浮点", 40, 270, "learning"),
        _Node(6, 3, "左值/右值", 150, 280, "weak"),
        _Node(7, 4, "constexpr", 270, 280, "todo"),
      ];
    }
  }

  Color _stateColor(String s) => switch (s) {
        "mastered" => AppColors.nodeMastered,
        "learning" => AppColors.nodeLearning,
        "weak" => AppColors.nodeWeak,
        _ => AppColors.nodeTodo,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("学习地图"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Stack(children: [
        InteractiveViewer(
          child: SizedBox(
            width: 360,
            height: 360,
            child: CustomPaint(
              painter: _MindmapPainter(_nodes, _stateColor, _tapped),
              child: GestureDetector(
                onTapUp: (d) {
                  for (final n in _nodes) {
                    if ((Offset(n.x, n.y) - d.localPosition).distance < 26) {
                      setState(() => _tapped = n.id);
                      break;
                    }
                  }
                },
              ),
            ),
          ),
        ),
        if (_tapped != null)
          Positioned(
            left: 16,
            right: 16,
            bottom: 20,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  CppCatMascot(
                    mood: _nodes.firstWhere((n) => n.id == _tapped).state == "weak"
                        ? CatMood.confused
                        : CatMood.happy,
                    size: 44,
                    glow: false,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "「${_nodes.firstWhere((n) => n.id == _tapped).label}」：${_hint(_nodes.firstWhere((n) => n.id == _tapped).state)}",
                      style: const TextStyle(fontSize: 12.5),
                    ),
                  ),
                ]),
              ),
            ),
          ),
      ]),
    );
  }

  String _hint(String s) => switch (s) {
        "mastered" => "已掌握，去做题巩固一下喵~",
        "learning" => "正在学，点进去继续看讲解。",
        "weak" => "这里有点薄弱，多练几道错题本里的题！",
        _ => "还没开始，先从概念讲起吧。",
      };
}

class _Node {
  _Node(this.id, this.parentId, this.label, this.x, this.y, this.state);
  factory _Node.fromJson(Map<String, dynamic> j) => _Node(
        j["id"] as int, j["parent_id"] as int? ?? 0, j["label"] as String,
        (j["x"] as num).toDouble(), (j["y"] as num).toDouble(), j["state"] as String? ?? "todo",
      );
  final int id, parentId;
  final String label;
  final double x, y;
  final String state;
}

class _MindmapPainter extends CustomPainter {
  _MindmapPainter(this.nodes, this.colorOf, this.tapped);
  final List<_Node> nodes;
  final Color Function(String) colorOf;
  final int? tapped;

  @override
  void paint(Canvas canvas, Size size) {
    final byId = {for (final n in nodes) n.id: n};
    final line = Paint()..color = AppColors.ice..strokeWidth = 2;
    for (final n in nodes) {
      if (n.parentId != 0 && byId.containsKey(n.parentId)) {
        final p = byId[n.parentId]!;
        canvas.drawLine(Offset(p.x, p.y), Offset(n.x, n.y), line);
      }
    }
    for (final n in nodes) {
      final c = colorOf(n.state);
      canvas.drawCircle(Offset(n.x, n.y), 24, Paint()..color = c);
      if (tapped == n.id) {
        canvas.drawCircle(Offset(n.x, n.y), 28, Paint()..color = c.withValues(alpha: 0.4));
      }
      final tp = TextPainter(
        text: TextSpan(text: n.label, style: const TextStyle(fontSize: 11, color: Colors.white, fontWeight: FontWeight.w600)),
        textAlign: TextAlign.center,
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 46);
      tp.paint(canvas, Offset(n.x - tp.width / 2, n.y - tp.height / 2));
    }
  }

  @override
  bool shouldRepaint(_MindmapPainter old) => old.tapped != tapped;
}
