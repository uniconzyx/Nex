from typing import Literal

from pydantic import BaseModel, Field


class MasteryPatch(BaseModel):
    mastery: int = Field(ge=0, le=3)  # 0未学 1学过 2掌握 3精通


# 注意：Literal 的取值必须与 app/models/enums.py 的 NoteTarget /
# FavoriteTarget 完全一致。写成裸 str 时，非法值会一路穿透到 asyncpg，
# 变成 `invalid input value for enum note_target: "chapter"` 的 500——
# 用户看到的是"服务器坏了"，实际是自己传错了参数。
class NoteIn(BaseModel):
    target_type: Literal["kp", "exercise", "project"]
    target_id: int
    content_md: str = ""


class FavoriteIn(BaseModel):
    target_type: Literal["kp", "exercise", "lesson", "resource", "interview"]
    target_id: int


class StudyStateIn(BaseModel):
    """前端 localStorage 快照。字段名与 ProgressState 一一对应，便于直接序列化。"""

    done_chapters: list[str] = Field(default_factory=list, max_length=2000)
    done_projects: list[str] = Field(default_factory=list, max_length=2000)
    checkins: list[str] = Field(default_factory=list, max_length=3650)  # YYYY-MM-DD
    coins: int = Field(default=0, ge=0, le=10_000_000)
    outfit: str = Field(default="default", max_length=40)
    theme: Literal["light", "dark"] = "light"
    client_rev: int = Field(default=0, ge=0)
