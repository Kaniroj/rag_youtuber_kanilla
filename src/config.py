from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # تنظیمات سراسری برای pydantic-settings (ورژن ۲)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # متغیرهای اضافی env را نادیده بگیر
        populate_by_name=True,   # اجازه بده با اسم فیلد هم مقداردهی شود
    )

    # --- LLM / Gemini ---
    # مقدار از متغیر محیطی GEMINI_API_KEY خوانده می‌شود
    gemini_api_key: str = Field(..., alias="GOOGLE_API_KEY")


    # --- Paths ---
    transcripts_dir: Path = Field(
        default_factory=lambda: Path("data/transcripts"),
        alias="TRANSCRIPTS_DIR",
    )
    lancedb_dir: Path = Field(
        default_factory=lambda: Path("db/lancedb"),
        alias="LANCEDB_DIR",
    )
    lancedb_table: str = Field(
        default="segments",
        alias="LANCEDB_TABLE",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


# استفادهٔ مستقیم در بقیه‌ی کدها
settings = get_settings()
