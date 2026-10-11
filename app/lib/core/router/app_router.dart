import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../features/ai/ai_page.dart";
import "../../features/ai/ai_quiz_page.dart";
import "../../features/ai/ai_insight_page.dart";
import "../../features/learn/chapter_list_page.dart";
import "../../features/auth/login_page.dart";
import "../../features/bank/bank_detail_page.dart";
import "../../features/bank/bank_page.dart";
import "../../features/bank/error_book_page.dart";
import "../../features/bank/exam_page.dart";
import "../../features/course/course_page.dart";
import "../../features/editor/editor_page.dart";
import "../../features/home/home_page.dart";
import "../../features/mindmap/mindmap_page.dart";
import "../../features/profile/profile_page.dart";
import "../../features/projects/projects_page.dart";
import "../../features/resources/resources_page.dart";
import "../../features/wrongbook/wrongbook_page.dart";

/// 路由表（PRD §6 页面清单移动端子集）。
/// 底部 5 Tab：首页 / 导图 / 题库 / AI / 我的；其余页面 push 进入。
/// 游客可浏览（后端 is_free 章节放行），登录页从「我的」进入，不强制拦截。
final appRouter = GoRouter(
  initialLocation: "/splash",
  routes: [
    GoRoute(path: "/splash", builder: (_, __) => const SplashPage()),
    ShellRoute(
      builder: (context, state, child) => _TabScaffold(child: child),
      routes: [
        GoRoute(path: "/home", builder: (_, __) => const HomePage()),
        GoRoute(path: "/map", builder: (_, __) => const MindmapPage()),
        GoRoute(path: "/exercises", builder: (_, __) => const BankPage()),
        GoRoute(path: "/ai", builder: (_, __) => const AiPage()),
        GoRoute(path: "/me", builder: (_, __) => const ProfilePage()),
      ],
    ),
    GoRoute(path: "/login", builder: (_, __) => const LoginPage()),
    GoRoute(
      path: "/chapter/:id",
      builder: (_, s) => CoursePage(chapterId: int.parse(s.pathParameters["id"]!)),
    ),
    GoRoute(
      path: "/editor",
      builder: (_, s) => EditorPage(
        exerciseId: s.uri.queryParameters["exercise"] == null
            ? null
            : int.parse(s.uri.queryParameters["exercise"]!),
        initialCode: s.uri.queryParameters["code"],
        initialStd: s.uri.queryParameters["std"] ?? "cpp17",
      ),
    ),
    GoRoute(path: "/wrongbook", builder: (_, __) => const WrongbookPage()),
    GoRoute(path: "/projects", builder: (_, __) => const ProjectsPage()),
    GoRoute(path: "/resources", builder: (_, __) => const ResourcesPage()),

    // ===== 阶段7：课程大纲（内容生产进度 + 真题/资源映射） =====
    GoRoute(path: "/learn", builder: (_, __) => const ChapterListPage()),

    // ===== 多学科题库模块（阶段5） =====
    GoRoute(path: "/bank", builder: (_, __) => const BankPage()),
    GoRoute(path: "/bank/:id", builder: (_, s) => BankDetailPage(id: s.pathParameters["id"]!)),
    GoRoute(path: "/exam", builder: (_, __) => const ExamPage()),
    GoRoute(path: "/errorbook", builder: (_, __) => const ErrorBookPage()),

    // ===== 阶段6：AI 深化（CppCat 伴侣 / 自适应测验 / 学习诊断） =====
    GoRoute(path: "/ai/quiz", builder: (_, __) => const AiQuizPage()),
    GoRoute(path: "/ai/insight", builder: (_, __) => const AiInsightPage()),
  ],
);

class _TabScaffold extends StatelessWidget {
  const _TabScaffold({required this.child});
  final Widget child;

  static const _tabs = [
    ("/home", Icons.home_rounded, "首页"),
    ("/map", Icons.account_tree_rounded, "导图"),
    ("/exercises", Icons.quiz_rounded, "题库"),
    ("/ai", Icons.smart_toy_rounded, "AI"),
    ("/me", Icons.person_rounded, "我的"),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final index = _tabs.indexWhere((t) => location.startsWith(t.$1)).clamp(0, _tabs.length - 1);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: scheme.surface.withValues(alpha: 0.85), // 毛玻璃底（PRD §14.1）
          border: Border(top: BorderSide(color: scheme.outline)),
        ),
        child: SafeArea(
          child: NavigationBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            selectedIndex: index,
            labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
            onDestinationSelected: (i) => context.go(_tabs[i].$1),
            destinations: [
              for (final t in _tabs)
                NavigationDestination(icon: Icon(t.$2), label: t.$3),
            ],
          ),
        ),
      ),
    );
  }
}
