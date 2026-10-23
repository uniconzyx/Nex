"""考试接口的边界校验模型。

只做「形状」校验，业务校验（题目是否属于该科目、选项是否越界）在
services/exam_bank.py 里做，因为它需要题库上下文。

extra="forbid"：客户端把 choice 写成 choise 时立刻报错，而不是当成没传
再到判分时抛出「缺 choice」——前者能一眼定位拼写错误。
"""
from pydantic import BaseModel, ConfigDict, Field


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=64, description="题目 id，如 q-algo-c01")
    # 单选传 choice；多选传 choices；填空传 text。互斥字段由题型决定，服务层校验。
    choice: int | None = Field(default=None, ge=0, description="单选题选项下标，从 0 开始")
    choices: list[int] | None = Field(default=None, max_length=20, description="多选题选项下标集合")
    text: str | None = Field(default=None, max_length=4000, description="填空题作答原文")


class GradeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AnswerIn] = Field(min_length=1, max_length=100)
