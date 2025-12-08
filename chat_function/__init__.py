from __future__ import annotations

import json

import azure.functions as func

from src.rag_engine import answer_question_sync


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function اصلی:
    - ورودی: JSON با فیلد "question"
    - خروجی: JSON با answer + sources (همان RagAnswer)
    """
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    question = body.get("question")
    if not question:
        return func.HttpResponse(
            json.dumps({"error": "Missing 'question' field"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        rag_answer = answer_question_sync(question, k=5)
        # RagAnswer یک Pydantic BaseModel است → می‌توانیم model_dump کنیم
        return func.HttpResponse(
            rag_answer.model_dump_json(indent=2, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        # خطاهای غیرمنتظره
        return func.HttpResponse(
            json.dumps({"error": f"Internal error: {e}"}),
            status_code=500,
            mimetype="application/json",
        )
