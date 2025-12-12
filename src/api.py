from __future__ import annotations

import os
import time
import hashlib
from typing import Dict, Tuple, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.rag_engine import RagAnswer, answer_question
from src.schemas import ChatRequest

app = FastAPI(
    title="RAG Youtuber API",
    description="چت‌بات RAG مبتنی بر ترنسکریپت‌های کورس کوکچون گیان",
    version="0.2.0",
)

# -----------------------------
# Cost-saving knobs (tune here)
# -----------------------------
# کمتر = ارزان‌تر (ولی ممکن است دقت کمی کاهش یابد)
DEFAULT_K = int(os.getenv("RAG_K", "3"))  # قبلاً 5 بود

# جلوگیری از سوال‌های خیلی بلند (توکن و هزینه)
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "600"))

# کش کوتاه‌مدت برای سوال‌های تکراری (بیشترین صرفه‌جویی)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "900"))  # 15 دقیقه
MAX_CACHE_ITEMS = int(os.getenv("MAX_CACHE_ITEMS", "256"))

# rate limit خیلی ساده (در حافظه) برای جلوگیری از کلیک/اسپم
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
    # نگذار سوال خام key شود (بهتر برای حافظه)
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
    # ساده: اگر بزرگ شد، چند تا قدیمی را حذف کن
    if len(_cache) >= MAX_CACHE_ITEMS:
        # حذف ~10% قدیمی‌ها
        oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[: max(1, MAX_CACHE_ITEMS // 10)]
        for k, _ in oldest:
            _cache.pop(k, None)
    _cache[key] = (_now(), value)


def _rate_limit_key(request: Request) -> str:
    # بهترین حالت: IP واقعی از reverse proxy
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    client = request.client.host if request.client else "unknown"
    return client


def _check_rate_limit(request: Request) -> None:
    key = _rate_limit_key(request)
    now = _now()
    window_start, count = _rate.get(key, (now, 0))

    if now - window_start > RATE_LIMIT_WINDOW_SECONDS:
        _rate[key] = (now, 1)
        return

    if count >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")

    _rate[key] = (window_start, count + 1)


CHAT_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>RAG Chat</title>
  <style>
    :root{
      --bg: #f7f8fc;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --border: #e5e7eb;
      --primary: #2563eb;
      --primary-2: #1d4ed8;
      --user: #e0f2fe;
      --bot: #ecfdf5;
      --shadow: 0 10px 30px rgba(0,0,0,.06);
      --radius: 14px;
    }
    body.dark{
      --bg:#0b1220;
      --card:#0f172a;
      --text:#e5e7eb;
      --muted:#9ca3af;
      --border:#243044;
      --primary:#60a5fa;
      --primary-2:#3b82f6;
      --user:#0b3a55;
      --bot:#0b3b2a;
      --shadow: 0 10px 30px rgba(0,0,0,.35);
    }

    *{ box-sizing: border-box; }
    body{
      margin:0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: radial-gradient(1200px 600px at 20% 0%, rgba(37,99,235,.12), transparent 60%),
                  radial-gradient(900px 500px at 90% 20%, rgba(16,185,129,.10), transparent 55%),
                  var(--bg);
      color: var(--text);
    }
    .container{
      max-width: 980px;
      margin: 28px auto;
      padding: 0 14px;
    }
    .topbar{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      margin-bottom: 16px;
    }
    .brand{
      display:flex;
      align-items:center;
      gap:10px;
    }
    .logo{
      width:42px;height:42px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(37,99,235,.95), rgba(16,185,129,.9));
      box-shadow: var(--shadow);
      display:grid;
      place-items:center;
      color:white;
      font-weight:800;
    }
    .title{
      line-height:1.1;
    }
    .title h1{
      font-size: 20px;
      margin: 0;
    }
    .title p{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 13px;
    }
    .actions{
      display:flex;
      gap:10px;
      align-items:center;
    }
    .btn{
      border: 1px solid var(--border);
      background: var(--card);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 12px;
      cursor:pointer;
      box-shadow: 0 6px 18px rgba(0,0,0,.05);
    }
    .btn.primary{
      background: var(--primary);
      border-color: transparent;
      color: white;
      font-weight: 600;
    }
    .btn.primary:hover{ background: var(--primary-2); }
    .btn:disabled{ opacity:.6; cursor:not-allowed; }

    .grid{
      display:grid;
      grid-template-columns: 1.35fr .65fr;
      gap: 14px;
    }
    @media (max-width: 900px){
      .grid{ grid-template-columns: 1fr; }
    }

    .card{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow:hidden;
    }
    .card-header{
      padding: 14px 14px 10px;
      border-bottom: 1px solid var(--border);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
    }
    .card-header .h{
      display:flex; align-items:center; gap:10px;
      font-weight: 700;
    }
    .badge{
      font-size: 12px;
      color: var(--muted);
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 999px;
    }
    .card-body{ padding: 14px; }

    label{ color: var(--muted); font-size: 13px; }
    select, textarea{
      width:100%;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text);
      border-radius: 12px;
      padding: 10px 12px;
      outline:none;
    }
    textarea{ min-height: 92px; resize: vertical; }

    .spinner{
      display:none;
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .chat{
      display:flex;
      flex-direction:column;
      gap:10px;
      max-height: 460px;
      overflow:auto;
      padding-right: 4px;
    }
    .bubble{
      border-radius: 14px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      line-height: 1.4;
      white-space: pre-wrap;
    }
    .bubble.user{ background: var(--user); }
    .bubble.bot{ background: var(--bot); }
    .meta{
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
      display:flex;
      align-items:center;
      gap:6px;
    }

    pre{
      margin:0;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--text);
    }
    .hint{
      font-size: 12px;
      color: var(--muted);
      margin-top: 10px;
    }
    a{ color: var(--primary); text-decoration: none; }
    a:hover{ text-decoration: underline; }
  </style>
</head>

<body>
  <div class="container">
    <div class="topbar">
      <div class="brand">
        <div class="logo">R</div>
        <div class="title">
          <h1>RAG Chat (Azure)</h1>
          <p>Retrieval Augmented Generation • <a href="/docs">Open API docs</a></p>
        </div>
      </div>

      <div class="actions">
        <button class="btn" onclick="toggleTheme()">🌗 Theme</button>
        <button class="btn" onclick="clearChat()">🧹 Clear</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-header">
          <div class="h">💬 Chat</div>
          <div class="badge" id="statusBadge">Ready</div>
        </div>

        <div class="card-body">
          <div style="display:flex; gap:10px;">
            <div style="flex:0.4;">
              <label>Language</label>
              <select id="lang">
                <option value="sv" selected>sv</option>
                <option value="en">en</option>
                <option value="fa">fa</option>
              </select>
            </div>
            <div style="flex:1;">
              <label>Question</label>
              <textarea id="q" placeholder="Skriv din fråga här..."></textarea>
            </div>
          </div>

          <div style="margin-top:10px;">
            <button id="askBtn" class="btn primary" onclick="ask()">🚀 Ask</button>
          </div>

          <div id="spinner" class="spinner">⏳ Thinking...</div>

          <div class="hint">Sources visas till höger (kortade). Backend är optimerad för lägre kostnad.</div>

          <div style="margin-top:12px;">
            <div class="meta">🧠 Chat history</div>
            <div id="chat" class="chat"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="h">📚 Latest sources</div>
          <div class="badge">short</div>
        </div>
        <div class="card-body">
          <pre id="s"></pre>
          <div class="hint">UI kortar sources. API returnerar full text.</div>
        </div>
      </div>
    </div>
  </div>

<script>
const history = [];

function setStatus(text) {
  document.getElementById('statusBadge').textContent = text;
}

function renderHistory() {
  const chat = document.getElementById('chat');
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

function clearChat() {
  history.length = 0;
  renderHistory();
  document.getElementById('s').textContent = "";
  setStatus("Ready");
}

function toggleTheme() {
  document.body.classList.toggle('dark');
}

async function ask() {
  const qEl = document.getElementById('q');
  const q = qEl.value.trim();
  const language = document.getElementById('lang').value;

  if (!q) return;

  const spinner = document.getElementById('spinner');
  const askBtn = document.getElementById('askBtn');

  spinner.style.display = 'block';
  askBtn.disabled = true;
  setStatus("Working...");

  history.push({ role: 'user', content: q });
  renderHistory();
  document.getElementById('s').textContent = '';

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ question: q, language })
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

    document.getElementById('s').textContent = JSON.stringify(shortSources, null, 2);

    qEl.value = '';
    setStatus("Ready");
  } catch (err) {
    history.push({ role: 'assistant', content: `Error: ${err}` });
    renderHistory();
    setStatus("Error");
  } finally {
    spinner.style.display = 'none';
    askBtn.disabled = false;
  }
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    # کش شدن UI در مرورگر/CDN کمک می‌کند Functions کمتر درگیر شود
    # (آسیبی به API نمی‌زند)
    return CHAT_HTML


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "build": "cost-optimized-2025-12-12"}


@app.get("/api/routes")
def list_routes():
    return [{"path": r.path, "methods": sorted(list(r.methods))} for r in app.router.routes]


@app.post("/api/chat", response_model=RagAnswer)
async def chat_endpoint(payload: ChatRequest, request: Request) -> RagAnswer:
    _check_rate_limit(request)

    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is required.")

    # جلوگیری از توکن/هزینه زیاد
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Question too long. Max {MAX_QUESTION_CHARS} characters.",
        )

    lang = payload.language or "sv"
    k = DEFAULT_K

    cache_key = _make_cache_key(question=question, language=lang, k=k)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = await answer_question(
        question=question,
        k=k,
        language=lang,
    )

    _cache_set(cache_key, result)
    return result
