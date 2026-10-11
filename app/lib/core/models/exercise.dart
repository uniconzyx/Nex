/// 题库数据模型：多学科 + 多题型（阶段5 架构升级，对应需求 §三.5 数据结构）
library;

import "subject.dart";

/// 选项
class QuestionOption {
  QuestionOption({required this.key, required this.text, this.isCorrect = false});
  factory QuestionOption.fromJson(Map<String, dynamic> j) => QuestionOption(
        key: j["key"]?.toString() ?? "",
        text: j["text"]?.toString() ?? "",
        isCorrect: j["is_correct"] == true,
      );
  final String key;
  final String text;
  final bool isCorrect;
}

/// 测试用例
class TestCase {
  TestCase({required this.input, required this.output, this.hidden = false});
  factory TestCase.fromJson(Map<String, dynamic> j) => TestCase(
        input: j["input"]?.toString() ?? "",
        output: j["output"]?.toString() ?? "",
        hidden: j["hidden"] == true,
      );
  final String input;
  final String output;
  final bool hidden;
}

/// 题目（覆盖编程/考研/客观题全场景）
class Exercise {
  Exercise({
    required this.id,
    required this.subject,
    required this.chapter,
    required this.type,
    required this.difficulty,
    required this.source,
    required this.title,
    this.content = "",
    this.options = const [],
    this.answer = "",
    this.explanation = "",
    this.tags = const [],
    this.testCases = const [],
    this.latexFormula = "",
    this.readingMaterial = "",
    this.aiPromptContext = "",
    this.sourceRef = "",
    this.resourceUrl,
    this.status = QuestionStatus.untouched,
    this.correctRate = 0.0,
  });

  factory Exercise.fromJson(Map<String, dynamic> j) => Exercise(
        id: j["id"]?.toString() ?? "",
        subject: _subject(j["subject"]),
        chapter: j["chapter"]?.toString() ?? "",
        type: _type(j["type"]),
        difficulty: _diff(j["difficulty"]),
        source: _src(j["source"]),
        title: j["title"]?.toString() ?? "",
        content: j["content"]?.toString() ?? "",
        options: (j["options"] as List?)
                ?.map((e) => QuestionOption.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        answer: j["answer"]?.toString() ?? "",
        explanation: j["explanation"]?.toString() ?? "",
        tags: (j["tags"] as List?)?.map((e) => "$e").toList() ?? const [],
        testCases: (j["test_cases"] as List?)
                ?.map((e) => TestCase.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        latexFormula: j["latex_formula"]?.toString() ?? "",
        readingMaterial: j["reading_material"]?.toString() ?? "",
        aiPromptContext: j["ai_prompt_context"]?.toString() ?? "",
        status: _status(j["status"]),
        correctRate: (j["correct_rate"] as num?)?.toDouble() ?? 0.0,
      );

  final String id;
  final Subject subject;
  final String chapter;
  final ExerciseType type;
  final Difficulty difficulty;
  final QuestionSource source;
  final String title;
  final String content;
  final List<QuestionOption> options;
  final String answer;
  final String explanation;
  final List<String> tags;
  final List<TestCase> testCases;
  final String latexFormula;
  final String readingMaterial;
  final String aiPromptContext;

  /// 真题依据：注明本题真实来源（C/C++/Java/Python/MySQL 学习内容、LeetCode/牛客真题、教材章节）。
  final String sourceRef;

  /// 外部资源链接：全栈开发路线等资源从 GitHub 获取时填仓库 URL；其余题目一般为空。
  final String? resourceUrl;
  final QuestionStatus status;
  final double correctRate;

  static Subject _subject(dynamic v) =>
      Subject.values.firstWhere((e) => e.name == v?.toString(), orElse: () => Subject.cpp);
  static ExerciseType _type(dynamic v) => ExerciseType.values.firstWhere(
      (e) => e.name == v?.toString(),
      orElse: () => ExerciseType.singleChoice);
  static Difficulty _diff(dynamic v) => Difficulty.values.firstWhere(
      (e) => e.name == v?.toString(),
      orElse: () => Difficulty.easy);
  static QuestionSource _src(dynamic v) => QuestionSource.values.firstWhere(
      (e) => e.name == v?.toString(),
      orElse: () => QuestionSource.chapter);
  static QuestionStatus _status(dynamic v) => QuestionStatus.values.firstWhere(
      (e) => e.name == v?.toString(),
      orElse: () => QuestionStatus.untouched);
}
