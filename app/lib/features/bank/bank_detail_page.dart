import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../core/api/exercise_api.dart";
import "../../core/models/exercise.dart";
import "../../core/models/subject.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";
import "../../widgets/question_widgets.dart";

/// 答题详情页：按题型差异化渲染（阶段5 §三.2）
class BankDetailPage extends StatefulWidget {
  const BankDetailPage({super.key, required this.id});
  final String id;

  @override
  State<BankDetailPage> createState() => _BankDetailPageState();
}

class _BankDetailPageState extends State<BankDetailPage> {
  Exercise? _q;
  bool _submitted = false;
  bool _correct = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final q = await exerciseRepo.getById(widget.id);
    setState(() => _q = q);
  }

  void _submit(bool correct) {
    setState(() {
      _submitted = true;
      _correct = correct;
    });
  }

  @override
  Widget build(BuildContext context) {
    final q = _q;
    if (q == null) {
      return Scaffold(
        appBar: AppBar(backgroundColor: Colors.transparent, elevation: 0),
        body: const Center(child: CatLoader(size: 72)),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(q.subject.label), centerTitle: true, backgroundColor: Colors.transparent, elevation: 0),
      body: Column(children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _header(q),
              const SizedBox(height: 14),
              Text(q.content.isEmpty ? "" : q.content, style: const TextStyle(fontSize: 14, height: 1.6)),
              if (q.sourceRef.isNotEmpty) ...[
                const SizedBox(height: 12),
                _sourceRefBar(q),
              ],
              if (q.latexFormula.isNotEmpty) ...[
                const SizedBox(height: 10),
                LatexRenderer(latex: q.latexFormula),
              ],
              const SizedBox(height: 14),
              _buildBody(q),
              if (_submitted) ...[
                const SizedBox(height: 16),
                _result(q),
              ],
            ],
          ),
        ),
      ]),
    );
  }

  Widget _header(Exercise q) => Row(children: [
        _tag(q.type.label, AppColors.blue),
        const SizedBox(width: 6),
        _tag(q.difficulty.label, diffColor(q.difficulty)),
        const SizedBox(width: 6),
        _tag(q.source.label, const Color(0xFF94A3B8)),
        const Spacer(),
        IconButton(
          icon: Icon(q.status == QuestionStatus.favorite ? Icons.star_rounded : Icons.star_outline_rounded,
              color: q.status == QuestionStatus.favorite ? AppColors.amber : const Color(0xFF94A3B8)),
          onPressed: () {},
        ),
      ]);

  Widget _tag(String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(99)),
        child: Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  /// 真题依据条：注明本题真实来源；全栈题附 GitHub 资源链接
  Widget _sourceRefBar(Exercise q) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFFEFF6FF),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.ice),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.verified_rounded, size: 14, color: AppColors.blue),
            const SizedBox(width: 6),
            const Text("真题依据", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.blue)),
          ]),
          const SizedBox(height: 6),
          Text(q.sourceRef, style: const TextStyle(fontSize: 12, height: 1.6, color: Color(0xFF1E3A8A))),
          if (q.resourceUrl != null && q.resourceUrl!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(children: [
              Icon(Icons.link_rounded, size: 14, color: AppColors.cyan),
              const SizedBox(width: 6),
              Expanded(
                child: Text(q.resourceUrl!,
                    style: const TextStyle(fontSize: 11.5, color: AppColors.cyan, decoration: TextDecoration.underline)),
              ),
            ]),
          ],
        ]),
      );

  Widget _buildBody(Exercise q) {
    switch (q.type) {
      case ExerciseType.singleChoice:
      case ExerciseType.multiChoice:
        return _objectiveBody(q);
      case ExerciseType.fillBlank:
      case ExerciseType.fixError:
        return _fillBody(q);
      case ExerciseType.programming:
        return _programmingBody(q);
      case ExerciseType.mathSolution:
        return _mathBody(q);
      case ExerciseType.reading:
        return _readingBody(q);
      case ExerciseType.essay:
        return _essayBody(q);
    }
  }

  // 客观题：OptionSelector + 提交
  Widget _objectiveBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      OptionSelector(options: q.options, multi: q.type == ExerciseType.multiChoice),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _submitted ? null : () => _submit(true),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
        child: const Text("提交答案"),
      ),
    ]);
  }

  // 填空/改错：输入框 + 提交
  Widget _fillBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const TextField(
        maxLines: 3,
        decoration: InputDecoration(hintText: "在这里填写你的答案…"),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _submitted ? null : () => _submit(false),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
        child: const Text("提交答案"),
      ),
    ]);
  }

  // 编程题：CodeEditorPanel + TestCasePanel
  Widget _programmingBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _CodeEditorPanel(subject: q.subject),
      const SizedBox(height: 14),
      TestCasePanel(cases: q.testCases),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(
          child: FilledButton(
            onPressed: _submitted ? null : () => _submit(true),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
            child: const Text("运行并提交"),
          ),
        ),
      ]),
    ]);
  }

  // 数学解答题：草稿纸 + 提交
  Widget _mathBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: const Color(0xFFFDF8E9), borderRadius: BorderRadius.circular(12)),
        child: const Text("草稿纸区域（可手写 / 输入推导过程）", style: TextStyle(fontSize: 12, color: Color(0xFF92400E))),
      ),
      const SizedBox(height: 12),
      const TextField(maxLines: 5, decoration: InputDecoration(hintText: "写出解题步骤…")),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _submitted ? null : () => _submit(true),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
        child: const Text("提交并查看解答"),
      ),
    ]);
  }

  // 英语阅读：左原文右题目
  Widget _readingBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: AppColors.ice.withValues(alpha: 0.5), borderRadius: BorderRadius.circular(12)),
        child: SelectableText(q.readingMaterial, style: const TextStyle(fontSize: 13.5, height: 1.7)),
      ),
      const SizedBox(height: 12),
      OptionSelector(options: q.options, multi: false),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _submitted ? null : () => _submit(true),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
        child: const Text("提交答案"),
      ),
    ]);
  }

  // 作文：输入框 + Mock AI 批改
  Widget _essayBody(Exercise q) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const TextField(maxLines: 10, decoration: InputDecoration(hintText: "在这里写你的作文…")),
      const SizedBox(height: 12),
      if (_submitted)
        const CatBubble(text: "（Mock AI 批改）整体结构清晰，注意时态一致性与用词多样性，继续加油喵~", mood: CatMood.happy)
      else
        FilledButton(
          onPressed: () => _submit(true),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
          child: const Text("提交作文（AI 批改）"),
        ),
    ]);
  }

  Widget _result(Exercise q) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _correct ? AppColors.green.withValues(alpha: 0.12) : AppColors.red.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(_correct ? Icons.check_circle_rounded : Icons.cancel_rounded, color: _correct ? AppColors.green : AppColors.red),
          const SizedBox(width: 8),
          Text(_correct ? "回答正确" : "回答有误", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: _correct ? AppColors.green : AppColors.red)),
        ]),
        const SizedBox(height: 8),
        Text("参考答案：${q.answer}", style: const TextStyle(fontSize: 13, height: 1.6)),
        const SizedBox(height: 6),
        Text("解析：${q.explanation}", style: const TextStyle(fontSize: 12.5, height: 1.6, color: const Color(0xFF64748B))),
        const SizedBox(height: 10),
        CatBubble(text: "做错了也别灰心，看看解析里「为什么」，下次就能举一反三喵~", mood: _correct ? CatMood.celebrate : CatMood.comfort),
      ]),
    );
  }
}

/// 多语言代码编辑器面板（阶段5 §二.3）
class _CodeEditorPanel extends StatefulWidget {
  const _CodeEditorPanel({required this.subject});
  final Subject subject;

  @override
  State<_CodeEditorPanel> createState() => _CodeEditorPanelState();
}

class _CodeEditorPanelState extends State<_CodeEditorPanel> {
  late String _lang = widget.subject.usesEditor ? _defaultLang(widget.subject) : "cpp";
  String _status = "未启动沙箱";

  static String _defaultLang(Subject s) => switch (s) {
        Subject.java => "java",
        Subject.python => "python",
        Subject.database => "sql",
        Subject.fullstack => "cpp",
        Subject.deepLearning => "cpp",
        _ => "cpp",
      };

  static const _langs = ["c", "cpp", "java", "python", "sql"];
  static const _sandbox = {
    "c": "正在启动 GCC 沙箱...",
    "cpp": "正在启动 G++ 沙箱...",
    "java": "正在启动 JVM 沙箱...",
    "python": "正在启动 CPython 沙箱...",
    "sql": "正在启动 MySQL 沙箱...",
  };

  void _run() {
    setState(() => _status = _sandbox[_lang] ?? "沙箱启动中...");
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) setState(() => _status = "运行完成 · AC ✅");
    });
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        DropdownButton<String>(
          value: _lang,
          underline: const SizedBox(),
          items: _langs.map((l) => DropdownMenuItem(value: l, child: Text(l.toUpperCase()))).toList(),
          onChanged: (v) => setState(() => _lang = v!),
        ),
        const Spacer(),
        CppCatMascot(mood: CatMood.thinking, size: 32, glow: false),
        const SizedBox(width: 6),
        Text(_status, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
      ]),
      const SizedBox(height: 8),
      Container(
        width: double.infinity,
        height: 140,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: dark ? const Color(0xFF0B1220) : const Color(0xFFF1F5F9),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.ice),
        ),
        child: const Text("// 在这里编写你的代码…",
            style: TextStyle(fontFamily: "JetBrains Mono", fontSize: 13, color: Color(0xFF1E3A8A))),
      ),
      const SizedBox(height: 8),
      FilledButton.icon(onPressed: _run, icon: const Icon(Icons.play_arrow_rounded, size: 18), label: const Text("运行")),
    ]);
  }
}
