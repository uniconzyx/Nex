/// 多学科体系：学科注册表 + 题型定义（阶段5 架构升级）
library;

import "package:flutter/material.dart";

/// 学科领域
enum SubjectDomain { programming, kaoyan, deepLearning }

/// 学科（9 门：编程5 + 考研3 + 深度学习1）
enum Subject {
  cpp,
  java,
  python,
  database,
  fullstack,
  math,
  english,
  politics,
  deepLearning;

  String get id => name;

  String get label => switch (this) {
        Subject.cpp => "C/C++",
        Subject.java => "Java",
        Subject.python => "Python",
        Subject.database => "数据库",
        Subject.fullstack => "全栈开发",
        Subject.math => "考研数学",
        Subject.english => "考研英语",
        Subject.politics => "考研政治",
        Subject.deepLearning => "深度学习",
      };

  String get shortLabel => switch (this) {
        Subject.cpp => "C++",
        Subject.java => "Java",
        Subject.python => "Python",
        Subject.database => "数据库",
        Subject.fullstack => "全栈",
        Subject.math => "数学",
        Subject.english => "英语",
        Subject.politics => "政治",
        Subject.deepLearning => "DL",
      };

  SubjectDomain get domain => switch (this) {
        Subject.cpp || Subject.java || Subject.python || Subject.database || Subject.fullstack =>
          SubjectDomain.programming,
        Subject.math || Subject.english || Subject.politics => SubjectDomain.kaoyan,
        Subject.deepLearning => SubjectDomain.deepLearning,
      };

  /// 是否走代码编辑器（编程/数据库/深度学习偏代码，考研三科不走编辑器）
  bool get usesEditor => switch (this) {
        Subject.cpp || Subject.java || Subject.python || Subject.database ||
        Subject.fullstack || Subject.deepLearning =>
          true,
        _ => false,
      };

  IconData get icon => switch (this) {
        Subject.cpp => Icons.memory_rounded,
        Subject.java => Icons.coffee_rounded,
        Subject.python => Icons.code_rounded,
        Subject.database => Icons.storage_rounded,
        Subject.fullstack => Icons.layers_rounded,
        Subject.math => Icons.functions_rounded,
        Subject.english => Icons.translate_rounded,
        Subject.politics => Icons.account_balance_rounded,
        Subject.deepLearning => Icons.auto_awesome_rounded,
      };

  /// 主题色（保持蓝白体系，用不同强调青点缀区分学科，主蓝 #3B82F6 贯穿）
  Color get accent => switch (this) {
        Subject.cpp => const Color(0xFF3B82F6),
        Subject.java => const Color(0xFFF59E0B),
        Subject.python => const Color(0xFF22C55E),
        Subject.database => const Color(0xFF22D3EE),
        Subject.fullstack => const Color(0xFF8B5CF6),
        Subject.math => const Color(0xFF3B82F6),
        Subject.english => const Color(0xFF60A5FA),
        Subject.politics => const Color(0xFFEF4444),
        Subject.deepLearning => const Color(0xFF22D3EE),
      };

  static const all = Subject.values;

  /// 从 GitHub 获取的外部学习资源（仓库清单，owner/repo）。
  /// 阶段5 要求：全栈开发路线资源必须从 GitHub 获取；其余编程学科也给出官方/权威仓库。
  List<String> get githubRepos => switch (this) {
        Subject.cpp => const [
            "changkun/modern-cpp-tutorial",
            "rigtorp/awesome-modern-cpp",
            "Alinshans/MyTinySTL",
          ],
        Subject.java => const [
            "iluwatar/java-design-patterns",
            "Snailclimb/JavaGuide",
          ],
        Subject.python => const [
            "vinta/awesome-python",
            "TheAlgorithms/Python",
          ],
        Subject.database => const [
            "daniellemurray/mysql-cheat-sheet",
            "digitalocean/mysql-resources",
          ],
        Subject.fullstack => const [
            "jwasham/coding-interview-university",
            "kamranahmedse/developer-roadmap",
            "thedaviddias/Front-End-Checklist",
            "tiangolo/full-stack-fastapi-template",
          ],
        Subject.deepLearning => const [
            "microsoft/onnxruntime",
            "ggml-org/llama.cpp",
          ],
        _ => const [],
      };

  /// 资源是否主要来自 GitHub（全栈开发路线强制走 GitHub 获取资源）
  bool get resourcesFromGithub => this == Subject.fullstack;
}

/// 题型（阶段5 题库差异化渲染核心）
enum ExerciseType {
  singleChoice,
  multiChoice,
  fillBlank,
  fixError,
  programming,
  mathSolution,
  essay,
  reading;

  String get id => name;

  String get label => switch (this) {
        ExerciseType.singleChoice => "单选题",
        ExerciseType.multiChoice => "多选题",
        ExerciseType.fillBlank => "填空题",
        ExerciseType.fixError => "改错题",
        ExerciseType.programming => "编程题",
        ExerciseType.mathSolution => "解答题",
        ExerciseType.essay => "作文",
        ExerciseType.reading => "阅读",
      };

  /// 是否客观题（可自动判分）
  bool get isObjective => switch (this) {
        ExerciseType.singleChoice || ExerciseType.multiChoice ||
        ExerciseType.fillBlank || ExerciseType.fixError =>
          true,
        _ => false,
      };
}

/// 难度
enum Difficulty {
  easy,
  medium,
  hard;

  String get label => switch (this) {
        Difficulty.easy => "简单",
        Difficulty.medium => "中等",
        Difficulty.hard => "困难",
      };
}

/// 来源
enum QuestionSource {
  chapter,
  pastPaper,
  mock,
  interview;

  String get label => switch (this) {
        QuestionSource.chapter => "章节练习",
        QuestionSource.pastPaper => "历年真题",
        QuestionSource.mock => "模拟题",
        QuestionSource.interview => "大厂面经",
      };
}

/// 题目状态
enum QuestionStatus {
  untouched,
  done,
  wrong,
  favorite;

  String get label => switch (this) {
        QuestionStatus.untouched => "未做",
        QuestionStatus.done => "已完成",
        QuestionStatus.wrong => "错误",
        QuestionStatus.favorite => "收藏",
      };
}
