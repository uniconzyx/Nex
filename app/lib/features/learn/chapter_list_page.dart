import "package:flutter/material.dart";

import "../../core/models/content_manifest.dart";

/// 课程大纲页（阶段 7）。
/// 展示 content/cpp/_manifest.json 的 20 章 + C 语言 7 单元，标注完成度与真题/资源映射。
class ChapterListPage extends StatelessWidget {
  const ChapterListPage({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final done = ContentManifest.chapters.where((c) => c.done).length;

    final groups = <String, List<ChapterSummary>>{};
    for (final c in ContentManifest.chapters) {
      (groups[c.group] ??= []).add(c);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("C/C++ 20 章课程体系"),
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 24),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: scheme.primaryContainer,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text(
              "阶段 7 · 内容生产进度 $done/${ContentManifest.chapters.length} 章已完成"
              "（已通过 7 类内容校验）。其余章节为大批量内容生产批次，按同格式续填。",
              style: TextStyle(fontSize: 12.5, color: scheme.onPrimaryContainer, height: 1.6),
            ),
          ),
          const SizedBox(height: 12),
          for (final entry in groups.entries) ...[
            _sectionTitle("$entry.key · ${ContentManifest.groupLabels[entry.key] ?? entry.key}"),
            for (final c in entry.value) _chapterCard(c, false),
          ],
          const SizedBox(height: 12),
          _sectionTitle("clang · C 语言独立模块（7 单元）"),
          for (final c in ContentManifest.clangUnits) _chapterCard(c, true),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) => Padding(
        padding: const EdgeInsets.fromLTRB(2, 12, 2, 6),
        child: Text(text, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );

  Widget _chapterCard(ChapterSummary c, bool isClang) {
    final chips = <Widget>[
      for (final x in c.leetcode) _chip("LC $x", const Color(0xFFEFF6FF), const Color(0xFF3B82F6)),
      for (final x in c.nowcoder) _chip(x, const Color(0xFFF8FAFC), const Color(0xFF64748B)),
      for (final x in c.books) _chip("📖 $x", const Color(0xFFFFFBEB), const Color(0xFF92400E)),
    ];
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  isClang ? "C" : c.order.toString().padLeft(2, "0"),
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(c.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                ),
                c.done
                    ? _chip("已完成", const Color(0xFF3B82F6), const Color(0xFFFFFFFF))
                    : _chip("规划中", const Color(0xFFDBEAFE), const Color(0xFF3B82F6)),
              ],
            ),
            if (chips.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(spacing: 5, runSpacing: 5, children: chips),
              ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(7)),
        child: Text(text, style: TextStyle(fontSize: 9.5, color: fg)),
      );
}
