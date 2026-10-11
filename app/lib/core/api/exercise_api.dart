/// 题库 API 封装：Mock 优先，预留阶段4后端接口
library;

import "../models/exercise.dart";
import "../models/mock_data.dart";
import "../models/subject.dart";

/// 题库筛选条件
class ExerciseFilter {
  const ExerciseFilter({
    this.subject,
    this.type,
    this.difficulty,
    this.source,
    this.keyword = "",
    this.status,
  });

  final Subject? subject;
  final ExerciseType? type;
  final Difficulty? difficulty;
  final QuestionSource? source;
  final String keyword;
  final QuestionStatus? status;

  bool get isEmpty =>
      subject == null &&
      type == null &&
      difficulty == null &&
      source == null &&
      keyword.isEmpty &&
      status == null;
}

/// 题库数据源：当前用 Mock 数据，后端就绪后替换为 api_client 调用。
class ExerciseRepository {
  ExerciseRepository();

  /// 查询题目列表（Mock 内存过滤）
  Future<List<Exercise>> list(ExerciseFilter f) async {
    var items = List<Exercise>.from(mockExercises);
    if (f.subject != null) items = items.where((e) => e.subject == f.subject).toList();
    if (f.type != null) items = items.where((e) => e.type == f.type).toList();
    if (f.difficulty != null) items = items.where((e) => e.difficulty == f.difficulty).toList();
    if (f.source != null) items = items.where((e) => e.source == f.source).toList();
    if (f.status != null) items = items.where((e) => e.status == f.status).toList();
    if (f.keyword.isNotEmpty) {
      final kw = f.keyword.toLowerCase();
      items = items
          .where((e) =>
              e.title.toLowerCase().contains(kw) ||
              e.tags.any((t) => t.toLowerCase().contains(kw)))
          .toList();
    }
    return items;
  }

  /// 单题详情
  Future<Exercise?> getById(String id) async {
    for (final e in mockExercises) {
      if (e.id == id) return e;
    }
    return null;
  }

  /// 错题列表（Mock：状态为 wrong 的题）
  Future<List<Exercise>> wrongQuestions(Subject? subject) async {
    var items = mockExercises.where((e) => e.status == QuestionStatus.wrong).toList();
    if (subject != null) items = items.where((e) => e.subject == subject).toList();
    return items;
  }

  /// 收藏列表
  Future<List<Exercise>> favorites() async =>
      mockExercises.where((e) => e.status == QuestionStatus.favorite).toList();
}

/// 全局单例（可后续换成 Riverpod Provider）
final exerciseRepo = ExerciseRepository();
