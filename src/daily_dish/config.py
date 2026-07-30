"""Application configuration loaded from environment variables."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WorkflowMode(StrEnum):
    """Which crew architecture to run."""

    AGENT_CENTRIC = "agent_centric"
    TASK_CENTRIC = "task_centric"
    COMPARE = "compare"


class Settings(BaseSettings):
    """Runtime settings for The Daily Dish chatbot."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    log_level: str = Field(default="INFO", alias="DAILY_DISH_LOG_LEVEL")
    verbose: bool = Field(default=True, alias="DAILY_DISH_VERBOSE")
    default_mode: WorkflowMode = Field(
        default=WorkflowMode.TASK_CENTRIC,
        alias="DAILY_DISH_DEFAULT_MODE",
    )
    faq_pdf_path: Path = Field(
        default=PROJECT_ROOT / "data" / "faqs" / "daily_dish_faq.pdf",
        alias="DAILY_DISH_FAQ_PDF_PATH",
    )
    openai_model_name: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_NAME")
    enable_web_search: bool = Field(default=False, alias="DAILY_DISH_ENABLE_WEB_SEARCH")

    @field_validator("faq_pdf_path", mode="before")
    @classmethod
    def _resolve_faq_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @property
    def faq_exists(self) -> bool:
        return self.faq_pdf_path.is_file()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
