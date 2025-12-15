from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from knowledge_base.rag_agent import answer_question

app = FastAPI(
    title="RAG Youtuber API",
    version="0.1.0",
)


class Prompt(BaseModel):
    prompt: str


@app.get("/test")
async def test():
    return {"test": "hello"}


@app.post("/rag/query")
async def query_documentation(query: Prompt):
    if not query.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        answer = await answer_question(query.prompt, k=5)
        return {"answer": answer}
    except Exception as e:
        # t.ex. quota error
        raise HTTPException(status_code=500, detail=str(e))
