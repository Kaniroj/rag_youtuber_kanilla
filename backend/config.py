from pathlib import Path

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # درست برای Pydantic v2
    gemini_api_key: str = Field(
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY")
    )

    # LanceDB
    lancedb_dir: Path = ROOT_DIR / "db" / "lancedb"
    lancedb_table: str = "segments"

    # Models
    embed_model: str = "models/text-embedding-004"
    chat_model: str = "gemini-2.0-flash"


settings = Settings()
