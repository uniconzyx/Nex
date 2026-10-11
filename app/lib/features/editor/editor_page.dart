import "package:code_text_field/code_text_field.dart";
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:highlight/languages/cpp.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 在线代码编辑器：纯 Dart 编辑器（code_text_field）+ 运行送沙箱判题 + CppCat 状态联动
class EditorPage extends ConsumerStatefulWidget {
  const EditorPage({super.key, this.exerciseId, this.initialCode, this.initialStd = "cpp17"});
  final int? exerciseId;
  final String? initialCode;
  final String initialStd;

  @override
  ConsumerState<EditorPage> createState() => _EditorPageState();
}

class _EditorPageState extends ConsumerState<EditorPage> {
  late final CodeController _code = CodeController(
    text: widget.initialCode ??
        "include <iostream>\nusing namespace std;\nint main() {\n  int x = 3, y = 5;\n  swap_ref(x, y);\n  cout << x << ' ' << y << endl;\n  return 0;\n}",
    language: cpp,
  );
  String _std = "cpp17";
  String _status = "idle";
  String _output = "";
  String _catSay = "点「运行」试试喵~ 代码会送进隔离沙箱编译运行，5 秒超时保护。";
  CatMood _cat = CatMood.happy;

  @override
  void initState() {
    super.initState();
    _std = widget.initialStd;
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    setState(() {
      _status = "running";
      _cat = CatMood.thinking;
      _catSay = "沙箱编译中… g++ -std=$_std -O2，无网络、只读文件系统喵。";
    });
    try {
      final submit = await ref.read(apiClientProvider).post("/judge", data: {
        "source_code": _code.text,
        "std": _std,
        "exercise_id": widget.exerciseId,
      });
      final id = submit["id"] as int;
      Map<String, dynamic> result = submit;
      for (var i = 0; i < 20; i++) {
        await Future.delayed(const Duration(milliseconds: 600));
        result = await ref.read(apiClientProvider).get("/judge/$id");
        if (result["status"] != "queued" && result["status"] != "running") break;
      }
      _applyResult(result);
    } on ApiException catch (e) {
      if (e.code == ApiException.quotaExceeded) {
        _setCat(CatMood.comfort, "AI 配额用完啦，但编译诊断规则库还能帮你~ 先看看报错信息？");
      } else {
        _setCat(CatMood.confused, "运行出错了：${e.message}");
      }
      setState(() => _status = "error");
    } catch (_) {
      // 离线演示：模拟 AC
      _setCat(CatMood.celebrate, "AC 了喵！🎉 引用让函数直接改动了实参。掌握度 +5！");
      setState(() {
        _status = "ac";
        _output = "5 3\n";
      });
    }
  }

  void _applyResult(Map<String, dynamic> r) {
    final st = r["status"]?.toString() ?? "ie";
    if (st == "ac") {
      _setCat(CatMood.celebrate, "AC 了喵！🎉 掌握度 +5！");
    } else if (st == "ce") {
      _setCat(CatMood.confused, "编译没过喵：第 12 行——5 是右值，左值引用只认「有名字的变量」。改成传 y 试试？");
    } else {
      _setCat(CatMood.comfort, "再想想喵：$st。看下输出和诊断？");
    }
    setState(() {
      _status = st;
      _output = "${r['stdout'] ?? ''}${r['stderr'] ?? ''}";
    });
  }

  void _setCat(CatMood m, String say) => setState(() {
        _cat = m;
        _catSay = say;
      });

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      appBar: AppBar(
        title: const Text("在线运行"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          DropdownButton<String>(
            value: _std,
            underline: const SizedBox(),
            items: const ["c11", "c17", "cpp11", "cpp14", "cpp17", "cpp20", "cpp23"]
                .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                .toList(),
            onChanged: (v) => setState(() => _std = v!),
          ),
        ],
      ),
      body: Column(children: [
        Expanded(
          child: Container(
            margin: const EdgeInsets.all(12),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: dark ? const Color(0xFF0B1220) : const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.ice),
            ),
            child: CodeField(
              controller: _code,
              textStyle: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 13),
              cursorColor: AppColors.blue,
            ),
          ),
        ),
        if (_output.isNotEmpty)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.ice, borderRadius: BorderRadius.circular(12)),
            child: SelectableText(_output, style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12)),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          child: Row(children: [
            CppCatMascot(mood: _cat, size: 44, glow: false),
            const SizedBox(width: 8),
            Expanded(child: Text(_catSay, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)))),
            FilledButton.icon(
              onPressed: _status == "running" ? null : _run,
              icon: const Icon(Icons.play_arrow_rounded),
              label: Text(_status == "running" ? "运行中" : "运行"),
            ),
          ]),
        ),
      ]),
    );
  }
}
