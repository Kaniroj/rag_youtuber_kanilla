from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, List

import lancedb
from google import genai

from backend.config import settings
from backend.constants import DATA_PATH


VECTOR_COLUMN = "embedding"
EMBED_DIM = 768  # text-embedding-004


def iter_text_files(root: Path) -> Iterable[Path]:
    """Yield all .txt files under root."""
    yield from root.glob("**/*.txt")


def infer_collection(path: Path) -> str:
    name = path.name.lower()

    allow_keywords = [
        "rag",
        "lancedb",
        "vector database",
        "fastapi",
        "pydantic",
        "pydanticai",
        "gemini",
        "azure",
        "function",
        "streamlit",
        "asgi",
    ]

    block_keywords = [
        "xgboost",
        "logistic regression",
        "regularization",
        "duckdb",
        "sakila",
        "sql analytics",
        "terraform",
        "snowflake",
        "dbt",
        "excel",
        "xlwings",
        "trafiklab",
    ]

    if any(b in name for b in block_keywords):
        return "misc"

    if any(a in name for a in allow_keywords):
        return "transcripts"

    return "misc"


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """Simple sliding-window chunking with overlap."""
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

        # Move forward with overlap (and avoid infinite loops)
        next_start = end - overlap
        start = next_start if next_start > start else end

    return chunks


def embed_texts(client: genai.Client, texts: List[str]) -> List[List[float]]:
    """Embed texts using the same model as retrieval."""
    res = client.models.embed_content(
        model=settings.embed_model,
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

    counts = Counter(infer_collection(p) for p in files)
    print("Collection file counts:", dict(counts))

    db = lancedb.connect(str(settings.lancedb_dir))

    # Drop table (dev mode)
    try:
        existing = set(db.list_tables())  # newer lancedb
    except Exception:
        existing = set(db.table_names())  # older lancedb

    if settings.lancedb_table in existing:
        db.drop_table(settings.lancedb_table)

    # Build client BEFORE creating table (we need a seed embedding for schema)
    client = genai.Client(api_key=settings.gemini_api_key)

    # Create table with a non-zero seed row (avoid zero-vector "schema magnet")
    seed_text = "__schema_seed_row_do_not_retrieve__"
    seed_vec = embed_texts(client, [seed_text])[0]

    seed_row = {
        "collection": "seed",
        "source_file": "__seed__",
        "chunk_index": -1,
        "text": seed_text,
        VECTOR_COLUMN: seed_vec,
    }

    table = db.create_table(settings.lancedb_table, data=[seed_row])

    total_chunks = 0

    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)
        if not chunks:
            continue

        vectors = embed_texts(client, chunks)
        collection = infer_collection(path)

        rows = [
            {
                "collection": collection,
                "source_file": path.name,
                "chunk_index": i,
                "text": chunk,
                VECTOR_COLUMN: vec,
            }
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]

        table.add(rows)
        total_chunks += len(rows)
        print(f"[OK] {path.name}: {len(rows)} chunks ({collection})")

    print(f"Done. Total chunks added: {total_chunks}")
    print("Table:", settings.lancedb_table)
    print('Tip: In retrieval, filter with where("collection = \'transcripts\'").')


if __name__ == "__main__":
    main()
