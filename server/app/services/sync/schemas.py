from pydantic import BaseModel, Field, field_validator, model_validator

# ===== 题库 JSON 包校验（与 Phase3 文档第 9 节格式一致）=====
# 两种包：外部题目映射包（cppmind-external-v1）/ 自建题库包（cppmind-exercise-v1）


class ExternalItem(BaseModel):
    external_id: str = Field(min_length=1)
    title: str
    title_cn: str | None = None
    difficulty: str | None = None  # easy / mid / hard
    tags: list[str] = []
    url: str
    mapped_chapters: list[str] = []


class ExternalPackage(BaseModel):
    meta: dict
    items: list[ExternalItem]

    @field_validator("meta")
    @classmethod
    def check_format(cls, v: dict) -> dict:
        if v.get("format") != "cppmind-external-v1":
            raise ValueError("meta.format 必须为 cppmind-external-v1")
        if v.get("source") not in ("leetcode", "nowcoder", "github", "doc"):
            raise ValueError("meta.source 非法")
        return v


class BankTestCase(BaseModel):
    input: str = ""
    expected_output: str
    is_sample: bool = False


class BankExercise(BaseModel):
    type: str  # choice / fix_error / output / coding
    difficulty: str = "mid"
    title: str
    content_md: str = ""
    options: list[dict] | None = None
    answer: dict = {}
    explanation: str = ""
    tags: list[str] = []
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256
    test_cases: list[BankTestCase] = []

    @model_validator(mode="after")
    def check_business_rules(self):
        if self.type == "coding":
            if not self.test_cases:
                raise ValueError(f"coding 题「{self.title}」必须包含至少 1 个测试用例")
        elif self.type == "choice":
            keys = {o.get("key") for o in (self.options or [])}
            correct = set(self.answer.get("correct", []))
            if len(keys) < 2:
                raise ValueError(f"选择题「{self.title}」选项必须 ≥2")
            if not correct or not correct.issubset(keys):
                raise ValueError(f"选择题「{self.title}」answer.correct 必须是选项 key 的子集")
        return self


class ExercisePackage(BaseModel):
    meta: dict
    items: list[BankExercise]

    @field_validator("meta")
    @classmethod
    def check_format(cls, v: dict) -> dict:
        if v.get("format") != "cppmind-exercise-v1":
            raise ValueError("meta.format 必须为 cppmind-exercise-v1")
        if not v.get("chapter"):
            raise ValueError("meta.chapter 必填（如 cpp-ch03）")
        return v
