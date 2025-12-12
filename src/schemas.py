# src/schemas.py
from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel


class Source(BaseModel):
    video_id: str
    chunk_index: int
    text: str


class RagAnswer(BaseModel):
    answer: str
    sources: List[Source]


class ChatRequest(BaseModel):
    question: str
    # سه زبان مجاز
    language: Literal["sv", "en", "fa"] = "sv"
