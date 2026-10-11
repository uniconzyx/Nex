/// 数据模型：与后端 schemas / 路由返回结构一一对应（宽容解析，字段缺失不炸）
library;

int _i(dynamic v, [int d = 0]) => v is int ? v : int.tryParse("$v") ?? d;
String _s(dynamic v, [String d = ""]) => v?.toString() ?? d;

class User {
  User({required this.id, required this.nickname, this.avatar, this.direction, this.plan});
  factory User.fromJson(Map<String, dynamic> j) => User(
        id: _i(j["id"]),
        nickname: _s(j["nickname"], "同学"),
        avatar: j["avatar"] as String?,
        direction: j["direction"] as String?,
        plan: _s(j["plan"], "free"),
      );
  final int id;
  final String nickname;
  final String? avatar;
  final String? direction;
  final String plan;
}

class Chapter {
  Chapter({required this.id, required this.code, required this.title,
      this.track = "cpp", this.isFree = false, this.estMinutes = 0, this.mastery});
  factory Chapter.fromJson(Map<String, dynamic> j) => Chapter(
        id: _i(j["id"]), code: _s(j["code"]), title: _s(j["title"]),
        track: _s(j["track"], "cpp"), isFree: j["is_free"] == true,
        estMinutes: _i(j["est_minutes"]),
        mastery: j["mastery"] == null ? null : _i(j["mastery"]),
      );
  final int id;
  final String code; // 如 cpp-ch03
  final String title;
  final String track; // c / cpp / dl
  final bool isFree;
  final int estMinutes;
  final int? mastery;
}

class Lesson {
  Lesson({required this.id, required this.type, required this.title,
      this.contentMd = "", this.code, this.lang = "cpp", this.std = "cpp17"});
  factory Lesson.fromJson(Map<String, dynamic> j) => Lesson(
        id: _i(j["id"]), type: _s(j["type"]), title: _s(j["title"]),
        contentMd: _s(j["content_md"]), code: j["code"] as String?,
        lang: _s(j["lang"], "cpp"), std: _s(j["std"], "cpp17"),
      );
  final int id;
  final String type; // concept / pitfall / example
  final String title;
  final String contentMd;
  final String? code;
  final String lang;
  final String std;
}

class MindmapNode {
  MindmapNode({required this.id, this.parentId, this.kpId,
      required this.label, required this.x, required this.y, required this.state});
  factory MindmapNode.fromJson(Map<String, dynamic> j) => MindmapNode(
        id: _i(j["id"]), parentId: j["parent_id"] == null ? null : _i(j["parent_id"]),
        kpId: j["kp_id"] == null ? null : _i(j["kp_id"]),
        label: _s(j["label"]),
        x: (j["x"] as num?)?.toDouble() ?? 0,
        y: (j["y"] as num?)?.toDouble() ?? 0,
        state: _s(j["state"], "todo"),
      );
  final int id;
  final int? parentId;
  final int? kpId;
  final String label;
  final double x, y;
  final String state; // mastered / learning / todo / weak
}

class Submission {
  Submission({required this.id, required this.status, this.passed = 0, this.total = 0,
      this.timeMs, this.memoryKb, this.stdout, this.stderr, this.diagnosisMd});
  factory Submission.fromJson(Map<String, dynamic> j) => Submission(
        id: _i(j["id"]), status: _s(j["status"], "queued"),
        passed: _i(j["passed"]), total: _i(j["total"]),
        timeMs: j["time_ms"] == null ? null : _i(j["time_ms"]),
        memoryKb: j["memory_kb"] == null ? null : _i(j["memory_kb"]),
        stdout: j["stdout"] as String?, stderr: j["stderr"] as String?,
        diagnosisMd: j["diagnosis_md"] as String?,
      );
  final int id;
  final String status; // queued/running/ac/wa/tle/mle/ce/re/ie
  final int passed, total;
  final int? timeMs, memoryKb;
  final String? stdout, stderr, diagnosisMd;
  bool get finished => !const {"queued", "running"}.contains(status);
}

class WrongQuestion {
  WrongQuestion({required this.id, required this.title, required this.wrongCount,
      required this.nextReviewAt, this.questionType = "exercise"});
  factory WrongQuestion.fromJson(Map<String, dynamic> j) => WrongQuestion(
        id: _i(j["id"]), title: _s(j["title"]), wrongCount: _i(j["wrong_count"], 1),
        nextReviewAt: _s(j["next_review_at"]), questionType: _s(j["question_type"], "exercise"),
      );
  final int id;
  final String title;
  final int wrongCount;
  final String nextReviewAt;
  final String questionType;
}

class Project {
  Project({required this.id, required this.title, required this.category,
      this.summary = "", this.difficulty = "mid", this.doneTasks = 0, this.totalTasks = 0});
  factory Project.fromJson(Map<String, dynamic> j) => Project(
        id: _i(j["id"]), title: _s(j["title"]), category: _s(j["category"], "basic"),
        summary: _s(j["summary"]), difficulty: _s(j["difficulty"], "mid"),
        doneTasks: _i(j["done_tasks"]), totalTasks: _i(j["total_tasks"]),
      );
  final int id;
  final String title;
  final String category; // basic / system / dl
  final String summary;
  final String difficulty;
  final int doneTasks, totalTasks;
}

class ResourceItem {
  ResourceItem({required this.id, required this.source, required this.type,
      required this.title, this.url = "", this.chapterId, this.meta = const {}});
  factory ResourceItem.fromJson(Map<String, dynamic> j) => ResourceItem(
        id: _i(j["id"]), source: _s(j["source"]), type: _s(j["type"]),
        title: _s(j["title"]), url: _s(j["url"]),
        chapterId: j["chapter_id"] == null ? null : _i(j["chapter_id"]),
        meta: (j["meta"] as Map?)?.cast<String, dynamic>() ?? const {},
      );
  final int id;
  final String source; // github / leetcode / nowcoder / doc
  final String type; // repo / problem / article / doc_link
  final String title;
  final String url;
  final int? chapterId;
  final Map<String, dynamic> meta;
}

class ChatMessage {
  ChatMessage({required this.role, required this.content, this.streaming = false});
  final String role; // user / assistant
  String content;
  bool streaming;
}

/// 判题语言标准（server CodeStd 枚举）
const kCodeStds = ["c11", "c17", "cpp11", "cpp14", "cpp17", "cpp20", "cpp23"];

/// AI 模式（server AIMode 枚举）
const kAiModes = {
  "socratic": "🎓 苏格拉底",
  "diagnose": "🩺 编译诊断",
  "review": "🔍 代码审查",
  "interview": "🎤 模拟面试",
  "plan": "🗓️ 学习计划",
  "dl_guide": "🚀 DL 部署",
};
