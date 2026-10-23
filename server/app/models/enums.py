from enum import Enum


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    banned = "banned"


class Direction(str, Enum):
    exam = "exam"
    job = "job"
    dl = "dl"


class Plan(str, Enum):
    free = "free"
    pro = "pro"


class Theme(str, Enum):
    light = "light"
    dark = "dark"
    system = "system"


class LessonType(str, Enum):
    concept = "concept"
    pitfall = "pitfall"
    example = "example"


class CodeLang(str, Enum):
    c = "c"
    cpp = "cpp"


class CodeStd(str, Enum):
    c11 = "c11"
    c17 = "c17"
    cpp11 = "cpp11"
    cpp14 = "cpp14"
    cpp17 = "cpp17"
    cpp20 = "cpp20"
    cpp23 = "cpp23"


class ExerciseType(str, Enum):
    choice = "choice"
    fix_error = "fix_error"
    output = "output"
    coding = "coding"


class Difficulty(str, Enum):
    easy = "easy"
    mid = "mid"
    hard = "hard"


class ExerciseSource(str, Enum):
    self_ = "self"
    leetcode = "leetcode"
    nowcoder = "nowcoder"


class SubmissionStatus(str, Enum):
    queued = "queued"
    running = "running"
    ac = "ac"
    wa = "wa"
    tle = "tle"
    mle = "mle"
    ce = "ce"
    re = "re"
    ie = "ie"


class QuestionType(str, Enum):
    exercise = "exercise"
    interview = "interview"


class NoteTarget(str, Enum):
    kp = "kp"
    exercise = "exercise"
    project = "project"


class FavoriteTarget(str, Enum):
    kp = "kp"
    exercise = "exercise"
    lesson = "lesson"
    resource = "resource"
    interview = "interview"


class PlanGenerator(str, Enum):
    ai = "ai"
    manual = "manual"


class PlanStatus(str, Enum):
    active = "active"
    done = "done"
    abandoned = "abandoned"


class TaskTarget(str, Enum):
    kp = "kp"
    exercise = "exercise"
    project_task = "project_task"


class TaskStatus(str, Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"


class ProjectCategory(str, Enum):
    basic = "basic"
    system = "system"
    dl = "dl"


class CareerTrack(str, Enum):
    """就业级项目库的学科维度，取值与 content/ 下的学科目录一一对应。"""

    cpp = "cpp"
    clang = "clang"
    java = "java"
    spring = "spring"
    python = "python"
    fullstack = "fullstack"
    database = "database"
    middleware = "middleware"
    ai = "ai"
    bigdata = "bigdata"
    data = "data"
    fundamentals = "fundamentals"
    tooling = "tooling"


class ProjectTier(str, Enum):
    """项目在能力阶梯上的位置，从入门到可写进简历。

    t1 能跑起来 / t2 能独立写 / t3 能讲清原理 / t4 能写进简历。
    """

    t1 = "t1"
    t2 = "t2"
    t3 = "t3"
    t4 = "t4"


class AIMode(str, Enum):
    socratic = "socratic"
    diagnose = "diagnose"
    review = "review"
    interview = "interview"
    plan = "plan"
    dl_guide = "dl_guide"


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class ResourceSource(str, Enum):
    github = "github"
    leetcode = "leetcode"
    nowcoder = "nowcoder"
    doc = "doc"


class ResourceType(str, Enum):
    repo = "repo"
    problem = "problem"
    article = "article"
    doc_link = "doc_link"


class SyncStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"


class SyncMode(str, Enum):
    full = "full"
    incremental = "incremental"


class DLModuleType(str, Enum):
    math = "math"
    ecosystem = "ecosystem"
    path = "path"


class DLFramework(str, Enum):
    pytorch = "pytorch"
    onnx = "onnx"
    tensorrt = "tensorrt"
    libtorch = "libtorch"
    llama_cpp = "llama_cpp"
    triton = "triton"


class GuideKind(str, Enum):
    """考研/学习指南条目的形态。

    note       = 原文笔记（这里只做索引与要点提炼，正文留在 GitHub）
    experience = 经验贴（按原文观点改写成可扫读要点）
    external   = 外部链接（幕布等第三方文档，不可内联）
    """

    note = "note"
    experience = "experience"
    external = "external"
