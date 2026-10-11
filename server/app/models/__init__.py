from app.models.ai import AIConversation, AIMessage  # noqa: F401
from app.models.content import (  # noqa: F401
    Chapter,
    Course,
    DeepLearningModule,
    KnowledgePoint,
    Lesson,
    MindMapNode,
)
from app.models.exercise import (  # noqa: F401
    Exercise,
    InterviewQuestion,
    Tag,
    TestCase,
    exercise_tags,
    interview_question_tags,
)
from app.models.progress import (  # noqa: F401
    Achievement,
    DailyTask,
    Note,
    Progress,
    StudyPlan,
    UserAchievement,
    WrongQuestion,
)
from app.models.project import Project, ProjectTask, ProjectTaskProgress  # noqa: F401
from app.models.resource import Favorite, Resource, SyncJob, resource_chapters  # noqa: F401
from app.models.submission import Submission  # noqa: F401
from app.models.user import OAuthIdentity, User, UserProfile  # noqa: F401
