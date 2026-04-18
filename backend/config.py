from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://scraper:scraper_pass@localhost:5432/scraper_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_broker_url: str = "redis://localhost:6379/1"

    # Security
    secret_key: str = "change-me-to-a-long-random-secret-key"
    encryption_key: str = "change-me-to-32-bytes-base64-key=="
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:8b"

    # Proxy
    proxy_pool_url: str = ""
    proxy_pool_username: str = ""
    proxy_pool_password: str = ""

    # Notifications
    slack_webhook_url: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"

    # External APIs
    data_go_kr_api_key: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""
    kakao_rest_api_key: str = ""
    dart_api_key: str = ""
    youtube_api_key: str = ""

    # Rate Limiting
    default_rate_limit_delay_ms: int = 1000
    max_concurrent_per_domain: int = 5

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
