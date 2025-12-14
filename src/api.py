from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Dict, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.history_store import append as hist_append
from src.history_store import clear as hist_clear
from src.history_store import get as hist_get
from src.rag_engine import answer_question
from src.schemas import RagAnswer, ChatRequest
from src.video_mvp import make_youtube_description, make_youtube_tags

# -------------------------------------------------
# FastAPI app MUST be defined before any decorators
# -------------------------------------------------
app = FastAPI(
    title="RAG Youtuber API",
    description="چت‌بات RAG مبتنی بر ترنسکریپت‌های کورس کوکچون گیان",
    version="0.3.1",
)

# -----------------------------
# Cost-saving knobs (tune here)
# -----------------------------
DEFAULT_K = int(os.getenv("RAG_K", "3"))
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "600"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "900"))
MAX_CACHE_ITEMS = int(os.getenv("MAX_CACHE_ITEMS", "256"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "10"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "6"))

# -----------------------------
# In-memory state (ephemeral)
# -----------------------------
_cache: Dict[str, Tuple[float, RagAnswer]] = {}
_rate: Dict[str, Tuple[float, int]] = {}


def _now() -> float:
    return time.time()


def _make_cache_key(question: str, language: str, k: int) -> str:
    raw = f"{language}|k={k}|{question}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _cache_get(key: str) -> RagAnswer | None:
    item = _cache.get(key)
    if not item:
        return None
    ts, value = item
    if _now() - ts > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: RagAnswer) -> None:
    # Light eviction: drop oldest ~10% when full
    if len(_cache) >= MAX_CACHE_ITEMS:
        drop_n = max(1, MAX_CACHE_ITEMS // 10)
        oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[:drop_n]
        for k, _ in oldest:
            _cache.pop(k, None)
    _cache[key] = (_now(), value)


def _rate_limit_key(request: Request) -> str:
    # Azure front door / proxies often set x-forwarded-for
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    key = _rate_limit_key(request)
    now = _now()
    window_start, count = _rate.get(key, (now, 0))

    # New window
    if now - window_start > RATE_LIMIT_WINDOW_SECONDS:
        _rate[key] = (now, 1)
        return

    if count >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")

    _rate[key] = (window_start, count + 1)


def _ensure_session_id(session_id: str | None) -> str:
    return session_id.strip() if session_id and session_id.strip() else str(uuid.uuid4())


# -----------------------------
# UI (HTML) - served at /ui
# -----------------------------
CHAT_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>RAG Chat</title>
  <style>
    /* (din CSS här om du vill) */
  </style>
</head>
<body>
  <div class="container">
    <!-- (din UI här om du vill) -->
  </div>

<script>
function getSessionId() {
  let sid = localStorage.getItem("rag_session_id");
  if (!sid) {
    sid = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + "-" + String(Math.random()).slice(2));
    localStorage.setItem("rag_session_id", sid);
  }
  return sid;
}

const history = [];

function setStatus(text) {
  const el = document.getElementById('statusBadge');
  if (el) el.textContent = text;
}

function renderHistory() {
  const chat = document.getElementById('chat');
  if (!chat) return;
  chat.innerHTML = "";
  for (const h of history) {
    const wrapper = document.createElement('div');
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = h.role === 'user' ? "👤 You" : "🤖 Bot";
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (h.role === 'user' ? 'user' : 'bot');
    bubble.textContent = h.content;
    wrapper.appendChild(meta);
    wrapper.appendChild(bubble);
    chat.appendChild(wrapper);
  }
  chat.scrollTop = chat.scrollHeight;
}

function shortenText(text, maxLen = 180) {
  if (!text) return "";
  const t = String(text).trim();
  if (t.length <= maxLen) return t;
  const sliced = t.slice(0, maxLen);
  const lastSpace = sliced.lastIndexOf(" ");
  return (lastSpace > 80 ? sliced.slice(0, lastSpace) : sliced) + "...";
}

async function loadHistoryFromApi() {
  const sid = getSessionId();
  try {
    const resp = await fetch(`/api/history/${sid}`);
    const data = await resp.json();
    history.length = 0;
    for (const m of (data.messages || [])) {
      history.push(m);
    }
    renderHistory();
  } catch (e) { /* ignore */ }
}

async function ask() {
  const qEl = document.getElementById('q');
  const q = (qEl ? qEl.value : "").trim();
  const langEl = document.getElementById('lang');
  const language = langEl ? langEl.value : "sv";
  const session_id = getSessionId();
  if (!q) return;

  const spinner = document.getElementById('spinner');
  const askBtn = document.getElementById('askBtn');
  if (spinner) spinner.style.display = 'block';
  if (askBtn) askBtn.disabled = true;
  setStatus("Working...");

  history.push({ role: 'user', content: q });
  renderHistory();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ question: q, language, session_id })
    });

    const data = await resp.json();

    if (!resp.ok) {
      history.push({ role: 'assistant', content: JSON.stringify(data, null, 2) });
      renderHistory();
      setStatus("Error");
      return;
    }

    history.push({ role: 'assistant', content: data.answer });
    renderHistory();

    const shortSources = (data.sources || []).map(s => ({
      video_id: s.video_id,
      chunk_index: s.chunk_index,
      text: shortenText(s.text, 180),
    }));

    const sEl = document.getElementById('s');
    if (sEl) sEl.textContent = JSON.stringify(shortSources, null, 2);

    if (qEl) qEl.value = '';
    setStatus("Ready");
  } catch (err) {
    history.push({ role: 'assistant', content: `Error: ${err}` });
    renderHistory();
    setStatus("Error");
  } finally {
    if (spinner) spinner.style.display = 'none';
    if (askBtn) askBtn.disabled = false;
  }
}

window.addEventListener("load", loadHistoryFromApi);
</script>
</body>
</html>
"""

# -----------------------------
# Base endpoints
# -----------------------------
@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "rag-youtuber", "docs": "/docs", "ui": "/ui"}


@app.get("/ui", response_class=HTMLResponse)
async def ui() -> str:
    return CHAT_HTML


# Kort health (för snabb test)
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# API health (för Azure / monitoring)
@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "build": "cost-optimized-2025-12-12"}


@app.get("/api/routes")
def list_routes():
    return [{"path": r.path, "methods": sorted(list(r.methods))} for r in app.router.routes]


# -----------------------------
# History endpoints
# -----------------------------
@app.get("/api/history/{session_id}")
def get_history(session_id: str):
    items = hist_get(session_id)
    return {
        "session_id": session_id,
        "messages": [{"role": i.role, "content": i.content} for i in items],
    }


@app.delete("/api/history/{session_id}")
def delete_history(session_id: str):
    hist_clear(session_id)
    return {"session_id": session_id, "deleted": True}


# -----------------------------
# YouTube description & tags
# -----------------------------
@app.get("/api/videos/{video_id}/description")
async def video_description(video_id: str):
    desc = await make_youtube_description(video_id)
    return {"video_id": video_id, "description": desc}


@app.get("/api/videos/{video_id}/tags")
async def video_tags(video_id: str):
    tags = await make_youtube_tags(video_id)
    return {"video_id": video_id, "tags": tags}


# -----------------------------
# Chat (stores history + cache)
# -----------------------------
@app.post("/api/chat", response_model=RagAnswer)
async def chat_endpoint(payload: ChatRequest, request: Request) -> RagAnswer:
    _check_rate_limit(request)

    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required.")

    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Question too long. Max {MAX_QUESTION_CHARS} characters.",
        )

    session_id = _ensure_session_id(getattr(payload, "session_id", None))
    lang = payload.language or "sv"
    k = DEFAULT_K

    # Save user message
    hist_append(session_id, "user", question)

    # Cache
    cache_key = _make_cache_key(question=question, language=lang, k=k)
    cached = _cache_get(cache_key)
    if cached is not None:
        hist_append(session_id, "assistant", cached.answer)
        return cached

    # RAG answer
    result = await answer_question(
        question=question,
        k=k,
        language=lang,
    )

    # Save assistant message + cache
    hist_append(session_id, "assistant", result.answer)
    _cache_set(cache_key, result)
    return result
