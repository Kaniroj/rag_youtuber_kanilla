from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

import lancedb
from google import genai

from backend.config import settings


@dataclass
class RetrievedChunk:
    source_file: str
    chunk_index: int
    text: str
    score: float | None = None


def embed_query(client: genai.Client, query: str) -> List[float]:
    res = client.models.embed_content(
        model=settings.embed_model,
        contents=[query],
    )
    return res.embeddings[0].values


def retrieve(query: str, k: int = 5) -> List[RetrievedChunk]:
    db = lancedb.connect(str(settings.lancedb_dir))
    table = db.open_table(settings.lancedb_table)

    client = genai.Client(api_key=settings.gemini_api_key)
    qvec = embed_query(client, query)

    # LanceDB search
    results: List[Dict[str, Any]] = (
        table.search(qvec)
        .limit(k)
        .to_list()
    )

    chunks: List[RetrievedChunk] = []
    for r in results:
        chunks.append(
            RetrievedChunk(
                source_file=r.get("source_file", "unknown"),
                chunk_index=int(r.get("chunk_index", -1)),
                text=r.get("text", ""),
                score=r.get("_distance") or r.get("_score"),
            )
        )
    return chunks


def format_context(chunks: List[RetrievedChunk]) -> str:
    # Context بسته‌بندی شده برای LLM
    blocks = []
    for c in chunks:
        header = f"[SOURCE: {c.source_file} | chunk={c.chunk_index}]"
        blocks.append(header + "\n" + c.text.strip())
    return "\n\n---\n\n".join(blocks)
