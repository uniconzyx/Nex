import "dart:convert";

import "package:dio/dio.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// AI 对话页（Phase 6 升级）：接后端 /ai/chat SSE 流式逐 token 输出；
/// 模式切换（苏格拉底/诊断/审查/面试/计划/DL）；快捷入口「生成测验」「学习诊断」。
/// 后端未连通时降级为引导式兜底回复，保证骨架始终可用。
class AiPage extends ConsumerStatefulWidget {
  const AiPage({super.key});

  @override
  ConsumerState<AiPage> createState() => _AiPageState();
}

class _AiPageState extends ConsumerState<AiPage> {
  final _msgs = <_Msg>[];
  final _ctrl = TextEditingController();
  String _mode = "socratic";
  bool _busy = false;
  String _sseBuffer = "";

  /// 「思考中」音效的延迟计时器（见 _send 中的说明）。
  Timer? _thinkingTimer;

  static const _modes = [
    ("socratic", "🎓 苏格拉底"),
    ("diagnose", "🩺 编译诊断"),
    ("review", "🔍 代码审查"),
    ("interview", "🎤 模拟面试"),
    ("plan", "🗓️ 学习计划"),
    ("dl_guide", "🚀 DL 部署"),
  ];

  @override
  void initState() {
    super.initState();
    _msgs.add(const _Msg(
      role: "assistant",
      text: "主人好喵~ 我是 CppCat。我不会直接给答案，但会一步步引导你自己想出来。今天卡在哪里了？",
    ));
  }

  @override
  void dispose() {
    _thinkingTimer?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  /// 播放 CppCat 音效（内部已尊重「音效」设置开关；失败静默）。
  void _sound(CppSound sound) => ref.read(soundServiceProvider).play(sound);

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _msgs.add(_Msg(role: "user", text: text));
      _msgs.add(const _Msg(role: "assistant", text: "…", typing: true));
      _busy = true;
    });
    _ctrl.clear();
    _sound(CppSound.send);

    // 延迟 450ms 才播「思考中」：模型快速响应时只响 send→receive 两声，
    // 避免三声叠在一起显得杂乱。
    _thinkingTimer?.cancel();
    _thinkingTimer = Timer(const Duration(milliseconds: 450), () {
      if (mounted && _busy) _sound(CppSound.thinking);
    });

    final history = _msgs
        .where((m) => !m.typing)
        .map((m) => {"role": m.role, "content": m.text})
        .toList();

    try {
      final dio = ref.read(apiClientProvider).dio;
      final rs = await dio.post<ResponseBody>(
        "/ai/chat",
        data: {"mode": _mode, "message": text, "history": history},
        options: Options(
          responseType: ResponseType.stream,
          headers: {"Accept": "text/event-stream"},
        ),
      );
      final body = rs.data;
      if (body == null) throw Exception("empty stream");
      var acc = "";
      await for (final chunk in body.stream.transform(utf8.decoder)) {
        _sseBuffer += chunk;
        // 按 SSE 事件边界（\n\n）切分
        var idx = _sseBuffer.indexOf("\n\n");
        while (idx != -1) {
          final raw = _sseBuffer.substring(0, idx);
          _sseBuffer = _sseBuffer.substring(idx + 2);
          final token = _parseDelta(raw);
          if (token != null) {
            acc += token;
            setState(() {
              _msgs.last = _Msg(role: "assistant", text: acc, typing: true);
            });
          }
          idx = _sseBuffer.indexOf("\n\n");
        }
      }
      setState(() => _msgs.last = _Msg(role: "assistant", text: acc.isEmpty ? "（无回复）" : acc));
      _sound(CppSound.receive);
    } catch (_) {
      // 降级：引导式兜底，避免空屏
      _sound(CppSound.fail);
      setState(() {
        _msgs.last = const _Msg(
          role: "assistant",
          text: "（演示）先想想：函数结束后栈帧去哪了？被 move 的对象还能用吗？连上后端我会一步步引导你。",
        );
      });
    } finally {
      _thinkingTimer?.cancel();
      _thinkingTimer = null;
      _sseBuffer = "";
      setState(() => _busy = false);
    }
  }

  String? _parseDelta(String rawEvent) {
    // rawEvent 形如：event: delta\ndata: {"text": "..."}
    for (final line in rawEvent.split("\n")) {
      if (line.startsWith("data:")) {
        final payload = line.substring(5).trim();
        try {
          final map = jsonDecode(payload) as Map<String, dynamic>;
          return map["text"] as String?;
        } on FormatException {
          return null;
        }
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("🐱 CppCat 辅导"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.quiz_outlined),
            tooltip: "生成自适应测验",
            onPressed: () => context.push("/ai/quiz"),
          ),
          IconButton(
            icon: const Icon(Icons.insights_outlined),
            tooltip: "学习诊断",
            onPressed: () => context.push("/ai/insight"),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: SizedBox(
              height: 40,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _modes.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) {
                  final m = _modes[i];
                  final selected = m.$1 == _mode;
                  return ChoiceChip(
                    label: Text(m.$2),
                    selected: selected,
                    onSelected: (_) {
                      if (!selected) _sound(CppSound.tap);
                      setState(() => _mode = m.$1);
                    },
                    selectedColor: AppColors.blue,
                    labelStyle: TextStyle(
                      color: selected ? Colors.white : Theme.of(context).colorScheme.onSurface,
                      fontSize: 12,
                    ),
                  );
                },
              ),
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(14),
              itemCount: _msgs.length,
              itemBuilder: (_, i) {
                final m = _msgs[i];
                if (m.role == "user") {
                  return Align(
                    alignment: Alignment.centerRight,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.blue,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Text(m.text, style: const TextStyle(fontSize: 13, color: Colors.white)),
                    ),
                  );
                }
                return Align(
                  alignment: Alignment.centerLeft,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      CppCatMascot(mood: m.typing ? CatMood.thinking : CatMood.happy, size: 34, glow: false),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 5),
                          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.surfaceContainerHighest,
                            borderRadius: const BorderRadius.only(
                              topLeft: Radius.circular(4),
                              topRight: Radius.circular(16),
                              bottomRight: Radius.circular(16),
                              bottomLeft: Radius.circular(16),
                            ),
                          ),
                          child: m.typing && m.text == "…"
                              ? const SizedBox(width: 40, height: 16, child: CatLoader(size: 28))
                              : Text(m.text, style: const TextStyle(fontSize: 13, height: 1.6)),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 6, 12, 14),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ctrl,
                    decoration: const InputDecoration(
                      hintText: "向 CppCat 提问…",
                      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(onPressed: _busy ? null : _send, icon: const Icon(Icons.send_rounded)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Msg {
  const _Msg({required this.role, required this.text, this.typing = false});
  final String role;
  final String text;
  final bool typing;
}
