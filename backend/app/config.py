"""Application settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "租约守护"
    database_url: str = "sqlite:///./lease_guard.db"
    jwt_secret: str = "dev-only-change-me-lease-guard-2026"
    jwt_expire_minutes: int = 720
    storage_dir: str = "./storage"
    max_upload_mb: int = 30
    max_pages: int = 50

    trial_username: str = "trial"
    trial_password: str = "LeaseGuard2026!"
    trial_review_quota: int = 3
    trial_question_quota: int = 20

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    enable_llm: bool = False

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir).resolve()


def get_settings() -> Settings:
    return Settings()
