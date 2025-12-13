from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict

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
        chunks.append(text[start:end].strip())
        if end == n:
            break
        start = max(0, end - overlap)

    return [c for c in chunks if c]


# ---------- Embeddings ----------
def embed_texts(client: genai.Client, texts: List[str]) -> List[List[float]]:
    """
    Skapar embeddings en och en (säkert).
    Om du vill snabba upp senare kan vi batcha.
    """
    embeddings: List[List[float]] = []
    for t in texts:
        resp = client.models.embed_content(
            model="models/embedding-gecko-001",
            contents=t,
        )
        # resp.embedding.values är standard-format i genai
        embeddings.append(list(resp.embedding.values))
    return embeddings


# ---------- DB ----------
def get_table():
    Path(settings.lancedb_dir).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(settings.lancedb_dir)

    # Om tabellen inte finns: skapa med ert schema via första insert (LanceDB kan infer).
    # Men ni har redan tabell + schema, så öppna bara:
    try:
        table = db.open_table(settings.lancedb_table)
    except Exception:
        # fallback: skapa tom tabell med minimal schema-liknande kolumner
        table = db.create_table(
            settings.lancedb_table,
            data=[
                {
                    "id": "init",
                    "video_id": "init",
                    "chunk_index": 0,
                    "text": "init",
                    "embedding": [0.0] * 768,
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
        video_id = file.stem  # ex: "video_10" eller själva YouTube-id om ni döper så
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

        # Lite debug-info
        print(f"[OK] {file.name}: {len(rows)} chunks -> tabell '{settings.lancedb_table}'")


if __name__ == "__main__":
    # Var ni har era transkript:
    # Alternativ 1: sätt env var TRANSCRIPTS_DIR
    # Alternativ 2: hårdkoda en rimlig default
    transcripts_dir = Path(os.getenv("TRANSCRIPTS_DIR", "data/transcripts"))

    table = get_table()
    ingest_folder(table, transcripts_dir=transcripts_dir)
