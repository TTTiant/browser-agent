"""
集中式配置（环境变量/ .env），保障可测性与可控性。
"""
# @file purpose: Centralized settings using Pydantic Settings.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BA_", env_file=".env", extra="ignore")

    headless: bool = True
    request_timeout_seconds: int = 30
    allowed_domains: list[str] = []
    log_level: str = "INFO"


settings = Settings()
