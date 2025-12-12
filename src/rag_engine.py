# src/rag_engine.py
from __future__ import annotations

from typing import List

import lancedb
from google import genai

from src.config import settings
from src.schemas import RagAnswer, Source


# 1) اتصال به LanceDB
db = lancedb.connect(settings.lancedb_dir)
table = db.open_table(settings.lancedb_table)

# 2) ساخت کلاینت Gemini
client = genai.Client(api_key=settings.gemini_api_key)

# 3) مدل Gemini (حتماً باید در models.list وجود داشته باشد)
GEMINI_MODEL = "models/gemini-2.5-flash"


# 4) System prompt بر اساس زبان
LANG_SYSTEM_PROMPTS = {
    "sv": (
        "Du är en hjälpsam lärare som svarar kort och tydligt på svenska. "
        "Svara bara baserat på kontexten från kursens transkript. "
        "Om du inte vet, säg att du är osäker."
    ),
    "en": (
        "You are a helpful teacher who answers briefly and clearly in English. "
        "Only use the provided course transcript context. "
        "If you don't know, say that you are unsure."
    ),
    "fa": (
        "تو یک مدرس حرفه‌ای هستی که کوتاه و واضح به زبان فارسی جواب می‌دهی. "
        "فقط از متن‌های داده‌شدهٔ دوره استفاده کن. "
        "اگر نمی‌دانی، صادقانه بگو مطمئن نیستی."
    ),
}


def shorten_sources(sources: List[Source], max_len: int = 200) -> List[Source]:
    """کوتاه‌کردن متن سورس‌ها برای نمایش"""
    shortened: List[Source] = []

    for s in sources:
        text = s.text.strip()
        if len(text) > max_len:
            text = text[:max_len].rsplit(" ", 1)[0] + "..."

        shortened.append(
            Source(
                video_id=s.video_id,
                chunk_index=s.chunk_index,
                text=text,
            )
        )

    return shortened


async def answer_question(
    question: str,
    k: int = 5,
    language: str = "sv",
) -> RagAnswer:
    """
    سؤال کاربر را می‌گیرد، نزدیک‌ترین چانک‌ها را از LanceDB پیدا می‌کند
    و با کمک Gemini پاسخی به زبان خواسته‌شده تولید می‌کند.
    """

    # 1) جستجو در LanceDB
    results = table.search(question).limit(k).to_list()

    sources: List[Source] = []
    context_chunks: List[str] = []

    for row in results:
        src = Source(
            video_id=row["video_id"],
            chunk_index=row["chunk_index"],
            text=row["text"],
        )
        sources.append(src)
        context_chunks.append(src.text)

    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "NO CONTEXT"

    # 2) انتخاب system prompt
    system_prompt = LANG_SYSTEM_PROMPTS.get(language, LANG_SYSTEM_PROMPTS["sv"])

    # 3) ساخت پرامپت نهایی
    full_prompt = (
        f"{system_prompt}\n\n"
        "Kurskontext (utdrag ur transkriptet):\n"
        f"{context}\n\n"
        "Fråga / Question från studenten:\n"
        f"{question}\n\n"
        "Svara endast baserat på kurskontexten ovan."
    )

    # 4) فراخوانی Gemini
    completion = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt,
    )

    answer_text = (
        getattr(completion, "output_text", None)
        or getattr(completion, "text", None)
        or str(completion)
    )

    # 5) کوتاه‌کردن سورس‌ها برای خروجی
    shortened_sources = shorten_sources(sources)

    return RagAnswer(
        answer=answer_text,
        sources=shortened_sources,
    )
