from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nickname: str = Field(default="", max_length=50)


class LoginIn(BaseModel):
    account: str  # email 或 phone
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class ProfilePatch(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None
    direction: str | None = None  # exam / job / dl
    daily_minutes: int | None = Field(default=None, ge=5, le=1440)
    theme: str | None = None
    reduced_motion: bool | None = None
    font_scale: float | None = Field(default=None, ge=0.8, le=2.0)
