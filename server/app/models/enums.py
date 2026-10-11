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
