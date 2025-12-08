from __future__ import annotations

from typing import List

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """مدلی برای درخواست چت از سمت کلاینت (فرانت‌اند)."""

    question: str


# توجه: برای پاسخ، مستقیم از RagAnswer که در rag_engine تعریف کردیم استفاده می‌کنیم.
# نیازی به تعریف مدل تکراری نیست.
