from __future__ import annotations

from typing import List
import lancedb
from google import genai

from src.config import settings

db = lancedb.connect(settings.lancedb_dir)
table = db.open_table(settings.lancedb_table)

client = genai.Client(api_key=settings.gemini_api_key)
MODEL = getattr(settings, "gemini_model", "models/gemini-2.5-flash")

def _load_video_text(video_id: str, max_chars: int = 12000) -> str:
    rows = table.to_pandas()
    df = rows[rows["video_id"] == video_id].sort_values("chunk_index")
    text = "\n\n".join(df["text"].tolist())
    return text[:max_chars]

async def make_youtube_description(video_id: str) -> str:
    text = _load_video_text(video_id)
    prompt = (
        "Write a concise YouTube video description (6-10 lines), focused on what the viewer learns. "
        "Use clear language. Avoid hallucinations; only use the provided transcript.\n\n"
        f"TRANSCRIPT:\n{text}"
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    return (resp.text or "").strip()

async def make_youtube_tags(video_id: str, min_n: int = 20, max_n: int = 40) -> str:
    text = _load_video_text(video_id)
    prompt = (
        f"Extract {min_n}-{max_n} relevant keywords/tags for YouTube based ONLY on the transcript. "
        "Return exactly one line: comma-separated keywords, no numbering, no extra text.\n\n"
        f"TRANSCRIPT:\n{text}"
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    line = (resp.text or "").strip().replace("\n", "")
    return line
