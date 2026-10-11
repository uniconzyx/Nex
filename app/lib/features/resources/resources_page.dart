import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:url_launcher/url_launcher.dart";

import "../../core/api/api_client.dart";
import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 资源中心：GitHub / LeetCode / 牛客 / 文档，按来源分组（PRD §三 资源整合）
/// 仅存储元数据与链接（合规红线：不搬运题面正文）。
class ResourcesPage extends ConsumerStatefulWidget {
  const ResourcesPage({super.key});

  @override
  ConsumerState<ResourcesPage> createState() => _ResourcesPageState();
}

class _ResourcesPageState extends ConsumerState<ResourcesPage> {
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ref.read(apiClientProvider).get("/resources");
      final list = (data is Map ? data["items"] : data) as List? ?? [];
      setState(() => _items = list.map((e) => Map<String, dynamic>.from(e as Map)).toList());
    } catch (_) {
      // 离线兜底：使用学科注册表里的真实 GitHub 资源（全栈路线强制来自 GitHub）
      final gh = Subject.fullstack.githubRepos
          .map((r) => {"id": r, "source": "github", "type": "repo", "title": r, "url": "https://github.com/$r"})
          .toList();
      _items = [
        ...gh,
        {"id": "lc", "source": "leetcode", "type": "problem", "title": "两数之和（入门）", "url": "https://leetcode.cn/"},
        {"id": "nc", "source": "nowcoder", "type": "article", "title": "面试 TOP101 映射", "url": "https://www.nowcoder.com/"},
        {"id": "doc", "source": "doc", "type": "doc_link", "title": "cppreference · move", "url": "https://en.cppreference.com/"},
      ];
    } finally {
      setState(() => _loading = false);
    }
  }

  IconData _icon(String s) => switch (s) {
        "github" => Icons.code_rounded,
        "leetcode" => Icons.quiz_rounded,
        "nowcoder" => Icons.work_rounded,
        _ => Icons.menu_book_rounded,
      };

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final r in _items) {
      (groups.putIfAbsent(r["source"]?.toString() ?? "doc", () => [])).add(r);
    }
    return Scaffold(
      appBar: AppBar(title: const Text("资源中心"), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const CatBubble(text: "所有外部题只存元数据与链接，不搬运题面正文，合规又省心喵~", mood: CatMood.happy),
                const SizedBox(height: 10),
                for (final g in groups.entries) ...[
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(g.key.toUpperCase(), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.blue)),
                  ),
                  for (final r in g.value)
                    Card(
                      child: ListTile(
                        leading: Icon(_icon(r["source"]?.toString() ?? "doc"), color: AppColors.blue),
                        title: Text(r["title"]?.toString() ?? "", style: const TextStyle(fontSize: 13.5)),
                        subtitle: Text(r["type"]?.toString() ?? "", style: const TextStyle(fontSize: 11)),
                        trailing: const Icon(Icons.open_in_new_rounded, size: 16, color: AppColors.blue),
                        onTap: () async {
                          final url = r["url"]?.toString() ?? "";
                          if (url.isNotEmpty && await canLaunchUrl(Uri.parse(url))) {
                            await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                          }
                        },
                      ),
                    ),
                ],
              ],
            ),
    );
  }
}
