from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI-Powered Attendance Platform"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./attendance.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"
    )
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    model_name: str | None = None

    @property
    def effective_groq_model(self) -> str:
        return self.groq_model or self.model_name or "qwen/qwen3.8-27b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
