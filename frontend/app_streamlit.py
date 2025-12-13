from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "https://datatalks-ai-function.azurewebsites.net"
API_URL = f"{API_BASE_URL}/api/chat"

LANGUAGES = [("sv", "Svenska"), ("en", "English"), ("fa", "فارسی")]

st.set_page_config(page_title="RAG Chat (Azure)", page_icon="🤖", layout="wide")

# ---------- State ----------
if "language" not in st.session_state:
    st.session_state.language = "sv"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # [{role, content}]

if "latest_sources" not in st.session_state:
    st.session_state.latest_sources = []  # list of sources from last answer

if "dark" not in st.session_state:
    st.session_state.dark = False

# ---------- Simple theme CSS ----------
def inject_css(dark: bool) -> None:
    if dark:
        bg = "#0b1220"
        card = "#0f172a"
        border = "#22304a"
        text = "#e5e7eb"
        muted = "#9ca3af"
    else:
        bg = "#f6f8fb"
        card = "#ffffff"
        border = "#e6eaf2"
        text = "#0f172a"
        muted = "#6b7280"

    st.markdown(
        f"""
        <style>
          .stApp {{
            background: {bg};
          }}
          .kani-card {{
            background: {card};
            border: 1px solid {border};
            border-radius: 16px;
            padding: 16px 18px;
            color: {text};
          }}
          .kani-muted {{
            color: {muted};
            font-size: 0.9rem;
          }}
          .kani-title {{
            font-size: 1.6rem;
            font-weight: 800;
            margin: 0;
          }}
          .kani-sub {{
            margin-top: 4px;
            margin-bottom: 0;
          }}
          /* Make chat area feel roomy */
          section.main > div {{
            padding-top: 1.2rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_css(st.session_state.dark)

# ---------- Header ----------
top_left, top_right = st.columns([0.75, 0.25], vertical_alignment="center")

with top_left:
    st.markdown(
        """
        <div class="kani-card">
          <div style="display:flex; gap:14px; align-items:center;">
            <div style="width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#22c1c3,#7f53ac);display:flex;align-items:center;justify-content:center;font-weight:900;color:white;">
              R
            </div>
            <div>
              <p class="kani-title">RAG Chat (Azure)</p>
              <p class="kani-sub kani-muted">Retrieval Augmented Generation • <a href="/docs" target="_blank">Open API docs</a></p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with top_right:
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.dark = st.toggle("Theme", value=st.session_state.dark)
    with c2:
        if st.button("Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.latest_sources = []
            st.rerun()

# Re-inject CSS if theme changed
inject_css(st.session_state.dark)

# ---------- Main layout ----------
left, right = st.columns([0.62, 0.38], gap="large")

# ----- Left: chat -----
with left:
    st.markdown('<div class="kani-card">', unsafe_allow_html=True)
    st.subheader("Chat")

    lang = st.selectbox(
        "Language",
        options=LANGUAGES,
        format_func=lambda x: x[1],
        index=[i for i, x in enumerate(LANGUAGES) if x[0] == st.session_state.language][0],
    )
    st.session_state.language = lang[0]
    current_lang = st.session_state.language

    st.markdown('<p class="kani-muted">Sources visas till höger (kortade). Backend är optimerad för lägre kostnad.</p>', unsafe_allow_html=True)

    # render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Skriv din fråga här...")

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        try:
            resp = requests.post(
                API_URL,
                json={"question": question, "language": current_lang},
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()

            answer = data.get("answer", "")
            sources = data.get("sources", []) or []
            st.session_state.latest_sources = sources

            with st.chat_message("assistant"):
                st.markdown(answer)

            st.session_state.chat_history.append({"role": "assistant", "content": answer})

        except requests.RequestException as e:
            err = f"❌ Fel vid anslutning till API: {e}"
            with st.chat_message("assistant"):
                st.markdown(err)
            st.session_state.chat_history.append({"role": "assistant", "content": err})

    st.markdown("</div>", unsafe_allow_html=True)

# ----- Right: latest sources -----
with right:
    st.markdown('<div class="kani-card">', unsafe_allow_html=True)
    header_row = st.columns([0.75, 0.25], vertical_alignment="center")
    with header_row[0]:
        st.subheader("Latest sources")
    with header_row[1]:
        mode = st.selectbox(" ", options=["short", "full"], label_visibility="collapsed", index=0)

    sources = st.session_state.latest_sources or []

    def short_text(t: str, n: int = 220) -> str:
        t = (t or "").strip()
        if len(t) <= n:
            return t
        cut = t[:n]
        last_space = cut.rfind(" ")
        return (cut[:last_space] if last_space > 120 else cut) + "…"

    if not sources:
        st.markdown('<p class="kani-muted">Inga källor ännu. Ställ en fråga så dyker de upp här.</p>', unsafe_allow_html=True)
    else:
        # show as JSON-like
        rendered = []
        for s in sources:
            rendered.append(
                {
                    "video_id": s.get("video_id", ""),
                    "chunk_index": s.get("chunk_index", ""),
                    "text": short_text(s.get("text", "")) if mode == "short" else (s.get("text", "") or ""),
                }
            )
        st.json(rendered)

    st.markdown("</div>", unsafe_allow_html=True)
