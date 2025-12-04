from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
   

    # --- LLM / Gemini ---
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")

    # --- Paths ---
    transcripts_dir: Path = Field(default=Path("data/transcripts"), alias="TRANSCRIPTS_DIR")
    lancedb_dir: Path = Field(default=Path("db/lancedb"), alias="LANCEDB_DIR")
    lancedb_table: str = Field(default="segments", alias="LANCEDB_TABLE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    
    return Settings()


# برای استفاده مستقیم:
settings = get_settings()
