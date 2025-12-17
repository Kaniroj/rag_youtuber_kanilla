from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    chat_model: str = "gemini-2.0-flash"
    lancedb_dir: str = "db"
    lancedb_table: str = "transcripts"

    class Config:
        env_file = ".env"

settings = Settings()
