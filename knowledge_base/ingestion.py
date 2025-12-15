from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import lancedb
from google import genai

from backend.constants import DATA_PATH
from backend.config import settings


EMBED_MODEL = "models/text-embedding-004"
VECTOR_COLUMN = "embedding"
EMBED_DIM = 768  # ← ثابت شده در تست


def iter_text_files(root: Path) -> Iterable[Path]:
    yield from root.glob("**/*.txt")


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    text = text.strip()
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
        start = max(end - overlap, end)

    return chunks


def embed_texts(client: genai.Client, texts: List[str]) -> List[List[float]]:
    res = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    return [e.values for e in res.embeddings]


def main() -> None:
    files = list(iter_text_files(DATA_PATH))
    print(f"DATA_PATH = {DATA_PATH}")
    print(f"Found {len(files)} .txt files")

    if not files:
        print("No .txt files to ingest.")
        return

    # --- LanceDB ---
    db = lancedb.connect(str(settings.lancedb_dir))

    # اگر جدول وجود دارد، پاکش کن (dev-mode, schema-safe)
    if settings.lancedb_table in db.table_names():
        db.drop_table(settings.lancedb_table)

    # ردیف نمونه برای تعریف schema
    schema_row = {
        "source_file": "schema",
        "chunk_index": 0,
        "text": "schema",
        VECTOR_COLUMN: [0.0] * EMBED_DIM,
    }

    table = db.create_table(
        settings.lancedb_table,
        data=[schema_row],
    )

    client = genai.Client(api_key=settings.gemini_api_key)

    total_chunks = 0

    # --- ingestion ---
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)

        if not chunks:
            continue

        vectors = embed_texts(client, chunks)

        rows = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            rows.append(
                {
                    "source_file": path.name,
                    "chunk_index": i,
                    "text": chunk,
                    VECTOR_COLUMN: vec,
                }
            )

        table.add(rows)
        total_chunks += len(rows)
        print(f"[OK] {path.name}: {len(rows)} chunks")

    print(f"Done. Total chunks added: {total_chunks}")
    print("Table:", settings.lancedb_table)


if __name__ == "__main__":
    main()
