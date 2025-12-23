from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import lancedb
from google import genai

from backend.config import settings


@dataclass
class RetrievedChunk:
    source_file: str
    chunk_index: int
    text: str
    score: float | None = None


VECTOR_COLUMN = "embedding"


def embed_query(client: genai.Client, query: str) -> List[float]:
    res = client.models.embed_content(
        model=settings.embed_model,
        contents=[query],
    )
    return res.embeddings[0].values


def retrieve(query: str, k: int = 5) -> List[RetrievedChunk]:
    """
    Retrieve top-k chunks from LanceDB for a given query.
    Applies:
      - optional collection filter (if 'collection' column exists)
      - drops 'schema' rows
      - basic distance gate to reduce irrelevant matches
    """
    db = lancedb.connect(str(settings.lancedb_dir))
    table = db.open_table(settings.lancedb_table)

    client = genai.Client(api_key=settings.gemini_api_key)
    qvec = embed_query(client, query)

    # --- LanceDB search ---
    # NOTE: Some editors show yellow warnings here because LanceDB typing is incomplete.
    search = table.search(qvec)

    # If your table has a 'collection' column (after re-ingest), keep only transcripts.
    # If not, this will raise at runtime; comment it out until you re-ingest with collection.
    
    search = search.where("collection = 'transcripts'")

    results: List[Dict[str, Any]] = search.limit(k).to_list()

    chunks: List[RetrievedChunk] = []
    for r in results:
        src = (r.get("source_file") or "").strip()

        # 1) Drop schema (highly generic / dominates retrieval)
        if src.lower() == "schema":
            continue

        dist = r.get("_distance")
        score = dist if dist is not None else r.get("_score")

        # 2) Basic distance gate (tune later using logs)
        # With your logs, 1.05 is a reasonable first safety cutoff.
        if dist is not None and dist >= 1.05:
            continue

        chunks.append(
            RetrievedChunk(
                source_file=src or "unknown",
                chunk_index=int(r.get("chunk_index", -1)),
                text=r.get("text", "") or "",
                score=score,
            )
        )

    return chunks


def format_context(chunks: List[RetrievedChunk]) -> str:
    blocks: List[str] = []
    for c in chunks:
        header = f"[SOURCE: {c.source_file} | chunk={c.chunk_index}]"
        blocks.append(header + "\n" + c.text.strip())
    return "\n\n---\n\n".join(blocks)
