import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "core/router/app_router.dart";
import "core/theme/app_theme.dart";
import "core/settings/settings.dart";

void main() => runApp(const ProviderScope(child: NexApp()));

class NexApp extends ConsumerWidget {
  const NexApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(settingsProvider);
    return MaterialApp.router(
      title: "Nex",
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: s.themeMode,
      routerConfig: appRouter,
      builder: (ctx, child) => MediaQuery(
        data: MediaQuery.of(ctx).copyWith(textScaleFactor: s.fontScale),
        child: child!,
      ),
    );
  }
}
