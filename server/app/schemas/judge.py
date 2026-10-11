from pydantic import BaseModel, Field

from app.models.enums import CodeStd


class SubmissionIn(BaseModel):
    exercise_id: int | None = None  # 空 = 自由运行台
    lang: CodeStd
    source_code: str = Field(min_length=1, max_length=100_000)
    stdin: str | None = Field(default=None, max_length=10_000)


class RedoIn(BaseModel):
    result: str  # right / wrong
