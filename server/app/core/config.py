from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cppmind:cppmind@localhost:5432/cppmind"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_refresh_secret: str = "dev-refresh-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_s: int = 7200        # 2h
    refresh_token_ttl_s: int = 30 * 86400  # 30d

    judge0_url: str = "http://localhost:2358"
    judge0_authn_token: str = ""

    ai_provider: str = "deepseek"  # deepseek | openai | claude（默认 DeepSeek，国内直连、成本低）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"            # 轻量模式：诊断/问答/学习陪伴
    deepseek_model_pro: str = "deepseek-reasoner"    # 重量模式：面试/审查/计划（R1 推理）
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_model_pro: str = "gpt-4o"
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"
    ai_daily_quota_free: int = 20
    ai_daily_quota_pro: int = 200

    judge_daily_quota_free: int = 10
    judge_daily_quota_pro: int = 100

    github_token: str = ""
    leetcode_graphql: str = "https://leetcode.cn/graphql"
    sync_cron_hour: int = 3

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "cppmind"
    minio_secret_key: str = "cppmind-secret"
    minio_bucket: str = "cppmind"

    sentry_dsn: str = ""

    shared_dir: str = "../shared"
    content_dir: str = "../content"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
