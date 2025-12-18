from __future__ import annotations

from typing import List

from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from backend.config import settings
from knowledge_base.retriever import retrieve, format_context, RetrievedChunk


SYSTEM_PROMPT = """
You are a nerdy, playful Swedish data-engineering YouTuber helping students learn.
You answer questions based ONLY on the provided transcript context.
If the context is insufficient, say you don't know based on the transcripts.
Be clear, practical, and slightly humorous (but not cringe).
Always cite sources in the format: (source_file, chunk_index).
""".strip()


# ✅ Correct Gemini setup
model = GeminiModel(
    settings.chat_model,
    provider=GoogleGLAProvider(api_key=settings.gemini_api_key),
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
)


async def answer_question(question: str, k: int = 5) -> str:
    # 1. Retrieve chunks
    chunks: List[RetrievedChunk] = retrieve(question, k=k)

    # 2. Build context
    context = format_context(chunks)

    # 3. Sources
    sources_text = "\n".join(
        f"- ({c.source_file}, chunk {c.chunk_index})"
        for c in chunks
    )

    # 4. Prompt
    prompt = f"""
TRANSCRIPT CONTEXT:
{context}

USER QUESTION:
{question}

Answer the question using the context above.
At the end of your answer, include a section called "Sources" and list:
{sources_text}
""".strip()

    # 5. Run agent
    result = await agent.run(prompt)

    # ✅ THIS IS THE FIX
    return result.output
