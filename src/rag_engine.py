from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import List

import lancedb
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.config import settings
from src.ingest import configure_gemini, get_embedding


# ---------- تنظیم کلید و مدل ----------

def _configure_google_key() -> None:
    """
    تنظیم API key برای هم google-generativeai (در ingest)
    و هم PydanticAI (GOOGLE_API_KEY).
    """
    configure_gemini()
    os.environ.setdefault("GOOGLE_API_KEY", settings.gemini_api_key)


_configure_google_key()

agent = Agent(
    "google-gla:gemini-2.5-flash",
    system_prompt=(
        "You are Kokchun Giang, a friendly but precise teacher in data engineering, "
        "AI engineering and Python.\n"
        "You answer questions based ONLY on the provided course transcript chunks.\n"
        "If the answer is not clearly in the context, say that you don't know.\n"
        "Explain concepts clearly, step-by-step, suitable for a motivated student."
    ),
)


# ---------- مدل‌های خروجی که API لازم دارد ----------


class SourceChunk(BaseModel):
    video_id: str = Field(description="نام فایل یا ویدیو")
    chunk_index: int = Field(description="شماره چانک در آن فایل")
    text: str = Field(description="متن کامل چانک")


class RagAnswer(BaseModel):
    answer: str = Field(description="جواب نهایی به کاربر")
    sources: list[SourceChunk] = Field(
        default_factory=list,
        description="چانک‌هایی که برای پاسخ استفاده شده‌اند",
    )


# ---------- کار با LanceDB ----------


@dataclass
class RetrievedChunk:
    video_id: str
    chunk_index: int
    text: str
    score: float


def _open_lancedb_table():
    db = lancedb.connect(str(settings.lancedb_dir))
    table = db.open_table(settings.lancedb_table)
    return table


def retrieve_context(question: str, k: int = 5) -> list[RetrievedChunk]:
    """
    از روی سوال embedding می‌گیرد و k تا چانک نزدیک را از LanceDB برمی‌گرداند.
    """
    table = _open_lancedb_table()
    query_emb: List[float] = get_embedding(question)

    df = table.search(query_emb).limit(k).to_pandas()

    chunks: list[RetrievedChunk] = []
    for _, row in df.iterrows():
        score = float(row.get("_distance", 0.0)) if "_distance" in df.columns else 0.0
        chunks.append(
            RetrievedChunk(
                video_id=str(row["video_id"]),
                chunk_index=int(row["chunk_index"]),
                text=str(row["text"]),
                score=score,
            )
        )

    return chunks


def _build_context_prompt(chunks: list[RetrievedChunk]) -> str:
    """
    چانک‌ها را به یک متن context تبدیل می‌کند که به مدل داده شود.
    """
    if not chunks:
        return "No context found."

    blocks: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        block = (
            f"[{i}] (video_id={ch.video_id}, chunk_index={ch.chunk_index})\n"
            f"{ch.text}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


# ---------- رابط اصلی RAG ----------


async def answer_question(question: str, *, k: int = 5) -> RagAnswer:
    """
    سوال کاربر را می‌گیرد، چانک‌های مرتبط را از LanceDB می‌آورد
    و با PydanticAI یک پاسخ ساختاریافته برمی‌گرداند.
    """
    chunks = retrieve_context(question, k=k)
    context_str = _build_context_prompt(chunks)

    prompt = (
        "You are answering a student's question based on these course transcript chunks.\n\n"
        f"Context:\n{context_str}\n\n"
        f"Question:\n{question}\n\n"
        "Answer clearly. If the answer is not in the context, say that you don't know.\n"
    )

    result = await agent.run(prompt, output_type=RagAnswer)
    rag_answer: RagAnswer = result.output

    # منبع‌ها را به SourceChunk تبدیل می‌کنیم
    sources_models = [
        SourceChunk(video_id=c.video_id, chunk_index=c.chunk_index, text=c.text)
        for c in chunks
    ]

    return RagAnswer(answer=rag_answer.answer, sources=sources_models)


def answer_question_sync(question: str, *, k: int = 5) -> RagAnswer:
    """
    نسخه sync فقط برای تست دستی از ترمینال.
    """
    return asyncio.run(answer_question(question, k=k))


if __name__ == "__main__":
    q = "LanceDB در این دوره چه استفاده‌ای دارد؟"
    ans = answer_question_sync(q, k=5)
    print("پاسخ:\n", ans.answer)
    print("\nمنابع:")
    for src in ans.sources:
        print(f"- {src.video_id} (chunk {src.chunk_index})")
