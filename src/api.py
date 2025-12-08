from __future__ import annotations

from fastapi import FastAPI

from src.rag_engine import RagAnswer, answer_question
from src.schemas import ChatRequest

app = FastAPI(
    title="RAG Youtuber API",
    description="چت‌بات RAG مبتنی بر ترنسکریپت‌های کورس کوکچون گیان",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict:
    """یه endpoint ساده برای تست سالم‌بودن سرویس."""
    return {"status": "ok"}


@app.post("/chat", response_model=RagAnswer)
async def chat_endpoint(payload: ChatRequest) -> RagAnswer:
    """
    endpoint اصلی چت:
    - ورودی: سوال کاربر
    - خروجی: جواب چت‌بات + لیست منابع
    """
    rag_answer = await answer_question(payload.question, k=5)
    return rag_answer
