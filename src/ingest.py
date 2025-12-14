from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import lancedb
from google import genai

from src.config import settings


# ---------- Chunking ----------
def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """
    Enkel chunking med overlap.
    chunk_size/overlap är i antal tecken (robust och enkelt).
    """
    text = (text or "").strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:
            break

        start = max(0, end - overlap)

    return chunks


# ---------- Embeddings ----------
def _extract_embedding_values(resp) -> List[float]:
    """
    google-genai kan returnera embedding i lite olika format beroende på version.
    Vi försöker hantera de vanligaste.
    """
    # Vanligt: resp.embedding.values
    if hasattr(resp, "embedding") and hasattr(resp.embedding, "values"):
        return list(resp.embedding.values)

    # Ibland: resp.embeddings[0].values
    if hasattr(resp, "embeddings") and resp.embeddings:
        emb0 = resp.embeddings[0]
        if hasattr(emb0, "values"):
            return list(emb0.values)

    raise ValueError(f"Kunde inte hitta embedding values i responsen: {type(resp)}")


def embed_texts(client: genai.Client, texts: List[str]) -> List[List[float]]:
    """
    Skapar embeddings en och en (säkert).
    """
    embeddings: List[List[float]] = []

    for t in texts:
        resp = client.models.embed_content(
            model="models/text-embedding-004",
            contents=t,  # ✅ här ska det vara texten, inte 'chunks'
        )
        embeddings.append(_extract_embedding_values(resp))

    return embeddings


# ---------- DB ----------
def get_table():
    Path(settings.lancedb_dir).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(settings.lancedb_dir)

    try:
        table = db.open_table(settings.lancedb_table)
    except Exception:
        # Fallback: skapa en tom tabell med ett init-row och ta bort den direkt
        table = db.create_table(
            settings.lancedb_table,
            data=[
                {
                    "id": "init",
                    "video_id": "init",
                    "chunk_index": 0,
                    "text": "init",
                    "embedding": [0.0] * 768,  # OBS: måste matcha embedding-dim i din tabell
                }
            ],
            mode="overwrite",
        )
        table.delete("id = 'init'")

    return table


def ingest_folder(
    table,
    transcripts_dir: Path,
    glob_pattern: str = "*.txt",
):
    client = genai.Client(api_key=settings.gemini_api_key)

    files = sorted(transcripts_dir.glob(glob_pattern))
    if not files:
        print(f"Inga filer hittades i: {transcripts_dir} ({glob_pattern})")
        return

    for file in files:
        video_id = file.stem  # ex: "video_10" eller YouTube-id om ni döper så
        text = file.read_text(encoding="utf-8", errors="ignore")

        chunks = chunk_text(text, chunk_size=1200, overlap=200)
        if not chunks:
            print(f"Skippar tom fil: {file.name}")
            continue

        # Rensa gamla chunks för samma video_id (upsert-beteende)
        table.delete(f"video_id = '{video_id}'")

        embs = embed_texts(client, chunks)

        rows: List[Dict] = []
        for i, (chunk, emb) in enumerate(zip(chunks, embs)):
            rows.append(
                {
                    "id": f"{video_id}_{i}",
                    "video_id": video_id,
                    "chunk_index": i,
                    "text": chunk,
                    "embedding": emb,
                }
            )

        table.add(rows)

        print(f"[OK] {file.name}: {len(rows)} chunks -> tabell '{settings.lancedb_table}'")


if __name__ == "__main__":
    transcripts_dir = Path(os.getenv("TRANSCRIPTS_DIR", "data/transcripts"))

    table = get_table()
    ingest_folder(table, transcripts_dir=transcripts_dir)
