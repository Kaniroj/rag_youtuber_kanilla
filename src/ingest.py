from __future__ import annotations

import textwrap
import uuid
from pathlib import Path
from typing import Iterable, List

import google.generativeai as genai
import lancedb
import numpy as np
import pandas as pd

from src.config import settings


# ---------- مرحله ۱: آماده‌سازی Gemini برای embedding ----------

def configure_gemini() -> None:
    """تنظیم API key برای کتابخانه‌ی Gemini."""
    genai.configure(api_key=settings.gemini_api_key)


def get_embedding(text: str) -> List[float]:
    """
    گرفتن embedding از یک متن.
    از مدل embedding رسمی Gemini استفاده می‌کنیم.
    """
    # برای احتیاط، متن خیلی طولانی را کوتاه می‌کنیم
    clipped = textwrap.shorten(text, width=8000, placeholder=" ...")

    result = genai.embed_content(
        model="models/text-embedding-004",  # مدل embedding Gemini
        content=clipped,
    )
    embedding = result["embedding"]
    # مطمئن شو لیست float است (نه numpy array عجیب)
    return list(embedding)


# ---------- مرحله ۲: خواندن و چانک‌کردن ترنسکریپت‌ها ----------

def load_transcript_files() -> Iterable[Path]:
    """
    همه فایل‌های ترنسکریپت را از پوشه‌ی تنظیم‌شده برمی‌گرداند.
    فعلاً پسوندهای txt و md را در نظر می‌گیریم.
    """
    transcripts_dir = settings.transcripts_dir
    if not transcripts_dir.exists():
        raise FileNotFoundError(f"Transcript directory not found: {transcripts_dir}")

    for path in transcripts_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            yield path


def read_text_file(path: Path) -> str:
    """خواندن محتوای یک فایل متنی با utf-8."""
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
    """
    شکستن متن بلند به چانک‌های کوچکتر برای RAG.

    مثال: chunk_size=800, overlap=200 یعنی:
    چانک ۰: کاراکترهای 0-800
    چانک ۱: از 600 تا 1400
    و ...

    این کمک می‌کند context در مرز چانک‌ها گم نشود.
    """
    if not text:
        return []

    # whitespaceهای اضافی را تمیز می‌کنیم
    text = " ".join(text.split())

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == length:
            break
        start = end - overlap

    return chunks


# ---------- مرحله ۳: ساخت دیتافریم آماده برای LanceDB ----------

def build_segments_dataframe() -> pd.DataFrame:
    """
    ترنسکریپت‌ها را می‌خواند، چانک می‌کند و
    یک DataFrame با ستون‌های زیر می‌سازد:

    - id: str (uuid)
    - video_id: str (نام فایل بدون پسوند)
    - chunk_index: int
    - text: str
    - embedding: list[float]
    """
    configure_gemini()

    rows = []

    for transcript_path in load_transcript_files():
        video_id = transcript_path.stem  # اسم فایل بدون پسوند
        raw_text = read_text_file(transcript_path)
        chunks = chunk_text(raw_text)

        for idx, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "video_id": video_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "embedding": emb,
                }
            )

    if not rows:
        raise RuntimeError(
            "هیچ دیتایی خوانده نشد. مطمئن شو در data/transcripts فایل .txt یا .md داری."
        )

    df = pd.DataFrame(rows)
    return df


# ---------- مرحله ۴: نوشتن در LanceDB ----------

def create_or_overwrite_lancedb_table(df: pd.DataFrame) -> None:
    """
    دیتابیس LanceDB را در مسیر تنظیم‌شده می‌سازد
    و جدول 'segments' را overwrite می‌کند.
    """
    db_path = settings.lancedb_dir
    db_path.mkdir(parents=True, exist_ok=True)

    db = lancedb.connect(str(db_path))

    table_name = settings.lancedb_table

    # اگر جدول از قبل هست، حذف می‌کنیم (حالت ساده برای پروژه)
    if table_name in db.table_names():
        db.drop_table(table_name)

    # LanceDB schema را از روی DataFrame تشخیص می‌دهد
    db.create_table(table_name, data=df)
    print(f"✅ LanceDB table '{table_name}' created with {len(df)} rows at {db_path}")


def main() -> None:
    print("🚀 شروع ingestion ترنسکریپت‌ها...")
    df = build_segments_dataframe()
    print(f"✅ DataFrame ساخته شد، تعداد ردیف‌ها: {len(df)}")
    create_or_overwrite_lancedb_table(df)
    print("🎉 کار ingestion با موفقیت تمام شد.")


if __name__ == "__main__":
    main()
