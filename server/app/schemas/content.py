from pydantic import BaseModel, Field


class MasteryPatch(BaseModel):
    mastery: int = Field(ge=0, le=3)  # 0未学 1学过 2掌握 3精通


class NoteIn(BaseModel):
    target_type: str  # kp / exercise / project
    target_id: int
    content_md: str = ""


class FavoriteIn(BaseModel):
    target_type: str  # kp / exercise / lesson / resource / interview
    target_id: int
