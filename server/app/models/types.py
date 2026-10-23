"""跨表复用的枚举类型单例。

为什么需要这个文件：
    SQLAlchemy 的 `Enum(X, name="...")` 每次调用都会产生**新的类型对象**。
    同一个 PG 枚举名在多张表里各自实例化时，`metadata.create_all` 会对每个对象
    各发一次 `CREATE TYPE`，PostgreSQL 报 `type "xxx" already exists`。
    把类型定义收敛到这里复用同一个对象，即可只创建一次。
"""
import uuid as uuid_pkg

from sqlalchemy import CHAR, JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import TypeDecorator

from app.models.enums import Difficulty, ProjectTier

PROJECT_DIFFICULTY = Enum(Difficulty, name="project_difficulty")
CAREER_TIER = Enum(ProjectTier, name="career_tier")

# --- 跨库类型别名 ---------------------------------------------------------
# 生产是 PostgreSQL，用原生 JSONB / UUID；SQLite（离线冒烟、演示）不认识这两个
# 方言类型，`create_all` 会直接 CompileError。with_variant 让同一列在两个方言
# 下各自编译：PG 仍是 JSONB / UUID（与既有迁移一致），SQLite 退化为 JSON / CHAR(36)。
# 这不是"生产换库"，只是让后端能在没有 Docker 的机器上被验证起来。
JSONType = JSON().with_variant(JSONB(), "postgresql")


class UUIDType(TypeDecorator):
    """PostgreSQL 用原生 UUID，其它方言（SQLite）用 CHAR(36)。

    注意：`CHAR(36).with_variant(...)` 是**不行的**。`CHAR` 没有绑定处理器，
    SQLite 驱动会直接收到 `uuid.UUID` 对象并抛
    `ProgrammingError: type 'UUID' is not supported`。必须用 TypeDecorator
    自己在绑定方向转 `str`、在取回方向转回 `uuid.UUID`，让 ORM 层始终面对
    Python 的 UUID 对象，应用代码无需感知底层方言。
    """

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        if isinstance(value, uuid_pkg.UUID):
            return str(value)
        return str(uuid_pkg.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        if isinstance(value, uuid_pkg.UUID):
            return value
        return uuid_pkg.UUID(str(value))
